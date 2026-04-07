from fastapi import APIRouter, Depends, HTTPException
from ..controllers.admin_controller import AdminController
from ..middleware.auth_middleware import login_required
from ..utils.websocket import manager
from ..config.database import db_singleton

router = APIRouter(prefix="/api/admin", tags=["Admin"])
admin_controller = AdminController()

def admin_required(user: dict = Depends(login_required)):
    if user.get("role") != "Admin":
        raise HTTPException(status_code=403, detail="Admin root access required.")
    return user

@router.get("/users")
async def get_all_users(admin: dict = Depends(admin_required)):
    return await admin_controller.get_all_users()

@router.delete("/delete/{table}/{id}")
async def delete_record(table: str, id: int, admin: dict = Depends(admin_required)):
    ALLOWED_TABLES = ["users", "scan_history", "medical_profiles", "doctor_appointments", "system_logs", "user_locations", "otp_verification", "user_login_history"]
    if table not in ALLOWED_TABLES:
        raise HTTPException(status_code=400, detail="Invalid table")

    conn = db_singleton.get_connection()
    if not conn:
        raise HTTPException(status_code=500, detail="Database connection failed")
    try:
        cursor = conn.cursor()
        cursor.execute(f"DELETE FROM {table} WHERE id=%s", (id,))
        conn.commit()
    finally:
        conn.close()

    # Broadcast to all clients
    await manager.broadcast({
        "action": "delete",
        "table": table,
        "id": id
    })

    return {"status": "success", "message": "Deleted successfully"}

@router.delete("/users/{uid}")
async def delete_user(uid: int, admin: dict = Depends(admin_required)):
    return await admin_controller.delete_user(uid)

@router.get("/scans")
async def get_all_scans(admin: dict = Depends(admin_required)):
    return await admin_controller.get_all_scans()

@router.get("/medical-profiles")
async def get_all_medical_profiles(admin: dict = Depends(admin_required)):
    return await admin_controller.get_all_medical_profiles()

@router.get("/appointments")
async def get_all_appointments(admin: dict = Depends(admin_required)):
    return await admin_controller.get_all_appointments()

@router.get("/logs")
async def get_system_logs(admin: dict = Depends(admin_required)):
    return await admin_controller.get_system_logs()

@router.get("/login-history")
async def get_login_history(
    page: int = 1, 
    limit: int = 50, 
    status: str = None, 
    date: str = None, 
    search: str = None,
    admin: dict = Depends(admin_required)
):
    return await admin_controller.get_login_history(page, limit, status, date, search)

@router.get("/user-history/{user_id}")
async def get_user_login_history(
    user_id: int, 
    page: int = 1, 
    limit: int = 50, 
    status: str = None, 
    date: str = None, 
    admin: dict = Depends(admin_required)
):
    return await admin_controller.get_user_login_history(user_id, page, limit, status, date)

@router.post("/force-logout/{session_id}")
async def force_logout(session_id: str, admin: dict = Depends(admin_required)):
    return await admin_controller.force_logout(session_id)

@router.get("/user-locations")
async def get_user_locations(admin: dict = Depends(admin_required)):
    return await admin_controller.get_user_locations()

@router.get("/otp-verifications")
async def get_otp_verifications(admin: dict = Depends(admin_required)):
    return await admin_controller.get_otp_verifications()
