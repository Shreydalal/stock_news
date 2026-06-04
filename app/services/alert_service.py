import logging
import httpx
import smtplib
from datetime import date
from pathlib import Path
from typing import Optional
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders

from app.core.config import settings
from app.utils.pdf_generator import generate_pdf_from_markdown

logger = logging.getLogger(__name__)

class AlertService:
    def __init__(self):
        self.bot_token = settings.TELEGRAM_BOT_TOKEN
        self.chat_id = settings.TELEGRAM_CHAT_ID

    def send_telegram_alert(self, message: str) -> bool:
        """Sends a text alert to a Telegram channel/chat."""
        if not self.bot_token or not self.chat_id:
            logger.info("Telegram Alerts: Not configured. Logging summary message instead:")
            logger.info(f"\n--- TELEGRAM MOCK DUMP ---\n{message}\n-------------------------")
            return False

        url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
        payload = {
            "chat_id": self.chat_id,
            "text": message,
            "parse_mode": "Markdown"
        }

        try:
            logger.info("Sending Telegram alert...")
            response = httpx.post(url, json=payload, timeout=10.0)
            response.raise_for_status()
            logger.info("Telegram alert sent successfully.")
            return True
        except Exception as e:
            logger.error(f"Failed to send Telegram alert: {e}", exc_info=True)
            return False

    def send_email_report(self, report_date: date, markdown_content: str, pdf_output_dir: Optional[Path] = None) -> bool:
        """
        Compiles the report markdown into a PDF and emails it to the configured address.
        """
        # Determine temporary PDF directory
        if not pdf_output_dir:
            pdf_output_dir = Path(__file__).resolve().parent.parent.parent / "reports" / "temp"
        pdf_output_dir.mkdir(parents=True, exist_ok=True)
        pdf_path = pdf_output_dir / f"market_report_{report_date}.pdf"

        # Generate PDF
        try:
            generate_pdf_from_markdown(markdown_content, pdf_path)
        except Exception as e:
            logger.error(f"Could not generate PDF for email attachment: {e}")
            return False

        # Check SMTP configuration
        smtp_configured = all([
            settings.SMTP_HOST,
            settings.SMTP_PORT,
            settings.SMTP_USER,
            settings.SMTP_PASSWORD,
            settings.EMAIL_TO
        ])

        if not smtp_configured:
            logger.info("Email Alerts: Not configured. Saved PDF locally. Skipped SMTP mailing.")
            logger.info(f"Local PDF copy available at: {pdf_path}")
            return False

        # Build email message
        msg = MIMEMultipart()
        msg['From'] = settings.SMTP_USER
        msg['To'] = settings.EMAIL_TO
        msg['Subject'] = f"Daily Market Intelligence Report - {report_date}"

        # Email body
        body = f"Please find attached the Daily Market Intelligence Report for {report_date} in PDF format."
        msg.attach(MIMEText(body, 'plain'))

        # Attach PDF
        try:
            with open(pdf_path, "rb") as attachment:
                part = MIMEBase('application', 'octet-stream')
                part.set_payload(attachment.read())
                encoders.encode_base64(part)
                part.add_header(
                    'Content-Disposition',
                    f"attachment; filename=market_report_{report_date}.pdf"
                )
                msg.attach(part)
        except Exception as e:
            logger.error(f"Failed to attach PDF to email: {e}")
            return False

        # Send email via SMTP
        try:
            logger.info(f"Connecting to SMTP server {settings.SMTP_HOST}:{settings.SMTP_PORT}...")
            # We use standard StartTLS standard port 587
            server = smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=15.0)
            server.starttls()
            server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
            
            logger.info(f"Sending email to {settings.EMAIL_TO}...")
            server.sendmail(settings.SMTP_USER, settings.EMAIL_TO, msg.as_string())
            server.quit()
            logger.info("Email report sent successfully.")
            
            # Clean up temp PDF
            if pdf_path.exists():
                pdf_path.unlink()
                
            return True
        except Exception as e:
            logger.error(f"SMTP email sending failed: {e}", exc_info=True)
            return False
