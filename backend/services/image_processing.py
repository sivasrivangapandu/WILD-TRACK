"""
WildTrackAI — Image Processing Service
========================================
Blur detection, quality warnings, contrast normalization,
edge enhancement, brightness correction, and preprocessing pipeline.
"""

import numpy as np
import cv2
import tensorflow as tf

from config import IMG_SIZE
from pipeline import pipeline


# ── Blur Detection ─────────────────────────────────────────────────

def detect_blur(image, threshold=100):
    """Detect image blurriness using Laplacian variance method.

    Returns:
        - blur_level: float (0-100, higher = sharper)
        - is_blurry: bool (True if blur_level < threshold)
    """
    if len(image.shape) == 3:
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    else:
        gray = image

    laplacian_var = cv2.Laplacian(gray, cv2.CV_64F).var()
    blur_level = min(100, max(0, laplacian_var / 5.0))
    is_blurry = blur_level < threshold

    return blur_level, is_blurry


def generate_quality_warning(blur_level):
    """Generate actionable quality warnings based on blur detection.

    Returns:
        - warning: str or None (human-readable message)
        - severity: str ('none', 'caution', 'warning')
    """
    if blur_level >= 75:
        return None, 'none'
    elif blur_level >= 60:
        return (
            "Image clarity is moderate. Footprint features are visible but soft. "
            "If possible, retake from directly above with stronger lighting.",
            'caution'
        )
    elif blur_level >= 45:
        return (
            "Image is significantly blurry. Footprint edge definition is limited. "
            "Classification confidence may be unreliable--field validation recommended.",
            'warning'
        )
    else:
        return (
            "Image is severely blurry or out of focus. Footprint structure is unclear. "
            "Please retake the image. Classification should NOT be trusted without field verification.",
            'critical'
        )


# ── Image Enhancement Utilities ────────────────────────────────────

def normalize_contrast(image):
    """Apply CLAHE (Contrast Limited Adaptive Histogram Equalization)."""
    if len(image.shape) == 3:
        lab = cv2.cvtColor(image, cv2.COLOR_BGR2LAB)
        l_channel = lab[:, :, 0]
        clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
        l_channel_clahe = clahe.apply(l_channel)
        lab[:, :, 0] = l_channel_clahe
        image = cv2.cvtColor(lab, cv2.COLOR_LAB2BGR)
    else:
        clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
        image = clahe.apply(image)
    return image


def enhance_edges(image):
    """Enhance footprint edges using unsharp masking."""
    if len(image.shape) == 3:
        for i in range(3):
            channel = image[:, :, i]
            channel_blurred = cv2.GaussianBlur(channel, (5, 5), 1.0)
            image[:, :, i] = cv2.addWeighted(channel, 1.4, channel_blurred, -0.4, 0)
    else:
        blurred = cv2.GaussianBlur(image, (5, 5), 1.0)
        image = cv2.addWeighted(image, 1.4, blurred, -0.4, 0)
    image = np.clip(image, 0, 255).astype(np.uint8)
    return image


def correct_brightness_gamma(image):
    """Adaptive brightness and gamma correction for dark/low-contrast images."""
    if len(image.shape) == 3 and image.shape[2] == 3:
        lab = cv2.cvtColor(image, cv2.COLOR_BGR2LAB)
        l_channel = lab[:, :, 0].astype(np.float32)
    else:
        l_channel = (
            image.astype(np.float32) if len(image.shape) == 2
            else cv2.cvtColor(image, cv2.COLOR_BGR2GRAY).astype(np.float32)
        )

    mean_luminance = np.mean(l_channel)

    gamma_applied = False
    if mean_luminance < 85:
        gamma = 1.8
        gamma_applied = True
    elif mean_luminance < 100:
        gamma = 1.5
        gamma_applied = True
    elif mean_luminance < 115:
        gamma = 1.2
        gamma_applied = True
    else:
        gamma = 1.0

    if gamma_applied:
        l_channel = np.power(l_channel / 255.0, 1.0 / gamma) * 255.0
        l_channel = np.clip(l_channel, 0, 255).astype(np.uint8)
        if len(image.shape) == 3 and image.shape[2] == 3:
            lab[:, :, 0] = l_channel
            image = cv2.cvtColor(lab, cv2.COLOR_LAB2BGR)
        else:
            image = l_channel

    return image, gamma_applied


def intelligent_resize(image, target_size=300):
    """Resize image intelligently while preserving aspect ratio."""
    h, w = image.shape[:2]
    aspect_ratio = w / h

    if aspect_ratio > 1:
        new_w = target_size
        new_h = int(target_size / aspect_ratio)
    else:
        new_h = target_size
        new_w = int(target_size * aspect_ratio)

    resized = cv2.resize(image, (new_w, new_h), interpolation=cv2.INTER_CUBIC)

    canvas = np.full(
        (target_size, target_size, 3 if len(image.shape) == 3 else 1),
        128, dtype=np.uint8
    )

    offset_h = (target_size - new_h) // 2
    offset_w = (target_size - new_w) // 2

    if len(image.shape) == 3:
        canvas[offset_h:offset_h + new_h, offset_w:offset_w + new_w, :] = resized
    else:
        canvas[offset_h:offset_h + new_h, offset_w:offset_w + new_w] = resized

    return canvas


# ── Main Preprocessing Pipeline ───────────────────────────────────

def preprocess_image(file_bytes, target_size=None, expansion_margin=0.15):
    """Preprocess uploaded image to EXACTLY match the training pipeline.

    Pipeline (matches training):
    1. Decode image from bytes
    2. Collect quality metrics (blur, pHash) for UI — does NOT modify the image
    3. Convert BGR → RGB (OpenCV decodes BGR, TF trained on RGB)
    4. Resize to target_size × target_size (simple resize, no padding)
    5. Cast to float32 [0, 255]

    Returns:
        - img_array: preprocessed image (1, H, W, 3) float32 RGB
        - original: original decoded image (BGR, for GradCAM/display)
        - quality_metrics: dict with blur_level, is_blurry, phash
        - stage1_meta: dict with YOLO cropping results (if available)
    """
    if target_size is None:
        target_size = IMG_SIZE

    # Decode image (OpenCV gives BGR)
    nparr = np.frombuffer(file_bytes, np.uint8)
    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    if img is None:
        raise ValueError("Cannot decode image")

    original = img.copy()

    # Quality metrics (for UI display only — does NOT modify the image)
    quality_metrics = {}

    # Perceptual hash
    phash = pipeline.generate_phash(img)
    quality_metrics['phash'] = phash
    quality_metrics['is_duplicate'] = pipeline.check_duplicate(phash)

    # Detect blur
    blur_level, is_blurry = pipeline.detect_blur(img)
    quality_metrics['blur_level'] = float(blur_level)
    quality_metrics['is_blurry'] = bool(is_blurry)

    # Brightness (for snow-track heuristic)
    if len(img.shape) == 3:
        lab = cv2.cvtColor(img, cv2.COLOR_BGR2LAB)
        brightness = np.mean(lab[:, :, 0])
    else:
        brightness = np.mean(img)
    quality_metrics['brightness'] = float(brightness)

    # Generate quality warning
    warning_msg, warning_severity = generate_quality_warning(blur_level)
    if warning_msg:
        quality_metrics['quality_warning'] = warning_msg
        quality_metrics['quality_severity'] = warning_severity

    quality_metrics['gamma_applied'] = False
    quality_metrics['processing_applied'] = False

    # Stage 1: YOLO Object Detection & Crop
    img, stage1_meta = pipeline.stage1_detect_and_crop(img, expansion_margin=expansion_margin)

    # Match training pipeline exactly
    img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)

    # Letterbox Resize to maintain aspect ratio
    old_h, old_w = img_rgb.shape[:2]
    ratio = float(target_size) / max(old_h, old_w)
    new_h, new_w = int(old_h * ratio), int(old_w * ratio)

    rsz = cv2.resize(img_rgb, (new_w, new_h), interpolation=cv2.INTER_CUBIC)

    # Create target canvas and center the image
    img_padded = np.full((target_size, target_size, 3), 127, dtype=np.uint8)
    y_offset = (target_size - new_h) // 2
    x_offset = (target_size - new_w) // 2
    img_padded[y_offset:y_offset + new_h, x_offset:x_offset + new_w] = rsz

    # Convert to tensor for consistency
    img_tensor = tf.convert_to_tensor(img_padded, dtype=tf.float32)
    img_array = img_tensor.numpy()
    img_array = np.expand_dims(img_array, axis=0)

    import sys
    sys.stdout.flush()

    return img_array, original, quality_metrics, stage1_meta
