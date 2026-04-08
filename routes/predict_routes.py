from fastapi import APIRouter, UploadFile, File, Depends, HTTPException
from backend.app.services.scan_service import ScanService
from backend.app.services.predict_service import PredictService
from backend.core.security import optional_login
from typing import Optional
import os
import base64

router = APIRouter(prefix="/api/predict", tags=["Prediction"])
scan_service = ScanService()
predict_service = PredictService()

@router.post("")
async def predict_skin_condition(
    file: UploadFile = File(...),
    current_user: Optional[dict] = Depends(optional_login)
):
    if not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="Invalid file type. Please upload an image.")

    try:
        # Read image bytes
        image_bytes = await file.read()
        
        # Run prediction using centralized service
        # This service now handles standard EfficientNetV2 preprocessing (RGB, Bilinear 224x224, [0,1] normalization)
        result = predict_service.predict(image_bytes)
        
        # Add original image for display
        result["image_base64"] = base64.b64encode(image_bytes).decode("utf-8")

        # Persist to DB if the user is authenticated
        user_id = current_user["user_id"] if current_user else 0
        if user_id > 0:
            scan_service.save_scan(
                user_id, 
                result["disease"], 
                result["confidence"], 
                result["remedies"], 
                image_bytes
            )

        return result

    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Prediction error: {str(e)}")
