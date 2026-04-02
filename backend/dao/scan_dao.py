from backend.db.connection import DatabaseSingleton
from backend.core.logger import get_logger
import json
from typing import Optional, List, Dict, Any

logger = get_logger(__name__)

class ScanDao:
    def __init__(self, db=None):
        self.db = db if db else DatabaseSingleton()

    def save_scan(self, user_id: int, user_name: str, disease: str, confidence: float, remedies: dict, image_data: bytes = None) -> Optional[int]:
        conn = self.db.get_connection()
        if not conn: return None
        try:
            cursor = conn.cursor()
            remedies_json = json.dumps(remedies) if remedies else None
            cursor.execute("""
                INSERT INTO scan_history (user_id, user_name, disease, confidence, remedies, image_data) 
                VALUES (%s, %s, %s, %s, %s, %s)
            """, (user_id, user_name, disease, confidence, remedies_json, image_data))
            scan_id = cursor.lastrowid
            conn.commit()
            return scan_id
        except Exception as e:
            logger.error(f"DAO Error saving scan: {e}")
            return None
        finally:
            if conn: conn.close()
        return None

    def get_scan_history(self, user_id: int) -> List[Dict[str, Any]]:
        conn = self.db.get_connection()
        if not conn: return []
        try:
            cursor = conn.cursor(dictionary=True)
            cursor.execute("""
                SELECT id, disease, confidence, remedies, image_data, scan_date 
                FROM scan_history 
                WHERE user_id = %s 
                ORDER BY scan_date DESC
            """, (user_id,))
            return cursor.fetchall() or []
        except Exception as e:
            logger.error(f"DAO Error fetching scan history: {e}")
            return []
        finally:
            if conn: conn.close()
        return []

    def get_user_stats(self, user_id: int) -> Dict[str, Any]:
        conn = self.db.get_connection()
        if not conn: return {"total_scans": 0, "avg_confidence": 0}
        try:
            cursor = conn.cursor(dictionary=True)
            cursor.execute("""
                SELECT 
                    COUNT(*) as total_scans,
                    SUM(CASE WHEN disease = 'Normal' THEN 1 ELSE 0 END) as normal_count,
                    SUM(CASE WHEN disease != 'Normal' THEN 1 ELSE 0 END) as conditions_count,
                    AVG(confidence) as avg_confidence
                FROM scan_history 
                WHERE user_id = %s
            """, (user_id,))
            return cursor.fetchone() or {"total_scans": 0, "avg_confidence": 0}
        except Exception as e:
            logger.error(f"DAO Error: {e}")
            return {"total_scans": 0, "avg_confidence": 0}
        finally:
            if conn: conn.close()
        return {"total_scans": 0, "avg_confidence": 0}

    def delete_scan(self, scan_id: int, user_id: int) -> bool:
        conn = self.db.get_connection()
        if not conn: return False
        try:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM scan_history WHERE id = %s AND user_id = %s", (scan_id, user_id))
            conn.commit()
            return cursor.rowcount > 0
        except Exception as e:
            logger.error(f"DAO Error: {e}")
            return False
        finally:
            if conn: conn.close()
        return False

class LocationDao:
    def __init__(self, db=None):
        self.db = db if db else DatabaseSingleton()

    def save_location(self, user_id: int, lat: float, lng: float) -> Optional[int]:
        conn = self.db.get_connection()
        if not conn: return None
        try:
            cursor = conn.cursor()
            cursor.execute("INSERT INTO user_locations (uid, latitude, longitude) VALUES (%s, %s, %s)", (user_id, lat, lng))
            loc_id = cursor.lastrowid
            conn.commit()
            return loc_id
        except Exception as e:
            logger.error(f"DAO Error: {e}")
            return None
        finally:
            if conn: conn.close()
        return None
