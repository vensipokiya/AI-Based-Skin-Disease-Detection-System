import logging
import os
from datetime import datetime

# Build logs folder at root of backend
LOG_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "logs")
if not os.path.exists(LOG_DIR):
    os.makedirs(LOG_DIR)

def get_logger(name):
    logger = logging.getLogger(name)
    if not logger.handlers:
        logger.setLevel(logging.INFO)
        
        # Consistent format
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        
        # Console output
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)
        
        # File output (daily)
        today = datetime.now().strftime("%Y-%m-%d")
        file_handler = logging.FileHandler(os.path.join(LOG_DIR, f"app_{today}.log"))
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
        
    return logger
