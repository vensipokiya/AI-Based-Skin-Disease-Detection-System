from fastapi import HTTPException
from ..services.scan_service import ScanService

class ScanController:
    def __init__(self, scan_service: ScanService = None):
        self.scan_service = scan_service if scan_service else ScanService()

    async def get_scan_history(self, user_id: int):
        return self.scan_service.get_history(user_id)

    async def delete_scan_record(self, scan_id: int, user_id: int):
        result = self.scan_service.delete_record(scan_id, user_id)
        if not result["success"]:
            raise HTTPException(status_code=404, detail=result.get("error"))
        return result

    async def save_user_location(self, user_id: int, lat: float, lng: float, location_name: str = None):
        if lat is None or lng is None:
            raise HTTPException(status_code=400, detail="Latitude and Longitude are required.")
        return self.scan_service.save_location(user_id, lat, lng, location_name)
