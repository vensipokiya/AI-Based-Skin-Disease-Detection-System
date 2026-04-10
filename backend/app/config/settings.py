import os
import secrets

try:
    from dotenv import load_dotenv
    env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), ".env")
    if os.path.exists(env_path):
        load_dotenv(env_path)
except ImportError:
    pass

def _jwt_secret() -> str:
    """No hardcoded JWT secret in source — use JWT_SECRET in .env for stable keys across restarts."""
    v = os.environ.get("JWT_SECRET", "").strip()
    return v if v else secrets.token_urlsafe(32)


class Settings:
    # App Settings
    APP_NAME: str = "DermaCare AI"
    APP_DEBUG: bool = os.environ.get("DEBUG", "True").lower() == "true"
    
    # MySQL Database Settings
    DB_HOST: str = os.environ.get("DB_HOST", "localhost")
    DB_USER: str = os.environ.get("DB_USER", "root")
    DB_PASSWORD: str = os.environ.get("DB_PASSWORD", "").strip()
    DB_NAME: str = os.environ.get("DB_NAME", "darmacare_db")
    DB_PORT: int = int(os.environ.get("DB_PORT", 3306))
    
    # Security / JWT
    SECRET_KEY: str = _jwt_secret()
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 24 hours
    
    # Admin bypass: only active when BOTH are set in environment (never hardcode passwords here)
    ADMIN_BYPASS_EMAIL: str = os.environ.get("ADMIN_BYPASS_EMAIL", "").strip()
    ADMIN_BYPASS_PW: str = os.environ.get("ADMIN_BYPASS_PW", "").strip()
    
    # SMTP Settings
    SMTP_SERVER: str = os.environ.get("SMTP_SERVER", "smtp.gmail.com")
    SMTP_PORT: int = int(os.environ.get("SMTP_PORT", 587))
    SMTP_USER: str = os.environ.get("SMTP_USER", "")
    SMTP_PASSWORD: str = os.environ.get("SMTP_PASSWORD", "")
    SMTP_USE_TLS: bool = os.environ.get("SMTP_USE_TLS", "True").lower() == "true"
    
    # AI Model Settings
    MODEL_PATH: str = os.path.join(os.getcwd(), "backend", "skin_disease_efficientnetV2_final.h5")
    CLASSES_PATH: str = os.path.join(os.getcwd(), "backend", "skin_disease_efficientnetV2_final_classes.json")
    
    # Uploads
    UPLOAD_DIR: str = os.path.join(os.getcwd(), "backend", "app", "uploads", "user_uploads")
    
    # OAuth — set in environment / .env (no placeholder secrets in repo)
    GOOGLE_CLIENT_ID: str = os.environ.get("GOOGLE_CLIENT_ID", "").strip()
    GOOGLE_CLIENT_SECRET: str = os.environ.get("GOOGLE_CLIENT_SECRET", "").strip()
    APPLE_CLIENT_ID: str = os.environ.get("APPLE_CLIENT_ID", "").strip()

    # Legacy optional variable kept for backward compatibility. Nearby does not require it.
    GOOGLE_PLACES_API_KEY: str = os.environ.get("GOOGLE_PLACES_API_KEY", "").strip()
    # Free tier available; used for richer nearby place metadata (ratings/hours/tips when provided).
    FOURSQUARE_API_KEY: str = os.environ.get("FOURSQUARE_API_KEY", "").strip()

    # Public Nominatim policy: identify your app with a contact email to reduce 403 blocks.
    NOMINATIM_CONTACT_EMAIL: str = os.environ.get("NOMINATIM_CONTACT_EMAIL", "").strip()

settings = Settings()
