import mysql.connector

passwords = ["root", "password", "Admin@123", "admin", "1234", "123456", ""]
work = False

for pw in passwords:
    try:
        conn = mysql.connector.connect(
            host="localhost",
            port=3307,
            user="root",
            password=pw
        )
        print(f"[SUCCESS] Found password: '{pw}'")
        conn.close()
        work = True
        break
    except mysql.connector.Error as err:
        print(f"[TRY] Password '{pw}' failed: {err}")

if not work:
    print("[FAIL] None of the common passwords worked for port 3307.")
