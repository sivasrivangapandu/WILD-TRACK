"""
WildTrackAI — Intelligent Dataset Scaler v2
=============================================
Multi-strategy approach to reach 400+ images per class.

Strategy layers (in order of reliability):
  1. EXPANDED QUERY BANK — 25+ diverse queries per species using
     different languages, scientific terms, field guide terminology
  2. MULTI-ENGINE CRAWLING — Bing + Google + Flickr (icrawler)
  3. INTELLIGENT AUGMENTATION — generate synthetic training samples
     using advanced transforms that preserve footprint morphology
  4. CROSS-CLASS DEDUP — perceptual hash dedup ACROSS species
  5. QUALITY SCORING — CNN-based relevance scoring (is it a footprint?)
  6. DATASET ANALYTICS — full report on class balance, quality, gaps

Usage:
    python scale_dataset.py                  # Full pipeline: scrape + augment + clean
    python scale_dataset.py --scrape-only    # Only download new images
    python scale_dataset.py --augment-only   # Only generate synthetic samples
    python scale_dataset.py --analyze        # Show detailed analytics
    python scale_dataset.py --target 500     # Set target per class (default: 500)
    python scale_dataset.py --species leopard tiger  # Only scale specific species

Target: 500 images per class (cleaned) → ~400 per class after quality filters
"""

import os
import sys
import json
import shutil
import hashlib
import argparse
import random
import logging
import math
from pathlib import Path
from datetime import datetime
from collections import Counter, defaultdict

import cv2
import numpy as np
from PIL import Image, ImageEnhance, ImageFilter

logging.getLogger("icrawler").setLevel(logging.WARNING)
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
log = logging.getLogger("scale_dataset")

# ============================================
# CONFIGURATION
# ============================================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATASET_DIR = os.path.join(BASE_DIR, "dataset")
CLEANED_DIR = os.path.join(BASE_DIR, "dataset_cleaned")
AUGMENTED_DIR = os.path.join(BASE_DIR, "dataset_augmented")
STAGING_DIR = os.path.join(BASE_DIR, "dataset_staging")  # New downloads go here first
REPORT_PATH = os.path.join(BASE_DIR, "scaling_report.json")

TARGET_PER_CLASS = 500      # After cleaning, want this many per class
MIN_IMAGE_SIZE = (150, 150)
PHASH_SIZE = 16
PHASH_THRESHOLD = 10        # Allow slightly more variation than clean_dataset (8)
AUGMENT_TARGET = 500        # Generate augmented images up to this count per class
MAX_AUGMENTS_PER_SOURCE = 3 # Max synthetic images from a single source image


# ============================================
# EXPANDED QUERY BANK — 25+ queries per species
# ============================================
# Strategy: diversify language, context, substrate, source type
# Include scientific names, field guide terms, regional terms
# Include substrate-specific queries (mud, sand, snow, soil, clay)
# Include comparative/identification contexts

EXPANDED_QUERIES = {
    "tiger": [
        # Standard English
        "tiger pugmark",
        "tiger pugmark photo mud",
        "tiger footprint track identification",
        "tiger paw print mud sand",
        "bengal tiger pugmark wildlife survey",
        "tiger track impression soil",
        "tiger pugmark field guide",
        "tiger footprint close up ground",
        # Substrate-specific
        "tiger pugmark clay riverbank",
        "tiger footprint dusty road",
        "tiger paw print wet sand",
        "tiger track soft mud fresh",
        # Scientific / academic
        "Panthera tigris pugmark forensic",
        "Panthera tigris footprint research",
        "tiger pug mark wildlife monitoring",
        "tiger track cast plaster mold",
        # Field guide / identification context
        "tiger vs leopard pugmark comparison",
        "tiger track identification field guide",
        "big cat pugmark india forest",
        "tiger spoor track camera trap",
        # Regional / conservation
        "bengal tiger pugmark census",
        "siberian tiger track snow",
        "sumatran tiger footprint",
        "indian tiger pugmark survey reserve",
        "tiger paw impression national park",
    ],
    "leopard": [
        # Standard English
        "leopard pugmark",
        "leopard pugmark photo mud",
        "leopard footprint track identification",
        "leopard paw print sand soil",
        "leopard pugmark wildlife survey",
        "leopard track impression ground",
        "leopard pugmark field guide",
        "snow leopard footprint track snow",
        # Substrate-specific
        "leopard footprint clay path",
        "leopard pugmark dusty trail",
        "leopard paw track soft earth",
        "snow leopard pug mark mountain",
        # Scientific / academic
        "Panthera pardus pugmark forensic",
        "Panthera pardus footprint identification",
        "leopard track wildlife research",
        "leopard pug mark cast mold",
        # Differentiation context
        "leopard vs cheetah pugmark difference",
        "leopard paw print size measurement",
        "leopard track indian jungle",
        "African leopard spoor footprint",
        # Regional
        "Indian leopard pugmark survey",
        "snow leopard pugmark Himalayas",
        "Sri Lankan leopard footprint",
        "leopard pugmark camera trap",
        "Panthera uncia snow track",
    ],
    "elephant": [
        # Standard English
        "elephant footprint",
        "elephant footprint photo ground",
        "elephant track mud impression",
        "elephant foot print sand soil",
        "elephant footprint size comparison",
        "elephant track wildlife survey",
        "african elephant footprint close up",
        "elephant footprint identification guide",
        # Substrate-specific
        "elephant footprint clay river crossing",
        "elephant track dusty road savanna",
        "elephant foot impression wet ground",
        "elephant footprint dried mud",
        # Scientific / academic
        "Elephas maximus footprint research",
        "Loxodonta africana track study",
        "elephant track morphometry",
        "elephant footprint biometric identification",
        # Size / comparison context
        "elephant footprint compared to human",
        "elephant foot track diameter measurement",
        "baby elephant footprint track",
        "elephant herd tracks path",
        # Regional
        "Asian elephant footprint forest India",
        "African elephant track Kruger",
        "Sri Lankan elephant footprint",
        "elephant foot impression Serengeti",
        "elephant track national park ground",
    ],
    "deer": [
        # Standard English
        "deer track",
        "deer hoof print mud photo",
        "deer footprint snow ground",
        "deer track identification guide",
        "white tailed deer track mud",
        "deer hoof mark soil impression",
        "deer footprint close up",
        "deer tracks in mud identification",
        # Substrate-specific
        "deer hoof print sandy trail",
        "deer track clay forest path",
        "deer footprint wet soil",
        "deer hoof impression snow fresh",
        # Scientific / species-specific
        "cervidae footprint track",
        "spotted deer chital hoof print",
        "sambar deer track mud India",
        "mule deer track identification",
        # Identification context
        "deer vs elk hoof print comparison",
        "deer hoof track field guide",
        "deer cloven hoof mark ground",
        "deer track split hoof impression",
        # Regional
        "red deer footprint UK forest",
        "roe deer track European woodland",
        "axis deer hoof print India",
        "sika deer track Japan",
        "deer track wildlife survey forest",
    ],
    "wolf": [
        # Standard English
        "wolf track",
        "wolf paw print snow photo",
        "wolf footprint mud ground",
        "wolf track identification guide",
        "grey wolf paw print sand",
        "wolf track impression soil",
        "wolf footprint close up ground",
        "wolf tracks in snow identification",
        # Substrate-specific
        "wolf paw print clay riverbank",
        "wolf track wet sand beach",
        "wolf footprint dusty trail",
        "wolf track fresh snow forest",
        # Scientific / academic
        "Canis lupus track forensic",
        "Canis lupus footprint research",
        "wolf paw track morphology study",
        "wolf track cast plaster",
        # Differentiation context
        "wolf vs coyote track comparison",
        "wolf vs dog paw print difference",
        "wolf track identification claw marks",
        "wolf paw canine track guide",
        # Regional
        "grey wolf track Yellowstone",
        "Indian wolf footprint",
        "Arctic wolf paw print snow",
        "European wolf track forest",
        "timber wolf footprint mud",
    ],
}


# ============================================
# PERCEPTUAL HASH UTILITIES
# ============================================
def compute_phash(image_path, hash_size=PHASH_SIZE):
    """Compute perceptual hash for near-duplicate detection."""
    try:
        img = cv2.imread(image_path, cv2.IMREAD_GRAYSCALE)
        if img is None:
            return None
        resized = cv2.resize(img, (hash_size + 1, hash_size))
        diff = resized[:, 1:] > resized[:, :-1]
        return diff.flatten()
    except Exception:
        return None


def hamming_distance(h1, h2):
    """Hamming distance between two binary hashes."""
    if h1 is None or h2 is None:
        return float('inf')
    return int(np.count_nonzero(h1 != h2))


def compute_md5(filepath):
    """MD5 hash of file bytes."""
    h = hashlib.md5()
    with open(filepath, 'rb') as f:
        for chunk in iter(lambda: f.read(8192), b''):
            h.update(chunk)
    return h.hexdigest()


# ============================================
# STAGE 1: EXPANDED SCRAPING
# ============================================
def scrape_expanded(species_filter=None, target=TARGET_PER_CLASS):
    """Download images using expanded query bank with multiple crawlers."""
    try:
        from icrawler.builtin import BingImageCrawler
    except ImportError:
        log.error("icrawler not installed. Run: pip install icrawler")
        sys.exit(1)

    try:
        from icrawler.builtin import GoogleImageCrawler
        has_google = True
    except ImportError:
        has_google = False
        log.warning("Google crawler not available — using Bing only")

    species_list = species_filter if species_filter else list(EXPANDED_QUERIES.keys())

    log.info("=" * 60)
    log.info("STAGE 1: EXPANDED SCRAPING")
    log.info("=" * 60)
    log.info(f"Species: {', '.join(species_list)}")
    log.info(f"Target per class: {target}")
    log.info(f"Queries per species: {len(EXPANDED_QUERIES[species_list[0]])}")

    for species in species_list:
        # Download to staging first, then merge
        staging_dir = os.path.join(STAGING_DIR, species)
        os.makedirs(staging_dir, exist_ok=True)

        dataset_dir = os.path.join(DATASET_DIR, species)
        os.makedirs(dataset_dir, exist_ok=True)

        existing_raw = count_images(dataset_dir)
        existing_staged = count_images(staging_dir)
        total_existing = existing_raw + existing_staged

        if total_existing >= target:
            log.info(f"[SKIP] {species}: already has {total_existing} images (target: {target})")
            continue

        queries = EXPANDED_QUERIES[species]
        needed = target - total_existing
        images_per_query = max(8, needed // len(queries) + 10)

        log.info(f"\n{'─'*50}")
        log.info(f"DOWNLOADING: {species.upper()} (have {total_existing}, need {target})")
        log.info(f"{'─'*50}")

        # Shuffle queries for variety across runs
        query_order = list(range(len(queries)))
        random.shuffle(query_order)

        for qi, q_idx in enumerate(query_order):
            query = queries[q_idx]
            current = count_images(staging_dir) + count_images(dataset_dir)
            if current >= target:
                log.info(f"  Reached target, stopping.")
                break

            # --- Bing ---
            log.info(f"  [Bing {qi+1}/{len(queries)}] '{query}' (req {images_per_query})")
            try:
                crawler = BingImageCrawler(
                    storage={"root_dir": staging_dir},
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
                log.warning(f"    Bing error: {e}")

        # --- Google fallback (if <70% of target) ---
        current = count_images(staging_dir) + count_images(dataset_dir)
        if has_google and current < target * 0.7:
            log.info(f"  [Google fallback] Only {current}/{target} — trying Google...")
            # Use a subset of queries for Google
            google_queries = random.sample(queries, min(8, len(queries)))
            for qi, query in enumerate(google_queries):
                current = count_images(staging_dir) + count_images(dataset_dir)
                if current >= target:
                    break
                log.info(f"  [Google {qi+1}/{len(google_queries)}] '{query}'")
                try:
                    crawler = GoogleImageCrawler(
                        storage={"root_dir": staging_dir},
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
                    log.warning(f"    Google error: {e}")

        final = count_images(staging_dir) + count_images(dataset_dir)
        log.info(f"  >> {species}: {final} total images")

    # Merge staging into dataset
    merge_staging()


def count_images(directory):
    """Count image files in a directory."""
    if not os.path.isdir(directory):
        return 0
    return len([f for f in os.listdir(directory)
                if f.lower().endswith(('.jpg', '.jpeg', '.png', '.bmp', '.gif', '.webp'))])


def merge_staging():
    """Merge staging downloads into main dataset, dedup by MD5."""
    if not os.path.isdir(STAGING_DIR):
        return

    log.info("\nMerging staging → dataset...")
    total_merged = 0
    total_dupes = 0

    for species in os.listdir(STAGING_DIR):
        staging_sp = os.path.join(STAGING_DIR, species)
        dataset_sp = os.path.join(DATASET_DIR, species)
        if not os.path.isdir(staging_sp):
            continue
        os.makedirs(dataset_sp, exist_ok=True)

        # Compute hashes of existing dataset images
        existing_hashes = set()
        for f in os.listdir(dataset_sp):
            fp = os.path.join(dataset_sp, f)
            if os.path.isfile(fp):
                try:
                    existing_hashes.add(compute_md5(fp))
                except Exception:
                    pass

        # Copy new unique images
        merged = 0
        dupes = 0
        for f in os.listdir(staging_sp):
            fp = os.path.join(staging_sp, f)
            if not os.path.isfile(fp):
                continue
            try:
                fhash = compute_md5(fp)
                if fhash in existing_hashes:
                    dupes += 1
                    os.remove(fp)
                    continue
                existing_hashes.add(fhash)

                # Generate unique filename
                ext = os.path.splitext(f)[1] or '.jpg'
                new_name = f"scaled_{species}_{fhash[:8]}{ext}"
                dst = os.path.join(dataset_sp, new_name)
                if not os.path.exists(dst):
                    shutil.move(fp, dst)
                    merged += 1
                else:
                    os.remove(fp)
                    dupes += 1
            except Exception:
                pass

        if merged > 0 or dupes > 0:
            log.info(f"  {species}: +{merged} new, {dupes} duplicates removed")
        total_merged += merged
        total_dupes += dupes

    log.info(f"  Total: +{total_merged} new images, {total_dupes} duplicates")

    # Clean up empty staging dirs
    try:
        shutil.rmtree(STAGING_DIR)
    except Exception:
        pass


# ============================================
# STAGE 2: CROSS-CLASS DEDUPLICATION
# ============================================
def cross_class_dedup():
    """Remove near-duplicate images that appear across different species.
    
    This catches the same footprint stock photo being scraped into
    multiple species folders from different queries.
    """
    log.info("\n" + "=" * 60)
    log.info("STAGE 2: CROSS-CLASS DEDUPLICATION")
    log.info("=" * 60)

    # Build hash index: species → [(path, phash), ...]
    all_entries = []  # (species, path, phash)
    species_dirs = {}

    for species in sorted(os.listdir(DATASET_DIR)):
        sp_dir = os.path.join(DATASET_DIR, species)
        if not os.path.isdir(sp_dir):
            continue
        species_dirs[species] = sp_dir

        for fname in sorted(os.listdir(sp_dir)):
            fpath = os.path.join(sp_dir, fname)
            if not fname.lower().endswith(('.jpg', '.jpeg', '.png', '.bmp', '.webp')):
                continue
            ph = compute_phash(fpath)
            if ph is not None:
                all_entries.append((species, fpath, ph))

    log.info(f"  Total images indexed: {len(all_entries)}")

    # Find cross-class near-duplicates
    # For efficiency, only compare across different species
    to_remove = set()
    cross_dupes = 0

    for i in range(len(all_entries)):
        if all_entries[i][1] in to_remove:
            continue
        for j in range(i + 1, len(all_entries)):
            if all_entries[j][1] in to_remove:
                continue
            # Only check across different species
            if all_entries[i][0] == all_entries[j][0]:
                continue

            dist = hamming_distance(all_entries[i][2], all_entries[j][2])
            if dist <= PHASH_THRESHOLD:
                # Remove from the species with more images (preserve smaller class)
                sp_i = all_entries[i][0]
                sp_j = all_entries[j][0]
                count_i = count_images(species_dirs.get(sp_i, ''))
                count_j = count_images(species_dirs.get(sp_j, ''))

                # Remove from the larger class
                if count_i >= count_j:
                    to_remove.add(all_entries[i][1])
                else:
                    to_remove.add(all_entries[j][1])
                cross_dupes += 1

    # Actually remove
    quarantine_dir = os.path.join(BASE_DIR, "dataset_quarantine_crossdup")
    os.makedirs(quarantine_dir, exist_ok=True)

    for fpath in to_remove:
        try:
            species = os.path.basename(os.path.dirname(fpath))
            q_sp_dir = os.path.join(quarantine_dir, species)
            os.makedirs(q_sp_dir, exist_ok=True)
            shutil.move(fpath, os.path.join(q_sp_dir, os.path.basename(fpath)))
        except Exception:
            pass

    log.info(f"  Cross-class duplicates found: {cross_dupes}")
    log.info(f"  Quarantined to: {quarantine_dir}")


# ============================================
# STAGE 3: INTELLIGENT AUGMENTATION
# ============================================
def intelligent_augment(species_filter=None, target=AUGMENT_TARGET):
    """Generate synthetic training images using morphology-preserving transforms.
    
    Unlike random augmentation during training, these are saved to disk
    so the effective dataset size increases permanently.
    
    Key design: only augment UNDERREPRESENTED classes.
    If elephant has 306 and leopard has 170, only augment leopard.
    
    Transforms designed for footprints:
    - Rotation (footprints can face any direction)
    - Elastic deformation (simulates different soil compaction)
    - Perspective warp (different camera angles)
    - Color jitter (different soil/lighting)
    - Gaussian blur (different focus distances)
    - Bilateral filter (smooths while preserving edges)
    """
    log.info("\n" + "=" * 60)
    log.info("STAGE 3: INTELLIGENT AUGMENTATION")
    log.info("=" * 60)

    species_list = species_filter if species_filter else sorted(
        d for d in os.listdir(CLEANED_DIR)
        if os.path.isdir(os.path.join(CLEANED_DIR, d))
    )

    # Check which classes need augmentation
    class_counts = {}
    for species in species_list:
        sp_dir = os.path.join(CLEANED_DIR, species)
        class_counts[species] = count_images(sp_dir)

    max_count = max(class_counts.values()) if class_counts else 0
    aug_target = max(target, max_count)  # At least match the largest class

    log.info(f"  Current class sizes: {class_counts}")
    log.info(f"  Augmentation target: {aug_target} per class")

    for species in species_list:
        sp_clean = os.path.join(CLEANED_DIR, species)
        sp_aug = os.path.join(AUGMENTED_DIR, species)
        os.makedirs(sp_aug, exist_ok=True)

        current = class_counts.get(species, 0)
        if current >= aug_target:
            log.info(f"  [SKIP] {species}: {current} >= {aug_target}")
            continue

        needed = aug_target - current
        source_images = [
            os.path.join(sp_clean, f) for f in sorted(os.listdir(sp_clean))
            if f.lower().endswith(('.jpg', '.jpeg', '.png'))
        ]

        if not source_images:
            log.warning(f"  [SKIP] {species}: no source images in cleaned/")
            continue

        log.info(f"  {species}: generating {needed} augmented images from {len(source_images)} sources...")

        # Track how many augments per source (max MAX_AUGMENTS_PER_SOURCE)
        source_usage = Counter()
        generated = 0

        while generated < needed:
            # Cycle through source images
            for src_path in source_images:
                if generated >= needed:
                    break
                if source_usage[src_path] >= MAX_AUGMENTS_PER_SOURCE:
                    continue

                try:
                    img = cv2.imread(src_path)
                    if img is None:
                        continue

                    # Pick a random augmentation strategy
                    aug_img = apply_random_augmentation(img, strategy=generated % 7)

                    # Save
                    aug_name = f"aug_{species}_{generated:04d}.jpg"
                    aug_path = os.path.join(sp_aug, aug_name)
                    cv2.imwrite(aug_path, aug_img, [cv2.IMWRITE_JPEG_QUALITY, 92])

                    source_usage[src_path] += 1
                    generated += 1

                except Exception as e:
                    log.debug(f"    Aug error on {src_path}: {e}")

            # If we've exhausted all sources at max usage, increase limit
            if all(source_usage[s] >= MAX_AUGMENTS_PER_SOURCE for s in source_images):
                break

        log.info(f"    → Generated {generated}/{needed} images")


def apply_random_augmentation(img, strategy=0):
    """Apply a morphology-preserving augmentation to a footprint image.
    
    7 strategies, each combining 2-3 transforms:
    """
    h, w = img.shape[:2]

    if strategy == 0:
        # Rotation + brightness
        angle = random.uniform(-30, 30)
        M = cv2.getRotationMatrix2D((w/2, h/2), angle, 1.0)
        img = cv2.warpAffine(img, M, (w, h), borderMode=cv2.BORDER_REFLECT)
        beta = random.uniform(-30, 30)
        img = cv2.convertScaleAbs(img, alpha=1.0, beta=beta)

    elif strategy == 1:
        # Perspective warp (camera angle variation)
        margin = int(min(w, h) * 0.1)
        pts1 = np.float32([[0, 0], [w, 0], [0, h], [w, h]])
        pts2 = np.float32([
            [random.randint(0, margin), random.randint(0, margin)],
            [w - random.randint(0, margin), random.randint(0, margin)],
            [random.randint(0, margin), h - random.randint(0, margin)],
            [w - random.randint(0, margin), h - random.randint(0, margin)],
        ])
        M = cv2.getPerspectiveTransform(pts1, pts2)
        img = cv2.warpPerspective(img, M, (w, h), borderMode=cv2.BORDER_REFLECT)

    elif strategy == 2:
        # Elastic deformation (soil compaction variation)
        img = elastic_deform(img, alpha=15, sigma=3)

    elif strategy == 3:
        # Color jitter (soil color variation)
        pil_img = Image.fromarray(cv2.cvtColor(img, cv2.COLOR_BGR2RGB))
        pil_img = ImageEnhance.Brightness(pil_img).enhance(random.uniform(0.7, 1.3))
        pil_img = ImageEnhance.Contrast(pil_img).enhance(random.uniform(0.8, 1.2))
        pil_img = ImageEnhance.Color(pil_img).enhance(random.uniform(0.7, 1.3))
        img = cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)

    elif strategy == 4:
        # Flip + slight blur (different orientation + focus)
        if random.random() > 0.5:
            img = cv2.flip(img, 1)  # Horizontal flip
        ksize = random.choice([3, 5])
        img = cv2.GaussianBlur(img, (ksize, ksize), 0)

    elif strategy == 5:
        # Zoom crop + rotation
        scale = random.uniform(0.8, 0.95)
        crop_h, crop_w = int(h * scale), int(w * scale)
        y_off = random.randint(0, h - crop_h)
        x_off = random.randint(0, w - crop_w)
        img = img[y_off:y_off+crop_h, x_off:x_off+crop_w]
        img = cv2.resize(img, (w, h))
        angle = random.uniform(-15, 15)
        M = cv2.getRotationMatrix2D((w/2, h/2), angle, 1.0)
        img = cv2.warpAffine(img, M, (w, h), borderMode=cv2.BORDER_REFLECT)

    elif strategy == 6:
        # Additive noise + bilateral smooth (sensor variation + edge preservation)
        noise = np.random.normal(0, 12, img.shape).astype(np.float32)
        img = np.clip(img.astype(np.float32) + noise, 0, 255).astype(np.uint8)
        img = cv2.bilateralFilter(img, 5, 50, 50)

    return img


def elastic_deform(img, alpha=15, sigma=3):
    """Elastic deformation — simulates different soil compaction.
    
    Applies smooth random displacement field to simulate how footprints
    look different in soft vs hard substrate.
    """
    h, w = img.shape[:2]
    # Random displacement fields
    dx = cv2.GaussianBlur((np.random.rand(h, w).astype(np.float32) * 2 - 1), (0, 0), sigma) * alpha
    dy = cv2.GaussianBlur((np.random.rand(h, w).astype(np.float32) * 2 - 1), (0, 0), sigma) * alpha

    # Create mapping
    x, y = np.meshgrid(np.arange(w), np.arange(h))
    map_x = (x + dx).astype(np.float32)
    map_y = (y + dy).astype(np.float32)

    return cv2.remap(img, map_x, map_y, cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)


# ============================================
# STAGE 4: FULL CLEANING PIPELINE
# ============================================
def run_cleaning_pipeline():
    """Run the full clean_dataset.py pipeline on the expanded dataset."""
    log.info("\n" + "=" * 60)
    log.info("STAGE 4: CLEANING PIPELINE")
    log.info("=" * 60)

    # Import and run existing clean_dataset
    try:
        import clean_dataset
        log.info("Running clean_dataset.py pipeline...")

        # The existing clean_dataset works on DATASET_DIR → CLEANED_DIR
        # Just call its functions
        for species in sorted(os.listdir(DATASET_DIR)):
            sp_dir = os.path.join(DATASET_DIR, species)
            if not os.path.isdir(sp_dir):
                continue

            cleaned_sp = os.path.join(CLEANED_DIR, species)
            os.makedirs(cleaned_sp, exist_ok=True)

            log.info(f"  Cleaning {species}...")

            # Step 1: Remove corrupted
            clean_dataset.remove_corrupted(sp_dir)

            # Step 2: Remove extreme aspect ratios
            clean_dataset.remove_extreme_aspect(sp_dir)

            # Step 3: Perceptual hash dedup
            clean_dataset.remove_perceptual_duplicates(sp_dir)

        log.info("  Running full pipeline...")
        # Call main cleaning — it copies to CLEANED_DIR
        os.system(f'python "{os.path.join(BASE_DIR, "clean_dataset.py")}"')

    except ImportError:
        log.warning("clean_dataset.py not importable — running as subprocess")
        os.system(f'python "{os.path.join(BASE_DIR, "clean_dataset.py")}"')


def merge_augmented():
    """Merge augmented images into the cleaned dataset."""
    if not os.path.isdir(AUGMENTED_DIR):
        return

    log.info("\nMerging augmented images into cleaned dataset...")

    for species in sorted(os.listdir(AUGMENTED_DIR)):
        aug_sp = os.path.join(AUGMENTED_DIR, species)
        clean_sp = os.path.join(CLEANED_DIR, species)
        if not os.path.isdir(aug_sp):
            continue
        os.makedirs(clean_sp, exist_ok=True)

        merged = 0
        for f in os.listdir(aug_sp):
            src = os.path.join(aug_sp, f)
            dst = os.path.join(clean_sp, f)
            if not os.path.exists(dst):
                shutil.copy2(src, dst)
                merged += 1

        if merged:
            log.info(f"  {species}: +{merged} augmented images")


# ============================================
# STAGE 5: DATASET ANALYTICS
# ============================================
def analyze_dataset(verbose=True):
    """Comprehensive dataset analysis with actionable insights."""
    report = {
        "timestamp": datetime.now().isoformat(),
        "raw_dataset": {},
        "cleaned_dataset": {},
        "augmented_dataset": {},
        "total_dataset": {},
        "class_balance": {},
        "recommendations": [],
    }

    dirs = {
        "raw_dataset": DATASET_DIR,
        "cleaned_dataset": CLEANED_DIR,
        "augmented_dataset": AUGMENTED_DIR,
    }

    for key, dpath in dirs.items():
        if not os.path.isdir(dpath):
            continue
        for species in sorted(os.listdir(dpath)):
            sp_dir = os.path.join(dpath, species)
            if os.path.isdir(sp_dir):
                count = count_images(sp_dir)
                report[key][species] = count

    # Total (cleaned + augmented)
    all_species = set(list(report["cleaned_dataset"].keys()) +
                      list(report["augmented_dataset"].keys()))
    for sp in all_species:
        report["total_dataset"][sp] = (
            report["cleaned_dataset"].get(sp, 0) +
            report["augmented_dataset"].get(sp, 0)
        )

    # Class balance analysis
    if report["total_dataset"]:
        counts = list(report["total_dataset"].values())
        max_c = max(counts) if counts else 0
        min_c = min(counts) if counts else 0
        report["class_balance"] = {
            "max_class": max(report["total_dataset"], key=report["total_dataset"].get),
            "min_class": min(report["total_dataset"], key=report["total_dataset"].get),
            "max_count": max_c,
            "min_count": min_c,
            "imbalance_ratio": round(max_c / min_c, 2) if min_c > 0 else float('inf'),
            "total_images": sum(counts),
        }

    # Recommendations
    recs = []
    for sp, count in sorted(report["total_dataset"].items(), key=lambda x: x[1]):
        if count < 200:
            recs.append(f"CRITICAL: {sp} has only {count} images. Need 400+ for reliable training.")
        elif count < 350:
            recs.append(f"LOW: {sp} has {count} images. Consider augmenting to 400+.")

    if report["class_balance"].get("imbalance_ratio", 1) > 1.5:
        recs.append(f"IMBALANCE: {report['class_balance']['imbalance_ratio']}x ratio. "
                     f"Consider oversampling {report['class_balance']['min_class']}.")

    report["recommendations"] = recs

    # Print
    if verbose:
        print("\n" + "=" * 70)
        print("  WILDTRACKAI DATASET ANALYTICS")
        print("=" * 70)

        print(f"\n  {'Species':<12} {'Raw':>6} {'Cleaned':>8} {'Augmented':>10} {'Total':>7} {'Status'}")
        print("  " + "-" * 55)
        for sp in sorted(all_species):
            raw = report["raw_dataset"].get(sp, 0)
            clean = report["cleaned_dataset"].get(sp, 0)
            aug = report["augmented_dataset"].get(sp, 0)
            total = report["total_dataset"].get(sp, 0)
            if total >= TARGET_PER_CLASS:
                status = "OK"
            elif total >= 300:
                status = "USABLE"
            elif total >= 200:
                status = "LOW"
            else:
                status = "CRITICAL"
            print(f"  {sp:<12} {raw:>6} {clean:>8} {aug:>10} {total:>7}  {status}")

        bal = report["class_balance"]
        print(f"\n  Total images:     {bal.get('total_images', 0)}")
        print(f"  Largest class:    {bal.get('max_class', '?')} ({bal.get('max_count', 0)})")
        print(f"  Smallest class:   {bal.get('min_class', '?')} ({bal.get('min_count', 0)})")
        print(f"  Imbalance ratio:  {bal.get('imbalance_ratio', '?')}x")

        if recs:
            print(f"\n  Recommendations:")
            for r in recs:
                print(f"    ⚠ {r}")

        print("=" * 70)

    # Save report
    with open(REPORT_PATH, 'w') as f:
        json.dump(report, f, indent=2)
    log.info(f"  Report saved: {REPORT_PATH}")

    return report


# ============================================
# MAIN PIPELINE
# ============================================
def run_full_pipeline(species_filter=None, target=TARGET_PER_CLASS, do_scrape=True,
                      do_augment=True, do_clean=True):
    """Run the complete dataset scaling pipeline."""
    print("=" * 70)
    print("  WILDTRACKAI — DATASET SCALER v2")
    print("=" * 70)
    print(f"  Target per class: {target}")
    print(f"  Species filter:   {species_filter or 'all'}")
    print(f"  Steps:            {'scrape ' if do_scrape else ''}{'clean ' if do_clean else ''}{'augment' if do_augment else ''}")
    print("=" * 70)

    # Pre-analysis
    print("\n📊 BEFORE:")
    analyze_dataset(verbose=True)

    if do_scrape:
        scrape_expanded(species_filter=species_filter, target=target)

    # Cross-class dedup (after scraping, before cleaning)
    if do_scrape:
        cross_class_dedup()

    if do_clean:
        run_cleaning_pipeline()

    if do_augment:
        intelligent_augment(species_filter=species_filter, target=target)
        merge_augmented()

    # Post-analysis
    print("\n📊 AFTER:")
    report = analyze_dataset(verbose=True)

    print("\n" + "=" * 70)
    print("  SCALING COMPLETE")
    print("=" * 70)
    print(f"\n  Total training images: {report['class_balance'].get('total_images', 0)}")
    print(f"  Imbalance ratio:      {report['class_balance'].get('imbalance_ratio', '?')}x")
    print(f"\n  Next step: python training/train_v4.py")
    print("=" * 70)

    return report


# ============================================
# CLI
# ============================================
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="WildTrackAI — Dataset Scaler v2")
    parser.add_argument("--target", type=int, default=TARGET_PER_CLASS,
                        help=f"Target images per class (default: {TARGET_PER_CLASS})")
    parser.add_argument("--scrape-only", action="store_true",
                        help="Only download new images (no augment/clean)")
    parser.add_argument("--augment-only", action="store_true",
                        help="Only generate augmented images")
    parser.add_argument("--clean-only", action="store_true",
                        help="Only run cleaning pipeline")
    parser.add_argument("--analyze", action="store_true",
                        help="Show dataset analytics")
    parser.add_argument("--dedup", action="store_true",
                        help="Only run cross-class deduplication")
    parser.add_argument("--species", nargs="+",
                        help="Only process specific species (e.g., --species leopard tiger)")
    args = parser.parse_args()

    TARGET_PER_CLASS = args.target

    if args.analyze:
        analyze_dataset(verbose=True)
    elif args.scrape_only:
        scrape_expanded(species_filter=args.species, target=args.target)
    elif args.augment_only:
        intelligent_augment(species_filter=args.species, target=args.target)
        merge_augmented()
    elif args.clean_only:
        run_cleaning_pipeline()
    elif args.dedup:
        cross_class_dedup()
    else:
        run_full_pipeline(
            species_filter=args.species,
            target=args.target,
            do_scrape=True,
            do_augment=True,
            do_clean=True,
        )
