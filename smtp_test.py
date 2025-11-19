import os, smtplib
from email.message import EmailMessage

SMTP = os.getenv('MAIL_SERVER', 'smtp.gmail.com')
PORT = int(os.getenv('MAIL_PORT', 587))
USERNAME = os.getenv('MAIL_USERNAME')
PASSWORD = os.getenv('MAIL_PASSWORD')
TO = os.getenv('TEST_RECIPIENT', USERNAME)

msg = EmailMessage()
msg['Subject'] = 'SMTP Test'
msg['From'] = USERNAME
msg['To'] = TO
msg.set_content('This is a test email from smtp_test.py')

print("Trying to connect to", SMTP, "port", PORT, "as", USERNAME)
try:
    server = smtplib.SMTP(SMTP, PORT, timeout=15)
    server.ehlo()
    server.starttls()
    server.login(USERNAME, PASSWORD)
    server.send_message(msg)
    server.quit()
    print("SMTP test succeeded; message sent to", TO)
except Exception as e:
    print("SMTP test failed:", repr(e))
