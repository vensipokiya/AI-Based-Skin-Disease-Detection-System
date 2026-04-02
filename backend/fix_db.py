import mysql.connector
import os
import re

# Ports to try
ports = [3307, 3306]
# Passwords to try (Include root as both user/pass)
default_passwords = "root,password,Admin@123,admin,1234,123456"
passwords = os.environ.get("TEST_DB_PASSWORDS", default_passwords).split(",")
passwords.append("")
db_name = "dermacare_db"

def update_env(port, password):
    env_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
    if not os.path.exists(env_file):
        print(f"[ERROR] .env file not found at {env_file}")
        return

    with open(env_file, "r") as f:
        content = f.read()

    # Update individual variables
    content = re.sub(r'DB_PORT=\d+', f'DB_PORT={port}', content)
    content = re.sub(r'DB_PASSWORD=.*', f'DB_PASSWORD={password}', content)
    content = re.sub(r'DB_NAME=.*', f'DB_NAME={db_name}', content)
    
    # Update DATABASE_URL composite
    content = re.sub(r'DATABASE_URL=.*', f'DATABASE_URL=mysql+mysqlconnector://root:{password}@localhost:{port}/{db_name}', content)

    with open(env_file, "w") as f:
        f.write(content)
    print(f"[OK] Updated .env with Port {port} and Password '{password}'")

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
            print(f"[SUCCESS] Connected to MySQL on Port {port} with Password '{pw}'")
            conn.close()
            update_env(port, pw)
            found = True
            break
        except mysql.connector.Error:
            continue
    if found: break

if not found:
    print("[FAIL] Could not find a valid MySQL connection. Please check your password manually!")
else:
    print("[DONE] Everything is fixed. START YOUR BACKEND SERVER NOW.")
