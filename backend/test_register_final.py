import requests
import json

URL = "http://127.0.0.1:8000/api/auth/register"

data = {
    "first_name": "Test",
    "last_name": "User",
    "email": "testuser@gmail.com",
    "password": "Password123!",
    "contact_number": "+919999999999",
    "gender": "male",
    "date_of_birth": "1990-01-01",
    "age": 34,
    "symptoms": "Itchy skin rash",
    "symptom_duration": "1 week",
    "previous_conditions": "no",
    "previous_condition_details": ""
}

try:
    print(f"Attempting to register test user at {URL}...")
    response = requests.post(URL, json=data, timeout=10)
    print(f"Status Code: {response.status_code}")
    print(f"Response: {response.json()}")
except Exception as e:
    print(f"Connection failed: {e}")
