from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, RedirectResponse
from starlette.middleware.sessions import SessionMiddleware
from contextlib import asynccontextmanager
import os
import asyncio
import httpx
import math
import json
import urllib.parse

from .config.database import DatabaseSingleton
from .utils.logger import get_logger
from .config.settings import settings
from .routes import auth_routes, user_routes, scan_routes, predict_routes, admin_routes
from .services.predict_service import PredictService
from .utils.websocket import manager

logger = get_logger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Pre-initialize DB
    db = DatabaseSingleton()
    if db.get_connection():
        logger.info("[OK] MySQL Database connected.")
    else:
        logger.warning("[WARNING] MySQL connection failed.")
        
    # Pre-load AI model assets
    try:
        PredictService.load_assets()
        logger.info("[OK] AI Model & Classes pre-loaded.")
    except Exception as e:
        logger.error(f"[ERROR] Failed to pre-load AI assets: {str(e)}")
        
    yield

app = FastAPI(title="DermaCare AI", version="2.0.0", lifespan=lifespan)

# CORS Configuration
allowed_origins = os.getenv("ALLOWED_ORIGINS", "*").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(SessionMiddleware, secret_key=settings.SECRET_KEY)

# ── Path Resolution ─────────────────────────────────────────────────────────
WORKING_DIR = os.getcwd()
FRONTEND_DIR = os.path.join(WORKING_DIR, "frontend")
UPLOADS_ROOT = os.path.join(WORKING_DIR, "backend", "app", "uploads")
USER_UPLOADS = os.path.join(UPLOADS_ROOT, "user_uploads")

# Ensure upload directories exist
os.makedirs(USER_UPLOADS, exist_ok=True)

# ── Static File Mounts ──────────────────────────────────────────────────────
app.mount("/static/user", StaticFiles(directory=os.path.join(FRONTEND_DIR, "user", "static")), name="static_user")
app.mount("/admin/static", StaticFiles(directory=os.path.join(FRONTEND_DIR, "admin", "static")), name="static_admin")
app.mount("/shared/static", StaticFiles(directory=os.path.join(FRONTEND_DIR, "shared", "static")), name="static_shared")
app.mount("/uploads", StaticFiles(directory=UPLOADS_ROOT), name="uploads")

# ── Template Configuration ──────────────────────────────────────────────────
templates = Jinja2Templates(
    directory=[
        os.path.join(FRONTEND_DIR, "user", "templates"),
        os.path.join(FRONTEND_DIR, "admin", "templates"),
        os.path.join(FRONTEND_DIR, "shared", "templates"),
    ]
)

# ── API Routers ─────────────────────────────────────────────────────────────
app.include_router(auth_routes.router)
app.include_router(user_routes.router)
app.include_router(scan_routes.router)
app.include_router(predict_routes.router)
app.include_router(admin_routes.router)

# ── User Page Routes ────────────────────────────────────────────────────────
@app.get("/", response_class=HTMLResponse)
async def read_index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/login", response_class=HTMLResponse)
async def read_login(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})

@app.get("/register", response_class=HTMLResponse)
async def read_register(request: Request):
    return templates.TemplateResponse("register.html", {"request": request})

@app.get("/detect", response_class=HTMLResponse)
async def read_detect(request: Request):
    return templates.TemplateResponse("detection.html", {"request": request})

@app.get("/scan-result", response_class=HTMLResponse)
async def read_scan_result(request: Request):
    return templates.TemplateResponse("scan_result.html", {"request": request})

@app.get("/history", response_class=HTMLResponse)
async def read_history(request: Request):
    return templates.TemplateResponse("history.html", {"request": request})

@app.get("/profile", response_class=HTMLResponse)
async def read_profile(request: Request):
    return templates.TemplateResponse("profile.html", {"request": request})

@app.get("/about", response_class=HTMLResponse)
async def read_about(request: Request):
    return templates.TemplateResponse("about_us.html", {"request": request})

@app.get("/forgot-password", response_class=HTMLResponse)
async def read_forgot(request: Request):
    return templates.TemplateResponse("forgot_pass.html", {"request": request})

@app.get("/nearby", response_class=HTMLResponse)
async def read_nearby(request: Request):
    return templates.TemplateResponse("nearby_dermatologist.html", {"request": request})

@app.get("/booking", response_class=HTMLResponse)
async def read_booking(request: Request):
    return templates.TemplateResponse("booking_appointment.html", {"request": request})

@app.get("/confirm-booking", response_class=HTMLResponse)
async def read_confirm_booking(request: Request):
    return templates.TemplateResponse("confirm_booking.html", {"request": request})

# ── Admin Page Route ────────────────────────────────────────────────────────
@app.get("/admin", response_class=HTMLResponse)
async def read_admin(request: Request):
    return templates.TemplateResponse("dashboard.html", {"request": request})

# ── Nearby Doctors Proxy ──────────────────────────────────────────────────
@app.get("/api/nearby-doctors")
async def nearby_doctors(lat: float, lng: float):
    """Proxy endpoint: searches Nominatim in parallel for faster results."""
    keywords = ["dermatologist", "skin clinic", "dermatology hospital", "skin specialist", "cosmetologist"]
    all_results = []
    seen_names = set()
    headers = {"User-Agent": "DermaCareAI/2.0 (student-project)"}
    
    # Tighten viewbox for better proximity (approx 20km radius)
    view_margin = 0.2
    
    async with httpx.AsyncClient(timeout=12.0, headers=headers) as client:
        tasks = []
        for kw in keywords:
            url = (
                f"https://nominatim.openstreetmap.org/search"
                f"?q={kw}&format=json&limit=15&addressdetails=1"
                f"&viewbox={lng-view_margin},{lat+view_margin},{lng+view_margin},{lat-view_margin}&bounded=1"
            )
            tasks.append(client.get(url))
        
        responses = await asyncio.gather(*tasks, return_exceptions=True)
        for resp in responses:
            if isinstance(resp, httpx.Response) and resp.status_code == 200:
                for item in resp.json():
                    name = item.get("display_name", "").split(",")[0].strip()
                    if not name or name.lower() in seen_names:
                        continue
                    seen_names.add(name.lower())
                    
                    addr = item.get("address", {})
                    city = addr.get("city") or addr.get("town") or addr.get("village") or addr.get("suburb") or ""
                    
                    all_results.append({
                        "name": name,
                        "lat": float(item["lat"]),
                        "lon": float(item["lon"]),
                        "city": city,
                        "street": addr.get("road", ""),
                        "type": item.get("type", "doctor"),
                    })

    def haversine(lat1, lon1, lat2, lon2):
        r_earth = 6371 # km
        phi1, phi2 = math.radians(lat1), math.radians(lat2)
        d_phi = math.radians(lat2 - lat1)
        d_lambda = math.radians(lon2 - lon1)
        a = math.sin(d_phi / 2)**2 + math.cos(phi1) * math.cos(phi2) * math.sin(d_lambda / 2)**2
        return r_earth * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    
    for r in all_results:
        r["distance"] = round(haversine(lat, lng, r["lat"], r["lon"]), 1)
    
    # Filter to only show results within 25km radius to avoid '106km' nonsense
    nearby_filtered = [r for r in all_results if r["distance"] <= 25.0]
    
    # If too few results, fallback to a slightly wider search or keep what we have
    if len(nearby_filtered) < 3:
        nearby_filtered = all_results[:10]
        
    nearby_filtered.sort(key=lambda x: x["distance"])
    return nearby_filtered[:15]

# ── Websocket Endpoint ──────────────────────────────────────────────────────
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)

# ── Error Handlers ──────────────────────────────────────────────────────────
@app.exception_handler(404)
async def not_found_handler(request: Request, exc):
    return templates.TemplateResponse("404.html", {"request": request}, status_code=404)

@app.exception_handler(500)
async def server_error_handler(request: Request, exc):
    return templates.TemplateResponse("500.html", {"request": request}, status_code=500)

