import mysql.connector

def check_databases(port, user, password):
    print(f"Checking dbs on port {port} user {user}")
    try:
        conn = mysql.connector.connect(
            host="localhost",
            port=port,
            user=user,
            password=password
        )
        cursor = conn.cursor()
        cursor.execute("SHOW DATABASES")
        dbs = [row[0] for row in cursor.fetchall()]
        print(f"[SUCCESS] Databases: {dbs}")
        conn.close()
    except Exception as e:
        print(f"[FAIL] {e}")

check_databases(3306, "root", "root")
