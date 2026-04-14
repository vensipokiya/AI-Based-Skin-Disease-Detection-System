from fastapi import APIRouter, Depends, Request
from ..controllers.auth_controller import AuthController
from ..schemas.user_schema import (
    LoginRequest, RegisterRequest,
    ForgotPasswordSendOtpRequest, ForgotPasswordVerifyOtpRequest, ForgotPasswordResetRequest
)
from ..middleware.auth_middleware import login_required
from ..utils.oauth import oauth

router = APIRouter(prefix="/api/auth", tags=["Authentication"])
auth_controller = AuthController()


@router.post("/register")
async def register(data: RegisterRequest):
    """Create a new user account."""
    return await auth_controller.register(data)


@router.post("/login")
async def login(request: Request, data: LoginRequest):
    """Authenticate user credentials and return a JWT."""
    return await auth_controller.login(request, data)


@router.post("/logout")
async def logout(request: Request, current_user: dict = Depends(login_required)):
    """End the authenticated user's session."""
    return await auth_controller.logout(request, current_user)


@router.post("/refresh")
async def refresh(current_user: dict = Depends(login_required)):
    """Refresh the JWT session for an active user."""
    return await auth_controller.refresh(current_user)


@router.post("/forgot-password/send-otp")
async def forgot_send_otp(data: ForgotPasswordSendOtpRequest):
    """Send a password-reset OTP to the user's email."""
    return await auth_controller.forgot_send_otp(data)


@router.post("/forgot-password/verify-otp")
async def forgot_verify_otp(data: ForgotPasswordVerifyOtpRequest):
    """Verify a password-reset OTP code."""
    return await auth_controller.forgot_verify_otp(data)


@router.post("/forgot-password/reset")
async def forgot_reset_password(data: ForgotPasswordResetRequest):
    """Reset the user's password after OTP verification."""
    return await auth_controller.forgot_reset_password(data)


@router.post("/google")
async def google_auth(data: dict, request: Request):
    """Process a Google ID token for direct OAuth login."""
    return await auth_controller.google_auth(request, data)


@router.post("/apple")
async def apple_auth(data: dict, request: Request):
    """Process an Apple ID token and user info for OAuth login."""
    return await auth_controller.apple_auth(request, data)


@router.get("/google/login")
async def google_login(request: Request):
    """Initiate the Google OAuth redirect flow."""
    redirect_uri = request.url_for("google_callback")
    return await oauth.google.authorize_redirect(request, str(redirect_uri))


@router.get("/google/callback", name="google_callback")
async def google_callback(request: Request):
    """Handle the Google OAuth redirect callback."""
    return await auth_controller.google_callback(request)
