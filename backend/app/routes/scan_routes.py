from fastapi import APIRouter, Depends, Body
from ..controllers.scan_controller import ScanController
from ..middleware.auth_middleware import login_required

router = APIRouter(prefix="/api/scan", tags=["Scans"])
scan_controller = ScanController()

@router.get("/history")
async def get_scan_history(current_user: dict = Depends(login_required)):
    return await scan_controller.get_scan_history(current_user["user_id"])

@router.delete("/history/{scan_id}")
async def delete_scan_record(scan_id: int, current_user: dict = Depends(login_required)):
    return await scan_controller.delete_scan_record(scan_id, current_user["user_id"])

@router.post("/location")
async def save_user_location(
    data: dict = Body(...),
    current_user: dict = Depends(login_required)
):
    lat = data.get("latitude")
    lng = data.get("longitude")
    location_name = data.get("location_name")
    return await scan_controller.save_user_location(current_user["user_id"], lat, lng, location_name)
