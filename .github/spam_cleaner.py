import datetime
import itertools
import json
import os
import re

import pandas as pd
import pickle

from collections import defaultdict
from urllib.parse import urlparse

from redminelib import Redmine
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import NoSuchElementException

from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow,Flow
from google.auth.transport.requests import Request

from .send_email import get_email_server

REDMINE_PAGE = 'https://pulp.plan.io'

REDMINE_LOGIN_PAGE = 'https://pulp.plan.io/login'
REDMINE_LOGIN_FORM_USERNAME = os.getenv('REDMINE_USERNAME')
REDMINE_LOGIN_FORM_PASSWORD = os.getenv('REDMINE_PASSWORD')

REDMINE_USERS_PAGE = 'https://pulp.plan.io/users'

SPREADSHEET_ID = os.getenv('SPREADSHEET_ID')
BASE_SHEET_RANGE = 'A1:AA1000'
VERIFIED_USERS_SHEET_RANGE = "verified!A1:AA1000"

CHROME_DRIVER_PATH = './chromedriver'

# https://stackoverflow.com/a/48689681
URL_REGEX = r'((http|https)\:\/\/)[a-zA-Z0-9\.\/\?\:@\-_=#]+\.([a-zA-Z]){2,6}([a-zA-Z0-9\.\&\/\?\:@\-_=#])*'

TRUSTED_EMAIL_ADDRESS_DOMAINS = ['redhat.com', 'atix.de']
TRUSTED_LINKS_DOMAINS = [
    'github.com',
    'pulp.plan.io',
    'travis-ci.com',
    'pulpproject.org',
    'docs.pulpproject.org',
    'pulp-container.readthedocs.io',
    'pulp-rpm.readthedocs.io',
    'pulp-file.readthedocs.io',
    'repos.fedorapeople.org'
]

REMOVAL_TIME_DELTA = datetime.timedelta(days=2)
ISSUES_TO_CHECK_TIME_DELTA = datetime.timedelta(days=1)


def contains_unknown_outbound_links(text):
    for link in re.finditer(URL_REGEX, text):
        if urlparse(link.group()).netloc not in TRUSTED_LINKS_DOMAINS:
            return True
    return False


def fetch_users(issues, journals):
    users = defaultdict(lambda: defaultdict(list))

    for issue in issues:
        user_id = f'{issue.author.name}/{issue.author.id}'
        users[user_id]['content'].append({'issue': issue.url})

    for issue, journal in journals:
        user_id = f'{journal.user.name}/{journal.user.id}'
        users[user_id]['content'].append({'journal': [issue.url, journal.id]})

    return users


def fetch_email_addresses(users):
    users_with_mails = {}

    for user in users.keys():
        user_name, id = user.split('/')
        if user_name != 'Anonymous':
            driver.get(f'{REDMINE_USERS_PAGE}/{id}/edit')

            email = driver.find_element_by_xpath('//*[@id="user_mail"]').get_attribute('value')
            _, domain = email.split('@', 1)
            if domain not in TRUSTED_EMAIL_ADDRESS_DOMAINS:
                users_with_mails[user] = users[user]
                users_with_mails[user]['email'] = email
        else:
            users_with_mails[user] = users[user]
            users_with_mails[user]['email'] = 'nomail'

    return users_with_mails


def remove_duplicates(data_list):
    without_duplicates = []
    for elem in data_list:
        if elem not in without_duplicates:
            without_duplicates.append(elem)
    return without_duplicates


def send_html_email(mail_to, text, server):
    """Nagger email to each owner.
    Arguments:
        mail_to {[list]} -- [email1, email2,...]
        text {str} -- plain text message
        server {SMTP} -- SMTP server instance
    """
    if not isinstance(mail_to, list):
        mail_to = [mail_to]

    mail_from = 'no-reply@redhat.com'
    mail_to_string = ', '.join(mail_to)
    msg = MIMEMultipart('alternative')
    subject = settings.get(
        "EMAIL.subject", "[Pulp] User verification"
    )
    msg["Subject"] = f"{subject} - {datetime.now().date().isoformat()}"
    msg["From"] = mail_from
    msg["To"] = mail_to_string

    body_text = MIMEText(text, "plain")

    msg.attach(body_text)
    return server.sendmail(mail_from, mail_to, msg.as_string())


redmine = Redmine(REDMINE_PAGE)

current_time = datetime.datetime.now()
datetime_after_threshold = current_time - ISSUES_TO_CHECK_TIME_DELTA
current_timestamp = datetime.datetime.timestamp(current_time)

recently_updated_issues = []
# iterate over all opened and closed issues sorted by the field 'updated_on' (2.20m)
for issue in redmine.issue.filter(status_id='*', sort='updated_on:desc', project_id='pulp_docker'):
    if issue.updated_on > datetime_after_threshold:
        recently_updated_issues.append(issue)
    else:
        # issues are ordered by the field 'updated_on'; therefore, we do not
        # have to browse through the rest of the issues
        break

issues_with_links = []
journals_with_links = []
# fetch recent issues/comments with outbound links
for issue in recently_updated_issues:
    if issue.created_on > datetime_after_threshold \
            and contains_unknown_outbound_links(issue.description):
        issues_with_links.append(issue)

    for journal in issue.journals:
        if journal.created_on > datetime_after_threshold \
                and hasattr(journal, 'notes') and contains_unknown_outbound_links(journal.notes):
            journals_with_links.append((issue, journal))

fetched_users = fetch_users(issues_with_links, journals_with_links)

# start a Chrome instance
options = Options()
options.add_argument('--headless')
options.add_argument('--no-sandbox')
options.add_argument('--disable-gpu')
driver = webdriver.Chrome(CHROME_DRIVER_PATH, options=options)

# log in
driver.get(REDMINE_LOGIN_PAGE)
username = driver.find_element_by_id('username')
password = driver.find_element_by_id('password')
username.send_keys(REDMINE_LOGIN_FORM_USERNAME)
password.send_keys(REDMINE_LOGIN_FORM_PASSWORD)
driver.find_element_by_id('login-submit').click()

fetched_issues_data = fetch_email_addresses(fetched_users)

# init the service required to access the spreadsheet
creds = None
if os.path.exists('token.pickle'):
    with open('token.pickle', 'rb') as token:
        creds = pickle.load(token)
if not creds or not creds.valid:
    if creds and creds.expired and creds.refresh_token:
        creds.refresh(Request())
    else:
        flow = InstalledAppFlow.from_client_secrets_file(
            'credentials.json', SCOPES) # here enter the name of your downloaded JSON file
        creds = flow.run_local_server(port=0)
    with open('token.pickle', 'wb') as token:
        pickle.dump(creds, token)

service = build('sheets', 'v4', credentials=creds)
sheet = service.spreadsheets()

# filter out verified users
result_input = sheet.values().get(
    spreadsheetId=SPREADSHEET_ID,
    range=VERIFIED_USERS_SHEET_RANGE
).execute()
values_input = result_input.get('values', [])
df = pd.DataFrame(values_input[1:], columns=values_input[0])

verified_users_data = [(user, email) for user, email in df.to_dict('split')['data']]

users_to_delete = []
for user, data in fetched_issues_data.items():
    if (user, data['email']) in verified_users_data:
        users_to_delete.append(user)

for user in users_to_delete:
    del fetched_issues_data[user]

# update already existing users' data and append new users' data
result_input = sheet.values().get(
    spreadsheetId=SPREADSHEET_ID,
    range=BASE_SHEET_RANGE
).execute()
values_input = result_input.get('values', [])
df = pd.DataFrame(values_input[1:], columns=values_input[0])
users_to_verify_data = df.to_dict('split')['data']

rows_to_update = []
rows_to_append = []
users_to_notify = []
for fetched_user, fetched_data in fetched_issues_data.items():
    updated = False
    # a first data row starts at the position 2 because of the heading
    last_row_number = 2
    for user, email, data, timestamp in users_to_verify_data:
        if (user, email) == (fetched_user, fetched_data['email']):
            data_list = json.loads(data)
            data_list.extend(fetched_data['content'])
            data_list_without_duplicates = remove_duplicates(data_list)
            dumped_data = json.dumps(data_list_without_duplicates)
            rows_to_update.append((last_row_number, dumped_data))
            updated = True
            break
        last_row_number += 1

    if not updated:
        dumped_data = json.dumps(fetched_data['content'])
        rows_to_append.append([fetched_user, fetched_data['email'], dumped_data, current_timestamp])
        users_to_notify.append(fetched_data['email'])


# prepare body for a batch update
value_ranges = []
for row_number, dumped_data in rows_to_update:
    value_ranges.append({
        'majorDimension': 'ROWS',
        'range': f'C{row_number}',
        'values': [[dumped_data]]
    })
if rows_to_append:
    next_empty_row_number = len(users_to_verify_data) + 2
    value_ranges.append({
        'majorDimension': 'ROWS',
        'range': f'A{next_empty_row_number}:AA1000',
        'values': rows_to_append
    })

    send_html_email(
        users_to_notify,
        'Dear user,\n we noticed your recent activity at pulp.plan.io. In order to verify your '
        'account, please, send an e-mail to pulp-infra@redhat.com with the subject "[Verification] '
        '{your username}" and the body containing (again) your username and reference to the '
        'recently added content. If we do not receive such an e-mail from you within 48 hours, '
        'your contributions will be automatically removed.\n Thank you for your understanding!',
        get_email_server()
    )

body = {'value_input_option': 'RAW', 'data': value_ranges}
sheet.values().batchUpdate(spreadsheetId=SPREADSHEET_ID, body=body).execute()

# read data after update again
result_input = sheet.values().get(
    spreadsheetId=SPREADSHEET_ID,
    range=BASE_SHEET_RANGE
).execute()
values_input = result_input.get('values', [])
df = pd.DataFrame(values_input[1:], columns=values_input[0])
users_to_verify_data = df.to_dict('split')['data']

rows_to_delete = []
# rows' indexes are zero-based in this scenario (0 is occupied by the header)
row_index = 1
# delete content when a user did not respond within a specified time
for user, _, data, timestamp in users_to_verify_data:
    timestamp_delta = current_time - datetime.datetime.fromtimestamp(int(timestamp))
    if timestamp_delta > REMOVAL_TIME_DELTA:
        data_list = json.loads(data)
        for content_data in data_list:
            if 'issue' in content_data:
                # delete an issue
                driver.get(content_data['issue'])
                try:
                    driver.find_element_by_xpath('//*[@id="content"]/div[2]/a[5]').click()
                except NoSuchElementException:
                    pass
                else:
                    driver.switch_to.alert.accept()
            else:
                # delete a note
                issue_url = content_data['journal'][0]
                journal_id = content_data['journal'][1]
                driver.get(issue_url)
                try:
                    driver.find_element_by_xpath(f'//*[@id="journal-{journal_id}-notes"]/div/a[3]').click()
                except NoSuchElementException:
                    pass
                else:
                    driver.switch_to.alert.accept()

        # remove a user
        username, id = user.split('/')
        if username != 'Anonymous':
            driver.get(f'{REDMINE_USERS_PAGE}/{id}/edit')
            try:
                driver.find_element_by_xpath('//*[@id="content"]/div[2]/a[4]').click()
            except NoSuchElementException:
                pass
            else:
                driver.switch_to.alert.accept()

        rows_to_delete.append(row_index)

    row_index += 1

# delete users' data who were removed during runtime
if rows_to_delete:
    requests = []
    for row_index in rows_to_delete:
        requests.append({
            "deleteDimension": {
                "range": {
                    "sheetId": 0,
                    "dimension": "ROWS",
                    "startIndex": row_index,
                    "endIndex": row_index + 1
                }
            }
        })

    # delete rows in the reversed order because they are shifted after each deletion
    requests.reverse()
    sheet.batchUpdate(spreadsheetId=SPREADSHEET_ID, body={'requests': requests}).execute()

driver.close()
