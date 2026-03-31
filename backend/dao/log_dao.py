from backend.db.connection import DatabaseSingleton
from backend.core.logger import get_logger
from typing import Optional, Dict, Any
import json

logger = get_logger(__name__)

class LogDao:
    def __init__(self, db=None):
        self.db = db if db else DatabaseSingleton()

    def log_event(self, user_id: Optional[int], event_type: str, details: Optional[Dict[str, Any]] = None) -> bool:
        conn = self.db.get_connection()
        if not conn: return False
        try:
            cursor = conn.cursor()
            details_json = json.dumps(details) if details else None
            cursor.execute("""
                INSERT INTO system_logs (user_id, event_type, details) 
                VALUES (%s, %s, %s)
            """, (user_id if user_id and user_id > 0 else None, event_type, details_json))
            conn.commit()
            return True
        except Exception as e:
            logger.error(f"DAO Error logging event: {e}")
            return False
        finally:
            if conn: conn.close()
        return False

    def get_user_logs(self, user_id: int) -> list:
        conn = self.db.get_connection()
        if not conn: return []
        try:
            cursor = conn.cursor(dictionary=True)
            cursor.execute("SELECT * FROM system_logs WHERE user_id = %s ORDER BY timestamp DESC", (user_id,))
            return cursor.fetchall()
        except Exception as e:
            logger.error(f"DAO Error fetching logs: {e}")
            return []
        finally:
            if conn: conn.close()
        return []
