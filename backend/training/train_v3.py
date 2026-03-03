"""
WildTrackAI v3 — EfficientNetB3 + Focal Loss + Enhanced Augmentation
=====================================================================
Upgrades:
  - EfficientNetB3 backbone (300x300, 12M params vs B0's 5M)
  - Focal Loss (γ=2.0) — penalizes easy examples, helps rare/confused classes
  - Computed class weights for imbalanced dataset
  - Enhanced augmentation: CoarseDropout, channel shifts, perspective
  - Cosine annealing LR with warmup
  - 3-phase training: frozen → unfreeze last 50 → unfreeze last 100

Usage:
    python train_v3.py
    python train_v3.py --epochs 30 --batch-size 16
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
from tensorflow.keras import layers, models, regularizers, backend as K
from tensorflow.keras.preprocessing.image import ImageDataGenerator
from tensorflow.keras.applications import EfficientNetB3
from tensorflow.keras.callbacks import (
    EarlyStopping, ModelCheckpoint, ReduceLROnPlateau, TensorBoard, Callback
)

# ============================================
# CONFIGURATION
# ============================================
IMG_SIZE = 300  # EfficientNetB3 native resolution
BATCH_SIZE = 16  # Smaller batch for B3 memory
PHASE1_EPOCHS = 25  # Frozen base
PHASE2_EPOCHS = 20  # Fine-tune last 60 layers
PHASE3_EPOCHS = 15  # Fine-tune last 120 layers

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.dirname(BASE_DIR)
DATASET_DIR = os.path.join(BACKEND_DIR, "dataset_cleaned")
DATASET_RAW = os.path.join(BACKEND_DIR, "dataset")
MODELS_DIR = os.path.join(BACKEND_DIR, "models")
OUTPUTS_DIR = os.path.join(MODELS_DIR, "evaluation")
LOG_DIR = os.path.join(BACKEND_DIR, "logs", "fit",
                       datetime.datetime.now().strftime('%Y%m%d-%H%M%S'))

MODEL_PATH = os.path.join(MODELS_DIR, "wildtrack_v3_b3.h5")
MODEL_FINAL_PATH = os.path.join(MODELS_DIR, "wildtrack_complete_model.h5")
CHECKPOINT_PATH = os.path.join(MODELS_DIR, "checkpoint_best.h5")
METADATA_PATH = os.path.join(MODELS_DIR, "model_metadata.json")


# ============================================
# FOCAL LOSS
# ============================================
class FocalLoss(tf.keras.losses.Loss):
    """Focal Loss — Lin et al. 2017
    
    Down-weights well-classified examples, focuses on hard/misclassified ones.
    FL(p_t) = -α_t * (1 - p_t)^γ * log(p_t)
    
    Perfect for imbalanced wildlife datasets where leopard/tiger are easily confused.
    """
    def __init__(self, gamma=2.0, alpha=None, label_smoothing=0.05, **kwargs):
        super().__init__(**kwargs)
        self.gamma = gamma
        self.alpha = alpha  # Per-class weights (set from class_weights)
        self.label_smoothing = label_smoothing
    
    def call(self, y_true, y_pred):
        # Label smoothing
        num_classes = tf.shape(y_true)[-1]
        y_true = y_true * (1.0 - self.label_smoothing) + self.label_smoothing / tf.cast(num_classes, tf.float32)
        
        # Clip predictions to prevent log(0)
        y_pred = tf.clip_by_value(y_pred, 1e-7, 1.0 - 1e-7)
        
        # Cross-entropy
        ce = -y_true * tf.math.log(y_pred)
        
        # Focal modulating factor
        p_t = tf.reduce_sum(y_true * y_pred, axis=-1, keepdims=True)
        focal_weight = tf.pow(1.0 - p_t, self.gamma)
        
        # Apply alpha (class weights) if provided
        if self.alpha is not None:
            alpha_t = tf.reduce_sum(y_true * self.alpha, axis=-1, keepdims=True)
            focal_weight = focal_weight * alpha_t
        
        loss = focal_weight * ce
        return tf.reduce_mean(tf.reduce_sum(loss, axis=-1))
    
    def get_config(self):
        config = super().get_config()
        config.update({
            'gamma': self.gamma,
            'alpha': self.alpha.numpy().tolist() if isinstance(self.alpha, tf.Tensor) else self.alpha,
            'label_smoothing': self.label_smoothing,
        })
        return config


# ============================================
# COSINE ANNEALING WITH WARMUP
# ============================================
class WarmupCosineSchedule(Callback):
    """Learning rate schedule: linear warmup → cosine annealing."""
    def __init__(self, warmup_epochs=3, max_lr=1e-3, min_lr=1e-7, total_epochs=25):
        super().__init__()
        self.warmup_epochs = warmup_epochs
        self.max_lr = max_lr
        self.min_lr = min_lr
        self.total_epochs = total_epochs
    
    def on_epoch_begin(self, epoch, logs=None):
        if epoch < self.warmup_epochs:
            lr = self.max_lr * (epoch + 1) / self.warmup_epochs
        else:
            progress = (epoch - self.warmup_epochs) / max(1, self.total_epochs - self.warmup_epochs)
            lr = self.min_lr + 0.5 * (self.max_lr - self.min_lr) * (1 + np.cos(np.pi * progress))
        self.model.optimizer.learning_rate.assign(lr)
        print(f"  → LR: {lr:.2e}")


def setup_directories():
    for d in [MODELS_DIR, OUTPUTS_DIR, LOG_DIR]:
        os.makedirs(d, exist_ok=True)


def detect_dataset():
    """Detect best available dataset."""
    for dpath in [DATASET_DIR, DATASET_RAW]:
        if os.path.isdir(dpath):
            classes = sorted([
                d for d in os.listdir(dpath)
                if os.path.isdir(os.path.join(dpath, d))
                and len(os.listdir(os.path.join(dpath, d))) > 0
            ])
            if classes:
                counts = {c: len(os.listdir(os.path.join(dpath, c))) for c in classes}
                total = sum(counts.values())
                print(f"\n  Dataset: {dpath}")
                print(f"  Total: {total} images")
                for c, n in counts.items():
                    print(f"    {c}: {n} ({n/total:.1%})")
                return dpath, classes
    
    print("ERROR: No dataset found!")
    sys.exit(1)


def compute_class_weights(train_generator, class_names):
    """Compute balanced class weights."""
    from sklearn.utils.class_weight import compute_class_weight
    weights = compute_class_weight(
        class_weight='balanced',
        classes=np.unique(train_generator.classes),
        y=train_generator.classes
    )
    weight_dict = dict(enumerate(weights))
    print("\n[WEIGHTS] Class weights (balanced):")
    for idx, w in weight_dict.items():
        print(f"  {class_names[idx]:>10}: {w:.3f}")
    return weight_dict


def build_model(num_classes):
    """Build EfficientNetB3 with enhanced classification head."""
    print(f"\n[MODEL] Building EfficientNetB3 ({IMG_SIZE}x{IMG_SIZE}, {num_classes} classes)...")
    
    base_model = EfficientNetB3(
        weights='imagenet',
        include_top=False,
        input_shape=(IMG_SIZE, IMG_SIZE, 3)
    )
    base_model.trainable = False  # Frozen for Phase 1
    
    inputs = tf.keras.Input(shape=(IMG_SIZE, IMG_SIZE, 3))
    x = base_model(inputs, training=False)
    x = layers.GlobalAveragePooling2D()(x)
    x = layers.BatchNormalization()(x)
    x = layers.Dense(512, kernel_regularizer=regularizers.l2(1e-4))(x)
    x = layers.Activation('swish')(x)  # Swish matches EfficientNet's activation
    x = layers.Dropout(0.4)(x)
    x = layers.Dense(256, kernel_regularizer=regularizers.l2(1e-4))(x)
    x = layers.Activation('swish')(x)
    x = layers.Dropout(0.3)(x)
    outputs = layers.Dense(num_classes, activation='softmax')(x)
    
    model = models.Model(inputs, outputs, name="WildTrackAI_B3_v3")
    
    print(f"  Base params:  {base_model.count_params():,}")
    print(f"  Total params: {model.count_params():,}")
    print(f"  Base layers:  {len(base_model.layers)}")
    
    return model, base_model


def compile_model(model, learning_rate=1e-3, focal_loss=None):
    """Compile with focal loss or standard CE."""
    loss = focal_loss if focal_loss else tf.keras.losses.CategoricalCrossentropy(label_smoothing=0.1)
    
    model.compile(
        optimizer=tf.keras.optimizers.AdamW(
            learning_rate=learning_rate, 
            weight_decay=1e-4,
            clipnorm=1.0  # Gradient clipping for stability
        ),
        loss=loss,
        metrics=[
            'accuracy',
            tf.keras.metrics.Precision(name='precision'),
            tf.keras.metrics.Recall(name='recall'),
            tf.keras.metrics.AUC(name='auc'),
        ]
    )


def create_callbacks(phase, lr_schedule=None):
    cbs = [
        ModelCheckpoint(CHECKPOINT_PATH, monitor='val_accuracy',
                       mode='max', save_best_only=True, verbose=1),
        EarlyStopping(monitor='val_loss', patience=8,
                     restore_best_weights=True, verbose=1),
        TensorBoard(log_dir=os.path.join(LOG_DIR, phase), histogram_freq=1),
    ]
    if lr_schedule:
        cbs.append(lr_schedule)
    else:
        cbs.append(ReduceLROnPlateau(monitor='val_loss', factor=0.5,
                                     patience=3, min_lr=1e-7, verbose=1))
    return cbs


def generate_evaluation(model, val_data, class_names):
    """Full evaluation: confusion matrix, ROC curves, per-class metrics."""
    from sklearn.metrics import confusion_matrix, classification_report, roc_curve, auc
    from sklearn.preprocessing import label_binarize
    import seaborn as sns
    
    print("\n[EVAL] Running full evaluation...")
    val_data.reset()
    predictions = model.predict(val_data, verbose=0)
    y_pred = np.argmax(predictions, axis=1)
    y_true = val_data.classes
    n_classes = len(class_names)
    
    # Classification report
    report = classification_report(y_true, y_pred, target_names=class_names,
                                   output_dict=True, zero_division=0)
    report_text = classification_report(y_true, y_pred, target_names=class_names,
                                        zero_division=0)
    print("\n" + report_text)
    
    with open(os.path.join(OUTPUTS_DIR, "classification_report.json"), 'w') as f:
        json.dump(report, f, indent=2)
    
    # Confusion matrix
    cm = confusion_matrix(y_true, y_pred)
    plt.figure(figsize=(12, 10))
    sns.heatmap(cm, annot=True, fmt='d', cmap='Blues',
                xticklabels=class_names, yticklabels=class_names)
    plt.title('WildTrackAI v3 — Confusion Matrix', fontsize=16)
    plt.ylabel('True Label', fontsize=13)
    plt.xlabel('Predicted Label', fontsize=13)
    plt.tight_layout()
    plt.savefig(os.path.join(OUTPUTS_DIR, "confusion_matrix.png"), dpi=150)
    plt.close()
    
    # ROC curves
    y_true_bin = label_binarize(y_true, classes=range(n_classes))
    plt.figure(figsize=(12, 8))
    colors = ['#2196F3', '#4CAF50', '#FF9800', '#E91E63', '#9C27B0']
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
    plt.title('WildTrackAI v3 — ROC Curves', fontsize=16)
    plt.legend(loc='lower right')
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig(os.path.join(OUTPUTS_DIR, "roc_curves.png"), dpi=150)
    plt.close()
    
    # Per-class performance
    precisions = [report.get(c, {}).get('precision', 0) for c in class_names]
    recalls = [report.get(c, {}).get('recall', 0) for c in class_names]
    f1s = [report.get(c, {}).get('f1-score', 0) for c in class_names]
    
    x = np.arange(n_classes)
    width = 0.25
    fig, ax = plt.subplots(figsize=(14, 6))
    ax.bar(x - width, precisions, width, label='Precision', color='#4e79a7')
    ax.bar(x, recalls, width, label='Recall', color='#f28e2b')
    ax.bar(x + width, f1s, width, label='F1-Score', color='#e15759')
    ax.set_xlabel('Species')
    ax.set_ylabel('Score')
    ax.set_title('WildTrackAI v3 — Per-Class Performance', fontsize=16)
    ax.set_xticks(x)
    ax.set_xticklabels(class_names, rotation=45, ha='right')
    ax.legend()
    ax.set_ylim(0, 1.1)
    ax.grid(True, axis='y', alpha=0.3)
    plt.tight_layout()
    plt.savefig(os.path.join(OUTPUTS_DIR, "per_class_accuracy.png"), dpi=150)
    plt.close()
    
    print("  Saved: confusion_matrix.png, roc_curves.png, per_class_accuracy.png")
    return report, y_true, y_pred, predictions


def plot_training_history(histories, phase_epochs):
    """Plot combined training history across all phases."""
    print("[EVAL] Training history plots...")
    
    acc, val_acc, loss, val_loss = [], [], [], []
    for h in histories:
        if h:
            acc.extend(h.history.get('accuracy', []))
            val_acc.extend(h.history.get('val_accuracy', []))
            loss.extend(h.history.get('loss', []))
            val_loss.extend(h.history.get('val_loss', []))
    
    fig, axes = plt.subplots(1, 2, figsize=(16, 6))
    
    axes[0].plot(acc, label='Train Acc', lw=2, color='#2196F3')
    axes[0].plot(val_acc, label='Val Acc', lw=2, color='#E91E63')
    cumulative = 0
    for i, pe in enumerate(phase_epochs[:-1]):
        cumulative += pe
        axes[0].axvline(x=cumulative, color='gray', ls='--', alpha=0.5,
                       label=f'Phase {i+2}' if i == 0 else '')
    axes[0].set_title('Model Accuracy', fontsize=14)
    axes[0].set_xlabel('Epoch')
    axes[0].set_ylabel('Accuracy')
    axes[0].legend()
    axes[0].grid(True, alpha=0.3)
    
    axes[1].plot(loss, label='Train Loss', lw=2, color='#2196F3')
    axes[1].plot(val_loss, label='Val Loss', lw=2, color='#E91E63')
    cumulative = 0
    for i, pe in enumerate(phase_epochs[:-1]):
        cumulative += pe
        axes[1].axvline(x=cumulative, color='gray', ls='--', alpha=0.5)
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
    
    print("=" * 70)
    print("  WILDTRACKAI v3 — EfficientNetB3 + Focal Loss")
    print("=" * 70)
    
    dataset_path, class_names = detect_dataset()
    num_classes = len(class_names)
    
    print(f"\n  Config:")
    print(f"    Backbone:  EfficientNetB3 ({IMG_SIZE}x{IMG_SIZE})")
    print(f"    Loss:      Focal Loss (γ=2.0)")
    print(f"    Batch:     {BATCH_SIZE}")
    print(f"    Phase 1:   {PHASE1_EPOCHS} epochs (frozen)")
    print(f"    Phase 2:   {PHASE2_EPOCHS} epochs (unfreeze 60)")
    print(f"    Phase 3:   {PHASE3_EPOCHS} epochs (unfreeze 120)")
    
    # ── Data augmentation ──
    print("\n[DATA] Setting up enhanced augmentation...")
    
    # EfficientNet expects [0, 255] — do NOT rescale!
    train_datagen = ImageDataGenerator(
        rotation_range=30,
        width_shift_range=0.2,
        height_shift_range=0.2,
        shear_range=0.15,
        zoom_range=0.2,
        horizontal_flip=True,
        vertical_flip=False,
        brightness_range=[0.75, 1.25],
        channel_shift_range=25.0,
        fill_mode='reflect',
        validation_split=0.2
    )
    
    val_datagen = ImageDataGenerator(validation_split=0.2)
    
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
    
    print(f"\n  Training:   {train_data.samples}")
    print(f"  Validation: {val_data.samples}")
    print(f"  Classes:    {train_data.class_indices}")
    
    # ── Class weights ──
    class_weights = compute_class_weights(train_data, class_names)
    
    # Convert class weights to alpha tensor for focal loss
    alpha_values = np.array([class_weights[i] for i in range(num_classes)], dtype=np.float32)
    alpha_tensor = tf.constant(alpha_values, dtype=tf.float32)
    
    focal_loss = FocalLoss(gamma=2.0, alpha=alpha_tensor, label_smoothing=0.05)
    
    # ── Build model ──
    model, base_model = build_model(num_classes)
    
    # ═══════════════════════════════════════════════
    # PHASE 1: FROZEN BASE — TRAIN HEAD ONLY
    # ═══════════════════════════════════════════════
    print("\n" + "=" * 70)
    print("  PHASE 1: FEATURE EXTRACTION (FROZEN BASE)")
    print("=" * 70)
    
    lr_schedule_p1 = WarmupCosineSchedule(
        warmup_epochs=3, max_lr=1e-3, min_lr=1e-6, total_epochs=PHASE1_EPOCHS
    )
    compile_model(model, learning_rate=1e-3, focal_loss=focal_loss)
    
    h1 = model.fit(
        train_data,
        validation_data=val_data,
        epochs=PHASE1_EPOCHS,
        callbacks=create_callbacks("phase1", lr_schedule_p1),
        class_weight=class_weights,
        verbose=1
    )
    p1_done = len(h1.epoch)
    p1_best = max(h1.history.get('val_accuracy', [0]))
    print(f"\n  Phase 1 complete: {p1_done} epochs, best val_acc={p1_best:.4f}")
    
    # Save Phase 1 checkpoint
    if os.path.exists(CHECKPOINT_PATH):
        shutil.copy2(CHECKPOINT_PATH, os.path.join(MODELS_DIR, "checkpoint_phase1_best.h5"))
    
    # ═══════════════════════════════════════════════
    # PHASE 2: UNFREEZE LAST 60 LAYERS
    # ═══════════════════════════════════════════════
    print("\n" + "=" * 70)
    print("  PHASE 2: FINE-TUNING (LAST 60 LAYERS)")
    print("=" * 70)
    
    h2 = None
    try:
        base_model.trainable = True
        for layer in base_model.layers[:-60]:
            layer.trainable = False
        
        trainable = sum(1 for l in base_model.layers if l.trainable)
        print(f"  Trainable: {trainable}/{len(base_model.layers)} base layers")
        
        lr_schedule_p2 = WarmupCosineSchedule(
            warmup_epochs=2, max_lr=5e-5, min_lr=1e-7, total_epochs=PHASE2_EPOCHS
        )
        compile_model(model, learning_rate=5e-5, focal_loss=focal_loss)
        
        total_epochs = p1_done + PHASE2_EPOCHS
        h2 = model.fit(
            train_data,
            validation_data=val_data,
            epochs=total_epochs,
            initial_epoch=p1_done,
            callbacks=create_callbacks("phase2", lr_schedule_p2),
            class_weight=class_weights,
            verbose=1
        )
        p2_done = len(h2.epoch)
        p2_best = max(h2.history.get('val_accuracy', [0]))
        print(f"\n  Phase 2 complete: {p2_done} epochs, best val_acc={p2_best:.4f}")
    except (KeyboardInterrupt, Exception) as e:
        print(f"\n[WARNING] Phase 2 interrupted: {e}")
        p2_done = 0
    
    # ═══════════════════════════════════════════════
    # PHASE 3: DEEP FINE-TUNING (LAST 120 LAYERS)
    # ═══════════════════════════════════════════════
    print("\n" + "=" * 70)
    print("  PHASE 3: DEEP FINE-TUNING (LAST 120 LAYERS)")
    print("=" * 70)
    
    h3 = None
    try:
        for layer in base_model.layers[:-120]:
            layer.trainable = False
        for layer in base_model.layers[-120:]:
            layer.trainable = True
        
        trainable = sum(1 for l in base_model.layers if l.trainable)
        print(f"  Trainable: {trainable}/{len(base_model.layers)} base layers")
        
        lr_schedule_p3 = WarmupCosineSchedule(
            warmup_epochs=1, max_lr=1e-5, min_lr=1e-8, total_epochs=PHASE3_EPOCHS
        )
        compile_model(model, learning_rate=1e-5, focal_loss=focal_loss)
        
        start_epoch = p1_done + (p2_done if h2 else 0)
        total_epochs = start_epoch + PHASE3_EPOCHS
        h3 = model.fit(
            train_data,
            validation_data=val_data,
            epochs=total_epochs,
            initial_epoch=start_epoch,
            callbacks=create_callbacks("phase3", lr_schedule_p3),
            class_weight=class_weights,
            verbose=1
        )
        p3_done = len(h3.epoch)
        p3_best = max(h3.history.get('val_accuracy', [0]))
        print(f"\n  Phase 3 complete: {p3_done} epochs, best val_acc={p3_best:.4f}")
    except (KeyboardInterrupt, Exception) as e:
        print(f"\n[WARNING] Phase 3 interrupted: {e}")
    
    # ── Load best checkpoint ──
    print("\n  Loading best checkpoint for evaluation...")
    if os.path.exists(CHECKPOINT_PATH):
        model = tf.keras.models.load_model(CHECKPOINT_PATH, compile=False,
                                            custom_objects={'FocalLoss': FocalLoss})
        compile_model(model, learning_rate=1e-5, focal_loss=focal_loss)
        print("  Best checkpoint loaded.")
    
    # ═══════════════════════════════════════════════
    # EVALUATION
    # ═══════════════════════════════════════════════
    print("\n" + "=" * 70)
    print("  EVALUATION")
    print("=" * 70)
    
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
    
    report, y_true, y_pred, preds = generate_evaluation(model, val_data, class_names)
    plot_training_history([h1, h2, h3], [p1_done, p2_done if h2 else 0, len(h3.epoch) if h3 else 0])
    
    # ── Save model ──
    # Save as v3 model
    print(f"\n[SAVE] Saving v3 model: {MODEL_PATH}")
    model.save(MODEL_PATH)
    
    # Also save as the production model (overwrite old B0)
    print(f"[SAVE] Saving as production model: {MODEL_FINAL_PATH}")
    model.save(MODEL_FINAL_PATH)
    
    # Save metadata
    report_accuracy = report.get('accuracy', 0) if isinstance(report.get('accuracy'), (int, float)) else 0
    report_macro = report.get('macro avg', {})
    metadata = {
        "model_name": "WildTrackAI_EfficientNetB3",
        "version": "3.0_focal_loss",
        "class_names": class_names,
        "class_indices": train_data.class_indices,
        "num_classes": num_classes,
        "img_size": IMG_SIZE,
        "architecture": "EfficientNetB3 + Focal Loss + Enhanced Head",
        "accuracy": float(report_accuracy),
        "precision": float(report_macro.get('precision', 0)),
        "recall": float(report_macro.get('recall', 0)),
        "auc": float(metrics.get('auc', 0)),
        "f1_score": float(report_macro.get('f1-score', 0)),
        "training_samples": train_data.samples,
        "validation_samples": val_data.samples,
        "total_params": model.count_params(),
        "backbone": "EfficientNetB3",
        "loss": "FocalLoss(gamma=2.0)",
        "phases": "3-phase: frozen→ft60→ft120",
        "training_date": datetime.datetime.now().isoformat(),
    }
    with open(METADATA_PATH, 'w') as f:
        json.dump(metadata, f, indent=2)
    
    print("\n" + "=" * 70)
    print("  TRAINING COMPLETE!")
    print("=" * 70)
    print(f"  Accuracy:  {report_accuracy:.2%}")
    print(f"  Precision: {report_macro.get('precision', 0):.2%}")
    print(f"  Recall:    {report_macro.get('recall', 0):.2%}")
    print(f"  F1-Score:  {report_macro.get('f1-score', 0):.2%}")
    print(f"  AUC:       {metrics.get('auc', 0):.4f}")
    print(f"\n  Model (v3):   {MODEL_PATH}")
    print(f"  Production:   {MODEL_FINAL_PATH}")
    print(f"  Metadata:     {METADATA_PATH}")
    print(f"  Evaluation:   {OUTPUTS_DIR}/")
    print("=" * 70)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="WildTrackAI v3 Training")
    parser.add_argument("--epochs", type=int, help="Phase 1 epochs (default: 25)")
    parser.add_argument("--batch-size", type=int, help="Batch size (default: 16)")
    args = parser.parse_args()
    
    if args.epochs:
        PHASE1_EPOCHS = args.epochs
    if args.batch_size:
        BATCH_SIZE = args.batch_size
    
    train()
