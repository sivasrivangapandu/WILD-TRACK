"""
WildTrackAI - Automated Dataset Quality Filter
===============================================
Uses computer vision heuristics to flag & remove obvious non-footprint images:

  1. GREEN DOMINANCE → animal body in vegetation (not footprint)
  2. HIGH SATURATION → clipart, illustration, diagram
  3. LOW UNIQUE COLORS → icon, logo, simple graphic
  4. MOSTLY WHITE/LIGHT → diagram on white background
  5. TEXT-HEAVY (horizontal edges) → stock photo watermarks, labeled charts
  6. VERY SMALL FILE → thumbnail, broken download
  7. EXTREME COLOR UNIFORMITY → solid color fills (clipart)

Each image gets a "garbage score" 0-100. Images scoring above threshold are moved
to a quarantine folder (not deleted) so you can review what was removed.

Usage:
    python auto_clean.py                      # Run with default threshold
    python auto_clean.py --threshold 50       # More aggressive cleaning
    python auto_clean.py --threshold 70       # More conservative
    python auto_clean.py --dry-run            # Preview without moving files
    python auto_clean.py --restore            # Move quarantined images back
"""

import os
import sys
import shutil
import argparse
from pathlib import Path
from collections import defaultdict

import cv2
import numpy as np
from PIL import Image

# ============================================
# CONFIGURATION
# ============================================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATASET_DIR = os.path.join(BASE_DIR, "dataset_cleaned")
QUARANTINE_DIR = os.path.join(BASE_DIR, "dataset_quarantine")

DEFAULT_THRESHOLD = 55  # Images scoring above this get quarantined
IMAGE_EXTS = ('.jpg', '.jpeg', '.png', '.bmp', '.gif', '.webp')


def load_image(filepath):
    """Load image with OpenCV, return BGR numpy array or None."""
    try:
        img = cv2.imread(filepath)
        if img is None or img.size == 0:
            return None
        return img
    except Exception:
        return None


def score_green_dominance(img):
    """
    Detect images dominated by green (animal body in vegetation).
    Footprints are in mud/sand/snow — mostly brown/gray/white.
    Green dominance → likely an animal body photo.
    Returns 0-100 score (higher = more green = more likely garbage).
    """
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    # Green hue range: 35-85 in OpenCV (0-180 scale)
    lower_green = np.array([35, 40, 40])
    upper_green = np.array([85, 255, 255])
    mask = cv2.inRange(hsv, lower_green, upper_green)
    green_ratio = np.count_nonzero(mask) / mask.size

    # If >35% green → likely body/vegetation photo
    if green_ratio > 0.50:
        return 90
    elif green_ratio > 0.35:
        return 70
    elif green_ratio > 0.25:
        return 40
    elif green_ratio > 0.15:
        return 20
    return 0


def score_high_saturation(img):
    """
    Detect clipart/illustrations with unnaturally high saturation.
    Real footprint photos are low-saturation (earth tones).
    Returns 0-100 score.
    """
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    mean_sat = np.mean(hsv[:, :, 1])

    # Very high average saturation → clipart
    if mean_sat > 150:
        return 85
    elif mean_sat > 120:
        return 60
    elif mean_sat > 100:
        return 30
    return 0


def score_low_unique_colors(img):
    """
    Detect images with very few unique colors (icons, logos, simple graphics).
    Real photos have thousands of unique colors. Clipart has <100.
    Returns 0-100 score.
    """
    # Downsample for speed
    small = cv2.resize(img, (64, 64))
    # Quantize to reduce near-duplicates
    small = (small // 16) * 16
    reshaped = small.reshape(-1, 3)
    unique = len(set(map(tuple, reshaped)))

    if unique < 20:
        return 95  # Almost certainly clipart/icon
    elif unique < 50:
        return 75
    elif unique < 100:
        return 45
    elif unique < 200:
        return 15
    return 0


def score_white_background(img):
    """
    Detect images with mostly white/light background (diagrams, charts on white).
    Returns 0-100 score.
    """
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    white_thresh = 230
    white_ratio = np.count_nonzero(gray > white_thresh) / gray.size

    if white_ratio > 0.60:
        return 90  # Mostly white → diagram
    elif white_ratio > 0.40:
        return 65
    elif white_ratio > 0.25:
        return 30
    return 0


def score_text_heavy(img):
    """
    Detect images that likely contain text overlays or labels.
    Uses edge detection — text creates lots of small horizontal edges.
    Returns 0-100 score.
    """
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    # Detect edges
    edges = cv2.Canny(gray, 50, 150)
    edge_ratio = np.count_nonzero(edges) / edges.size

    # Text-heavy images have moderate-high edge density in a structured pattern
    # Very high edge density → likely text/labels
    if edge_ratio > 0.25:
        return 70
    elif edge_ratio > 0.18:
        return 40
    return 0


def score_small_file(filepath):
    """
    Very small files are likely thumbnails or broken downloads.
    Returns 0-100 score.
    """
    size_kb = os.path.getsize(filepath) / 1024
    if size_kb < 3:
        return 95  # Too tiny to be useful
    elif size_kb < 8:
        return 70
    elif size_kb < 15:
        return 30
    return 0


def score_black_dominant(img):
    """
    Detect images that are mostly black (broken, irrelevant).
    Returns 0-100 score.
    """
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    dark_ratio = np.count_nonzero(gray < 25) / gray.size

    if dark_ratio > 0.60:
        return 85
    elif dark_ratio > 0.40:
        return 50
    return 0


def score_color_uniformity(img):
    """
    Detect images with very little color variation (solid fills, simple graphics).
    Real photos have high standard deviation in pixel values.
    Returns 0-100 score.
    """
    std_dev = np.std(img.astype(float))

    if std_dev < 15:
        return 90  # Almost uniform → clipart or solid fill
    elif std_dev < 25:
        return 60
    elif std_dev < 35:
        return 25
    return 0


def score_bright_colorful(img):
    """
    Detect bright, colorful images that are likely illustrations rather than photos.
    Real footprint photos have muted earth tones.
    Returns 0-100 score.
    """
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    # Check if image has multiple bright, saturated color regions
    bright_sat = (hsv[:, :, 1] > 100) & (hsv[:, :, 2] > 150)
    ratio = np.count_nonzero(bright_sat) / bright_sat.size

    if ratio > 0.50:
        return 75
    elif ratio > 0.35:
        return 45
    elif ratio > 0.20:
        return 15
    return 0


def compute_garbage_score(filepath):
    """
    Compute an overall garbage score for an image.
    Returns (score, reasons) where score is 0-100.
    Higher = more likely garbage.
    """
    img = load_image(filepath)
    if img is None:
        return 100, ["CORRUPTED: cannot load image"]

    reasons = []
    scores = []

    # Weight each signal
    checks = [
        ("green_dominance", score_green_dominance(img), 1.0),
        ("high_saturation", score_high_saturation(img), 0.8),
        ("low_unique_colors", score_low_unique_colors(img), 1.0),
        ("white_background", score_white_background(img), 0.9),
        ("text_heavy", score_text_heavy(img), 0.6),
        ("small_file", score_small_file(filepath), 0.9),
        ("black_dominant", score_black_dominant(img), 0.8),
        ("color_uniformity", score_color_uniformity(img), 0.7),
        ("bright_colorful", score_bright_colorful(img), 0.7),
    ]

    weighted_sum = 0
    total_weight = 0

    for name, raw_score, weight in checks:
        if raw_score > 30:  # Only count significant signals
            reasons.append(f"{name}={raw_score}")
        weighted_sum += raw_score * weight
        total_weight += weight

    overall = weighted_sum / total_weight if total_weight > 0 else 0

    return min(100, overall), reasons


def auto_clean(threshold=DEFAULT_THRESHOLD, dry_run=False):
    """Run automated cleaning on the dataset."""
    print("=" * 60)
    print("WILDTRACKAI - AUTOMATED DATASET QUALITY FILTER")
    print("=" * 60)
    print(f"  Source: {DATASET_DIR}")
    print(f"  Quarantine: {QUARANTINE_DIR}")
    print(f"  Threshold: {threshold} (images scoring above get quarantined)")
    if dry_run:
        print("  ** DRY RUN — no files will be moved **")
    print("=" * 60)

    if not os.path.isdir(DATASET_DIR):
        print(f"ERROR: Dataset not found at {DATASET_DIR}")
        sys.exit(1)

    species_dirs = sorted([
        d for d in os.listdir(DATASET_DIR)
        if os.path.isdir(os.path.join(DATASET_DIR, d))
    ])

    total_checked = 0
    total_quarantined = 0
    summary = {}

    for species in species_dirs:
        sp_src = os.path.join(DATASET_DIR, species)
        sp_quarantine = os.path.join(QUARANTINE_DIR, species)

        images = sorted([
            f for f in os.listdir(sp_src)
            if f.lower().endswith(IMAGE_EXTS)
            and os.path.isfile(os.path.join(sp_src, f))
        ])

        initial_count = len(images)
        quarantined = 0

        print(f"\n{'='*60}")
        print(f"  CHECKING: {species.upper()} ({initial_count} images)")
        print(f"{'='*60}")

        for i, fname in enumerate(images):
            fpath = os.path.join(sp_src, fname)
            score, reasons = compute_garbage_score(fpath)

            if score >= threshold:
                quarantined += 1
                reason_str = ", ".join(reasons[:3]) if reasons else "high_overall"
                print(f"    [{score:5.1f}] QUARANTINE: {fname} ({reason_str})")

                if not dry_run:
                    os.makedirs(sp_quarantine, exist_ok=True)
                    dst = os.path.join(sp_quarantine, fname)
                    shutil.move(fpath, dst)

            # Progress indicator
            if (i + 1) % 50 == 0:
                print(f"    ... checked {i+1}/{initial_count}")

        remaining = initial_count - quarantined
        print(f"\n    {species}: {initial_count} → {remaining} ({quarantined} quarantined)")

        summary[species] = {
            "initial": initial_count,
            "quarantined": quarantined,
            "remaining": remaining,
        }
        total_checked += initial_count
        total_quarantined += quarantined

    # Summary
    print("\n" + "=" * 60)
    print("CLEANING SUMMARY")
    print("=" * 60)
    print(f"  {'Species':<12} {'Before':>8} {'Removed':>8} {'After':>8}")
    print("  " + "-" * 40)

    for sp, st in summary.items():
        print(f"  {sp:<12} {st['initial']:>6} {st['quarantined']:>8} {st['remaining']:>8}")

    print("  " + "-" * 40)
    total_remaining = total_checked - total_quarantined
    pct = (total_quarantined / max(total_checked, 1)) * 100
    print(f"  {'TOTAL':<12} {total_checked:>6} {total_quarantined:>8} {total_remaining:>8}")
    print(f"\n  Removed: {total_quarantined} images ({pct:.1f}%)")

    if not dry_run:
        print(f"\n  Quarantined images moved to: {QUARANTINE_DIR}")
        print("  You can review & restore false positives with: python auto_clean.py --restore")
    else:
        print(f"\n  ** DRY RUN — no files were moved **")
        print(f"  Run without --dry-run to apply changes.")


def restore_quarantine():
    """Move all quarantined images back to dataset."""
    if not os.path.isdir(QUARANTINE_DIR):
        print("No quarantine folder found. Nothing to restore.")
        return

    restored = 0
    for species in os.listdir(QUARANTINE_DIR):
        q_dir = os.path.join(QUARANTINE_DIR, species)
        d_dir = os.path.join(DATASET_DIR, species)

        if not os.path.isdir(q_dir):
            continue

        for fname in os.listdir(q_dir):
            src = os.path.join(q_dir, fname)
            dst = os.path.join(d_dir, fname)
            if os.path.isfile(src):
                os.makedirs(d_dir, exist_ok=True)
                shutil.move(src, dst)
                restored += 1

    # Clean up empty quarantine dirs
    shutil.rmtree(QUARANTINE_DIR, ignore_errors=True)
    print(f"Restored {restored} images back to dataset.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="WildTrackAI Auto-Cleaner")
    parser.add_argument("--threshold", type=int, default=DEFAULT_THRESHOLD,
                        help=f"Garbage score threshold (default: {DEFAULT_THRESHOLD})")
    parser.add_argument("--dry-run", action="store_true",
                        help="Preview without moving files")
    parser.add_argument("--restore", action="store_true",
                        help="Restore all quarantined images")
    args = parser.parse_args()

    if args.restore:
        restore_quarantine()
    else:
        auto_clean(threshold=args.threshold, dry_run=args.dry_run)
