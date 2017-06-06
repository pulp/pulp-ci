# coding=utf-8
from __future__ import print_function

import logging
import os
import pprint
import sys
import time

import pip
import requests

JENKINS_URL = os.environ.get('REMOTE_JENKINS_URL')
JENKINS_API_TOKEN = os.environ.get('REMOTE_JENKINS_API_TOKEN')
JENKINS_USERNAME = os.environ.get('REMOTE_JENKINS_USERNAME')
JOB_NAME = '{job_name}'

logging.captureWarnings(True)
print('Queuing job {{}}...'.format(JOB_NAME))
queue_url = requests.post(
    JENKINS_URL + '/job/{{}}/buildWithParameters'
    .format(JOB_NAME),
    auth=(JENKINS_USERNAME, JENKINS_API_TOKEN),
    data={{
        {job_parameters}
    }},
    verify=False
).headers['Location']

time.sleep(5)
queue = requests.get(queue_url + '/api/json', verify=False).json()
while not queue.get('executable'):
    time.sleep(1)
    queue = requests.get(queue_url + '/api/json', verify=False).json()
print('Job #{{0}} ({{1}}) was triggered...'.format(
    queue['executable']['number'],
    queue['executable']['url']
))

result = ''
while not result:
    time.sleep(30)
    response = requests.get(
        JENKINS_URL + '/job/{{0}}/{{1}}/api/json'
        .format(
            JOB_NAME,
            queue['executable']['number']
        ),
        verify=False
    ).json()
    result = response.get('result') or ''
    if result.lower() == 'failure':
        print(
            'Triggered job failed. Check its console output '
            'for more information: {{}}console'
            .format(queue['executable']['url'])
        )
        sys.exit(1)
    elif result.lower() == 'success':
        print('Triggered job succeeded.')
    elif result:
        print(
            'Triggered job completed with result: {{}}'
            .format(result)
        )
        sys.exit(1)
