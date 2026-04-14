from fastapi import APIRouter, UploadFile, File, Depends, HTTPException
from backend.app.services.scan_service import ScanService
from backend.app.middleware.auth_middleware import optional_login
from backend.app.utils.remedies import get_remedies
from typing import Optional
import os
import shutil
import json
import tensorflow as tf
import base64
import uuid
import numpy as np

router = APIRouter(prefix="/api/predict", tags=["Prediction"])
scan_service = ScanService()

# ── Path resolution ────────────────────────────────────────────────────────────
PROJECT_ROOT = os.getcwd()
BACKEND_DIR  = os.path.join(PROJECT_ROOT, "backend")

MODEL_PATH   = os.path.join(BACKEND_DIR, "skin_disease_efficientnetV2_final.h5")
CLASSES_PATH = os.path.join(BACKEND_DIR, "skin_disease_efficientnetV2_final_classes.json")
UPLOAD_DIR   = os.path.join(BACKEND_DIR, "uploads")

print(f"[predict_routes] BACKEND_DIR  : {BACKEND_DIR}")
print(f"[predict_routes] MODEL_PATH   : {MODEL_PATH}  exists={os.path.exists(MODEL_PATH)}")
print(f"[predict_routes] CLASSES_PATH : {CLASSES_PATH}  exists={os.path.exists(CLASSES_PATH)}")

os.makedirs(UPLOAD_DIR, exist_ok=True)


# ── Global model & labels cache ────────────────────────────────────────────────
model  = None
labels = {}

def load_model_assets():
    global model, labels
    if model is None and os.path.exists(MODEL_PATH):
        try:
            model = tf.keras.models.load_model(MODEL_PATH)
            print("[predict_routes] Model loaded successfully.")
        except Exception as e:
            print(f"[ERROR] Failed to load model: {e}")

    if not labels and os.path.exists(CLASSES_PATH):
        try:
            with open(CLASSES_PATH, "r") as f:
                labels = json.load(f)
            print(f"[predict_routes] Classes loaded: {labels}")
        except Exception as e:
            print(f"[ERROR] Failed to load classes: {e}")

load_model_assets()


@router.post("")
async def predict_skin_condition(
    file: UploadFile = File(...),
    current_user: Optional[dict] = Depends(optional_login)
):
    if not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="Invalid file type. Please upload an image.")

    # Read image bytes for DB storage
    image_bytes = await file.read()
    # Reset file pointer for the file processing
    file.file.seek(0)
    
    # Hardened: Enforce purely internal filename & extension to prevent path traversal
    temp_filename = f"upload_{uuid.uuid4().hex}.jpg"
    temp_path = os.path.join(UPLOAD_DIR, temp_filename)

    import anyio

    def save_file_sync(data, path):
        with open(path, "wb") as f:
            f.write(data)

    await anyio.to_thread.run_sync(save_file_sync, image_bytes, temp_path)


    try:
        load_model_assets()
        if model is None:
            raise Exception("AI Model is not available on the server. Please check model file.")

        # ── Image Preprocessing ────────────────────────────────────────────────
        # Decode: handle JPEG and PNG
        try:
            img_tensor = tf.image.decode_image(image_bytes, channels=3, expand_animations=False)
        except Exception as e:
            print(f"[predict_routes] Multi-type decode failed: {e}. Falling back to JPEG-only.")
            img_tensor = tf.image.decode_jpeg(image_bytes, channels=3)


        # Resize with BILINEAR (exactly as training)
        img_tensor = tf.image.resize(img_tensor, (224, 224), method=tf.image.ResizeMethod.BILINEAR)

        # Cast to float32
        img_array = tf.cast(img_tensor, tf.float32).numpy()
        img_batch = np.expand_dims(img_array, axis=0)  # shape: (1, 224, 224, 3)

        # ── Run Prediction ────────────────────────────────────────────────────
        predictions  = model.predict(img_batch, verbose=0)
        pred_probs   = predictions[0]                           # shape: (8,)

        # Primary result
        top_idx      = int(np.argmax(pred_probs))
        confidence   = float(pred_probs[top_idx]) * 100
        disease_name = labels.get(str(top_idx), "Unknown Condition").replace("_", " ")

        # Top-3 predictions for confidence breakdown panel
        top3_indices = np.argsort(pred_probs)[::-1][:3]
        top3 = [
            {
                "disease":    labels.get(str(int(i)), "Unknown").replace("_", " "),
                "confidence": round(float(pred_probs[i]) * 100, 1)
            }
            for i in top3_indices
        ]

        print(f"[PREDICT] Result: {disease_name} ({confidence:.1f}%)")

        result = {
            "disease":         disease_name,
            "confidence":      round(confidence, 1),
            "remedies":        get_remedies(disease_name),
            "top_predictions": top3,
            "image_base64":    base64.b64encode(image_bytes).decode("utf-8")
        }

        # Persist to DB if the user is authenticated
        user_id = current_user["user_id"] if current_user else 0
        if user_id > 0:
            scan_service.save_scan(user_id, result["disease"], result["confidence"], result["remedies"], image_bytes)

        return result

    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Prediction error: {str(e)}")

    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)
