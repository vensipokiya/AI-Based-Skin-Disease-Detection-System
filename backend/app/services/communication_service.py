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
                logger.warning(f"SMTP password not set. Logging OTP for {email}: {otp}")
                return True # Simulate success for demo
            
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
    def send_otp_messenger(phone, otp):
        # Stub for Messenger/WhatsApp integration
        logger.info(f"MESSENGER OTP for {phone}: {otp}")
        return True
