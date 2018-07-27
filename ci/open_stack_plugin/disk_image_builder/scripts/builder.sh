#!/bin/bash

init(){
# The initializer function that installs all the dependencies and sources the environment variables.
# The `init` function is called once only, even if builder script is run in the `all` mode or used just for calling
# out a single image creation mode.

    if [[ -f ./env_variables.sh ]];then
        echo "sourcing environment variables for this build"
        source ./env_variables.sh
    fi

    # Check whether Open Stack values are configured
    if [[ (  -z "${OS_AUTH_URL}" ) || (  -z "${OS_TENANT_NAME}" ) || ( -z "${OS_USERNAME}" ) || ( -z "${OS_PASSWORD}"  ) ||  ( -z "${OS_TENANT_ID}" ) ]];then
        echo >&2 "Image creation in openstack requires 'OS_AUTH_URL' 'OS_TENANT_NAME' and
            'OS_USERNAME' 'OS_PASSWORD' and 'OS_TENANT_ID' set in the environment"
        exit 1
    fi

    # Directory of the script
    scripts_dir="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

    # Path to the Disk Image Builder Elements
    export ELEMENTS_PATH="${scripts_dir}/../elements"

    # Installing the required dependencies
    source "${scripts_dir}/local_dependencies.sh"
    source "${scripts_dir}/base_image_config.conf"

    # The jenkins public key must be present in the following location
    export JENKINS_PUBLIC_SSH_KEY_PATH=~/.ssh/jenkins/id_rsa.pub

    # initiallizing the output directories
    recreate_input_output_image_dirs
}


conditional_init(){
# This is used when an image is to be build separately.
# This is used for avoiding duplicate initializations in the builder script.

    if [[ -z $BASH_ARGV ]];then
        init
    fi
}

recreate_input_output_image_dirs(){
# Delete and create the input and output directories.
# Don't delete the directories if `PERSIST_IMAGES` is set in the environment.

    if [[ -z "${PERSIST_IMAGES}" ]];then
        echo "removing and creating image directories"
        rm -rf  "${scripts_dir}/output_images";
        rm -rf "${scripts_dir}/input_images";
    fi
    mkdir -p "${scripts_dir}/output_images"
    mkdir -p "${scripts_dir}/input_images"
}

get_image_id_from_name(){
# Retrieve Image IDs of images in OpenStack
# param $1: Image_name

    _image_id_temp="$(openstack image show -c id -f value ${1} 2> /dev/null)"
}


download_base_image(){
# Download the base image from OpenStack for building our images
# param $1: OS name
# param $2: OS version
# `${!temp}` evaluates the value sourced from the variable in `base_image_config.conf` file.

    local temp="${1}_${2}"
    get_image_id_from_name "${!temp}"
    echo "downloading  ${_image_id_temp}"
    glance image-download --progress --file  "${scripts_dir}/input_images/${1}_${2}_base.img" "${_image_id_temp}"
}


remove_existing_image(){
# remove existing images in OpenStack
# param $1: OS name
# param $2: OS version
# param $3: OS identifier : `fips` or `common`

    echo "removing ${1}_${2}_${3}_DIB_updated"
    value="${1}_${2}_${3}_DIB_updated"
    get_image_id_from_name ${value}
    if [[ ${_image_id_temp} ]];then
        echo "deleting existing image ${_image_id_temp}"
        glance image-delete ${_image_id_temp}
    fi
}


upload_image(){
# Upload images to OpenStack
# param $1: OS name
# param $2: OS version

    temp="${1}_${2}"
    remove_existing_image ${1} ${2} ${3}
    echo "uploading ${temp}"
    if [[ ! -f "${scripts_dir}/output_images/template-${1}${2}-os.qcow2" ]];then
        echo >&2 "Image File ${temp} not created"
        exit 1
    fi
    glance image-create --progress  --disk-format qcow2 --container-format bare --visibility private --file "${scripts_dir}/output_images/template-${1}${2}-os.qcow2" --name "${1}_${2}_${3}_DIB_updated"
    recreate_input_output_image_dirs
}

check_rhel_params_present(){
# Check whether `Rhel` parameters are present in the environment

    if [[ ( -z "${RHN_USERNAME}" ) || ( -z "${RHN_PASSWORD}" ) || ( -z "${RHN_SKU_POOLID}" ) ]];then
        echo >&2 "Rhel Installation must contain following parameters 'RHN_USERNAME' 'RHN_PASSWORD' and 'RHN_SKU_POOLID' set in the environment"
        exit 1
    fi
}

build_fedora_images(){
# This `method` is used for building `Fedora` Images

    conditional_init
    local OS="fedora"
    for DIB_RELEASE in 27; do
       export DIB_RELEASE
       download_base_image $OS $DIB_RELEASE
       export DIB_LOCAL_IMAGE="$scripts_dir/input_images/${OS}_${DIB_RELEASE}_base.img"
       disk-image-create -o "${scripts_dir}/output_images/template-${OS}${DIB_RELEASE}-os" fedora redhat-common vm growroot jenkins-slave
       upload_image $OS $DIB_RELEASE 'common'
    done
}

build_centos_images(){
# This `method` is used for building `CentOS` Images.

    conditional_init
    local OS='centos'
    export DIB_RELEASE=7
    download_base_image $OS $DIB_RELEASE
    export DIB_LOCAL_IMAGE="$scripts_dir/input_images/${OS}_${DIB_RELEASE}_base.img"
    disk-image-create -o "${scripts_dir}/output_images/template-${OS}${DIB_RELEASE}-os" centos7 grub2 bootloader selinux-permissive jenkins-slave vm simple-init growroot epel
    upload_image $OS $DIB_RELEASE 'common'
}


build_rhelos_images(){
# This `method` is used for building `Rhel` Images.

    conditional_init
    check_rhel_params_present
    local OS='rhel'
    export DIB_RELEASE=7
    download_base_image $OS $DIB_RELEASE
    export DIB_LOCAL_IMAGE="$scripts_dir/input_images/${OS}_${DIB_RELEASE}_base.img"
    export REG_USER=$RHN_USERNAME
    export REG_PASSWORD=$RHN_PASSWORD
    export REG_POOL_ID=$RHN_SKU_POOLID
    export REG_METHOD=portal
    disk-image-create -o "${scripts_dir}/output_images/template-${OS}${DIB_RELEASE}-os" rhel7 rhel-common simple-init vm growroot jenkins-slave epel
    upload_image $OS $DIB_RELEASE 'common'
}


build_rhel_fips_images(){
# This `method` is used for building `Rhel` Images with FIPS enabled.

    conditional_init
    check_rhel_params_present
    local OS='rhel'
    export DIB_RELEASE=7
    download_base_image $OS $DIB_RELEASE
    export DIB_LOCAL_IMAGE="$scripts_dir/input_images/${OS}_${DIB_RELEASE}_base.img"
    export DIB_BOOTLOADER_DEFAULT_CMDLINE="fips=1"
    export REG_USER=$RHN_USERNAME
    export REG_PASSWORD=$RHN_PASSWORD
    export REG_POOL_ID=$RHN_SKU_POOLID
    export REG_METHOD=portal
    export IS_FIPS=true # This flag will set the necessary boot cmd line parameters in the install.d and finalise.d steps
    disk-image-create -o "${scripts_dir}/output_images/template-${OS}${DIB_RELEASE}-os" rhel7 rhel-common simple-init vm growroot jenkins-slave bootloader epel
    upload_image $OS $DIB_RELEASE 'fips'
}

if [[ ( ! -z "${1}" ) && ( $1 = "all" ) ]];then
    init
    build_fedora_images
    build_rhelos_images
    build_rhel_fips_images
fi

