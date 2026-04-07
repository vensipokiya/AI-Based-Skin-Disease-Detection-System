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

def count_history():
    try:
        conn = mysql.connector.connect(
            host=DB_HOST,
            user=DB_USER,
            password=DB_PASSWORD,
            database=DB_NAME,
            port=DB_PORT
        )
        cursor = conn.cursor()
        
        cursor.execute("SELECT COUNT(*) FROM scan_history")
        count = cursor.fetchone()[0]
        print(f"Total scans in database: {count}")
        
        cursor.execute("SELECT id, user_id, disease, scan_date FROM scan_history LIMIT 10")
        rows = cursor.fetchall()
        for row in rows:
            print(row)
            
        conn.close()
    except Exception as e:
        print(f"[FAIL] {e}")

if __name__ == "__main__":
    count_history()
