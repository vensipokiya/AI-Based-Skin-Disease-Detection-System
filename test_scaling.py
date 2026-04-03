import tensorflow as tf
import numpy as np
import os
import json

MODEL_PATH = r"backend/skin_disease_efficientnetV2_final.h5"
CLASSES_PATH = r"backend/skin_disease_efficientnetV2_final_classes.json"
TEST_IMAGE = r"backend/app/uploads/user_uploads/140f6db818d04ec3b68c4669f27ccc88.jpg"

if not os.path.exists(MODEL_PATH) or not os.path.exists(TEST_IMAGE):
    print("Files missing.")
    exit(1)

model = tf.keras.models.load_model(MODEL_PATH)
with open(CLASSES_PATH, "r") as f:
    classes = json.load(f)

img_bytes = open(TEST_IMAGE, "rb").read()
img_tensor = tf.image.decode_jpeg(img_bytes, channels=3)
img_tensor = tf.image.resize(img_tensor, (224, 224))

# Case 1: No scaling [0, 255]
img1 = tf.cast(img_tensor, tf.float32).numpy()
img1 = np.expand_dims(img1, axis=0)
preds1 = model.predict(img1, verbose=0)[0]
idx1 = np.argmax(preds1)

# Case 2: Normalized [0, 1]
img2 = img1 / 255.0
preds2 = model.predict(img2, verbose=0)[0]
idx2 = np.argmax(preds2)

# Case 3: Standard MobileNet [-1, 1]
img3 = (img1 / 127.5) - 1.0
preds3 = model.predict(img3, verbose=0)[0]
idx3 = np.argmax(preds3)

# Case 4: BGR Unscaled
img4 = img1[..., ::-1] # Swapping channels to BGR
preds4 = model.predict(img4, verbose=0)[0]
idx4 = np.argmax(preds4)

print(f"Case 1 (RGB Unscaled): Class={classes.get(str(idx1))}, Conf={preds1[idx1]:.4f}")
print(f"Case 2 (0-1):          Class={classes.get(str(idx2))}, Conf={preds2[idx2]:.4f}")
print(f"Case 3 (-1 to 1):      Class={classes.get(str(idx3))}, Conf={preds3[idx3]:.4f}")
print(f"Case 4 (BGR Unscaled): Class={classes.get(str(idx4))}, Conf={preds4[idx4]:.4f}")

