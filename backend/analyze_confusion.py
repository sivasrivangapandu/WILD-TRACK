"""Analyze confusion matrix in detail — find exact problem pairs."""
import os, warnings
warnings.filterwarnings('ignore')
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'

import numpy as np
import tensorflow as tf
from sklearn.metrics import confusion_matrix, classification_report
from keras.preprocessing import image

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MODEL_PATH = os.path.join(BASE_DIR, "models", "wildtrack_complete_model.h5")
DATASET_DIR = os.path.join(BASE_DIR, "dataset_cleaned")

model = tf.keras.models.load_model(MODEL_PATH, compile=False)
print("Model loaded")

gen = image.ImageDataGenerator(validation_split=0.2)
val = gen.flow_from_directory(DATASET_DIR, target_size=(300,300), batch_size=32,
                              class_mode='categorical', subset='validation', shuffle=False)

preds = model.predict(val, verbose=0)
y_pred = np.argmax(preds, axis=1)
y_true = val.classes
names = list(val.class_indices.keys())
confidences = np.max(preds, axis=1)

cm = confusion_matrix(y_true, y_pred)

print("\n" + "="*60)
print("CONFUSION MATRIX (rows=true, cols=predicted)")
print("="*60)
header = "         " + "  ".join(f"{n:>8}" for n in names)
print(header)
for i, row in enumerate(cm):
    print(f"{names[i]:>8} " + "  ".join(f"{v:>8}" for v in row))

print("\n" + "="*60)
print("KEY CONFUSION PAIRS (>= 3 misclassified)")
print("="*60)
for i in range(len(names)):
    for j in range(len(names)):
        if i != j and cm[i][j] >= 3:
            pct = cm[i][j] / cm[i].sum() * 100
            print(f"  {names[i]:>8} -> {names[j]:<8}: {cm[i][j]:>3} samples ({pct:.1f}%)")

# Find the most confused TRAINING images (not just validation)
print("\n" + "="*60)
print("SCANNING ALL TRAINING IMAGES FOR WORST CONFUSIONS")
print("="*60)

all_gen = image.ImageDataGenerator()
all_data = all_gen.flow_from_directory(DATASET_DIR, target_size=(300,300), batch_size=32,
                                       class_mode='categorical', shuffle=False)

all_preds = model.predict(all_data, verbose=0)
all_files = all_data.filenames
all_true = all_data.classes

# Find images where model is CONFIDENT about the WRONG class
confused = []
for idx in range(len(all_files)):
    true_cls = all_true[idx]
    pred_cls = np.argmax(all_preds[idx])
    true_prob = all_preds[idx][true_cls]
    pred_prob = all_preds[idx][pred_cls]
    
    if pred_cls != true_cls and pred_prob > 0.4:
        confused.append({
            'file': all_files[idx],
            'true': names[true_cls],
            'predicted': names[pred_cls],
            'true_prob': true_prob,
            'pred_prob': pred_prob,
        })

confused.sort(key=lambda x: x['pred_prob'], reverse=True)

print(f"\nFound {len(confused)} confidently wrong predictions (>40% for wrong class)")
print(f"\nTop 50 most confused images:")
print(f"{'File':<35} {'True':<10} {'Predicted':<10} {'TrueProb':>9} {'PredProb':>9}")
print("-" * 75)
for c in confused[:50]:
    print(f"{c['file']:<35} {c['true']:<10} {c['predicted']:<10} {c['true_prob']:>8.3f} {c['pred_prob']:>9.3f}")

# Count confusion by pair
pair_counts = {}
for c in confused:
    pair = f"{c['true']}->{c['predicted']}"
    pair_counts[pair] = pair_counts.get(pair, 0) + 1

print(f"\nConfusion pair summary:")
for pair, count in sorted(pair_counts.items(), key=lambda x: -x[1]):
    print(f"  {pair}: {count} images")

# Per-class "borderline" images — low confidence for correct class
print("\n" + "="*60)
print("BORDERLINE IMAGES (correct class prob 0.15-0.30)")
print("="*60)
borderline = []
for idx in range(len(all_files)):
    true_cls = all_true[idx]
    true_prob = all_preds[idx][true_cls]
    if 0.15 <= true_prob <= 0.30:
        borderline.append({
            'file': all_files[idx],
            'true': names[true_cls],
            'true_prob': true_prob,
        })

print(f"Found {len(borderline)} borderline images")
for sp in names:
    sp_border = [b for b in borderline if b['true'] == sp]
    print(f"  {sp}: {len(sp_border)} borderline")

# Total per-class counts
print("\n" + "="*60)
print("CURRENT CLASS DISTRIBUTION")
print("="*60)
for sp in names:
    count = sum(1 for c in all_true if c == names.index(sp))
    n_confused = sum(1 for c in confused if c['true'] == sp)
    n_border = sum(1 for b in borderline if b['true'] == sp)
    print(f"  {sp:>10}: {count:>4} images, {n_confused:>3} confidently wrong, {n_border:>3} borderline")
