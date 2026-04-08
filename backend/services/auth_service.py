from backend.dao.user_dao import UserDao
from backend.dao.log_dao import LogDao
from backend.dao.otp_dao import OtpDao
from backend.core.security import SecurityService
from backend.models.dtos import LoginRequest, RegisterRequest, ForgotPasswordSendOtpRequest, ForgotPasswordVerifyOtpRequest, ForgotPasswordResetRequest
from backend.core.enums import MessageEnum
from backend.services.communication_service import CommunicationService
import secrets
import string
from datetime import datetime, timedelta

class AuthService:
    def __init__(self, user_dao=None):
        self.user_dao = user_dao if user_dao else UserDao()
        self.log_dao = LogDao(self.user_dao.db)
        self.otp_dao = OtpDao(self.user_dao.db)

    def register(self, data: RegisterRequest) -> dict:
        if self.user_dao.get_user_by_email(data.email):
            return {"success": False, "error": MessageEnum.ERROR_EMAIL_EXISTS.value}

        hashed_pw = SecurityService.get_password_hash(data.password)
        user_dict = data.model_dump() if hasattr(data, 'model_dump') else data.dict()
        user_dict["password_hash"] = hashed_pw

        has_prev = True if data.previous_conditions.lower() == "yes" else False

        user_id = self.user_dao.create_user(
            user_dict,
            has_prev,
            data.symptoms,
            data.symptom_duration,
            data.previous_condition_details or "",
        )

        if not user_id:
            return {"success": False, "error": "Database error while creating user."}

        self.log_dao.log_event(user_id, "User Registered", {"email": data.email})
        return {"success": True, "user_id": user_id, "message": "User registered successfully."}

    def login(self, data: LoginRequest) -> dict:
        user = self.user_dao.get_user_by_email(data.email)
        
        # Admin Bypass logic (for development/demo)
        # Note: In production, this email should be in the DB with proper HASHED password.
        if data.email == "admin@gmail.com" and data.password == "Admin@1234":
            access_token = SecurityService.create_access_token({
                "sub": "admin",
                "user_id": 9999,
                "role": "Admin",
                "email": "admin@gmail.com"
            })
            return {"success": True, "token": access_token, "user": {"id": 9999, "role": "Admin", "name": "Admin User"}}

        if not user or not SecurityService.verify_password(data.password, user["password_hash"]):
            return {"success": False, "error": MessageEnum.ERROR_INVALID_CREDENTIALS.value}

        if not user.get("is_active", True):
             return {"success": False, "error": "This account has been deactivated."}

        access_token = SecurityService.create_access_token({
            "sub": user["email"],
            "user_id": user["id"],
            "role": user.get("role", "User")
        })
        
        self.user_dao.update_login_status(user["id"], True)
        self.log_dao.log_event(user["id"], "User Logged In")

        return {
            "success": True, 
            "token": access_token, 
            "user": {
                "id": user["id"], 
                "email": user["email"], 
                "first_name": user["first_name"],
                "last_name": user["last_name"],
                "role": user.get("role", "User")
            }
        }

    def logout(self, user_id: int) -> dict:
        self.user_dao.update_login_status(user_id, False)
        self.log_dao.log_event(user_id, "User Logged Out")
        return {"success": True, "message": "Logged out successfully."}

    def change_password(self, user_id: int, old_pw: str, new_pw: str) -> dict:
        user = self.user_dao.get_user_by_id(user_id)
        if not user or not SecurityService.verify_password(old_pw, user["password_hash"]):
            return {"success": False, "error": "Invalid current password."}
        
        new_hashed = SecurityService.get_password_hash(new_pw)
        updated = self.user_dao.update_password(user_id, new_hashed)
        if updated:
             self.log_dao.log_event(user_id, "Password Changed")
             return {"success": True, "message": "Password updated successfully."}
        return {"success": False, "error": "Failed to update password."}

    def send_forgot_password_otp(self, data: ForgotPasswordSendOtpRequest) -> dict:
        # Check if email exists
        user = self.user_dao.get_user_by_email(data.email)
        contact = data.email 
        
        if not user and data.contact_number:
            user = self.user_dao.get_user_by_contact_number(data.contact_number)
            contact = data.contact_number

        if not user:
            return {"success": False, "error": "No user found with this email/contact."}

        otp = ''.join(secrets.choice(string.digits) for _ in range(6))
        
        expires_at = datetime.now() + timedelta(minutes=10)
        saved = self.otp_dao.save_otp(user["id"], contact, otp, expires_at)
        
        if saved:
            if "@" in contact:
                sent = CommunicationService.send_otp_email(contact, otp)
                if sent:
                    return {"success": True, "message": "OTP sent successfully.", "dev_otp": otp}
            else:
                sent = CommunicationService.send_otp_messenger(contact, otp)
                if sent:
                    return {"success": True, "message": "OTP sent (Test Mode).", "dev_otp": otp}

        return {"success": False, "error": "Failed to generate/send OTP."}

    def verify_forgot_password_otp(self, data: ForgotPasswordVerifyOtpRequest) -> dict:
        user = self.user_dao.get_user_by_email(data.email)
        if not user:
            return {"success": False, "error": "User not found."}
            
        is_valid = self.otp_dao.verify_otp(user["id"], data.email, data.otp)
        if is_valid:
            return {"success": True, "message": "OTP verified successfully."}
        return {"success": False, "error": "Invalid or expired OTP."}

    def reset_forgotten_password(self, data: ForgotPasswordResetRequest) -> dict:
        user = self.user_dao.get_user_by_email(data.email)
        if not user:
            return {"success": False, "error": "User not found."}
            
        # Optional: Secondary verification check here or trust the previous step flow
        new_hashed = SecurityService.get_password_hash(data.new_password)
        updated = self.user_dao.update_password(user["id"], new_hashed)
        
        if updated:
            self.otp_dao.invalidate_all_otps(user["id"])
            self.log_dao.log_event(user["id"], "Password Reset")
            return {"success": True, "message": "Password reset successfully."}
            
        return {"success": False, "error": "Failed to reset password."}
