import tensorflow as tf
import os
import json

MODEL_PATH = r"backend/skin_disease_efficientnetV2_final.h5"
CLASSES_PATH = r"backend/skin_disease_efficientnetV2_final_classes.json"

if not os.path.exists(MODEL_PATH):
    print(f"Model not found at {MODEL_PATH}")
    exit(1)

try:
    model = tf.keras.models.load_model(MODEL_PATH)
    print("--- Model Summary ---")
    model.summary()
    print("--- Input Shape ---")
    print(model.input_shape)
    print("--- Output Shape ---")
    print(model.output_shape)
    
    if os.path.exists(CLASSES_PATH):
        with open(CLASSES_PATH, "r") as f:
            classes = json.load(f)
            print("--- Classes ---")
            print(classes)
except Exception as e:
    print(f"Error loading model: {e}")
