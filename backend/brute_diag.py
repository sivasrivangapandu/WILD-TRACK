import os
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'
import tensorflow as tf
import numpy as np
import cv2
import json

# Setup
model_path = r"d:\Wild Track AI\backend\models\wildtrack_complete_model.h5"
meta_path = r"d:\Wild Track AI\backend\models\model_metadata.json"
img_path = r"c:\Users\abhis\Downloads\elephant-footprint.jpg"

model = tf.keras.models.load_model(model_path, compile=False)
meta = json.load(open(meta_path))
class_names = meta["class_names"]

def test_combination(img_bgr, norm_type, color_order, resize_method):
    # 1. Color
    img = img_bgr.copy()
    if color_order == "RGB":
        img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    
    # 2. Resize
    img = cv2.resize(img, (160, 160), interpolation=resize_method)
    
    # 3. Norm
    img = img.astype('float32')
    if norm_type == "float_0_1":
        img = img / 255.0
    elif norm_type == "float_neg1_1":
        img = (img / 127.5) - 1.0
    # else float_0_255
    
    arr = np.expand_dims(img, axis=0)
    preds = model.predict(arr, verbose=0)[0]
    best_idx = np.argmax(preds)
    return class_names[best_idx], preds[best_idx], preds

norms = ["float_0_255", "float_0_1", "float_neg1_1"]
colors = ["RGB", "BGR"]
resizes = [cv2.INTER_LINEAR, cv2.INTER_AREA, cv2.INTER_CUBIC]

img_bgr = cv2.imread(img_path)
print(f"Testing image: {img_path}")
print("-" * 60)
print(f"{'Normalization':<15} | {'Color':<5} | {'Resize':<10} | {'Pred Class':<10} | {'Conf'}")
print("-" * 60)

for n in norms:
    for c in colors:
        for r in resizes:
            r_name = "Linear" if r == cv2.INTER_LINEAR else "Area" if r == cv2.INTER_AREA else "Cubic"
            cls, conf, all_p = test_combination(img_bgr, n, c, r)
            marker = " (***)" if cls == "elephant" else ""
            print(f"{n:<15} | {c:<5} | {r_name:<10} | {cls:<10} | {conf:.2f}{marker}")
