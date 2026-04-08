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
        try:
            with self.user_dao.db.cursor(dictionary=True, commit=True) as cursor:
                if data.email:
                    cursor.execute("SELECT * FROM users WHERE email = %s", (data.email,))
                elif data.phone:
                    cursor.execute("SELECT * FROM users WHERE contact_number = %s", (data.phone,))
                else:
                    return {"success": False, "error": "Email or phone required"}
                    
                user = cursor.fetchone()
                if not user:
                    return {"success": False, "error": "User not found"}
                    
                otp = ''.join(secrets.choice(string.digits) for _ in range(6))
                expiry = datetime.now() + timedelta(minutes=10)
                contact = data.email if data.email else data.phone
                
                cursor.execute("""
                    INSERT INTO otp_verification (uid, contact, otp, is_verified, expires_at, created_at)
                    VALUES (%s, %s, %s, %s, %s, %s)
                """, (user["id"], contact, otp, 0, expiry, datetime.now()))
                
                print(f">>> [DEV] OTP for {contact} is {otp} <<<")
                if data.email:
                    CommunicationService.send_otp_email(contact, otp)
                    
                return {"success": True, "message": "OTP sent successfully", "dev_otp": otp}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def verify_forgot_password_otp(self, data: ForgotPasswordVerifyOtpRequest) -> dict:
        try:
            with self.user_dao.db.cursor(dictionary=True, commit=True) as cursor:
                contact = data.email if data.email else data.phone
                cursor.execute("""
                    SELECT * FROM otp_verification 
                    WHERE contact=%s AND otp=%s 
                    ORDER BY created_at DESC LIMIT 1
                """, (contact, data.otp))
                    
                record = cursor.fetchone()
                if not record:
                    return {"success": False, "error": "Invalid OTP"}
                    
                if datetime.now() > record["expires_at"]:
                    return {"success": False, "error": "OTP expired"}
                
                cursor.execute("UPDATE otp_verification SET is_verified=1 WHERE id=%s", (record["id"],))
                return {"success": True, "message": "OTP verified"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def reset_forgotten_password(self, data: ForgotPasswordResetRequest) -> dict:
        try:
            with self.user_dao.db.cursor(commit=True) as cursor:
                new_hashed = SecurityService.get_password_hash(data.password)
                if data.email:
                    cursor.execute("UPDATE users SET password_hash=%s WHERE email=%s", (new_hashed, data.email))
                elif data.phone:
                    cursor.execute("UPDATE users SET password_hash=%s WHERE contact_number=%s", (new_hashed, data.phone))
                return {"success": True, "message": "Password updated successfully"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def _generate_auth_response(self, request, user, provider_name, provider_id):
        session_id = str(uuid.uuid4())
        access_token = SecurityService.create_access_token({
            "sub": user["email"], "user_id": user["id"], "role": user.get("role", "User"), "session_id": session_id
        })
        
        ip_address = request.client.host if request.client else "Unknown"
        device_info = request.headers.get("user-agent", "Unknown")
        
        self.user_dao.update_login_status(user["id"], True)
        self.user_dao.record_login(user["id"], session_id, device_info, ip_address)
        self.log_dao.log_event(user["id"], f"{provider_name} Login: {provider_id[:10]}...")

        return {
            "success": True, 
            "token": access_token, 
            "user": {
                "id": user["id"], 
                "email": user["email"], 
                "first_name": user["first_name"],
                "last_name": user["last_name"],
                "name": f"{user['first_name']} {user['last_name']}",
                "role": user.get("role", "User"),
                "picture": user.get("profile_image")
            }
        }

    def google_login(self, request, token: str) -> dict:
        from google.oauth2 import id_token
        from google.auth.transport import requests as google_requests
        CLIENT_ID = "YOUR_GOOGLE_CLIENT_ID.apps.googleusercontent.com"
        try:
            idinfo = id_token.verify_oauth2_token(token, google_requests.Request(), CLIENT_ID)
            if idinfo["aud"] != CLIENT_ID:
                 return {"success": False, "error": "Invalid token audience."}
            
            user = self.user_dao.get_or_create_oauth_user(
                "google", idinfo["sub"], idinfo["email"], 
                idinfo.get("given_name", "Google"), idinfo.get("family_name", "User"),
                idinfo.get("picture")
            )
            if not user: return {"success": False, "error": "Auth sync failed."}
            return self._generate_auth_response(request, user, "Google", idinfo["sub"])
        except Exception as e:
            return {"success": False, "error": str(e)}

    def apple_login(self, request, token: str, user_info: dict = None) -> dict:
        import jwt, requests, base64
        from cryptography.hazmat.primitives.asymmetric.rsa import RSAPublicNumbers
        APPLE_CLIENT_ID = "com.your.app.service"
        try:
            apple_keys = requests.get("https://appleid.apple.com/auth/keys").json()["keys"]
            header = jwt.get_unverified_header(token)
            key_data = next((k for k in apple_keys if k["kid"] == header["kid"]), None)
            
            n = int.from_bytes(base64.urlsafe_b64decode(key_data["n"] + "=="), "big")
            e = int.from_bytes(base64.urlsafe_b64decode(key_data["e"] + "=="), "big")
            pub_key = RSAPublicNumbers(e, n).public_key()
            
            decoded = jwt.decode(token, pub_key, algorithms=["RS256"], audience=APPLE_CLIENT_ID, issuer="https://appleid.apple.com")
            
            fname = "Apple"
            lname = "User"
            if user_info and user_info.get("name"):
                fname = user_info["name"].get("firstName", fname)
                lname = user_info["name"].get("lastName", lname)

            user = self.user_dao.get_or_create_oauth_user("apple", decoded["sub"], decoded.get("email"), fname, lname)
            if not user: return {"success": False, "error": "Auth sync failed."}
            return self._generate_auth_response(request, user, "Apple", decoded["sub"])
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def google_callback(self, request) -> dict:
        from ..utils.oauth import oauth
        try:
            token = await oauth.google.authorize_access_token(request)
            uinfo = token.get('userinfo')
            if not uinfo: return {"success": False, "error": "No user info"}
            
            user = self.user_dao.get_or_create_oauth_user(
                "google", uinfo["sub"], uinfo["email"], 
                uinfo.get("given_name", "Google"), uinfo.get("family_name", "User"),
                uinfo.get("picture")
            )
            if not user: return {"success": False, "error": "Auth sync failed."}
            return self._generate_auth_response(request, user, "Google", uinfo["sub"])
        except Exception as e:
            return {"success": False, "error": str(e)}
