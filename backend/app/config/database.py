import mysql.connector
from mysql.connector import pooling
import os
import threading
from typing import Any, Optional
import logging

try:
    from dotenv import load_dotenv
    env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), ".env")
    if os.path.exists(env_path):
        load_dotenv(env_path)
except ImportError:
    pass

from .settings import settings

# Set up logging for the DB
logger = logging.getLogger(__name__)

class DatabaseSingleton:
    _instance = None
    _initialize_lock = threading.Lock()
    pool: Any = None

    def __new__(cls):
        if cls._instance is None:
            with cls._initialize_lock:
                if cls._instance is None:
                    cls._instance = super(DatabaseSingleton, cls).__new__(cls)
                    cls._instance._initialize_pool()
        return cls._instance

    def _initialize_pool(self):
        try:
            db_config = {
                "host": settings.DB_HOST,
                "user": settings.DB_USER,
                "password": settings.DB_PASSWORD, 
                "database": settings.DB_NAME,
                "port": settings.DB_PORT,
                "charset": "utf8",
                "connect_timeout": 5 
            }
            
            logger.info(f"Initializing MySQL connection pool to {db_config['host']}:{db_config['port']}")
            
            self.pool = pooling.MySQLConnectionPool(
                pool_name="derma_pool",
                pool_size=10,
                pool_reset_session=True,
                **db_config
            )
            
            logger.info("Successfully established MySQL connection pool.")
            self._ensure_tables()
            
        except mysql.connector.Error as err:
            logger.error(f"Failed to create MySQL pool: {err}")
            self.pool = None

    def get_connection(self):
        if not self.pool:
            logger.error("No active connection pool found. Re-initializing...")
            self._initialize_pool()
            if not self.pool: return None
        try:
            return self.pool.get_connection()
        except mysql.connector.Error as err:
            logger.error(f"Error getting connection from pool: {err}")
            return None

    def _ensure_tables(self):
        conn = self.get_connection()
        if not conn: return
        try:
            cursor = conn.cursor()
            
            # Ensure tables exist (Mirroring the logic from connection.py)
            # Core 'users' 
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    first_name VARCHAR(100) NOT NULL,
                    last_name VARCHAR(100) NOT NULL,
                    email VARCHAR(150) UNIQUE NOT NULL,
                    password_hash VARCHAR(255) NOT NULL,
                    contact_number VARCHAR(20),
                    is_active BOOLEAN DEFAULT TRUE,
                    is_logged_in BOOLEAN DEFAULT FALSE,
                    role VARCHAR(50) DEFAULT 'User',
                    last_login TIMESTAMP NULL,
                    date_of_birth DATE,
                    age INT,
                    gender VARCHAR(20),
                    user_location VARCHAR(255) DEFAULT 'Unknown',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Medical Profiles
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS medical_profiles (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    user_id INT,
                    symptoms TEXT,
                    symptom_duration VARCHAR(100),
                    has_previous_conditions BOOLEAN DEFAULT FALSE,
                    previous_condition_details TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
                )
            """)

            # Scan History
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS scan_history (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    user_id INT,
                    user_name VARCHAR(200),
                    disease VARCHAR(100) NOT NULL,
                    confidence FLOAT NOT NULL,
                    remedies TEXT,
                    image_data LONGBLOB,
                    scan_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
                )
            """)
            
            # Additional tables (merged logic)
            cursor.execute("CREATE TABLE IF NOT EXISTS user_locations (id INT AUTO_INCREMENT PRIMARY KEY, uid INT NOT NULL, latitude DOUBLE, longitude DOUBLE, timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP, FOREIGN KEY (uid) REFERENCES users(id) ON DELETE CASCADE)")
            cursor.execute("CREATE TABLE IF NOT EXISTS otp_verification (id INT AUTO_INCREMENT PRIMARY KEY, uid INT NOT NULL, contact VARCHAR(150) NOT NULL, otp VARCHAR(10) NOT NULL, is_verified BOOLEAN DEFAULT FALSE, expires_at TIMESTAMP NULL, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, FOREIGN KEY (uid) REFERENCES users(id) ON DELETE CASCADE)")
            cursor.execute("CREATE TABLE IF NOT EXISTS doctor_appointments (id INT AUTO_INCREMENT PRIMARY KEY, user_id INT NOT NULL, doctor_name VARCHAR(255) NOT NULL, doctor_specialty VARCHAR(255), doctor_area VARCHAR(255), doctor_city VARCHAR(255), appointment_date DATE NOT NULL, appointment_time TIME NOT NULL, status VARCHAR(50) DEFAULT 'Confirmed', created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE)")
            cursor.execute("CREATE TABLE IF NOT EXISTS system_logs (id INT AUTO_INCREMENT PRIMARY KEY, user_id INT, event_type VARCHAR(100), details TEXT, timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP, FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE)")

            conn.commit()
            logger.info("All MySQL database tables are synchronized.")
            
        except mysql.connector.Error as err:
            logger.error(f"Migration error: {err}")
        finally:
            if conn: conn.close()

    from contextlib import contextmanager

    @contextmanager
    def connection(self):
        conn = self.get_connection()
        if not conn:
            raise Exception("Database connection error: Could not get connection from pool.")
        try:
            yield conn
        finally:
            if conn:
                conn.close()

    @contextmanager
    def cursor(self, dictionary=True, commit=False):
        with self.connection() as conn:
            cursor = conn.cursor(dictionary=dictionary)
            try:
                yield cursor
                if commit:
                    conn.commit()
            except Exception as e:
                conn.rollback()
                raise e
            finally:
                cursor.close()

db_singleton = DatabaseSingleton()
