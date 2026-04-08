from ..config.database import db_singleton
from ..utils.logger import get_logger
from typing import Optional, Dict, Any, List

logger = get_logger(__name__)

class UserDao:
    def __init__(self, db=None):
        self.db = db if db else db_singleton

    def get_user_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        try:
            with self.db.cursor(dictionary=True) as cursor:
                cursor.execute("SELECT * FROM users WHERE email = %s", (email,))
                return cursor.fetchone()
        except Exception as e:
            logger.error(f"DAO Error: {e}")
            return None

    def get_user_by_id(self, user_id: int) -> Optional[Dict[str, Any]]:
        try:
            with self.db.cursor(dictionary=True) as cursor:
                cursor.execute("SELECT * FROM users WHERE id = %s", (user_id,))
                user = cursor.fetchone()
                
                if user:
                    loc = user.get("user_location")
                    if not loc or str(loc).strip() == "" or str(loc).strip().lower() == "unknown":
                        cursor.execute("SELECT location_name FROM user_locations WHERE uid = %s ORDER BY timestamp DESC LIMIT 1", (user_id,))
                        loc_record = cursor.fetchone()
                        if loc_record and loc_record.get("location_name") and loc_record["location_name"].lower() != "unknown":
                            user["user_location"] = loc_record["location_name"]
                return user
        except Exception as e:
            logger.error(f"DAO Error: {e}")
            return None

    def create_user(self, user_data: dict, has_prev: bool, symptoms: str, duration: str, prev_details: str) -> Optional[int]:
        try:
            with self.db.cursor(commit=True) as cursor:
                cursor.execute("""
                    INSERT INTO users (first_name, last_name, email, password_hash, contact_number, gender, date_of_birth, age, role)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                """, (
                    user_data["first_name"], user_data["last_name"], user_data["email"], user_data["password_hash"],
                    user_data.get("contact_number"), user_data.get("gender"), user_data.get("date_of_birth"), user_data.get("age"),
                    user_data.get("role", "User")
                ))
                user_id = cursor.lastrowid
                
                cursor.execute("""
                    INSERT INTO medical_profiles (user_id, symptoms, symptom_duration, has_previous_conditions, previous_condition_details)
                    VALUES (%s, %s, %s, %s, %s)
                """, (user_id, symptoms, duration, has_prev, prev_details))
                return user_id
        except Exception as e:
            logger.error(f"DAO Error creating user: {e}")
            return None

    def update_login_status(self, user_id: int, status: bool) -> bool:
        try:
            with self.db.cursor(commit=True) as cursor:
                status_val = 1 if status else 0
                if status:
                    cursor.execute("UPDATE users SET is_logged_in = %s, last_login = CURRENT_TIMESTAMP WHERE id = %s", (status_val, user_id))
                else:
                    cursor.execute("UPDATE users SET is_logged_in = %s WHERE id = %s", (status_val, user_id))
                return True
        except Exception as e:
            logger.error(f"DAO Error: {e}")
            return False

    def update_password(self, user_id: int, new_password_hash: str) -> bool:
        try:
            with self.db.cursor(commit=True) as cursor:
                cursor.execute("UPDATE users SET password_hash = %s WHERE id = %s", (new_password_hash, user_id))
                return True
        except Exception as e:
            logger.error(f"DAO Error: {e}")
            return False

    def update_user_profile(self, user_id: int, fname: str, lname: str, phone: str, dob: str, age: int, gender: str, location: str) -> bool:
        try:
            with self.db.cursor(commit=True) as cursor:
                cursor.execute("""
                    UPDATE users 
                    SET first_name = %s, last_name = %s, contact_number = %s, 
                        date_of_birth = %s, age = %s, gender = %s, user_location = %s
                    WHERE id = %s
                """, (fname, lname, phone, dob, age, gender, location, user_id))
                return True
        except Exception as e:
            logger.error(f"DAO Error updating profile: {e}")
            return False

    def record_login(self, user_id: int, session_id: str, device_info: str, ip_address: str) -> bool:
        try:
            with self.db.cursor(commit=True) as cursor:
                cursor.execute("""
                    INSERT INTO user_login_history (user_id, session_id, device_info, ip_address, status)
                    VALUES (%s, %s, %s, %s, 'LOGIN')
                """, (user_id, session_id, device_info, ip_address))
                return True
        except Exception as e:
            logger.error(f"DAO Error recording login: {e}")
            return False

    def record_logout(self, session_id: str) -> bool:
        try:
            with self.db.cursor(commit=True) as cursor:
                cursor.execute("""
                    UPDATE user_login_history 
                    SET logout_time = CURRENT_TIMESTAMP, status = 'LOGOUT'
                    WHERE session_id = %s
                """, (session_id,))
                return True
        except Exception as e:
            logger.error(f"DAO Error recording logout: {e}")
            return False

    def update_session_active(self, session_id: str) -> bool:
        try:
            with self.db.cursor(commit=True) as cursor:
                cursor.execute("""
                    UPDATE user_login_history 
                    SET status = 'ACTIVE'
                    WHERE session_id = %s AND status != 'LOGOUT'
                """, (session_id,))
                return True
        except Exception as e:
            logger.error(f"DAO Error updating session: {e}")
            return False

    def create_appointment(self, user_id: int, doctor_name: str, doctor_specialty: str, doctor_area: str, doctor_city: str, appointment_date: str, appointment_time: str) -> bool:
        try:
            with self.db.cursor(commit=True) as cursor:
                cursor.execute("""
                    INSERT INTO doctor_appointments (user_id, doctor_name, doctor_specialty, doctor_area, doctor_city, appointment_date, appointment_time)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                """, (user_id, doctor_name, doctor_specialty, doctor_area, doctor_city, appointment_date, appointment_time))
                return True
        except Exception as e:
            logger.error(f"DAO Error creating appointment: {e}")
            return False

    def get_or_create_oauth_user(self, provider: str, provider_id: str, email: str, first_name: str, last_name: str, profile_image: str = None) -> Optional[Dict[str, Any]]:
        try:
            with self.db.cursor(dictionary=True, commit=True) as cursor:
                # Ensure necessary columns exist (Safe Migrations)
                cursor.execute("SHOW COLUMNS FROM users LIKE 'profile_image'")
                if not cursor.fetchone():
                    cursor.execute("ALTER TABLE users ADD COLUMN profile_image TEXT DEFAULT NULL")
                
                cursor.execute("SHOW COLUMNS FROM users LIKE 'auth_provider'")
                if not cursor.fetchone():
                    cursor.execute("ALTER TABLE users ADD COLUMN auth_provider VARCHAR(50) DEFAULT NULL")
                
                id_col = f"{provider}_id"
                cursor.execute(f"SHOW COLUMNS FROM users LIKE %s", (id_col,))
                if not cursor.fetchone():
                    cursor.execute(f"ALTER TABLE users ADD COLUMN {id_col} VARCHAR(255) DEFAULT NULL")

                # 1. Try to find by provider_id
                cursor.execute(f"SELECT * FROM users WHERE {id_col} = %s", (provider_id,))
                user = cursor.fetchone()

                if not user:
                    # 2. Try to find by email
                    cursor.execute("SELECT * FROM users WHERE email = %s", (email,))
                    user = cursor.fetchone()

                    if user:
                        # Link existing account
                        cursor.execute(f"UPDATE users SET {id_col}=%s, auth_provider=%s, profile_image=%s WHERE id=%s", (provider_id, provider, profile_image, user["id"]))
                    else:
                        # 3. Create new user
                        cursor.execute(f"""
                            INSERT INTO users (first_name, last_name, email, password_hash, {id_col}, auth_provider, profile_image, role)
                            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                        """, (first_name, last_name, email, f"{provider}_oauth_token", provider_id, provider, profile_image, "User"))
                        user_id = cursor.lastrowid
                        cursor.execute("SELECT * FROM users WHERE id = %s", (user_id,))
                        user = cursor.fetchone()
                else:
                    # Sync profile image if provided
                    if profile_image:
                        cursor.execute("UPDATE users SET profile_image=%s WHERE id=%s", (profile_image, user["id"]))
                
                return user
        except Exception as e:
            logger.error(f"DAO OAuth Error: {e}")
            return None
