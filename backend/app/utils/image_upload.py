import os
import uuid
from ..config.settings import settings

def save_upload_file(image_bytes: bytes, extension: str = "jpg") -> str:
    """
    Saves the image bytes to the local upload directory and returns the relative path.
    """
    if not os.path.exists(settings.UPLOAD_DIR):
        os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
    
    filename = f"{uuid.uuid4().hex}.{extension}"
    file_path = os.path.join(settings.UPLOAD_DIR, filename)
    
    with open(file_path, "wb") as f:
        f.write(image_bytes)
    
    return f"/uploads/user_uploads/{filename}"
