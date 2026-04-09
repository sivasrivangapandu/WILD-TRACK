"""
WildTrackAI - Model-Based Dataset Cleaning
===========================================
Uses the trained model to identify garbage images in the training set.

Strategy:
  1. Load the 57% accuracy model
  2. Predict on every image in dataset_cleaned/
  3. Flag images where:
     a) Model confidence for THE LABELED class is very low (<threshold)
     b) Model predicts a DIFFERENT class with high confidence (mislabeled)
     c) Model is near-uniform across all classes (image has no useful signal)
  4. Move flagged images to quarantine folder

This is a well-known technique: models that are "partially right" are excellent
at identifying which data points are hurting them.

Usage:
    python model_clean.py                     # Run with default settings
    python model_clean.py --threshold 0.15    # More aggressive
    python model_clean.py --threshold 0.25    # More conservative
    python model_clean.py --dry-run           # Preview without moving
"""

import os
import sys
import json
import shutil
import argparse
import warnings
warnings.filterwarnings('ignore')

import numpy as np
from PIL import Image

os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'
import tensorflow as tf

# ============================================
# CONFIGURATION
# ============================================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATASET_DIR = os.path.join(BASE_DIR, "dataset_cleaned")
QUARANTINE_DIR = os.path.join(BASE_DIR, "dataset_quarantine")
MODEL_PATH = os.path.join(BASE_DIR, "models", "wildtrack_complete_model.h5")
IMG_SIZE = 224
IMAGE_EXTS = ('.jpg', '.jpeg', '.png', '.bmp', '.gif', '.webp')

# Thresholds
DEFAULT_CORRECT_CLASS_THRESHOLD = 0.15  # If model gives <15% prob to labeled class → suspicious
DEFAULT_ENTROPY_THRESHOLD = 0.90        # If prediction entropy is very high → no signal
DEFAULT_WRONG_CLASS_THRESHOLD = 0.70    # If model gives >70% to a DIFFERENT class → mislabeled


def load_and_preprocess(filepath):
    """Load and preprocess an image for EfficientNet (no rescaling!)."""
    try:
        img = tf.keras.utils.load_img(filepath, target_size=(IMG_SIZE, IMG_SIZE))
        arr = tf.keras.utils.img_to_array(img)
        return np.expand_dims(arr, axis=0)  # No rescale — EfficientNet handles it
    except Exception:
        return None


def compute_entropy(probs):
    """Compute normalized prediction entropy (0=certain, 1=uniform)."""
    probs = np.clip(probs, 1e-10, 1.0)
    entropy = -np.sum(probs * np.log(probs))
    max_entropy = np.log(len(probs))  # Maximum possible entropy (uniform)
    return entropy / max_entropy if max_entropy > 0 else 0


def model_clean(correct_threshold=DEFAULT_CORRECT_CLASS_THRESHOLD,
                entropy_threshold=DEFAULT_ENTROPY_THRESHOLD,
                wrong_threshold=DEFAULT_WRONG_CLASS_THRESHOLD,
                dry_run=False):
    """Use trained model to identify and quarantine garbage images."""

    print("=" * 60)
    print("WILDTRACKAI - MODEL-BASED DATASET CLEANING")
    print("=" * 60)
    print(f"  Model: {MODEL_PATH}")
    print(f"  Dataset: {DATASET_DIR}")
    print(f"  Quarantine: {QUARANTINE_DIR}")
    print(f"  Correct class threshold: {correct_threshold:.2f}")
    print(f"  Entropy threshold: {entropy_threshold:.2f}")
    print(f"  Wrong class threshold: {wrong_threshold:.2f}")
    if dry_run:
        print("  ** DRY RUN — no files will be moved **")
    print("=" * 60)

    # Load model
    print("\n[1] Loading model...")
    if not os.path.exists(MODEL_PATH):
        print(f"ERROR: Model not found at {MODEL_PATH}")
        sys.exit(1)

    model = tf.keras.models.load_model(MODEL_PATH, compile=False)
    print(f"    Model loaded: {model.name}")

    # Detect classes
    class_names = sorted([
        d for d in os.listdir(DATASET_DIR)
        if os.path.isdir(os.path.join(DATASET_DIR, d))
    ])
    print(f"    Classes: {class_names}")
    n_classes = len(class_names)

    # Process each class
    print("\n[2] Scanning all images...")
    total_checked = 0
    total_quarantined = 0
    summary = {}
    all_flagged = []

    for cls_idx, species in enumerate(class_names):
        sp_dir = os.path.join(DATASET_DIR, species)
        sp_quarantine = os.path.join(QUARANTINE_DIR, species)

        images = sorted([
            f for f in os.listdir(sp_dir)
            if f.lower().endswith(IMAGE_EXTS)
            and os.path.isfile(os.path.join(sp_dir, f))
        ])

        n_images = len(images)
        quarantined = 0
        reasons_count = {"low_confidence": 0, "mislabeled": 0, "no_signal": 0}

        print(f"\n  {'='*50}")
        print(f"  {species.upper()} ({n_images} images, expected class index: {cls_idx})")
        print(f"  {'='*50}")

        for i, fname in enumerate(images):
            fpath = os.path.join(sp_dir, fname)
            batch = load_and_preprocess(fpath)

            if batch is None:
                # Can't load → quarantine
                quarantined += 1
                reasons_count["low_confidence"] += 1
                print(f"    [BROKEN] {fname}")
                if not dry_run:
                    os.makedirs(sp_quarantine, exist_ok=True)
                    shutil.move(fpath, os.path.join(sp_quarantine, fname))
                continue

            # Predict
            preds = model.predict(batch, verbose=0)[0]
            correct_prob = preds[cls_idx]
            predicted_class = np.argmax(preds)
            predicted_prob = preds[predicted_class]
            entropy = compute_entropy(preds)

            # Decision logic
            flag = False
            reason = ""

            # Check 1: Very low probability for the labeled class
            if correct_prob < correct_threshold:
                flag = True
                reason = f"low_conf={correct_prob:.3f}"
                reasons_count["low_confidence"] += 1

            # Check 2: High confidence for a DIFFERENT class (mislabeled/wrong)
            elif predicted_class != cls_idx and predicted_prob > wrong_threshold:
                flag = True
                reason = f"mislabeled→{class_names[predicted_class]}({predicted_prob:.3f})"
                reasons_count["mislabeled"] += 1

            # Check 3: Near-uniform predictions (no useful signal)
            elif entropy > entropy_threshold:
                flag = True
                reason = f"no_signal(entropy={entropy:.3f})"
                reasons_count["no_signal"] += 1

            if flag:
                quarantined += 1
                all_flagged.append({
                    "species": species,
                    "file": fname,
                    "reason": reason,
                    "correct_prob": float(correct_prob),
                    "predicted": class_names[predicted_class],
                    "predicted_prob": float(predicted_prob),
                    "entropy": float(entropy),
                })
                print(f"    [{correct_prob:.3f}] QUARANTINE: {fname} ({reason})")

                if not dry_run:
                    os.makedirs(sp_quarantine, exist_ok=True)
                    shutil.move(fpath, os.path.join(sp_quarantine, fname))

            # Progress
            if (i + 1) % 100 == 0:
                print(f"    ... checked {i+1}/{n_images}")

        remaining = n_images - quarantined
        print(f"\n    {species}: {n_images} → {remaining} (removed: {quarantined})")
        print(f"      low_confidence={reasons_count['low_confidence']}, "
              f"mislabeled={reasons_count['mislabeled']}, "
              f"no_signal={reasons_count['no_signal']}")

        summary[species] = {
            "initial": n_images,
            "quarantined": quarantined,
            "remaining": remaining,
            "reasons": dict(reasons_count),
        }
        total_checked += n_images
        total_quarantined += quarantined

    # Summary
    print("\n" + "=" * 60)
    print("MODEL-BASED CLEANING SUMMARY")
    print("=" * 60)
    print(f"  {'Species':<12} {'Before':>8} {'LowConf':>8} {'Mislbl':>8} {'NoSig':>8} {'After':>8}")
    print("  " + "-" * 52)

    for sp, st in summary.items():
        r = st["reasons"]
        print(f"  {sp:<12} {st['initial']:>6} "
              f"{r['low_confidence']:>8} {r['mislabeled']:>8} {r['no_signal']:>8} "
              f"{st['remaining']:>8}")

    print("  " + "-" * 52)
    total_remaining = total_checked - total_quarantined
    pct = (total_quarantined / max(total_checked, 1)) * 100
    print(f"  {'TOTAL':<12} {total_checked:>6} {'':>8} {'':>8} {'':>8} {total_remaining:>8}")
    print(f"\n  Removed: {total_quarantined} images ({pct:.1f}%)")

    if not dry_run:
        # Save flagged list for review
        flagged_path = os.path.join(BASE_DIR, "quarantine_report.json")
        with open(flagged_path, "w") as f:
            json.dump(all_flagged, f, indent=2)
        print(f"\n  Quarantine report: {flagged_path}")
        print(f"  Quarantined images: {QUARANTINE_DIR}")
        print(f"\n  To restore: python auto_clean.py --restore")
    else:
        print(f"\n  ** DRY RUN — no files moved **")
        print(f"  Run without --dry-run to apply.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="WildTrackAI Model-Based Cleaner")
    parser.add_argument("--threshold", type=float, default=DEFAULT_CORRECT_CLASS_THRESHOLD,
                        help=f"Min probability for correct class (default: {DEFAULT_CORRECT_CLASS_THRESHOLD})")
    parser.add_argument("--entropy", type=float, default=DEFAULT_ENTROPY_THRESHOLD,
                        help=f"Max normalized entropy (default: {DEFAULT_ENTROPY_THRESHOLD})")
    parser.add_argument("--wrong", type=float, default=DEFAULT_WRONG_CLASS_THRESHOLD,
                        help=f"Confidence threshold for wrong class (default: {DEFAULT_WRONG_CLASS_THRESHOLD})")
    parser.add_argument("--dry-run", action="store_true",
                        help="Preview without moving files")
    args = parser.parse_args()

    model_clean(
        correct_threshold=args.threshold,
        entropy_threshold=args.entropy,
        wrong_threshold=args.wrong,
        dry_run=args.dry_run,
    )
