"""FAST verification of temperature scaling fix using batch prediction."""
import os, sys, numpy as np
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))
import tensorflow as tf

MODEL_PATH = os.path.join('backend', 'models', 'wildtrack_complete_model.h5')
DATA_DIR = os.path.join('backend', 'dataset')
IMG_SIZE = (300, 300)

model = tf.keras.models.load_model(MODEL_PATH)
class_names = sorted(os.listdir(DATA_DIR))
print(f"Classes: {class_names}\n")

# --- Quick sample test (3 per class) ---
print("SAMPLE PREDICTIONS (3 per class):")
print("-" * 100)
for cls in class_names:
    cls_dir = os.path.join(DATA_DIR, cls)
    imgs = os.listdir(cls_dir)[:3]
    for img_name in imgs:
        img_path = os.path.join(cls_dir, img_name)
        img = tf.keras.utils.load_img(img_path, target_size=IMG_SIZE)
        img_array = tf.keras.utils.img_to_array(img)  # [0,255] — EfficientNet has internal Rescaling
        img_array = np.expand_dims(img_array, 0)
        
        raw_probs = model.predict(img_array, verbose=0)[0]
        
        # OLD broken (double-softmax)
        s = raw_probs / 1.8
        e = np.exp(s - np.max(s))
        probs_old = e / np.sum(e)
        
        # NEW fixed
        logits = np.log(raw_probs + 1e-10)
        s = logits / 1.5
        e = np.exp(s - np.max(s))
        probs_new = e / np.sum(e)
        
        ok = "OK" if class_names[np.argmax(probs_new)] == cls else "XX"
        print(f"  {ok} [{cls:>8}] Raw={np.max(raw_probs):.1%} OLD={np.max(probs_old):.1%} NEW={np.max(probs_new):.1%}  pred={class_names[np.argmax(probs_new)]}")

# --- Batch test across full dataset ---
print("\n" + "="*80)
print("FULL DATASET (batch prediction)")
print("="*80)

# Load all images into arrays
all_images = []
all_labels = []
for cls_idx, cls in enumerate(class_names):
    cls_dir = os.path.join(DATA_DIR, cls)
    for img_name in os.listdir(cls_dir):
        try:
            img = tf.keras.utils.load_img(os.path.join(cls_dir, img_name), target_size=IMG_SIZE)
            all_images.append(tf.keras.utils.img_to_array(img))  # [0,255] — EfficientNet internal Rescaling
            all_labels.append(cls_idx)
        except:
            pass

X = np.array(all_images)
y = np.array(all_labels)
print(f"Loaded {len(X)} images")

# Batch predict
raw_probs = model.predict(X, verbose=1, batch_size=32)

# OLD broken
s_old = raw_probs / 1.8
e_old = np.exp(s_old - s_old.max(axis=1, keepdims=True))
probs_old = e_old / e_old.sum(axis=1, keepdims=True)

# NEW fixed (T=1.5)
logits = np.log(raw_probs + 1e-10)
s_new = logits / 1.5
e_new = np.exp(s_new - s_new.max(axis=1, keepdims=True))
probs_new = e_new / e_new.sum(axis=1, keepdims=True)

# Also test T=1.0 (no scaling), T=1.2, T=2.0
for T_val in [1.0, 1.2, 1.5, 2.0]:
    s = logits / T_val
    e = np.exp(s - s.max(axis=1, keepdims=True))
    p = e / e.sum(axis=1, keepdims=True)
    acc = np.mean(np.argmax(p, axis=1) == y)
    above50 = np.mean(np.max(p, axis=1) > 0.5)
    avg_conf = np.mean(np.max(p, axis=1))
    print(f"  T={T_val:.1f}: accuracy={acc:.1%}, above_50%={above50:.1%}, avg_max_conf={avg_conf:.1%}")

# Old broken stats
acc_old = np.mean(np.argmax(probs_old, axis=1) == y)
above50_old = np.mean(np.max(probs_old, axis=1) > 0.5)
print(f"\n  OLD BROKEN (T=1.8 double-softmax): accuracy={acc_old:.1%}, above_50%={above50_old:.1%}")

# Threshold analysis with new T=1.5
print("\n" + "="*80)
print("THRESHOLD ANALYSIS (with fixed T=1.5)")
print("="*80)
for threshold in [0.30, 0.40, 0.50, 0.60, 0.70, 0.80]:
    mask = np.max(probs_new, axis=1) >= threshold
    n_above = mask.sum()
    if n_above > 0:
        acc_above = np.mean(np.argmax(probs_new[mask], axis=1) == y[mask])
    else:
        acc_above = 0
    pct = n_above / len(y)
    print(f"  Threshold {threshold:.0%}: {n_above}/{len(y)} ({pct:.1%}) pass, accuracy among passed = {acc_above:.1%}")

# Entropy analysis with fixed scaling
ent_new = -np.sum(probs_new * np.log2(probs_new + 1e-10), axis=1)
max_ent = np.log2(5)
ent_ratio = ent_new / max_ent
print(f"\nEntropy (fixed T=1.5): mean={np.mean(ent_new):.3f}, mean_ratio={np.mean(ent_ratio):.3f}")
print(f"Entropy ratio < 0.85: {np.sum(ent_ratio < 0.85)}/{len(y)} ({np.mean(ent_ratio < 0.85):.1%})")
print(f"Entropy ratio < 0.70: {np.sum(ent_ratio < 0.70)}/{len(y)} ({np.mean(ent_ratio < 0.70):.1%})")
