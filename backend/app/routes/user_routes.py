from fastapi import APIRouter, Depends, Body, HTTPException
from fastapi.responses import JSONResponse
from ..services.user_service import UserService
from ..middleware.auth_middleware import login_required

router = APIRouter(prefix="/api/user", tags=["User"])
user_service = UserService()

@router.get("/profile")
def get_user_profile(current_user: dict = Depends(login_required)):
    """Fetches the profile for the currently authenticated user."""
    result = user_service.get_profile(current_user["user_id"])
    if not result["success"]:
        raise HTTPException(status_code=404, detail=result["error"])
    return result

@router.put("/profile")
def update_user_profile(
    data: dict = Body(...),
    current_user: dict = Depends(login_required)
):
    """Updates user profile information using the provided body data."""
    result = user_service.update_profile(current_user["user_id"], data)
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["error"])
    return result

@router.post("/appointments")
def create_appointment(
    data: dict = Body(...),
    current_user: dict = Depends(login_required)
):
    """Saves a new dermatologist appointment to the user's medical history."""
    result = user_service.create_appointment(current_user["user_id"], data)
    if not result["success"]:
        return JSONResponse(status_code=500, content=result)
    return result
