import mysql.connector
import os
from dotenv import load_dotenv

# Load the NEW settings from .env
env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
load_dotenv(env_path)

db_host = os.environ.get("DB_HOST", "localhost")
db_user = os.environ.get("DB_USER", "root")
db_pass = os.environ.get("DB_PASSWORD", "")
db_name = os.environ.get("DB_NAME", "darmacare_db")
db_port = int(os.environ.get("DB_PORT", 3306))

def setup_all():
    print(f"Connecting to MySQL on {db_host}:{db_port}...")
    try:
        # 1. Connect without DB to create it
        conn = mysql.connector.connect(
            host=db_host,
            user=db_user,
            password=db_pass,
            port=db_port
        )
        cursor = conn.cursor()
        cursor.execute(f"CREATE DATABASE IF NOT EXISTS {db_name}")
        print(f"[OK] Database '{db_name}' ensured.")
        conn.close()

        # 2. Use the standard connection logic to create tables
        from backend.app.config.database import DatabaseSingleton
        db = DatabaseSingleton()
        db._ensure_tables()
        print("[SUCCESS] All tables created and synchronized successfully!")

    except Exception as e:
        print(f"[ERROR] Setup failed: {e}")

if __name__ == "__main__":
    setup_all()
