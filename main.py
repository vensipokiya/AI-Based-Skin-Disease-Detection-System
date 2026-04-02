"""
Root entry point - delegates to backend/app/main.py
Run with: uvicorn main:app --reload --host 127.0.0.1 --port 8000
"""
import os
import sys

# Add project root to path so 'backend' package is importable
sys.path.insert(0, os.getcwd())

try:
    from dotenv import load_dotenv
    load_dotenv(os.path.join("backend", ".env"))
except ImportError:
    pass

from backend.app.main import app

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
