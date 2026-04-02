from ..dao.user_dao import UserDao
from typing import Optional, Dict, Any

class UserService:
    def __init__(self, user_dao=None):
        self.user_dao = user_dao if user_dao else UserDao()

    def get_profile(self, user_id: int) -> dict:
        user = self.user_dao.get_user_by_id(user_id)
        if not user:
             return {"success": False, "error": "User not found"}
        
        return {
            "success": True,
            "profile": {
                "id": user["id"],
                "first_name": user["first_name"],
                "last_name": user["last_name"],
                "email": user["email"],
                "contact_number": user["contact_number"],
                "age": user["age"],
                "gender": user["gender"],
                "date_of_birth": str(user["date_of_birth"]) if user["date_of_birth"] else None,
                "location": user.get("user_location", "Unknown"),
            }
        }
    
    def update_profile(self, user_id: int, data: dict) -> dict:
        updated = self.user_dao.update_user_profile(
            user_id,
            data.get("first_name"),
            data.get("last_name"),
            data.get("contact_number"),
            data.get("date_of_birth"),
            data.get("age"),
            data.get("gender"),
            data.get("location", "Unknown")
        )
        if updated:
             return {"success": True, "message": "Profile updated successfully"}
        return {"success": False, "error": "Update failed"}

    def create_appointment(self, user_id: int, data: dict) -> dict:
        success = self.user_dao.create_appointment(
            user_id,
            data.get("doctor_name"),
            data.get("doctor_specialty"),
            data.get("doctor_area"),
            data.get("doctor_city"),
            data.get("appointment_date"),
            data.get("appointment_time")
        )
        if success:
            return {"success": True, "message": "Appointment booked successfully"}
        return {"success": False, "error": "Failed to save appointment to database."}
