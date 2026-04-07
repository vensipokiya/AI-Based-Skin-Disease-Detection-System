import tensorflow as tf
import numpy as np
import cv2
import json
import os
from tensorflow.keras.applications.efficientnet import preprocess_input
from ..config.settings import settings
from ..utils.remedies import get_remedies
from ..utils.logger import get_logger

logger = get_logger(__name__)

class PredictService:
    _model = None
    _labels = None

    @classmethod
    def load_assets(cls):
        if cls._model is None and os.path.exists(settings.MODEL_PATH):
            try:
                cls._model = tf.keras.models.load_model(settings.MODEL_PATH)
                logger.info("AI Model loaded successfully.")
            except Exception as e:
                logger.error(f"Failed to load AI model: {e}")

        if cls._labels is None and os.path.exists(settings.CLASSES_PATH):
            try:
                with open(settings.CLASSES_PATH, "r") as f:
                    cls._labels = json.load(f)
                logger.info("AI Classes loaded successfully.")
            except Exception as e:
                logger.error(f"Failed to load AI classes: {e}")

    def predict(self, image_bytes: bytes, extension: str = "jpg") -> dict:
        self.load_assets()
        if self._model is None or self._labels is None:
            raise Exception("AI Assets or labels not available.")

        # Replicate preprocessing from predict_routes.py
        # ── Fix Image Preprocessing ──
        try:
            # Decode using cv2 from raw bytes
            nparr = np.frombuffer(image_bytes, np.uint8)
            img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            
            if img is None:
                raise ValueError("Could not decode image.")

            # Convert BGR to RGB (Required for standard Keras models)
            img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)

            # Resize to 224x224 and preprocess for EfficientNet
            img = cv2.resize(img, (224, 224))
            img = preprocess_input(img)
            img_batch = np.expand_dims(img, axis=0)

            # Predict using model direct call for speed
            predictions_tensor = self._model(img_batch, training=False)
            pred_probs = predictions_tensor[0].numpy()
            
            top_3_idx = pred_probs.argsort()[-3:][::-1]
            
            # Map labels to human-readable names
            classes = [self._labels.get(str(i), "Unknown").replace("_", " ") for i in range(len(self._labels))]
            
            top_3 = [
                {
                    "disease": classes[i] if i < len(classes) else "Unknown", 
                    "confidence": round(float(pred_probs[i]) * 100, 1)
                }
                for i in top_3_idx
            ]
            
            confidence = float(pred_probs[top_3_idx[0]])
            result_disease = classes[top_3_idx[0]] if top_3_idx[0] < len(classes) else "Unknown"

            # Alert logic (PRO Level Feature)
            alert = None
            if result_disease.lower() in ["malignant", "melanoma"]:
                alert = "⚠️ High risk detected. Please consult a doctor immediately."

            return {
                "disease": result_disease,
                "confidence": round(confidence * 100, 1),
                "remedies": get_remedies(result_disease),
                "top_predictions": top_3,
                "alert": alert
            }
        except Exception as e:
            logger.error(f"Prediction error: {e}")
            raise e
