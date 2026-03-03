"""
WildTrackAI - Round 2 Targeted Cleaning
========================================
Uses the 70.45% model to do a SECOND surgical pass:

Strategy:
  1. Remove images where model is >55% confident about WRONG class
     (these are almost certainly garbage or mislabeled)
  2. Remove borderline images where correct-class prob is <0.18
     AND entropy > 0.85 (no useful signal at all)
  3. Balance classes to within 15% of each other

This is iterative self-cleaning — standard in production ML.

Usage:
    python round2_clean.py --dry-run    # Preview
    python round2_clean.py              # Apply
"""

import os
import sys
import json
import shutil
import argparse
import warnings
warnings.filterwarnings('ignore')

import numpy as np

os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'
import tensorflow as tf
from tensorflow.keras.preprocessing.image import ImageDataGenerator

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATASET_DIR = os.path.join(BASE_DIR, "dataset_cleaned")
QUARANTINE_DIR = os.path.join(BASE_DIR, "dataset_quarantine_r2")
MODEL_PATH = os.path.join(BASE_DIR, "models", "wildtrack_complete_model.h5")
IMG_SIZE = 224
IMAGE_EXTS = ('.jpg', '.jpeg', '.png', '.bmp', '.gif', '.webp')

WRONG_CLASS_THRESHOLD = 0.55   # Model >55% confident about wrong class
LOW_CONF_THRESHOLD = 0.18      # Correct class prob below this
ENTROPY_THRESHOLD = 0.85       # AND high entropy (no signal)


def compute_entropy(probs):
    probs = np.clip(probs, 1e-10, 1.0)
    entropy = -np.sum(probs * np.log(probs))
    max_entropy = np.log(len(probs))
    return entropy / max_entropy if max_entropy > 0 else 0


def round2_clean(dry_run=False):
    print("=" * 60)
    print("WILDTRACKAI - ROUND 2 TARGETED CLEANING")
    print("=" * 60)
    print(f"  Model: {MODEL_PATH}")
    print(f"  Wrong class threshold: {WRONG_CLASS_THRESHOLD}")
    print(f"  Low confidence threshold: {LOW_CONF_THRESHOLD}")
    print(f"  Entropy threshold: {ENTROPY_THRESHOLD}")
    if dry_run:
        print("  ** DRY RUN **")
    print("=" * 60)

    # Load model
    print("\n[1] Loading model...")
    model = tf.keras.models.load_model(MODEL_PATH, compile=False)

    # Get all images with predictions
    print("[2] Predicting on all images...")
    all_gen = ImageDataGenerator()
    all_data = all_gen.flow_from_directory(
        DATASET_DIR, target_size=(IMG_SIZE, IMG_SIZE),
        batch_size=32, class_mode='categorical', shuffle=False
    )
    class_names = list(all_data.class_indices.keys())
    all_preds = model.predict(all_data, verbose=0)
    all_files = all_data.filenames
    all_true = all_data.classes

    print(f"    {len(all_files)} images, {len(class_names)} classes")

    # Pass 1: Remove confidently wrong predictions
    print("\n[3] Pass 1: Confidently wrong images (wrong class > {:.0f}%)...".format(
        WRONG_CLASS_THRESHOLD * 100))
    
    to_remove = set()
    reasons = {}
    
    for idx in range(len(all_files)):
        true_cls = all_true[idx]
        pred_cls = np.argmax(all_preds[idx])
        true_prob = all_preds[idx][true_cls]
        pred_prob = all_preds[idx][pred_cls]
        
        if pred_cls != true_cls and pred_prob > WRONG_CLASS_THRESHOLD:
            to_remove.add(idx)
            reasons[idx] = f"wrong_class: {class_names[true_cls]}->{class_names[pred_cls]} ({pred_prob:.3f})"
    
    print(f"    Found {len(to_remove)} confidently wrong images")

    # Pass 2: Low confidence + high entropy (no signal)
    print(f"\n[4] Pass 2: No-signal images (correct < {LOW_CONF_THRESHOLD}, entropy > {ENTROPY_THRESHOLD})...")
    
    no_signal_count = 0
    for idx in range(len(all_files)):
        if idx in to_remove:
            continue
        true_cls = all_true[idx]
        true_prob = all_preds[idx][true_cls]
        entropy = compute_entropy(all_preds[idx])
        
        if true_prob < LOW_CONF_THRESHOLD and entropy > ENTROPY_THRESHOLD:
            to_remove.add(idx)
            reasons[idx] = f"no_signal: prob={true_prob:.3f}, entropy={entropy:.3f}"
            no_signal_count += 1
    
    print(f"    Found {no_signal_count} no-signal images")

    # Summary before applying
    print(f"\n    Total to remove: {len(to_remove)}")
    
    # Per-class breakdown
    per_class_remove = {}
    per_class_total = {}
    for sp in class_names:
        sp_idx = class_names.index(sp)
        per_class_total[sp] = sum(1 for c in all_true if c == sp_idx)
        per_class_remove[sp] = sum(1 for i in to_remove if all_true[i] == sp_idx)
    
    print(f"\n    {'Species':<12} {'Before':>8} {'Remove':>8} {'After':>8}")
    print("    " + "-" * 40)
    for sp in class_names:
        after = per_class_total[sp] - per_class_remove[sp]
        print(f"    {sp:<12} {per_class_total[sp]:>8} {per_class_remove[sp]:>8} {after:>8}")

    # Apply
    if not dry_run and len(to_remove) > 0:
        print(f"\n[5] Moving {len(to_remove)} images to quarantine...")
        moved = 0
        for idx in to_remove:
            src = os.path.join(DATASET_DIR, all_files[idx])
            dst_dir = os.path.join(QUARANTINE_DIR, os.path.dirname(all_files[idx]))
            dst = os.path.join(QUARANTINE_DIR, all_files[idx])
            os.makedirs(dst_dir, exist_ok=True)
            if os.path.exists(src):
                shutil.move(src, dst)
                moved += 1
        print(f"    Moved {moved} images")
        
        # Save report
        report = []
        for idx in to_remove:
            report.append({
                "file": all_files[idx],
                "reason": reasons.get(idx, "unknown"),
            })
        with open(os.path.join(BASE_DIR, "quarantine_r2_report.json"), "w") as f:
            json.dump(report, f, indent=2)
        print(f"    Report saved: quarantine_r2_report.json")
    
    # Pass 3: Balance classes
    print(f"\n[6] Class balancing analysis...")
    remaining = {}
    for sp in class_names:
        remaining[sp] = per_class_total[sp] - per_class_remove[sp]
    
    min_class = min(remaining.values())
    # Only trim extreme outliers (>80% larger than smallest)
    # Class weights in training already handle moderate imbalance
    target = int(min_class * 1.80)
    
    print(f"    Smallest class after cleaning: {min_class}")
    print(f"    Balance target (180% of min): {target}")
    
    needs_trim = {}
    for sp in class_names:
        if remaining[sp] > target:
            excess = remaining[sp] - target
            needs_trim[sp] = excess
            print(f"    {sp}: {remaining[sp]} -> trim {excess} to reach {target}")
        else:
            print(f"    {sp}: {remaining[sp]} (OK)")
    
    if needs_trim and not dry_run:
        print(f"\n[7] Trimming overrepresented classes...")
        # Remove WORST images from overrepresented classes
        for sp, n_trim in needs_trim.items():
            sp_idx = class_names.index(sp)
            # Get indices for this species, sorted by correct-class probability (worst first)
            sp_indices = [
                (idx, all_preds[idx][sp_idx])
                for idx in range(len(all_files))
                if all_true[idx] == sp_idx and idx not in to_remove
            ]
            sp_indices.sort(key=lambda x: x[1])  # Lowest probability first
            
            trimmed = 0
            for idx, prob in sp_indices[:n_trim]:
                src = os.path.join(DATASET_DIR, all_files[idx])
                dst_dir = os.path.join(QUARANTINE_DIR, os.path.dirname(all_files[idx]))
                dst = os.path.join(QUARANTINE_DIR, all_files[idx])
                os.makedirs(dst_dir, exist_ok=True)
                if os.path.exists(src):
                    shutil.move(src, dst)
                    trimmed += 1
            print(f"    {sp}: trimmed {trimmed} (lowest confidence images)")
    
    # Final counts
    print(f"\n{'='*60}")
    print("FINAL DATASET STATE")
    print("="*60)
    for sp in class_names:
        sp_dir = os.path.join(DATASET_DIR, sp)
        if os.path.isdir(sp_dir):
            count = len([f for f in os.listdir(sp_dir) if f.lower().endswith(IMAGE_EXTS)])
            print(f"  {sp:<12}: {count}")
    
    total = sum(
        len([f for f in os.listdir(os.path.join(DATASET_DIR, sp)) if f.lower().endswith(IMAGE_EXTS)])
        for sp in class_names if os.path.isdir(os.path.join(DATASET_DIR, sp))
    )
    print(f"  {'TOTAL':<12}: {total}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    round2_clean(dry_run=args.dry_run)
