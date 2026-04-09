"""
WildTrackAI - Controlled Footprint Dataset Collection
======================================================
Downloads animal footprint/track images for 5 species with highly targeted search terms.
Creates a review folder with random samples for human inspection.

Strategy:
  - 5 species only: tiger, leopard, elephant, deer, wolf
  - 8-10 queries per species, each emphasizing "footprint", "track", "pugmark"
  - Target 400 per class (expect ~250-300 after cleaning)
  - Multiple crawlers: Bing + Google (fallback)
  - Review folder for manual inspection before training

Usage:
    python collect_dataset.py              # Full download
    python collect_dataset.py --review     # Only create review samples from existing data
    python collect_dataset.py --stats      # Show dataset statistics
"""

import os
import sys
import random
import shutil
import hashlib
from pathlib import Path
from PIL import Image
import argparse
import logging

# Suppress icrawler verbose logging
logging.getLogger("icrawler").setLevel(logging.WARNING)

# ============================================
# CONFIGURATION
# ============================================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATASET_DIR = os.path.join(BASE_DIR, "dataset")
REVIEW_DIR = os.path.join(BASE_DIR, "dataset_review")
IMAGES_PER_CLASS = 400  # Download target (will clean down to ~250-300)
REVIEW_SAMPLES = 50     # Samples per class for manual review
MIN_IMAGE_SIZE = (150, 150)  # Minimum width x height

# ============================================
# 5 SPECIES — Highly targeted footprint queries
# ============================================
# Key insight: queries must say "footprint" / "track" / "pugmark" PROMINENTLY
# to avoid getting body/face photos of the animal.
SPECIES_QUERIES = {
    "tiger": [
        "tiger pugmark",
        "tiger pugmark photo mud",
        "tiger footprint track identification",
        "tiger paw print mud sand",
        "bengal tiger pugmark wildlife survey",
        "tiger track impression soil",
        "tiger pugmark field guide",
        "tiger footprint close up ground",
    ],
    "leopard": [
        "leopard pugmark",
        "leopard pugmark photo mud",
        "leopard footprint track identification",
        "leopard paw print sand soil",
        "leopard pugmark wildlife survey",
        "leopard track impression ground",
        "leopard pugmark field guide",
        "snow leopard footprint track snow",
    ],
    "elephant": [
        "elephant footprint",
        "elephant footprint photo ground",
        "elephant track mud impression",
        "elephant foot print sand soil",
        "elephant footprint size comparison",
        "elephant track wildlife survey",
        "african elephant footprint close up",
        "elephant footprint identification guide",
    ],
    "deer": [
        "deer track",
        "deer hoof print mud photo",
        "deer footprint snow ground",
        "deer track identification guide",
        "white tailed deer track mud",
        "deer hoof mark soil impression",
        "deer footprint close up",
        "deer tracks in mud identification",
    ],
    "wolf": [
        "wolf track",
        "wolf paw print snow photo",
        "wolf footprint mud ground",
        "wolf track identification guide",
        "grey wolf paw print sand",
        "wolf track impression soil",
        "wolf footprint close up ground",
        "wolf tracks in snow identification",
    ],
}

SPECIES_LIST = list(SPECIES_QUERIES.keys())


def count_images(directory):
    """Count image files in a directory."""
    if not os.path.isdir(directory):
        return 0
    return len([f for f in os.listdir(directory)
               if f.lower().endswith(('.jpg', '.jpeg', '.png', '.bmp', '.gif', '.webp'))])


def download_images():
    """Download footprint images for 5 species using Bing + Google crawlers."""
    try:
        from icrawler.builtin import BingImageCrawler
    except ImportError:
        print("ERROR: icrawler not installed. Run: pip install icrawler")
        sys.exit(1)

    # Try Google as backup source
    try:
        from icrawler.builtin import GoogleImageCrawler
        has_google = True
    except ImportError:
        has_google = False

    print("=" * 60)
    print("WILDTRACKAI - FOOTPRINT DATASET COLLECTION")
    print("=" * 60)
    print(f"Species: {', '.join(SPECIES_LIST)} ({len(SPECIES_LIST)} classes)")
    print(f"Target per class: {IMAGES_PER_CLASS}")
    print(f"Min image size: {MIN_IMAGE_SIZE}")
    print(f"Crawlers: Bing" + (" + Google" if has_google else ""))
    print(f"Output: {DATASET_DIR}")
    print("=" * 60)

    for species in SPECIES_LIST:
        species_dir = os.path.join(DATASET_DIR, species)
        os.makedirs(species_dir, exist_ok=True)

        existing = count_images(species_dir)
        if existing >= IMAGES_PER_CLASS:
            print(f"\n[SKIP] {species}: already has {existing} images (target: {IMAGES_PER_CLASS})")
            continue

        print(f"\n{'='*60}")
        print(f"DOWNLOADING: {species.upper()} (have {existing}, need {IMAGES_PER_CLASS})")
        print(f"{'='*60}")

        queries = SPECIES_QUERIES[species]
        needed = IMAGES_PER_CLASS - existing
        # Request extra per query to account for duplicates and failures
        images_per_query = max(10, needed // len(queries) + 15)

        # --- Bing Image Crawler ---
        for i, query in enumerate(queries):
            current = count_images(species_dir)
            if current >= IMAGES_PER_CLASS:
                print(f"  [Bing] Reached target, skipping remaining queries")
                break

            print(f"  [Bing {i+1}/{len(queries)}] '{query}' (requesting {images_per_query})...")
            try:
                crawler = BingImageCrawler(
                    storage={"root_dir": species_dir},
                    downloader_threads=4,
                    parser_threads=2,
                )
                crawler.crawl(
                    keyword=query,
                    max_num=images_per_query,
                    min_size=MIN_IMAGE_SIZE,
                    file_idx_offset="auto",
                )
            except Exception as e:
                print(f"    WARNING: {e}")
                continue

        # --- Google Image Crawler (backup) ---
        current = count_images(species_dir)
        if has_google and current < IMAGES_PER_CLASS * 0.7:
            print(f"\n  [Google] Bing only got {current} — trying Google backup...")
            # Use first 3 queries for Google
            for i, query in enumerate(queries[:3]):
                current = count_images(species_dir)
                if current >= IMAGES_PER_CLASS:
                    break
                print(f"  [Google {i+1}/3] '{query}' (requesting {images_per_query})...")
                try:
                    crawler = GoogleImageCrawler(
                        storage={"root_dir": species_dir},
                        downloader_threads=4,
                        parser_threads=2,
                    )
                    crawler.crawl(
                        keyword=query,
                        max_num=images_per_query,
                        min_size=MIN_IMAGE_SIZE,
                        file_idx_offset="auto",
                    )
                except Exception as e:
                    print(f"    WARNING: {e}")
                    continue

        final_count = count_images(species_dir)
        status = "OK" if final_count >= IMAGES_PER_CLASS * 0.5 else "LOW"
        print(f"\n  >> {species}: {final_count} images [{status}]")

    print("\n" + "=" * 60)
    print("DOWNLOAD COMPLETE")
    print("=" * 60)
    show_stats()


def validate_images():
    """Remove corrupted and undersized images."""
    print("\n" + "=" * 60)
    print("VALIDATING IMAGES (removing corrupted/undersized)")
    print("=" * 60)

    total_removed = 0
    for species in SPECIES_LIST:
        species_dir = os.path.join(DATASET_DIR, species)
        if not os.path.isdir(species_dir):
            continue

        removed = 0
        for fname in os.listdir(species_dir):
            fpath = os.path.join(species_dir, fname)
            if not os.path.isfile(fpath):
                continue
            try:
                with Image.open(fpath) as img:
                    img.verify()
                # Re-open after verify (verify can close file)
                with Image.open(fpath) as img:
                    w, h = img.size
                    if w < MIN_IMAGE_SIZE[0] or h < MIN_IMAGE_SIZE[1]:
                        os.remove(fpath)
                        removed += 1
                        continue
            except Exception:
                try:
                    os.remove(fpath)
                except Exception:
                    pass
                removed += 1

        if removed > 0:
            print(f"  {species}: removed {removed} invalid images")
        total_removed += removed

    print(f"\nTotal removed: {total_removed}")


def create_review_folder():
    """Copy random samples to review folder for human inspection."""
    print("\n" + "=" * 60)
    print(f"CREATING REVIEW FOLDER ({REVIEW_SAMPLES} per class)")
    print("=" * 60)

    if os.path.exists(REVIEW_DIR):
        shutil.rmtree(REVIEW_DIR)

    os.makedirs(REVIEW_DIR, exist_ok=True)

    for species in SPECIES_LIST:
        species_dir = os.path.join(DATASET_DIR, species)
        review_species_dir = os.path.join(REVIEW_DIR, species)
        os.makedirs(review_species_dir, exist_ok=True)

        if not os.path.isdir(species_dir):
            print(f"  {species}: NO DATA")
            continue

        all_images = [f for f in os.listdir(species_dir)
                     if f.lower().endswith(('.jpg', '.jpeg', '.png', '.bmp', '.gif', '.webp'))]

        sample_count = min(REVIEW_SAMPLES, len(all_images))
        samples = random.sample(all_images, sample_count)

        for fname in samples:
            src = os.path.join(species_dir, fname)
            dst = os.path.join(review_species_dir, fname)
            shutil.copy2(src, dst)

        print(f"  {species}: {sample_count} samples copied to review folder")

    print(f"\nReview folder: {REVIEW_DIR}")
    print("Open this folder and manually inspect the images.")
    print("If >40% per class are NOT footprints, the scraping source is unreliable.")


def show_stats():
    """Display dataset statistics."""
    print("\n" + "=" * 60)
    print("DATASET STATISTICS")
    print("=" * 60)
    print(f"{'Species':<12} {'Images':>8}  {'Status'}")
    print("-" * 40)

    total = 0
    for species in SPECIES_LIST:
        species_dir = os.path.join(DATASET_DIR, species)
        count = count_images(species_dir)

        if count >= IMAGES_PER_CLASS:
            status = "OK"
        elif count >= IMAGES_PER_CLASS * 0.5:
            status = "USABLE"
        elif count >= 100:
            status = "LOW"
        elif count > 0:
            status = "VERY LOW"
        else:
            status = "MISSING"

        print(f"  {species:<12} {count:>6}    {status}")
        total += count

    print("-" * 40)
    print(f"  {'TOTAL':<12} {total:>6}")
    print(f"  Classes: {len(SPECIES_LIST)}")
    print(f"  Target: {IMAGES_PER_CLASS} per class")


def compute_file_hash(filepath):
    """Compute MD5 hash of file for duplicate detection."""
    hasher = hashlib.md5()
    with open(filepath, 'rb') as f:
        for chunk in iter(lambda: f.read(8192), b''):
            hasher.update(chunk)
    return hasher.hexdigest()


def remove_exact_duplicates():
    """Remove exact file duplicates within each class."""
    print("\n" + "=" * 60)
    print("REMOVING EXACT DUPLICATES")
    print("=" * 60)

    total_removed = 0
    for species in SPECIES_LIST:
        species_dir = os.path.join(DATASET_DIR, species)
        if not os.path.isdir(species_dir):
            continue

        seen_hashes = {}
        removed = 0
        for fname in sorted(os.listdir(species_dir)):
            fpath = os.path.join(species_dir, fname)
            if not os.path.isfile(fpath):
                continue
            try:
                fhash = compute_file_hash(fpath)
                if fhash in seen_hashes:
                    os.remove(fpath)
                    removed += 1
                else:
                    seen_hashes[fhash] = fpath
            except Exception:
                pass

        if removed > 0:
            print(f"  {species}: removed {removed} duplicates")
        total_removed += removed

    print(f"\nTotal duplicates removed: {total_removed}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="WildTrackAI Dataset Collector")
    parser.add_argument("--review", action="store_true", help="Only create review samples")
    parser.add_argument("--stats", action="store_true", help="Show dataset statistics")
    parser.add_argument("--validate", action="store_true", help="Only validate and clean images")
    args = parser.parse_args()

    if args.stats:
        show_stats()
    elif args.review:
        create_review_folder()
    elif args.validate:
        validate_images()
        remove_exact_duplicates()
        show_stats()
    else:
        # Full pipeline
        download_images()
        validate_images()
        remove_exact_duplicates()
        create_review_folder()
        print("\n" + "=" * 60)
        print("PHASE 1 COMPLETE")
        print("=" * 60)
        print("\nNEXT STEPS:")
        print(f"  1. Open: {REVIEW_DIR}")
        print("  2. Check each species folder")
        print("  3. If >40% images are NOT footprints → quality is poor")
        print("  4. Run: python clean_dataset.py")
        print("=" * 60)
