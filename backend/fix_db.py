import mysql.connector
import os
import re

# Ports to try
ports = [3307, 3306]
# Passwords to try (Include root as both user/pass)
default_passwords = "root,admin123,Admin@123,admin,1234,123456"
passwords = os.environ.get("TEST_DB_PASSWORDS", default_passwords).split(",")
passwords.append("")
db_name = "dermacare_db"

def update_env(db_port, db_auth_token):
    env_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
    if not os.path.exists(env_file):
        print(f"[ERROR] .env file not found at {env_file}")
        return

    with open(env_file, "r") as f:
        content = f.read()

    # Update individual variables - Logic maintains .env consistency
    content = re.sub(r'DB_PORT=\d+', f'DB_PORT={db_port}', content)
    content = re.sub(r'DB_PASSWORD=.*', f'DB_PASSWORD={db_auth_token}', content)
    content = re.sub(r'DB_NAME=.*', f'DB_NAME={db_name}', content)
    
    # Update DATABASE_URL composite
    content = re.sub(r'DATABASE_URL=.*', f'DATABASE_URL=mysql+mysqlconnector://root:{db_auth_token}@localhost:{db_port}/{db_name}', content)

    with open(env_file, "w") as f:
        f.write(content)
    print(f"[OK] Dynamic .env update: Synchronized connection parameters for Port {db_port}")

found = False
for port in ports:
    for auth_val in passwords:
        try:
            conn = mysql.connector.connect(
                host="localhost",
                port=port,
                user="root",
                password=auth_val
            )
            print(f"[SUCCESS] Connection verified on Port {port}")
            conn.close()
            update_env(port, auth_val)
            found = True
            break
        except mysql.connector.Error:
            continue
    if found: break

if not found:
    print("[FAIL] Could not find a valid MySQL connection. Please check your password manually!")
else:
    print("[DONE] Everything is fixed. START YOUR BACKEND SERVER NOW.")
