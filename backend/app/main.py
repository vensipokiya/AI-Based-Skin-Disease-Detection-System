from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from contextlib import asynccontextmanager
import os
import sys

# Ensure project root is in path
sys.path.insert(0, os.getcwd())

try:
    from dotenv import load_dotenv
    env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env")
    if os.path.exists(env_path):
        load_dotenv(env_path)
except ImportError:
    pass

from .config.database import DatabaseSingleton
from .utils.logger import get_logger
from .routes import auth_routes, user_routes, scan_routes, predict_routes, admin_routes

logger = get_logger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    db = DatabaseSingleton()
    if db.get_connection():
        logger.info("[OK] MySQL Database connected and tables synchronized.")
    else:
        logger.warning("[WARNING] MySQL initialization failed. Check DB is running on port 3306.")
    yield

app = FastAPI(title="DermaCare AI", version="2.0.0", lifespan=lifespan)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Static file mounts ──────────────────────────────────────────────────────
FRONTEND = os.path.join(os.getcwd(), "frontend")

# User static assets  → /static/user/css, /static/user/js
app.mount("/static/user", StaticFiles(directory=os.path.join(FRONTEND, "user", "static")), name="static_user")

# Admin static assets → /static/admin/css, /static/admin/js
app.mount("/static/admin", StaticFiles(directory=os.path.join(FRONTEND, "admin", "static")), name="static_admin")

# Shared static assets → /static/shared/css, /static/shared/js, /static/shared/images
app.mount("/static/shared", StaticFiles(directory=os.path.join(FRONTEND, "shared", "static")), name="static_shared")

# Serve uploaded scan images → /uploads/user_uploads/<file>
UPLOAD_DIR = os.path.join(os.getcwd(), "backend", "app", "uploads", "user_uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=os.path.join(os.getcwd(), "backend", "app", "uploads")), name="uploads")

# ── Template configuration ──────────────────────────────────────────────────
from jinja2 import ChoiceLoader, FileSystemLoader, Environment
from starlette.templating import Jinja2Templates as StarletteTemplates

templates = Jinja2Templates(
    directory=[
        os.path.join(FRONTEND, "user", "templates"),
        os.path.join(FRONTEND, "admin", "templates"),
        os.path.join(FRONTEND, "shared", "templates"),
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

# ── Admin Page Routes ───────────────────────────────────────────────────────
@app.get("/admin", response_class=HTMLResponse)
async def read_admin(request: Request):
    return templates.TemplateResponse("dashboard.html", {"request": request})

# ── Nearby Doctors Proxy (bypasses browser CORS) ───────────────────────────
import httpx

@app.get("/api/nearby-doctors")
async def nearby_doctors(lat: float, lng: float):
    """Proxy endpoint: searches Nominatim from the server side so the browser
    never hits CORS / 403 issues with external APIs."""
    
    keywords = ["dermatologist", "skin clinic", "skin doctor", "derma clinic", "skin care center"]
    all_results = []
    seen_names = set()

    async with httpx.AsyncClient(timeout=12.0, headers={"User-Agent": "DermaCareAI/1.0 (student-project)"}) as client:
        for kw in keywords:
            try:
                url = (
                    f"https://nominatim.openstreetmap.org/search"
                    f"?q={kw}"
                    f"&format=json&limit=15&addressdetails=1"
                    f"&viewbox={lng-1.5},{lat+1.5},{lng+1.5},{lat-1.5}"
                    f"&bounded=0"
                )
                resp = await client.get(url)
                if resp.status_code == 200:
                    for item in resp.json():
                        name = item.get("display_name", "").split(",")[0].strip()
                        if not name or name.lower() in seen_names:
                            continue
                        seen_names.add(name.lower())
                        all_results.append({
                            "name": name,
                            "lat": float(item["lat"]),
                            "lon": float(item["lon"]),
                            "city": (item.get("address") or {}).get("city")
                                    or (item.get("address") or {}).get("town")
                                    or (item.get("address") or {}).get("village") or "",
                            "street": (item.get("address") or {}).get("road") or "",
                            "type": item.get("type", "doctor"),
                        })
            except Exception as e:
                logger.warning(f"Nominatim search failed for '{kw}': {e}")
                continue

    # If no skin specialists found, search for general clinics/hospitals
    if len(all_results) < 3:
        async with httpx.AsyncClient(timeout=12.0, headers={"User-Agent": "DermaCareAI/1.0 (student-project)"}) as client2:
            for kw in ["clinic", "hospital"]:
                try:
                    url = (
                        f"https://nominatim.openstreetmap.org/search"
                        f"?q={kw}"
                        f"&format=json&limit=10&addressdetails=1"
                        f"&viewbox={lng-1.0},{lat+1.0},{lng+1.0},{lat-1.0}"
                        f"&bounded=0"
                    )
                    resp = await client2.get(url)
                    if resp.status_code == 200:
                        for item in resp.json():
                            name = item.get("display_name", "").split(",")[0].strip()
                            if not name or name.lower() in seen_names:
                                continue
                            seen_names.add(name.lower())
                            all_results.append({
                                "name": name,
                                "lat": float(item["lat"]),
                                "lon": float(item["lon"]),
                                "city": (item.get("address") or {}).get("city") or "",
                                "street": (item.get("address") or {}).get("road") or "",
                                "type": "clinic",
                            })
                except Exception:
                    continue

    # Sort by distance to user
    import math
    def haversine(la1, lo1, la2, lo2):
        R = 6371
        d_lat = math.radians(la2 - la1)
        d_lon = math.radians(lo2 - lo1)
        a = math.sin(d_lat/2)**2 + math.cos(math.radians(la1)) * math.cos(math.radians(la2)) * math.sin(d_lon/2)**2
        return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    
    for r in all_results:
        r["distance"] = round(haversine(lat, lng, r["lat"], r["lon"]), 1)
    
    all_results.sort(key=lambda x: x["distance"])
    return all_results[:15]


# ── Error Handlers ──────────────────────────────────────────────────────────
@app.exception_handler(404)
async def not_found_handler(request: Request, exc):
    return templates.TemplateResponse("404.html", {"request": request}, status_code=404)

@app.exception_handler(500)
async def server_error_handler(request: Request, exc):
    return templates.TemplateResponse("500.html", {"request": request}, status_code=500)
