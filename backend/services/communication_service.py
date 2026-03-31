import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from backend.config.config import Config
from backend.core.logger import get_logger

logger = get_logger(__name__)

class CommunicationService:
    @staticmethod
    def send_otp_email(email, otp):
        try:
            smtp_config = Config.SMTP_CONFIG
            if not smtp_config.get("password"):
                logger.warning(f"SMTP password not set. Logging OTP for {email}: {otp}")
                return True # Simulate success for demo
            
            msg = MIMEMultipart()
            msg['From'] = smtp_config["user"]
            msg['To'] = email
            msg['Subject'] = "DermaCare AI - Forgot Password OTP"
            
            body = f"Hello, Your OTP is: {otp}. It expires in 10 minutes."
            msg.attach(MIMEText(body, 'plain'))
            
            server = smtplib.SMTP(smtp_config["server"], smtp_config["port"])
            if smtp_config.get("use_tls"):
                server.starttls()
            server.login(smtp_config["user"], smtp_config["password"])
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
