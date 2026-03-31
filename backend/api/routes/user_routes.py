from fastapi import APIRouter, Depends, Body, HTTPException
from backend.services.user_service import UserService
from backend.core.security import login_required
from typing import Dict, Any

router = APIRouter(prefix="/api/user", tags=["User"])
user_service = UserService()

@router.get("/profile")
async def get_user_profile(current_user: dict = Depends(login_required)):
    result = user_service.get_profile(current_user["user_id"])
    if not result["success"]:
        raise HTTPException(status_code=404, detail=result["error"])
    return result

@router.put("/profile")
async def update_user_profile(
    data: dict = Body(...),
    current_user: dict = Depends(login_required)
):
    result = user_service.update_profile(current_user["user_id"], data)
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["error"])
    return result

@router.post("/appointments")
async def create_appointment(
    data: dict = Body(...),
    current_user: dict = Depends(login_required)
):
    # This logic uses userDao directly for appointment creation
    from backend.dao.user_dao import UserDao
    dao = UserDao()
    success = dao.create_appointment(
        current_user["user_id"],
        data.get("doctor_name"),
        data.get("doctor_specialty"),
        data.get("doctor_area"),
        data.get("doctor_city"),
        data.get("appointment_date"),
        data.get("appointment_time")
    )
    if success:
         return {"success": True, "message": "Appointment booked successfully"}
    raise HTTPException(status_code=500, detail="Failed to book appointment")
