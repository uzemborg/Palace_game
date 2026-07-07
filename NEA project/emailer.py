import smtplib
from email.mime.text import MIMEText

sender_email = "uzemborg@gmail.com"      
sender_pass = "mwhe zioe gkhc bobh"       

def load_emails(path="emails.txt"):
    try:
        with open(path, "r") as f:
            return [line.strip() for line in f if line.strip()]
    except FileNotFoundError:
        return []

def send_email(to_address, subject, body):
    msg = MIMEText(body)
    msg["From"] = sender_email
    msg["To"] = to_address
    msg["Subject"] = subject

    server = smtplib.SMTP("smtp.gmail.com", 587)
    try:
        server.starttls()
        server.login(sender_email, sender_pass)
        server.sendmail(sender_email, to_address, msg.as_string())
    finally:
        server.quit()

def send_to_all(subject, body, on_result=None):
    addresses = load_emails()
    for address in addresses:
        try:
            send_email(address, subject, body)
            if on_result:
                on_result(address, True, None)
        except Exception as e:
            if on_result:
                on_result(address, False, str(e))
    return addresses