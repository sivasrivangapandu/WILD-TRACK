"""FAST verification of temperature scaling fix using chunked batch prediction.
EfficientNet expects [0,255] pixel values (has internal Rescaling layer).
"""
import os, sys, numpy as np
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'

import tensorflow as tf

MODEL_PATH = os.path.join('backend', 'models', 'wildtrack_complete_model.h5')
DATA_DIR = os.path.join('backend', 'dataset')
IMG_SIZE = (300, 300)

model = tf.keras.models.load_model(MODEL_PATH, compile=False)
class_names = sorted(os.listdir(DATA_DIR))
print(f"Classes: {class_names}\n")

# --- Quick sample test (3 per class) ---
print("SAMPLE PREDICTIONS (3 per class):")
print("-" * 100)
for cls in class_names:
    cls_dir = os.path.join(DATA_DIR, cls)
    imgs = [f for f in os.listdir(cls_dir) if f.lower().endswith(('.jpg','.png','.jpeg'))][:3]
    for img_name in imgs:
        img_path = os.path.join(cls_dir, img_name)
        img = tf.keras.utils.load_img(img_path, target_size=IMG_SIZE)
        img_array = tf.keras.utils.img_to_array(img)  # [0,255] — EfficientNet internal Rescaling
        img_array = np.expand_dims(img_array, 0)
        
        raw_probs = model.predict(img_array, verbose=0)[0]
        
        # OLD broken (double-softmax with T=1.8)
        s = raw_probs / 1.8
        e = np.exp(s - np.max(s))
        probs_old = e / np.sum(e)
        
        # NEW fixed (log→logits→scale→softmax with T=1.5)
        logits = np.log(raw_probs + 1e-10)
        s = logits / 1.5
        e = np.exp(s - np.max(s))
        probs_new = e / np.sum(e)
        
        ok = "OK" if class_names[np.argmax(probs_new)] == cls else "XX"
        print(f"  {ok} [{cls:>8}] Raw: {class_names[np.argmax(raw_probs)]} {np.max(raw_probs):.1%} | "
              f"OLD(T=1.8): {np.max(probs_old):.1%} | NEW(T=1.5): {class_names[np.argmax(probs_new)]} {np.max(probs_new):.1%}")

# --- Chunked dataset processing ---
print("\n" + "="*80)
print("FULL DATASET (chunked processing)")
print("="*80)

# Collect all file paths and labels
all_paths = []
all_labels = []
for cls_idx, cls in enumerate(class_names):
    cls_dir = os.path.join(DATA_DIR, cls)
    for img_name in os.listdir(cls_dir):
        if img_name.lower().endswith(('.jpg', '.png', '.jpeg')):
            all_paths.append(os.path.join(cls_dir, img_name))
            all_labels.append(cls_idx)

all_labels = np.array(all_labels)
total = len(all_paths)
print(f"Total images: {total}")

# Process in chunks to avoid OOM
CHUNK_SIZE = 64
all_raw_probs = []

for start in range(0, total, CHUNK_SIZE):
    end = min(start + CHUNK_SIZE, total)
    batch = []
    for path in all_paths[start:end]:
        try:
            img = tf.keras.utils.load_img(path, target_size=IMG_SIZE)
            batch.append(tf.keras.utils.img_to_array(img))  # [0,255]
        except:
            batch.append(np.zeros((256, 256, 3), dtype=np.float32))
    
    X = np.array(batch)
    probs = model.predict(X, verbose=0, batch_size=32)
    all_raw_probs.append(probs)
    
    pct = end / total * 100
    if pct % 20 < (CHUNK_SIZE / total * 100):
        print(f"  Processing: {end}/{total} ({pct:.0f}%)")

raw_probs = np.vstack(all_raw_probs)
print(f"  Predictions shape: {raw_probs.shape}")

# Compute various temperature-scaled results
print("\nTemperature scaling comparison (FIXED method: log→logits→scale→softmax):")
logits = np.log(raw_probs + 1e-10)

for T_val in [1.0, 1.2, 1.5, 2.0]:
    s = logits / T_val
    e = np.exp(s - s.max(axis=1, keepdims=True))
    p = e / e.sum(axis=1, keepdims=True)
    acc = np.mean(np.argmax(p, axis=1) == all_labels)
    above50 = np.mean(np.max(p, axis=1) > 0.5)
    avg_conf = np.mean(np.max(p, axis=1))
    med_conf = np.median(np.max(p, axis=1))
    print(f"  T={T_val:.1f}: acc={acc:.1%}, >50%={above50:.1%}, avg_conf={avg_conf:.1%}, median_conf={med_conf:.1%}")

# Old broken stats
s_old = raw_probs / 1.8
e_old = np.exp(s_old - s_old.max(axis=1, keepdims=True))
probs_old = e_old / e_old.sum(axis=1, keepdims=True)
acc_old = np.mean(np.argmax(probs_old, axis=1) == all_labels)
above50_old = np.mean(np.max(probs_old, axis=1) > 0.5)
print(f"\n  OLD BROKEN (double-softmax T=1.8): acc={acc_old:.1%}, >50%={above50_old:.1%}")

# Raw model stats
acc_raw = np.mean(np.argmax(raw_probs, axis=1) == all_labels)
above50_raw = np.mean(np.max(raw_probs, axis=1) > 0.5)
avg_raw = np.mean(np.max(raw_probs, axis=1))
print(f"  RAW (no T-scaling):                acc={acc_raw:.1%}, >50%={above50_raw:.1%}, avg_conf={avg_raw:.1%}")

# Threshold analysis with fixed T=1.5
s_new = logits / 1.5
e_new = np.exp(s_new - s_new.max(axis=1, keepdims=True))
probs_new = e_new / e_new.sum(axis=1, keepdims=True)

print("\n" + "="*80)
print("THRESHOLD ANALYSIS (fixed T=1.5)")
print("="*80)
for threshold in [0.30, 0.40, 0.50, 0.60, 0.70, 0.80]:
    mask = np.max(probs_new, axis=1) >= threshold
    n_above = mask.sum()
    if n_above > 0:
        acc_above = np.mean(np.argmax(probs_new[mask], axis=1) == all_labels[mask])
    else:
        acc_above = 0
    pct = n_above / len(all_labels)
    print(f"  >={threshold:.0%}: {n_above}/{total} ({pct:.1%}) pass, accuracy={acc_above:.1%}")

# Entropy analysis
ent = -np.sum(probs_new * np.log2(probs_new + 1e-10), axis=1)
max_ent = np.log2(5)
ent_ratio = ent / max_ent
print(f"\nEntropy (T=1.5): mean={np.mean(ent):.3f}, mean_ratio={np.mean(ent_ratio):.3f}")
print(f"  Entropy ratio < 0.85: {np.sum(ent_ratio < 0.85)}/{total} ({np.mean(ent_ratio < 0.85):.1%})")
print(f"  Entropy ratio < 0.70: {np.sum(ent_ratio < 0.70)}/{total} ({np.mean(ent_ratio < 0.70):.1%})")
