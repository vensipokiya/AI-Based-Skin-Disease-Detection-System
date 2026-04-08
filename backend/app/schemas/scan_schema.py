from pydantic import BaseModel
from typing import Optional, Dict, Any

class ScanSaveRequest(BaseModel):
    disease: str
    confidence: float
    remedies: Dict[str, Any]

class ScanResponse(BaseModel):
    id: int
    user_name: Optional[str]
    disease: str
    confidence: float
    scan_date: str
    image_path: Optional[str]
