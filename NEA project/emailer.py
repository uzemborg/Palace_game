import smtplib
import accounts
from email.mime.text import MIMEText

sender_email = "uzemborg@gmail.com"
sender_pass = "mwhe zioe gkhc bobh"

def load_emails():  #load all email addresses
    return accounts.get_email_addresses()

def send_email(to_address, subject, body):  # Construct an email message and deliver it using SMTP
    msg = MIMEText(body)
    msg["From"] = sender_email
    msg["To"] = to_address
    msg["Subject"] = subject

    server = smtplib.SMTP("smtp.gmail.com", 587)
    try:
        server.starttls()  # Secure the SMTP connection before authenticating
        server.login(sender_email, sender_pass)  # Authenticate the sender before delivering a message
        server.sendmail(sender_email, to_address, msg.as_string())
    finally:
        server.quit()

def send_to_all(subject, body, on_result=None):  # Attempt each delivery independently and notify the caller of failures
    addresses = load_emails()
    for address in addresses:  # Try each recipient independently so a failure does not stop the mailing list
        try:
            send_email(address, subject, body)
            if on_result:
                on_result(address, True, None)
        except Exception as e:
            if on_result:
                on_result(address, False, str(e))
    return addresses