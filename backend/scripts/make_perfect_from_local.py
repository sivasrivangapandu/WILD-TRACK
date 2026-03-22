"""
WildTrackAI — Extreme Local Dataset Filter
============================================
Creates a 'dataset_perfect' from the existing 'dataset_cleaned' by applying
extremely strict heuristics. Only the absolute highest-quality natural
footprint photos will survive this filter (score < 35).
"""

import os
import shutil

# Import the scoring functions from auto_clean
import sys
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(BASE_DIR)

from auto_clean import compute_garbage_score

CLEAN_DIR = os.path.join(BASE_DIR, "dataset_cleaned")
PERFECT_DIR = os.path.join(BASE_DIR, "dataset_perfect")
STRICT_THRESHOLD = 35  # Very aggressive

def make_perfect_dataset():
    print("=" * 60)
    print(" WILDTRACKAI - EXTREME DATASET CURATION ")
    print("=" * 60)
    
    if os.path.exists(PERFECT_DIR):
        shutil.rmtree(PERFECT_DIR)
        
    os.makedirs(PERFECT_DIR, exist_ok=True)
    
    classes = [d for d in os.listdir(CLEAN_DIR) if os.path.isdir(os.path.join(CLEAN_DIR, d))]
    
    total_kept = 0
    total_removed = 0
    
    for c in classes:
        src_c = os.path.join(CLEAN_DIR, c)
        dst_c = os.path.join(PERFECT_DIR, c)
        os.makedirs(dst_c, exist_ok=True)
        
        images = [f for f in os.listdir(src_c) if f.lower().endswith(('.jpg', '.jpeg', '.png'))]
        
        kept = 0
        removed = 0
        print(f"\nFiltering {c.upper()} ({len(images)} images)...")
        
        for img in images:
            src_path = os.path.join(src_c, img)
            score, reasons = compute_garbage_score(src_path)
            
            if score < STRICT_THRESHOLD:
                # Keep it! It's a pristine natural footprint
                dst_path = os.path.join(dst_c, img)
                shutil.copy2(src_path, dst_path)
                kept += 1
            else:
                removed += 1
                
        print(f"  Kept: {kept} (Pristine)")
        print(f"  Removed: {removed} (Garbage score >= {STRICT_THRESHOLD})")
        total_kept += kept
        total_removed += removed
        
    print("\n" + "=" * 60)
    print(" CURATION COMPLETE ")
    print("=" * 60)
    print(f"Total pristine images: {total_kept}")
    print(f"Total images removed: {total_removed}")
    print(f"Perfect dataset saved to: {PERFECT_DIR}")

if __name__ == "__main__":
    make_perfect_dataset()
