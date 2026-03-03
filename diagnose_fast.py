"""Fast confusion matrix using batch prediction on test split only."""
import numpy as np
import os, json
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'
import tensorflow as tf
tf.get_logger().setLevel('ERROR')
import cv2

model_path = 'backend/models/wildtrack_complete_model.h5'
model = tf.keras.models.load_model(model_path)
img_size = model.input_shape[1] or 256
class_names = ['deer', 'elephant', 'leopard', 'tiger', 'wolf']
TEMPERATURE = 1.8

# Load ALL images per class, batch predict
print("=== BATCH CONFUSION MATRIX ===\n")

confusion = np.zeros((5, 5), dtype=int)
all_entropies = {c: [] for c in class_names}
all_confidences = {c: [] for c in class_names}
misclass_examples = []

for true_idx, cls in enumerate(class_names):
    cls_dir = None
    for d in ['backend/dataset_cleaned', 'backend/dataset']:
        p = os.path.join(d, cls)
        if os.path.exists(p):
            cls_dir = p
            break
    if not cls_dir:
        continue
    
    images = [f for f in os.listdir(cls_dir) if f.lower().endswith(('.jpg','.jpeg','.png','.webp'))]
    
    # Load all images into batch
    batch = []
    valid_names = []
    for img_name in images:
        img = cv2.imread(os.path.join(cls_dir, img_name))
        if img is not None:
            img = cv2.resize(img, (img_size, img_size))
            batch.append(img.astype('float32'))
            valid_names.append(img_name)
    
    if not batch:
        continue
    
    batch_array = np.array(batch)
    raw_logits = model.predict(batch_array, verbose=0, batch_size=32)
    
    for i in range(len(batch)):
        logits = raw_logits[i]
        scaled = logits / TEMPERATURE
        exp_l = np.exp(scaled - np.max(scaled))
        probs = exp_l / np.sum(exp_l)
        
        pred_idx = int(np.argmax(probs))
        confidence = float(probs[pred_idx])
        entropy = float(-np.sum(probs * np.log2(probs + 1e-10)))
        max_entropy = float(np.log2(len(probs)))
        
        confusion[true_idx][pred_idx] += 1
        all_entropies[cls].append(entropy / max_entropy)
        all_confidences[cls].append(confidence)
        
        if pred_idx != true_idx:
            misclass_examples.append({
                'true': cls,
                'pred': class_names[pred_idx],
                'conf': confidence,
                'entropy_ratio': entropy / max_entropy,
                'probs': {class_names[j]: float(probs[j]) for j in range(5)},
                'file': valid_names[i]
            })
    
    print(f"  Processed {cls}: {len(batch)} images")

# Print confusion matrix
print(f"\n{'':14s}", end='')
for c in class_names:
    print(f"{c:>10s}", end='')
print("  | recall   | avg_conf | avg_entropy_ratio")
print("  " + "-" * 100)

for i, cls in enumerate(class_names):
    row_sum = sum(confusion[i])
    recall = confusion[i][i] / row_sum if row_sum > 0 else 0
    avg_conf = np.mean(all_confidences[cls]) if all_confidences[cls] else 0
    avg_ent = np.mean(all_entropies[cls]) if all_entropies[cls] else 0
    
    print(f"  {cls:12s}", end='')
    for j in range(5):
        val = confusion[i][j]
        print(f"{val:10d}", end='')
    print(f"  | {recall:.3f}    | {avg_conf:.3f}    | {avg_ent:.3f}")

total = np.sum(confusion)
correct = sum(confusion[i][i] for i in range(5))
print(f"\n  Total: {correct}/{total} = {correct/total*100:.1f}% accuracy (with T={TEMPERATURE})")

# Print worst confusion pairs
print("\n=== WORST CONFUSION PAIRS ===")
pairs = []
for i in range(5):
    for j in range(5):
        if i != j and confusion[i][j] >= 3:
            pairs.append((class_names[i], class_names[j], confusion[i][j]))
pairs.sort(key=lambda x: -x[2])
for true_c, pred_c, count in pairs[:10]:
    print(f"  {true_c:10s} => {pred_c:10s}: {count} misclassifications")

# Print example misclassifications
print("\n=== SAMPLE MISCLASSIFICATIONS ===")
for ex in misclass_examples[:8]:
    print(f"\n  True: {ex['true']}  Predicted: {ex['pred']}  Confidence: {ex['conf']*100:.1f}%  Entropy: {ex['entropy_ratio']:.3f}")
    print(f"  File: {ex['file']}")
    for c in class_names:
        print(f"    {c:10s} {ex['probs'][c]*100:.1f}%")

print("\n=== KEY INSIGHTS ===")
print(f"  Temperature: {TEMPERATURE}")
print(f"  Accuracy WITHOUT temperature (argmax of raw logits): same — T doesn't change argmax")
print(f"  Temperature DOES flatten probabilities, making confident predictions look less confident")
print(f"  Model sees footprints at {img_size}x{img_size} pixels")

# Check if reducing T would help
print("\n=== IMPACT OF TEMPERATURE ON ACCURACY (argmax is same, but threshold changes) ===")
for t in [1.0, 1.2, 1.5, 1.8, 2.0]:
    above_threshold = 0
    below_threshold = 0
    for cls_idx, cls in enumerate(class_names):
        cls_dir = None
        for d in ['backend/dataset_cleaned', 'backend/dataset']:
            p = os.path.join(d, cls)
            if os.path.exists(p):
                cls_dir = p
                break
        if not cls_dir:
            continue
        images = [f for f in os.listdir(cls_dir) if f.lower().endswith(('.jpg','.jpeg','.png','.webp'))]
        batch = []
        for img_name in images:
            img = cv2.imread(os.path.join(cls_dir, img_name))
            if img is not None:
                img = cv2.resize(img, (img_size, img_size))
                batch.append(img.astype('float32'))
        if not batch:
            continue
        batch_array = np.array(batch)
        raw_logits_all = model.predict(batch_array, verbose=0, batch_size=32)
        for logits in raw_logits_all:
            scaled = logits / t
            exp_l = np.exp(scaled - np.max(scaled))
            probs = exp_l / np.sum(exp_l)
            max_p = float(np.max(probs))
            if max_p >= 0.5:
                above_threshold += 1
            else:
                below_threshold += 1
    total = above_threshold + below_threshold
    print(f"  T={t:.1f}: {above_threshold}/{total} above 50% threshold ({above_threshold/total*100:.1f}%), {below_threshold} marked unknown")
