import requests
import json

BASE = "http://127.0.0.1:8000"

# 1. Login as admin
print("=== Step 1: Admin Login ===")
resp = requests.post(f"{BASE}/api/auth/login", json={"email": "admin@gmail.com", "password": "Admin@1234"})
print("Status:", resp.status_code)
data = resp.json()
print("Success:", data.get("success"))
token = data.get("token", "")
print("Token obtained:", bool(token))

if token:
    headers = {"Authorization": f"Bearer {token}"}

    # 2. Fetch login history
    print("\n=== Step 2: Fetch Login History ===")
    r2 = requests.get(f"{BASE}/api/admin/login-history", headers=headers)
    print("Status:", r2.status_code)
    d2 = r2.json()
    history = d2.get("history", [])
    print("Records found:", len(history))
    for h in history[:5]:
        name = h.get("first_name", "Admin")
        status = h.get("status")
        ip = h.get("ip_address")
        login_time = h.get("login_time")
        logout_time = h.get("logout_time")
        session = h.get("session_id", "")[:8] + "..."
        print(f"  [{status}] {name} | IP: {ip} | Login: {login_time} | Logout: {logout_time} | Session: {session}")

    # 3. Logout
    print("\n=== Step 3: Admin Logout ===")
    r3 = requests.post(f"{BASE}/api/auth/logout", headers=headers)
    print("Status:", r3.status_code)
    d3 = r3.json()
    print("Logout Response:", json.dumps(d3, indent=2))

    # 4. Fetch login history again to verify LOGOUT was recorded
    print("\n=== Step 4: Login History After Logout (verify LOGOUT status) ===")
    r4 = requests.get(f"{BASE}/api/admin/login-history", headers=headers)
    d4 = r4.json()
    after_logout = d4.get("history", [])
    for h in after_logout[:5]:
        name = h.get("first_name", "Admin")
        status = h.get("status")
        logout_time = h.get("logout_time")
        print(f"  [{status}] {name} | Logout: {logout_time}")

print("\n=== DONE ===")
