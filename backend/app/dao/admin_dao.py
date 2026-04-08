import os
import json
import base64
import requests
from typing import List, Dict, Any, Optional
from ..config.database import db_singleton
from ..utils.logger import get_logger

logger = get_logger(__name__)

class AdminDao:
    def __init__(self, db=None):
        self.db = db if db else db_singleton

    def get_all_users(self) -> List[Dict[str, Any]]:
        try:
            with self.db.cursor(dictionary=True) as cursor:
                cursor.execute("SELECT id, first_name, last_name, email, age, date_of_birth, gender, contact_number, user_location, role, is_active, is_logged_in FROM users")
                return cursor.fetchall() or []
        except Exception as e:
            logger.error(f"DAO Error: {e}")
            return []

    def delete_user(self, uid: int) -> bool:
        try:
            with self.db.cursor(commit=True) as cursor:
                cursor.execute("DELETE FROM users WHERE id = %s", (uid,))
                return cursor.rowcount > 0
        except Exception as e:
            logger.error(f"DAO Error: {e}")
            return False

    def get_all_scans(self) -> List[Dict[str, Any]]:
        try:
            with self.db.cursor(dictionary=True) as cursor:
                cursor.execute("SELECT * FROM scan_history ORDER BY scan_date DESC LIMIT 500")
                rows = cursor.fetchall() or []
                
                for row in rows:
                    if row.get("image_data"):
                        row["image_base64"] = base64.b64encode(row["image_data"]).decode("utf-8")
                        row["image_path"] = f"data:image/jpeg;base64,{row['image_base64']}"
                        del row["image_data"]
                    else:
                        row["image_base64"] = None
                        row["image_path"] = None
                return rows
        except Exception as e:
            logger.error(f"DAO Error: {e}")
            return []

    def get_all_medical_profiles(self) -> List[Dict[str, Any]]:
        try:
            with self.db.cursor(dictionary=True) as cursor:
                cursor.execute("""
                    SELECT mp.*, CONCAT(u.first_name, ' ', u.last_name) as patient_name 
                    FROM medical_profiles mp 
                    JOIN users u ON mp.user_id = u.id
                """)
                return cursor.fetchall() or []
        except Exception as e:
            logger.error(f"DAO Error: {e}")
            return []

    def get_all_appointments(self) -> List[Dict[str, Any]]:
        try:
            with self.db.cursor(dictionary=True) as cursor:
                cursor.execute("""
                    SELECT a.*, u.first_name, u.last_name, u.email 
                    FROM doctor_appointments a 
                    JOIN users u ON a.user_id = u.id
                """)
                return cursor.fetchall() or []
        except Exception as e:
            logger.error(f"DAO Error: {e}")
            return []

    def get_system_logs(self) -> List[Dict[str, Any]]:
        try:
            with self.db.cursor(dictionary=True) as cursor:
                cursor.execute("""
                    SELECT sl.*, u.email as user_email 
                    FROM system_logs sl 
                    LEFT JOIN users u ON sl.user_id = u.id 
                    ORDER BY sl.timestamp DESC LIMIT 200
                """)
                return cursor.fetchall() or []
        except Exception as e:
            logger.error(f"DAO Error: {e}")
            return []

    def get_login_history(self, offset: int = 0, limit: int = 50, status: str = None, date: str = None, search: str = None) -> List[Dict[str, Any]]:
        try:
            with self.db.cursor(dictionary=True) as cursor:
                query = """
                    SELECT lh.*, 
                        COALESCE(u.first_name, 'Admin') as first_name,
                        COALESCE(u.last_name, '')        as last_name,
                        COALESCE(u.email, 'admin@system') as email 
                    FROM user_login_history lh
                    LEFT JOIN users u ON lh.user_id = u.id
                    WHERE 1=1
                """
                params = []
                
                if status:
                    query += " AND lh.status = %s"
                    params.append(status)
                    
                if date:
                    query += " AND DATE(lh.login_time) = %s"
                    params.append(date)

                if search:
                    query += " AND (u.email LIKE %s OR u.first_name LIKE %s OR u.last_name LIKE %s)"
                    search_param = f"%{search}%"
                    params.extend([search_param, search_param, search_param])
                    
                query += " ORDER BY lh.login_time DESC LIMIT %s OFFSET %s"
                params.extend([limit, offset])
                
                cursor.execute(query, params)
                return cursor.fetchall() or []
        except Exception as e:
            logger.error(f"DAO Error: {e}")
            return []

    def get_user_login_history(self, user_id: int, offset: int = 0, limit: int = 50, status: str = None, date: str = None) -> List[Dict[str, Any]]:
        try:
            with self.db.cursor(dictionary=True) as cursor:
                query = """
                    SELECT lh.*, 
                        COALESCE(u.first_name, 'Admin') as first_name,
                        COALESCE(u.last_name, '')        as last_name,
                        COALESCE(u.email, 'admin@system') as email 
                    FROM user_login_history lh
                    LEFT JOIN users u ON lh.user_id = u.id
                    WHERE lh.user_id = %s
                """
                params = [user_id]
                
                if status:
                    query += " AND lh.status = %s"
                    params.append(status)
                    
                if date:
                    query += " AND DATE(lh.login_time) = %s"
                    params.append(date)
                    
                query += " ORDER BY lh.login_time DESC LIMIT %s OFFSET %s"
                params.extend([limit, offset])
                
                cursor.execute(query, params)
                return cursor.fetchall() or []
        except Exception as e:
            logger.error(f"DAO Error: {e}")
            return []
            
    def force_logout(self, session_id: str) -> bool:
        try:
            with self.db.cursor(commit=True) as cursor:
                cursor.execute("DELETE FROM user_login_history WHERE session_id = %s", (session_id,))
                return cursor.rowcount > 0
        except Exception as e:
            logger.error(f"DAO Error: {e}")
            return False

    def get_all_user_locations(self) -> List[Dict[str, Any]]:
        try:
            with self.db.cursor(dictionary=True, commit=True) as cursor:
                # Performance Fix: Add column if it doesn't exist dynamically
                cursor.execute("SHOW COLUMNS FROM user_locations LIKE 'location_name'")
                if not cursor.fetchone():
                    try: cursor.execute("ALTER TABLE user_locations ADD COLUMN location_name VARCHAR(255)")
                    except: pass

                cursor.execute("""
                    SELECT l.*, CONCAT(u.first_name, ' ', u.last_name) as patient_name, u.email 
                    FROM user_locations l 
                    JOIN users u ON l.uid = u.id 
                    ORDER BY l.timestamp DESC LIMIT 200
                """)
                rows = cursor.fetchall() or []
                
                updated = False
                for r in rows:
                    if not r.get("location_name") or r["location_name"] == "Unknown":
                        url = f"https://nominatim.openstreetmap.org/reverse?format=jsonv2&lat={r['latitude']}&lon={r['longitude']}"
                        try:
                            resp = requests.get(url, headers={"User-Agent": "DermaCare-App/1.0"}, timeout=2)
                            if resp.status_code == 200:
                                addr = resp.json().get("address", {})
                                city = addr.get("city") or addr.get("town") or addr.get("municipality") or addr.get("village") or addr.get("county") or addr.get("city_district") or ""
                                area = addr.get("suburb") or addr.get("neighbourhood") or ""
                                state = addr.get("state") or ""
                                
                                parts = [p for p in [area, city, state] if p]
                                loc = ", ".join(parts) if parts else "Unknown"
                                r["location_name"] = loc
                                cursor.execute("UPDATE user_locations SET location_name=%s WHERE id=%s", (loc, r["id"]))
                                updated = True
                        except:
                            r["location_name"] = "Unknown"
                return rows
        except Exception as e:
            logger.error(f"DAO Error: {e}")
            return []

    def get_all_otp_verifications(self) -> List[Dict[str, Any]]:
        try:
            with self.db.cursor(dictionary=True) as cursor:
                cursor.execute("SELECT * FROM otp_verification ORDER BY created_at DESC LIMIT 200")
                return cursor.fetchall() or []
        except Exception as e:
            logger.error(f"DAO Error: {e}")
            return []
