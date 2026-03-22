"""STEP 1: Diagnose model accuracy — raw probability vectors, class distribution, per-class F1."""
import numpy as np
import json, os, sys, glob

# 1. Per-class performance from classification report
report_path = 'backend/models/evaluation/classification_report.json'
if os.path.exists(report_path):
    with open(report_path) as f:
        report = json.load(f)
    print('=== PER-CLASS PERFORMANCE ===')
    for cls in ['deer', 'elephant', 'leopard', 'tiger', 'wolf']:
        if cls in report:
            r = report[cls]
            print(f"  {cls:10s}  precision={r['precision']:.3f}  recall={r['recall']:.3f}  f1={r['f1-score']:.3f}  support={r['support']}")
    if 'accuracy' in report:
        print(f"\n  Overall accuracy: {report['accuracy']:.4f}")
    if 'weighted avg' in report:
        w = report['weighted avg']
        print(f"  Weighted F1: {w['f1-score']:.4f}")
else:
    print('No classification report found')

# 2. Dataset class distribution
print('\n=== DATASET CLASS DISTRIBUTION ===')
for d in ['dataset_cleaned', 'dataset']:
    dpath = f'backend/{d}'
    if os.path.exists(dpath):
        print(f"\n  {d}/")
        total = 0
        for cls_dir in sorted(os.listdir(dpath)):
            cls_path = os.path.join(dpath, cls_dir)
            if os.path.isdir(cls_path):
                count = len([f for f in os.listdir(cls_path) if f.lower().endswith(('.jpg','.jpeg','.png','.webp'))])
                bar = '█' * (count // 10) + '░' * max(0, 30 - count // 10)
                print(f"    {cls_dir:12s} {count:4d} |{bar}|")
                total += count
        print(f"    {'TOTAL':12s} {total:4d}")

# 3. Run raw predictions on sample images from each class
print('\n=== RAW SOFTMAX PREDICTIONS (sample per class) ===')
try:
    os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'
    import tensorflow as tf
    tf.get_logger().setLevel('ERROR')
    
    model_path = 'backend/models/wildtrack_complete_model.h5'
    model = tf.keras.models.load_model(model_path)
    
    # Detect input size
    input_shape = model.input_shape
    img_size = input_shape[1] if input_shape[1] else 256
    
    class_names = ['deer', 'elephant', 'leopard', 'tiger', 'wolf']
    
    import cv2
    
    TEMPERATURE = 1.8
    
    for cls in class_names:
        # Find a sample image
        for dataset_dir in ['backend/dataset_cleaned', 'backend/dataset']:
            cls_dir = os.path.join(dataset_dir, cls)
            if os.path.exists(cls_dir):
                images = [f for f in os.listdir(cls_dir) if f.lower().endswith(('.jpg','.jpeg','.png','.webp'))]
                if images:
                    img_path = os.path.join(cls_dir, images[len(images)//2])  # middle image
                    img = cv2.imread(img_path)
                    if img is not None:
                        img = cv2.resize(img, (img_size, img_size))
                        img_array = np.expand_dims(img.astype('float32'), axis=0)
                        
                        raw_logits = model.predict(img_array, verbose=0)[0]
                        
                        # Temperature scaling
                        scaled = raw_logits / TEMPERATURE
                        exp_l = np.exp(scaled - np.max(scaled))
                        probs = exp_l / np.sum(exp_l)
                        
                        # Entropy
                        entropy = float(-np.sum(probs * np.log2(probs + 1e-10)))
                        max_entropy = float(np.log2(len(probs)))
                        entropy_ratio = entropy / max_entropy
                        
                        pred_idx = int(np.argmax(probs))
                        pred_cls = class_names[pred_idx]
                        correct = "✓" if pred_cls == cls else "✗ WRONG"
                        
                        print(f"\n  True: {cls:10s}  Predicted: {pred_cls:10s}  {correct}")
                        print(f"  Image: {os.path.basename(img_path)}")
                        for i, c in enumerate(class_names):
                            bar = '█' * int(probs[i] * 40)
                            marker = " ◄ pred" if i == pred_idx else ""
                            print(f"    {c:10s} {probs[i]*100:6.2f}% |{bar}{marker}")
                        print(f"    Entropy: {entropy:.3f} bits  (ratio: {entropy_ratio:.3f})")
                        print(f"    Raw logits: {[f'{l:.3f}' for l in raw_logits]}")
                    break
            
    # 4. Confusion patterns — test ALL images
    print('\n=== CONFUSION MATRIX (full dataset) ===')
    confusion = np.zeros((5, 5), dtype=int)
    total_tested = 0
    
    for true_idx, cls in enumerate(class_names):
        for dataset_dir in ['backend/dataset_cleaned', 'backend/dataset']:
            cls_dir = os.path.join(dataset_dir, cls)
            if os.path.exists(cls_dir):
                images = [f for f in os.listdir(cls_dir) if f.lower().endswith(('.jpg','.jpeg','.png','.webp'))]
                for img_name in images:
                    img_path = os.path.join(cls_dir, img_name)
                    img = cv2.imread(img_path)
                    if img is not None:
                        img = cv2.resize(img, (img_size, img_size))
                        img_array = np.expand_dims(img.astype('float32'), axis=0)
                        raw_logits = model.predict(img_array, verbose=0)[0]
                        scaled = raw_logits / TEMPERATURE
                        exp_l = np.exp(scaled - np.max(scaled))
                        probs = exp_l / np.sum(exp_l)
                        pred_idx = int(np.argmax(probs))
                        confusion[true_idx][pred_idx] += 1
                        total_tested += 1
                break  # use first found dataset
    
    print(f"\n  {'':12s}", end='')
    for c in class_names:
        print(f"  {c:>8s}", end='')
    print("  | recall")
    print("  " + "-" * 65)
    
    for i, cls in enumerate(class_names):
        row_sum = sum(confusion[i])
        recall = confusion[i][i] / row_sum if row_sum > 0 else 0
        print(f"  {cls:12s}", end='')
        for j in range(5):
            val = confusion[i][j]
            marker = "" if i != j else ""
            print(f"  {val:8d}", end='')
        print(f"  | {recall:.3f}")
    
    print(f"\n  Total images tested: {total_tested}")
    correct = sum(confusion[i][i] for i in range(5))
    print(f"  Correct: {correct}/{total_tested} = {correct/total_tested*100:.1f}%")
    
    # Worst confusions
    print('\n  WORST CONFUSIONS:')
    for i in range(5):
        for j in range(5):
            if i != j and confusion[i][j] > 5:
                print(f"    {class_names[i]} → {class_names[j]}: {confusion[i][j]} misclassifications")

except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
