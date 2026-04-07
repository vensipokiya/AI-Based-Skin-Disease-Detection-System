import mysql.connector
import os
from dotenv import load_dotenv

# Load env
env_path = ".env"
if os.path.exists(env_path):
    load_dotenv(env_path)

DB_HOST = os.getenv("DB_HOST", "localhost")
DB_USER = os.getenv("DB_USER", "root")
DB_PASSWORD = os.getenv("DB_PASSWORD", "MySQL2573")
DB_NAME = os.getenv("DB_NAME", "dermacare_db")
DB_PORT = int(os.getenv("DB_PORT", 3306))

def fix_scan_history():
    print(f"Connecting to {DB_HOST}:{DB_PORT}...")
    try:
        conn = mysql.connector.connect(
            host=DB_HOST,
            user=DB_USER,
            password=DB_PASSWORD,
            database=DB_NAME,
            port=DB_PORT
        )
        cursor = conn.cursor()
        
        # Check columns
        cursor.execute("DESCRIBE scan_history")
        columns = [row[0] for row in cursor.fetchall()]
        print(f"Current columns in scan_history: {columns}")
        
        updates = []
        if 'user_name' not in columns:
            print("Adding user_name column...")
            cursor.execute("ALTER TABLE scan_history ADD COLUMN user_name VARCHAR(200) AFTER user_id")
            updates.append("user_name")
            
        if 'image_path' not in columns:
            print("Adding image_path column...")
            cursor.execute("ALTER TABLE scan_history ADD COLUMN image_path VARCHAR(500) AFTER remedies")
            updates.append("image_path")
            
        if updates:
            conn.commit()
            print(f"[SUCCESS] Added columns: {updates}")
        else:
            print("[INFO] All columns already exist.")
            
        conn.close()
    except Exception as e:
        print(f"[FAIL] {e}")

if __name__ == "__main__":
    fix_scan_history()
