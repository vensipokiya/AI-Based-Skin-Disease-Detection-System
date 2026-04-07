from fastapi import APIRouter, Depends, Body, Request
from ..controllers.auth_controller import AuthController
from ..schemas.user_schema import LoginRequest, RegisterRequest, ForgotPasswordSendOtpRequest, ForgotPasswordVerifyOtpRequest, ForgotPasswordResetRequest
from ..middleware.auth_middleware import login_required
from ..utils.oauth import oauth

router = APIRouter(prefix="/api/auth", tags=["Authentication"])
auth_controller = AuthController()

@router.post("/register")
async def register(data: RegisterRequest):
    return await auth_controller.register(data)

@router.post("/login")
async def login(request: Request, data: LoginRequest):
    return await auth_controller.login(request, data)

@router.post("/logout")
async def logout(request: Request, current_user: dict = Depends(login_required)):
    return await auth_controller.logout(request, current_user)

@router.post("/refresh")
async def refresh(current_user: dict = Depends(login_required)):
    return await auth_controller.refresh(current_user)

@router.post("/forgot-password/send-otp")
async def forgot_send_otp(data: ForgotPasswordSendOtpRequest):
    return await auth_controller.forgot_send_otp(data)

@router.post("/forgot-password/verify-otp")
async def forgot_verify_otp(data: ForgotPasswordVerifyOtpRequest):
    return await auth_controller.forgot_verify_otp(data)

@router.post("/forgot-password/reset")
async def forgot_reset_password(data: ForgotPasswordResetRequest):
    return await auth_controller.forgot_reset_password(data)

@router.post("/google")
async def google_auth(data: dict, request: Request):
    return auth_controller.google_auth(request, data.get("token"))

@router.post("/apple")
async def apple_auth(data: dict, request: Request):
    return auth_controller.apple_auth(request, data.get("token"), data.get("user"))

@router.get("/google/login")
async def google_login(request: Request):
    redirect_uri = request.url_for('google_callback')
    return await oauth.google.authorize_redirect(request, str(redirect_uri))

@router.get("/google/callback", name="google_callback")
async def google_callback(request: Request):
    return await auth_controller.google_callback(request)
