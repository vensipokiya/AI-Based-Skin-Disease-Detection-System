import base64
import json
from typing import Optional, List, Dict, Any
from ..config.database import db_singleton
from ..utils.logger import get_logger

logger = get_logger(__name__)


class ScanDao:
    def __init__(self, db=None):
        self.db = db if db else db_singleton

    def save_scan(self, user_id: int, user_name: str, disease: str, confidence: float, remedies: dict, image_bytes: bytes = None) -> Optional[int]:
        try:
            with self.db.cursor(commit=True) as cursor:
                remedies_json = json.dumps(remedies) if remedies else None
                cursor.execute("""
                    INSERT INTO scan_history (user_id, user_name, disease, confidence, remedies, image_data) 
                    VALUES (%s, %s, %s, %s, %s, %s)
                """, (user_id, user_name, disease, confidence, remedies_json, image_bytes))
                return cursor.lastrowid
        except Exception as e:
            logger.error(f"DAO Error saving scan: {e}")
            return None

    def get_scan_history(self, user_id: int) -> List[Dict[str, Any]]:
        try:
            with self.db.cursor(dictionary=True) as cursor:
                cursor.execute("""
                    SELECT id, disease, confidence, remedies, image_data, scan_date 
                    FROM scan_history 
                    WHERE user_id = %s 
                    ORDER BY scan_date DESC
                """, (user_id,))
                rows = cursor.fetchall() or []

                for row in rows:
                    if row.get("image_data"):
                        row["image_path"] = base64.b64encode(row["image_data"]).decode("utf-8")
                        del row["image_data"]
                    else:
                        row["image_path"] = None

                return rows
        except Exception as e:
            logger.error(f"DAO Error fetching scan history: {e}")
            return []

    def get_user_stats(self, user_id: int) -> Dict[str, Any]:
        default = {"total_scans": 0, "avg_confidence": 0}
        try:
            with self.db.cursor(dictionary=True) as cursor:
                cursor.execute("""
                    SELECT 
                        COUNT(*) as total_scans,
                        AVG(confidence) as avg_confidence
                    FROM scan_history 
                    WHERE user_id = %s
                """, (user_id,))
                return cursor.fetchone() or default
        except Exception as e:
            logger.error(f"DAO Error: {e}")
            return default

    def delete_scan(self, scan_id: int, user_id: int) -> bool:
        try:
            with self.db.cursor(commit=True) as cursor:
                cursor.execute("DELETE FROM scan_history WHERE id = %s AND user_id = %s", (scan_id, user_id))
                return cursor.rowcount > 0
        except Exception as e:
            logger.error(f"DAO Error: {e}")
            return False


class LocationDao:
    def __init__(self, db=None):
        self.db = db if db else db_singleton

    def save_location(self, user_id: int, lat: float, lng: float, location_name: str = None) -> Optional[int]:
        try:
            with self.db.cursor(commit=True) as cursor:
                cursor.execute("INSERT INTO user_locations (uid, latitude, longitude) VALUES (%s, %s, %s)", (user_id, lat, lng))
                loc_id = cursor.lastrowid
                if location_name:
                    cursor.execute("UPDATE users SET user_location = %s WHERE id = %s", (location_name, user_id))
                return loc_id
        except Exception as e:
            logger.error(f"DAO Error: {e}")
            return None
