from fastapi import HTTPException
from ..services.auth_service import AuthService
from ..schemas.user_schema import LoginRequest, RegisterRequest, ForgotPasswordSendOtpRequest, ForgotPasswordVerifyOtpRequest, ForgotPasswordResetRequest

class AuthController:
    def __init__(self, auth_service: AuthService = None):
        self.auth_service = auth_service if auth_service else AuthService()

    async def register(self, data: RegisterRequest):
        result = self.auth_service.register(data)
        if not result["success"]:
            raise HTTPException(status_code=400, detail=result.get("error"))
        return result

    async def login(self, request, data: LoginRequest):
        result = self.auth_service.login(request, data)
        if not result["success"]:
            raise HTTPException(status_code=401, detail=result.get("error"))
        return result

    async def logout(self, request, current_user: dict):
        return self.auth_service.logout(request, current_user)

    async def refresh(self, current_user: dict):
        return self.auth_service.refresh_token_session(current_user)

    async def forgot_send_otp(self, data: ForgotPasswordSendOtpRequest):
        result = self.auth_service.send_forgot_password_otp(data)
        if not result["success"]:
            raise HTTPException(status_code=400, detail=result.get("error"))
        return result

    async def forgot_verify_otp(self, data: ForgotPasswordVerifyOtpRequest):
        result = self.auth_service.verify_forgot_password_otp(data)
        if not result["success"]:
            raise HTTPException(status_code=400, detail=result.get("error"))
        return result

    async def forgot_reset_password(self, data: ForgotPasswordResetRequest):
        result = self.auth_service.reset_forgotten_password(data)
        if not result["success"]:
            raise HTTPException(status_code=400, detail=result.get("error"))
        return result

    async def google_auth(self, request, data: dict):
        result = self.auth_service.google_login(request, data.get("token"))
        if not result["success"]:
            raise HTTPException(status_code=401, detail=result.get("error"))
        return result

    async def apple_auth(self, request, data: dict):
        result = self.auth_service.apple_login(request, data.get("token"), data.get("user_info"))
        if not result["success"]:
            raise HTTPException(status_code=401, detail=result.get("error"))
        return result

    async def google_callback(self, request):
        result = await self.auth_service.google_callback(request)
        if not result["success"]:
            # For callback, we might want to redirect to login with error rather than raise HTTPException
            # but for now let's stick to the controller pattern
            raise HTTPException(status_code=401, detail=result.get("error"))
        
        from fastapi.responses import RedirectResponse
        import json
        import urllib.parse
        
        token = result["token"]
        user_json = json.dumps(result.get("user", {}))
        encoded_user = urllib.parse.quote(user_json)
        
        # Redirect to the frontend login page with the token and user data so Javascript can finalize it
        response = RedirectResponse(url=f"/login?token={token}&user={encoded_user}")
        return response
