import mysql.connector
import os
from dotenv import load_dotenv

# Standardize path resolution
current_dir = os.path.dirname(os.path.abspath(__file__))
env_path = os.path.join(current_dir, ".env")
load_dotenv(env_path)

db_config = {
    "host": os.environ.get("DB_HOST", "localhost"),
    "user": os.environ.get("DB_USER", "root"),
    "password": os.environ.get("DB_PASSWORD", "root"),
    "database": os.environ.get("DB_NAME", "dermacare_db"),
    "port": int(os.environ.get("DB_PORT", 3306))
}

email_to_delete = "inaxatra@gmail.com"

try:
    print(f"Connecting to database to remove {email_to_delete}...")
    conn = mysql.connector.connect(**db_config)
    cursor = conn.cursor()
    
    # Check if user exists first
    cursor.execute("SELECT id FROM users WHERE email = %s", (email_to_delete,))
    user = cursor.fetchone()
    
    if user:
        user_id = user[0]
        # Delete from users (ON DELETE CASCADE will handle medical_profiles etc.)
        cursor.execute("DELETE FROM users WHERE id = %s", (user_id,))
        conn.commit()
        print(f"[SUCCESS] User with email {email_to_delete} (ID: {user_id}) has been removed.")
    else:
        print(f"[INFO] No user found with email {email_to_delete}. It is already free to use.")
        
    conn.close()
except Exception as e:
    print(f"[FAIL] Error removing user: {e}")
