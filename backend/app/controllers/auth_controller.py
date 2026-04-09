from fastapi import HTTPException
from ..services.auth_service import AuthService
from ..schemas.user_schema import LoginRequest, RegisterRequest, ForgotPasswordSendOtpRequest, ForgotPasswordVerifyOtpRequest, ForgotPasswordResetRequest

class AuthController:
    """Controller for authentication-related endpoints (Login, Register, OAuth, OTP)."""
    
    def __init__(self, auth_service: AuthService = None):
        """Initializes the controller with an optional AuthService."""
        self.auth_service = auth_service if auth_service else AuthService()

    async def register(self, data: RegisterRequest):
        """Registers a new user account."""
        import anyio
        result = await anyio.to_thread.run_sync(self.auth_service.register, data)
        if not result["success"]:
            raise HTTPException(status_code=400, detail=result.get("error"))
        return result

    async def login(self, request, data: LoginRequest):
        """Authenticates a user and starts a session."""
        import anyio
        result = await anyio.to_thread.run_sync(self.auth_service.login, request, data)
        if not result["success"]:
            raise HTTPException(status_code=401, detail=result.get("error"))
        return result

    async def logout(self, request, current_user: dict):
        """Terminates the current user session."""
        import anyio
        return await anyio.to_thread.run_sync(self.auth_service.logout, request, current_user)

    async def refresh(self, current_user: dict):
        """Refreshes the session token for an active user."""
        import anyio
        return await anyio.to_thread.run_sync(self.auth_service.refresh_token_session, current_user)

    async def forgot_send_otp(self, data: ForgotPasswordSendOtpRequest):
        """Sends a password reset OTP to the user's email."""
        import anyio
        result = await anyio.to_thread.run_sync(self.auth_service.send_forgot_password_otp, data)
        if not result["success"]:
            raise HTTPException(status_code=400, detail=result.get("error"))
        return result

    async def forgot_verify_otp(self, data: ForgotPasswordVerifyOtpRequest):
        """Verifies a password reset OTP."""
        import anyio
        result = await anyio.to_thread.run_sync(self.auth_service.verify_forgot_password_otp, data)
        if not result["success"]:
            raise HTTPException(status_code=400, detail=result.get("error"))
        return result

    async def forgot_reset_password(self, data: ForgotPasswordResetRequest):
        """Resets the user's password after successful OTP verification."""
        import anyio
        result = await anyio.to_thread.run_sync(self.auth_service.reset_forgotten_password, data)
        if not result["success"]:
            raise HTTPException(status_code=400, detail=result.get("error"))
        return result

    async def google_auth(self, request, data: dict):
        """Handles Google OAuth login with an ID token."""
        import anyio
        result = await anyio.to_thread.run_sync(self.auth_service.google_login, request, data.get("token"))
        if not result["success"]:
            raise HTTPException(status_code=401, detail=result.get("error"))
        return result

    async def apple_auth(self, request, data: dict):
        """Handles Apple OAuth login with an ID token."""
        import anyio
        result = await anyio.to_thread.run_sync(self.auth_service.apple_login, request, data.get("token"), data.get("user_info"))
        if not result["success"]:
            raise HTTPException(status_code=401, detail=result.get("error"))
        return result

    async def google_callback(self, request):
        """Processes the Google OAuth callback redirect."""
        result = await self.auth_service.google_callback(request)
        if not result["success"]:
            raise HTTPException(status_code=401, detail=result.get("error"))
        
        from fastapi.responses import RedirectResponse
        import json
        import urllib.parse
        
        token = result["token"]
        user_json = json.dumps(result.get("user", {}))
        encoded_user = urllib.parse.quote(user_json)
        
        return RedirectResponse(url=f"/login?token={token}&user={encoded_user}")
