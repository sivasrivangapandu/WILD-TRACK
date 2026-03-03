"""
WildTrackAI - Phase 3: Professional CNN Training Pipeline
==========================================================
Transfer Learning with EfficientNetB4 (380x380)
Two-phase training: frozen base -> fine-tuned last 100 layers
Full evaluation suite: confusion matrix, ROC curves, per-class accuracy

Usage:
    python train.py
    python train.py --epochs 60 --batch-size 16
"""

import os
import sys
import json
import shutil
import argparse
import datetime
import warnings
warnings.filterwarnings('ignore', category=DeprecationWarning)

import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

import tensorflow as tf
from tensorflow.keras import layers, models, regularizers
from tensorflow.keras.preprocessing.image import ImageDataGenerator
from tensorflow.keras.applications import EfficientNetB0
from tensorflow.keras.callbacks import (
    EarlyStopping, ModelCheckpoint, ReduceLROnPlateau, TensorBoard
)

# ============================================
# CONFIGURATION
# ============================================
IMG_SIZE = 256
BATCH_SIZE = 32
PHASE1_EPOCHS = 20
PHASE2_EPOCHS = 15
PHASE2_UNFREEZE = 30

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.dirname(BASE_DIR)
DATASET_DIR = os.path.join(BACKEND_DIR, "dataset_cleaned")
MODELS_DIR = os.path.join(BACKEND_DIR, "models")
OUTPUTS_DIR = os.path.join(MODELS_DIR, "evaluation")
LOG_DIR = os.path.join(BACKEND_DIR, "logs", "fit",
                       datetime.datetime.now().strftime('%Y%m%d-%H%M%S'))

MODEL_PATH = os.path.join(MODELS_DIR, "wildtrack_complete_model.h5")
CHECKPOINT_PATH = os.path.join(MODELS_DIR, "checkpoint_best.h5")
METADATA_PATH = os.path.join(MODELS_DIR, "model_metadata.json")


def setup_directories():
    for d in [MODELS_DIR, OUTPUTS_DIR, LOG_DIR]:
        os.makedirs(d, exist_ok=True)


def detect_classes():
    """Auto-detect classes from dataset directory."""
    # Try cleaned dataset first, fallback to raw
    for dpath in [DATASET_DIR, os.path.join(BACKEND_DIR, "dataset")]:
        if os.path.isdir(dpath):
            classes = sorted([
                d for d in os.listdir(dpath)
                if os.path.isdir(os.path.join(dpath, d))
                and len(os.listdir(os.path.join(dpath, d))) > 0
            ])
            if classes:
                if dpath != DATASET_DIR:
                    print(f"WARNING: Using raw dataset (cleaned not found)")
                return dpath, classes

    print("ERROR: No dataset found!")
    sys.exit(1)


def compute_class_weights(train_generator):
    """Compute balanced class weights for imbalanced data."""
    from sklearn.utils.class_weight import compute_class_weight
    weights = compute_class_weight(
        class_weight='balanced',
        classes=np.unique(train_generator.classes),
        y=train_generator.classes
    )
    return dict(enumerate(weights))


def build_model(num_classes):
    """Build EfficientNetB0 with classification head."""
    print(f"\n[MODEL] Building EfficientNetB0 ({IMG_SIZE}x{IMG_SIZE}, {num_classes} classes)...")

    base_model = EfficientNetB0(
        weights='imagenet',
        include_top=False,
        input_shape=(IMG_SIZE, IMG_SIZE, 3)
    )
    base_model.trainable = False

    inputs = tf.keras.Input(shape=(IMG_SIZE, IMG_SIZE, 3))
    x = base_model(inputs, training=False)
    x = layers.GlobalAveragePooling2D()(x)
    x = layers.BatchNormalization()(x)
    x = layers.Dense(256, activation='relu')(x)
    x = layers.Dropout(0.3)(x)
    outputs = layers.Dense(num_classes, activation='softmax')(x)

    model = models.Model(inputs, outputs, name="WildTrackAI_B0")
    return model, base_model


def compile_model(model, learning_rate=1e-3):
    model.compile(
        optimizer=tf.keras.optimizers.AdamW(
            learning_rate=learning_rate, weight_decay=1e-4),
        loss=tf.keras.losses.CategoricalCrossentropy(label_smoothing=0.1),
        metrics=[
            'accuracy',
            tf.keras.metrics.Precision(name='precision'),
            tf.keras.metrics.Recall(name='recall'),
            tf.keras.metrics.AUC(name='auc'),
        ]
    )


def create_callbacks(phase):
    return [
        ModelCheckpoint(CHECKPOINT_PATH, monitor='val_accuracy',
                       mode='max', save_best_only=True, verbose=1),
        EarlyStopping(monitor='val_loss', patience=10,
                     restore_best_weights=True, verbose=1),
        ReduceLROnPlateau(monitor='val_loss', factor=0.5,
                         patience=3, min_lr=1e-7, verbose=1),
        TensorBoard(log_dir=os.path.join(LOG_DIR, phase), histogram_freq=1),
    ]


def generate_confusion_matrix(model, val_data, class_names):
    from sklearn.metrics import confusion_matrix, classification_report
    import seaborn as sns

    print("\n[EVAL] Confusion matrix...")
    val_data.reset()
    predictions = model.predict(val_data, verbose=0)
    y_pred = np.argmax(predictions, axis=1)
    y_true = val_data.classes

    report = classification_report(y_true, y_pred, target_names=class_names,
                                   output_dict=True, zero_division=0)
    report_text = classification_report(y_true, y_pred, target_names=class_names,
                                        zero_division=0)
    print("\nClassification Report:")
    print(report_text)

    with open(os.path.join(OUTPUTS_DIR, "classification_report.json"), 'w') as f:
        json.dump(report, f, indent=2)

    cm = confusion_matrix(y_true, y_pred)
    plt.figure(figsize=(12, 10))
    sns.heatmap(cm, annot=True, fmt='d', cmap='Blues',
                xticklabels=class_names, yticklabels=class_names)
    plt.title('Confusion Matrix', fontsize=16)
    plt.ylabel('True Label', fontsize=13)
    plt.xlabel('Predicted Label', fontsize=13)
    plt.tight_layout()
    plt.savefig(os.path.join(OUTPUTS_DIR, "confusion_matrix.png"), dpi=150)
    plt.close()
    print("  Saved: confusion_matrix.png")

    return report, y_true, y_pred, predictions


def generate_roc_curves(y_true, predictions, class_names):
    from sklearn.preprocessing import label_binarize
    from sklearn.metrics import roc_curve, auc

    print("[EVAL] ROC curves...")
    n_classes = len(class_names)
    y_true_bin = label_binarize(y_true, classes=range(n_classes))

    plt.figure(figsize=(12, 8))
    colors = plt.cm.Set3(np.linspace(0, 1, n_classes))

    for i, (cls, color) in enumerate(zip(class_names, colors)):
        if y_true_bin.shape[1] <= i:
            continue
        fpr, tpr, _ = roc_curve(y_true_bin[:, i], predictions[:, i])
        roc_auc = auc(fpr, tpr)
        plt.plot(fpr, tpr, color=color, lw=2,
                 label=f'{cls} (AUC = {roc_auc:.3f})')

    plt.plot([0, 1], [0, 1], 'k--', lw=1)
    plt.xlim([0.0, 1.0])
    plt.ylim([0.0, 1.05])
    plt.xlabel('False Positive Rate')
    plt.ylabel('True Positive Rate')
    plt.title('ROC Curves (One-vs-Rest)', fontsize=16)
    plt.legend(loc='lower right')
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig(os.path.join(OUTPUTS_DIR, "roc_curves.png"), dpi=150)
    plt.close()
    print("  Saved: roc_curves.png")


def generate_per_class_accuracy(report, class_names):
    print("[EVAL] Per-class accuracy chart...")

    precisions = [report.get(c, {}).get('precision', 0) for c in class_names]
    recalls = [report.get(c, {}).get('recall', 0) for c in class_names]
    f1s = [report.get(c, {}).get('f1-score', 0) for c in class_names]

    x = np.arange(len(class_names))
    width = 0.25

    fig, ax = plt.subplots(figsize=(14, 6))
    ax.bar(x - width, precisions, width, label='Precision', color='#4e79a7')
    ax.bar(x, recalls, width, label='Recall', color='#f28e2b')
    ax.bar(x + width, f1s, width, label='F1-Score', color='#e15759')

    ax.set_xlabel('Species')
    ax.set_ylabel('Score')
    ax.set_title('Per-Class Performance', fontsize=16)
    ax.set_xticks(x)
    ax.set_xticklabels(class_names, rotation=45, ha='right')
    ax.legend()
    ax.set_ylim(0, 1.1)
    ax.grid(True, axis='y', alpha=0.3)
    plt.tight_layout()
    plt.savefig(os.path.join(OUTPUTS_DIR, "per_class_accuracy.png"), dpi=150)
    plt.close()
    print("  Saved: per_class_accuracy.png")


def plot_training_history(h1, h2, p1_epochs):
    print("[EVAL] Training history plots...")

    acc = h1.history['accuracy'] + h2.history['accuracy']
    val_acc = h1.history['val_accuracy'] + h2.history['val_accuracy']
    loss = h1.history['loss'] + h2.history['loss']
    val_loss = h1.history['val_loss'] + h2.history['val_loss']

    fig, axes = plt.subplots(1, 2, figsize=(16, 6))

    axes[0].plot(acc, label='Train Acc', lw=2)
    axes[0].plot(val_acc, label='Val Acc', lw=2)
    axes[0].axvline(x=p1_epochs, color='r', ls='--', alpha=0.5, label='Fine-tune')
    axes[0].set_title('Model Accuracy', fontsize=14)
    axes[0].set_xlabel('Epoch')
    axes[0].set_ylabel('Accuracy')
    axes[0].legend()
    axes[0].grid(True, alpha=0.3)

    axes[1].plot(loss, label='Train Loss', lw=2)
    axes[1].plot(val_loss, label='Val Loss', lw=2)
    axes[1].axvline(x=p1_epochs, color='r', ls='--', alpha=0.5, label='Fine-tune')
    axes[1].set_title('Model Loss', fontsize=14)
    axes[1].set_xlabel('Epoch')
    axes[1].set_ylabel('Loss')
    axes[1].legend()
    axes[1].grid(True, alpha=0.3)

    plt.tight_layout()
    plt.savefig(os.path.join(OUTPUTS_DIR, "training_history.png"), dpi=150)
    plt.close()
    print("  Saved: training_history.png")


def train():
    setup_directories()

    print("=" * 60)
    print("WILDTRACKAI - PHASE 3: PROFESSIONAL CNN TRAINING")
    print("=" * 60)

    dataset_path, class_names = detect_classes()
    num_classes = len(class_names)

    print(f"\n  Dataset: {dataset_path}")
    print(f"  Classes ({num_classes}): {class_names}")
    print(f"  Image: {IMG_SIZE}x{IMG_SIZE}")
    print(f"  Batch: {BATCH_SIZE}")
    print(f"  Phase 1: {PHASE1_EPOCHS} epochs (frozen)")
    print(f"  Phase 2: {PHASE2_EPOCHS} epochs (unfreeze last {PHASE2_UNFREEZE})")

    # Data augmentation — SEPARATE generators for train/val
    # NOTE: EfficientNet includes its own Rescaling layer.
    #       It expects pixel values in [0, 255]. Do NOT rescale=1/255!
    print("\n[DATA] Setting up augmentation...")
    train_datagen = ImageDataGenerator(
        rotation_range=25,
        width_shift_range=0.15,
        height_shift_range=0.15,
        shear_range=0.1,
        zoom_range=0.15,
        horizontal_flip=True,
        brightness_range=[0.85, 1.15],
        fill_mode='reflect',
        validation_split=0.2
    )

    # Validation: NO augmentation, NO rescale (EfficientNet handles it)
    val_datagen = ImageDataGenerator(
        validation_split=0.2
    )

    train_data = train_datagen.flow_from_directory(
        dataset_path,
        target_size=(IMG_SIZE, IMG_SIZE),
        batch_size=BATCH_SIZE,
        class_mode='categorical',
        subset='training',
        shuffle=True,
        classes=class_names
    )

    val_data = val_datagen.flow_from_directory(
        dataset_path,
        target_size=(IMG_SIZE, IMG_SIZE),
        batch_size=BATCH_SIZE,
        class_mode='categorical',
        subset='validation',
        shuffle=False,
        classes=class_names
    )

    print(f"  Training: {train_data.samples}")
    print(f"  Validation: {val_data.samples}")
    print(f"  Mapping: {train_data.class_indices}")

    # Class weights
    print("\n[DATA] Computing class weights...")
    class_weights = compute_class_weights(train_data)
    for idx, w in class_weights.items():
        print(f"  {class_names[idx]}: {w:.3f}")

    # Build model
    model, base_model = build_model(num_classes)
    compile_model(model, learning_rate=1e-3)
    model.summary()

    # Phase 1
    print("\n" + "=" * 60)
    print("PHASE 1: FEATURE EXTRACTION (FROZEN BASE)")
    print("=" * 60)

    h1 = model.fit(
        train_data,
        validation_data=val_data,
        epochs=PHASE1_EPOCHS,
        callbacks=create_callbacks("phase1"),
        class_weight=class_weights,
        verbose=1
    )
    p1_done = len(h1.epoch)
    print(f"\nPhase 1 done: {p1_done} epochs")

    # Save Phase 1 best checkpoint separately so Phase 2 can't overwrite it
    p1_best_path = os.path.join(MODELS_DIR, "checkpoint_phase1_best.h5")
    if os.path.exists(CHECKPOINT_PATH):
        import shutil
        shutil.copy2(CHECKPOINT_PATH, p1_best_path)
        print(f"  Phase 1 best saved: {p1_best_path}")

    # Get Phase 1 best val_accuracy for Phase 2 threshold
    p1_best_val_acc = max(h1.history.get('val_accuracy', [0]))
    print(f"  Phase 1 best val_accuracy: {p1_best_val_acc:.4f}")

    # Phase 2
    print("\n" + "=" * 60)
    print(f"PHASE 2: FINE-TUNING (LAST {PHASE2_UNFREEZE} LAYERS)")
    print("=" * 60)

    h2 = None
    try:
        base_model.trainable = True
        for layer in base_model.layers[:-PHASE2_UNFREEZE]:
            layer.trainable = False

        trainable = sum(1 for l in base_model.layers if l.trainable)
        print(f"  Trainable layers: {trainable}/{len(base_model.layers)}")

        compile_model(model, learning_rate=1e-5)

        # Phase 2 checkpoint ONLY saves if it beats Phase 1's best
        p2_callbacks = [
            ModelCheckpoint(CHECKPOINT_PATH, monitor='val_accuracy',
                           mode='max', save_best_only=True, verbose=1,
                           initial_value_threshold=p1_best_val_acc),
            EarlyStopping(monitor='val_loss', patience=10,
                         restore_best_weights=True, verbose=1),
            ReduceLROnPlateau(monitor='val_loss', factor=0.5,
                             patience=3, min_lr=1e-7, verbose=1),
            TensorBoard(log_dir=os.path.join(LOG_DIR, "phase2"), histogram_freq=1),
        ]

        total = p1_done + PHASE2_EPOCHS
        h2 = model.fit(
            train_data,
            validation_data=val_data,
            epochs=total,
            initial_epoch=p1_done,
            callbacks=p2_callbacks,
            class_weight=class_weights,
            verbose=1
        )
        print(f"\nPhase 2 done: {len(h2.epoch)} epochs")
    except (KeyboardInterrupt, Exception) as e:
        print(f"\n[WARNING] Phase 2 interrupted: {e}")

    # Load the BEST checkpoint (Phase 1 or Phase 2, whichever is better)
    print("\n  Loading best checkpoint for evaluation...")
    if os.path.exists(CHECKPOINT_PATH):
        model = tf.keras.models.load_model(CHECKPOINT_PATH, compile=False)
        compile_model(model, learning_rate=1e-5)
        print("  Best checkpoint loaded.")

    # Evaluation
    print("\n" + "=" * 60)
    print("EVALUATION")
    print("=" * 60)

    val_data.reset()
    results = model.evaluate(val_data, verbose=1)
    metrics = dict(zip(model.metrics_names, results))

    prec = metrics.get('precision', 0)
    rec = metrics.get('recall', 0)
    f1 = 2 * (prec * rec) / (prec + rec + 1e-7)
    metrics['f1_score'] = f1

    print("\nFinal Metrics:")
    for k, v in metrics.items():
        print(f"  {k}: {v:.4f}")

    report, y_true, y_pred, preds = generate_confusion_matrix(model, val_data, class_names)
    generate_roc_curves(y_true, preds, class_names)
    generate_per_class_accuracy(report, class_names)
    plot_training_history(h1, h2, p1_done)

    # Save model
    print(f"\n[SAVE] Saving model: {MODEL_PATH}")
    model.save(MODEL_PATH)

    # Save metadata
    # Use classification report for accurate metrics (model.evaluate can have key mismatches)
    report_accuracy = report.get('accuracy', 0) if isinstance(report.get('accuracy'), (int, float)) else 0
    report_macro = report.get('macro avg', {})
    metadata = {
        "model_name": "WildTrackAI_EfficientNetB0",
        "version": "2.0_pipeline_validation",
        "class_names": class_names,
        "class_indices": train_data.class_indices,
        "num_classes": num_classes,
        "img_size": IMG_SIZE,
        "architecture": "EfficientNetB0 + Custom Head",
        "accuracy": float(report_accuracy),
        "precision": float(report_macro.get('precision', 0)),
        "recall": float(report_macro.get('recall', 0)),
        "auc": float(metrics.get('auc', 0)),
        "f1_score": float(report_macro.get('f1-score', 0)),
        "training_samples": train_data.samples,
        "validation_samples": val_data.samples,
        "total_params": model.count_params(),
        "training_date": datetime.datetime.now().isoformat(),
    }
    with open(METADATA_PATH, 'w') as f:
        json.dump(metadata, f, indent=2)

    print("\n" + "=" * 60)
    print("TRAINING COMPLETE!")
    print("=" * 60)
    print(f"  Accuracy:  {metrics.get('accuracy', 0):.2%}")
    print(f"  Precision: {prec:.2%}")
    print(f"  Recall:    {rec:.2%}")
    print(f"  F1:        {f1:.2%}")
    print(f"  AUC:       {metrics.get('auc', 0):.4f}")
    print(f"\n  Model: {MODEL_PATH}")
    print(f"  Evaluation: {OUTPUTS_DIR}/")
    for f_name in os.listdir(OUTPUTS_DIR):
        print(f"    - {f_name}")
    print("=" * 60)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--epochs", type=int)
    parser.add_argument("--batch-size", type=int)
    args = parser.parse_args()

    if args.epochs:
        PHASE1_EPOCHS = args.epochs
    if args.batch_size:
        BATCH_SIZE = args.batch_size

    train()
