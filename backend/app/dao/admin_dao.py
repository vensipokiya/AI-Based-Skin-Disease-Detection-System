from ..config.database import db_singleton
from ..utils.logger import get_logger
from typing import List, Dict, Any, Optional
import json

logger = get_logger(__name__)

class AdminDao:
    def __init__(self, db=None):
        self.db = db if db else db_singleton

    def get_all_users(self) -> List[Dict[str, Any]]:
        conn = self.db.get_connection()
        if not conn: return []
        try:
            cursor = conn.cursor(dictionary=True)
            cursor.execute("SELECT id, first_name, last_name, email, age, date_of_birth, gender, contact_number, user_location, role, is_active, is_logged_in FROM users")
            return cursor.fetchall() or []
        finally:
            if conn: conn.close()

    def delete_user(self, uid: int) -> bool:
        conn = self.db.get_connection()
        if not conn: return False
        try:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM users WHERE id = %s", (uid,))
            conn.commit()
            return cursor.rowcount > 0
        finally:
            if conn: conn.close()

    def get_all_scans(self) -> List[Dict[str, Any]]:
        conn = self.db.get_connection()
        if not conn: return []
        try:
            cursor = conn.cursor(dictionary=True)
            cursor.execute("SELECT * FROM scan_history ORDER BY scan_date DESC LIMIT 500")
            rows = cursor.fetchall() or []
            
            import base64
            for row in rows:
                if row.get("image_data"):
                    # For compatibility with admin.js which expects image_base64
                    row["image_base64"] = base64.b64encode(row["image_data"]).decode("utf-8")
                    # For compatibility with any legacy code expecting image_path as a URL/string
                    row["image_path"] = f"data:image/jpeg;base64,{row['image_base64']}"
                    del row["image_data"]
                else:
                    row["image_base64"] = None
                    row["image_path"] = None
            return rows
        finally:
            if conn: conn.close()

    def get_all_medical_profiles(self) -> List[Dict[str, Any]]:
        conn = self.db.get_connection()
        if not conn: return []
        try:
            cursor = conn.cursor(dictionary=True)
            cursor.execute("""
                SELECT mp.*, CONCAT(u.first_name, ' ', u.last_name) as patient_name 
                FROM medical_profiles mp 
                JOIN users u ON mp.user_id = u.id
            """)
            return cursor.fetchall() or []
        finally:
            if conn: conn.close()

    def get_all_appointments(self) -> List[Dict[str, Any]]:
        conn = self.db.get_connection()
        if not conn: return []
        try:
            cursor = conn.cursor(dictionary=True)
            cursor.execute("""
                SELECT a.*, u.first_name, u.last_name, u.email 
                FROM doctor_appointments a 
                JOIN users u ON a.user_id = u.id
            """)
            return cursor.fetchall() or []
        finally:
            if conn: conn.close()

    def get_system_logs(self) -> List[Dict[str, Any]]:
        conn = self.db.get_connection()
        if not conn: return []
        try:
            cursor = conn.cursor(dictionary=True)
            cursor.execute("""
                SELECT sl.*, u.email as user_email 
                FROM system_logs sl 
                LEFT JOIN users u ON sl.user_id = u.id 
                ORDER BY sl.timestamp DESC LIMIT 200
            """)
            return cursor.fetchall() or []
        finally:
            if conn: conn.close()

    def get_login_history(self, offset: int = 0, limit: int = 50, status: str = None, date: str = None, search: str = None) -> List[Dict[str, Any]]:
        conn = self.db.get_connection()
        if not conn: return []
        try:
            cursor = conn.cursor(dictionary=True)
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
        finally:
            if conn: conn.close()

    def get_user_login_history(self, user_id: int, offset: int = 0, limit: int = 50, status: str = None, date: str = None) -> List[Dict[str, Any]]:
        conn = self.db.get_connection()
        if not conn: return []
        try:
            cursor = conn.cursor(dictionary=True)
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
        finally:
            if conn: conn.close()
            
    def force_logout(self, session_id: str) -> bool:
        conn = self.db.get_connection()
        if not conn: return False
        try:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM user_login_history WHERE session_id = %s", (session_id,))
            conn.commit()
            return cursor.rowcount > 0
        finally:
            if conn: conn.close()
