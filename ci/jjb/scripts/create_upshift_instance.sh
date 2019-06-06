#!/usr/bin/env bash
sudo pip install -U pip virtualenv
virtualenv pulp-jenkins
source pulp-jenkins/bin/activate
pip install openstacksdk==0.31.1

echo $PWD
ls
python ci/jjb/scripts/create_upshift_instance.py

# wait for ssh connection
sleep 60
