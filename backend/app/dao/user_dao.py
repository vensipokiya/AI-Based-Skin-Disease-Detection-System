from ..config.database import db_singleton
from ..utils.logger import get_logger
from typing import Optional, Dict, Any, List

logger = get_logger(__name__)

class UserDao:
    def __init__(self, db=None):
        self.db = db if db else db_singleton

    def get_user_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        conn = self.db.get_connection()
        if not conn: return None
        try:
            cursor = conn.cursor(dictionary=True)
            cursor.execute("SELECT * FROM users WHERE email = %s", (email,))
            return cursor.fetchone()
        except Exception as e:
            logger.error(f"DAO Error: {e}")
            return None
        finally:
            if conn: conn.close()
        return None

    def get_user_by_id(self, user_id: int) -> Optional[Dict[str, Any]]:
        conn = self.db.get_connection()
        if not conn: return None
        try:
            cursor = conn.cursor(dictionary=True)
            cursor.execute("SELECT * FROM users WHERE id = %s", (user_id,))
            return cursor.fetchone()
        except Exception as e:
            logger.error(f"DAO Error: {e}")
            return None
        finally:
            if conn: conn.close()
        return None

    def create_user(self, user_data: dict, has_prev: bool, symptoms: str, duration: str, prev_details: str) -> Optional[int]:
        conn = self.db.get_connection()
        if not conn: return None
        try:
            cursor = conn.cursor()
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
            
            conn.commit()
            return user_id
        except Exception as e:
            logger.error(f"DAO Error creating user: {e}")
            return None
        finally:
            if conn: conn.close()
        return None

    def update_login_status(self, user_id: int, status: bool) -> bool:
        conn = self.db.get_connection()
        if not conn: return False
        try:
            cursor = conn.cursor()
            status_val = 1 if status else 0
            if status:
                cursor.execute("UPDATE users SET is_logged_in = %s, last_login = CURRENT_TIMESTAMP WHERE id = %s", (status_val, user_id))
            else:
                cursor.execute("UPDATE users SET is_logged_in = %s WHERE id = %s", (status_val, user_id))
            conn.commit()
            return True
        except Exception as e:
            logger.error(f"DAO Error: {e}")
            return False
        finally:
            if conn: conn.close()
        return False

    def update_password(self, user_id: int, new_password_hash: str) -> bool:
        conn = self.db.get_connection()
        if not conn: return False
        try:
            cursor = conn.cursor()
            cursor.execute("UPDATE users SET password_hash = %s WHERE id = %s", (new_password_hash, user_id))
            conn.commit()
            return True
        except Exception as e:
            logger.error(f"DAO Error: {e}")
            return False
        finally:
            if conn: conn.close()
        return False

    def update_user_profile(self, user_id: int, fname: str, lname: str, phone: str, dob: str, age: int, gender: str, location: str) -> bool:
        conn = self.db.get_connection()
        if not conn: return False
        try:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE users 
                SET first_name = %s, last_name = %s, contact_number = %s, 
                    date_of_birth = %s, age = %s, gender = %s, user_location = %s
                WHERE id = %s
            """, (fname, lname, phone, dob, age, gender, location, user_id))
            conn.commit()
            return True
        except Exception as e:
            logger.error(f"DAO Error updating profile: {e}")
            return False
        finally:
            if conn: conn.close()
        return False

    def record_login(self, user_id: int, session_id: str, device_info: str, ip_address: str) -> bool:
        conn = self.db.get_connection()
        if not conn: return False
        try:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO user_login_history (user_id, session_id, device_info, ip_address, status)
                VALUES (%s, %s, %s, %s, 'LOGIN')
            """, (user_id, session_id, device_info, ip_address))
            conn.commit()
            return True
        except Exception as e:
            logger.error(f"DAO Error recording login: {e}")
            return False
        finally:
            if conn: conn.close()
        return False

    def record_logout(self, session_id: str) -> bool:
        conn = self.db.get_connection()
        if not conn: return False
        try:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE user_login_history 
                SET logout_time = CURRENT_TIMESTAMP, status = 'LOGOUT'
                WHERE session_id = %s
            """, (session_id,))
            conn.commit()
            return True
        except Exception as e:
            logger.error(f"DAO Error recording logout: {e}")
            return False
        finally:
            if conn: conn.close()
        return False

    def update_session_active(self, session_id: str) -> bool:
        conn = self.db.get_connection()
        if not conn: return False
        try:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE user_login_history 
                SET status = 'ACTIVE'
                WHERE session_id = %s AND status != 'LOGOUT'
            """, (session_id,))
            conn.commit()
            return True
        except Exception as e:
            logger.error(f"DAO Error updating session: {e}")
            return False
        finally:
            if conn: conn.close()
        return False

    def create_appointment(self, user_id: int, doctor_name: str, doctor_specialty: str, doctor_area: str, doctor_city: str, appointment_date: str, appointment_time: str) -> bool:
        conn = self.db.get_connection()
        if not conn: return False
        try:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO doctor_appointments (user_id, doctor_name, doctor_specialty, doctor_area, doctor_city, appointment_date, appointment_time)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """, (user_id, doctor_name, doctor_specialty, doctor_area, doctor_city, appointment_date, appointment_time))
            conn.commit()
            return True
        except Exception as e:
            logger.error(f"DAO Error creating appointment: {e}")
            return False
        finally:
            if conn: conn.close()
        return False
