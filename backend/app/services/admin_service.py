from ..dao.admin_dao import AdminDao
import json

class AdminService:
    def __init__(self, admin_dao=None):
        self.admin_dao = admin_dao if admin_dao else AdminDao()

    def get_users_list(self) -> dict:
        users = self.admin_dao.get_all_users()
        return {"success": True, "users": users}

    def delete_user(self, uid: int) -> dict:
        if self.admin_dao.delete_user(uid):
            return {"success": True, "message": "User deleted"}
        return {"success": False, "error": "User not found"}

    def get_scans_list(self) -> dict:
        scans = self.admin_dao.get_all_scans()
        for s in scans:
            if s.get("scan_date"): s["scan_date"] = s["scan_date"].isoformat()
            if s.get("remedies") and isinstance(s["remedies"], str): 
                try: s["remedies"] = json.loads(s["remedies"]) 
                except: pass
        return {"success": True, "scans": scans}

    def get_medical_profiles(self) -> dict:
        profiles = self.admin_dao.get_all_medical_profiles()
        for p in profiles:
            if p.get("created_at"): p["created_at"] = p["created_at"].isoformat()
        return {"success": True, "profiles": profiles}

    def get_appointments(self) -> dict:
        appointments = self.admin_dao.get_all_appointments()
        from datetime import datetime, date, timedelta
        for a in appointments:
            dt = a.get("appointment_date")
            tm = a.get("appointment_time")
            
            # Calculate dynamic status
            try:
                # Attempt to combine date and time if available
                if isinstance(dt, date) and isinstance(tm, timedelta):
                    appointment_dt = datetime.combine(dt, datetime.min.time()) + tm
                    a["status"] = "Done" if datetime.now() >= appointment_dt else "Pending"
                else:
                    appointment_dt = datetime.strptime(f"{dt} {tm}", "%Y-%m-%d %H:%M:%S")
                    a["status"] = "Done" if datetime.now() >= appointment_dt else "Pending"
            except Exception:
                a["status"] = "Pending"

            if a.get("appointment_date"): a["appointment_date"] = a["appointment_date"].isoformat() if hasattr(a["appointment_date"], 'isoformat') else str(a["appointment_date"])
            if a.get("appointment_time"): a["appointment_time"] = str(a["appointment_time"])
        return {"success": True, "appointments": appointments}

    def get_logs(self) -> dict:
        logs = self.admin_dao.get_system_logs()
        for l in logs:
            if l.get("timestamp"): l["timestamp"] = l["timestamp"].isoformat()
            if not l.get("action"): l["action"] = l.get("event_type", "Action")
        return {"success": True, "logs": logs}

    def get_login_history(self, page: int, limit: int, status: str, date: str, search: str = None) -> dict:
        offset = (page - 1) * limit
        history = self.admin_dao.get_login_history(offset, limit, status, date, search)
        for h in history:
            if h.get("login_time"): h["login_time"] = h["login_time"].isoformat()
            if h.get("logout_time"): h["logout_time"] = h["logout_time"].isoformat()
        return {"success": True, "history": history, "page": page, "limit": limit}

    def get_user_login_history(self, user_id: int, page: int, limit: int, status: str, date: str) -> dict:
        offset = (page - 1) * limit
        history = self.admin_dao.get_user_login_history(user_id, offset, limit, status, date)
        for h in history:
            if h.get("login_time"): h["login_time"] = h["login_time"].isoformat()
            if h.get("logout_time"): h["logout_time"] = h["logout_time"].isoformat()
        return {"success": True, "history": history, "page": page, "limit": limit}

    def force_logout(self, session_id: str) -> dict:
        if self.admin_dao.force_logout(session_id):
            return {"success": True, "message": "Session terminated and user logged out."}
        return {"success": False, "error": "Session not found."}

    def get_user_locations(self) -> dict:
        locations = self.admin_dao.get_all_user_locations()
        for l in locations:
            if l.get("timestamp"): l["timestamp"] = l["timestamp"].isoformat()
        return {"success": True, "locations": locations}

    def get_otp_verifications(self) -> dict:
        otps = self.admin_dao.get_all_otp_verifications()
        for o in otps:
            if o.get("created_at"): o["created_at"] = o["created_at"].isoformat()
            if o.get("expires_at"): o["expires_at"] = o["expires_at"].isoformat()
        return {"success": True, "otps": otps}
