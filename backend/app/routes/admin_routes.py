from fastapi import APIRouter, Depends, HTTPException
from ..controllers.admin_controller import AdminController
from ..middleware.auth_middleware import login_required
from ..utils.websocket import manager
from ..config.database import db_singleton
import mysql.connector

router = APIRouter(prefix="/api/admin", tags=["Admin"])
admin_controller = AdminController()

_ALLOWED_TABLES = frozenset([
    "users", "scan_history", "medical_profiles",
    "doctor_appointments", "system_logs",
    "user_locations", "otp_verification", "user_login_history"
])

DB_CONN_ERROR = "Database connection failed"


def admin_required(user: dict = Depends(login_required)):
    if user.get("role") != "Admin":
        raise HTTPException(status_code=403, detail="Admin root access required.")
    return user


@router.get("/users")
async def get_all_users(admin: dict = Depends(admin_required)):
    return admin_controller.get_all_users()


@router.delete("/delete/{table}/{id}")
async def delete_record(table: str, id: int, admin: dict = Depends(admin_required)):
    if table not in _ALLOWED_TABLES:
        raise HTTPException(status_code=400, detail="Invalid table")

    def _do_delete():
        conn = db_singleton.get_connection()
        if not conn:
            raise Exception(DB_CONN_ERROR)
        try:
            cursor = conn.cursor()
            cursor.execute(f"DELETE FROM {table} WHERE id=%s", (id,))
            conn.commit()
        except mysql.connector.Error as err:
            conn.rollback()
            raise err
        finally:
            conn.close()

    import anyio
    try:
        await anyio.to_thread.run_sync(_do_delete)
    except Exception as e:
        raise HTTPException(status_code=500, detail="Database deletion failed.")

    await manager.broadcast({"action": "delete", "table": table, "id": id})
    return {"status": "success", "message": "Deleted successfully"}


@router.delete("/users/{uid}")
async def delete_user(uid: int, admin: dict = Depends(admin_required)):
    return admin_controller.delete_user(uid)


@router.get("/scans")
async def get_all_scans(admin: dict = Depends(admin_required)):
    return admin_controller.get_all_scans()


@router.get("/medical-profiles")
async def get_all_medical_profiles(admin: dict = Depends(admin_required)):
    return admin_controller.get_all_medical_profiles()


@router.get("/appointments")
async def get_all_appointments(admin: dict = Depends(admin_required)):
    return admin_controller.get_all_appointments()


@router.get("/logs")
async def get_system_logs(admin: dict = Depends(admin_required)):
    return admin_controller.get_system_logs()


@router.delete("/logs")
async def clear_system_logs(admin: dict = Depends(admin_required)):
    return admin_controller.clear_system_logs()


@router.get("/login-history")
async def get_login_history(
    page: int = 1,
    limit: int = 50,
    status: str = None,
    date: str = None,
    search: str = None,
    admin: dict = Depends(admin_required)
):
    return admin_controller.get_login_history(page, limit, status, date, search)


@router.get("/user-history/{user_id}")
async def get_user_login_history(
    user_id: int,
    page: int = 1,
    limit: int = 50,
    status: str = None,
    date: str = None,
    admin: dict = Depends(admin_required)
):
    return admin_controller.get_user_login_history(user_id, page, limit, status, date)


@router.post("/force-logout/{session_id}")
async def force_logout(session_id: str, admin: dict = Depends(admin_required)):
    return admin_controller.force_logout(session_id)


@router.get("/user-locations")
async def get_user_locations(admin: dict = Depends(admin_required)):
    return admin_controller.get_user_locations()


@router.get("/otp-verifications")
async def get_otp_verifications(admin: dict = Depends(admin_required)):
    return admin_controller.get_otp_verifications()
