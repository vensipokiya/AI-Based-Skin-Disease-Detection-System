import mysql.connector
import os

try:
    conn = mysql.connector.connect(
        host=os.environ.get("DB_HOST", "localhost"),
        port=int(os.environ.get("DB_PORT", 3306)),
        user=os.environ.get("DB_USER", "root"),
        password=os.environ.get("DB_PASSWORD", ""),
        database=os.environ.get("DB_NAME", "dermacare_db"),
        charset='utf8'
    )
    cursor = conn.cursor()
    cursor.execute("SHOW TABLES")
    tabs = [row[0] for row in cursor.fetchall()]
    print(f"[SUCCESS] Tables in dermacare_db: {tabs}")
    conn.close()
except Exception as e:
    print(f"[FAIL] {e}")
