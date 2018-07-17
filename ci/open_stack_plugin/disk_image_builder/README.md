# diskimage-builder Notes

## Contents:

* What is diskimage-builder + how to install
* What are elements
* How to create a custom element
* How to build our images
* How to import images into OpenStack


## What is diskimage-builder

The [diskimage-builder](https://docs.openstack.org/diskimage-builder/latest/)
project provides tooling to allow creation of `qcow2` images and allows the
user to combine any number of "elements" to create a custom image.  Elements
allow reuse of common image creation tasks. If you are familar with ansible
"roles", diskimage-builder elements are kind of like that.
First, you need to set up your environment and install diskimage-builder.

Currently diskimage-builder has a bug that prevents use of virtual environments
created with `python3 -m venv path/to/new/venv` (see:
https://bugs.launchpad.net/diskimage-builder/+bug/1745626 ). For this reason I
will show installing into a python2.7 virtual environment.

```
python2.7 -m virtualenv ~/envs/dibenv
source ~/envs/dibenv/bin/activate
pip install diskimage-builder
```

Additionally you need some tools that should be available from your package manager.
For example, on Fedora 26, I was able to install the following:

```
dnf install qemu-img yum-utils
```

This list may not be exhaustive, as the machines this workflow has been tested
on also have been set up with all necessary to run kvm based virtualization.

## What are elements

When you run the `disk-image-create` command, you provide a list of "elements"
that define how the image will be created. These Elements can either be user defined
(As in this case the Jenkins-slave element) and Open stack Elements.Elements define tasks to be done at
each of the "phases" of image creation. Each phase has a directory in the
"element" directory. The [phase
documentation](https://docs.openstack.org/diskimage-builder/latest/developer/developing_elements.html#phase-subdirectories)
shows the name of the phases and the order in which they are executed. An
element need only include directory for the phases in which it needs to execute
scripts.

Also not every phase runs on the image(chroot) that is being build. Some of the phases : 
root.d, extra-data.d, block-device.d,cleanup.d runs on the local machine,
while the other phases runs on the machine that is being build.

If you use multiple elements and they all have the `install.d` phase directory
defined, then all the scripts found in each element's `install.d` directory
run. The order in which they run is determined by sorting the scripts based on
the name of the script. This is the rational to why the scripts you find in all
example elements have numbers in front of the name. For example if `element1`
has a script named `22-do-this-thing`, then it will run before `element2`'s
script named `23-do-the-other-thing`.

All elements found in
https://github.com/openstack/diskimage-builder/tree/master/diskimage_builder/elements
ship with diskimage-builder and can be used simply by specifying the name.

## Creating new elements

Documentation for developers wanting to create their own custom elements can be
found on the OpenStack docs for diskimage-builder:
https://docs.openstack.org/diskimage-builder/latest/developer/developing_elements.html

One way to start working on a new element is to template it after existing
[elements packaged with diskimage-builder
itself](https://github.com/openstack/diskimage-builder/tree/master/diskimage_builder/elements).

The name of the top directory of the element is the name of the element.
Create directories for each
[phase](https://docs.openstack.org/diskimage-builder/latest/developer/developing_elements.html#phase-subdirectories)
you want to execute scripts during.
Below are some extra notes about the phases we are currently using in this element. They are listed in the order in which they execute. Exhaustive list of [phases can be found in the OpenStack docs](https://docs.openstack.org/diskimage-builder/latest/developer/developing_elements.html#phase-subdirectories).

## Interacting with the elements

Customizing the image to your needs is done with the help of variables. All the variables that are required for the elements
are exported as environment variables before building the image using the diskimage builder. 

for example: The bootloader element that steps up grub on the boot partition that allows setting up boot variables. This can be achieved by 
exporting the DIB_BOOTLOADER_DEFAULT_CMDLINE with the key-value boot variable pairs.   

## Phases

### extra-data.d

This phase is when we can copy items from the local filesystem into the image
filesystem.  For example we copy the jenkins sshkey into the image in
[`elements/jenkins-slave/extra-data.d/20-jenkins-slave`](https://github.com/quipucords/ci/blob/ed1d9d040bcfc6bca9543fd1b528e036983772ed/ansible/roles/nodepool/files/elements/jenkins-slave/extra-data.d/20-jenkins-public-ssh-key#L7)

### install.d

This phase runs scripts after the OS is provisioned For example, we create the
jenkins user in 
[`elements/jenkins-slave/install.d/20-jenkins-slave`](https://github.com/quipucords/ci/blob/ed1d9d040bcfc6bca9543fd1b528e036983772ed/ansible/roles/nodepool/files/elements/jenkins-slave/install.d/20-jenkins-slave#L7).

### How to define dependencies on other elements for an element

Place a file named `element-deps` in base directory of the element. It is
newline seperated list where you name the elements you depend on.  You can
specify custom elements or built in elements from disk image builder. Custom
elements can be used by diskimage-builder if they are located in a directory
pointed to by the environment variable `$ELEMENTS_PATH`.

> Note: It remains to be seen if there is precedence if there is namespace clash.

### How to install packages after the OS provisioned:

If you depend on the use the package-installs element so you don't have to
reinvent lots of logic about differnt package managers. Then you can create
`package-installs.yaml` in the base directory of your element. It can be as
simple as our current
[`package-installs.yaml`](https://github.com/quipucords/ci/blob/ed1d9d040bcfc6bca9543fd1b528e036983772ed/ansible/roles/nodepool/files/elements/jenkins-slave/package-installs.yaml#L1)
or more complicated, including some logic after the name of the package if the
package name differs based on the OS. Example of this is shown in this README:
https://github.com/openstack/diskimage-builder/tree/master/diskimage_builder/elements/package-installs#package-installs.


## Using elements

You can use elements either by depending on them in the `element-deps` file or
by including them in arguments to `diskimage-builder-create`.  Before you use
an element, you should look through it to see if the element needs any
environment variables!
There is no method to pass command line arguments to the elements at the invocation of diskimage-builder-create to the elements, so all configuration is done by environment variables.


### Special variables

All variables that start with $DIB_* are special environment variables used by
the diskimage-builder built in elements.

## Building Our Images

We use the following elements for fedora images:

 element        | description
 ---------------| ---------------------------        
 fedora-minimal | DIB built in. says we want a fedora machine. Needs DIB_RELEASE to decide what version to use
 vm             | DIB built in. Sets up a partitioned disk (rather than building just one filesystem with no partition table).
 simple-init    | DIB built in. Network and system configuration that cannot be done until boot time
 growroot       | DIB built in. Grow the root partition on first boot.
 jenkins-slave  | Custom defined element found in this repo.

We use the following elements for CentOS images:

 element        | description
 ---------------| ---------------------------   
 centos7        | DIB built in. Needs DIB_RELEASE to decide what version to use
 vm             | DIB built in. Sets up a partitioned disk (rather than building just one filesystem with no partition table).
 simple-init    | DIB built in. Network and system configuration that cannot be done until boot time
 growroot       | DIB built in. Grow the root partition on first boot.
 epel           | DIB built in.
 jenkins-slave  | Custom defined element found in this repo.

We use the following elements for Rhel images:

 element        | description
 ---------------| ---------------------------   
 rhel7          | DIB built in. Provides the base image for building rhel images. Needs DIB_LOCAL_IMAGE which points to the base image location(qcow2 images)
 rhel-common    | DIB built in. Takes case of rhel subscription manager.Needs REG_USER,REG_PASSWORD,REG_POOL_ID for subscription.
 vm             | DIB built in. Sets up a partitioned disk (rather than building just one filesystem with no partition table).
 simple-init    | DIB built in. Network and system configuration that cannot be done until boot time
 growroot       | DIB built in. Grow the root partition on first boot.
 jenkins-slave  | Custom defined element found in this repo.
 bootloader     | DIB built in. Installs grub2 on boot partition. Used for setting boot parameters. Needs DIB_BOOTLOADER_DEFAULT_CMDLINE for boot variables
 epel           | DIB built in. For Extra packages

The script that is currently used for building images can be found at scripts/builder.sh. 

### Setting up the image to be accessed via Jenkins

An user jenkins with password jenkins is configured as a sudo user in the image, during the install.d phase of the element. This makes the image instances accesible
with usernames and password.

For jenkins to access this image's instance, ssh public keys of jenkins needs to be passed to the image. This could be specified in JENKINS_PUBLIC_SSH_KEY_PATH.
The JENKINS_PUBLIC_SSH_KEY_PATH should point to id_rsa.pub file containing jenkins public keys, which should be present in the host machine.

## Uploading to Openstack

1) Log into our shared OpenStack instance.
2) Under the "compute" tab, navigate to "Images"
3) There is a button near the search bar with a plus sign labeled "+ create image"
4) Name the image something reasonable. Confer with other team members.
   This is what jenkins will know the image by.

## Configuring Jenkins to use your image

Under `Manage Jenkins> Configure System` Find the `Cloud > Cloud (OpenStack)`
section.  Create a new template by clicking `Add template`.

The `label` is important -- it is what the jenkins jobs will specify to Jenkins
to tell it what node to use.  Under `Advanced` options, change the `Boot
Source` to `Image`. A new drop down will appear and will populate with names of
images available on the OpenStack instance that the cloud is configured to talk
to. Select the name of the image you uploaded.


## Alternate Workflow

If you cannot obtain the base image you need to use diskimage-builder, there is
a way to customize images based off of images allready present on OpenStack.

## To create image from snapshot on Openstack

Under `Compute>Instances` create instance with `Launch Instance` Specify you
public key so you will be able to ssh into the machine.  Then associate a
floating IP to the image and log into it and do any necessary set up.

After done, shut down the instance. Look under `Compute>Volumes` and see
what volume is associated with it. May need to make a note of this as it as a
long UUID like name.

Then you can go back to the instance and delete it. This won't delete the
volume, which is what we want.  Then under `Compute>Volumes` next to volume,
click down arrow and click `Upload to Image`. Name it something sensible, as
this is what Jenkins will know it by.  Choose the QCOW2 file format.

Configuring Jenkins to use this image is the same as images created with
 `diskimage-builder`.