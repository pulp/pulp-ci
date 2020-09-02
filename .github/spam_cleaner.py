import binascii
import datetime
import json
import logging
import logging.config
import os
import pickle
import re
import smtplib
import tldextract

from collections import defaultdict
from urllib.parse import urlparse

import pandas as pd

from redminelib import Redmine
from selenium import webdriver
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver import ActionChains
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions

from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request

REDMINE_PAGE = "https://pulp.plan.io"

REDMINE_LOGIN_PAGE = "https://pulp.plan.io/login"
REDMINE_LOGIN_FORM_USERNAME = "pulpbot"
REDMINE_LOGIN_FORM_PASSWORD = os.getenv("REDMINE_PASSWORD")

REDMINE_USERS_PAGE = "https://pulp.plan.io/users"

GOOGLE_CLIENT_CONFIG = os.getenv("GOOGLE_CLIENT_CONFIG")
SPREADSHEET_ID = os.getenv("SPREADSHEET_ID")
USERS_TO_VERIFY_SHEET_RANGE = "A1:AA1000"
VERIFIED_USERS_SHEET_RANGE = "verified!A1:AA1000"
SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]
MAX_NUMBER_OF_UPDATES = 10

EMAIL_USERNAME = "pulpbotnoreply@gmail.com"
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")

# https://github.com/actions/virtual-environments/pull/269
CHROME_DRIVER_PATH = os.path.join(os.getenv("CHROMEWEBDRIVER"), "chromedriver")
SECONDS_TO_WAIT = 2

# https://stackoverflow.com/a/48689681
URL_REGEX = (
    r"((http|https)\:\/\/)[a-zA-Z0-9\.\/\?\:@\-_=#]+"
    r"\.([a-zA-Z]){2,6}([a-zA-Z0-9\.\&\/\?\:@\-_=#])*"
)

TRUSTED_EMAIL_ADDRESS_DOMAINS = ["redhat.com", "atix.de"]
TRUSTED_LINKS_DOMAINS = [
    "centos.org",
    "debian.org",
    "example.com",
    "fedorapeople.org",
    "git.io",
    "github.com",
    "microsoft.com",
    "pulpproject.org",
    "plan.io",
    "puppet.com",
    "puppetlabs.com",
    "pypi.org",
    "redhat.com",
    "readthedocs.io",
    "travis-ci.com",
    "theforeman.org",
    "ubuntu.com",
]

# if a user does not respond within the given time, he/she will be removed
REMOVAL_TIME_DELTA = datetime.timedelta(days=7)

# check for issues/comments that were created 7 days ago
ISSUES_TO_CHECK_TIME_DELTA = datetime.timedelta(days=7)

EMAIL_SUBJECT = "[Pulp] [Plan.io] User Verification"

EMAIL_MESSAGE = (
    "Dear {user},\n\nWe have recorded your activity at pulp.plan.io. In order to verify your "
    "account, please, send an e-mail to pulp-infra@redhat.com with the subject '[Verification] "
    "[your username]' and the body containing (again) your username and reference to "
    "the recently added content. If we do not receive such an e-mail from you within "
    + str(REMOVAL_TIME_DELTA.days) + " days, your contributions will be automatically "
    "removed.\n\nLearn more at https://www.redhat.com/archives/pulp-list/2020-August/msg00011.html."
    "\n\nThank you for your understanding!"
)

ISSUE_DELETE_BUTTON_XPATH = '//*[@id="content"]/div[2]/a[5]'
COMMENT_DELETE_BUTTON_XPATH = '//*[@id="journal-{journal_id}-notes"]/div/a[3]'
USER_LOCK_BUTTON_XPATH = '//*[@id="content"]/div[2]/a[3]'

logging.config.dictConfig({
    'version': 1,
    'disable_existing_loggers': True,
})
logging.basicConfig(level=logging.INFO)

logger = logging.getLogger('spam_cleaner')
logger.setLevel(logging.INFO)


def run():
    current_time = datetime.datetime.now()

    logger.info("Initializing the chrome driver...")
    driver = init_chrome_driver()
    log_in_to_redmine(driver)
    logger.info("The chrome driver was initialized.")

    logger.info("Fetching recently updated issues...")
    fetched_issues_data = fetch_issue_data(driver, current_time)
    logger.info("All issues were fetched.")

    logger.info("Initializing the spreadsheet service...")
    sheet = init_spreadsheet_service()
    logger.info("The service was properly initialized.")

    logger.info("Filtering out verified content...")
    filter_out_verified_content(sheet, fetched_issues_data)
    logger.info("Updating the spreadsheet...")
    update_sheet_and_send_notifications(sheet, fetched_issues_data, current_time)
    logger.info("Deleting unverified content...")
    delete_unverified_content(sheet, driver, current_time)

    logger.info("Closing the chrome driver...")
    driver.close()


def init_chrome_driver():
    """Initialize a webdriver instance for Chrome."""
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-gpu")
    return webdriver.Chrome(CHROME_DRIVER_PATH, options=options)


def log_in_to_redmine(driver):
    """Log in to REDMINE like an ordinary user."""
    driver.get(REDMINE_LOGIN_PAGE)
    username = driver.find_element_by_id("username")
    password = driver.find_element_by_id("password")
    username.send_keys(REDMINE_LOGIN_FORM_USERNAME)
    password.send_keys(REDMINE_LOGIN_FORM_PASSWORD)
    driver.find_element_by_id("login-submit").click()


def fetch_issue_data(driver, current_time):
    """Fetch recently updated issues with authors and associated e-mail addresses."""
    datetime_after_threshold = current_time - ISSUES_TO_CHECK_TIME_DELTA
    recently_updated_issues = fetch_recently_updated_issues(datetime_after_threshold)

    issues_with_links, journals_with_links = extract_issues_and_journals(
        recently_updated_issues, datetime_after_threshold
    )

    fetched_users = fetch_users(driver, issues_with_links, journals_with_links)
    return fetched_users


def fetch_recently_updated_issues(datetime_after_threshold):
    """Use REDMINE API to fetch recently updated issues."""
    redmine = Redmine(REDMINE_PAGE)

    recently_updated_issues = []

    # iterate over all opened and closed issues sorted by the field 'updated_on' (takes about 2.20m)
    for issue in redmine.issue.filter(status_id="*", sort="updated_on:desc"):
        if issue.updated_on > datetime_after_threshold:
            recently_updated_issues.append(issue)
        else:
            # issues are ordered by the field 'updated_on'; therefore, we do not
            # have to browse through the rest of the issues
            break

    return recently_updated_issues


def extract_issues_and_journals(recently_updated_issues, datetime_after_threshold):
    """Determine whether an issue itself was updated or a new journal was added."""
    issues_with_links = []
    journals_with_links = []
    for issue in recently_updated_issues:
        if issue.created_on > datetime_after_threshold \
                and contains_unknown_outbound_links(issue.description):
            issues_with_links.append(issue)

        for journal in issue.journals:
            if journal.created_on > datetime_after_threshold and hasattr(journal, "notes") \
                    and contains_unknown_outbound_links(journal.notes):
                journals_with_links.append((issue, journal))

    return issues_with_links, journals_with_links


def contains_unknown_outbound_links(text):
    """Check for untrusted outbound links."""
    for link in re.finditer(URL_REGEX, text):
        result = tldextract.extract(link.group())
        domain = f"{result.domain}.{result.suffix}"
        if domain not in TRUSTED_LINKS_DOMAINS:
            return True
    return False


def fetch_users(driver, issues, journals):
    """Associate users to content and return a dictionary that contains the associations."""
    users = defaultdict(lambda: defaultdict(list))

    for issue in issues:
        user_id = f"{issue.author.name}/{issue.author.id}"
        # store a URL of the issue
        users[user_id]["content"].append({"issue": issue.url})

    for issue, journal in journals:
        user_id = f"{journal.user.name}/{journal.user.id}"
        # store a URL of the associated issue and a journal ID
        users[user_id]["content"].append({"journal": [issue.url, journal.id]})

    users = assign_email_addresses(driver, users)

    return users


def assign_email_addresses(driver, users):
    """Retrieve e-mail addresses for all users and return a new dictionary of users."""
    users_with_assigned_email_addresses = {}

    for user in users.keys():
        user_name, user_id = user.split("/")
        if user_name == "Anonymous":
            users[user]["email"] = "Anonymous"
            users_with_assigned_email_addresses[user] = users[user]
        else:
            driver.get(f"{REDMINE_USERS_PAGE}/{user_id}/edit")
            email = driver.find_element_by_xpath(
                '//*[@id="user_mail"]'
            ).get_attribute("value").lower()
            _, domain = email.split("@", 1)
            if domain not in TRUSTED_EMAIL_ADDRESS_DOMAINS:
                # this filters out all e-mail addresses that are trusted
                users[user]["email"] = email
                users_with_assigned_email_addresses[user] = users[user]

    return users_with_assigned_email_addresses


def init_spreadsheet_service():
    """Initialize the service used to work with Google Sheets."""
    token = binascii.unhexlify(GOOGLE_CLIENT_CONFIG.encode())
    creds = pickle.loads(token)
    if creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
    else:
        raise RuntimeError("Credentials were not loaded.")

    with open("token.pickle", "wb") as token:
        pickle.dump(creds, token)

    service = build("sheets", "v4", credentials=creds, cache_discovery=False)
    return service.spreadsheets()


def filter_out_verified_content(sheet, fetched_issues_data):
    """Filter out users and the corresponding content if it has been already verified."""
    data = read_sheet(sheet, VERIFIED_USERS_SHEET_RANGE)
    verified_users_data = [(user, email) for user, email in data]
    delete_verified_users(fetched_issues_data, verified_users_data)


def read_sheet(sheet, sheet_range):
    """Read a sheet specified by the sheet_range."""
    result_input = sheet.values().get(spreadsheetId=SPREADSHEET_ID, range=sheet_range).execute()
    values_input = result_input.get("values", [])
    df = pd.DataFrame(values_input[1:], columns=values_input[0])
    return df.to_dict("split")["data"]


def delete_verified_users(fetched_issues_data, verified_users_data):
    """Delete all users who were verified from the passed dictionary."""
    users_to_delete = []
    for user, data in fetched_issues_data.items():
        if (user, data["email"]) in verified_users_data:
            users_to_delete.append(user)

    for user in users_to_delete:
        del fetched_issues_data[user]


def update_sheet_and_send_notifications(sheet, fetched_issues_data, current_time):
    """Update the sheet with newly added content, and newly added users and then notify them."""
    users_to_verify_data = read_sheet(sheet, USERS_TO_VERIFY_SHEET_RANGE)
    current_timestamp = datetime.datetime.timestamp(current_time)

    rows_to_update, rows_to_append = separate_users_to_update_and_append(
        fetched_issues_data, users_to_verify_data, current_timestamp
    )
    request_data = prepare_update_request(
        rows_to_update, rows_to_append, users_to_verify_data
    )
    send_batch_update_request(sheet, request_data)

    users_to_notify = [
        (user, email) for user, email, _, _ in rows_to_append if email != "Anonymous"
    ]
    send_notifications(users_to_notify)


def separate_users_to_update_and_append(
    fetched_issues_data, users_to_verify_data, current_timestamp
):
    """Prepare updated sheet's rows for existing users with recently added content and new users."""
    rows_to_update = []
    rows_to_append = []

    # update already existing users' data and append new users' data
    for fetched_user, fetched_data in fetched_issues_data.items():
        updated = False
        # a first data row starts at the position 2 because of the heading
        last_row_number = 2
        for user, email, data, _ in users_to_verify_data:
            if (user, email) == (fetched_user, fetched_data["email"]):
                data_list = json.loads(data)
                data_list.extend(fetched_data["content"])
                data_list_without_duplicates = remove_duplicates(data_list)
                dumped_data = json.dumps(data_list_without_duplicates)
                rows_to_update.append((last_row_number, dumped_data))
                updated = True
                break
            last_row_number += 1

        if not updated:
            dumped_data = json.dumps(fetched_data["content"])
            rows_to_append.append(
                [fetched_user, fetched_data["email"], dumped_data, current_timestamp]
            )

    return rows_to_update, rows_to_append


def remove_duplicates(data_list):
    """Remove duplicates from the passed data_list."""
    without_duplicates = []
    for elem in data_list:
        if elem not in without_duplicates:
            without_duplicates.append(elem)
    return without_duplicates


def prepare_update_request(rows_to_update, rows_to_append, users_to_verify_data):
    """Create the request's body used for batch update."""
    value_ranges = []

    for row_number, dumped_data in rows_to_update:
        # there is going to be updated just a single column within a specific row range
        value_ranges.append(
            {
                "majorDimension": "ROWS",
                "range": f"C{row_number}",
                "values": [[dumped_data]],
            }
        )
    if rows_to_append:
        next_empty_row_number = len(users_to_verify_data) + 2
        value_ranges.append(
            {
                "majorDimension": "ROWS",
                "range": f"A{next_empty_row_number}:AA1000",
                "values": rows_to_append,
            }
        )

    return value_ranges


def send_batch_update_request(sheet, request_data):
    """Send a batch update request."""
    body = {"value_input_option": "RAW", "data": request_data}
    sheet.values().batchUpdate(spreadsheetId=SPREADSHEET_ID, body=body).execute()


def send_notifications(users_to_notify):
    """Send e-mail to new users who recently created issues/journals and are not yet verified."""
    if not users_to_notify:
        return

    server = smtplib.SMTP_SSL("smtp.gmail.com", 465)
    server.login(EMAIL_USERNAME, EMAIL_PASSWORD)

    for user, email in users_to_notify:
        message = "Subject: " + EMAIL_SUBJECT + "\n\n" + EMAIL_MESSAGE.format(user=user)
        server.sendmail(EMAIL_USERNAME, email, message)


def delete_unverified_content(sheet, driver, current_time):
    """Delete all unverified content which was not checked within a defined time."""
    users_to_verify_data = read_sheet(sheet, USERS_TO_VERIFY_SHEET_RANGE)
    rows_to_delete_from_sheet = delete_users_content(
        driver, users_to_verify_data, current_time
    )
    delete_users_data_from_sheet(rows_to_delete_from_sheet, sheet)


def delete_users_content(driver, users_to_verify_data, current_time):
    """Delete issues, journals and users who are considered to be the spam."""
    rows_to_delete = []
    # rows' indexes are zero-based in this scenario (0 is occupied by the header)
    row_index = 1

    # delete content when a user did not respond within a specified time
    for user, _, data, timestamp in users_to_verify_data:
        timestamp_delta = current_time - datetime.datetime.fromtimestamp(int(timestamp))
        if timestamp_delta > REMOVAL_TIME_DELTA:
            data_list = json.loads(data)
            for content_data in data_list:
                if "issue" in content_data:
                    delete_issue(driver, content_data)
                else:
                    delete_journal(driver, content_data)

            lock_user(driver, user)

            rows_to_delete.append(row_index)

        row_index += 1

    return rows_to_delete


def delete_issue(driver, content_data):
    """Delete an issue via the chrome driver."""
    issue_url = content_data["issue"]
    driver.get(issue_url)

    try:
        perform_delete_button_click(driver, ISSUE_DELETE_BUTTON_XPATH)
    except TimeoutException:
        logger.error(f"The issue '{issue_url}' could not be deleted.")
    else:
        driver.switch_to.alert.accept()


def delete_journal(driver, content_data):
    """Delete a journal (a note/comment) via the chrome driver."""
    issue_url = content_data["journal"][0]
    journal_id = content_data["journal"][1]
    driver.get(issue_url)

    journal_delete_button_xpath = COMMENT_DELETE_BUTTON_XPATH.format(journal_id=journal_id)
    try:
        perform_delete_button_click(driver, journal_delete_button_xpath)
    except TimeoutException:
        logger.error(f"The journal '{journal_id}' of the issue '{issue_url}' could not be deleted.")
    else:
        driver.switch_to.alert.accept()


def perform_delete_button_click(driver, element_xpath):
    """Perform the click, but wait until the element is visible and clickable."""
    wait = WebDriverWait(driver, SECONDS_TO_WAIT)

    element = wait.until(expected_conditions.element_to_be_clickable((By.XPATH, element_xpath)))
    ActionChains(driver).move_to_element(element).click(element).perform()


def lock_user(driver, user):
    """Lock a user via the chrome driver."""
    username, user_id = user.split("/")
    if username != "Anonymous":
        driver.get(f"{REDMINE_USERS_PAGE}/{user_id}/edit")
        try:
            wait = WebDriverWait(driver, SECONDS_TO_WAIT)
            lock_element = wait.until(
                expected_conditions.element_to_be_clickable((By.XPATH, USER_LOCK_BUTTON_XPATH))
            )
        except TimeoutException:
            logger.error(f"The user '{username}' could not be locked.")
        else:
            # some users could be already locked; therefore, check for the context
            if lock_element.text == "Lock":
                ActionChains(driver).move_to_element(lock_element).click(lock_element).perform()


def delete_users_data_from_sheet(rows_to_delete, sheet):
    """Delete users from the sheet who were actually deleted/locked from REDMINE."""
    if rows_to_delete:
        requests = []
        for row_index in rows_to_delete:
            requests.append(
                {
                    "deleteDimension": {
                        "range": {
                            "sheetId": 0,
                            "dimension": "ROWS",
                            "startIndex": row_index,
                            "endIndex": row_index + 1,
                        }
                    }
                }
            )

        # delete rows in the reversed order because they are shifted after each deletion
        requests.reverse()

        # write operations often got timed out; therefore, batch updates are sent in batch
        max_requests = 0
        batch_requests = []
        for request in requests:
            max_requests += 1
            batch_requests.append(request)
            if max_requests == MAX_NUMBER_OF_UPDATES:
                sheet.batchUpdate(
                    spreadsheetId=SPREADSHEET_ID, body={"requests": batch_requests}
                ).execute()
                max_requests = 0
                batch_requests = []

        if batch_requests:
            sheet.batchUpdate(
                spreadsheetId=SPREADSHEET_ID, body={"requests": batch_requests}
            ).execute()


if __name__ == "__main__":
    run()
