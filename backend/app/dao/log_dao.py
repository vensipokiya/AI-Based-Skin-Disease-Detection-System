import json
from typing import Optional, Dict, Any
from ..config.database import db_singleton
from ..utils.logger import get_logger

logger = get_logger(__name__)


class LogDao:
    def __init__(self, db=None):
        self.db = db if db else db_singleton

    def log_event(self, user_id: Optional[int], event_type: str, details: Optional[Dict[str, Any]] = None) -> bool:
        try:
            with self.db.cursor(commit=True) as cursor:
                details_json = json.dumps(details) if details else None
                cursor.execute("""
                    INSERT INTO system_logs (user_id, event_type, details) 
                    VALUES (%s, %s, %s)
                """, (user_id if user_id and user_id > 0 else None, event_type, details_json))
                return True
        except Exception as e:
            logger.error(f"DAO Error logging event: {e}")
            return False

    def get_user_logs(self, user_id: int) -> list:
        try:
            with self.db.cursor(dictionary=True) as cursor:
                cursor.execute("SELECT * FROM system_logs WHERE user_id = %s ORDER BY timestamp DESC", (user_id,))
                return cursor.fetchall()
        except Exception as e:
            logger.error(f"DAO Error fetching logs: {e}")
            return []
