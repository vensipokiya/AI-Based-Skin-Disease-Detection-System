import mysql.connector
import os
from dotenv import load_dotenv

load_dotenv("backend/.env")

def test_conn(host, port, user, password, database):
    print(f"Testing {user}@{host}:{port} db={database} password={password}")
    try:
        conn = mysql.connector.connect(
            host=host,
            port=port,
            user=user,
            password=password,
            database=database
        )
        print(f"[SUCCESS] Connected to {database} on port {port}")
        conn.close()
        return True
    except Exception as e:
        print(f"[FAIL] Port {port}: {e}")
        return False

# Common scenarios
scenarios = [
    (3307, "root", "password"),
    (3307, "root", ""),
    (3307, "root", "root")
]

for p, u, pw in scenarios:
    test_conn("localhost", p, u, pw, "skin_disease")
    print("-" * 20)
