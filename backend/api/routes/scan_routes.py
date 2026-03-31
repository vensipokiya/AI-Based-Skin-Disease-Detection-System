from fastapi import APIRouter, Depends, HTTPException, Body
from backend.services.scan_service import ScanService
from backend.core.security import login_required
from typing import Dict, Any

router = APIRouter(prefix="/api/scan", tags=["Scans"])
scan_service = ScanService()

@router.get("/history")
async def get_scan_history(current_user: dict = Depends(login_required)):
    return scan_service.get_history(current_user["user_id"])

@router.delete("/history/{scan_id}")
async def delete_scan_record(scan_id: int, current_user: dict = Depends(login_required)):
    result = scan_service.delete_record(scan_id, current_user["user_id"])
    if not result["success"]:
        raise HTTPException(status_code=404, detail=result["error"])
    return result

@router.post("/location")
async def save_user_location(
    data: dict = Body(...),
    current_user: dict = Depends(login_required)
):
    lat = data.get("latitude")
    lng = data.get("longitude")
    loc_name = data.get("location_name")
    
    if lat is None or lng is None:
        raise HTTPException(status_code=400, detail="Latitude and Longitude are required.")
        
    return scan_service.save_location(current_user["user_id"], lat, lng, loc_name)
