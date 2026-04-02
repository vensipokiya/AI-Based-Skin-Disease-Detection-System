import os

try:
    from dotenv import load_dotenv
    env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), ".env")
    if os.path.exists(env_path):
        load_dotenv(env_path)
except ImportError:
    pass

class Settings:
    # App Settings
    APP_NAME: str = "DermaCare AI"
    APP_DEBUG: bool = os.environ.get("DEBUG", "True").lower() == "true"
    
    # MySQL Database Settings
    DB_HOST: str = os.environ.get("DB_HOST", "localhost")
    DB_USER: str = os.environ.get("DB_USER", "root")
    DB_PASSWORD: str = os.environ.get("DB_PASSWORD", "MySQL2573")
    DB_NAME: str = os.environ.get("DB_NAME", "darmacare_db")
    DB_PORT: int = int(os.environ.get("DB_PORT", 3306))
    
    # Security / JWT
    SECRET_KEY: str = os.environ.get("JWT_SECRET", "DERMACARE_SECRET_KEY_2026")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 24 hours
    
    # Admin Bypass Credentials
    ADMIN_BYPASS_EMAIL: str = os.environ.get("ADMIN_BYPASS_EMAIL", "admin@gmail.com")
    ADMIN_BYPASS_PW: str = os.environ.get("ADMIN_BYPASS_PW", "Admin@1234")
    
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

settings = Settings()
