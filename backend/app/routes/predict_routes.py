from fastapi import APIRouter, Depends, UploadFile, File
from ..controllers.predict_controller import PredictController
from ..middleware.auth_middleware import optional_login
from typing import Optional

router = APIRouter(prefix="/api/predict", tags=["Prediction"])
predict_controller = PredictController()

@router.post("")
async def predict_skin_condition(
    file: UploadFile = File(...),
    current_user: Optional[dict] = Depends(optional_login)
):
    user_id = current_user.get("user_id") if current_user else 0
    return await predict_controller.predict_skin_condition(file, user_id)
