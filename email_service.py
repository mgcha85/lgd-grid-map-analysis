import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.image import MIMEImage
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

SMTP_SERVER = os.getenv("SMTP_SERVER", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD")
SMTP_SENDER = os.getenv("SMTP_SENDER", SMTP_USER)

def send_analysis_complete_email(recipients, report_path, image_path):
    """
    Sends an email with the analysis report and result image.
    recipients: List of email addresses (strings).
    """
    if not recipients:
        print("No recipients found. Skipping email.")
        return

    if not SMTP_USER or not SMTP_PASSWORD:
        print("SMTP credentials not found in .env. Skipping email.")
        return

    msg = MIMEMultipart()
    msg['Subject'] = 'Grid Map Analysis Complete'
    msg['From'] = SMTP_SENDER
    msg['To'] = ", ".join(recipients)

    # Body
    body_text = "The Grid Map Analysis simulation has completed successfully.\n\nPlease find the attached report and result image."
    msg.attach(MIMEText(body_text, 'plain'))

    # Attach Report (as text in body or attachment? Let's attach)
    if os.path.exists(report_path):
        with open(report_path, 'r', encoding='utf-8') as f:
            report_content = f.read()
            # Attach as markdown file
            attachment = MIMEText(report_content, 'markdown')
            attachment.add_header('Content-Disposition', 'attachment', filename="final_report.md")
            msg.attach(attachment)
    
    # Attach Image
    if os.path.exists(image_path):
        with open(image_path, 'rb') as f:
            img_data = f.read()
            image = MIMEImage(img_data, name="final_result.png")
            msg.attach(image)

    try:
        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        server.starttls()
        server.login(SMTP_USER, SMTP_PASSWORD)
        server.send_message(msg)
        server.quit()
        print(f"Email sent successfully to {len(recipients)} recipients.")
    except Exception as e:
        print(f"Failed to send email: {e}")
