#!/usr/bin/env bash
HOSTNAME="$1"
DOCKER="$(grep docker 2>/dev/null <<< ${HOSTNAME})"

echo "Disable selinux"
sudo setenforce 0

# Fail immediately on error
set -ex

source bootstrap.sh

echo "Performaing a general update"
sudo "${PKG_MGR}" update -y

echo "Installing base packages"
sudo "${PKG_MGR}" install -y gcc git python-devel python-pip redhat-lsb-core wget

echo "OS specific setup"
if [ "${DISTRIBUTION}" == "redhat" ] && [ "${DISTRIBUTION_MAJOR_VERSION}" == "5" ]; then
    sudo "${PKG_MGR}" install -y yum-security
    curl -O https://dl.fedoraproject.org/pub/epel/epel-release-latest-5.noarch.rpm
    sudo rpm -ivh epel-release-latest-5.noarch.rpm
    cat > mrg.repo <<EOF
[mrg-el5]
name=mrg-el5
baseurl=http://download.devel.redhat.com/cds/prod/content/dist/rhel/server/5/5Server/x86_64/mrg-m/2/os/
enabled=1
gpgcheck=0
EOF
    sudo mv mrg.repo /etc/yum.repos.d/
elif  [ "${DISTRIBUTION}" == "redhat" ] && [ "${DISTRIBUTION_MAJOR_VERSION}" == "6" ]; then
    sudo rpm -ivh https://dl.fedoraproject.org/pub/epel/epel-release-latest-6.noarch.rpm
    sudo su -c "curl https://copr.fedorainfracloud.org/coprs/g/qpid/qpid/repo/epel-6/irina-qpid-epel-6.repo > /etc/yum.repos.d/copr-qpid.repo"
elif  [ "${DISTRIBUTION}" == "redhat" ] && [ "${DISTRIBUTION_MAJOR_VERSION}" == "7" ]; then
    sudo rpm -ivh https://dl.fedoraproject.org/pub/epel/epel-release-latest-7.noarch.rpm
    # https://bugzilla.redhat.com/show_bug.cgi?id=1173993 is similar to what we've been seeing
    # to break the rhel7 image booting. This fixes it, but it's not clear why.
    sudo sed -i '/sixteenbit=/d' /etc/grub.d/10_linux
    # after fixing that ^, the rhel7-vanilla images occasional kernel panic starting the apic timer
    # simple solution: don't use apic?
    sudo sed -i 's/GRUB_CMDLINE_LINUX="/GRUB_CMDLINE_LINUX="apic=verbose /' /etc/default/grub
    sudo grub2-mkconfig -o /boot/grub2/grub.cfg
elif  [ "${DISTRIBUTION}" == "fedora" ]; then
    sudo sed -i 's/clean_requirements_on_remove=true/clean_requirements_on_remove=false/g' /etc/dnf/dnf.conf
    # "which" isn't installed in fedora 22+ by default?
    sudo "${PKG_MGR}" install -y python2 python-dnf which
fi

echo "Disable ttysudo requirement"
sudo sed -i 's|Defaults[ ]*requiretty|#Defaults    requiretty|g' /etc/sudoers

if [ "${DOCKER}" ]; then
    sudo "${PKG_MGR}" install -y docker
    sudo systemctl enable docker

    echo "Allowing jenkins user access to docker"
    sudo groupadd docker
    sudo gpasswd -a jenkins docker
    # add -G docker to docker's OPTIONS in /etc/sysconfig/docker
    sudo sed -i "s/^\(OPTIONS=.*\)'/\1 -G docker'/" /etc/sysconfig/docker
fi
