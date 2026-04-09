"""
Quick evaluation + save script for v4 best checkpoint.
Run: python evaluate_v4.py
"""
import os, json, sys, datetime, shutil
import numpy as np

os.environ['TF_CPP_MIN_LOG_LEVEL'] = '2'
import tensorflow as tf

MODELS_DIR = 'models'
OUTPUTS_DIR = os.path.join(MODELS_DIR, 'evaluation')
CHECKPOINT = os.path.join(MODELS_DIR, 'checkpoint_best_v4.h5')
FINAL_PATH = os.path.join(MODELS_DIR, 'wildtrack_v4.h5')
PROD_PATH = os.path.join(MODELS_DIR, 'wildtrack_complete_model.h5')
META_PATH = os.path.join(MODELS_DIR, 'model_metadata.json')

os.makedirs(OUTPUTS_DIR, exist_ok=True)

from training.train_v4 import FocalLoss, load_dataset, IMG_SIZE_FINAL

print('='*60)
print('  WILDTRACKAI v4 — EVALUATION & DEPLOY')
print('='*60)

# Load model
print('\nLoading checkpoint_best_v4.h5...')
model = tf.keras.models.load_model(CHECKPOINT, compile=False,
                                    custom_objects={'FocalLoss': FocalLoss})
print(f'  Params: {model.count_params():,}')
print(f'  Input:  {model.input_shape}')

# Load dataset
dataset_path = 'dataset_cleaned'
class_names = sorted([d for d in os.listdir(dataset_path) 
                      if os.path.isdir(os.path.join(dataset_path, d))])
num_classes = len(class_names)
print(f'  Classes: {class_names}')

_, _, val_paths, val_labels = load_dataset(
    dataset_path, class_names, IMG_SIZE_FINAL, validation_split=0.2)

# Per-image prediction for detailed metrics
print(f'\nEvaluating {len(val_paths)} validation images...')
all_preds = []
all_probs = []

for i, path in enumerate(val_paths):
    img = tf.io.read_file(path)
    img = tf.image.decode_image(img, channels=3, expand_animations=False)
    img = tf.image.resize(img, [IMG_SIZE_FINAL, IMG_SIZE_FINAL])
    img = tf.cast(img, tf.float32)
    img_array = np.expand_dims(img.numpy(), 0)
    probs = model.predict(img_array, verbose=0)[0]
    all_probs.append(probs)
    all_preds.append(np.argmax(probs))
    if (i+1) % 50 == 0:
        print(f'  {i+1}/{len(val_paths)}...')

y_pred = np.array(all_preds)
y_true = np.array(val_labels)
predictions = np.array(all_probs)

# Classification report
from sklearn.metrics import classification_report, confusion_matrix
report = classification_report(y_true, y_pred, target_names=class_names,
                               output_dict=True, zero_division=0)
report_text = classification_report(y_true, y_pred, target_names=class_names,
                                    zero_division=0)
print('\n' + report_text)

with open(os.path.join(OUTPUTS_DIR, 'classification_report_v4.json'), 'w') as f:
    json.dump(report, f, indent=2)

# Confusion matrix
cm = confusion_matrix(y_true, y_pred)
print('Confusion Matrix:')
print(f'{"":>10}', '  '.join(f'{c:>8}' for c in class_names))
for i, row in enumerate(cm):
    print(f'{class_names[i]:>10}', '  '.join(f'{v:>8}' for v in row))

# Top confusions
print('\nTop confusion pairs:')
confusion_pairs = []
for i in range(num_classes):
    for j in range(num_classes):
        if i != j and cm[i][j] > 0:
            confusion_pairs.append((class_names[i], class_names[j], cm[i][j]))
confusion_pairs.sort(key=lambda x: x[2], reverse=True)
for true_cls, pred_cls, count in confusion_pairs[:5]:
    print(f'  {true_cls} -> {pred_cls}: {count} errors')

# Save plots
try:
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    import seaborn as sns
    
    plt.figure(figsize=(12, 10))
    sns.heatmap(cm, annot=True, fmt='d', cmap='Blues',
                xticklabels=class_names, yticklabels=class_names)
    plt.title('WildTrackAI v4 — Confusion Matrix', fontsize=16)
    plt.ylabel('True Label', fontsize=13)
    plt.xlabel('Predicted Label', fontsize=13)
    plt.tight_layout()
    plt.savefig(os.path.join(OUTPUTS_DIR, 'confusion_matrix_v4.png'), dpi=150)
    plt.close()
    print('\nSaved: confusion_matrix_v4.png')
except Exception as e:
    print(f'Plot error: {e}')

# Save model as production
print(f'\nSaving v4 as production model...')
model.save(FINAL_PATH)
print(f'  Saved: {FINAL_PATH}')
model.save(PROD_PATH)
print(f'  Saved: {PROD_PATH}')

# Save metadata
acc = report.get('accuracy', 0)
macro = report.get('macro avg', {})
metadata = {
    "model_name": "WildTrackAI_v4",
    "version": "4.0_max_accuracy",
    "class_names": class_names,
    "class_indices": {c: i for i, c in enumerate(class_names)},
    "num_classes": num_classes,
    "img_size": IMG_SIZE_FINAL,
    "architecture": "EfficientNetB3 + SE Attention + MixUp/CutMix + SGDR + SWA",
    "accuracy": float(acc),
    "precision": float(macro.get('precision', 0)),
    "recall": float(macro.get('recall', 0)),
    "f1_score": float(macro.get('f1-score', 0)),
    "training_samples": 1600,
    "validation_samples": len(val_paths),
    "total_params": model.count_params(),
    "backbone": "EfficientNetB3",
    "loss": "FocalLoss(gamma=2.0, smoothing=0.1)",
    "augmentation": "MixUp+CutMix+RandomErase+StrongAug",
    "optimizer": "AdamW + SGDR",
    "phases": "3-phase: frozen->ft80->ft140",
    "tta_augments": 5,
    "training_date": datetime.datetime.now().isoformat(),
}
with open(META_PATH, 'w') as f:
    json.dump(metadata, f, indent=2)
print(f'  Saved: {META_PATH}')

print('\n' + '='*60)
print(f'  v4 DEPLOYED!')
print(f'  Accuracy:  {acc:.2%}')
print(f'  Precision: {macro.get("precision", 0):.2%}')
print(f'  Recall:    {macro.get("recall", 0):.2%}')
print(f'  F1-Score:  {macro.get("f1-score", 0):.2%}')
print('='*60)
