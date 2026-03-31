import mysql.connector

try:
    conn = mysql.connector.connect(
        host="localhost",
        port=3306,
        user="root",
        password="root",
        database="dermacare_db",
        charset='utf8'
    )
    cursor = conn.cursor()
    cursor.execute("SHOW TABLES")
    tabs = [row[0] for row in cursor.fetchall()]
    print(f"[SUCCESS] Tables in dermacare_db: {tabs}")
    conn.close()
except Exception as e:
    print(f"[FAIL] {e}")
