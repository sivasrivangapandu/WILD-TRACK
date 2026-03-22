"""
WildTrackAI v5 — Perfect Dataset Training Pipeline
=====================================================
Optimized exclusively for highly curated, "perfect" datasets (e.g., from Kaggle/Roboflow).
Target: 95%+ accuracy.

Upgrades over v4 for clean datasets:
  1. Reduced random erasing (clean data doesn't need as much destruction).
  2. Higher resolution (IMG_SIZE_FINAL = 300 from epoch 1).
  3. Deeper fine-tuning phase (since noisy gradients are no longer an issue).
  4. Adjusted class weights (assuming balanced, curated dataset).
  5. Outputs to 'wildtrack_v5_perfect.keras'

Usage:
    python train_v5_perfect.py
"""

import os
import sys
import json
import datetime
import warnings
import math
import random

warnings.filterwarnings('ignore', category=DeprecationWarning)
warnings.filterwarnings('ignore', category=FutureWarning)

import numpy as np
import tensorflow as tf
from tensorflow.keras import layers, models, regularizers
from tensorflow.keras.applications import EfficientNetB3
from tensorflow.keras.callbacks import (
    EarlyStopping, ModelCheckpoint, ReduceLROnPlateau, TensorBoard
)

# ============================================
# CONFIGURATION
# ============================================
IMG_SIZE = 300             # EfficientNetB3 native resolution
BATCH_SIZE = 16
PHASE1_EPOCHS = 15         # Frozen base — head training
PHASE2_EPOCHS = 30         # Deep fine-tuning (longer because data is clean)
MIXUP_ALPHA = 0.2          # Lighter MixUp for clean data
LABEL_SMOOTHING = 0.05     # Less label smoothing (high confidence is okay here)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.dirname(BASE_DIR)
DATASET_DIR = os.path.join(BACKEND_DIR, "dataset_perfect")
MODELS_DIR = os.path.join(BACKEND_DIR, "models")
OUTPUTS_DIR = os.path.join(MODELS_DIR, "evaluation")

# The ultimate goal model
MODEL_PATH = os.path.join(MODELS_DIR, "wildtrack_v5_perfect.keras")
CHECKPOINT_PATH = os.path.join(MODELS_DIR, "checkpoint_v5_perfect.keras")

SEED = 42
tf.random.set_seed(SEED)
np.random.seed(SEED)
random.seed(SEED)

def detect_dataset():
    if not os.path.isdir(DATASET_DIR):
        print(f"ERROR: {DATASET_DIR} not found.")
        print("Please run one of the import scripts first:")
        print("  - python backend/scripts/import_roboflow_dataset.py --api-key YOUR_KEY")
        print("  - python backend/scripts/import_kaggle_dataset.py")
        sys.exit(1)
        
    classes = sorted([d for d in os.listdir(DATASET_DIR) if os.path.isdir(os.path.join(DATASET_DIR, d))])
    if not classes:
        print("Dataset directory is empty!")
        sys.exit(1)
        
    print(f"\n[DATASET] Found PERFECT dataset at {DATASET_DIR}")
    for c in classes:
        count = len(os.listdir(os.path.join(DATASET_DIR, c)))
        print(f"  {c:>10}: {count} images")
    return classes

def parse_image(path, label, num_classes):
    img = tf.io.read_file(path)
    img = tf.image.decode_image(img, channels=3, expand_animations=False)
    img = tf.image.resize(img, [IMG_SIZE, IMG_SIZE])
    img = tf.cast(img, tf.float32)
    label_onehot = tf.one_hot(label, num_classes)
    return img, label_onehot

def augment_image(image, label):
    """Lighter augmentation. We assume the dataset is already curated."""
    # Rotation handles track orientation
    angle = tf.random.uniform([], -15, 15) * (math.pi / 180.0)
    image = tf.raw_ops.ImageProjectiveTransformV3(
        images=tf.expand_dims(image, 0),
        transforms=tf.expand_dims([tf.math.cos(angle), -tf.math.sin(angle), 0.0, 
                                   tf.math.sin(angle), tf.math.cos(angle), 0.0, 
                                   0.0, 0.0], 0),
        output_shape=[IMG_SIZE, IMG_SIZE],
        interpolation='BILINEAR', fill_mode='REFLECT', fill_value=0.0
    )[0]
    
    image = tf.image.random_flip_left_right(image)
    image = tf.image.random_brightness(image, max_delta=30.0)
    image = tf.image.random_contrast(image, lower=0.85, upper=1.15)
    
    # Very light erasing (clean datsets don't need heavy occlusion)
    if tf.random.uniform([]) < 0.1:
        h, w = IMG_SIZE, IMG_SIZE
        eh, ew = int(h * 0.1), int(w * 0.1)
        y = tf.random.uniform([], 0, h - eh, dtype=tf.int32)
        x = tf.random.uniform([], 0, w - ew, dtype=tf.int32)
        mask = tf.pad(tf.ones([eh, ew, 1]), [[y, h-eh-y], [x, w-ew-x], [0, 0]])
        noise = tf.random.uniform([h, w, 3], 0, 255)
        image = image * (1.0 - mask) + noise * mask
        
    image = tf.clip_by_value(image, 0.0, 255.0)
    return image, label

def get_datasets(class_names):
    image_paths, labels = [], []
    for idx, cls in enumerate(class_names):
        cls_dir = os.path.join(DATASET_DIR, cls)
        for fname in os.listdir(cls_dir):
            if fname.lower().endswith(('.jpg', '.png', '.jpeg')):
                image_paths.append(os.path.join(cls_dir, fname))
                labels.append(idx)
                
    paths = np.array(image_paths)
    lbls = np.array(labels)
    
    # 85/15 stratified split for clean data
    train_p, train_l, val_p, val_l = [], [], [], []
    for cls_idx in range(len(class_names)):
        mask = lbls == cls_idx
        c_paths = paths[mask]
        np.random.shuffle(c_paths)
        split = int(len(c_paths) * 0.85)
        train_p.extend(c_paths[:split])
        train_l.extend([cls_idx]*split)
        val_p.extend(c_paths[split:])
        val_l.extend([cls_idx]*(len(c_paths)-split))
        
    print(f"\n[SPLIT] Train: {len(train_p)} | Val: {len(val_p)}")
    
    # Train Dataset
    train_ds = tf.data.Dataset.from_tensor_slices((train_p, train_l))
    train_ds = train_ds.shuffle(len(train_p)).map(lambda p, l: parse_image(p, l, len(class_names)), num_parallel_calls=tf.data.AUTOTUNE)
    train_ds = train_ds.map(augment_image, num_parallel_calls=tf.data.AUTOTUNE)
    train_ds = train_ds.batch(BATCH_SIZE, drop_remainder=True).prefetch(tf.data.AUTOTUNE)
    
    # Val Dataset
    val_ds = tf.data.Dataset.from_tensor_slices((val_p, val_l))
    val_ds = val_ds.map(lambda p, l: parse_image(p, l, len(class_names)), num_parallel_calls=tf.data.AUTOTUNE)
    val_ds = val_ds.batch(BATCH_SIZE).prefetch(tf.data.AUTOTUNE)
    
    return train_ds, val_ds

def build_model(num_classes):
    print(f"\n[MODEL] Building EfficientNetB3 for perfectly curated dataset...")
    base_model = EfficientNetB3(weights='imagenet', include_top=False, input_shape=(IMG_SIZE, IMG_SIZE, 3))
    base_model.trainable = False 
    
    inputs = tf.keras.Input(shape=(IMG_SIZE, IMG_SIZE, 3))
    x = base_model(inputs, training=False)
    x = layers.GlobalAveragePooling2D()(x)
    
    # Head optimized for high accuracy on clean features
    x = layers.BatchNormalization()(x)
    x = layers.Dense(512, activation='swish', kernel_regularizer=regularizers.l2(1e-4))(x)
    x = layers.Dropout(0.3)(x)
    x = layers.Dense(256, activation='swish', kernel_regularizer=regularizers.l2(1e-4))(x)
    x = layers.Dropout(0.2)(x)
    outputs = layers.Dense(num_classes, activation='softmax')(x)
    
    return models.Model(inputs, outputs), base_model

def main():
    print("="*60)
    print(" WILDTRACKAI V5 — PERFECT DATASET TRAINING PIPELINE ")
    print("="*60)
    
    class_names = detect_dataset()
    train_ds, val_ds = get_datasets(class_names)
    
    model, base_model = build_model(len(class_names))
    
    loss_fn = tf.keras.losses.CategoricalCrossentropy(label_smoothing=LABEL_SMOOTHING)
    
    # ── PHASE 1: Train Top ──
    print("\n" + "="*40 + "\n PHASE 1: Training Head (Frozen Base) \n" + "="*40)
    model.compile(optimizer=tf.keras.optimizers.Adam(1e-3), loss=loss_fn, metrics=['accuracy'])
    
    cbs1 = [
        ModelCheckpoint(CHECKPOINT_PATH, save_best_only=True, monitor='val_accuracy'),
        EarlyStopping(patience=5, restore_best_weights=True)
    ]
    model.fit(train_ds, validation_data=val_ds, epochs=PHASE1_EPOCHS, callbacks=cbs1)
    
    # ── PHASE 2: Deep Fine-Tuning ──
    print("\n" + "="*40 + "\n PHASE 2: Unfreezing Top 100 Layers \n" + "="*40)
    base_model.trainable = True
    for layer in base_model.layers[:-100]:
        layer.trainable = False
        
    model.compile(optimizer=tf.keras.optimizers.Adam(1e-4), loss=loss_fn, metrics=['accuracy'])
    cbs2 = [
        ModelCheckpoint(CHECKPOINT_PATH, save_best_only=True, monitor='val_accuracy'),
        ReduceLROnPlateau(factor=0.5, patience=3, min_lr=1e-6),
        EarlyStopping(patience=8, restore_best_weights=True)
    ]
    model.fit(train_ds, validation_data=val_ds, epochs=PHASE2_EPOCHS, callbacks=cbs2)
    
    # ── SAVE & METADATA ──
    print("\n[SAVING] Exporting ultimate perfect model...")
    model.save(MODEL_PATH)
    
    # Final eval
    results = model.evaluate(val_ds, verbose=0)
    val_acc = results[1]
    
    metadata = {
        "version": "v5.0-perfect",
        "model_name": "WildTrackAI_v5_Perfect",
        "accuracy": float(val_acc),
        "classes": class_names,
        "input_size": IMG_SIZE,
        "timestamp": datetime.datetime.utcnow().isoformat(),
        "dataset": "perfect_curated"
    }
    
    with open(os.path.join(MODELS_DIR, "model_metadata_v5.json"), "w") as f:
        json.dump(metadata, f, indent=4)
        
    print(f"\n✅ Training Complete! Validation Accuracy: {val_acc*100:.2f}%")
    print(f"Model saved to: {MODEL_PATH}")

if __name__ == "__main__":
    main()
