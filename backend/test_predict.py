"""Quick inference test for production model."""
import requests
import json
import time
import sys

BASE = "http://localhost:8000"

# Test health
print("=" * 50)
print("WILDTRACK AI - LIVE INFERENCE TEST")
print("=" * 50)

resp = requests.get(f"{BASE}/health")
h = resp.json()
print(f"\nHealth: {h['status']}")
print(f"Model loaded: {h['model_loaded']}")
print(f"GradCAM: {h['gradcam_available']}")

# Test system status
resp = requests.get(f"{BASE}/api/system/status")
s = resp.json()
print(f"\nSystem Status:")
print(f"  Model: {s['model_name']} ({s['model_version']})")
print(f"  Architecture: {s['architecture']}")
print(f"  Accuracy: {s['validation_accuracy']*100:.1f}%")
print(f"  TTA: {'Enabled' if s['tta_enabled'] else 'Disabled'} ({s['tta_passes']} passes)")
print(f"  Classes: {s['class_names']}")
print(f"  Status: {s['status']}")
print(f"  Uptime: {s['uptime']}")

# Test predictions on one image per class
import os
dataset_path = "dataset_cleaned"
classes = sorted([d for d in os.listdir(dataset_path) if os.path.isdir(os.path.join(dataset_path, d))])

print(f"\n{'='*50}")
print(f"LIVE INFERENCE TEST (1 image per class)")
print(f"{'='*50}")

correct = 0
total = 0
for cls in classes:
    cls_dir = os.path.join(dataset_path, cls)
    images = [f for f in os.listdir(cls_dir) if f.lower().endswith(('.jpg', '.jpeg', '.png'))]
    if not images:
        continue
    
    test_img = os.path.join(cls_dir, images[0])
    start = time.time()
    
    with open(test_img, 'rb') as f:
        resp = requests.post(f"{BASE}/predict", files={'file': (images[0], f, 'image/jpeg')})
    
    elapsed = time.time() - start
    d = resp.json()
    
    predicted = d['species']
    conf = d['confidence']
    is_correct = predicted == cls
    correct += int(is_correct)
    total += 1
    
    status = "✓" if is_correct else "✗"
    print(f"\n  {status} {cls:10s} → {predicted:10s} ({conf*100:.1f}%)  [{elapsed:.1f}s]")
    print(f"    Model: {d.get('model_version', 'N/A')} | TTA: {d.get('tta_enabled', 'N/A')} | Entropy: {d.get('entropy_ratio', 0)*100:.0f}%")
    
    top3 = d.get('top3', [])
    for t in top3:
        print(f"    #{top3.index(t)+1} {t['class']:10s} {t['confidence']*100:.1f}%")

print(f"\n{'='*50}")
print(f"RESULT: {correct}/{total} correct ({correct/total*100:.0f}%)")
print(f"{'='*50}")
