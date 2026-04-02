from backend.db.connection import DatabaseSingleton
from backend.core.logger import get_logger
from typing import Optional, Dict, Any, List

logger = get_logger(__name__)

class UserDao:
    def __init__(self, db=None):
        self.db = db if db else DatabaseSingleton()

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

    def get_medical_profile(self, user_id: int) -> Optional[Dict[str, Any]]:
        conn = self.db.get_connection()
        if not conn: return None
        try:
            cursor = conn.cursor(dictionary=True)
            cursor.execute("SELECT * FROM medical_profiles WHERE user_id = %s", (user_id,))
            return cursor.fetchone()
        except Exception as e:
            return None
        finally:
            if conn: conn.close()
        return None

    def create_appointment(self, user_id: int, doc_name: str, doc_specialty: str, doc_area: str, doc_city: str, app_date: str, app_time: str) -> bool:
        conn = self.db.get_connection()
        if not conn: return False
        try:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO doctor_appointments (user_id, doctor_name, doctor_specialty, doctor_area, doctor_city, appointment_date, appointment_time)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """, (user_id, doc_name, doc_specialty, doc_area, doc_city, app_date, app_time))
            conn.commit()
            return True
        except Exception as e:
            logger.error(f"DAO Error adding appointment: {e}")
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
