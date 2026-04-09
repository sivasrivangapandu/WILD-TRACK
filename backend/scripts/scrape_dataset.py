"""
WildTrackAI - Automatic Dataset Scraper
Downloads animal footprint images from Google automatically.
No manual download required!
"""

import os
import time
import random
from icrawler.builtin import BingImageCrawler
import cv2
import numpy as np
from PIL import Image


class WildTrackDatasetBuilder:
    def __init__(self):
        # Define animals and their search terms
        self.animals = {
            'tiger': [
                'tiger pugmark',
                'tiger footprint in mud',
                'tiger paw print soil',
                'tiger foot print forest',
                'tiger track wildlife'
            ],
            'leopard': [
                'leopard pugmark',
                'leopard footprint soil',
                'leopard paw print',
                'leopard track wildlife',
                'leopard foot print jungle'
            ],
            'elephant': [
                'elephant footprint mud',
                'elephant foot print forest',
                'elephant track soil',
                'elephant pugmark',
                'elephant foot impression'
            ],
            'deer': [
                'deer hoof print',
                'deer footprint mud',
                'deer track forest',
                'spotted deer foot print',
                'deer pugmark soil'
            ],
            'wolf': [
                'wolf footprint mud',
                'wolf paw print soil',
                'wolf track forest',
                'wolf pugmark',
                'wolf foot impression'
            ],
            'fox': [
                'fox footprint mud',
                'fox paw print soil',
                'fox track wildlife',
                'fox foot print forest',
                'fox pugmark'
            ]
        }

        # Base directory
        self.base_dir = os.path.join(os.path.dirname(__file__), 'dataset')

    def create_folders(self):
        """Create folder structure for all animals"""
        print("Creating folder structure...")
        for animal in self.animals.keys():
            folder_path = os.path.join(self.base_dir, animal)
            os.makedirs(folder_path, exist_ok=True)
            print(f"  Created: {folder_path}")

    def download_images(self, animal, search_terms, num_images=150):
        """Download images for a specific animal"""
        print(f"\nDownloading {animal.upper()} images...")

        animal_dir = os.path.join(self.base_dir, animal)
        downloaded = 0

        for search_term in search_terms:
            if downloaded >= num_images:
                break

            remaining = num_images - downloaded
            images_to_get = min(50, remaining)

            print(f"  Searching: '{search_term}' ({images_to_get} images)")

            try:
                crawler = BingImageCrawler(
                    storage={'root_dir': animal_dir},
                    parser_threads=2,
                    downloader_threads=4
                )

                crawler.crawl(
                    keyword=search_term,
                    max_num=images_to_get,
                    min_size=(200, 200),
                    file_idx_offset=downloaded
                )

                downloaded += images_to_get
                print(f"  Got {images_to_get} images")

                # Random delay to avoid being blocked
                time.sleep(random.uniform(2, 5))

            except Exception as e:
                print(f"  Error: {e}")
                continue

        print(f"  Total {animal}: {downloaded} images")
        return downloaded

    def clean_images(self, animal):
        """Remove corrupted or invalid images"""
        print(f"\nCleaning {animal} images...")

        animal_dir = os.path.join(self.base_dir, animal)
        if not os.path.exists(animal_dir):
            return 0

        images = os.listdir(animal_dir)
        removed = 0

        for img_name in images:
            img_path = os.path.join(animal_dir, img_name)

            try:
                with Image.open(img_path) as img:
                    img.verify()

                img_cv = cv2.imread(img_path)
                if img_cv is None or img_cv.size == 0:
                    raise Exception("Invalid image")

                height, width = img_cv.shape[:2]
                if height < 100 or width < 100:
                    raise Exception("Image too small")

            except Exception:
                os.remove(img_path)
                removed += 1
                print(f"  Removed invalid: {img_name}")

        print(f"  Cleaned {removed} invalid images")
        return removed

    def augment_dataset(self, animal):
        """Create augmented versions to increase dataset size"""
        print(f"\nAugmenting {animal} dataset...")

        animal_dir = os.path.join(self.base_dir, animal)
        if not os.path.exists(animal_dir):
            return 0

        images = [f for f in os.listdir(animal_dir)
                  if f.lower().endswith(('.jpg', '.jpeg', '.png'))]

        augmented = 0
        for img_name in images[:50]:
            img_path = os.path.join(animal_dir, img_name)

            try:
                img = cv2.imread(img_path)
                if img is None:
                    continue

                base_name = os.path.splitext(img_name)[0]

                # 1. Rotate
                for angle in [90, 180, 270]:
                    rotated = self._rotate_image(img, angle)
                    cv2.imwrite(
                        os.path.join(animal_dir, f"{base_name}_rot{angle}.jpg"),
                        rotated
                    )
                    augmented += 1

                # 2. Flip
                flipped = cv2.flip(img, 1)
                cv2.imwrite(
                    os.path.join(animal_dir, f"{base_name}_flip.jpg"),
                    flipped
                )
                augmented += 1

                # 3. Brightness adjustment
                bright = self._adjust_brightness(img, 1.2)
                cv2.imwrite(
                    os.path.join(animal_dir, f"{base_name}_bright.jpg"),
                    bright
                )
                augmented += 1

                # 4. Add noise (simulate real conditions)
                noisy = self._add_noise(img)
                cv2.imwrite(
                    os.path.join(animal_dir, f"{base_name}_noise.jpg"),
                    noisy
                )
                augmented += 1

            except Exception as e:
                print(f"  Error augmenting {img_name}: {e}")
                continue

        print(f"  Created {augmented} augmented images")
        return augmented

    @staticmethod
    def _rotate_image(image, angle):
        height, width = image.shape[:2]
        center = (width // 2, height // 2)
        matrix = cv2.getRotationMatrix2D(center, angle, 1.0)
        return cv2.warpAffine(image, matrix, (width, height))

    @staticmethod
    def _adjust_brightness(image, factor):
        hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
        hsv[:, :, 2] = np.clip(hsv[:, :, 2] * factor, 0, 255).astype(np.uint8)
        return cv2.cvtColor(hsv, cv2.COLOR_HSV2BGR)

    @staticmethod
    def _add_noise(image):
        noise = np.random.normal(0, 25, image.shape).astype(np.uint8)
        return cv2.add(image, noise)

    def build_dataset(self, images_per_class=200):
        """Main method to build complete dataset"""
        print("=" * 60)
        print("WILDTRACK AI - AUTOMATIC DATASET BUILDER")
        print("=" * 60)

        self.create_folders()

        total_downloaded = 0
        total_cleaned = 0
        total_augmented = 0

        for animal, search_terms in self.animals.items():
            print("\n" + "-" * 40)

            downloaded = self.download_images(animal, search_terms, images_per_class)
            total_downloaded += downloaded

            cleaned = self.clean_images(animal)
            total_cleaned += cleaned

            augmented = self.augment_dataset(animal)
            total_augmented += augmented

        print("\n" + "=" * 60)
        print("DATASET BUILD COMPLETE!")
        print("=" * 60)
        print(f"Total images downloaded: {total_downloaded}")
        print(f"Total invalid removed: {total_cleaned}")
        print(f"Total augmented created: {total_augmented}")
        print(f"Final dataset size: {total_downloaded - total_cleaned + total_augmented}")
        print("=" * 60)

        print("\nFolder Structure:")
        for animal in self.animals.keys():
            animal_dir = os.path.join(self.base_dir, animal)
            if os.path.exists(animal_dir):
                count = len([f for f in os.listdir(animal_dir)
                             if f.lower().endswith(('.jpg', '.jpeg', '.png'))])
                print(f"  {animal}: {count} images")


if __name__ == "__main__":
    builder = WildTrackDatasetBuilder()
    builder.build_dataset(images_per_class=200)
    print("\nDataset ready for training!")
    print("Next: Run python training/train.py")
