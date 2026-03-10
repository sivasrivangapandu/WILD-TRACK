import os
import cv2
import numpy as np
import tensorflow as tf
import json

# Setup
os.chdir(r"d:\Wild Track AI\backend")
model_path = r"models\wildtrack_complete_model.h5"
model = tf.keras.models.load_model(model_path, compile=False)
meta = json.load(open(r"models\model_metadata.json"))
class_names = meta["class_names"]

img_path = r"c:\Users\abhis\Downloads\elephant-footprint.jpg"
contents = open(img_path, "rb").read()

def diag_preprocess(contents, method=cv2.INTER_AREA):
    nparr = np.frombuffer(contents, np.uint8)
    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    # Match main.py exactly
    img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    img_resized = cv2.resize(img, (160, 160), interpolation=method)
    img_array = img_resized.astype('float32')
    # Save for visual check
    cv2.imwrite(f"diag_{'area' if method==cv2.INTER_AREA else 'linear'}.jpg", cv2.cvtColor(img_resized, cv2.COLOR_RGB2BGR))
    return np.expand_dims(img_array, axis=0)

print("--- Testing INTER_AREA ---")
arr_area = diag_preprocess(contents, cv2.INTER_AREA)
probs_area = model.predict(arr_area, verbose=0)[0]
for cls, p in zip(class_names, probs_area):
    print(f"  {cls}: {p:.4f}")

print("\n--- Testing INTER_LINEAR ---")
arr_linear = diag_preprocess(contents, cv2.INTER_LINEAR)
probs_linear = model.predict(arr_linear, verbose=0)[0]
for cls, p in zip(class_names, probs_linear):
    print(f"  {cls}: {p:.4f}")

# Compare
pred_area = class_names[np.argmax(probs_area)]
pred_linear = class_names[np.argmax(probs_linear)]
print(f"\nPred AREA: {pred_area}")
print(f"Pred LINEAR: {pred_linear}")
