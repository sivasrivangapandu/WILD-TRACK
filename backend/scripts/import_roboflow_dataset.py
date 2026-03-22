"""
WildTrackAI — Perfect Dataset Importer (Roboflow)
===================================================
Automatically downloads a highly-curated, labelled animal footprints dataset
from Roboflow Universe and prepares it for training.

Usage:
    pip install roboflow
    python import_roboflow_dataset.py --api-key YOUR_ROBOFLOW_KEY
"""

import os
import shutil
import argparse
from pathlib import Path

# ============================================
# CONFIGURATION
# ============================================
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PERFECT_DATASET_DIR = os.path.join(BASE_DIR, "dataset_perfect")

# We map external dataset classes to our 5 target classes
CLASS_MAPPING = {
    "tiger": "tiger",
    "bengal_tiger": "tiger",
    "leopard": "leopard",
    "amur_leopard": "leopard",
    "snow_leopard": "leopard",
    "elephant": "elephant",
    "asian_elephant": "elephant",
    "african_elephant": "elephant",
    "deer": "deer",
    "white_tailed_deer": "deer",
    "wolf": "wolf",
    "grey_wolf": "wolf"
}

def import_dataset(api_key):
    try:
        from roboflow import Roboflow
    except ImportError:
        print("ERROR: roboflow package not installed.")
        print("Run: pip install roboflow")
        return

    print("=" * 60)
    print("WILDTRACKAI - ROBOFLOW DATASET IMPORTER")
    print("=" * 60)
    
    rf = Roboflow(api_key=api_key)
    
    # We use a known high-quality public dataset from Roboflow Universe
    # Project: animal-footprints-classification
    print("Connecting to Roboflow Universe...")
    try:
        project = rf.workspace("animal-footprints").project("animal-footprints-classification")
        version = project.version(1)
        dataset = version.download("folder")
        
        print(f"\nSuccessfully downloaded dataset to: {dataset.location}")
    except Exception as e:
        print(f"\nERROR downloading dataset: {e}")
        print("Please check your API key and internet connection.")
        return

    print("\nProcessing and organizing classes...")
    
    # Create target directories
    for target_class in set(CLASS_MAPPING.values()):
        os.makedirs(os.path.join(PERFECT_DATASET_DIR, target_class), exist_ok=True)
        
    # Move and map images
    copied = 0
    skipped = 0
    
    # Roboflow structure is typically train/valid/test folders
    for split in ['train', 'valid', 'test']:
        split_dir = os.path.join(dataset.location, split)
        if not os.path.exists(split_dir):
            continue
            
        for class_dir in os.listdir(split_dir):
            src_class_path = os.path.join(split_dir, class_dir)
            if not os.path.isdir(src_class_path):
                continue
                
            # Normalize class name for mapping
            normalized_class = class_dir.lower().replace(" ", "_")
            
            # Find matching target class
            target_class = None
            for key, val in CLASS_MAPPING.items():
                if key in normalized_class:
                    target_class = val
                    break
                    
            if not target_class:
                skipped += len(os.listdir(src_class_path))
                continue
                
            dest_dir = os.path.join(PERFECT_DATASET_DIR, target_class)
            
            for file in os.listdir(src_class_path):
                if file.lower().endswith(('.png', '.jpg', '.jpeg')):
                    src_file = os.path.join(src_class_path, file)
                    dest_file = os.path.join(dest_dir, f"rf_{copied}_{file}")
                    shutil.copy2(src_file, dest_file)
                    copied += 1

    print("\n" + "=" * 60)
    print("IMPORT COMPLETE!")
    print("=" * 60)
    print(f"Total curated images imported: {copied}")
    print(f"Ignored irrelevant classes: {skipped}")
    print(f"\nDataset is ready at: {PERFECT_DATASET_DIR}")
    print("Next step: python backend/training/train_v5_perfect.py")
    
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Import curated footprint dataset")
    parser.add_argument("--api-key", required=True, help="Roboflow API Key")
    args = parser.parse_args()
    import_dataset(args.api_key)
