import sys
import os

# Add parent directory to sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.app.config.database import DatabaseSingleton

db = DatabaseSingleton()
conn = db.get_connection()
if conn:
    print("[SUCCESS] Connected to DB and ensured tables.")
    cursor = conn.cursor()
    cursor.execute("SHOW TABLES")
    print(f"Tables: {[row[0] for row in cursor.fetchall()]}")
    conn.close()
else:
    print("[FAIL] Could not connect to DB.")
