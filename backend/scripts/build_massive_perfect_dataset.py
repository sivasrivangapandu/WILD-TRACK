"""
WildTrackAI — Massive Dataset Builder & Curator
===================================================
Automatically downloads a massive volume of images across multiple search
engines and routes them directly through the strict `auto_clean` filter to
produce thousands of perfectly clean images in `dataset_perfect`.

Usage:
    pip install icrawler duckduckgo_search
    python build_massive_perfect_dataset.py
"""

import os
import shutil
import threading
from concurrent.futures import ThreadPoolExecutor

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TEMP_DIR = os.path.join(BASE_DIR, "temp_downloads")
PERFECT_DIR = os.path.join(BASE_DIR, "dataset_perfect")

# We import the strict garbage filter
import sys
sys.path.append(BASE_DIR)
try:
    from auto_clean import compute_garbage_score
    CLEANER_AVAILABLE = True
except ImportError:
    CLEANER_AVAILABLE = False
    print("WARNING: auto_clean.py not found. Dataset will not be filtered.")

# The strict threshold for massive datasets - more forgiving than extreme local but still tight
STRICT_THRESHOLD = 40

ANIMALS = {
    "tiger": ["tiger footprint ground", "tiger pugmark clear mud", "bengal tiger track sand"],
    "leopard": ["leopard footprint", "leopard pugmark dirt", "snow leopard track snow"],
    "elephant": ["elephant footprint mud", "elephant track dirt", "large elephant footprint"],
    "deer": ["deer hoof print mud", "buck deer track dirt", "white tailed deer footprint"],
    "wolf": ["wolf footprint snow", "grey wolf track mud", "wolf paw print dirt"],
}

IMAGES_PER_QUERY = 500  # Total possible per class: 1500

def scrape_with_icrawler(query, save_dir, engine="google"):
    try:
        if engine == "google":
            from icrawler.builtin import GoogleImageCrawler
            crawler = GoogleImageCrawler(storage={'root_dir': save_dir}, feeder_threads=1, parser_threads=2, downloader_threads=4)
        else:
            from icrawler.builtin import BingImageCrawler
            crawler = BingImageCrawler(storage={'root_dir': save_dir}, feeder_threads=1, parser_threads=2, downloader_threads=4)
            
        crawler.crawl(keyword=query, max_num=IMAGES_PER_QUERY, file_idx_offset='auto')
    except Exception as e:
        print(f"[{engine.upper()}] Error scraping '{query}': {e}")

def curate_folder(animal_class):
    src_dir = os.path.join(TEMP_DIR, animal_class)
    dst_dir = os.path.join(PERFECT_DIR, animal_class)
    os.makedirs(dst_dir, exist_ok=True)
    
    if not os.path.exists(src_dir):
        return 0, 0
        
    kept, removed = 0, 0
    images = [f for f in os.listdir(src_dir) if f.lower().endswith(('.jpg', '.jpeg', '.png'))]
    
    for img in images:
        src_path = os.path.join(src_dir, img)
        if CLEANER_AVAILABLE:
            score, _ = compute_garbage_score(src_path)
            if score < STRICT_THRESHOLD:
                dst_path = os.path.join(dst_dir, img)
                shutil.move(src_path, dst_path)
                kept += 1
            else:
                os.remove(src_path)
                removed += 1
        else:
            dst_path = os.path.join(dst_dir, img)
            shutil.move(src_path, dst_path)
            kept += 1
            
    return kept, removed

def process_animal(animal, queries):
    print(f"\n--- Starting massive collection for: {animal.upper()} ---")
    animal_temp = os.path.join(TEMP_DIR, animal)
    os.makedirs(animal_temp, exist_ok=True)
    
    # 1. Scrape in parallel
    with ThreadPoolExecutor(max_workers=6) as executor:
        for q in queries:
            executor.submit(scrape_with_icrawler, q, animal_temp, "google")
            executor.submit(scrape_with_icrawler, q, animal_temp, "bing")
            
    # 2. Curate immediately to save space
    kept, removed = curate_folder(animal)
    print(f"[{animal.upper()}] Curation Done: Kept={kept}, Removed={removed} (Score > {STRICT_THRESHOLD})")

def main():
    print("=" * 70)
    print(" WILDTRACKAI - MASSIVE PERFECT DATASET PIPELINE ")
    print("=" * 70)
    print(f"Targeting ~{IMAGES_PER_QUERY * 6} images per class before filtering...")
    
    os.makedirs(TEMP_DIR, exist_ok=True)
    os.makedirs(PERFECT_DIR, exist_ok=True)
    
    for animal, queries in ANIMALS.items():
        process_animal(animal, queries)
        
    # Cleanup temp
    shutil.rmtree(TEMP_DIR, ignore_errors=True)
    print("\n" + "=" * 70)
    print(" MASSIVE COLLECTION COMPLETE ")
    print(f" Dataset is ready at: {PERFECT_DIR}")
    print(" Next Step: run backend/training/train_v5_perfect.py")
    print("=" * 70)

if __name__ == "__main__":
    main()
