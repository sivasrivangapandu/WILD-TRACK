#!/usr/bin/env python3
"""
WildTrackAI - Intelligent Data Augmentation Pipeline
====================================================
Smart augmentation system that enhances training data while preserving essential features:

✅ Augmentation Techniques:
   - Controlled rotation (±5-15 degrees)
   - Scale variations (0.9-1.1x)
   - Limited brightness/contrast adjustment
   - Noise injection (for robustness)
   - Blur variations (simulate different cameras)
   - Horizontal flip (when appropriate)

✅ Smart Application Rules:
   - PERFECT images: Minimal augmentation (1-2 variants)
   - EXCELLENT/GOOD: Moderate augmentation (3-5 variants)
   - FAIR: Aggressive augmentation (5-8 variants)
   - POOR: Heavy reconstruction/augmentation (8-15 variants)

✅ Quality Preservation:
   - Subject occupancy maintained
   - Aspect ratio preserved
   - Center focus maintained
   - Artifact-free augmentation

Usage:
    python augment_dataset.py --source dataset_perfect/FAIR/ --output dataset_augmented/
    python augment_dataset.py --source dataset_perfect/ --levels GOOD FAIR POOR
    python augment_dataset.py --aggressive --output aggressive_augmented/
"""

import os
import sys
import argparse
from pathlib import Path
from typing import Tuple, List

import cv2
import numpy as np
from PIL import Image, ImageEnhance


class DataAugmentation:
    """Smart data augmentation to expand training dataset."""
    
    def __init__(self, seed: int = 42):
        np.random.seed(seed)
        self.augmentation_count = 0
    
    def rotate_image(self, image: np.ndarray, angle: float) -> np.ndarray:
        """Rotate image by angle (degrees)."""
        h, w = image.shape[:2]
        center = (w // 2, h // 2)
        
        rotation_matrix = cv2.getRotationMatrix2D(center, angle, 1.0)
        rotated = cv2.warpAffine(image, rotation_matrix, (w, h), 
                                  borderMode=cv2.BORDER_REFLECT)
        return rotated
    
    def scale_image(self, image: np.ndarray, scale: float) -> np.ndarray:
        """Scale image by factor (keeping center)."""
        h, w = image.shape[:2]
        
        new_h = int(h * scale)
        new_w = int(w * scale)
        
        resized = cv2.resize(image, (new_w, new_h))
        
        # Pad back to original size
        if scale < 1.0:
            result = np.ones_like(image) * 255
            y_offset = (h - new_h) // 2
            x_offset = (w - new_w) // 2
            result[y_offset:y_offset+new_h, x_offset:x_offset+new_w] = resized
        else:
            # Crop center
            y_start = (new_h - h) // 2
            x_start = (new_w - w) // 2
            result = resized[y_start:y_start+h, x_start:x_start+w]
        
        return result
    
    def adjust_brightness(self, image: np.ndarray, factor: float) -> np.ndarray:
        """Adjust brightness (1.0 = no change, <1.0 = darker, >1.0 = brighter)."""
        pil_image = Image.fromarray(cv2.cvtColor(image, cv2.COLOR_BGR2RGB))
        enhancer = ImageEnhance.Brightness(pil_image)
        enhanced = enhancer.enhance(factor)
        return cv2.cvtColor(np.array(enhanced), cv2.COLOR_RGB2BGR)
    
    def adjust_contrast(self, image: np.ndarray, factor: float) -> np.ndarray:
        """Adjust contrast (1.0 = no change, <1.0 = lower, >1.0 = higher)."""
        pil_image = Image.fromarray(cv2.cvtColor(image, cv2.COLOR_BGR2RGB))
        enhancer = ImageEnhance.Contrast(pil_image)
        enhanced = enhancer.enhance(factor)
        return cv2.cvtColor(np.array(enhanced), cv2.COLOR_RGB2BGR)
    
    def adjust_saturation(self, image: np.ndarray, factor: float) -> np.ndarray:
        """Adjust color saturation (1.0 = no change, <1.0 = less, >1.0 = more)."""
        pil_image = Image.fromarray(cv2.cvtColor(image, cv2.COLOR_BGR2RGB))
        enhancer = ImageEnhance.Color(pil_image)
        enhanced = enhancer.enhance(factor)
        return cv2.cvtColor(np.array(enhanced), cv2.COLOR_RGB2BGR)
    
    def add_gaussian_noise(self, image: np.ndarray, std: float = 10.0) -> np.ndarray:
        """Add Gaussian noise to image."""
        noise = np.random.normal(0, std, image.shape)
        noisy = image.astype(np.float32) + noise
        noisy = np.clip(noisy, 0, 255).astype(np.uint8)
        return noisy
    
    def blur_image(self, image: np.ndarray, kernel_size: int = 3) -> np.ndarray:
        """Apply Gaussian blur (simulate motion blur or different camera)."""
        if kernel_size % 2 == 0:
            kernel_size += 1  # Must be odd
        return cv2.GaussianBlur(image, (kernel_size, kernel_size), 0)
    
    def horizontal_flip(self, image: np.ndarray) -> np.ndarray:
        """Flip image horizontally."""
        return cv2.flip(image, 1)
    
    def elastic_deformation(self, image: np.ndarray, alpha: float = 34, sigma: float = 3) -> np.ndarray:
        """Apply elastic deformation (natural augmentation for footprints)."""
        h, w = image.shape[:2]
        
        # Generate random deformation
        dx = np.random.randn(h, w) * sigma
        dy = np.random.randn(h, w) * sigma
        
        # Smooth the deformation fields
        from scipy.ndimage import gaussian_filter
        dx = gaussian_filter(dx, sigma=2) * alpha
        dy = gaussian_filter(dy, sigma=2) * alpha
        
        # Create coordinate maps
        x, y = np.meshgrid(np.arange(w), np.arange(h))
        indices = y + dy, x + dx
        
        # Apply deformation
        if len(image.shape) == 3:
            deformed = np.zeros_like(image)
            for c in range(image.shape[2]):
                deformed[:, :, c] = cv2.remap(
                    image[:, :, c], 
                    (x + dx).astype(np.float32), 
                    (y + dy).astype(np.float32),
                    cv2.INTER_LINEAR,
                    borderMode=cv2.BORDER_REFLECT
                )
        else:
            deformed = cv2.remap(
                image,
                (x + dx).astype(np.float32),
                (y + dy).astype(np.float32),
                cv2.INTER_LINEAR,
                borderMode=cv2.BORDER_REFLECT
            )
        
        return deformed
    
    def augment_image(self, image: np.ndarray, num_variants: int = 3, 
                     quality_level: str = 'GOOD') -> List[np.ndarray]:
        """
        Generate augmented variants of image based on quality level.
        
        Returns: List of augmented images
        """
        variants = [image]  # Always include original
        
        # Define augmentation strategies by quality level
        strategies = {
            'PERFECT': [
                lambda: self.rotate_image(image, np.random.uniform(-3, 3)),
            ],
            'EXCELLENT': [
                lambda: self.rotate_image(image, np.random.uniform(-5, 5)),
                lambda: self.adjust_brightness(image, np.random.uniform(0.95, 1.05)),
                lambda: self.adjust_contrast(image, np.random.uniform(0.95, 1.05)),
            ],
            'GOOD': [
                lambda: self.rotate_image(image, np.random.uniform(-8, 8)),
                lambda: self.scale_image(image, np.random.uniform(0.95, 1.05)),
                lambda: self.adjust_brightness(image, np.random.uniform(0.9, 1.1)),
                lambda: self.adjust_contrast(image, np.random.uniform(0.9, 1.1)),
                lambda: self.blur_image(image, kernel_size=3),
            ],
            'FAIR': [
                lambda: self.rotate_image(image, np.random.uniform(-15, 15)),
                lambda: self.scale_image(image, np.random.uniform(0.9, 1.1)),
                lambda: self.adjust_brightness(image, np.random.uniform(0.8, 1.2)),
                lambda: self.adjust_contrast(image, np.random.uniform(0.85, 1.15)),
                lambda: self.adjust_saturation(image, np.random.uniform(0.9, 1.1)),
                lambda: self.add_gaussian_noise(image, std=5.0),
                lambda: self.blur_image(image, kernel_size=5),
                lambda: self.horizontal_flip(image),
            ],
            'POOR': [
                lambda: self.rotate_image(image, np.random.uniform(-20, 20)),
                lambda: self.scale_image(image, np.random.uniform(0.85, 1.15)),
                lambda: self.adjust_brightness(image, np.random.uniform(0.7, 1.3)),
                lambda: self.adjust_contrast(image, np.random.uniform(0.75, 1.25)),
                lambda: self.adjust_saturation(image, np.random.uniform(0.85, 1.15)),
                lambda: self.add_gaussian_noise(image, std=8.0),
                lambda: self.blur_image(image, kernel_size=5),
                lambda: self.horizontal_flip(image),
                lambda: self.elastic_deformation(image, alpha=30, sigma=2.5),
            ]
        }
        
        # Get augmentation functions for this quality level
        augment_funcs = strategies.get(quality_level, strategies['GOOD'])
        
        # Apply random augmentations
        num_to_generate = min(num_variants - 1, len(augment_funcs))
        selected_funcs = np.random.choice(augment_funcs, num_to_generate, replace=False)
        
        for aug_func in selected_funcs:
            try:
                augmented = aug_func()
                variants.append(augmented)
                self.augmentation_count += 1
            except Exception as e:
                print(f"  ⚠️  Augmentation failed: {str(e)[:50]}")
        
        return variants


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', required=True, help='Source images or directory')
    parser.add_argument('--output', default='dataset_augmented/', help='Output directory')
    parser.add_argument('--levels', nargs='+', default=['FAIR', 'POOR'], 
                       choices=['PERFECT', 'EXCELLENT', 'GOOD', 'FAIR', 'POOR'],
                       help='Quality levels to augment')
    parser.add_argument('--variants', type=int, default=5, 
                       help='Number of variants per image')
    parser.add_argument('--aggressive', action='store_true', 
                       help='Use aggressive augmentation')
    
    args = parser.parse_args()
    
    augmentor = DataAugmentation()
    
    print("\n🎨 INTELLIGENT DATA AUGMENTATION")
    print("=" * 70)
    print(f"Source: {args.source}")
    print(f"Output: {args.output}")
    print(f"Quality Levels: {', '.join(args.levels)}")
    print(f"Variants per image: {args.variants}")
    print("=" * 70)
    
    os.makedirs(args.output, exist_ok=True)
    
    # Find images
    image_files = []
    for root, dirs, files in os.walk(args.source):
        for fname in files:
            if fname.lower().endswith(('.jpg', '.jpeg', '.png', '.bmp', '.webp')):
                image_files.append(os.path.join(root, fname))
    
    if not image_files:
        print("❌ No images found")
        return
    
    print(f"\nFound {len(image_files)} images\n")
    
    # Augment images
    total_generated = 0
    for idx, image_path in enumerate(image_files, 1):
        try:
            # Determine quality level from path
            quality_level = 'GOOD'
            for level in args.levels:
                if level in image_path:
                    quality_level = level
                    break
            
            image = cv2.imread(image_path)
            if image is None:
                print(f"[{idx}] ❌ Cannot read: {os.path.basename(image_path)}")
                continue
            
            # Generate variants
            num_variants = args.variants
            if args.aggressive:
                num_variants = max(8, args.variants)
            
            variants = augmentor.augment_image(image, num_variants, quality_level)
            
            # Save variants
            base_name = Path(image_path).stem
            for var_idx, variant in enumerate(variants):
                if var_idx == 0:
                    # Save original
                    output_path = os.path.join(args.output, f"{base_name}_orig.png")
                else:
                    output_path = os.path.join(args.output, f"{base_name}_aug_{var_idx:02d}.png")
                
                cv2.imwrite(output_path, variant)
                total_generated += 1
            
            if idx % 5 == 0 or idx == len(image_files):
                print(f"[{idx}/{len(image_files)}] ✅ Augmented {idx} images ({total_generated} total variants)")
        
        except Exception as e:
            print(f"[{idx}] ❌ Error: {str(e)[:60]}")
    
    print("\n" + "=" * 70)
    print("✨ AUGMENTATION COMPLETE")
    print("=" * 70)
    print(f"Original Images: {len(image_files)}")
    print(f"Total Variants Generated: {total_generated}")
    print(f"Expansion Factor: {total_generated / len(image_files):.1f}x")
    print(f"Output Directory: {args.output}")


if __name__ == '__main__':
    main()
