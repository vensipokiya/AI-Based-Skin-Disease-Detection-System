import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from ..config.settings import settings
from ..utils.logger import get_logger

logger = get_logger(__name__)

class CommunicationService:
    @staticmethod
    def send_otp_email(email, otp):
        try:
            if not settings.SMTP_PASSWORD:
                logger.warning(
                    "SMTP not configured; OTP email was not sent. Set SMTP_USER and SMTP_PASSWORD."
                )
                return True  # API may still return success when dev_otp is shown in-app
            
            msg = MIMEMultipart()
            msg['From'] = settings.SMTP_USER
            msg['To'] = email
            msg['Subject'] = "DermaCare AI - Forgot Password OTP"
            
            body = f"Hello, Your OTP is: {otp}. It expires in 10 minutes."
            msg.attach(MIMEText(body, 'plain'))
            
            server = smtplib.SMTP(settings.SMTP_SERVER, settings.SMTP_PORT)
            if settings.SMTP_USE_TLS:
                server.starttls()
            server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
            server.send_message(msg)
            server.quit()
            return True
        except Exception as e:
            logger.error(f"Failed to send email to {email}: {e}")
            return False

    @staticmethod
    def send_otp_messenger(phone, _otp):
        # Stub for Messenger/WhatsApp integration — do not log OTP contents
        logger.info("Messenger OTP dispatch requested (stub; not implemented).")
        return True
