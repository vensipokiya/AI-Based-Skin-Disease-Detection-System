from ..config.database import db_singleton
from ..utils.logger import get_logger
from datetime import datetime
from typing import Optional

logger = get_logger(__name__)

class OtpDao:
    def __init__(self, db=None):
        self.db = db if db else db_singleton

    def save_otp(self, user_id: int, contact: str, otp: str, expires_at: datetime) -> bool:
        try:
            with self.db.cursor(commit=True) as cursor:
                cursor.execute("DELETE FROM otp_verification WHERE uid = %s", (user_id,))
                cursor.execute("""
                    INSERT INTO otp_verification (uid, contact, otp, expires_at) 
                    VALUES (%s, %s, %s, %s)
                """, (user_id, contact, otp, expires_at))
                return True
        except Exception as e:
            logger.error(f"DAO Error saving OTP: {e}")
            return False

    def verify_otp(self, user_id: int, contact: str, otp: str) -> bool:
        try:
            with self.db.cursor(dictionary=True, commit=True) as cursor:
                cursor.execute("""
                    SELECT * FROM otp_verification 
                    WHERE uid = %s AND contact = %s AND otp = %s AND expires_at > %s
                """, (user_id, contact, otp, datetime.now()))
                
                result = cursor.fetchone()
                if result:
                    cursor.execute("UPDATE otp_verification SET is_verified = TRUE WHERE id = %s", (result["id"],))
                    return True
                return False
        except Exception as e:
            logger.error(f"DAO Error verifying OTP: {e}")
            return False

    def invalidate_all_otps(self, user_id: int) -> bool:
        try:
            with self.db.cursor(commit=True) as cursor:
                cursor.execute("DELETE FROM otp_verification WHERE uid = %s", (user_id,))
                return True
        except Exception as e:
            logger.error(f"DAO Error: {e}")
            return False
