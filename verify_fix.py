"""Verify double-softmax fix — compare old vs new temperature scaling."""
import os, sys, numpy as np
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))
import tensorflow as tf

MODEL_PATH = os.path.join('backend', 'training', 'models', 'wildlife_footprint_model.h5')
DATA_DIR = os.path.join('backend', 'training', 'data', 'cleaned')
IMG_SIZE = (300, 300)

model = tf.keras.models.load_model(MODEL_PATH)
class_names = sorted(os.listdir(DATA_DIR))
print(f"Classes: {class_names}\n")

# Test on a few images from each class
for cls in class_names:
    cls_dir = os.path.join(DATA_DIR, cls)
    imgs = os.listdir(cls_dir)[:3]
    for img_name in imgs:
        img_path = os.path.join(cls_dir, img_name)
        img = tf.keras.utils.load_img(img_path, target_size=IMG_SIZE)
        img_array = tf.keras.utils.img_to_array(img) / 255.0
        img_array = np.expand_dims(img_array, 0)
        
        raw_probs = model.predict(img_array, verbose=0)[0]
        
        # OLD broken method (double-softmax)
        T_old = 1.8
        scaled_old = raw_probs / T_old
        exp_old = np.exp(scaled_old - np.max(scaled_old))
        probs_old = exp_old / np.sum(exp_old)
        
        # NEW fixed method (log → logits → scale → softmax)
        T_new = 1.5
        logits = np.log(raw_probs + 1e-10)
        scaled_new = logits / T_new
        exp_new = np.exp(scaled_new - np.max(scaled_new))
        probs_new = exp_new / np.sum(exp_new)
        
        pred_old = class_names[np.argmax(probs_old)]
        conf_old = np.max(probs_old)
        pred_new = class_names[np.argmax(probs_new)]
        conf_new = np.max(probs_new)
        pred_raw = class_names[np.argmax(raw_probs)]
        conf_raw = np.max(raw_probs)
        
        status = "✓" if pred_new == cls else "✗"
        print(f"{status} [{cls:>8}] Raw: {pred_raw} {conf_raw:.1%} | OLD(T=1.8): {pred_old} {conf_old:.1%} | NEW(T=1.5): {pred_new} {conf_new:.1%}")

# Summary stats across entire dataset
print("\n" + "="*80)
print("FULL DATASET ANALYSIS")
print("="*80)

total = 0
correct_raw = 0
correct_new = 0
above_50_raw = 0
above_50_new = 0
above_50_old = 0

for cls_idx, cls in enumerate(class_names):
    cls_dir = os.path.join(DATA_DIR, cls)
    for img_name in os.listdir(cls_dir):
        img_path = os.path.join(cls_dir, img_name)
        try:
            img = tf.keras.utils.load_img(img_path, target_size=IMG_SIZE)
        except:
            continue
        img_array = tf.keras.utils.img_to_array(img) / 255.0
        img_array = np.expand_dims(img_array, 0)
        
        raw_probs = model.predict(img_array, verbose=0)[0]
        
        # New method
        logits = np.log(raw_probs + 1e-10)
        scaled = logits / 1.5
        exp_l = np.exp(scaled - np.max(scaled))
        probs_new = exp_l / np.sum(exp_l)
        
        # Old method
        scaled_old = raw_probs / 1.8
        exp_old = np.exp(scaled_old - np.max(scaled_old))
        probs_old = exp_old / np.sum(exp_old)
        
        total += 1
        if np.argmax(raw_probs) == cls_idx:
            correct_raw += 1
        if np.argmax(probs_new) == cls_idx:
            correct_new += 1
        if np.max(raw_probs) > 0.5:
            above_50_raw += 1
        if np.max(probs_new) > 0.5:
            above_50_new += 1
        if np.max(probs_old) > 0.5:
            above_50_old += 1

print(f"\nTotal images: {total}")
print(f"Raw accuracy: {correct_raw}/{total} = {correct_raw/total:.1%}")
print(f"New (T=1.5) accuracy: {correct_new}/{total} = {correct_new/total:.1%}")
print(f"\nAbove 50% threshold:")
print(f"  Raw model:     {above_50_raw}/{total} = {above_50_raw/total:.1%}")
print(f"  OLD (T=1.8):   {above_50_old}/{total} = {above_50_old/total:.1%}  ← BROKEN")
print(f"  NEW (T=1.5):   {above_50_new}/{total} = {above_50_new/total:.1%}  ← FIXED")
