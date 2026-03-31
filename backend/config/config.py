import os
try:
    from dotenv import load_dotenv
    # Load from backend/.env
    env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env")
    if os.path.exists(env_path):
        load_dotenv(env_path)
except ImportError:
    pass

class Config:
    DATABASE_URL = os.environ.get("DATABASE_URL", "mysql+mysqlconnector://root:password@localhost:3307/dermacare_db")
    JWT_SECRET = os.environ.get("JWT_SECRET", "DERMACARE_SECRET_2026")
    
    SMTP_CONFIG = {
        "server": os.environ.get("SMTP_SERVER", "smtp.gmail.com"),
        "port": int(os.environ.get("SMTP_PORT", 587)),
        "user": os.environ.get("SMTP_USER", ""),
        "password": os.environ.get("SMTP_PASSWORD", ""),
        "use_tls": True
    }
    
    # Development bypass settings
    ADMIN_BYPASS = {
        "email": os.environ.get("ADMIN_BYPASS_EMAIL", "admin@gmail.com"),
        "password": os.environ.get("ADMIN_BYPASS_PW", "Admin@1234")
    }
