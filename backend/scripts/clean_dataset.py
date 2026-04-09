"""
WildTrackAI - Phase 2: Dataset Cleaning Pipeline
=================================================
Professional data cleaning with:
  1. Corrupted image removal
  2. Perceptual hash deduplication (detects near-duplicates)
  3. Resize to uniform 300x300
  4. Brightness normalization
  5. Extreme aspect ratio removal
  6. Final statistics report

Usage:
    python clean_dataset.py
    python clean_dataset.py --target-size 380
    python clean_dataset.py --dry-run        # Preview without deleting
"""

import os
import sys
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
DATASET_DIR = os.path.join(BASE_DIR, "dataset")
CLEANED_DIR = os.path.join(BASE_DIR, "dataset_cleaned")

DEFAULT_TARGET_SIZE = 300
MIN_IMAGE_SIZE = 100  # Pixels - reject anything smaller
MAX_ASPECT_RATIO = 3.0  # Reject if width/height or height/width > this
PHASH_THRESHOLD = 8  # Hamming distance threshold for near-duplicates (0=identical, higher=more lenient)


def compute_phash(image_path, hash_size=16):
    """
    Compute perceptual hash of an image.
    More robust than MD5 — detects visually similar images
    even with different resolutions/compression.
    """
    try:
        img = cv2.imread(image_path, cv2.IMREAD_GRAYSCALE)
        if img is None:
            return None
        # Resize to hash_size+1 x hash_size for DCT
        resized = cv2.resize(img, (hash_size + 1, hash_size))
        # Compute difference
        diff = resized[:, 1:] > resized[:, :-1]
        # Convert to hash
        return diff.flatten()
    except Exception:
        return None


def hamming_distance(hash1, hash2):
    """Compute hamming distance between two perceptual hashes."""
    if hash1 is None or hash2 is None:
        return float('inf')
    return np.count_nonzero(hash1 != hash2)


def remove_corrupted(species_dir, dry_run=False):
    """Remove images that cannot be opened or are too small."""
    removed = []
    for fname in os.listdir(species_dir):
        fpath = os.path.join(species_dir, fname)
        if not os.path.isfile(fpath):
            continue
        if not fname.lower().endswith(('.jpg', '.jpeg', '.png', '.bmp', '.gif', '.webp')):
            continue

        try:
            with Image.open(fpath) as img:
                img.verify()
            with Image.open(fpath) as img:
                w, h = img.size
                if w < MIN_IMAGE_SIZE or h < MIN_IMAGE_SIZE:
                    removed.append(fpath)
                    if not dry_run:
                        os.remove(fpath)
        except Exception:
            removed.append(fpath)
            if not dry_run:
                try:
                    os.remove(fpath)
                except Exception:
                    pass

    return removed


def remove_extreme_aspect_ratio(species_dir, dry_run=False):
    """Remove images with extreme width/height ratios (banners, strips)."""
    removed = []
    for fname in os.listdir(species_dir):
        fpath = os.path.join(species_dir, fname)
        if not os.path.isfile(fpath):
            continue
        if not fname.lower().endswith(('.jpg', '.jpeg', '.png', '.bmp', '.gif', '.webp')):
            continue

        try:
            with Image.open(fpath) as img:
                w, h = img.size
                ratio = max(w / h, h / w) if min(w, h) > 0 else float('inf')
                if ratio > MAX_ASPECT_RATIO:
                    removed.append(fpath)
                    if not dry_run:
                        os.remove(fpath)
        except Exception:
            pass

    return removed


def remove_perceptual_duplicates(species_dir, dry_run=False):
    """Remove near-duplicate images using perceptual hashing."""
    image_files = sorted([
        os.path.join(species_dir, f) for f in os.listdir(species_dir)
        if f.lower().endswith(('.jpg', '.jpeg', '.png', '.bmp', '.gif', '.webp'))
        and os.path.isfile(os.path.join(species_dir, f))
    ])

    if len(image_files) < 2:
        return []

    # Compute hashes
    hashes = []
    for fpath in image_files:
        phash = compute_phash(fpath)
        hashes.append((fpath, phash))

    # Find duplicates
    removed = []
    removed_set = set()

    for i in range(len(hashes)):
        if hashes[i][0] in removed_set:
            continue
        for j in range(i + 1, len(hashes)):
            if hashes[j][0] in removed_set:
                continue
            if hashes[i][1] is None or hashes[j][1] is None:
                continue
            dist = hamming_distance(hashes[i][1], hashes[j][1])
            if dist <= PHASH_THRESHOLD:
                # Keep the first, remove the second
                removed.append(hashes[j][0])
                removed_set.add(hashes[j][0])
                if not dry_run:
                    try:
                        os.remove(hashes[j][0])
                    except Exception:
                        pass

    return removed


def normalize_brightness(image_path, output_path):
    """Normalize image brightness using CLAHE (Contrast Limited Adaptive Histogram Equalization)."""
    try:
        img = cv2.imread(image_path)
        if img is None:
            return False

        # Convert to LAB color space
        lab = cv2.cvtColor(img, cv2.COLOR_BGR2LAB)
        l_channel, a, b = cv2.split(lab)

        # Apply CLAHE to L channel
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        cl = clahe.apply(l_channel)

        # Merge and convert back
        merged = cv2.merge((cl, a, b))
        result = cv2.cvtColor(merged, cv2.COLOR_LAB2BGR)

        cv2.imwrite(output_path, result, [cv2.IMWRITE_JPEG_QUALITY, 95])
        return True
    except Exception:
        return False


def resize_image(image_path, output_path, target_size):
    """Resize image to target_size x target_size, preserving aspect ratio with center crop."""
    try:
        img = cv2.imread(image_path)
        if img is None:
            return False

        h, w = img.shape[:2]

        # Determine crop to make square
        if w > h:
            # Landscape: crop width
            offset = (w - h) // 2
            img = img[:, offset:offset + h]
        elif h > w:
            # Portrait: crop height
            offset = (h - w) // 2
            img = img[offset:offset + w, :]

        # Resize
        img = cv2.resize(img, (target_size, target_size), interpolation=cv2.INTER_LANCZOS4)
        cv2.imwrite(output_path, img, [cv2.IMWRITE_JPEG_QUALITY, 95])
        return True
    except Exception:
        return False


def clean_dataset(target_size=DEFAULT_TARGET_SIZE, dry_run=False):
    """Run the complete cleaning pipeline."""
    print("=" * 60)
    print("WILDTRACKAI - PHASE 2: DATASET CLEANING")
    print("=" * 60)
    if dry_run:
        print("  ** DRY RUN MODE - no files will be modified **")
    print(f"  Source: {DATASET_DIR}")
    print(f"  Output: {CLEANED_DIR}")
    print(f"  Target size: {target_size}x{target_size}")
    print("=" * 60)

    species_list = sorted([
        d for d in os.listdir(DATASET_DIR)
        if os.path.isdir(os.path.join(DATASET_DIR, d))
    ])

    if not species_list:
        print("ERROR: No species directories found in dataset folder.")
        sys.exit(1)

    stats = {}

    for species in species_list:
        species_src = os.path.join(DATASET_DIR, species)
        species_dst = os.path.join(CLEANED_DIR, species)

        initial_count = len([f for f in os.listdir(species_src)
                           if f.lower().endswith(('.jpg', '.jpeg', '.png', '.bmp', '.gif', '.webp'))
                           and os.path.isfile(os.path.join(species_src, f))])

        print(f"\n{'='*60}")
        print(f"PROCESSING: {species.upper()} ({initial_count} images)")
        print(f"{'='*60}")

        # Step 1: Remove corrupted
        print(f"  [1/5] Removing corrupted images...")
        corrupted = remove_corrupted(species_src, dry_run)
        print(f"        Removed: {len(corrupted)}")

        # Step 2: Remove extreme aspect ratios
        print(f"  [2/5] Removing extreme aspect ratios (>{MAX_ASPECT_RATIO})...")
        extreme = remove_extreme_aspect_ratio(species_src, dry_run)
        print(f"        Removed: {len(extreme)}")

        # Step 3: Remove perceptual duplicates
        print(f"  [3/5] Removing near-duplicate images (phash)...")
        duplicates = remove_perceptual_duplicates(species_src, dry_run)
        print(f"        Removed: {len(duplicates)}")

        # Step 4 & 5: Resize + Normalize brightness → write to cleaned dir
        if not dry_run:
            os.makedirs(species_dst, exist_ok=True)

        remaining_images = sorted([
            f for f in os.listdir(species_src)
            if f.lower().endswith(('.jpg', '.jpeg', '.png', '.bmp', '.gif', '.webp'))
            and os.path.isfile(os.path.join(species_src, f))
        ])

        print(f"  [4/5] Resizing to {target_size}x{target_size}...")
        print(f"  [5/5] Normalizing brightness...")

        processed = 0
        failed = 0
        for fname in remaining_images:
            src_path = os.path.join(species_src, fname)
            # Convert all to jpg
            out_name = os.path.splitext(fname)[0] + ".jpg"
            dst_path = os.path.join(species_dst, out_name)

            if dry_run:
                processed += 1
                continue

            # Resize first
            if resize_image(src_path, dst_path, target_size):
                # Then normalize brightness in-place
                if normalize_brightness(dst_path, dst_path):
                    processed += 1
                else:
                    processed += 1  # Keep resize-only version
            else:
                failed += 1

        print(f"        Processed: {processed}, Failed: {failed}")

        final_count = processed
        stats[species] = {
            "initial": initial_count,
            "corrupted": len(corrupted),
            "extreme_ratio": len(extreme),
            "duplicates": len(duplicates),
            "final": final_count,
        }

    # Print summary
    print("\n" + "=" * 60)
    print("CLEANING SUMMARY")
    print("=" * 60)
    print(f"{'Species':<12} {'Initial':>8} {'Corrupt':>8} {'Ratio':>8} {'Dupes':>8} {'Final':>8}")
    print("-" * 60)

    total_initial = 0
    total_final = 0
    for species, s in stats.items():
        print(f"  {species:<12} {s['initial']:>6} {s['corrupted']:>8} {s['extreme_ratio']:>8} {s['duplicates']:>8} {s['final']:>8}")
        total_initial += s["initial"]
        total_final += s["final"]

    print("-" * 60)
    print(f"  {'TOTAL':<12} {total_initial:>6} {' ':>8} {' ':>8} {' ':>8} {total_final:>8}")
    removed_pct = ((total_initial - total_final) / max(total_initial, 1)) * 100
    print(f"\n  Removed: {total_initial - total_final} images ({removed_pct:.1f}%)")

    if not dry_run:
        print(f"\n  Cleaned dataset saved to: {CLEANED_DIR}")
        print(f"  Target size: {target_size}x{target_size}")

    print("\nNEXT STEP: python training/train.py")
    print("=" * 60)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="WildTrackAI Dataset Cleaner")
    parser.add_argument("--target-size", type=int, default=DEFAULT_TARGET_SIZE,
                        help=f"Output image size (default: {DEFAULT_TARGET_SIZE})")
    parser.add_argument("--dry-run", action="store_true",
                        help="Preview changes without modifying files")
    args = parser.parse_args()

    clean_dataset(target_size=args.target_size, dry_run=args.dry_run)
