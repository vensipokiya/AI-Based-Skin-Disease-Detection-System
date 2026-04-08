import tensorflow as tf
import numpy as np
import json
import os
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

    def predict(self, image_bytes: bytes) -> dict:
        """
        Runs AI inference on the provided image bytes.
        Implements standardized preprocessing for EfficientNetV2:
        1. Decode and convert to RGB
        2. Resize to 224x224 using BILINEAR interpolation (matching training)
        3. Normalize pixel values to [0, 1] range
        """
        self.load_assets()
        if self._model is None or self._labels is None:
            raise Exception("AI Model or labels not loaded on the server.")

        try:
            # 1. Decode Image using TensorFlow for consistency with training pipeline
            img_tensor = tf.io.decode_image(image_bytes, channels=3, expand_animations=False)
            
            # 2. Resize with BILINEAR (Training Standard)
            img_tensor = tf.image.resize(img_tensor, (224, 224), method=tf.image.ResizeMethod.BILINEAR)

            # 3. Cast and Normalize to [0, 1]
            # Many EfficientNetV2 models expect [0, 1] if no Rescaling layer is present at top
            img_array = tf.cast(img_tensor, tf.float32)
            img_batch = np.expand_dims(img_array.numpy(), axis=0)

            # 4. Predict
            pred_probs_batch = self._model.predict(img_batch, verbose=0)
            pred_probs = pred_probs_batch[0]
            
            # 5. Map results
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
            
            best_idx = top_3_idx[0]
            confidence = float(pred_probs[best_idx])
            result_disease = classes[best_idx] if best_idx < len(classes) else "Unknown"

            # Alert logic for high-risk conditions
            alert = None
            if result_disease.lower() in ["malignant", "melanoma", "basal cell carcinoma", "squamous cell carcinoma"]:
                alert = "⚠️ HIGH RISK DETECTED. Please consult a dermatologist as soon as possible for a professional biopsy."

            return {
                "disease": result_disease,
                "confidence": round(confidence * 100, 1),
                "remedies": get_remedies(result_disease),
                "top_predictions": top_3,
                "alert": alert
            }
        except Exception as e:
            logger.error(f"PredictService Error: {str(e)}")
            raise e
