from fastapi import APIRouter, Depends, Request, HTTPException
from fastapi.responses import JSONResponse, RedirectResponse
from authlib.integrations.starlette_client import OAuth, OAuthError
from backend.core.security import SecurityService, login_required
from backend.dao.user_dao import UserDao
import os
import json

router = APIRouter(prefix="/api/admin", tags=["Admin"])
oauth = OAuth()
user_dao = UserDao()

# Google OAuth Configuration
GOOGLE_CLIENT_ID = os.environ.get("GOOGLE_CLIENT_ID", "YOUR_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.environ.get("GOOGLE_CLIENT_SECRET", "YOUR_CLIENT_SECRET")

oauth.register(
    name='google',
    client_id=GOOGLE_CLIENT_ID,
    client_secret=GOOGLE_CLIENT_SECRET,
    server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
    client_kwargs={'scope': 'openid email profile'}
)

ADMIN_WHITELIST = ["nakshi@gmail.com"]

@router.get("/login")
async def admin_login(request: Request):
    # This generates the correct absolute URL for the callback
    redirect_uri = request.url_for('admin_auth_callback')
    return await oauth.google.authorize_redirect(request, redirect_uri)

@router.get("/auth")
async def admin_auth_callback(request: Request):
    try:
        token = await oauth.google.authorize_access_token(request)
        user_info = token.get("userinfo") or await oauth.google.parse_id_token(request, token)
        email = user_info.get("email")

        if not email or email.lower() not in ADMIN_WHITELIST:
             return JSONResponse(status_code=403, content={"error": "Unauthorized email"})

        access_token = SecurityService.create_access_token({"email": email, "role": "Admin"})
        return RedirectResponse(url=f"/static/admin.html?token={access_token}")
    except OAuthError as error:
        return JSONResponse(status_code=400, content={"error": error.error})

def admin_required(user: dict = Depends(login_required)):
    if user.get("role") != "Admin":
        raise HTTPException(status_code=403, detail="Admin root access required.")
    return user

@router.get("/users")
async def get_all_users(admin: dict = Depends(admin_required)):
    conn = user_dao.db.get_connection()
    if not conn: raise HTTPException(status_code=500, detail="Database connection failed")
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT id, first_name, last_name, email, age, date_of_birth, gender, contact_number, user_location, role, is_active, is_logged_in FROM users")
        return {"success": True, "users": cursor.fetchall()}
    finally:
        if conn: conn.close()

@router.delete("/users/{uid}")
async def delete_user(uid: int, admin: dict = Depends(admin_required)):
    conn = user_dao.db.get_connection()
    if not conn: raise HTTPException(status_code=500, detail="Database connection failed")
    try:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM users WHERE id = %s", (uid,))
        conn.commit()
        return {"success": True, "message": "User deleted"}
    finally:
        if conn: conn.close()

@router.get("/scans")
async def get_all_scans(admin: dict = Depends(admin_required)):
    conn = user_dao.db.get_connection()
    if not conn: raise HTTPException(status_code=500, detail="Database connection failed")
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM scan_history ORDER BY scan_date DESC LIMIT 500")
        scans = cursor.fetchall()
        for s in scans:
            if s.get("scan_date"): s["scan_date"] = s["scan_date"].isoformat()
            if s.get("remedies") and isinstance(s["remedies"], str): 
                try: s["remedies"] = json.loads(s["remedies"]) 
                except: pass
        return {"success": True, "scans": scans}
    finally:
        if conn: conn.close()

@router.get("/medical-profiles")
async def get_all_medical_profiles(admin: dict = Depends(admin_required)):
    conn = user_dao.db.get_connection()
    if not conn: raise HTTPException(status_code=500, detail="Database connection failed")
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT mp.*, CONCAT(u.first_name, ' ', u.last_name) as patient_name 
            FROM medical_profiles mp 
            JOIN users u ON mp.user_id = u.id
        """)
        profiles = cursor.fetchall()
        for p in profiles:
            if p.get("created_at"): p["created_at"] = p["created_at"].isoformat()
        return {"success": True, "profiles": profiles}
    finally:
        if conn: conn.close()

@router.get("/appointments")
async def get_all_appointments(admin: dict = Depends(admin_required)):
    conn = user_dao.db.get_connection()
    if not conn: raise HTTPException(status_code=500, detail="Database connection failed")
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT a.*, u.first_name, u.last_name, u.email 
            FROM doctor_appointments a 
            JOIN users u ON a.user_id = u.id
        """)
        appointments = cursor.fetchall()
        for a in appointments:
            if a.get("appointment_date"): a["appointment_date"] = a["appointment_date"].isoformat()
            if a.get("appointment_time"): a["appointment_time"] = str(a["appointment_time"])
        return {"success": True, "appointments": appointments}
    finally:
        if conn: conn.close()

@router.get("/logs")
async def get_system_logs(admin: dict = Depends(admin_required)):
    conn = user_dao.db.get_connection()
    if not conn: raise HTTPException(status_code=500, detail="Database connection failed")
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT sl.*, u.email as user_email 
            FROM system_logs sl 
            LEFT JOIN users u ON sl.user_id = u.id 
            ORDER BY sl.timestamp DESC LIMIT 200
        """)
        logs = cursor.fetchall()
        for l in logs:
            if l.get("timestamp"): l["timestamp"] = l["timestamp"].isoformat()
            if not l.get("action"): l["action"] = l.get("event_type", "Action")
        return {"success": True, "logs": logs}
    finally:
        if conn: conn.close()

@router.get("/user-locations")
async def get_user_locations(admin: dict = Depends(admin_required)):
    conn = user_dao.db.get_connection()
    if not conn: raise HTTPException(status_code=500, detail="Database connection failed")
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT ul.*, CONCAT(u.first_name, ' ', u.last_name) as patient_name, u.email 
            FROM user_locations ul 
            JOIN users u ON ul.uid = u.id 
            ORDER BY ul.timestamp DESC
        """)
        locations = cursor.fetchall()
        for l in locations:
            if l.get("timestamp"): l["timestamp"] = l["timestamp"].isoformat()
        return {"success": True, "locations": locations}
    finally:
        if conn: conn.close()

@router.get("/otp-verifications")
async def get_otp_verifications(admin: dict = Depends(admin_required)):
    conn = user_dao.db.get_connection()
    if not conn: raise HTTPException(status_code=500, detail="Database connection failed")
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM otp_verification ORDER BY created_at DESC")
        otps = cursor.fetchall()
        for o in otps:
            if o.get("created_at"): o["created_at"] = o["created_at"].isoformat()
            if o.get("expires_at"): o["expires_at"] = o["expires_at"].isoformat()
        return {"success": True, "otps": otps}
    finally:
        if conn: conn.close()
