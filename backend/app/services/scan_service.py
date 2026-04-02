from ..dao.scan_dao import ScanDao, LocationDao
from ..dao.user_dao import UserDao
from ..utils.image_upload import save_upload_file
import json
from typing import Optional, Dict, Any

class ScanService:
    def __init__(self, scan_dao=None, user_dao=None):
        self.scan_dao = scan_dao if scan_dao else ScanDao()
        self.user_dao = user_dao if user_dao else UserDao()
        self.location_dao = LocationDao(self.scan_dao.db)

    def save_scan(self, user_id: int, disease: str, confidence: float, remedies: dict, image_bytes: bytes = None) -> dict:
        user = self.user_dao.get_user_by_id(user_id)
        user_name = f"{user['first_name']} {user['last_name']}" if user else "Unknown User"
        
        scan_id = self.scan_dao.save_scan(user_id, user_name, disease, confidence, remedies, image_bytes)
        if scan_id:
             return {"success": True, "scan_id": scan_id}
        return {"success": False, "error": "Database error"}

    def get_history(self, user_id: int) -> dict:
        history_rows = self.scan_dao.get_scan_history(user_id)
        history = []
        for row in history_rows:
            remedies_data = row.get("remedies")
            if isinstance(remedies_data, str):
                try: remedies_data = json.loads(remedies_data)
                except: remedies_data = None
            
            history.append({
                "id": row["id"],
                "disease": row["disease"],
                "confidence": row["confidence"],
                "remedies": remedies_data,
                "image_path": row.get("image_path"),
                "date": row["scan_date"].isoformat() if hasattr(row["scan_date"], 'isoformat') else str(row["scan_date"])
            })
            
        stats = self.scan_dao.get_user_stats(user_id)
        stats_formatted = {
            "total_scans": int(stats.get("total_scans", 0) or 0),
            "avg_confidence": round(float(stats.get("avg_confidence", 0) or 0), 1)
        }
        
        return {"history": history, "stats": stats_formatted}

    def delete_record(self, scan_id: int, user_id: int) -> dict:
        # TODO: Potentially delete the local file too
        deleted = self.scan_dao.delete_scan(scan_id, user_id)
        if deleted:
            return {"success": True, "message": "Record deleted"}
        return {"success": False, "error": "Record not found"}

    def save_location(self, user_id: int, lat: float, lng: float) -> dict:
        loc_id = self.location_dao.save_location(user_id, lat, lng)
        if loc_id:
            return {"success": True, "location_id": loc_id}
        return {"success": False, "error": "Database error"}
