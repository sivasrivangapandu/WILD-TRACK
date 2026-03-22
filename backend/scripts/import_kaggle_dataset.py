"""
WildTrackAI — Perfect Dataset Importer (Kaggle)
===================================================
Automatically downloads a high-quality, curated animal footprints dataset
from Kaggle and prepares it for training.

Usage:
    Ensure you have your kaggle.json configured (in ~/.kaggle/kaggle.json)
    pip install kaggle
    python import_kaggle_dataset.py
"""

import os
import zipfile
import shutil
import argparse

# ============================================
# CONFIGURATION
# ============================================
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PERFECT_DATASET_DIR = os.path.join(BASE_DIR, "dataset_perfect")

# We map external dataset classes to our 5 target classes
CLASS_MAPPING = {
    "tiger": "tiger",
    "bengaltiger": "tiger",
    "leopard": "leopard",
    "amurleopard": "leopard",
    "snowleopard": "leopard",
    "elephant": "elephant",
    "asianelephant": "elephant",
    "africanelephant": "elephant",
    "deer": "deer",
    "whitetaileddeer": "deer",
    "wolf": "wolf",
    "greywolf": "wolf"
}

def import_kaggle_dataset(dataset_name="paultimothymooney/animal-tracks-and-signs"):
    try:
        import kaggle
    except ImportError:
        print("ERROR: kaggle package not installed.")
        print("Run: pip install kaggle")
        return
    except OSError:
        print("ERROR: Kaggle API credentials not found.")
        print("Please place your kaggle.json in ~/.kaggle/kaggle.json")
        return

    print("=" * 60)
    print("WILDTRACKAI - KAGGLE DATASET IMPORTER")
    print("=" * 60)
    
    print(f"Downloading Kaggle dataset: {dataset_name}...")
    dl_path = os.path.join(BASE_DIR, "temp_kaggle_dl")
    os.makedirs(dl_path, exist_ok=True)
    
    try:
        kaggle.api.dataset_download_files(dataset_name, path=dl_path, unzip=True)
    except Exception as e:
        print(f"\nERROR downloading dataset: {e}")
        return

    print("\nProcessing and organizing classes...")
    
    # Create target directories
    for target_class in set(CLASS_MAPPING.values()):
        os.makedirs(os.path.join(PERFECT_DATASET_DIR, target_class), exist_ok=True)
        
    copied = 0
    skipped = 0
    
    # Traverse unzipped dataset and map to target classes
    for root, _, files in os.walk(dl_path):
        for file in files:
            if not file.lower().endswith(('.png', '.jpg', '.jpeg')):
                continue
                
            # Deduce class from folder name or file name
            folder_name = os.path.basename(root).lower().replace(" ", "").replace("_", "")
            
            target_class = None
            for key, val in CLASS_MAPPING.items():
                if key in folder_name:
                    target_class = val
                    break
                    
            if not target_class:
                skipped += 1
                continue
                
            src_file = os.path.join(root, file)
            dest_dir = os.path.join(PERFECT_DATASET_DIR, target_class)
            dest_file = os.path.join(dest_dir, f"kg_{copied}_{file}")
            
            shutil.copy2(src_file, dest_file)
            copied += 1

    # Clean up temp directoy
    shutil.rmtree(dl_path, ignore_errors=True)

    print("\n" + "=" * 60)
    print("IMPORT COMPLETE!")
    print("=" * 60)
    print(f"Total curated images imported: {copied}")
    print(f"Ignored irrelevant classes: {skipped}")
    print(f"\nDataset is ready at: {PERFECT_DATASET_DIR}")
    print("Next step: python backend/training/train_v5_perfect.py")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Import curated footprint dataset from Kaggle")
    parser.add_argument("--dataset", type=str, default="paultimothymooney/animal-tracks-and-signs",
                        help="Kaggle dataset ID (default: animal footprints)")
    args = parser.parse_args()
    import_kaggle_dataset(args.dataset)
