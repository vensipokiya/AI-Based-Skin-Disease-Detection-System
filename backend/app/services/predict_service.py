import tensorflow as tf
import numpy as np
import json
import os
from ..config.settings import settings
from ..utils.remedies import get_remedies
from ..utils.logger import get_logger

logger = get_logger(__name__)

class PredictService:
    """Service layer for AI skin disease detection using TensorFlow."""
    _model = None
    _labels = None

    @classmethod
    def load_assets(cls):
        """Pre-loads AI model and class labels into memory for faster inference."""
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

    def predict(self, image_bytes: bytes) -> dict:
        """
        Runs AI inference on the provided image bytes.
        Implements standardized preprocessing for EfficientNetV2:
        1. Decode and convert to RGB
        2. Resize to 224x224 using BILINEAR interpolation
        3. Normalize pixel values to [0, 1] range
        """
        self.load_assets()
        if self._model is None or self._labels is None:
            raise ValueError("AI Model or labels not loaded on the server.")

        try:
            # Preprocessing Tensor operation
            img_batch = self._preprocess_image(image_bytes)

            # Predict
            pred_probs_batch = self._model.predict(img_batch, verbose=0)
            pred_probs = pred_probs_batch[0]
            
            return self._format_predictions(pred_probs)
        except Exception as e:
            logger.error(f"PredictService Error: {str(e)}")
            raise e

    def _preprocess_image(self, image_bytes: bytes):
        """Converts raw bytes into a normalized tensor batch."""
        img_tensor = tf.io.decode_image(image_bytes, channels=3, expand_animations=False)
        img_tensor = tf.image.resize(img_tensor, (224, 224), method=tf.image.ResizeMethod.BILINEAR)
        img_array = tf.cast(img_tensor, tf.float32)
        return np.expand_dims(img_array.numpy(), axis=0)

    def _format_predictions(self, pred_probs: np.ndarray) -> dict:
        """Maps probabilities to disease names and adds risk alerts."""
        class_indices = list(range(len(self._labels)))
        classes = [self._labels.get(str(i), "Unknown").replace("_", " ") for i in class_indices]
        top_3_idx = pred_probs.argsort()[-3:][::-1]
        
        top_3 = [
            {
                "disease": classes[i] if i < len(classes) else "Unknown", 
                "confidence": round(float(pred_probs[i]) * 100, 1)
            }
            for i in top_3_idx
        ]
        
        result_disease = top_3[0]["disease"]
        confidence = top_3[0]["confidence"]

        # Alert logic for high-risk conditions
        alert = None
        high_risk = ["malignant", "melanoma", "basal cell carcinoma", "squamous cell carcinoma"]
        if result_disease.lower() in high_risk:
            alert = "⚠️ HIGH RISK DETECTED. Please consult a dermatologist as soon as possible for a professional biopsy."

        return {
            "disease": result_disease,
            "confidence": confidence,
            "remedies": get_remedies(result_disease),
            "top_predictions": top_3,
            "alert": alert
        }
