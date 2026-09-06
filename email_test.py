import os
import smtplib
from email.message import EmailMessage

from dotenv import load_dotenv


# Load credentials
load_dotenv(".env.txt")

gmail_address = os.getenv("GMAIL_ADDRESS")
gmail_app_password = os.getenv("GMAIL_APP_PASSWORD")
email_to = os.getenv("EMAIL_TO")


# Check that credentials exist
if not gmail_address:
    raise ValueError("GMAIL_ADDRESS not found")

if not gmail_app_password:
    raise ValueError("GMAIL_APP_PASSWORD not found")

if not email_to:
    raise ValueError("EMAIL_TO not found")


# Create email
message = EmailMessage()

message["Subject"] = "Weather AI Agent - Test"
message["From"] = gmail_address
message["To"] = email_to

message.set_content(
    "Hello!\n\n"
    "This is a test email from my first AI agent project.\n\n"
    "Gmail connection is working successfully! 🚀"
)


# Connect to Gmail
with smtplib.SMTP("smtp.gmail.com", 587) as server:

    server.starttls()

    server.login(
        gmail_address,
        gmail_app_password
    )

    server.send_message(message)


print("✅ EMAIL SENT SUCCESSFULLY!")