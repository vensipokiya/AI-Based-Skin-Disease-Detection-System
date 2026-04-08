from ..dao.admin_dao import AdminDao
import json

class AdminService:
    def __init__(self, admin_dao=None):
        self.admin_dao = admin_dao if admin_dao else AdminDao()

    def _format_dates(self, data: list, fields: list):
        for item in data:
            for field in fields:
                val = item.get(field)
                if val:
                    if hasattr(val, 'isoformat'):
                        item[field] = val.isoformat()
                    else:
                        item[field] = str(val)
        return data

    def get_users_list(self) -> dict:
        users = self.admin_dao.get_all_users()
        return {"success": True, "users": self._format_dates(users, ["date_of_birth", "last_login", "created_at"])}

    def delete_user(self, uid: int) -> dict:
        if self.admin_dao.delete_user(uid):
            return {"success": True, "message": "User deleted"}
        return {"success": False, "error": "User not found"}

    def get_scans_list(self) -> dict:
        scans = self.admin_dao.get_all_scans()
        for s in scans:
            if s.get("remedies") and isinstance(s["remedies"], str):
                try:
                    s["remedies"] = json.loads(s["remedies"])
                except json.JSONDecodeError:
                    pass
        return {"success": True, "scans": self._format_dates(scans, ["scan_date"])}

    def get_medical_profiles(self) -> dict:
        profiles = self.admin_dao.get_all_medical_profiles()
        return {"success": True, "profiles": self._format_dates(profiles, ["created_at"])}

    def get_appointments(self) -> dict:
        appointments = self.admin_dao.get_all_appointments()
        from datetime import datetime, date, timedelta
        for a in appointments:
            dt, tm = a.get("appointment_date"), a.get("appointment_time")
            try:
                if isinstance(dt, date) and isinstance(tm, timedelta):
                    appointment_dt = datetime.combine(dt, datetime.min.time()) + tm
                    a["status"] = "Done" if datetime.now() >= appointment_dt else "Pending"
                else:
                    appointment_dt = datetime.strptime(f"{dt} {tm}", "%Y-%m-%d %H:%M:%S")
                    a["status"] = "Done" if datetime.now() >= appointment_dt else "Pending"
            except (ValueError, TypeError):
                a["status"] = "Pending"
        
        self._format_dates(appointments, ["appointment_date"])
        for a in appointments:
            if a.get("appointment_time"): a["appointment_time"] = str(a["appointment_time"])
        return {"success": True, "appointments": appointments}

    def get_logs(self) -> dict:
        logs = self.admin_dao.get_system_logs()
        for log in logs:
            if not log.get("action"):
                log["action"] = log.get("event_type", "Action")
        return {"success": True, "logs": self._format_dates(logs, ["timestamp"])}

    def clear_logs(self) -> dict:
        if self.admin_dao.clear_system_logs():
            return {"success": True, "message": "All system logs cleared."}
        return {"success": False, "error": "Failed to clear logs."}

    def get_login_history(self, page: int, limit: int, status: str, date: str, search: str = None) -> dict:
        offset = (page - 1) * limit
        history = self.admin_dao.get_login_history(offset, limit, status, date, search)
        return {"success": True, "history": self._format_dates(history, ["login_time", "logout_time"]), "page": page, "limit": limit}

    def get_user_login_history(self, user_id: int, page: int, limit: int, status: str, date: str) -> dict:
        offset = (page - 1) * limit
        history = self.admin_dao.get_user_login_history(user_id, offset, limit, status, date)
        return {"success": True, "history": self._format_dates(history, ["login_time", "logout_time"]), "page": page, "limit": limit}

    def force_logout(self, session_id: str) -> dict:
        if self.admin_dao.force_logout(session_id):
            return {"success": True, "message": "Session terminated and user logged out."}
        return {"success": False, "error": "Session not found."}

    def get_user_locations(self) -> dict:
        locations = self.admin_dao.get_all_user_locations()
        return {"success": True, "locations": self._format_dates(locations, ["timestamp"])}

    def get_otp_verifications(self) -> dict:
        otps = self.admin_dao.get_all_otp_verifications()
        return {"success": True, "otps": self._format_dates(otps, ["created_at", "expires_at"])}
