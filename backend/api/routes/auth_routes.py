from fastapi import APIRouter, Depends, HTTPException, Body
from backend.models.dtos import LoginRequest, RegisterRequest, ForgotPasswordSendOtpRequest, ForgotPasswordVerifyOtpRequest, ForgotPasswordResetRequest
from backend.services.auth_service import AuthService
from backend.core.security import login_required
from typing import Dict, Any

router = APIRouter(prefix="/api/auth", tags=["Authentication"])
auth_service = AuthService()

@router.post("/register")
async def register(data: RegisterRequest):
    result = auth_service.register(data)
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["error"])
    return result

@router.post("/login")
async def login(data: LoginRequest):
    result = auth_service.login(data)
    if not result["success"]:
        raise HTTPException(status_code=401, detail=result["error"])
    return result

@router.post("/logout")
async def logout(current_user: dict = Depends(login_required)):
    return auth_service.logout(current_user["user_id"])

@router.post("/forgot-password/send-otp")
async def forgot_send_otp(data: ForgotPasswordSendOtpRequest):
    result = auth_service.send_forgot_password_otp(data)
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["error"])
    return result

@router.post("/forgot-password/verify-otp")
async def forgot_verify_otp(data: ForgotPasswordVerifyOtpRequest):
    result = auth_service.verify_forgot_password_otp(data)
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["error"])
    return result

@router.post("/forgot-password/reset")
async def forgot_reset_password(data: ForgotPasswordResetRequest):
    result = auth_service.reset_forgotten_password(data)
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["error"])
    return result

@router.post("/password/change")
async def change_password(
    data: dict = Body(...), 
    current_user: dict = Depends(login_required)
):
    result = auth_service.change_password(current_user["user_id"], data["old_password"], data["new_password"])
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["error"])
    return result
