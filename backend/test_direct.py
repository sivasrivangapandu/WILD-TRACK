"""Test: raw model prediction (no TTA, no temp scaling, no geo-filter)"""
import os, sys
os.chdir(r"d:\Wild Track AI\backend")
sys.path.insert(0, ".")

import numpy as np
import cv2
import json

# Suppress TF warnings
os.environ["TF_CPP_MIN_LOG_LEVEL"] = "3"
import tensorflow as tf

# Load model
model_path = r"d:\Wild Track AI\backend\models\wildtrack_complete_model.h5"
model = tf.keras.models.load_model(model_path)

# Load metadata
with open(r"d:\Wild Track AI\backend\models\model_metadata.json") as f:
    meta = json.load(f)
class_names = meta["class_names"]
img_size = meta["img_size"]

print("Model loaded. Classes:", class_names, "Size:", img_size)

# Load user's image
img = cv2.imread(r"c:\Users\abhis\Downloads\elephant-footprint.jpg")
print("Image shape (BGR):", img.shape)

# Convert BGR to RGB (matching training pipeline)
img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)

# Simple resize (matching training pipeline)  
img_resized = cv2.resize(img_rgb, (img_size, img_size), interpolation=cv2.INTER_LINEAR)

# Float32 (matching training pipeline)
img_array = img_resized.astype("float32")
img_array = np.expand_dims(img_array, axis=0)

print("\nInput shape:", img_array.shape, "Range:", img_array.min(), "-", img_array.max())

# Raw prediction (no TTA, no temperature, no geo-filter)
raw_probs = model.predict(img_array, verbose=0)[0]
print("\n=== RAW MODEL OUTPUT (no TTA, no temp scaling) ===")
for i, (cls, prob) in enumerate(zip(class_names, raw_probs)):
    marker = " <-- PREDICTED" if i == np.argmax(raw_probs) else ""
    print("  %s: %.2f%%%s" % (cls, prob * 100, marker))

# Also test WITHOUT RGB conversion (to see if BGR gives different results)
img_bgr_resized = cv2.resize(img, (img_size, img_size), interpolation=cv2.INTER_LINEAR)
img_bgr_array = img_bgr_resized.astype("float32")
img_bgr_array = np.expand_dims(img_bgr_array, axis=0)

bgr_probs = model.predict(img_bgr_array, verbose=0)[0]
print("\n=== BGR INPUT (wrong color channel order) ===")
for i, (cls, prob) in enumerate(zip(class_names, bgr_probs)):
    marker = " <-- PREDICTED" if i == np.argmax(bgr_probs) else ""
    print("  %s: %.2f%%%s" % (cls, prob * 100, marker))

# Test with temperature scaling
T = 1.2
scaled = np.exp(np.log(raw_probs + 1e-10) / T)
scaled = scaled / scaled.sum()
print("\n=== WITH TEMPERATURE T=1.2 ===")
for i, (cls, prob) in enumerate(zip(class_names, scaled)):
    marker = " <-- PREDICTED" if i == np.argmax(scaled) else ""
    print("  %s: %.2f%%%s" % (cls, prob * 100, marker))
