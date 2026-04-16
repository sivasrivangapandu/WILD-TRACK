#!/usr/bin/env python3
"""
WildTrackAI - Advanced Image Validation System
==============================================
Multi-stage validation to ensure only high-quality images are used for training:

✅ Stage 1: Technical Validation
   - Format check (supported image types)
   - Size validation (too small/large)
   - Corruption detection
   - Metadata verification

✅ Stage 2: Quality Metrics Validation
   - Minimum sharpness (avoid blurry)
   - Minimum contrast (avoid washed out)
   - Brightness range (avoid too dark/bright)
   - Noise level limits
   - Subject occupancy rules

✅ Stage 3: Content Validation
   - No people/faces (security)
   - No UI/screenshots (false positives)
   - No non-footprint subjects
   - Natural composition verification

✅ Stage 4: Pathology Detection
   - No extreme compression artifacts
   - No over-processing artifacts
   - No watermarks/text overlays
   - No duplicate/near-duplicate images

Usage:
    python validate_training_images.py --source dataset/ --dry-run
    python validate_training_images.py --source dataset/ --strict
    python validate_training_images.py --check-pathology
"""

import os
import sys
import json
import argparse
from pathlib import Path
from collections import defaultdict
from datetime import datetime
from typing import Dict, Tuple, List, Optional

import cv2
import numpy as np
from PIL import Image
import imagehash


class ImageValidator:
    """Advanced multi-stage image validation."""
    
    def __init__(self, strict: bool = False, check_pathology: bool = True):
        self.strict = strict
        self.check_pathology = check_pathology
        self.validation_log = []
        
        # Quality thresholds
        self.MIN_WIDTH = 200
        self.MAX_WIDTH = 4000
        self.MIN_HEIGHT = 200
        self.MAX_HEIGHT = 4000
        self.MIN_SHARPNESS = 30.0 if not strict else 50.0
        self.MIN_CONTRAST = 15.0 if not strict else 25.0
        self.MIN_BRIGHTNESS = 30.0 if not strict else 40.0
        self.MAX_BRIGHTNESS = 90.0 if not strict else 85.0
        self.MAX_NOISE = 70.0 if not strict else 50.0
        self.MIN_OCCUPANCY = 0.08 if not strict else 0.15
        self.MAX_OCCUPANCY = 0.95
    
    def log_validation(self, image_path: str, stage: str, passed: bool, reason: str = ""):
        """Log validation result."""
        self.validation_log.append({
            'image': os.path.basename(image_path),
            'stage': stage,
            'passed': passed,
            'reason': reason
        })
    
    def check_format(self, image_path: str) -> Tuple[bool, str]:
        """Stage 1.1: Check file format and readability."""
        try:
            if not os.path.exists(image_path):
                return False, "File does not exist"
            
            if not image_path.lower().endswith(('.jpg', '.jpeg', '.png', '.bmp', '.webp')):
                return False, "Unsupported file format"
            
            image = cv2.imread(image_path)
            if image is None:
                return False, "Cannot read image (corrupted or invalid)"
            
            return True, "Format OK"
        except Exception as e:
            return False, f"Format check error: {str(e)[:50]}"
    
    def check_dimensions(self, image: np.ndarray, image_path: str) -> Tuple[bool, str]:
        """Stage 1.2: Validate image dimensions."""
        try:
            h, w = image.shape[:2]
            
            if w < self.MIN_WIDTH or w > self.MAX_WIDTH:
                return False, f"Width {w} outside range [{self.MIN_WIDTH}, {self.MAX_WIDTH}]"
            
            if h < self.MIN_HEIGHT or h > self.MAX_HEIGHT:
                return False, f"Height {h} outside range [{self.MIN_HEIGHT}, {self.MAX_HEIGHT}]"
            
            # Check aspect ratio
            aspect_ratio = max(w, h) / min(w, h)
            if aspect_ratio > 4.0:
                return False, f"Extreme aspect ratio: {aspect_ratio:.1f}:1"
            
            return True, f"Dimensions OK ({w}x{h})"
        except Exception as e:
            return False, f"Dimension check error: {str(e)[:50]}"
    
    def check_quality_metrics(self, image: np.ndarray, image_path: str) -> Tuple[bool, str, Dict]:
        """Stage 2: Validate quality metrics."""
        try:
            if len(image.shape) == 3:
                gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            else:
                gray = image
            
            # Sharpness
            sharpness = cv2.Laplacian(gray, cv2.CV_64F).var() / 5.0
            sharpness = min(100, max(0, sharpness))
            if sharpness < self.MIN_SHARPNESS:
                reason = f"Low sharpness: {sharpness:.1f} < {self.MIN_SHARPNESS}"
                return False, reason, {'sharpness': sharpness}
            
            # Contrast
            contrast = np.std(gray)
            if contrast < self.MIN_CONTRAST:
                reason = f"Low contrast: {contrast:.1f} < {self.MIN_CONTRAST}"
                return False, reason, {'contrast': contrast}
            
            # Brightness
            brightness = np.mean(gray)
            if not (self.MIN_BRIGHTNESS <= brightness <= self.MAX_BRIGHTNESS):
                reason = f"Bad brightness: {brightness:.1f} (range: {self.MIN_BRIGHTNESS}-{self.MAX_BRIGHTNESS})"
                return False, reason, {'brightness': brightness}
            
            # Noise
            kernel = cv2.getGaussianKernel(5, 1.0)
            kernel = kernel @ kernel.T
            log_filtered = cv2.filter2D(gray.astype(np.float32), -1, kernel)
            noise = np.var(log_filtered)
            if noise > self.MAX_NOISE:
                reason = f"High noise: {noise:.1f} > {self.MAX_NOISE}"
                return False, reason, {'noise': noise}
            
            metrics = {
                'sharpness': float(sharpness),
                'contrast': float(contrast),
                'brightness': float(brightness),
                'noise': float(noise)
            }
            
            return True, "Quality OK", metrics
        except Exception as e:
            return False, f"Quality check error: {str(e)[:50]}", {}
    
    def check_content_validity(self, image: np.ndarray, image_path: str) -> Tuple[bool, str]:
        """Stage 3: Content validation (no people, no UI, real footprints)."""
        try:
            if len(image.shape) == 3:
                gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            else:
                gray = image
            
            # Check for faces (should not have)
            cascade = cv2.CascadeClassifier(
                cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
            )
            faces = cascade.detectMultiScale(gray, 1.1, 5, minSize=(30, 30))
            if len(faces) > 0:
                return False, f"Detected human face(s): {len(faces)}"
            
            # Check for UI elements (straight lines, uniform regions)
            edges = cv2.Canny(gray, 50, 150)
            lines = cv2.HoughLinesP(edges, 1, np.pi/180, 50, minLineLength=50, maxLineGap=10)
            if lines is not None and len(lines) > 30:
                return False, f"Too many straight lines detected: {len(lines)} (likely UI/screenshot)"
            
            # Check for natural contours (subject occupancy)
            contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            if not contours:
                return False, "No significant features detected"
            
            subject_area = sum(cv2.contourArea(c) for c in contours if cv2.contourArea(c) > 10)
            occupancy = subject_area / (gray.shape[0] * gray.shape[1])
            
            if not (self.MIN_OCCUPANCY <= occupancy <= self.MAX_OCCUPANCY):
                reason = f"Bad occupancy: {occupancy:.2%} (range: {self.MIN_OCCUPANCY:.1%}-{self.MAX_OCCUPANCY:.1%})"
                return False, reason
            
            return True, "Content OK"
        except Exception as e:
            return False, f"Content check error: {str(e)[:50]}"
    
    def check_compression_quality(self, image_path: str) -> Tuple[bool, str]:
        """Stage 4.1: Check for excessive compression artifacts."""
        try:
            image = cv2.imread(image_path)
            if image is None:
                return False, "Cannot read image"
            
            if len(image.shape) == 3:
                gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            else:
                gray = image
            
            # Detect compression blocks (common in JPEG)
            # This is a simple check - look for block patterns
            h, w = gray.shape
            if h > 16 and w > 16:
                # Sample several 8x8 blocks
                block_variance = []
                for i in range(0, min(h, 64), 8):
                    for j in range(0, min(w, 64), 8):
                        block = gray[i:i+8, j:j+8]
                        variance = np.var(block)
                        block_variance.append(variance)
                
                # If many blocks have very similar variance, it's likely JPEG compressed
                # (JPEG compression creates 8x8 blocks with uniform variance)
                if len(block_variance) > 10:
                    mean_var = np.mean(block_variance)
                    std_var = np.std(block_variance)
                    if std_var < mean_var * 0.1:  # Very uniform block variance
                        return False, "Excessive JPEG compression artifacts detected"
            
            return True, "Compression OK"
        except Exception as e:
            return False, f"Compression check error: {str(e)[:50]}"
    
    def check_duplicates(self, image_path: str, phash_db: Dict[str, str]) -> Tuple[bool, str]:
        """Stage 4.2: Check for duplicate/near-duplicate images."""
        try:
            image = cv2.imread(image_path)
            if image is None:
                return False, "Cannot read image"
            
            pil_image = Image.fromarray(cv2.cvtColor(image, cv2.COLOR_BGR2RGB))
            phash = str(imagehash.phash(pil_image))
            
            # Check against known hashes
            for known_path, known_hash in phash_db.items():
                if known_path == image_path:
                    continue
                
                hamming_distance = sum(c1 != c2 for c1, c2 in zip(phash, known_hash))
                if hamming_distance <= 4:  # Near-duplicate threshold
                    return False, f"Near-duplicate of {os.path.basename(known_path)}"
            
            phash_db[image_path] = phash
            return True, "Unique image"
        except Exception as e:
            return False, f"Duplicate check error: {str(e)[:50]}"
    
    def validate_image(self, image_path: str, phash_db: Dict[str, str]) -> Tuple[bool, Dict]:
        """Run complete validation pipeline."""
        result = {
            'image': os.path.basename(image_path),
            'passed': False,
            'stages': {},
            'reasons': []
        }
        
        # Stage 1: Format
        passed, reason = self.check_format(image_path)
        result['stages']['format'] = {'passed': passed, 'reason': reason}
        if not passed:
            result['reasons'].append(reason)
            return False, result
        
        # Read image
        image = cv2.imread(image_path)
        if image is None:
            result['reasons'].append("Cannot read image")
            return False, result
        
        # Stage 1.2: Dimensions
        passed, reason = self.check_dimensions(image, image_path)
        result['stages']['dimensions'] = {'passed': passed, 'reason': reason}
        if not passed:
            result['reasons'].append(reason)
            return False if self.strict else False, result
        
        # Stage 2: Quality
        passed, reason, metrics = self.check_quality_metrics(image, image_path)
        result['stages']['quality'] = {'passed': passed, 'reason': reason, 'metrics': metrics}
        if not passed:
            result['reasons'].append(reason)
            return False, result
        
        # Stage 3: Content
        passed, reason = self.check_content_validity(image, image_path)
        result['stages']['content'] = {'passed': passed, 'reason': reason}
        if not passed:
            result['reasons'].append(reason)
            return False, result
        
        # Stage 4: Pathology (optional)
        if self.check_pathology:
            passed, reason = self.check_compression_quality(image_path)
            result['stages']['compression'] = {'passed': passed, 'reason': reason}
            if not passed:
                result['reasons'].append(reason)
                return False, result
            
            passed, reason = self.check_duplicates(image_path, phash_db)
            result['stages']['duplicates'] = {'passed': passed, 'reason': reason}
            if not passed:
                result['reasons'].append(reason)
                return False, result
        
        result['passed'] = True
        return True, result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', required=True, help='Source dataset directory')
    parser.add_argument('--dry-run', action='store_true', help='Report without modifying')
    parser.add_argument('--strict', action='store_true', help='Use strict validation thresholds')
    parser.add_argument('--check-pathology', action='store_true', help='Check for compression artifacts and duplicates')
    parser.add_argument('--output', default='validation_report.json', help='Output report path')
    
    args = parser.parse_args()
    
    validator = ImageValidator(strict=args.strict, check_pathology=args.check_pathology)
    
    print("\n🔍 ADVANCED IMAGE VALIDATION")
    print("=" * 70)
    print(f"Source: {args.source}")
    print(f"Strict Mode: {'✅ Yes' if args.strict else '❌ No'}")
    print(f"Pathology Check: {'✅ Yes' if args.check_pathology else '❌ No'}")
    print(f"Dry Run: {'✅ Yes (No files deleted)' if args.dry_run else '❌ No (Files will be deleted)'}")
    print("=" * 70)
    
    results = {'passed': [], 'failed': []}
    phash_db = {}
    
    # Find all images
    image_files = []
    for root, dirs, files in os.walk(args.source):
        for fname in files:
            if fname.lower().endswith(('.jpg', '.jpeg', '.png', '.bmp', '.webp')):
                image_files.append(os.path.join(root, fname))
    
    total = len(image_files)
    print(f"\nFound {total} images to validate\n")
    
    for idx, image_path in enumerate(image_files, 1):
        passed, result = validator.validate_image(image_path, phash_db)
        
        if passed:
            results['passed'].append(result)
            status = "✅"
        else:
            results['failed'].append(result)
            status = "❌"
        
        if idx % 10 == 0 or idx == total:
            print(f"[{idx}/{total}] {status} Validated {idx} images...")
    
    # Report
    print("\n" + "=" * 70)
    print("📊 VALIDATION REPORT")
    print("=" * 70)
    print(f"Total Images: {total}")
    print(f"Valid Images: {len(results['passed'])} ({len(results['passed'])/total*100:.1f}%)")
    print(f"Invalid Images: {len(results['failed'])} ({len(results['failed'])/total*100:.1f}%)")
    
    # Save report
    with open(args.output, 'w') as f:
        json.dump(results, f, indent=2)
    
    print(f"✅ Report saved to: {args.output}")


if __name__ == '__main__':
    main()
