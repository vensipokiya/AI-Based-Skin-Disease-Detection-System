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
        conn = self.user_dao.db.get_connection()
        if not conn: return {"success": False, "error": "Database connection error"}
        try:
            cursor = conn.cursor(dictionary=True)
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
            
            conn.commit()
            
            # Simulated send
            print(f">>> [DEV] OTP for {contact} is {otp} <<<")
            if data.email:
                CommunicationService.send_otp_email(contact, otp)
                
            # Send dev_otp in response so frontend demo works smoothly if SMTP is not configured
            return {"success": True, "message": "OTP sent successfully", "dev_otp": otp}
        except Exception as e:
            return {"success": False, "error": str(e)}
        finally:
            conn.close()

    def verify_forgot_password_otp(self, data: ForgotPasswordVerifyOtpRequest) -> dict:
        conn = self.user_dao.db.get_connection()
        if not conn: return {"success": False, "error": "Database conn error"}
        try:
            cursor = conn.cursor(dictionary=True)
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
            
            # mark verified
            cursor.execute("""
                UPDATE otp_verification 
                SET is_verified=1 
                WHERE id=%s
            """, (record["id"],))
            conn.commit()
                
            return {"success": True, "message": "OTP verified"}
        except Exception as e:
            return {"success": False, "error": str(e)}
        finally:
            conn.close()

    def reset_forgotten_password(self, data: ForgotPasswordResetRequest) -> dict:
        conn = self.user_dao.db.get_connection()
        if not conn: return {"success": False, "error": "DB err"}
        try:
            cursor = conn.cursor(dictionary=True)
            new_hashed = SecurityService.get_password_hash(data.password)
            
            if data.email:
                cursor.execute(
                    "UPDATE users SET password_hash=%s WHERE email=%s",
                    (new_hashed, data.email)
                )
            elif data.phone:
                cursor.execute(
                    "UPDATE users SET password_hash=%s WHERE contact_number=%s",
                    (new_hashed, data.phone)
                )
            conn.commit()
            return {"success": True, "message": "Password updated successfully"}
        except Exception as e:
            return {"success": False, "error": str(e)}
        finally:
            conn.close()

    def google_login(self, request, token: str) -> dict:
        from google.oauth2 import id_token
        from google.auth.transport import requests as google_requests
        
        # Replace this with your actual Client ID from Google Cloud Console
        CLIENT_ID = "YOUR_GOOGLE_CLIENT_ID.apps.googleusercontent.com"
        
        try:
            # Verify the ID token
            idinfo = id_token.verify_oauth2_token(token, google_requests.Request(), CLIENT_ID)
            
            # Audience check (Security Hardening)
            if idinfo["aud"] != CLIENT_ID:
                 return {"success": False, "error": "Invalid token audience."}
            
            # Extract info 
            google_id = idinfo["sub"] # Unique Google ID
            email = idinfo['email']
            name = idinfo.get('name', 'Google User')
            picture = idinfo.get('picture') # Profile Image URL
            first_name = idinfo.get('given_name') or name.split(' ')[0]
            last_name = idinfo.get('family_name') or (name.split(' ')[1:] if ' ' in name else ['User'])[0]
            
            db_conn = self.user_dao.db.get_connection()
            if not db_conn:
                return {"success": False, "error": "Database connection error"}
                
            try:
                cursor = db_conn.cursor(dictionary=True)
                
                # Check for profile_image column (Safe Migration)
                cursor.execute("SHOW COLUMNS FROM users LIKE 'profile_image'")
                if not cursor.fetchone():
                    cursor.execute("ALTER TABLE users ADD COLUMN profile_image TEXT DEFAULT NULL")

                # 1. First check by Google ID
                cursor.execute("SELECT * FROM users WHERE google_id = %s", (google_id,))
                user = cursor.fetchone()
                
                if not user:
                    # 2. If not found by Google ID, check by Email (to link accounts)
                    cursor.execute("SELECT * FROM users WHERE email = %s", (email,))
                    user = cursor.fetchone()
                    
                    if user:
                        # Link existing email account to this Google ID
                        cursor.execute("SHOW COLUMNS FROM users LIKE 'google_id'")
                        if not cursor.fetchone():
                            cursor.execute("ALTER TABLE users ADD COLUMN google_id VARCHAR(255) DEFAULT NULL")
                        
                        cursor.execute("""
                            UPDATE users 
                            SET google_id=%s, auth_provider='google', profile_image=%s 
                            WHERE id=%s
                        """, (google_id, picture, user["id"]))
                        db_conn.commit()
                        user = self.user_dao.get_user_by_id(user["id"])
                    else:
                        # 3. Create NEW user for first-time Google login
                        # Ensure auth_provider exists
                        cursor.execute("SHOW COLUMNS FROM users LIKE 'auth_provider'")
                        if not cursor.fetchone():
                            cursor.execute("ALTER TABLE users ADD COLUMN auth_provider VARCHAR(50) DEFAULT NULL")
                        
                        cursor.execute("SHOW COLUMNS FROM users LIKE 'google_id'")
                        if not cursor.fetchone():
                            cursor.execute("ALTER TABLE users ADD COLUMN google_id VARCHAR(255) DEFAULT NULL")
                        
                        cursor.execute("""
                            INSERT INTO users (first_name, last_name, email, password_hash, google_id, auth_provider, profile_image, role)
                            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                        """, (first_name, last_name, email, "google_oauth_token", google_id, "google", picture, "User"))
                        db_conn.commit()
                        user_id = cursor.lastrowid
                        user = self.user_dao.get_user_by_id(user_id)
                else:
                    # Sync picture if changed
                    cursor.execute("UPDATE users SET profile_image=%s WHERE google_id=%s", (picture, google_id))
                    db_conn.commit()
            finally:
                db_conn.close()

            # --- standard login logic ---
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
            self.log_dao.log_event(user["id"], f"Google Account Linked: {google_id[:10]}...")

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
                    "picture": picture
                }
            }
            
        except ValueError:
            return {"success": False, "error": "Invalid Google token received."}
        except Exception as e:
            return {"success": False, "error": f"Internal Google Login Error: {str(e)}"}

    def apple_login(self, request, token: str, user_info: dict = None) -> dict:
        import jwt
        import requests
        from cryptography.hazmat.primitives import serialization
        from cryptography.hazmat.primitives.asymmetric.rsa import RSAPublicNumbers
        import base64

        # Replace with your actual Apple Client ID (Service ID)
        APPLE_CLIENT_ID = "com.your.app.service"

        try:
            # 1. Fetch Apple's public keys
            apple_keys_url = "https://appleid.apple.com/auth/keys"
            apple_keys = requests.get(apple_keys_url).json()["keys"]

            # 2. Get the key ID from the token header
            header = jwt.get_unverified_header(token)
            kid = header["kid"]

            # 3. Find matching key
            key_data = next((k for k in apple_keys if k["kid"] == kid), None)
            if not key_data:
                return {"success": False, "error": "Apple Public Key not found."}

            # 4. Convert RSA key data to public key object
            n = int.from_bytes(base64.urlsafe_b64decode(key_data["n"] + "=="), "big")
            e = int.from_bytes(base64.urlsafe_b64decode(key_data["e"] + "=="), "big")
            pub_key = RSAPublicNumbers(e, n).public_key()
            
            # 5. Verify the token
            decoded = jwt.decode(
                token, 
                pub_key, 
                algorithms=["RS256"], 
                audience=APPLE_CLIENT_ID,
                issuer="https://appleid.apple.com"
            )

            # Verification successful
            apple_id = decoded["sub"]
            email = decoded.get("email")

            # Extract Name (Only given during FIRST authorize for Apple)
            first_name = "Apple"
            last_name = "User"
            if user_info and user_info.get("name"):
                first_name = user_info["name"].get("firstName", first_name)
                last_name = user_info["name"].get("lastName", last_name)

            db_conn = self.user_dao.db.get_connection()
            if not db_conn:
                return {"success": False, "error": "DB err"}
                
            try:
                cursor = db_conn.cursor(dictionary=True)
                
                # Check for apple_id column (Safe Migration)
                cursor.execute("SHOW COLUMNS FROM users LIKE 'apple_id'")
                if not cursor.fetchone():
                    cursor.execute("ALTER TABLE users ADD COLUMN apple_id VARCHAR(255) DEFAULT NULL")

                # 1. Check by Apple ID
                cursor.execute("SELECT * FROM users WHERE apple_id = %s", (apple_id,))
                user = cursor.fetchone()
                
                if not user:
                    # 2. Check by Email
                    cursor.execute("SELECT * FROM users WHERE email = %s", (email,))
                    user = cursor.fetchone()
                    
                    if user:
                        # Link existing account to Apple ID
                        cursor.execute("UPDATE users SET apple_id=%s, auth_provider='apple' WHERE id=%s", (apple_id, user["id"]))
                        db_conn.commit()
                        user = self.user_dao.get_user_by_id(user["id"])
                    else:
                        # 3. Create NEW user
                        cursor.execute("""
                            INSERT INTO users (first_name, last_name, email, password_hash, apple_id, auth_provider, role)
                            VALUES (%s, %s, %s, %s, %s, %s, %s)
                        """, (first_name, last_name, email, "apple_oauth_token", apple_id, "apple", "User"))
                        db_conn.commit()
                        user_id = cursor.lastrowid
                        user = self.user_dao.get_user_by_id(user_id)
            finally:
                db_conn.close()

            # --- Authentication Succeeded (Same standard login logic) ---
            session_id = str(uuid.uuid4())
            access_token = SecurityService.create_access_token({
                "sub": user["email"], "user_id": user["id"], "role": user.get("role", "User"), "session_id": session_id
            })
            
            ip_address = request.client.host if request.client else "Unknown"
            device_info = request.headers.get("user-agent", "Unknown")
            
            self.user_dao.update_login_status(user["id"], True)
            self.user_dao.record_login(user["id"], session_id, device_info, ip_address)
            self.log_dao.log_event(user["id"], f"Apple Account Linked: {apple_id[:10]}...")

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

        except Exception as e:
            return {"success": False, "error": f"Internal Apple Auth Error: {str(e)}"}
    async def google_callback(self, request) -> dict:
        from ..utils.oauth import oauth
        try:
            token = await oauth.google.authorize_access_token(request)
            user_info = token.get('userinfo')
            if not user_info:
                return {"success": False, "error": "Could not retrieve user info from Google."}
            
            email = user_info.get('email')
            name = user_info.get('name', 'Google User')
            picture = user_info.get('picture')
            google_id = user_info.get('sub')
            
            first_name = user_info.get('given_name') or name.split(' ')[0]
            last_name = user_info.get('family_name') or (name.split(' ')[1] if ' ' in name else 'User')
            
            db_conn = self.user_dao.db.get_connection()
            if not db_conn: return {"success": False, "error": "DB connection error"}
            
            try:
                cursor = db_conn.cursor(dictionary=True)
                # Ensure columns exist
                cursor.execute("SHOW COLUMNS FROM users LIKE 'google_id'")
                if not cursor.fetchone():
                    cursor.execute("ALTER TABLE users ADD COLUMN google_id VARCHAR(255) DEFAULT NULL")
                
                cursor.execute("SHOW COLUMNS FROM users LIKE 'profile_image'")
                if not cursor.fetchone():
                    cursor.execute("ALTER TABLE users ADD COLUMN profile_image TEXT DEFAULT NULL")
                
                cursor.execute("SHOW COLUMNS FROM users LIKE 'auth_provider'")
                if not cursor.fetchone():
                    cursor.execute("ALTER TABLE users ADD COLUMN auth_provider VARCHAR(50) DEFAULT NULL")

                # Find user
                cursor.execute("SELECT * FROM users WHERE google_id = %s OR email = %s", (google_id, email))
                user = cursor.fetchone()
                
                if not user:
                    # Create new
                    cursor.execute("""
                        INSERT INTO users (first_name, last_name, email, password_hash, google_id, auth_provider, profile_image, role)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    """, (first_name, last_name, email, "google_oauth_token", google_id, "google", picture, "User"))
                    db_conn.commit()
                    user = self.user_dao.get_user_by_id(cursor.lastrowid)
                else:
                    # Update/Link
                    cursor.execute("""
                        UPDATE users SET google_id=%s, auth_provider='google', profile_image=%s 
                        WHERE id=%s
                    """, (google_id, picture, user["id"]))
                    db_conn.commit()
                    user = self.user_dao.get_user_by_id(user["id"])
            finally:
                db_conn.close()

            # Create session and token
            session_id = str(uuid.uuid4())
            access_token = SecurityService.create_access_token({
                "sub": user["email"], "user_id": user["id"], "role": user.get("role", "User"), "session_id": session_id
            })
            
            ip_address = request.client.host if request.client else "Unknown"
            device_info = request.headers.get("user-agent", "Unknown")
            self.user_dao.update_login_status(user["id"], True)
            self.user_dao.record_login(user["id"], session_id, device_info, ip_address)
            
            return {"success": True, "token": access_token, "user": user}
            
        except Exception as e:
            return {"success": False, "error": f"OAuth Error: {str(e)}"}
