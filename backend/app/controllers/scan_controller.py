from fastapi import HTTPException
from ..services.scan_service import ScanService

class ScanController:
    """Controller for managing user scan history and location data."""
    def __init__(self, scan_service: ScanService = None):
        """Initializes the controller with the Scan service."""
        self.scan_service = scan_service if scan_service else ScanService()

    async def get_scan_history(self, user_id: int):
        """Retrieves the complete scan history and statistics for a user."""
        return self.scan_service.get_history(user_id)

    async def delete_scan_record(self, scan_id: int, user_id: int):
        """Deletes a specific scan record from the user's history."""
        result = self.scan_service.delete_record(scan_id, user_id)
        if not result["success"]:
            raise HTTPException(status_code=404, detail=result.get("error"))
        return result

    async def save_user_location(self, user_id: int, lat: float, lng: float, location_name: str = None):
        """Updates or saves the user's current geographic location for specialist search."""
        if lat is None or lng is None:
            raise HTTPException(status_code=400, detail="Latitude and Longitude are required.")
        return self.scan_service.save_location(user_id, lat, lng, location_name)
