"""
WildTrackAI v4 — Maximum Accuracy From Limited Data
=====================================================
Target: ≥75-80% validation accuracy from ~1,166 images across 5 classes.

Key upgrades over v3:
  1. tf.data pipeline (replaces deprecated ImageDataGenerator)
  2. MixUp + CutMix regularization (proven 3-8% boost on small datasets)
  3. Progressive resizing: 224→300 (acts as regularizer)
  4. Snapshot ensemble: save & average multiple checkpoints
  5. Stratified K-Fold cross-validation for reliable metrics
  6. Test-Time Augmentation (TTA) baked into evaluation
  7. Improved head: squeeze-excite attention channel
  8. Stochastic Weight Averaging (SWA) in final phase
  9. Per-class analysis with top confusion pairs

Architecture: EfficientNetB3 (kept — proven backbone for this scale)
Loss:         Focal Loss (γ=2.0) + label smoothing via soft targets
Optimizer:    AdamW + cosine annealing with warm restarts (SGDR)

Usage:
    python train_v4.py                        # Standard training
    python train_v4.py --kfold 5              # 5-fold cross-validation
    python train_v4.py --progressive           # Progressive resizing
    python train_v4.py --epochs 30 --batch 16  # Custom config
"""

import os
import sys
import json
import shutil
import argparse
import datetime
import warnings
import random
import math
from pathlib import Path
from collections import Counter

warnings.filterwarnings('ignore', category=DeprecationWarning)
warnings.filterwarnings('ignore', category=FutureWarning)

import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

import tensorflow as tf
from tensorflow.keras import layers, models, regularizers, backend as K
from tensorflow.keras.applications import EfficientNetB3
from tensorflow.keras.callbacks import (
    EarlyStopping, ModelCheckpoint, ReduceLROnPlateau, TensorBoard, Callback
)

# ============================================
# CONFIGURATION
# ============================================
IMG_SIZE_FINAL = 300       # EfficientNetB3 native resolution (final stage)
IMG_SIZE_WARMUP = 224      # Progressive resizing: start smaller
BATCH_SIZE = 16
PHASE1_EPOCHS = 20         # Frozen base — head training
PHASE2_EPOCHS = 20         # Fine-tune last 80 layers
PHASE3_EPOCHS = 15         # Deep fine-tune + SWA
MIXUP_ALPHA = 0.3          # MixUp interpolation (0.2-0.4 optimal for small datasets)
CUTMIX_ALPHA = 1.0         # CutMix beta distribution parameter
MIXUP_PROB = 0.5           # Probability of applying MixUp per batch
CUTMIX_PROB = 0.3          # Probability of applying CutMix per batch
LABEL_SMOOTHING = 0.1      # Smooth one-hot labels
TTA_AUGMENTS = 5            # Number of TTA forward passes

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.dirname(BASE_DIR)
DATASET_DIR = os.path.join(BACKEND_DIR, "dataset_cleaned")
DATASET_STRICT = os.path.join(BACKEND_DIR, "dataset_strict")
DATASET_RAW = os.path.join(BACKEND_DIR, "dataset")
MODELS_DIR = os.path.join(BACKEND_DIR, "models")
OUTPUTS_DIR = os.path.join(MODELS_DIR, "evaluation")
LOG_DIR = os.path.join(BACKEND_DIR, "logs", "v4",
                       datetime.datetime.now().strftime('%Y%m%d-%H%M%S'))

MODEL_PATH = os.path.join(MODELS_DIR, "wildtrack_v4.h5")
MODEL_FINAL_PATH = os.path.join(MODELS_DIR, "wildtrack_complete_model.h5")
CHECKPOINT_PATH = os.path.join(MODELS_DIR, "checkpoint_best_v4.h5")
SWA_PATH = os.path.join(MODELS_DIR, "wildtrack_v4_swa.h5")
METADATA_PATH = os.path.join(MODELS_DIR, "model_metadata.json")

# Reproducibility
SEED = 42
tf.random.set_seed(SEED)
np.random.seed(SEED)
random.seed(SEED)


# ============================================
# FOCAL LOSS (kept from v3 for compatibility)
# ============================================
class FocalLoss(tf.keras.losses.Loss):
    """Focal Loss — down-weights well-classified examples.
    
    FL(p_t) = -α_t * (1 - p_t)^γ * log(p_t)
    """
    def __init__(self, gamma=2.0, alpha=None, label_smoothing=0.05, **kwargs):
        super().__init__(**kwargs)
        self.gamma = gamma
        self.alpha = alpha
        self.label_smoothing = label_smoothing
    
    def call(self, y_true, y_pred):
        num_classes = tf.shape(y_true)[-1]
        y_true = y_true * (1.0 - self.label_smoothing) + self.label_smoothing / tf.cast(num_classes, tf.float32)
        y_pred = tf.clip_by_value(y_pred, 1e-7, 1.0 - 1e-7)
        ce = -y_true * tf.math.log(y_pred)
        p_t = tf.reduce_sum(y_true * y_pred, axis=-1, keepdims=True)
        focal_weight = tf.pow(1.0 - p_t, self.gamma)
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
# COSINE ANNEALING WITH WARM RESTARTS (SGDR)
# ============================================
class SGDRSchedule(Callback):
    """Cosine annealing with warm restarts (Loshchilov & Hutter, 2017).
    
    Each restart doubles the cycle length (T_mult=2).
    Better than plain cosine — gives multiple "convergence attempts".
    """
    def __init__(self, max_lr=1e-3, min_lr=1e-7, cycle_length=10, t_mult=2, warmup_epochs=3):
        super().__init__()
        self.max_lr = max_lr
        self.min_lr = min_lr
        self.cycle_length = cycle_length
        self.t_mult = t_mult
        self.warmup_epochs = warmup_epochs
        self.cycle_epoch = 0
        self.current_cycle_length = cycle_length
        self.restart_count = 0
    
    def on_epoch_begin(self, epoch, logs=None):
        if epoch < self.warmup_epochs:
            lr = self.max_lr * (epoch + 1) / self.warmup_epochs
        else:
            self.cycle_epoch += 1
            if self.cycle_epoch >= self.current_cycle_length:
                self.cycle_epoch = 0
                self.restart_count += 1
                self.current_cycle_length = int(self.cycle_length * (self.t_mult ** self.restart_count))
                print(f"  ↻ LR restart #{self.restart_count} (next cycle: {self.current_cycle_length} epochs)")
            
            progress = self.cycle_epoch / max(1, self.current_cycle_length)
            lr = self.min_lr + 0.5 * (self.max_lr - self.min_lr) * (1 + math.cos(math.pi * progress))
        
        self.model.optimizer.learning_rate.assign(lr)
        print(f"  → LR: {lr:.2e}")


# ============================================
# DATA PIPELINE (tf.data — replaces ImageDataGenerator)
# ============================================
def load_dataset(dataset_path, class_names, img_size, validation_split=0.2):
    """Load dataset into stratified train/val splits using tf.data.
    
    Returns (train_paths, train_labels, val_paths, val_labels).
    """
    image_paths = []
    labels = []
    
    for idx, cls in enumerate(class_names):
        cls_dir = os.path.join(dataset_path, cls)
        if not os.path.isdir(cls_dir):
            continue
        for fname in sorted(os.listdir(cls_dir)):
            fpath = os.path.join(cls_dir, fname)
            if fname.lower().endswith(('.jpg', '.jpeg', '.png', '.bmp', '.webp')):
                image_paths.append(fpath)
                labels.append(idx)
    
    image_paths = np.array(image_paths)
    labels = np.array(labels)
    
    # Stratified split
    train_paths, train_labels = [], []
    val_paths, val_labels = [], []
    
    for cls_idx in range(len(class_names)):
        cls_mask = labels == cls_idx
        cls_paths = image_paths[cls_mask]
        n = len(cls_paths)
        
        # Shuffle within class
        perm = np.random.permutation(n)
        cls_paths = cls_paths[perm]
        
        split = int(n * (1 - validation_split))
        train_paths.extend(cls_paths[:split])
        train_labels.extend([cls_idx] * split)
        val_paths.extend(cls_paths[split:])
        val_labels.extend([cls_idx] * (n - split))
    
    # Shuffle training set
    train_perm = np.random.permutation(len(train_paths))
    train_paths = np.array(train_paths)[train_perm]
    train_labels = np.array(train_labels)[train_perm]
    val_paths = np.array(val_paths)
    val_labels = np.array(val_labels)
    
    print(f"\n  Dataset split:")
    print(f"    Train: {len(train_paths)} images")
    print(f"    Val:   {len(val_paths)} images")
    for idx, cls in enumerate(class_names):
        t_count = np.sum(train_labels == idx)
        v_count = np.sum(val_labels == idx)
        print(f"    {cls:>10}: {t_count} train, {v_count} val")
    
    return train_paths, train_labels, val_paths, val_labels


def parse_image(path, label, img_size, num_classes):
    """Load and decode a single image."""
    img = tf.io.read_file(path)
    img = tf.image.decode_image(img, channels=3, expand_animations=False)
    img = tf.image.resize(img, [img_size, img_size])
    img = tf.cast(img, tf.float32)  # EfficientNet expects [0, 255]
    label_onehot = tf.one_hot(label, num_classes)
    return img, label_onehot


def augment_image(image, label):
    """Strong augmentation for footprint images.
    
    Designed for wildlife footprints:
    - Rotation handles track orientation variation
    - Brightness/contrast handles lighting conditions
    - Zoom handles distance-to-track variation
    - Gaussian noise handles sensor/camera noise
    - Random erasing forces model to use multiple features
    """
    # Random rotation (±25°) — footprints in any orientation
    angle = tf.random.uniform([], -25, 25) * (math.pi / 180.0)
    image = rotate_image(image, angle)
    
    # Random flip (horizontal only — footprints are laterally variable)
    image = tf.image.random_flip_left_right(image)
    
    # Random brightness (±20%) — lighting conditions
    image = tf.image.random_brightness(image, max_delta=50.0)
    
    # Random contrast — shadow/highlight variation
    image = tf.image.random_contrast(image, lower=0.8, upper=1.2)
    
    # Random saturation — soil color variation
    image = tf.image.random_saturation(image, lower=0.8, upper=1.2)
    
    # Random hue (slight) — camera white balance variation
    image = tf.image.random_hue(image, max_delta=0.05)
    
    # Random zoom/crop (±15%)
    image = random_zoom_crop(image)
    
    # Gaussian noise — sensor noise
    noise = tf.random.normal(shape=tf.shape(image), mean=0.0, stddev=8.0)
    image = image + noise
    
    # Random erasing (CoarseDropout) — force multi-feature learning
    image = random_erasing(image)
    
    # Clip to valid range
    image = tf.clip_by_value(image, 0.0, 255.0)
    
    return image, label


def rotate_image(image, angle):
    """Rotate image by angle (radians) with reflection padding."""
    cos_a = tf.math.cos(angle)
    sin_a = tf.math.sin(angle)
    h = tf.cast(tf.shape(image)[0], tf.float32)
    w = tf.cast(tf.shape(image)[1], tf.float32)
    cx, cy = w / 2, h / 2
    
    # Affine transform matrix [a0, a1, a2, b0, b1, b2, c0, c1]
    transform = tf.stack([cos_a, -sin_a, cx - cx * cos_a + cy * sin_a,
                          sin_a,  cos_a, cy - cx * sin_a - cy * cos_a,
                          0.0, 0.0])
    image = tf.expand_dims(image, 0)
    try:
        image = tf.raw_ops.ImageProjectiveTransformV3(
            images=image,
            transforms=tf.expand_dims(transform, 0),
            output_shape=tf.shape(image)[1:3],
            interpolation='BILINEAR',
            fill_mode='REFLECT',
            fill_value=0.0
        )
    except (AttributeError, tf.errors.NotFoundError):
        # Fallback for older TF versions
        image = tf.raw_ops.ImageProjectiveTransformV2(
            images=image,
            transforms=tf.expand_dims(transform, 0),
            output_shape=tf.shape(image)[1:3],
            interpolation='BILINEAR'
        )
    return tf.squeeze(image, 0)


def random_zoom_crop(image):
    """Random zoom by cropping and resizing back."""
    shape = tf.shape(image)
    h, w = shape[0], shape[1]
    
    # Random crop between 80-100% of image
    scale = tf.random.uniform([], 0.80, 1.0)
    crop_h = tf.cast(tf.cast(h, tf.float32) * scale, tf.int32)
    crop_w = tf.cast(tf.cast(w, tf.float32) * scale, tf.int32)
    
    image = tf.image.random_crop(image, [crop_h, crop_w, 3])
    image = tf.image.resize(image, [h, w])
    return image


def random_erasing(image, probability=0.3, sl=0.02, sh=0.15):
    """Random erasing — masks a random rectangle with noise.
    
    Forces the model to not rely on a single region.
    Critical for footprints where the model might overfit to background.
    """
    def _erase():
        shape = tf.shape(image)
        h, w = shape[0], shape[1]
        area = tf.cast(h * w, tf.float32)
        
        erase_area = tf.random.uniform([], sl, sh) * area
        aspect = tf.random.uniform([], 0.3, 3.3)
        
        eh = tf.cast(tf.math.sqrt(erase_area * aspect), tf.int32)
        ew = tf.cast(tf.math.sqrt(erase_area / aspect), tf.int32)
        eh = tf.minimum(eh, h - 1)
        ew = tf.minimum(ew, w - 1)
        eh = tf.maximum(eh, 1)
        ew = tf.maximum(ew, 1)
        
        y = tf.random.uniform([], 0, h - eh, dtype=tf.int32)
        x = tf.random.uniform([], 0, w - ew, dtype=tf.int32)
        
        # Create binary mask using meshgrid (graph-safe)
        rows = tf.range(h)
        cols = tf.range(w)
        row_mask = tf.logical_and(rows >= y, rows < y + eh)
        col_mask = tf.logical_and(cols >= x, cols < x + ew)
        mask_2d = tf.logical_and(tf.expand_dims(row_mask, 1), tf.expand_dims(col_mask, 0))
        mask = tf.cast(tf.expand_dims(mask_2d, -1), tf.float32)  # [H, W, 1]
        
        # Fill masked area with random noise
        noise = tf.random.uniform(tf.shape(image), 0, 255)
        return image * (1.0 - mask) + noise * mask
    
    return tf.cond(tf.random.uniform([]) < probability, _erase, lambda: image)


def mixup(images, labels, alpha=0.3):
    """MixUp regularization — blend pairs of images and labels.
    
    Zhang et al. 2018 — proven 3-5% improvement on small datasets.
    Creates virtual training examples between real ones.
    """
    batch_size = tf.shape(images)[0]
    # Sample lambda — use uniform distribution biased toward endpoints
    lam = tf.random.uniform([], 0.65, 0.95)  # Keep most of original image
    
    indices = tf.random.shuffle(tf.range(batch_size))
    shuffled_images = tf.gather(images, indices)
    shuffled_labels = tf.gather(labels, indices)
    
    mixed_images = lam * images + (1 - lam) * shuffled_images
    mixed_labels = lam * labels + (1 - lam) * shuffled_labels
    
    return mixed_images, mixed_labels


def cutmix(images, labels, alpha=1.0):
    """CutMix regularization — cut and paste regions between images.
    
    Yun et al. 2019 — more effective than CutOut for classification.
    Uses binary mask approach (graph-mode safe).
    """
    batch_size = tf.shape(images)[0]
    img_h = tf.shape(images)[1]
    img_w = tf.shape(images)[2]
    
    # Sample lambda from Beta(alpha, alpha) — approximate with uniform
    lam = tf.random.uniform([], 0.2, 0.8)
    
    # Compute cut region
    cut_ratio = tf.math.sqrt(1.0 - lam)
    cut_h = tf.cast(tf.cast(img_h, tf.float32) * cut_ratio, tf.int32)
    cut_w = tf.cast(tf.cast(img_w, tf.float32) * cut_ratio, tf.int32)
    
    cy = tf.random.uniform([], 0, img_h, dtype=tf.int32)
    cx = tf.random.uniform([], 0, img_w, dtype=tf.int32)
    
    y1 = tf.maximum(cy - cut_h // 2, 0)
    y2 = tf.minimum(cy + cut_h // 2, img_h)
    x1 = tf.maximum(cx - cut_w // 2, 0)
    x2 = tf.minimum(cx + cut_w // 2, img_w)
    
    indices = tf.random.shuffle(tf.range(batch_size))
    shuffled_images = tf.gather(images, indices)
    shuffled_labels = tf.gather(labels, indices)
    
    # Create binary mask using meshgrid (graph-mode safe)
    rows = tf.range(img_h)
    cols = tf.range(img_w)
    row_mask = tf.logical_and(rows >= y1, rows < y2)  # [H]
    col_mask = tf.logical_and(cols >= x1, cols < x2)  # [W]
    # Outer product to create 2D mask [H, W]
    mask_2d = tf.logical_and(tf.expand_dims(row_mask, 1), tf.expand_dims(col_mask, 0))
    # Expand to [1, H, W, 1] for broadcasting
    mask = tf.cast(tf.reshape(mask_2d, [1, img_h, img_w, 1]), tf.float32)
    
    # Apply mask: keep original outside box, paste shuffled inside box
    mixed_images = images * (1.0 - mask) + shuffled_images * mask
    
    # Adjust labels proportionally to area
    cut_area = tf.cast((y2 - y1) * (x2 - x1), tf.float32)
    total_area = tf.cast(img_h * img_w, tf.float32)
    actual_lam = 1.0 - cut_area / total_area
    
    mixed_labels = actual_lam * labels + (1.0 - actual_lam) * shuffled_labels
    
    return mixed_images, mixed_labels


def create_train_dataset(paths, labels, img_size, num_classes, batch_size, augment=True):
    """Create training tf.data.Dataset with augmentation + MixUp/CutMix."""
    
    ds = tf.data.Dataset.from_tensor_slices((paths, labels))
    ds = ds.shuffle(buffer_size=len(paths), seed=SEED, reshuffle_each_iteration=True)
    ds = ds.map(lambda p, l: parse_image(p, l, img_size, num_classes),
                num_parallel_calls=tf.data.AUTOTUNE)
    
    if augment:
        ds = ds.map(augment_image, num_parallel_calls=tf.data.AUTOTUNE)
    
    ds = ds.batch(batch_size, drop_remainder=True)
    
    if augment:
        # Apply MixUp or CutMix at batch level using tf.cond (autograph-safe)
        def apply_batch_augment(images, labels):
            """Randomly apply MixUp, CutMix, or neither to a batch."""
            r = tf.random.uniform([])
            mixed_imgs, mixed_lbls = tf.cond(
                r < MIXUP_PROB,
                lambda: mixup(images, labels, MIXUP_ALPHA),
                lambda: tf.cond(
                    r < MIXUP_PROB + CUTMIX_PROB,
                    lambda: cutmix(images, labels, CUTMIX_ALPHA),
                    lambda: (images, labels)
                )
            )
            return mixed_imgs, mixed_lbls
        
        ds = ds.map(apply_batch_augment, num_parallel_calls=tf.data.AUTOTUNE)
    
    ds = ds.prefetch(tf.data.AUTOTUNE)
    return ds


def create_val_dataset(paths, labels, img_size, num_classes, batch_size):
    """Create validation tf.data.Dataset (no augmentation)."""
    ds = tf.data.Dataset.from_tensor_slices((paths, labels))
    ds = ds.map(lambda p, l: parse_image(p, l, img_size, num_classes),
                num_parallel_calls=tf.data.AUTOTUNE)
    ds = ds.batch(batch_size)
    ds = ds.prefetch(tf.data.AUTOTUNE)
    return ds


# ============================================
# TEST-TIME AUGMENTATION (TTA)
# ============================================
def tta_predict(model, img_array, n_augments=5):
    """Run multiple augmented forward passes and average predictions.
    
    Consistently adds 1-3% accuracy over single-pass inference.
    Uses conservative augmentations that don't distort features.
    """
    predictions = []
    
    # Original (no augmentation)
    pred = model.predict(img_array, verbose=0)[0]
    predictions.append(pred)
    
    for _ in range(n_augments - 1):
        aug = img_array.copy()
        
        # Random horizontal flip
        if random.random() > 0.5:
            aug = np.flip(aug, axis=2)
        
        # Slight brightness shift
        aug = aug + np.random.uniform(-15, 15)
        
        # Slight zoom (center crop + resize)
        if random.random() > 0.5:
            h, w = aug.shape[1], aug.shape[2]
            crop = int(0.9 * h)
            offset = (h - crop) // 2
            cropped = aug[:, offset:offset+crop, offset:offset+crop, :]
            aug = tf.image.resize(cropped, [h, w]).numpy()
        
        aug = np.clip(aug, 0, 255).astype(np.float32)
        pred = model.predict(aug, verbose=0)[0]
        predictions.append(pred)
    
    # Geometric mean (better than arithmetic for probabilities)
    predictions = np.array(predictions)
    geo_mean = np.exp(np.mean(np.log(predictions + 1e-10), axis=0))
    geo_mean = geo_mean / np.sum(geo_mean)  # Normalize
    
    return geo_mean


# ============================================
# MODEL ARCHITECTURE
# ============================================
def build_model(num_classes, img_size=IMG_SIZE_FINAL):
    """Build EfficientNetB3 with improved classification head.
    
    Improvements over v3:
    - Squeeze-and-Excitation channel attention after GAP
    - Slightly wider bottleneck (384 → 256 → num_classes)
    - Consistent swish activations
    """
    print(f"\n[MODEL] Building EfficientNetB3 ({img_size}x{img_size}, {num_classes} classes)...")
    
    base_model = EfficientNetB3(
        weights='imagenet',
        include_top=False,
        input_shape=(img_size, img_size, 3)
    )
    base_model.trainable = False  # Frozen for Phase 1
    
    inputs = tf.keras.Input(shape=(img_size, img_size, 3))
    x = base_model(inputs, training=False)
    
    # Global Average Pooling
    x = layers.GlobalAveragePooling2D(name='gap')(x)
    
    # Squeeze-and-Excitation channel attention
    # Learns which feature channels are most important for footprint classification
    se = layers.Dense(x.shape[-1] // 16, activation='swish', name='se_squeeze')(x)
    se = layers.Dense(x.shape[-1], activation='sigmoid', name='se_excite')(se)
    x = layers.Multiply(name='se_scale')([x, se])
    
    # Classification head
    x = layers.BatchNormalization(name='head_bn')(x)
    x = layers.Dense(384, kernel_regularizer=regularizers.l2(1e-4), name='fc1')(x)
    x = layers.Activation('swish', name='fc1_act')(x)
    x = layers.Dropout(0.4, name='dropout1')(x)
    x = layers.Dense(256, kernel_regularizer=regularizers.l2(1e-4), name='fc2')(x)
    x = layers.Activation('swish', name='fc2_act')(x)
    x = layers.Dropout(0.3, name='dropout2')(x)
    outputs = layers.Dense(num_classes, activation='softmax', name='predictions')(x)
    
    model = models.Model(inputs, outputs, name="WildTrackAI_v4")
    
    print(f"  Base params:  {base_model.count_params():,}")
    print(f"  Total params: {model.count_params():,}")
    print(f"  Base layers:  {len(base_model.layers)}")
    
    return model, base_model


def compile_model(model, learning_rate=1e-3, focal_loss=None):
    """Compile with focal loss and AdamW."""
    loss = focal_loss if focal_loss else tf.keras.losses.CategoricalCrossentropy(label_smoothing=0.1)
    
    model.compile(
        optimizer=tf.keras.optimizers.AdamW(
            learning_rate=learning_rate,
            weight_decay=1e-4,
            clipnorm=1.0
        ),
        loss=loss,
        metrics=[
            'accuracy',
            tf.keras.metrics.Precision(name='precision'),
            tf.keras.metrics.Recall(name='recall'),
            tf.keras.metrics.AUC(name='auc', multi_label=True),
        ]
    )


# ============================================
# CALLBACKS
# ============================================
class SnapshotEnsemble(Callback):
    """Save model snapshots at each LR cycle minimum for later ensembling."""
    def __init__(self, save_dir, lr_schedule):
        super().__init__()
        self.save_dir = save_dir
        self.lr_schedule = lr_schedule
        self.snapshot_count = 0
        os.makedirs(save_dir, exist_ok=True)
    
    def on_epoch_end(self, epoch, logs=None):
        # Save snapshot when LR is at minimum (end of cosine cycle)
        if hasattr(self.lr_schedule, 'cycle_epoch') and self.lr_schedule.cycle_epoch == 0 and epoch > 3:
            path = os.path.join(self.save_dir, f"snapshot_{self.snapshot_count}.h5")
            self.model.save(path)
            self.snapshot_count += 1
            val_acc = logs.get('val_accuracy', 0)
            print(f"  📸 Snapshot #{self.snapshot_count} saved (val_acc={val_acc:.4f})")


def create_callbacks(phase, lr_schedule=None, snapshot_ensemble=None):
    """Create callbacks for a training phase."""
    cbs = [
        ModelCheckpoint(CHECKPOINT_PATH, monitor='val_accuracy',
                       mode='max', save_best_only=True, verbose=1),
        EarlyStopping(monitor='val_loss', patience=8,
                     restore_best_weights=True, verbose=1),
        TensorBoard(log_dir=os.path.join(LOG_DIR, phase), histogram_freq=0),
    ]
    if lr_schedule:
        cbs.append(lr_schedule)
    else:
        cbs.append(ReduceLROnPlateau(monitor='val_loss', factor=0.5,
                                     patience=3, min_lr=1e-7, verbose=1))
    if snapshot_ensemble:
        cbs.append(snapshot_ensemble)
    return cbs


# ============================================
# STOCHASTIC WEIGHT AVERAGING (SWA)
# ============================================
def apply_swa(model, snapshot_dir, val_dataset, focal_loss):
    """Average weights from multiple snapshots for smoother generalization.
    
    Izmailov et al. 2018 — SWA consistently improves generalization.
    """
    snapshot_files = sorted(Path(snapshot_dir).glob("snapshot_*.h5"))
    if len(snapshot_files) < 2:
        print("  Not enough snapshots for SWA (need ≥2)")
        return model
    
    print(f"\n[SWA] Averaging {len(snapshot_files)} snapshots...")
    
    # Load all snapshot weights
    all_weights = []
    for sf in snapshot_files:
        snap_model = tf.keras.models.load_model(
            str(sf), compile=False, custom_objects={'FocalLoss': FocalLoss}
        )
        all_weights.append(snap_model.get_weights())
        print(f"  Loaded: {sf.name}")
    
    # Average weights
    avg_weights = []
    for weights_list_tuple in zip(*all_weights):
        avg_weights.append(np.mean(weights_list_tuple, axis=0))
    
    model.set_weights(avg_weights)
    
    # Evaluate SWA model
    compile_model(model, learning_rate=1e-5, focal_loss=focal_loss)
    results = model.evaluate(val_dataset, verbose=0)
    metrics = dict(zip(model.metrics_names, results))
    print(f"  SWA val_accuracy: {metrics.get('accuracy', 0):.4f}")
    
    # Save SWA model
    model.save(SWA_PATH)
    print(f"  Saved: {SWA_PATH}")
    
    return model


# ============================================
# DATASET DETECTION
# ============================================
def detect_dataset(preferred_dataset=None):
    """Detect best available dataset."""
    candidates = []
    if preferred_dataset:
        candidates.append(preferred_dataset)
    candidates.extend([DATASET_STRICT, DATASET_DIR, DATASET_RAW])

    unique_candidates = []
    for dpath in candidates:
        if dpath and dpath not in unique_candidates:
            unique_candidates.append(dpath)

    for dpath in unique_candidates:
        if os.path.isdir(dpath):
            classes = sorted([
                d for d in os.listdir(dpath)
                if os.path.isdir(os.path.join(dpath, d))
                and len(os.listdir(os.path.join(dpath, d))) > 0
            ])
            if classes:
                counts = {c: len([f for f in os.listdir(os.path.join(dpath, c))
                                  if f.lower().endswith(('.jpg', '.jpeg', '.png', '.bmp', '.webp'))])
                          for c in classes}
                total = sum(counts.values())
                print(f"\n  Dataset: {dpath}")
                print(f"  Total: {total} images")
                for c, n in counts.items():
                    pct = n / total if total > 0 else 0
                    print(f"    {c}: {n} ({pct:.1%})")
                return dpath, classes
    
    print("ERROR: No dataset found!")
    sys.exit(1)


def compute_class_weights(labels, class_names):
    """Compute balanced class weights from label array."""
    from sklearn.utils.class_weight import compute_class_weight
    weights = compute_class_weight(
        class_weight='balanced',
        classes=np.unique(labels),
        y=labels
    )
    weight_dict = dict(enumerate(weights))
    print("\n[WEIGHTS] Class weights (balanced):")
    for idx, w in weight_dict.items():
        print(f"  {class_names[idx]:>10}: {w:.3f}")
    return weight_dict


# ============================================
# EVALUATION
# ============================================
def generate_evaluation(model, val_paths, val_labels, class_names, img_size, use_tta=False):
    """Full evaluation with optional TTA."""
    from sklearn.metrics import confusion_matrix, classification_report, roc_curve, auc
    from sklearn.preprocessing import label_binarize
    import seaborn as sns
    
    print("\n[EVAL] Running full evaluation...")
    num_classes = len(class_names)
    
    all_preds = []
    all_probs = []
    
    for i, path in enumerate(val_paths):
        img = tf.io.read_file(path)
        img = tf.image.decode_image(img, channels=3, expand_animations=False)
        img = tf.image.resize(img, [img_size, img_size])
        img = tf.cast(img, tf.float32)
        img_array = np.expand_dims(img.numpy(), 0)
        
        if use_tta:
            probs = tta_predict(model, img_array, n_augments=TTA_AUGMENTS)
        else:
            probs = model.predict(img_array, verbose=0)[0]
        
        all_probs.append(probs)
        all_preds.append(np.argmax(probs))
        
        if (i + 1) % 50 == 0:
            print(f"  Evaluated {i+1}/{len(val_paths)}...")
    
    y_pred = np.array(all_preds)
    y_true = np.array(val_labels)
    predictions = np.array(all_probs)
    
    # Classification report
    report = classification_report(y_true, y_pred, target_names=class_names,
                                   output_dict=True, zero_division=0)
    report_text = classification_report(y_true, y_pred, target_names=class_names,
                                        zero_division=0)
    print(f"\n{'With TTA' if use_tta else 'Standard'} Results:")
    print(report_text)
    
    suffix = "_tta" if use_tta else ""
    
    with open(os.path.join(OUTPUTS_DIR, f"classification_report{suffix}.json"), 'w') as f:
        json.dump(report, f, indent=2)
    
    # Confusion matrix
    cm = confusion_matrix(y_true, y_pred)
    plt.figure(figsize=(12, 10))
    sns.heatmap(cm, annot=True, fmt='d', cmap='Blues',
                xticklabels=class_names, yticklabels=class_names)
    plt.title(f'WildTrackAI v4 — Confusion Matrix{"(TTA)" if use_tta else ""}', fontsize=16)
    plt.ylabel('True Label', fontsize=13)
    plt.xlabel('Predicted Label', fontsize=13)
    plt.tight_layout()
    plt.savefig(os.path.join(OUTPUTS_DIR, f"confusion_matrix{suffix}.png"), dpi=150)
    plt.close()
    
    # Top confusion pairs — which species are most confused?
    print("\n  Top confusion pairs:")
    confusion_pairs = []
    for i in range(num_classes):
        for j in range(num_classes):
            if i != j and cm[i][j] > 0:
                confusion_pairs.append((class_names[i], class_names[j], cm[i][j]))
    confusion_pairs.sort(key=lambda x: x[2], reverse=True)
    for true_cls, pred_cls, count in confusion_pairs[:5]:
        print(f"    {true_cls} → {pred_cls}: {count} errors")
    
    with open(os.path.join(OUTPUTS_DIR, f"top_confusions{suffix}.json"), 'w') as f:
        json.dump([{"true": t, "predicted": p, "count": int(c)} for t, p, c in confusion_pairs], f, indent=2)
    
    # ROC curves
    y_true_bin = label_binarize(y_true, classes=range(num_classes))
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
    plt.title(f'WildTrackAI v4 — ROC Curves{"(TTA)" if use_tta else ""}', fontsize=16)
    plt.legend(loc='lower right')
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig(os.path.join(OUTPUTS_DIR, f"roc_curves{suffix}.png"), dpi=150)
    plt.close()
    
    # Per-class performance bar chart
    precisions = [report.get(c, {}).get('precision', 0) for c in class_names]
    recalls = [report.get(c, {}).get('recall', 0) for c in class_names]
    f1s = [report.get(c, {}).get('f1-score', 0) for c in class_names]
    
    x = np.arange(num_classes)
    width = 0.25
    fig, ax = plt.subplots(figsize=(14, 6))
    ax.bar(x - width, precisions, width, label='Precision', color='#4e79a7')
    ax.bar(x, recalls, width, label='Recall', color='#f28e2b')
    ax.bar(x + width, f1s, width, label='F1-Score', color='#e15759')
    ax.set_xlabel('Species')
    ax.set_ylabel('Score')
    ax.set_title(f'WildTrackAI v4 — Per-Class Performance{"(TTA)" if use_tta else ""}', fontsize=16)
    ax.set_xticks(x)
    ax.set_xticklabels(class_names, rotation=45, ha='right')
    ax.legend()
    ax.set_ylim(0, 1.1)
    ax.grid(True, axis='y', alpha=0.3)
    plt.tight_layout()
    plt.savefig(os.path.join(OUTPUTS_DIR, f"per_class_accuracy{suffix}.png"), dpi=150)
    plt.close()
    
    print(f"  Saved: confusion_matrix{suffix}.png, roc_curves{suffix}.png, per_class_accuracy{suffix}.png")
    return report, y_true, y_pred, predictions


def plot_training_history(histories, phase_labels):
    """Plot combined training history across all phases."""
    print("[EVAL] Training history plots...")
    
    acc, val_acc, loss, val_loss = [], [], [], []
    phase_boundaries = []
    total = 0
    
    for h, label in zip(histories, phase_labels):
        if h:
            n = len(h.history.get('accuracy', []))
            acc.extend(h.history.get('accuracy', []))
            val_acc.extend(h.history.get('val_accuracy', []))
            loss.extend(h.history.get('loss', []))
            val_loss.extend(h.history.get('val_loss', []))
            total += n
            phase_boundaries.append((total, label))
    
    if not acc:
        return
    
    fig, axes = plt.subplots(1, 2, figsize=(16, 6))
    
    axes[0].plot(acc, label='Train Acc', lw=2, color='#2196F3')
    axes[0].plot(val_acc, label='Val Acc', lw=2, color='#E91E63')
    for boundary, label in phase_boundaries[:-1]:
        axes[0].axvline(x=boundary, color='gray', ls='--', alpha=0.5, label=label)
    axes[0].set_title('Model Accuracy', fontsize=14)
    axes[0].set_xlabel('Epoch')
    axes[0].set_ylabel('Accuracy')
    axes[0].legend()
    axes[0].grid(True, alpha=0.3)
    
    axes[1].plot(loss, label='Train Loss', lw=2, color='#2196F3')
    axes[1].plot(val_loss, label='Val Loss', lw=2, color='#E91E63')
    for boundary, label in phase_boundaries[:-1]:
        axes[1].axvline(x=boundary, color='gray', ls='--', alpha=0.5)
    axes[1].set_title('Model Loss', fontsize=14)
    axes[1].set_xlabel('Epoch')
    axes[1].set_ylabel('Loss')
    axes[1].legend()
    axes[1].grid(True, alpha=0.3)
    
    plt.suptitle('WildTrackAI v4 — Training History', fontsize=16, y=1.02)
    plt.tight_layout()
    plt.savefig(os.path.join(OUTPUTS_DIR, "training_history_v4.png"), dpi=150, bbox_inches='tight')
    plt.close()
    print("  Saved: training_history_v4.png")


# ============================================
# STRATIFIED K-FOLD CROSS-VALIDATION
# ============================================
def kfold_train(dataset_path, class_names, n_folds=5):
    """Run stratified K-fold cross-validation for reliable metrics.
    
    With only ~232 validation samples per split, a single split is noisy.
    K-fold gives standard deviation of accuracy — measures reliability.
    """
    from sklearn.model_selection import StratifiedKFold
    
    print(f"\n{'='*70}")
    print(f"  STRATIFIED {n_folds}-FOLD CROSS-VALIDATION")
    print(f"{'='*70}")
    
    num_classes = len(class_names)
    
    # Load all paths and labels
    all_paths = []
    all_labels = []
    for idx, cls in enumerate(class_names):
        cls_dir = os.path.join(dataset_path, cls)
        for fname in sorted(os.listdir(cls_dir)):
            if fname.lower().endswith(('.jpg', '.jpeg', '.png', '.bmp', '.webp')):
                all_paths.append(os.path.join(cls_dir, fname))
                all_labels.append(idx)
    
    all_paths = np.array(all_paths)
    all_labels = np.array(all_labels)
    
    skf = StratifiedKFold(n_splits=n_folds, shuffle=True, random_state=SEED)
    fold_results = []
    
    for fold, (train_idx, val_idx) in enumerate(skf.split(all_paths, all_labels)):
        print(f"\n{'─'*50}")
        print(f"  FOLD {fold+1}/{n_folds}")
        print(f"{'─'*50}")
        
        train_paths = all_paths[train_idx]
        train_labels = all_labels[train_idx]
        val_paths = all_paths[val_idx]
        val_labels = all_labels[val_idx]
        
        # Compute class weights for this fold
        class_weights = compute_class_weights(train_labels, class_names)
        alpha_values = np.array([class_weights[i] for i in range(num_classes)], dtype=np.float32)
        alpha_tensor = tf.constant(alpha_values, dtype=tf.float32)
        focal_loss = FocalLoss(gamma=2.0, alpha=alpha_tensor, label_smoothing=LABEL_SMOOTHING)
        
        # Create datasets
        train_ds = create_train_dataset(train_paths, train_labels, IMG_SIZE_FINAL,
                                        num_classes, BATCH_SIZE, augment=True)
        val_ds = create_val_dataset(val_paths, val_labels, IMG_SIZE_FINAL,
                                    num_classes, BATCH_SIZE)
        
        # Build fresh model for each fold
        model, base_model = build_model(num_classes, IMG_SIZE_FINAL)
        compile_model(model, learning_rate=1e-3, focal_loss=focal_loss)
        
        # Phase 1: Frozen base
        lr1 = SGDRSchedule(max_lr=1e-3, min_lr=1e-6, cycle_length=10, warmup_epochs=2)
        h1 = model.fit(train_ds, validation_data=val_ds, epochs=15,
                       callbacks=[lr1, EarlyStopping(monitor='val_loss', patience=5,
                                                     restore_best_weights=True)],
                       class_weight=class_weights, verbose=0)
        
        # Phase 2: Unfreeze last 80 layers
        base_model.trainable = True
        for layer in base_model.layers[:-80]:
            layer.trainable = False
        compile_model(model, learning_rate=5e-5, focal_loss=focal_loss)
        h2 = model.fit(train_ds, validation_data=val_ds, epochs=10,
                       callbacks=[EarlyStopping(monitor='val_loss', patience=5,
                                               restore_best_weights=True)],
                       class_weight=class_weights, verbose=0)
        
        # Evaluate (with TTA)
        report, _, _, _ = generate_evaluation(model, val_paths, val_labels,
                                              class_names, IMG_SIZE_FINAL, use_tta=True)
        
        fold_acc = report.get('accuracy', 0)
        fold_f1 = report.get('macro avg', {}).get('f1-score', 0)
        fold_results.append({'fold': fold+1, 'accuracy': fold_acc, 'f1': fold_f1})
        print(f"  Fold {fold+1}: acc={fold_acc:.4f}, f1={fold_f1:.4f}")
        
        # Clean up
        del model, base_model
        tf.keras.backend.clear_session()
    
    # Summary
    accs = [r['accuracy'] for r in fold_results]
    f1s = [r['f1'] for r in fold_results]
    print(f"\n{'='*70}")
    print(f"  K-FOLD RESULTS ({n_folds} folds)")
    print(f"{'='*70}")
    print(f"  Accuracy: {np.mean(accs):.4f} ± {np.std(accs):.4f}")
    print(f"  F1-Score: {np.mean(f1s):.4f} ± {np.std(f1s):.4f}")
    print(f"  Range:    [{min(accs):.4f}, {max(accs):.4f}]")
    
    with open(os.path.join(OUTPUTS_DIR, "kfold_results.json"), 'w') as f:
        json.dump({
            'n_folds': n_folds,
            'accuracy_mean': float(np.mean(accs)),
            'accuracy_std': float(np.std(accs)),
            'f1_mean': float(np.mean(f1s)),
            'f1_std': float(np.std(f1s)),
            'folds': fold_results
        }, f, indent=2)
    
    return fold_results


# ============================================
# MAIN TRAINING LOOP
# ============================================
def train(progressive=False, dataset_path=None, target_accuracy=0.80, enforce_target=False):
    """Full training pipeline with all v4 improvements."""
    for d in [MODELS_DIR, OUTPUTS_DIR, LOG_DIR]:
        os.makedirs(d, exist_ok=True)
    
    snapshot_dir = os.path.join(MODELS_DIR, "snapshots")
    os.makedirs(snapshot_dir, exist_ok=True)
    
    print("=" * 70)
    print("  WILDTRACKAI v4 — Maximum Accuracy Pipeline")
    print("=" * 70)
    
    dataset_path, class_names = detect_dataset(dataset_path)
    num_classes = len(class_names)
    
    config_summary = {
        'backbone': 'EfficientNetB3',
        'loss': f'FocalLoss(γ=2.0, smoothing={LABEL_SMOOTHING})',
        'mixup': f'α={MIXUP_ALPHA}, p={MIXUP_PROB}',
        'cutmix': f'α={CUTMIX_ALPHA}, p={CUTMIX_PROB}',
        'optimizer': 'AdamW + SGDR',
        'progressive': progressive,
        'tta': f'{TTA_AUGMENTS} augments',
        'dataset': dataset_path,
        'target_accuracy': f'{target_accuracy:.2%}',
    }
    
    print(f"\n  Config:")
    for k, v in config_summary.items():
        print(f"    {k:>15}: {v}")
    
    # ── Load data ──
    train_paths, train_labels, val_paths, val_labels = load_dataset(
        dataset_path, class_names, IMG_SIZE_FINAL, validation_split=0.2
    )
    
    # ── Class weights ──
    class_weights = compute_class_weights(train_labels, class_names)
    alpha_values = np.array([class_weights[i] for i in range(num_classes)], dtype=np.float32)
    alpha_tensor = tf.constant(alpha_values, dtype=tf.float32)
    focal_loss = FocalLoss(gamma=2.0, alpha=alpha_tensor, label_smoothing=LABEL_SMOOTHING)
    
    # ═══════════════════════════════════════════════════
    # PROGRESSIVE RESIZING (optional) — Phase 0
    # ═══════════════════════════════════════════════════
    if progressive:
        print("\n" + "=" * 70)
        print(f"  PHASE 0: PROGRESSIVE WARMUP ({IMG_SIZE_WARMUP}x{IMG_SIZE_WARMUP})")
        print("=" * 70)
        
        train_ds_small = create_train_dataset(train_paths, train_labels, IMG_SIZE_WARMUP,
                                              num_classes, BATCH_SIZE, augment=True)
        val_ds_small = create_val_dataset(val_paths, val_labels, IMG_SIZE_WARMUP,
                                          num_classes, BATCH_SIZE)
        
        model_small, base_small = build_model(num_classes, IMG_SIZE_WARMUP)
        compile_model(model_small, learning_rate=1e-3, focal_loss=focal_loss)
        
        lr0 = SGDRSchedule(max_lr=1e-3, min_lr=1e-6, cycle_length=5, warmup_epochs=1)
        h0 = model_small.fit(
            train_ds_small, validation_data=val_ds_small,
            epochs=10,
            callbacks=[lr0, EarlyStopping(monitor='val_loss', patience=5,
                                          restore_best_weights=True)],
            class_weight=class_weights, verbose=1
        )
        
        p0_best = max(h0.history.get('val_accuracy', [0]))
        print(f"\n  Phase 0 complete: best val_acc={p0_best:.4f}")
        
        # Transfer head weights to full-size model
        head_weights = {}
        for layer in model_small.layers:
            if 'efficientnet' not in layer.name.lower():
                try:
                    head_weights[layer.name] = layer.get_weights()
                except:
                    pass
        
        del model_small, base_small
        tf.keras.backend.clear_session()
    
    # ── Create full-size datasets ──
    train_ds = create_train_dataset(train_paths, train_labels, IMG_SIZE_FINAL,
                                    num_classes, BATCH_SIZE, augment=True)
    val_ds = create_val_dataset(val_paths, val_labels, IMG_SIZE_FINAL,
                                num_classes, BATCH_SIZE)
    
    # ── Build full-size model ──
    model, base_model = build_model(num_classes, IMG_SIZE_FINAL)
    
    # Transfer progressive warmup weights
    if progressive and head_weights:
        print("  Transferring head weights from Phase 0...")
        for layer in model.layers:
            if layer.name in head_weights and head_weights[layer.name]:
                try:
                    layer.set_weights(head_weights[layer.name])
                    print(f"    ✓ {layer.name}")
                except Exception as e:
                    print(f"    ✗ {layer.name}: {e}")
    
    # ═══════════════════════════════════════════════════
    # PHASE 1: FROZEN BASE — HEAD TRAINING
    # ═══════════════════════════════════════════════════
    print("\n" + "=" * 70)
    print("  PHASE 1: FEATURE EXTRACTION (FROZEN BASE)")
    print("=" * 70)
    
    lr1 = SGDRSchedule(max_lr=1e-3, min_lr=1e-6, cycle_length=10, warmup_epochs=3)
    snapshot1 = SnapshotEnsemble(snapshot_dir, lr1)
    compile_model(model, learning_rate=1e-3, focal_loss=focal_loss)
    
    h1 = model.fit(
        train_ds, validation_data=val_ds,
        epochs=PHASE1_EPOCHS,
        callbacks=create_callbacks("phase1", lr1, snapshot1),
        class_weight=class_weights, verbose=1
    )
    p1_done = len(h1.epoch)
    p1_best = max(h1.history.get('val_accuracy', [0]))
    print(f"\n  Phase 1 complete: {p1_done} epochs, best val_acc={p1_best:.4f}")
    
    # Save Phase 1 checkpoint
    if os.path.exists(CHECKPOINT_PATH):
        shutil.copy2(CHECKPOINT_PATH, os.path.join(MODELS_DIR, "checkpoint_phase1_v4.h5"))
    
    # ═══════════════════════════════════════════════════
    # PHASE 2: FINE-TUNE LAST 80 LAYERS
    # ═══════════════════════════════════════════════════
    print("\n" + "=" * 70)
    print("  PHASE 2: FINE-TUNING (LAST 80 LAYERS)")
    print("=" * 70)
    
    h2 = None
    try:
        base_model.trainable = True
        for layer in base_model.layers[:-80]:
            layer.trainable = False
        
        trainable = sum(1 for l in base_model.layers if l.trainable)
        print(f"  Trainable: {trainable}/{len(base_model.layers)} base layers")
        
        lr2 = SGDRSchedule(max_lr=5e-5, min_lr=1e-7, cycle_length=7, warmup_epochs=2)
        snapshot2 = SnapshotEnsemble(snapshot_dir, lr2)
        compile_model(model, learning_rate=5e-5, focal_loss=focal_loss)
        
        h2 = model.fit(
            train_ds, validation_data=val_ds,
            epochs=p1_done + PHASE2_EPOCHS,
            initial_epoch=p1_done,
            callbacks=create_callbacks("phase2", lr2, snapshot2),
            class_weight=class_weights, verbose=1
        )
        p2_done = len(h2.epoch)
        p2_best = max(h2.history.get('val_accuracy', [0]))
        print(f"\n  Phase 2 complete: {p2_done} epochs, best val_acc={p2_best:.4f}")
    except (KeyboardInterrupt, Exception) as e:
        print(f"\n[WARNING] Phase 2 interrupted: {e}")
        p2_done = 0
    
    # ═══════════════════════════════════════════════════
    # PHASE 3: DEEP FINE-TUNE + SWA COLLECTION
    # ═══════════════════════════════════════════════════
    print("\n" + "=" * 70)
    print("  PHASE 3: DEEP FINE-TUNING (LAST 140 LAYERS) + SWA")
    print("=" * 70)
    
    h3 = None
    try:
        for layer in base_model.layers[:-140]:
            layer.trainable = False
        for layer in base_model.layers[-140:]:
            layer.trainable = True
        
        trainable = sum(1 for l in base_model.layers if l.trainable)
        print(f"  Trainable: {trainable}/{len(base_model.layers)} base layers")
        
        lr3 = SGDRSchedule(max_lr=1e-5, min_lr=1e-8, cycle_length=5, warmup_epochs=1)
        snapshot3 = SnapshotEnsemble(snapshot_dir, lr3)
        compile_model(model, learning_rate=1e-5, focal_loss=focal_loss)
        
        start_epoch = p1_done + (p2_done if h2 else 0)
        h3 = model.fit(
            train_ds, validation_data=val_ds,
            epochs=start_epoch + PHASE3_EPOCHS,
            initial_epoch=start_epoch,
            callbacks=create_callbacks("phase3", lr3, snapshot3),
            class_weight=class_weights, verbose=1
        )
        p3_done = len(h3.epoch)
        p3_best = max(h3.history.get('val_accuracy', [0]))
        print(f"\n  Phase 3 complete: {p3_done} epochs, best val_acc={p3_best:.4f}")
    except (KeyboardInterrupt, Exception) as e:
        print(f"\n[WARNING] Phase 3 interrupted: {e}")
    
    # ── Load best checkpoint ──
    print("\n  Loading best checkpoint...")
    if os.path.exists(CHECKPOINT_PATH):
        model = tf.keras.models.load_model(CHECKPOINT_PATH, compile=False,
                                            custom_objects={'FocalLoss': FocalLoss})
        compile_model(model, learning_rate=1e-5, focal_loss=focal_loss)
        print("  Best checkpoint loaded.")
    
    # ── Apply SWA ──
    swa_model = apply_swa(model, snapshot_dir, val_ds, focal_loss)
    
    # ═══════════════════════════════════════════════════
    # EVALUATION — Standard + TTA
    # ═══════════════════════════════════════════════════
    print("\n" + "=" * 70)
    print("  EVALUATION")
    print("=" * 70)
    
    # Standard evaluation
    report_std, _, _, _ = generate_evaluation(
        model, val_paths, val_labels, class_names, IMG_SIZE_FINAL, use_tta=False
    )
    
    # TTA evaluation
    report_tta, y_true, y_pred, preds = generate_evaluation(
        model, val_paths, val_labels, class_names, IMG_SIZE_FINAL, use_tta=True
    )
    
    # SWA evaluation (if available)
    report_swa = None
    if swa_model is not model:
        print("\n  Evaluating SWA model with TTA...")
        report_swa, _, _, _ = generate_evaluation(
            swa_model, val_paths, val_labels, class_names, IMG_SIZE_FINAL, use_tta=True
        )
    
    # Pick the best model variant
    acc_std = report_std.get('accuracy', 0)
    acc_tta = report_tta.get('accuracy', 0)
    acc_swa = report_swa.get('accuracy', 0) if report_swa else 0
    
    best_acc = max(acc_std, acc_tta, acc_swa)
    best_variant = "standard"
    best_model = model
    best_report = report_std
    
    if acc_tta >= best_acc:
        best_variant = "TTA"
        best_report = report_tta
    if acc_swa > best_acc:
        best_variant = "SWA+TTA"
        best_model = swa_model
        best_report = report_swa
    
    print(f"\n  Best variant: {best_variant} (acc={best_acc:.4f})")
    
    # Training history plot
    plot_training_history(
        [h1, h2, h3],
        ['Phase 1→2', 'Phase 2→3', 'End']
    )
    
    # ── Save best model ──
    print(f"\n[SAVE] Saving v4 model: {MODEL_PATH}")
    best_model.save(MODEL_PATH)
    
    print(f"[SAVE] Saving as production model: {MODEL_FINAL_PATH}")
    best_model.save(MODEL_FINAL_PATH)
    
    # Save metadata
    macro = best_report.get('macro avg', {})
    metadata = {
        "model_name": "WildTrackAI_v4",
        "version": "4.0_max_accuracy",
        "class_names": class_names,
        "class_indices": {c: i for i, c in enumerate(class_names)},
        "num_classes": num_classes,
        "img_size": IMG_SIZE_FINAL,
        "architecture": "EfficientNetB3 + SE Attention + MixUp/CutMix + SGDR + SWA",
        "accuracy": float(best_report.get('accuracy', 0)),
        "precision": float(macro.get('precision', 0)),
        "recall": float(macro.get('recall', 0)),
        "f1_score": float(macro.get('f1-score', 0)),
        "best_variant": best_variant,
        "results_standard": {
            "accuracy": float(acc_std),
            "f1": float(report_std.get('macro avg', {}).get('f1-score', 0))
        },
        "results_tta": {
            "accuracy": float(acc_tta),
            "f1": float(report_tta.get('macro avg', {}).get('f1-score', 0))
        },
        "results_swa": {
            "accuracy": float(acc_swa),
            "f1": float(report_swa.get('macro avg', {}).get('f1-score', 0)) if report_swa else 0
        },
        "training_samples": len(train_paths),
        "validation_samples": len(val_paths),
        "total_params": best_model.count_params(),
        "backbone": "EfficientNetB3",
        "loss": f"FocalLoss(gamma=2.0, smoothing={LABEL_SMOOTHING})",
        "augmentation": f"MixUp(α={MIXUP_ALPHA})+CutMix(α={CUTMIX_ALPHA})+RandomErase+StrongAug",
        "optimizer": "AdamW + SGDR (cosine warm restarts)",
        "phases": "3-phase: frozen→ft80→ft140",
        "tta_augments": TTA_AUGMENTS,
        "training_date": datetime.datetime.now().isoformat(),
        "dataset_path": dataset_path,
        "target_accuracy": float(target_accuracy),
        "target_met": bool(best_report.get('accuracy', 0) >= target_accuracy),
    }
    with open(METADATA_PATH, 'w') as f:
        json.dump(metadata, f, indent=2)
    
    print("\n" + "=" * 70)
    print("  TRAINING COMPLETE!")
    print("=" * 70)
    print(f"  Best variant:  {best_variant}")
    print(f"  Accuracy:      {best_report.get('accuracy', 0):.2%}")
    print(f"  Target (>=):   {target_accuracy:.2%}")
    print(f"  Target met:    {'YES' if best_report.get('accuracy', 0) >= target_accuracy else 'NO'}")
    print(f"  Precision:     {macro.get('precision', 0):.2%}")
    print(f"  Recall:        {macro.get('recall', 0):.2%}")
    print(f"  F1-Score:      {macro.get('f1-score', 0):.2%}")
    print(f"\n  Standard:      {acc_std:.2%}")
    print(f"  + TTA:         {acc_tta:.2%}")
    print(f"  + SWA+TTA:     {acc_swa:.2%}")
    print(f"\n  Model (v4):    {MODEL_PATH}")
    print(f"  Production:    {MODEL_FINAL_PATH}")
    print(f"  Metadata:      {METADATA_PATH}")
    print(f"  Evaluation:    {OUTPUTS_DIR}/")
    print("=" * 70)

    if enforce_target and best_report.get('accuracy', 0) < target_accuracy:
        raise RuntimeError(
            f"Target accuracy not reached: {best_report.get('accuracy', 0):.4f} < {target_accuracy:.4f}"
        )
    
    return best_model, best_report


# ============================================
# CLI
# ============================================
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="WildTrackAI v4 — Maximum Accuracy Training")
    parser.add_argument("--epochs", type=int, help="Phase 1 epochs (default: 20)")
    parser.add_argument("--batch", type=int, help="Batch size (default: 16)")
    parser.add_argument("--progressive", action="store_true", help="Enable progressive resizing")
    parser.add_argument("--kfold", type=int, default=0, help="Run K-fold CV (e.g., --kfold 5)")
    parser.add_argument("--tta", type=int, default=TTA_AUGMENTS, help=f"TTA augments (default: {TTA_AUGMENTS})")
    parser.add_argument("--dataset", type=str, default=None, help="Dataset path (default: auto-detect strict→cleaned→raw)")
    parser.add_argument("--target-accuracy", type=float, default=0.80, help="Target validation accuracy (default: 0.80)")
    parser.add_argument("--enforce-target", action="store_true", help="Fail run if target accuracy is not reached")
    args = parser.parse_args()
    
    if args.epochs:
        PHASE1_EPOCHS = args.epochs
    if args.batch:
        BATCH_SIZE = args.batch
    if args.tta:
        TTA_AUGMENTS = args.tta
    
    if args.kfold > 1:
        dataset_path, class_names = detect_dataset(args.dataset)
        kfold_train(dataset_path, class_names, n_folds=args.kfold)
    else:
        train(
            progressive=args.progressive,
            dataset_path=args.dataset,
            target_accuracy=args.target_accuracy,
            enforce_target=args.enforce_target,
        )
