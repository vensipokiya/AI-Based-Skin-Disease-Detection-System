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

    def predict(self, image_bytes: bytes, extension: str = "jpg") -> dict:
        self.load_assets()
        if self._model is None or self._labels is None:
            raise Exception("AI Assets or labels not available.")

        # Replicate preprocessing from predict_routes.py
        try:
            # Decode image
            if extension.lower() in (".png",):
                img_tensor = tf.image.decode_png(image_bytes, channels=3)
            else:
                try:
                    img_tensor = tf.image.decode_jpeg(image_bytes, channels=3)
                except:
                    img_tensor = tf.image.decode_image(image_bytes, channels=3, expand_animations=False)

            # Resize and process
            img_tensor = tf.image.resize(img_tensor, (224, 224), method=tf.image.ResizeMethod.BILINEAR)
            img_array = tf.cast(img_tensor, tf.float32).numpy()
            img_batch = np.expand_dims(img_array, axis=0)

            # Predict
            predictions = self._model.predict(img_batch, verbose=0)
            pred_probs = predictions[0]

            top_idx = int(np.argmax(pred_probs))
            confidence = float(pred_probs[top_idx]) * 100
            disease_name = self._labels.get(str(top_idx), "Unknown").replace("_", " ")

            # Top-3 predictions
            top3_indices = np.argsort(pred_probs)[::-1][:3]
            top3 = [
                {
                    "disease": self._labels.get(str(int(i)), "Unknown").replace("_", " "),
                    "confidence": round(float(pred_probs[i]) * 100, 1)
                }
                for i in top3_indices
            ]

            return {
                "disease": disease_name,
                "confidence": round(confidence, 1),
                "remedies": get_remedies(disease_name),
                "top_predictions": top3
            }
        except Exception as e:
            logger.error(f"Prediction error: {e}")
            raise e
