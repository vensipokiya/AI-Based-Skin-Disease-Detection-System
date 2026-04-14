from fastapi import APIRouter, UploadFile, File, Depends, HTTPException
from backend.services.scan_service import ScanService
from backend.core.security import optional_login
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
# __file__ = routes/predict_routes.py
# PROJECT_ROOT = ./
# BACKEND_DIR  = ./backend
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
        with open(CLASSES_PATH, "r") as f:
            labels = json.load(f)
        print(f"[predict_routes] Classes loaded: {labels}")

load_model_assets()

# ── Remedies database (ALL 8 disease classes) ──────────────────────────────────
# Keys are LOWERCASE to support case-insensitive lookup.
# Model returns: Acne, Benign, Eczema, Malignant, Non_Acne, Normal skin, Psoriasis, Vitiligo
# After .replace("_"," "): Acne, Benign, Eczema, Malignant, Non Acne, Normal skin, Psoriasis, Vitiligo
REMEDIES_MAP = {
    "acne": {
        "home_remedies": [
            "Apply tea tree oil (diluted) to affected areas",
            "Use honey and cinnamon mask twice a week",
            "Wash face with lukewarm water 2× daily",
            "Apply ice to reduce inflammation"
        ],
        "skincare_routine": [
            "Use salicylic acid or benzoyl peroxide cleanser",
            "Apply lightweight, non-comedogenic moisturizer",
            "Never sleep with makeup on",
            "Use oil-free sunscreen SPF 30+"
        ],
        "diet_suggestions": [
            "Reduce dairy and high-glycemic foods",
            "Drink green tea (anti-inflammatory)",
            "Eat zinc-rich foods: pumpkin seeds, nuts",
            "Increase omega-3 intake: fish, flaxseed"
        ],
        "consult_doctor": [
            "If acne is severe, nodular, or cystic",
            "If scarring or hyperpigmentation occurs",
            "If no improvement after 8 weeks of home care"
        ]
    },
    "benign": {
        "home_remedies": [
            "Monitor the lesion monthly for size or color changes",
            "Protect from direct sun exposure with clothing or sunscreen",
            "Avoid scratching or irritating the area",
            "Keep the area clean and dry"
        ],
        "skincare_routine": [
            "Apply broad-spectrum SPF 50+ sunscreen daily",
            "Keep surrounding skin well moisturized",
            "Schedule annual full-body skin checks",
            "Photograph the lesion monthly to track changes"
        ],
        "diet_suggestions": [
            "Eat antioxidant-rich foods: berries, leafy greens",
            "Stay well hydrated (8+ glasses of water/day)",
            "Omega-3 fatty acids for skin health",
            "Vitamin E and C rich foods"
        ],
        "consult_doctor": [
            "If the mole changes size, shape, or color (ABCDE rule)",
            "If it bleeds, itches, or becomes painful",
            "Annual dermatologist screening is recommended"
        ]
    },
    "eczema": {
        "home_remedies": [
            "Keep skin moisturized with thick creams (Vaseline, Cetaphil)",
            "Use lukewarm (not hot) water for bathing",
            "Oatmeal baths to soothe itching",
            "Wear soft, breathable cotton clothing",
            "Avoid known triggers: dust, pet dander, harsh soaps"
        ],
        "skincare_routine": [
            "Apply fragrance-free moisturizer within 3 minutes of bathing",
            "Use gentle, soap-free cleansers only",
            "Avoid products with alcohol or fragrances",
            "Apply prescribed topical corticosteroids as directed"
        ],
        "diet_suggestions": [
            "Increase omega-3: salmon, walnuts, flaxseed",
            "Probiotic-rich foods: yogurt, kefir, kimchi",
            "Avoid common triggers: dairy, eggs, gluten (if sensitive)",
            "Stay hydrated to support skin barrier"
        ],
        "consult_doctor": [
            "If eczema covers a large area or is severe",
            "If the skin becomes infected (yellow crusts, oozing)",
            "If itching disrupts sleep regularly",
            "For prescription immunomodulators or biologics"
        ]
    },
    "malignant": {
        "home_remedies": [
            "⚠️ URGENT: Seek immediate medical attention",
            "Do NOT attempt to treat at home",
            "Avoid any sun exposure on the affected area",
            "Cover with clean, non-adhesive bandage if needed"
        ],
        "skincare_routine": [
            "Apply high SPF (50+) sunscreen to all exposed skin",
            "Follow your oncologist's wound care instructions exactly",
            "Avoid any irritants on or near the lesion",
            "Keep follow-up appointments strictly"
        ],
        "diet_suggestions": [
            "Anti-inflammatory diet: Mediterranean style",
            "Antioxidant-rich foods: blueberries, spinach, tomatoes",
            "Limit processed meats and alcohol",
            "Consult oncology nutritionist for personalized plan"
        ],
        "consult_doctor": [
            "⚠️ IMMEDIATE consultation with a dermatologist/oncologist required",
            "Do not delay — early treatment dramatically improves outcomes",
            "Ask about biopsy, staging, and treatment options"
        ]
    },
    "non acne": {
        "home_remedies": [
            "Keep skin clean with gentle cleanser",
            "Avoid touching or picking the affected area",
            "Apply cold compress to reduce redness",
            "Use non-comedogenic products only"
        ],
        "skincare_routine": [
            "Use gentle, non-comedogenic skincare products",
            "Light chemical exfoliation (AHA/BHA) once a week",
            "Oil-free moisturizer and sunscreen",
            "Remove makeup thoroughly before bed"
        ],
        "diet_suggestions": [
            "Drink 8+ glasses of water daily",
            "Eat a diet rich in fruits and vegetables",
            "Reduce processed/junk food intake",
            "Include vitamin C-rich foods for skin clarity"
        ],
        "consult_doctor": [
            "If spots persist for more than 6 weeks",
            "If you are unsure of the nature of the skin lesion"
        ]
    },
    "normal skin": {
        "home_remedies": [
            "Maintain your current skincare routine",
            "Stay well hydrated throughout the day",
            "Get 7-9 hours of quality sleep",
            "Manage stress with exercise or meditation"
        ],
        "skincare_routine": [
            "Cleanse morning and night with gentle cleanser",
            "Apply antioxidant serum (Vitamin C) in the morning",
            "Moisturize daily to maintain skin barrier",
            "Always apply SPF 30+ sunscreen before going out"
        ],
        "diet_suggestions": [
            "Balanced diet: fruits, vegetables, lean protein",
            "Drink 8 glasses of water daily",
            "Limit alcohol and processed foods",
            "Omega-3 rich foods for skin glow"
        ],
        "consult_doctor": []
    },
    "psoriasis": {
        "home_remedies": [
            "Apply pure aloe vera gel to plaques",
            "Moderate sun exposure (10-15 min/day) for Vitamin D",
            "Apple cider vinegar diluted on scalp plaques",
            "Dead Sea salt baths to reduce scaling",
            "Keep skin moisturized to prevent cracking"
        ],
        "skincare_routine": [
            "Use coal tar or salicylic acid shampoos for scalp",
            "Apply thick emollients immediately after bathing",
            "Avoid scratching — use patting motion on itchy skin",
            "Targeted prescription topicals as advised by doctor"
        ],
        "diet_suggestions": [
            "Anti-inflammatory Mediterranean diet",
            "Avoid alcohol (proven psoriasis trigger)",
            "Reduce red meat and processed foods",
            "Omega-3 rich foods: fish, walnuts, flaxseed",
            "Turmeric supplements (consult doctor first)"
        ],
        "consult_doctor": [
            "If psoriasis covers more than 10% of body surface",
            "If joints are painful or swollen (psoriatic arthritis)",
            "For phototherapy (UVB/PUVA) treatments",
            "For systemic medications or biologics"
        ]
    },
    "vitiligo": {
        "home_remedies": [
            "Apply SPF 50+ sunscreen on depigmented patches daily",
            "Ginkgo biloba extract (consult doctor before use)",
            "Turmeric + mustard oil paste on affected areas",
            "Protect skin from sunburn — depigmented skin burns easily",
            "Use cosmetic camouflage makeup if preferred"
        ],
        "skincare_routine": [
            "Broad-spectrum SPF 50+ sunscreen is essential",
            "Use skin camouflage products for aesthetic coverage",
            "Gentle, fragrance-free cleansers only",
            "Keep the skin moisturized to maintain barrier"
        ],
        "diet_suggestions": [
            "Antioxidant-rich foods: berries, spinach, broccoli",
            "Folic acid sources: spinach, fortified cereals, lentils",
            "Vitamin B12: eggs, dairy, fortified foods",
            "Copper-rich foods: nuts, seeds, shellfish",
            "Avoid Vitamin C supplements (may reduce pigment)"
        ],
        "consult_doctor": [
            "For NB-UVB phototherapy (most effective treatment)",
            "For topical tacrolimus or corticosteroids",
            "For surgical options (skin grafting) in stable vitiligo",
            "For newer oral JAK inhibitors (ruxolitinib)"
        ]
    }
}

def get_remedies(disease_name: str) -> dict:
    """
    Case-insensitive lookup of remedies for the predicted disease.
    Falls back to a generic response if disease is unknown.
    """
    key = disease_name.lower().strip()
    return REMEDIES_MAP.get(key, {
        "home_remedies": ["Consult a dermatologist for proper diagnosis", "Keep affected area clean"],
        "skincare_routine": ["Gentle cleansing twice daily", "Apply broad-spectrum SPF 30+ sunscreen"],
        "diet_suggestions": ["Maintain a balanced, nutritious diet", "Stay well hydrated"],
        "consult_doctor": ["Please consult a dermatologist for professional evaluation"]
    })


@router.post("")
async def predict_skin_condition(
    file: UploadFile = File(...),
    current_user: Optional[dict] = Depends(optional_login)
):
    if not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="Invalid file type. Please upload an image.")

    # Read image bytes for DB storage
    image_bytes = await file.read()
    # Reset file pointer for the shutil.copyfileobj if we still use it (though we can just write image_bytes)
    file.file.seek(0)
    
    # Secure the filename against path traversal

    safe_filename = os.path.basename(file.filename) if file.filename else ""
    ext = os.path.splitext(safe_filename)[1] or ".jpg"
    
    temp_filename = f"upload_{uuid.uuid4().hex}{ext}"
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
        # Using image_bytes directly instead of reading back from disk (Performance Fix)
        # ────────────────────────────────────────────────────────────────────────
        
        # Decode: handle JPEG and PNG
        ext_lower = ext.lower()
        if ext_lower in (".png",):
            img_tensor = tf.image.decode_png(image_bytes, channels=3)
        else:
            try:
                img_tensor = tf.image.decode_jpeg(image_bytes, channels=3)
            except Exception:
                img_tensor = tf.image.decode_image(image_bytes, channels=3, expand_animations=False)


        # Resize with BILINEAR (exactly as training)
        img_tensor = tf.image.resize(img_tensor, (224, 224), method=tf.image.ResizeMethod.BILINEAR)

        # Cast to float32 — raw [0, 255] range (model handles normalization internally)
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
        print(f"[PREDICT] Top-3: {[(t['disease'], t['confidence']) for t in top3]}")

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
