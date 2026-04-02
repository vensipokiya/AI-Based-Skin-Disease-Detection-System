from ..dao.user_dao import UserDao
from ..dao.log_dao import LogDao
from ..dao.otp_dao import OtpDao
from ..middleware.auth_middleware import SecurityService
from ..schemas.user_schema import LoginRequest, RegisterRequest, ForgotPasswordSendOtpRequest, ForgotPasswordVerifyOtpRequest, ForgotPasswordResetRequest
from ..services.communication_service import CommunicationService
from ..config.settings import settings
import secrets
import string
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
import uuid

class AuthService:
    def __init__(self, user_dao=None):
        self.user_dao = user_dao if user_dao else UserDao()
        self.log_dao = LogDao(self.user_dao.db)
        self.otp_dao = OtpDao(self.user_dao.db)

    def register(self, data: RegisterRequest) -> dict:
        if self.user_dao.get_user_by_email(data.email):
            return {"success": False, "error": "Email already registered."}

        hashed_pw = SecurityService.get_password_hash(data.password)
        user_dict = data.model_dump()
        user_dict["password_hash"] = hashed_pw

        has_prev = True if data.previous_conditions.lower() == "yes" else False

        user_id = self.user_dao.create_user(
            user_dict, has_prev, data.symptoms, data.symptom_duration, data.previous_condition_details
        )

        if not user_id:
            return {"success": False, "error": "Database error while creating user."}

        self.log_dao.log_event(user_id, "User Registered", {"email": data.email})
        return {"success": True, "user_id": user_id, "message": "User registered successfully."}

    def login(self, request, data: LoginRequest) -> dict:
        # Admin Bypass logic
        if data.email == settings.ADMIN_BYPASS_EMAIL and data.password == settings.ADMIN_BYPASS_PW:
            session_id = str(uuid.uuid4())
            access_token = SecurityService.create_access_token({
                "sub": "admin",
                "user_id": 9999,
                "role": "Admin",
                "email": settings.ADMIN_BYPASS_EMAIL,
                "session_id": session_id
            })
            
            ip_address = request.client.host if request.client else "Unknown"
            device_info = request.headers.get("user-agent", "Unknown")
            self.user_dao.record_login(9999, session_id, device_info, ip_address)
            
            return {"success": True, "token": access_token, "user": {"id": 9999, "role": "Admin", "name": "Admin User"}}

        user = self.user_dao.get_user_by_email(data.email)
        if not user or not SecurityService.verify_password(data.password, user["password_hash"]):
            return {"success": False, "error": "Invalid email or password."}

        if not user.get("is_active", True):
             return {"success": False, "error": "This account has been deactivated."}

        session_id = str(uuid.uuid4())
        access_token = SecurityService.create_access_token({
            "sub": user["email"],
            "user_id": user["id"],
            "role": user.get("role", "User"),
            "session_id": session_id
        })
        
        ip_address = request.client.host if request.client else "Unknown"
        device_info = request.headers.get("user-agent", "Unknown")
        
        self.user_dao.update_login_status(user["id"], True)
        self.user_dao.record_login(user["id"], session_id, device_info, ip_address)
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

    def logout(self, request, current_user: dict) -> dict:
        user_id = current_user.get("user_id")
        session_id = current_user.get("session_id")
        
        if user_id:
            self.user_dao.update_login_status(user_id, False)
            self.log_dao.log_event(user_id, "User Logged Out")
            
        if session_id:
            self.user_dao.record_logout(session_id)
            
        return {"success": True, "message": "Logged out successfully."}

    def refresh_token_session(self, current_user: dict) -> dict:
        session_id = current_user.get("session_id")
        if session_id:
            self.user_dao.update_session_active(session_id)
            return {"success": True, "message": "Session status updated to ACTIVE."}
        return {"success": False, "error": "Session ID not found in token."}

    def send_forgot_password_otp(self, data: ForgotPasswordSendOtpRequest) -> dict:
        user = self.user_dao.get_user_by_email(data.email)
        if not user:
            return {"success": False, "error": "No user found with this email."}

        otp = ''.join(secrets.choice(string.digits) for _ in range(6))
        expires_at = datetime.now() + timedelta(minutes=10)
        saved = self.otp_dao.save_otp(user["id"], data.email, otp, expires_at)
        
        if saved:
            sent = CommunicationService.send_otp_email(data.email, otp)
            if sent:
                return {"success": True, "message": "OTP sent successfully."}

        return {"success": False, "error": "Failed to generate/send OTP."}

    def verify_forgot_password_otp(self, data: ForgotPasswordVerifyOtpRequest) -> dict:
        user = self.user_dao.get_user_by_email(data.email)
        if not user:
            return {"success": False, "error": "User not found."}
            
        if self.otp_dao.verify_otp(user["id"], data.email, data.otp):
            return {"success": True, "message": "OTP verified successfully."}
        return {"success": False, "error": "Invalid or expired OTP."}

    def reset_forgotten_password(self, data: ForgotPasswordResetRequest) -> dict:
        user = self.user_dao.get_user_by_email(data.email)
        if not user:
            return {"success": False, "error": "User not found."}
            
        new_hashed = SecurityService.get_password_hash(data.new_password)
        if self.user_dao.update_password(user["id"], new_hashed):
            self.otp_dao.invalidate_all_otps(user["id"])
            self.log_dao.log_event(user["id"], "Password Reset")
            return {"success": True, "message": "Password reset successfully."}
            
        return {"success": False, "error": "Failed to reset password."}
