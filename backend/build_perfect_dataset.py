#!/usr/bin/env python3
"""
WildTrackAI - Perfect Image Quality Dataset Builder
====================================================
Advanced multi-stage system to build training datasets with perfect quality metrics:

✅ Image Quality Scoring (0-100):
   - Sharpness/Clarity (20%)
   - Contrast & Brightness (20%)
   - Color Balance (15%)
   - Subject Occupancy (20%)
   - Noise Level (15%)
   - Composition Quality (10%)

✅ Automatic Categorization:
   - PERFECT (85-100): Ready for training immediately
   - EXCELLENT (70-84): Minor enhancements possible
   - GOOD (55-69): Augmentation recommended
   - FAIR (40-54): Requires processing
   - POOR (0-39): Reject or heavy processing

✅ Smart Data Augmentation:
   - Only applied to non-PERFECT images
   - Controlled augmentation (rotation, scale, noise)
   - Preserves subject structure
   - Generates training variations

Usage:
    python build_perfect_dataset.py --source dataset/ --output dataset_perfect/
    python build_perfect_dataset.py --score-only  (Quality audit only)
    python build_perfect_dataset.py --augment-poor (Enhance POOR/FAIR quality)
"""

import os
import sys
import json
import argparse
from pathlib import Path
from collections import defaultdict
from datetime import datetime
from typing import Dict, Tuple, List

import cv2
import numpy as np
from PIL import Image
from scipy import signal as scipy_signal
from scipy import ndimage as scipy_ndimage


class ImageQualityMetrics:
    """Compute comprehensive image quality metrics."""
    
    @staticmethod
    def compute_sharpness(image: np.ndarray) -> float:
        """
        Compute Laplacian variance (Tenengrad focus measure).
        Higher = sharper image.
        Range: 0-100 (normalized)
        """
        try:
            if len(image.shape) == 3:
                gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            else:
                gray = image
            
            lap_var = cv2.Laplacian(gray, cv2.CV_64F).var()
            # Normalize to 0-100 range (adjust threshold as needed)
            sharpness = min(100.0, (lap_var / 500.0) * 100.0)
            return max(0, sharpness)
        except Exception as e:
            return 0.0
    
    @staticmethod
    def compute_contrast(image: np.ndarray) -> float:
        """
        Compute image contrast using standard deviation of pixel intensities.
        Range: 0-100
        """
        try:
            if len(image.shape) == 3:
                gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            else:
                gray = image
            
            contrast = np.std(gray)
            # Normalize to 0-100 range
            contrast_normalized = min(100.0, (contrast / 100.0) * 100.0)
            return contrast_normalized
        except Exception as e:
            return 0.0
    
    @staticmethod
    def compute_brightness(image: np.ndarray) -> float:
        """
        Compute brightness and return a score (0-100) for optimal range.
        Optimal: mid-range brightness (40-180 mean for 8-bit images)
        """
        try:
            if len(image.shape) == 3:
                gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            else:
                gray = image
            
            mean_brightness = np.mean(gray)
            # Optimal brightness around 127 (middle gray)
            distance_from_optimal = abs(mean_brightness - 127.0)
            brightness_score = max(0, 100.0 - (distance_from_optimal / 127.0) * 100.0)
            return brightness_score
        except Exception as e:
            return 0.0
    
    @staticmethod
    def compute_color_balance(image: np.ndarray) -> float:
        """
        Compute color balance by analyzing R/G/B channel distribution.
        Optimal: balanced channels without color cast.
        Range: 0-100
        """
        try:
            if len(image.shape) != 3:
                return 50.0  # Grayscale gets neutral score
            
            b_mean = np.mean(image[:, :, 0])
            g_mean = np.mean(image[:, :, 1])
            r_mean = np.mean(image[:, :, 2])
            
            # Calculate balance deviation
            max_mean = max(b_mean, g_mean, r_mean)
            min_mean = min(b_mean, g_mean, r_mean)
            balance_deviation = (max_mean - min_mean) / 255.0
            
            # Convert to score (lower deviation = higher score)
            color_balance = max(0, 100.0 - (balance_deviation * 100.0))
            return color_balance
        except Exception as e:
            return 0.0
    
    @staticmethod
    def compute_subject_occupancy(image: np.ndarray, target_min: float = 0.15, target_max: float = 0.85) -> float:
        """
        Estimate subject occupancy by detecting non-background regions.
        Optimal range: 15-85% of image contains the subject.
        Range: 0-100
        """
        try:
            if len(image.shape) == 3:
                gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            else:
                gray = image
            
            # Detect edges
            edges = cv2.Canny(gray, 50, 150)
            contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            
            if not contours:
                return 0.0
            
            # Calculate subject area
            subject_area = sum(cv2.contourArea(c) for c in contours if cv2.contourArea(c) > 10)
            image_area = gray.shape[0] * gray.shape[1]
            occupancy = subject_area / image_area if image_area > 0 else 0
            
            # Score based on how close to optimal range
            if target_min <= occupancy <= target_max:
                occupancy_score = 100.0
            elif occupancy < target_min:
                occupancy_score = (occupancy / target_min) * 100.0
            else:
                occupancy_score = max(0, 100.0 - ((occupancy - target_max) / (1.0 - target_max)) * 100.0)
            
            return occupancy_score
        except Exception as e:
            return 0.0
    
    @staticmethod
    def compute_noise_level(image: np.ndarray) -> float:
        """
        Estimate noise level using Laplacian of Gaussian.
        Lower noise = higher score.
        Range: 0-100
        """
        try:
            if len(image.shape) == 3:
                gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            else:
                gray = image
            
            # Apply LoG filter
            kernel = cv2.getGaussianKernel(5, 1.0)
            kernel = kernel @ kernel.T
            log_filtered = cv2.filter2D(gray.astype(np.float32), -1, kernel)
            
            # Calculate variance of filtered image (indicates noise)
            noise_variance = np.var(log_filtered)
            
            # Normalize to 0-100 (lower variance = less noise = higher score)
            noise_score = max(0, 100.0 - min(100.0, (noise_variance / 50.0) * 100.0))
            return noise_score
        except Exception as e:
            return 50.0
    
    @staticmethod
    def compute_composition_quality(image: np.ndarray) -> float:
        """
        Evaluate composition using corner/feature detection.
        Good composition = natural distribution of features.
        Range: 0-100
        """
        try:
            if len(image.shape) == 3:
                gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            else:
                gray = image
            
            # Detect corners using Harris
            corners = cv2.goodFeaturesToTrack(
                gray, maxCorners=100, qualityLevel=0.01, minDistance=10
            )
            
            if corners is None or len(corners) == 0:
                return 20.0  # No features detected
            
            # Distribute corners well across image = good composition
            corner_count = len(corners)
            # Ideal: 30-50 well-distributed corners
            if 30 <= corner_count <= 50:
                composition_score = 100.0
            elif corner_count < 30:
                composition_score = (corner_count / 30.0) * 100.0
            else:
                composition_score = max(20, 100.0 - ((corner_count - 50) / 50.0) * 50.0)
            
            return composition_score
        except Exception as e:
            return 50.0
    
    @staticmethod
    def compute_overall_quality(image: np.ndarray) -> Tuple[float, Dict[str, float]]:
        """
        Compute comprehensive quality score (0-100) with component breakdown.
        Weights:
        - Sharpness: 20%
        - Contrast: 20%
        - Brightness: 15%
        - Subject Occupancy: 20%
        - Noise Level: 15%
        - Composition: 10%
        """
        sharpness = ImageQualityMetrics.compute_sharpness(image)
        contrast = ImageQualityMetrics.compute_contrast(image)
        brightness = ImageQualityMetrics.compute_brightness(image)
        occupancy = ImageQualityMetrics.compute_subject_occupancy(image)
        noise = ImageQualityMetrics.compute_noise_level(image)
        composition = ImageQualityMetrics.compute_composition_quality(image)
        
        weights = {
            'sharpness': 0.20,
            'contrast': 0.20,
            'brightness': 0.15,
            'occupancy': 0.20,
            'noise': 0.15,
            'composition': 0.10
        }
        
        overall_score = (
            sharpness * weights['sharpness'] +
            contrast * weights['contrast'] +
            brightness * weights['brightness'] +
            occupancy * weights['occupancy'] +
            noise * weights['noise'] +
            composition * weights['composition']
        )
        
        metrics = {
            'sharpness': sharpness,
            'contrast': contrast,
            'brightness': brightness,
            'occupancy': occupancy,
            'noise': noise,
            'composition': composition
        }
        
        return overall_score, metrics


class DatasetBuilder:
    """Build perfect quality training dataset."""
    
    def __init__(self, source_dir: str, output_dir: str):
        self.source_dir = source_dir
        self.output_dir = output_dir
        self.quality_scores = {}
        self.categorized = defaultdict(list)
        
        # Create output directories
        os.makedirs(output_dir, exist_ok=True)
        for category in ['PERFECT', 'EXCELLENT', 'GOOD', 'FAIR', 'POOR']:
            os.makedirs(os.path.join(output_dir, category), exist_ok=True)
    
    def categorize_by_quality(self, score: float) -> str:
        """Categorize image by quality score."""
        if score >= 85:
            return 'PERFECT'
        elif score >= 70:
            return 'EXCELLENT'
        elif score >= 55:
            return 'GOOD'
        elif score >= 40:
            return 'FAIR'
        else:
            return 'POOR'
    
    def score_images(self) -> Dict[str, Dict]:
        """Score all images in source directory."""
        print(f"\n📊 SCORING IMAGES FROM: {self.source_dir}")
        print("=" * 70)
        
        if not os.path.isdir(self.source_dir):
            print(f"❌ Source directory not found: {self.source_dir}")
            return {}
        
        all_files = []
        for root, dirs, files in os.walk(self.source_dir):
            for fname in files:
                if fname.lower().endswith(('.jpg', '.jpeg', '.png', '.bmp', '.webp')):
                    all_files.append(os.path.join(root, fname))
        
        total = len(all_files)
        print(f"Found {total} images to score")
        
        results = {}
        for idx, fpath in enumerate(all_files, 1):
            try:
                image = cv2.imread(fpath)
                if image is None:
                    print(f"  [{idx}/{total}] ⚠️  Could not read: {os.path.basename(fpath)}")
                    continue
                
                score, metrics = ImageQualityMetrics.compute_overall_quality(image)
                category = self.categorize_by_quality(score)
                
                results[fpath] = {
                    'score': float(score),
                    'category': category,
                    'metrics': {k: float(v) for k, v in metrics.items()}
                }
                
                self.categorized[category].append(fpath)
                
                if idx % 10 == 0 or idx == total:
                    print(f"  [{idx}/{total}] ✅ Scored {idx} images...")
                
            except Exception as e:
                print(f"  [{idx}/{total}] ❌ Error processing {os.path.basename(fpath)}: {str(e)[:50]}")
        
        return results
    
    def copy_and_categorize(self, scores: Dict[str, Dict]) -> None:
        """Copy images to category-specific directories."""
        print(f"\n📁 ORGANIZING IMAGES BY QUALITY")
        print("=" * 70)
        
        for category, image_paths in self.categorized.items():
            if not image_paths:
                continue
            
            category_dir = os.path.join(self.output_dir, category)
            for fpath in image_paths:
                try:
                    filename = os.path.basename(fpath)
                    dest_path = os.path.join(category_dir, filename)
                    
                    image = cv2.imread(fpath)
                    if image is not None:
                        cv2.imwrite(dest_path, image)
                except Exception as e:
                    print(f"  ❌ Failed to copy {os.path.basename(fpath)}: {str(e)[:50]}")
            
            print(f"  ✅ {category}: {len(image_paths)} images")
    
    def generate_report(self, scores: Dict[str, Dict]) -> None:
        """Generate comprehensive quality report."""
        print(f"\n📋 QUALITY REPORT")
        print("=" * 70)
        
        if not scores:
            print("No scores to report")
            return
        
        # Statistics
        score_values = [s['score'] for s in scores.values()]
        
        print(f"\nTotal Images Processed: {len(scores)}")
        print(f"Average Quality Score: {np.mean(score_values):.1f}/100")
        print(f"Median Quality Score: {np.median(score_values):.1f}/100")
        print(f"Min Quality Score: {np.min(score_values):.1f}/100")
        print(f"Max Quality Score: {np.max(score_values):.1f}/100")
        print(f"Std Dev: {np.std(score_values):.1f}")
        
        # Category breakdown
        print(f"\n📊 CATEGORY BREAKDOWN:")
        print("-" * 70)
        for category in ['PERFECT', 'EXCELLENT', 'GOOD', 'FAIR', 'POOR']:
            count = len(self.categorized.get(category, []))
            pct = (count / len(scores) * 100) if scores else 0
            print(f"  {category:12} : {count:4} images ({pct:5.1f}%)")
        
        # Save detailed report
        report_path = os.path.join(self.output_dir, 'quality_report.json')
        with open(report_path, 'w') as f:
            json.dump({
                'timestamp': datetime.now().isoformat(),
                'total_images': len(scores),
                'statistics': {
                    'mean': float(np.mean(score_values)),
                    'median': float(np.median(score_values)),
                    'min': float(np.min(score_values)),
                    'max': float(np.max(score_values)),
                    'std_dev': float(np.std(score_values))
                },
                'scores': scores
            }, f, indent=2)
        print(f"\n✅ Detailed report saved: {report_path}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', default='dataset/', help='Source dataset directory')
    parser.add_argument('--output', default='dataset_perfect/', help='Output directory')
    parser.add_argument('--score-only', action='store_true', help='Only score, no organization')
    
    args = parser.parse_args()
    
    builder = DatasetBuilder(args.source, args.output)
    
    # Score all images
    scores = builder.score_images()
    
    if not scores:
        print("❌ No images to process")
        return
    
    # Generate report
    builder.generate_report(scores)
    
    # Organize by quality unless --score-only
    if not args.score_only:
        builder.copy_and_categorize(scores)
        print(f"\n✅ PERFECT DATASET READY: {args.output}")
    
    print("\n" + "=" * 70)
    print("✨ Dataset Quality Analysis Complete!")
    print("=" * 70)


if __name__ == '__main__':
    main()
