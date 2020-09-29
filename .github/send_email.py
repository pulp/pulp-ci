import smtplib
from dynaconf import settings
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText


def get_email_server():
    """Creates an instance of email server.
    Returns:
        server -- SMTP instance
    """
    server = (smtplib.SMTP_SSL if settings.get("EMAIL.ssl") else smtplib.SMTP)(
        settings.get("EMAIL.server", "localhost"),
        settings.get("EMAIL.port", 25),
    )
    if settings.get("EMAIL.tls"):
        server.starttls()
    if settings.get("EMAIL.auth"):
        server.login(
            settings.EMAIL.auth.username, settings.EMAIL.auth.password
        )
    return server


def send_html_email(mail_to, text, html, server, test=False):
    """Nagger email to each owner.
    Arguments:
        mail_to {[list]} -- [email1, email2,...]
        text {str} -- plain text message
        html {str} -- html message
        server {SMTP} -- SMTP server instance
    """
    if not isinstance(mail_to, list):
        mail_to = [mail_to]

    mail_from = settings.get("EMAIL.from", "no-reply@redhat.com")
    mail_to_string = ", ".join(mail_to)
    msg = MIMEMultipart("alternative")
    subject = settings.get(
        "EMAIL.subject", "[Nagger BZ] Bugzilla cleanup report"
    )
    msg["Subject"] = f"{subject} - {datetime.now().date().isoformat()}"
    msg["From"] = mail_from
    msg["To"] = mail_to_string

    # Record the MIME types of both parts - text/plain and text/html.
    part1 = MIMEText(text, "plain")
    part2 = MIMEText(html, "html")

    # Attach parts into message container.
    # According to RFC 2046, the last part of a multipart message, in this case
    # the HTML message, is best and preferred.
    msg.attach(part1)

    # if test:
    #     click.echo(msg)
    #     return

    msg.attach(part2)  # html is included only if not --test
    return server.sendmail(mail_from, mail_to, msg.as_string())


if __name__ == '__main__':
    send_html_email(
        ["bmbouter@redhat.com", "ipanova@redhat.com", "rchan@redhat.com"],
        "Pulp CI job failed",
        "<h1>Pulp CI job failed</h1> - https://github.com/pulp/pulp-ci/actions",
        get_email_server(),
    )
