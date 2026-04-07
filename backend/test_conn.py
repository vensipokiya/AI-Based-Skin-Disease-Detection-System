import mysql.connector
import os
from dotenv import load_dotenv

load_dotenv()

configs = [
    {
        "host": "localhost",
        "port": 3306,
        "user": "root",
        "password": "MySQL2573",
        "database": "dermacare_db"
    },
    {
        "host": "localhost",
        "port": 3307,
        "user": "root",
        "password": "MySQL2573",
        "database": "dermacare_db"
    }
]

for config in configs:
    print(f"Testing connection to {config['host']}:{config['port']} (Database: {config['database']})")
    try:
        conn = mysql.connector.connect(**config)
        print(f"SUCCESS: Connected to {config['host']}:{config['port']}")
        conn.close()
    except mysql.connector.Error as err:
        print(f"FAILURE: {err}")
