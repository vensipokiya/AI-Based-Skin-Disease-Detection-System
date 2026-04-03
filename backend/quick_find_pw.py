import mysql.connector

passwords = ["MySQL2573", "root", "password", "Admin@123", "admin", "1234", "123456", ""]
ports = [3306, 3307]

found = False
for port in ports:
    for pw in passwords:
        try:
            conn = mysql.connector.connect(
                host="localhost",
                port=port,
                user="root",
                password=pw
            )
            print(f"[SUCCESS] FOUND MATCH! Port: {port}, Password: '{pw}'")
            conn.close()
            found = True
            break
        except mysql.connector.Error as err:
            pass
    if found: break

if not found:
    print("[FAIL] Could not find the password among the common list.")
