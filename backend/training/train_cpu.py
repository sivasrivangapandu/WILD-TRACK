"""
WildTrackAI — CPU-Optimized Training Script
============================================
Uses MobileNetV2 (lightweight) for fast CPU training.
Targets ≥80% validation accuracy with transfer learning.

Usage:
    python train_cpu.py
    python train_cpu.py --dataset ../dataset_strict --epochs 30
    python train_cpu.py --target-accuracy 0.80 --enforce-target
"""

import os
import sys
import json
import argparse
import datetime
import numpy as np

os.environ["TF_CPP_MIN_LOG_LEVEL"] = "2"
os.environ["TF_ENABLE_ONEDNN_OPTS"] = "0"

import gc
import tensorflow as tf
from tensorflow import keras
from tensorflow.keras import layers, callbacks

# Limit TF memory usage
os.environ["OMP_NUM_THREADS"] = "2"

BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODELS_DIR = os.path.join(BACKEND_DIR, "models")
EVAL_DIR = os.path.join(MODELS_DIR, "evaluation")

IMG_SIZE = 160
BATCH_SIZE = 8
DEFAULT_EPOCHS = 60
SEED = 42


def detect_dataset():
    """Auto-detect best available dataset."""
    for name in ["dataset_strict", "dataset_cleaned", "dataset"]:
        path = os.path.join(BACKEND_DIR, name)
        if os.path.isdir(path):
            classes = [d for d in os.listdir(path)
                       if os.path.isdir(os.path.join(path, d))]
            if len(classes) >= 2:
                return path
    return None


def build_model(num_classes):
    """Build MobileNetV2 transfer-learning model."""
    base = keras.applications.MobileNetV2(
        input_shape=(IMG_SIZE, IMG_SIZE, 3),
        include_top=False,
        weights="imagenet",
    )
    base.trainable = False  # Freeze base initially

    inputs = keras.Input(shape=(IMG_SIZE, IMG_SIZE, 3))
    x = keras.applications.mobilenet_v2.preprocess_input(inputs)
    x = base(x, training=False)
    x = layers.GlobalAveragePooling2D()(x)
    x = layers.Dropout(0.3)(x)
    x = layers.Dense(128, activation="relu")(x)
    x = layers.Dropout(0.2)(x)
    outputs = layers.Dense(num_classes, activation="softmax")(x)

    model = keras.Model(inputs, outputs, name="WildTrackAI_MobileNetV2")
    return model, base


def compute_class_weights(labels, class_names):
    """Compute balanced class weights."""
    from sklearn.utils.class_weight import compute_class_weight
    weights = compute_class_weight("balanced", classes=np.arange(len(class_names)),
                                   y=labels)
    cw = {i: w for i, w in enumerate(weights)}
    print("\n[WEIGHTS] Class weights:")
    for i, name in enumerate(class_names):
        print(f"    {name:>12s}: {cw[i]:.3f}")
    return cw


def train(dataset_path=None, epochs=DEFAULT_EPOCHS,
          target_accuracy=0.80, enforce_target=False):
    """Main training function."""

    if dataset_path is None:
        dataset_path = detect_dataset()
    if dataset_path is None or not os.path.isdir(dataset_path):
        raise FileNotFoundError(f"No dataset found at {dataset_path}")

    os.makedirs(MODELS_DIR, exist_ok=True)
    os.makedirs(EVAL_DIR, exist_ok=True)

    # ── Load data ────────────────────────────────────────────────
    print("=" * 70)
    print("  WILDTRACKAI — CPU-Optimized Training (MobileNetV2)")
    print("=" * 70)

    train_ds = keras.utils.image_dataset_from_directory(
        dataset_path,
        validation_split=0.2,
        subset="training",
        seed=SEED,
        image_size=(IMG_SIZE, IMG_SIZE),
        batch_size=BATCH_SIZE,
        label_mode="int",
    )

    val_ds = keras.utils.image_dataset_from_directory(
        dataset_path,
        validation_split=0.2,
        subset="validation",
        seed=SEED,
        image_size=(IMG_SIZE, IMG_SIZE),
        batch_size=BATCH_SIZE,
        label_mode="int",
    )

    class_names = train_ds.class_names
    num_classes = len(class_names)

    # Collect labels for class weights
    train_labels = np.concatenate([y.numpy() for _, y in train_ds])
    total_train = len(train_labels)
    total_val = sum(y.shape[0] for _, y in val_ds)

    print(f"\n  Dataset: {dataset_path}")
    print(f"  Classes: {class_names}")
    print(f"  Train:   {total_train} images")
    print(f"  Val:     {total_val} images")
    print(f"  Image:   {IMG_SIZE}x{IMG_SIZE}")
    print(f"  Batch:   {BATCH_SIZE}")
    print(f"  Epochs:  {epochs}")
    print(f"  Target:  {target_accuracy*100:.0f}%")

    class_weights = compute_class_weights(train_labels, class_names)

    # Performance optimization
    AUTOTUNE = tf.data.AUTOTUNE
    train_ds = train_ds.prefetch(buffer_size=AUTOTUNE)
    val_ds = val_ds.prefetch(buffer_size=AUTOTUNE)

    # ── Data augmentation ────────────────────────────────────────
    augmentation = keras.Sequential([
        layers.RandomFlip("horizontal"),
        layers.RandomRotation(0.15),
        layers.RandomZoom(0.15),
        layers.RandomContrast(0.2),
    ], name="augmentation")

    train_ds = train_ds.map(
        lambda x, y: (augmentation(x, training=True), y),
        num_parallel_calls=AUTOTUNE,
    )

    # ── Phase 1: Feature extraction (frozen base) ────────────────
    print("\n" + "=" * 70)
    print("  PHASE 1: FEATURE EXTRACTION (frozen base)")
    print("=" * 70)

    model, base = build_model(num_classes)
    phase1_epochs = min(10, epochs // 3)

    model.compile(
        optimizer=keras.optimizers.Adam(learning_rate=1e-3),
        loss="sparse_categorical_crossentropy",
        metrics=["accuracy"],
    )

    checkpoint_path = os.path.join(MODELS_DIR, "checkpoint_best.weights.h5")
    cbs = [
        callbacks.ModelCheckpoint(
            checkpoint_path, monitor="val_accuracy",
            save_best_only=True, save_weights_only=True, verbose=1,
        ),
        callbacks.EarlyStopping(
            monitor="val_accuracy", patience=5,
            restore_best_weights=True, verbose=1,
        ),
        callbacks.ReduceLROnPlateau(
            monitor="val_loss", factor=0.5, patience=3, verbose=1,
        ),
    ]

    model.fit(
        train_ds, validation_data=val_ds,
        epochs=phase1_epochs, callbacks=cbs,
        class_weight=class_weights,
    )

    best_p1 = max(model.history.history.get("val_accuracy", [0]))
    print(f"\n  Phase 1 best val_accuracy: {best_p1:.4f}")

    # Free memory before Phase 2
    gc.collect()

    # ── Phase 2: Fine-tuning (unfreeze top layers) ───────────────
    print("\n" + "=" * 70)
    print("  PHASE 2: FINE-TUNING (unfreeze top 50 layers)")
    print("=" * 70)

    base.trainable = True
    # Freeze all but last 50 layers
    for layer in base.layers[:-50]:
        layer.trainable = False

    # Cosine decay: starts at 1e-4, decays smoothly to 1e-6
    phase2_total = epochs - phase1_epochs
    steps_per_epoch = len(train_labels) // BATCH_SIZE + 1
    cosine_lr = keras.optimizers.schedules.CosineDecay(
        initial_learning_rate=1e-4,
        decay_steps=phase2_total * steps_per_epoch,
        alpha=1e-6 / 1e-4,  # min LR ratio
    )

    model.compile(
        optimizer=keras.optimizers.Adam(learning_rate=cosine_lr),
        loss="sparse_categorical_crossentropy",
        metrics=["accuracy"],
    )

    phase2_epochs = epochs

    cbs_p2 = [
        callbacks.ModelCheckpoint(
            checkpoint_path, monitor="val_accuracy",
            save_best_only=True, save_weights_only=True, verbose=1,
        ),
        callbacks.EarlyStopping(
            monitor="val_accuracy", patience=15,
            restore_best_weights=True, verbose=1,
        ),
    ]

    model.fit(
        train_ds, validation_data=val_ds,
        epochs=phase2_epochs, callbacks=cbs_p2,
        class_weight=class_weights,
        initial_epoch=phase1_epochs,
    )

    best_p2 = max(model.history.history.get("val_accuracy", [0]))
    print(f"\n  Phase 2 best val_accuracy: {best_p2:.4f}")

    # ── Load best checkpoint ─────────────────────────────────────
    if os.path.exists(checkpoint_path):
        model.load_weights(checkpoint_path)
        print("  Loaded best checkpoint weights.")

    # ── Evaluate ─────────────────────────────────────────────────
    print("\n" + "=" * 70)
    print("  EVALUATION")
    print("=" * 70)

    val_labels = []
    val_preds = []
    for x_batch, y_batch in val_ds:
        preds = model.predict(x_batch, verbose=0)
        val_preds.extend(np.argmax(preds, axis=1).tolist())
        val_labels.extend(y_batch.numpy().tolist())
    val_labels = np.array(val_labels)
    val_preds = np.array(val_preds)

    from sklearn.metrics import classification_report, accuracy_score
    accuracy = accuracy_score(val_labels, val_preds)
    report_text = classification_report(
        val_labels, val_preds, target_names=class_names, digits=4
    )
    report_dict = classification_report(
        val_labels, val_preds, target_names=class_names,
        digits=4, output_dict=True
    )
    print(f"\n{report_text}")

    # ── Save models ──────────────────────────────────────────────
    print("\n" + "=" * 70)
    print("  SAVING")
    print("=" * 70)

    v4_path = os.path.join(MODELS_DIR, "wildtrack_v4.h5")
    prod_path = os.path.join(MODELS_DIR, "wildtrack_complete_model.h5")
    final_path = os.path.join(MODELS_DIR, "wildtrack_final.h5")

    model.save(v4_path)
    model.save(prod_path)
    model.save(final_path)
    print(f"  Saved: {v4_path}")
    print(f"  Saved: {prod_path}")
    print(f"  Saved: {final_path}")

    # ── Save metadata ────────────────────────────────────────────
    best_acc = max(best_p1, best_p2, accuracy)
    target_met = best_acc >= target_accuracy

    metadata = {
        "version": "v4-cpu",
        "backbone": "MobileNetV2",
        "img_size": IMG_SIZE,
        "image_size": IMG_SIZE,
        "class_names": class_names,
        "classes": class_names,
        "num_classes": num_classes,
        "accuracy": round(float(best_acc), 4),
        "target_accuracy": target_accuracy,
        "target_met": target_met,
        "dataset_path": dataset_path,
        "train_images": int(total_train),
        "val_images": int(total_val),
        "per_class": {
            name: {
                "precision": round(report_dict[name]["precision"], 4),
                "recall": round(report_dict[name]["recall"], 4),
                "f1": round(report_dict[name]["f1-score"], 4),
                "support": int(report_dict[name]["support"]),
            }
            for name in class_names
        },
        "training_date": datetime.datetime.now().isoformat(),
        "model_path": prod_path,
        "phase1_best": round(float(best_p1), 4),
        "phase2_best": round(float(best_p2), 4),
    }

    meta_path = os.path.join(MODELS_DIR, "model_metadata.json")
    with open(meta_path, "w") as f:
        json.dump(metadata, f, indent=2)
    print(f"  Saved: {meta_path}")

    # ── Final summary ────────────────────────────────────────────
    print("\n" + "=" * 70)
    print("  TRAINING COMPLETE!")
    print("=" * 70)
    print(f"  Accuracy:    {best_acc*100:.2f}%")
    print(f"  Target (>=): {target_accuracy*100:.2f}%")
    print(f"  Target met:  {'YES' if target_met else 'NO'}")
    print(f"  Model:       {prod_path}")
    print(f"  Metadata:    {meta_path}")
    print("=" * 70)

    if enforce_target and not target_met:
        raise RuntimeError(
            f"Target accuracy not reached: {best_acc:.4f} < {target_accuracy}"
        )

    return metadata


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="CPU-optimized WildTrackAI training")
    parser.add_argument("--dataset", type=str, default=None,
                        help="Path to dataset directory")
    parser.add_argument("--epochs", type=int, default=DEFAULT_EPOCHS,
                        help=f"Total training epochs (default: {DEFAULT_EPOCHS})")
    parser.add_argument("--target-accuracy", type=float, default=0.80,
                        help="Target validation accuracy (default: 0.80)")
    parser.add_argument("--enforce-target", action="store_true",
                        help="Fail if target accuracy not reached")
    args = parser.parse_args()

    train(
        dataset_path=args.dataset,
        epochs=args.epochs,
        target_accuracy=args.target_accuracy,
        enforce_target=args.enforce_target,
    )
