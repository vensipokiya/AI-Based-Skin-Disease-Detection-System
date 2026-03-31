import mysql.connector

try:
    conn = mysql.connector.connect(
        host="localhost",
        port=3306,
        user="root",
        password="root",
        charset='utf8'
    )
    cursor = conn.cursor()
    cursor.execute("CREATE DATABASE IF NOT EXISTS dermacare_db")
    print("[OK] dermacare_db ensured.")
    conn.close()
except Exception as e:
    print(f"[FAIL] {e}")
