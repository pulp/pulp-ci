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
    # These keys will be copied to the image being built, which allows ssh
    # access to those image instances.
    export JENKINS_PUBLIC_SSH_KEY_PATH=~/.ssh/authorized_keys

    # Identifier for the images
    identifier=common
    if [[ ( ! -z "${DOCKER}" ) && ( "${DOCKER}" = true) ]]; then
        identifier='docker'
    fi

    # initiallizing the output directories
    recreate_input_output_image_dirs
}


conditional_init(){
# This is used when an image is to be build separately.
# This is used for avoiding duplicate initializations in the builder script.

    if [[ -z "${BASH_ARGV}" ]];then
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
# Retrieve image ID for a given image name from OpenStack.
# Since many images can have the same name, We select the id from one of the images.
# param $1: Image_name
    _image_id_temp="$(openstack image list --name "${1}" -c ID -f value | tail -1)"
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
    get_image_id_from_name "${value}"
    if [[ "${_image_id_temp}" ]];then
        echo "deleting existing image ${_image_id_temp}"
        glance image-delete "${_image_id_temp}"
    fi
}


upload_image(){
# Upload images to OpenStack
# param $1: OS name
# param $2: OS version

    temp="${1}_${2}"
    remove_existing_image "${1}" "${2}" "${3}"
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
    FEDORA_RELEASES="${FEDORA_RELEASES:-${fedora_default}}"
    IFS=',' read -ra RELEASES <<< "${FEDORA_RELEASES}"
    for RELEASE in "${RELEASES[@]}"; do
       download_base_image "${OS}" "${RELEASE}"
       export DIB_LOCAL_IMAGE="${scripts_dir}/input_images/${OS}_${RELEASE}_base.img"
       disk-image-create -o "${scripts_dir}/output_images/template-${OS}${RELEASE}-os" fedora redhat-common vm growroot jenkins-slave
       upload_image "${OS}" "${RELEASE}" "${identifier}"
       unset DOCKER # unsetting docker
    done
}

build_centos_images(){
# This `method` is used for building `CentOS` Images.

    conditional_init
    local OS='centos'
    CENTOS_RELEASES="${CENTOS_RELEASES:-${centos_default}}"
    IFS=',' read -ra RELEASES <<< "${CENTOS_RELEASES}"
    for RELEASE in "${RELEASES[@]}"; do
        download_base_image "${OS}" "${RELEASE}"
        export DIB_LOCAL_IMAGE="${scripts_dir}/input_images/${OS}_${RELEASE}_base.img"
        disk-image-create -o "${scripts_dir}/output_images/template-${OS}${RELEASE}-os" centos7 grub2 bootloader selinux-permissive jenkins-slave vm simple-init growroot epel
        upload_image "${OS}" "${RELEASE}" "${identifier}"
    done
}


build_rhelos_images(){
# This `method` is used for building `Rhel` Images.

    conditional_init
    check_rhel_params_present
    local OS='rhel'
    RHEL_RELEASES="${RHEL_RELEASES:-${rhel_default}}"
    IFS=',' read -ra RELEASES <<< "${RHEL_RELEASES}"
    for RELEASE in "${RELEASES[@]}"; do
        download_base_image "${OS}" "${RELEASE}"
        export DIB_LOCAL_IMAGE="${scripts_dir}/input_images/${OS}_${RELEASE}_base.img"
        export REG_USER="${RHN_USERNAME}"
        export REG_PASSWORD="${RHN_PASSWORD}"
        export REG_POOL_ID="${RHN_SKU_POOLID}"
        export REG_METHOD=portal
        disk-image-create -o "${scripts_dir}/output_images/template-${OS}${RELEASE}-os" rhel7 rhel-common simple-init vm growroot jenkins-slave epel
        upload_image "${OS}" "${RELEASE}" "${identifier}"
    done
}


build_rhel_fips_images(){
# This `method` is used for building `Rhel` Images with FIPS enabled.

    conditional_init
    check_rhel_params_present
    local OS='rhel'
    RHEL_RELEASES="${RHEL_RELEASES:-${rhel_default}}"
    IFS=',' read -ra RELEASES <<< "${RHEL_RELEASES}"
    for RELEASE in "${RELEASES[@]}"; do
        download_base_image "${OS}" "${RELEASE}"
        export DIB_LOCAL_IMAGE="${scripts_dir}/input_images/${OS}_${RELEASE}_base.img"
        export DIB_BOOTLOADER_DEFAULT_CMDLINE="fips=1"
        export REG_USER="${RHN_USERNAME}"
        export REG_PASSWORD="${RHN_PASSWORD}"
        export REG_POOL_ID="${RHN_SKU_POOLID}"
        export REG_METHOD=portal
        export IS_FIPS=true # This flag will set the necessary boot cmd line parameters in the install.d and finalise.d steps
        disk-image-create -o "${scripts_dir}/output_images/template-${OS}${RELEASE}-os" rhel7 rhel-common simple-init vm growroot jenkins-slave bootloader epel
        upload_image "${OS}" "${RELEASE}" 'fips'
    done
}

if [[ ( ! -z "${1}" ) && ( "${1}" = "all" ) ]];then
    init
    build_fedora_images
    build_rhelos_images
    build_rhel_fips_images
fi

