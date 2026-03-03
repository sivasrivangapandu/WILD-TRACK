"""
WildTrackAI — Stage 1: Load Clean Dataset for Pipeline Validation
==================================================================
Downloads TF Flowers dataset (5 classes, ~3670 images, clean labels)
from Google's servers — fast, reliable, proven.

Validates: architecture, training, evaluation, confusion matrix, GradCAM.

Usage:
    python load_clean_dataset.py
    python load_clean_dataset.py --stats
"""

import os
import sys
import shutil
import pathlib
import argparse

os.environ['TF_CPP_MIN_LOG_LEVEL'] = '2'

import tensorflow as tf


# ============================================
# CONFIGURATION
# ============================================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_DIR = os.path.join(BASE_DIR, "dataset")

FLOWERS_URL = "https://storage.googleapis.com/download.tensorflow.org/example_images/flower_photos.tgz"


def download_and_prepare():
    """Download TF Flowers dataset and organize into folder structure."""

    print("=" * 60)
    print("STAGE 1: Clean Dataset Loader")
    print("=" * 60)
    print(f"Dataset: TensorFlow Flowers (5 classes)")
    print(f"Source:  Google Cloud Storage (fast)")
    print(f"Output:  {OUTPUT_DIR}")
    print()

    # Download
    print("[1/3] Downloading dataset...")
    archive_path = tf.keras.utils.get_file(
        origin=FLOWERS_URL,
        fname='flower_photos.tgz',
        extract=True
    )

    # The extracted folder — Keras extracts into <name>_extracted/<name>/
    base = pathlib.Path(archive_path).parent
    # Try multiple possible extraction paths
    candidates = [
        base / 'flower_photos_extracted' / 'flower_photos',
        base / 'flower_photos',
        base,
    ]
    data_dir = None
    for c in candidates:
        if c.exists() and any(c.iterdir()):
            # Check if it has subdirectories with images
            subdirs = [d for d in c.iterdir() if d.is_dir()]
            if subdirs:
                data_dir = c
                break

    print(f"  Downloaded to: {data_dir}")

    if not data_dir.exists():
        print("ERROR: Download failed or extraction failed!")
        sys.exit(1)

    # Count what we got
    image_count = len(list(data_dir.glob('*/*.jpg')))
    print(f"  Total images found: {image_count}")

    # Copy to our dataset folder
    print(f"\n[2/3] Organizing into {OUTPUT_DIR}...")
    if os.path.exists(OUTPUT_DIR):
        shutil.rmtree(OUTPUT_DIR)
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    classes = sorted([d.name for d in data_dir.iterdir()
                      if d.is_dir() and not d.name.startswith('.')])

    total_copied = 0
    for cls in classes:
        src_dir = data_dir / cls
        dst_dir = pathlib.Path(OUTPUT_DIR) / cls
        dst_dir.mkdir(exist_ok=True)

        images = list(src_dir.glob('*.jpg'))
        for img in images:
            shutil.copy2(str(img), str(dst_dir / img.name))
            total_copied += 1

    # Also remove the LICENSE file if it ended up as a class
    license_dir = pathlib.Path(OUTPUT_DIR) / 'LICENSE.txt'
    if license_dir.exists():
        os.remove(str(license_dir))

    # Summary
    print(f"\n[3/3] Complete!")
    print("=" * 60)
    print()

    final_classes = sorted([d for d in os.listdir(OUTPUT_DIR)
                            if os.path.isdir(os.path.join(OUTPUT_DIR, d))])

    total = 0
    for cls in final_classes:
        count = len(os.listdir(os.path.join(OUTPUT_DIR, cls)))
        print(f"  {cls}: {count} images")
        total += count

    print(f"\n  Total: {total} images across {len(final_classes)} classes")
    print(f"\n  Output: {OUTPUT_DIR}")
    print(f"\n  Next: python training/train.py")

    return final_classes


def show_stats():
    """Show stats of existing dataset."""
    if not os.path.isdir(OUTPUT_DIR):
        print("No dataset found. Run without --stats first.")
        return

    print(f"Dataset: {OUTPUT_DIR}\n")
    total = 0
    for cls in sorted(os.listdir(OUTPUT_DIR)):
        cls_path = os.path.join(OUTPUT_DIR, cls)
        if os.path.isdir(cls_path):
            count = len([f for f in os.listdir(cls_path)
                         if f.lower().endswith(('.jpg', '.png', '.jpeg'))])
            print(f"  {cls}: {count}")
            total += count
    print(f"\n  Total: {total}")


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Load clean dataset for pipeline validation')
    parser.add_argument('--stats', action='store_true', help='Show dataset statistics')
    args = parser.parse_args()

    if args.stats:
        show_stats()
    else:
        download_and_prepare()
