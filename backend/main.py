from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from contextlib import asynccontextmanager
import os
import sys

# Standardize path resolution for imports
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
if parent_dir not in sys.path:
    sys.path.append(parent_dir)

from backend.config.config import Config
from backend.db.connection import DatabaseSingleton
from backend.core.logger import get_logger
from backend.api.routes import auth_routes, user_routes, scan_routes, predict_routes, admin_routes

logger = get_logger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize singleton connection
    db = DatabaseSingleton()
    if db.get_connection():
        logger.info("[OK] MySQL Database strictly connected and tables ensured on start.")
    else:
        logger.warning("[WARNING] MySQL initialization failed. Make sure DB is running.")
    yield

app = FastAPI(title="DermaCare AI APIs", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API Routers (MVC structure)
app.include_router(auth_routes.router)
app.include_router(user_routes.router)
app.include_router(scan_routes.router)
app.include_router(predict_routes.router)
app.include_router(admin_routes.router)

frontend_dir = os.path.join(parent_dir, "frontend")

app.mount("/css", StaticFiles(directory=os.path.join(frontend_dir, "css")), name="css")
app.mount("/js", StaticFiles(directory=os.path.join(frontend_dir, "js")), name="js")
# Only mount if directory exists
assets_dir = os.path.join(frontend_dir, "assets")
if os.path.exists(assets_dir):
    app.mount("/assets", StaticFiles(directory=assets_dir), name="assets")
else:
    logger.warning(f"Static assets directory not found at {assets_dir}. Skipping mount.")

# Serve HTML pages directly from backend so CORS works correctly
# Access the app at http://127.0.0.1:8000  (NOT as a file://)
@app.get("/")
async def serve_index():
    return FileResponse(os.path.join(frontend_dir, "index.html"))

# Serve any .html file by name (e.g. /detection.html, /login.html)
@app.get("/{page_name}.html")
async def serve_html_page(page_name: str):
    html_path = os.path.join(frontend_dir, f"{page_name}.html")
    if os.path.exists(html_path):
        return FileResponse(html_path)
    return FileResponse(os.path.join(frontend_dir, "index.html"))  # fallback

app.mount("/static", StaticFiles(directory=frontend_dir), name="static")

if __name__ == "__main__":
    import uvicorn # type: ignore
    # Running from root directory as backend.main
    uvicorn.run("backend.main:app", host="0.0.0.0", port=8000, reload=True)
