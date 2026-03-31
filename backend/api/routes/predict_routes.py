from fastapi import APIRouter, UploadFile, File, Depends, HTTPException
from backend.services.scan_service import ScanService
from backend.core.security import optional_login
from typing import Optional
import os
import shutil
import json
import numpy as np
import tensorflow as tf
from PIL import Image

router = APIRouter(prefix="/api/predict", tags=["Prediction"])
scan_service = ScanService()

# BACKEND_DIR = the 'backend' folder that contains this 'api' subfolder and the model files
# __file__ is backend/api/routes/predict_routes.py
# dirname x1 → backend/api/routes
# dirname x2 → backend/api
# dirname x3 → backend          ← this is BACKEND_DIR
BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Project root is one level above backend/
PROJECT_ROOT = os.path.dirname(BACKEND_DIR)

# Model files live directly inside the backend/ folder
MODEL_PATH   = os.path.join(BACKEND_DIR, "skin_disease_efficientnetV2_final.h5")
CLASSES_PATH = os.path.join(BACKEND_DIR, "skin_disease_efficientnetV2_final_classes.json")

# Uploads folder sits at project root level
UPLOAD_DIR = os.path.join(BACKEND_DIR, "uploads")

# Debug log so startup prints tell us if paths are correct
print(f"[predict_routes] BACKEND_DIR : {BACKEND_DIR}")
print(f"[predict_routes] MODEL_PATH  : {MODEL_PATH}  exists={os.path.exists(MODEL_PATH)}")
print(f"[predict_routes] CLASSES_PATH: {CLASSES_PATH}  exists={os.path.exists(CLASSES_PATH)}")

if not os.path.exists(UPLOAD_DIR):
    os.makedirs(UPLOAD_DIR)

# Global model & labels cache
model = None
labels = {}

def load_model_assets():
    global model, labels
    if model is None:
        if os.path.exists(MODEL_PATH):
            try:
                model = tf.keras.models.load_model(MODEL_PATH)
            except Exception as e:
                print(f"[ERROR] Failed to load model: {e}")

    if not labels:
        if os.path.exists(CLASSES_PATH):
            with open(CLASSES_PATH, "r") as f:
                labels = json.load(f)

# Load immediately
load_model_assets()

def get_remedies(disease):
    # NOTE: Disease names must match exactly as they appear after replacing underscores with spaces.
    # Classes in classes.json: "Acne", "Eczema", "Non_Acne", "benign", "malignant", "normal skin", "psoriasis", "vitiligo"
    # After .replace("_", " ") these become:
    # "Acne", "Eczema", "Non Acne", "benign", "malignant", "normal skin", "psoriasis", "vitiligo"
    remedies_map = {
        "Acne": {
            "home_remedies": ["Use tea tree oil", "Apply honey-cinnamon mask", "Wash with warm water"],
            "skincare_routine": ["Use salicylic acid cleanser", "Non-comedogenic moisturizer"],
            "diet_suggestions": ["Reduce dairy/sugar", "Drink green tea"]
        },
        "Eczema": {
            "home_remedies": ["Keep skin moisturized", "Use gentle soap", "Oatmeal baths"],
            "skincare_routine": ["Apply moisturizer after bathing", "Avoid fragrance"],
            "diet_suggestions": ["Include omega-3 rich foods", "Probiotics"]
        },
        "Non Acne": {
            "home_remedies": ["Keep skin clean", "Avoid touching face", "Use gentle cleansers"],
            "skincare_routine": ["Use non-comedogenic products", "Regular gentle exfoliation"],
            "diet_suggestions": ["Drink plenty of water", "Eat fruits and vegetables"]
        },
        "benign": {
            "home_remedies": ["Monitor for any changes in size or color", "Protect from sun exposure", "Avoid irritating the area"],
            "skincare_routine": ["Apply SPF 30+ sunscreen daily", "Keep skin moisturized", "Regular dermatologist check-ups"],
            "diet_suggestions": ["Antioxidant-rich foods", "Stay hydrated", "Healthy balanced diet"]
        },
        "malignant": {
            "home_remedies": ["Seek immediate medical attention", "Avoid sun exposure on affected area", "Do not self-treat"],
            "skincare_routine": ["Apply high SPF sunscreen", "Cover affected area", "Follow doctor's skincare plan"],
            "diet_suggestions": ["Anti-inflammatory diet", "Antioxidant-rich foods", "Consult oncologist for diet plan"]
        },
        "normal skin": {
            "home_remedies": ["Maintain regular skincare routine", "Stay hydrated", "Get adequate sleep"],
            "skincare_routine": ["Cleanse and moisturize daily", "Apply sunscreen SPF 30+", "Exfoliate gently once a week"],
            "diet_suggestions": ["Balanced diet with fruits and vegetables", "Drink 8 glasses of water daily", "Limit processed foods"]
        },
        "psoriasis": {
            "home_remedies": ["Apply aloe vera", "Vitamin D from sunlight", "Apple cider vinegar"],
            "skincare_routine": ["Targeted topical treatments", "Scalp care specifically"],
            "diet_suggestions": ["Anti-inflammatory diet", "Avoid alcohol"]
        },
        "vitiligo": {
            "home_remedies": ["Protect depigmented skin from sun", "Use concealer if preferred"],
            "skincare_routine": ["Sunscreen is crucial", "Skin camouflage"],
            "diet_suggestions": ["Antioxidant-rich foods", "Folic acid"]
        }
    }
    return remedies_map.get(disease, {
        "home_remedies": ["Consult a dermatologist", "Keep affected area clean"],
        "skincare_routine": ["Gentle cleansing", "SPF protection"],
        "diet_suggestions": ["Healthy balanced diet", "Stay hydrated"]
    })

@router.post("")
async def predict_skin_condition(
    file: UploadFile = File(...),
    current_user: Optional[dict] = Depends(optional_login)
):
    if not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="Invalid file type. Please upload an image.")

    temp_path = os.path.join(UPLOAD_DIR, file.filename)
    with open(temp_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    try:
        load_model_assets()
        if model is None:
            raise Exception("AI Model not available on server.")

        # -----------------------------------------------------------------------
        # Image Preprocessing
        # CRITICAL: EfficientNetV2S was trained with include_preprocessing=True.
        # This means the Keras model itself handles pixel normalization internally.
        # We must pass RAW pixel values (0-255) as float32.
        # DO NOT divide by 255.0 — doing so produces incorrect predictions.
        # -----------------------------------------------------------------------
        img = Image.open(temp_path).convert('RGB')
        img = img.resize((224, 224))          # Model trained at 224x224
        img_array = np.array(img).astype(np.float32)  # Raw pixels [0, 255]
        img_array = np.expand_dims(img_array, axis=0)

        # Predict
        predictions = model.predict(img_array)
        class_idx = str(np.argmax(predictions[0]))
        confidence = float(np.max(predictions[0]) * 100)

        disease_name = labels.get(class_idx, "Unknown Condition")
        # Replace underscores with spaces (e.g. "Non_Acne" -> "Non Acne")
        disease_name = disease_name.replace("_", " ")

        result = {
            "disease": disease_name,
            "confidence": round(confidence, 1),
            "remedies": get_remedies(disease_name)
        }

        # Save to DB if user is logged in
        user_id = current_user["user_id"] if current_user else 0
        if user_id > 0:
            scan_service.save_scan(user_id, result["disease"], result["confidence"], result["remedies"])

        return result
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Prediction error: {str(e)}")
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)
