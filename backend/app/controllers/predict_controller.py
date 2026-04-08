from fastapi import UploadFile, HTTPException
from ..services.predict_service import PredictService
from ..services.scan_service import ScanService
import base64
from typing import Optional

class PredictController:
    def __init__(self, predict_service=None, scan_service=None):
        self.predict_service = predict_service if predict_service else PredictService()
        self.scan_service = scan_service if scan_service else ScanService()

    async def predict_skin_condition(self, file: UploadFile, current_user_id: Optional[int] = None):
        if not file.content_type.startswith("image/"):
            raise HTTPException(status_code=400, detail="Invalid file type. Please upload an image.")

        try:
            image_bytes = await file.read()
            prediction_result = self.predict_service.predict(image_bytes)
            
            # Combine result for response
            response = prediction_result.copy()
            response["image_base64"] = base64.b64encode(image_bytes).decode("utf-8")

            # Persist to DB if user is logged in
            if current_user_id and current_user_id > 0:
                self.scan_service.save_scan(
                    current_user_id, 
                    response["disease"], 
                    response["confidence"], 
                    response["remedies"], 
                    image_bytes
                )

            return response
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Prediction error: {str(e)}")
