"""
WildTrackAI Strict Dataset Filter
=================================
Builds a high-quality training dataset using only clear, real-looking images.

What it removes:
- blurry images
- tiny/low-detail images
- likely graphics/watermarked/text-heavy images
- suspicious filename patterns (stock/watermark/logo)
- near-duplicates (keeps sharper copy)

Usage:
    python strict_filter_dataset.py
    python strict_filter_dataset.py --dry-run
    python strict_filter_dataset.py --min-blur 100 --garbage-threshold 55
"""

import os
import json
import shutil
import argparse
from pathlib import Path
from collections import defaultdict

import cv2
import numpy as np

from auto_clean import compute_garbage_score
from clean_dataset import compute_phash, hamming_distance

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DEFAULT_SOURCE = os.path.join(BASE_DIR, "dataset_cleaned")
DEFAULT_OUTPUT = os.path.join(BASE_DIR, "dataset_strict")
DEFAULT_QUARANTINE = os.path.join(BASE_DIR, "dataset_quarantine_strict")
IMAGE_EXTS = (".jpg", ".jpeg", ".png", ".bmp", ".webp")

SUSPICIOUS_NAME_TOKENS = {
    "shutterstock", "getty", "istock", "stock", "watermark", "logo",
    "vector", "clipart", "illustration", "diagram", "pinterest"
}


def iter_images(folder):
    for name in sorted(os.listdir(folder)):
        path = os.path.join(folder, name)
        if os.path.isfile(path) and name.lower().endswith(IMAGE_EXTS):
            yield name, path


def image_entropy(gray_image):
    hist = cv2.calcHist([gray_image], [0], None, [256], [0, 256]).ravel()
    total = np.sum(hist)
    if total <= 0:
        return 0.0
    probs = hist / total
    probs = probs[probs > 0]
    return float(-np.sum(probs * np.log2(probs)))


def blur_score(gray_image):
    return float(cv2.Laplacian(gray_image, cv2.CV_64F).var())


def center_square_resize(img, target_size):
    height, width = img.shape[:2]
    side = min(height, width)
    top = (height - side) // 2
    left = (width - side) // 2
    crop = img[top:top + side, left:left + side]
    return cv2.resize(crop, (target_size, target_size), interpolation=cv2.INTER_LANCZOS4)


def evaluate_image(filepath, args):
    reasons = []
    metrics = {}

    img = cv2.imread(filepath)
    if img is None or img.size == 0:
        return None, ["corrupted_or_unreadable"], metrics

    height, width = img.shape[:2]
    metrics["width"] = int(width)
    metrics["height"] = int(height)

    if min(height, width) < args.min_size:
        reasons.append("too_small")

    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    b_score = blur_score(gray)
    metrics["blur_score"] = round(b_score, 3)
    if b_score < args.min_blur:
        reasons.append("blurry")

    entropy = image_entropy(gray)
    metrics["entropy"] = round(entropy, 3)
    if entropy < args.min_entropy:
        reasons.append("low_detail")

    filename_lower = os.path.basename(filepath).lower()
    if any(token in filename_lower for token in SUSPICIOUS_NAME_TOKENS):
        reasons.append("suspicious_filename")

    garbage_score, garbage_reasons = compute_garbage_score(filepath)
    metrics["garbage_score"] = round(float(garbage_score), 2)
    if garbage_score >= args.garbage_threshold:
        reasons.append("non_real_or_unwanted")

    if any("text_heavy" in reason for reason in garbage_reasons):
        reasons.append("possible_watermark_or_text_overlay")

    return img, reasons, metrics


def quarantine_copy(src_path, quarantine_path, dry_run):
    os.makedirs(os.path.dirname(quarantine_path), exist_ok=True)
    if not dry_run:
        shutil.copy2(src_path, quarantine_path)


def dedupe_species(species_output_dir, species_quarantine_dir, args, dry_run):
    files = [
        os.path.join(species_output_dir, f)
        for f in os.listdir(species_output_dir)
        if f.lower().endswith(IMAGE_EXTS)
    ]

    if len(files) < 2:
        return 0

    records = []
    for path in files:
        phash = compute_phash(path)
        img = cv2.imread(path, cv2.IMREAD_GRAYSCALE)
        score = blur_score(img) if img is not None else 0.0
        records.append({"path": path, "phash": phash, "blur": score})

    removed = 0
    removed_set = set()

    for i in range(len(records)):
        if records[i]["path"] in removed_set:
            continue
        for j in range(i + 1, len(records)):
            if records[j]["path"] in removed_set:
                continue
            if records[i]["phash"] is None or records[j]["phash"] is None:
                continue

            dist = hamming_distance(records[i]["phash"], records[j]["phash"])
            if dist <= args.phash_threshold:
                keep = i if records[i]["blur"] >= records[j]["blur"] else j
                drop = j if keep == i else i
                drop_path = records[drop]["path"]

                rel = os.path.basename(drop_path)
                quarantine_path = os.path.join(species_quarantine_dir, rel)
                quarantine_copy(drop_path, quarantine_path, dry_run)

                if not dry_run and os.path.exists(drop_path):
                    os.remove(drop_path)

                removed_set.add(drop_path)
                removed += 1

    return removed


def strict_filter(args):
    source = args.source
    output = args.output
    quarantine = args.quarantine

    if not os.path.isdir(source):
        raise FileNotFoundError(f"Source dataset not found: {source}")

    species_list = sorted([
        d for d in os.listdir(source)
        if os.path.isdir(os.path.join(source, d))
    ])

    if not species_list:
        raise RuntimeError("No class folders found in source dataset")

    if args.reset_output and os.path.isdir(output) and not args.dry_run:
        shutil.rmtree(output)

    os.makedirs(output, exist_ok=True)
    os.makedirs(quarantine, exist_ok=True)

    total_before = 0
    total_after = 0
    total_quarantine = 0
    total_deduped = 0

    summary = {}

    print("=" * 70)
    print("WILDTRACKAI STRICT DATA FILTER")
    print("=" * 70)
    print(f"Source:      {source}")
    print(f"Output:      {output}")
    print(f"Quarantine:  {quarantine}")
    print(f"Dry-run:     {args.dry_run}")
    print(f"Min blur:    {args.min_blur}")
    print(f"Min entropy: {args.min_entropy}")
    print(f"Min size:    {args.min_size}")
    print(f"Garbage thr: {args.garbage_threshold}")
    print("=" * 70)

    for species in species_list:
        species_src = os.path.join(source, species)
        species_out = os.path.join(output, species)
        species_quarantine = os.path.join(quarantine, species)

        os.makedirs(species_out, exist_ok=True)
        os.makedirs(species_quarantine, exist_ok=True)

        class_reasons = defaultdict(int)
        class_before = 0
        class_kept = 0
        class_quarantined = 0

        for filename, src_path in iter_images(species_src):
            class_before += 1
            total_before += 1

            img, reasons, metrics = evaluate_image(src_path, args)
            if img is None:
                reasons = ["corrupted_or_unreadable"]

            if reasons:
                class_quarantined += 1
                total_quarantine += 1
                for reason in set(reasons):
                    class_reasons[reason] += 1
                q_path = os.path.join(species_quarantine, filename)
                quarantine_copy(src_path, q_path, args.dry_run)
                continue

            out_name = f"{Path(filename).stem}.jpg"
            out_path = os.path.join(species_out, out_name)
            resized = center_square_resize(img, args.target_size)
            if not args.dry_run:
                cv2.imwrite(out_path, resized, [cv2.IMWRITE_JPEG_QUALITY, 95])
            class_kept += 1
            total_after += 1

        deduped = dedupe_species(species_out, species_quarantine, args, args.dry_run)
        total_deduped += deduped
        class_kept -= deduped
        total_after -= deduped
        class_reasons["near_duplicate"] += deduped

        summary[species] = {
            "before": class_before,
            "kept": class_kept,
            "quarantined": class_quarantined + deduped,
            "reasons": dict(sorted(class_reasons.items(), key=lambda x: x[0]))
        }

        print(f"{species:>12}: before={class_before:4d} kept={class_kept:4d} quarantined={class_quarantined + deduped:4d}")

    report = {
        "source": source,
        "output": output,
        "quarantine": quarantine,
        "target_size": args.target_size,
        "thresholds": {
            "min_blur": args.min_blur,
            "min_entropy": args.min_entropy,
            "min_size": args.min_size,
            "garbage_threshold": args.garbage_threshold,
            "phash_threshold": args.phash_threshold,
        },
        "totals": {
            "before": total_before,
            "after": total_after,
            "quarantined": total_quarantine,
            "deduped": total_deduped,
        },
        "classes": summary,
    }

    report_path = os.path.join(BASE_DIR, "strict_filter_report.json")
    if not args.dry_run:
        with open(report_path, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2)

    print("=" * 70)
    print(f"Total before:      {total_before}")
    print(f"Total after:       {total_after}")
    print(f"Total quarantined: {total_quarantine + total_deduped}")
    print(f"Duplicates removed:{total_deduped}")
    if not args.dry_run:
        print(f"Report:            {report_path}")
    print("=" * 70)


def parse_args():
    parser = argparse.ArgumentParser(description="Build strict, clear-image dataset")
    parser.add_argument("--source", default=DEFAULT_SOURCE)
    parser.add_argument("--output", default=DEFAULT_OUTPUT)
    parser.add_argument("--quarantine", default=DEFAULT_QUARANTINE)
    parser.add_argument("--target-size", type=int, default=300)
    parser.add_argument("--min-size", type=int, default=160)
    parser.add_argument("--min-blur", type=float, default=50.0)
    parser.add_argument("--min-entropy", type=float, default=3.2)
    parser.add_argument("--garbage-threshold", type=float, default=85.0)
    parser.add_argument("--phash-threshold", type=int, default=8)
    parser.add_argument("--reset-output", action="store_true", default=True)
    parser.add_argument("--no-reset-output", dest="reset_output", action="store_false")
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args()


if __name__ == "__main__":
    strict_filter(parse_args())
