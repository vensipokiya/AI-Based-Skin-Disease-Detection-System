from fastapi import HTTPException
from ..services.admin_service import AdminService

class AdminController:
    def __init__(self, admin_service: AdminService = None):
        self.admin_service = admin_service if admin_service else AdminService()

    async def get_all_users(self):
        return self.admin_service.get_users_list()

    async def delete_user(self, uid: int):
        result = self.admin_service.delete_user(uid)
        if not result["success"]:
            raise HTTPException(status_code=404, detail=result.get("error"))
        return result

    async def get_all_scans(self):
        return self.admin_service.get_scans_list()

    async def get_all_medical_profiles(self):
        return self.admin_service.get_medical_profiles()

    async def get_all_appointments(self):
        return self.admin_service.get_appointments()

    async def get_system_logs(self):
        return self.admin_service.get_logs()

    async def get_login_history(self, page: int, limit: int, status: str, date: str, search: str):
        return self.admin_service.get_login_history(page, limit, status, date, search)

    async def get_user_login_history(self, user_id: int, page: int, limit: int, status: str, date: str):
        return self.admin_service.get_user_login_history(user_id, page, limit, status, date)

    async def force_logout(self, session_id: str):
        result = self.admin_service.force_logout(session_id)
        if not result["success"]:
            raise HTTPException(status_code=400, detail=result.get("error"))
        return result
