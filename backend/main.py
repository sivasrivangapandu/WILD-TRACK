"""
WildTrackAI - Phase 5: Production FastAPI Backend
==================================================
SQLite database with SQLAlchemy for prediction history.
Full REST API with health checks, analytics, and batch processing.
Model loaded once at startup. GradCAM integrated.

Endpoints:
    POST /predict          - Single image prediction
    POST /predict/batch    - Batch prediction
    GET  /species          - List all species
    GET  /species/{name}   - Species details
    GET  /history          - Prediction history
    GET  /analytics        - Dashboard analytics
    GET  /model-metrics    - Model performance metrics
    GET  /health           - Health check

Usage:
    python main.py
    uvicorn main:app --host 0.0.0.0 --port 8000
"""

import os
import sys
import json
import uuid
import base64
import shutil
import datetime
from pathlib import Path
from typing import List, Optional
from contextlib import asynccontextmanager

import numpy as np
import cv2
from PIL import Image
from dotenv import load_dotenv

from fastapi import FastAPI, UploadFile, File, Form, HTTPException, BackgroundTasks, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse, Response
from pydantic import BaseModel
import uvicorn

# Google Gemini AI
import google.generativeai as genai

from database import SessionLocal, init_db, DB_PATH
from models import Prediction

# Chat streaming and database routes
from routes import chat_router, chat_db_router, auth_router

# ============================================
# CONFIGURATION
# ============================================
load_dotenv()
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MODELS_DIR = os.path.join(BASE_DIR, "models")
UPLOADS_DIR = os.path.join(BASE_DIR, "uploads")
OUTPUTS_DIR = os.path.join(BASE_DIR, "outputs")
# SQLite path is configured in database.py

from pipeline import pipeline
from consensus import compute_consensus

# Model files (order: .keras first, then .h5 variants)
MODEL_PATH_KERAS = os.path.join(MODELS_DIR, "wildtrack_v4_cpu.keras")
MODEL_PATH = os.path.join(MODELS_DIR, "wildtrack_complete_model.h5")
MODEL_PATH_LEGACY = os.path.join(MODELS_DIR, "wildtrack_final.h5")
MODEL_PATH_V4 = os.path.join(MODELS_DIR, "wildtrack_v4.h5")
MODEL_PATH_V3 = os.path.join(MODELS_DIR, "wildtrack_v3_b3.h5")
METADATA_PATH = os.path.join(MODELS_DIR, "model_metadata.json")

# Default image size (overridden by metadata if available)
IMG_SIZE = 300

# Confidence threshold — below this, prediction is "unknown"
CONFIDENCE_THRESHOLD = 0.40

# Gemini AI Configuration
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
gemini_model = None
if GEMINI_API_KEY:
    try:
        genai.configure(api_key=GEMINI_API_KEY)
        gemini_model = genai.GenerativeModel("gemini-2.0-flash")
        print(f"  ✅ Gemini AI initialized (gemini-2.0-flash)")
    except Exception as e:
        print(f"  ⚠️ Gemini init failed: {e} — falling back to rule-based chat")
else:
    print("  ⚠️ No GEMINI_API_KEY found — using rule-based chat")

# API Ninjas Configuration
NINJA_API_KEY = os.getenv("NINJA_API_KEY", "")
if NINJA_API_KEY:
    print(f"  ✅ API Ninjas initialized")
else:
    print("  ⚠️ No NINJA_API_KEY found — animal search will be unavailable")

# Create directories
for d in [UPLOADS_DIR, OUTPUTS_DIR]:
    os.makedirs(d, exist_ok=True)

# ============================================
# DATABASE INITIALIZATION
# ============================================
init_db()

# ============================================
# MODEL LOADING
# ============================================
model = None
model_metadata = {}
class_names = []
gradcam = None
model_load_diagnostics = {
    "loaded_from": None,
    "attempted": [],
    "error": None,
}

# ============================================
# MODEL DOWNLOAD (for cloud deployment)
# ============================================
MODEL_URLS = {
    "wildtrack_v4_cpu.keras": "https://github.com/sivasrivangapandu/WILD-TRACK/releases/download/v2.0-models/wildtrack_v4_cpu.keras",
    "wildtrack_complete_model.h5": "https://github.com/sivasrivangapandu/WILD-TRACK/releases/download/v2.0-models/wildtrack_complete_model.h5",
    "wildtrack_final.h5": "https://github.com/sivasrivangapandu/WILD-TRACK/releases/download/v2.0-models/wildtrack_final.h5",
}

model_download_status = {"status": "pending", "downloaded": [], "failed": []}


def download_models_if_missing():
    """Download model files from GitHub Release if not present locally."""
    import requests as req
    from time import sleep
    
    global model_download_status
    model_download_status["status"] = "downloading"
    
    for filename, url in MODEL_URLS.items():
        filepath = os.path.join(MODELS_DIR, filename)
        if os.path.exists(filepath):
            file_size = os.path.getsize(filepath) / (1024 * 1024)
            print(f"  ✓ Model exists: {filename} ({file_size:.1f} MB)")
            model_download_status["downloaded"].append(filename)
            continue
            
        # Retry logic: try up to 3 times
        max_retries = 3
        for attempt in range(1, max_retries + 1):
            try:
                print(f"  Downloading {filename}... (attempt {attempt}/{max_retries})")
                resp = req.get(url, stream=True, timeout=300, allow_redirects=True)
                resp.raise_for_status()
                
                os.makedirs(MODELS_DIR, exist_ok=True)
                total_size = int(resp.headers.get('content-length', 0))
                downloaded = 0
                
                with open(filepath, "wb") as f:
                    for chunk in resp.iter_content(chunk_size=65536):
                        if chunk:
                            f.write(chunk)
                            downloaded += len(chunk)
                            if total_size > 0 and downloaded % (5 * 1024 * 1024) == 0:
                                progress = (downloaded / total_size) * 100
                                print(f"    Progress: {progress:.0f}% ({downloaded / (1024*1024):.1f}/{total_size / (1024*1024):.1f} MB)")
                
                size_mb = os.path.getsize(filepath) / (1024 * 1024)
                print(f"  ✅ Downloaded {filename} ({size_mb:.1f} MB)")
                model_download_status["downloaded"].append(filename)
                break  # Success, exit retry loop
                
            except Exception as e:
                print(f"  ❌ Attempt {attempt} failed: {e}")
                if attempt < max_retries:
                    wait_time = 2 ** attempt  # Exponential backoff
                    print(f"  Retrying in {wait_time}s...")
                    sleep(wait_time)
                else:
                    print(f"  ❌ All download attempts failed for {filename}")
                    model_download_status["failed"].append(filename)
                    # Clean up partial download
                    if os.path.exists(filepath):
                        os.remove(filepath)
    
    model_download_status["status"] = "completed" if not model_download_status["failed"] else "partial"


def load_model():
    """Load the trained model and metadata at startup."""
    global model, model_metadata, class_names, gradcam, IMG_SIZE, model_load_diagnostics

    # Download models if not present (cloud deployment)
    download_models_if_missing()

    import tensorflow as tf
    from tensorflow import keras
    from tensorflow.keras import layers

    # Register custom preprocessing layer for safe deserialization
    @keras.utils.register_keras_serializable(package='WildTrackAI')
    class MobileNetPreprocess(layers.Layer):
        """MobileNetV2 preprocessing: scale [0,255] -> [-1,1]."""
        def call(self, x):
            x = tf.cast(x, tf.float32)
            return (x / 127.5) - 1.0

    # Try .keras first, then .h5 variants
    candidate_files = [
        p
        for p in [MODEL_PATH_KERAS, MODEL_PATH, MODEL_PATH_LEGACY, MODEL_PATH_V4, MODEL_PATH_V3]
        if os.path.exists(p)
    ]

    if not candidate_files:
        print("WARNING: No trained model found!")
        print(f"  Checked: {MODEL_PATH_KERAS}")
        print(f"  Checked: {MODEL_PATH}")
        print(f"  Checked: {MODEL_PATH_LEGACY}")
        print(f"  Checked: {MODEL_PATH_V4}")
        print(f"  Checked: {MODEL_PATH_V3}")
        print("  Run training first: python training/train.py")
        model_load_diagnostics = {
            "loaded_from": None,
            "attempted": [],
            "error": "No trained model file found",
        }
        return

    # Build custom_objects for deserialization compatibility
    custom_objects = {
        'MobileNetPreprocess': MobileNetPreprocess,
    }

    # Support FocalLoss from v3/v4 training
    try:
        from training.train_v4 import FocalLoss
        custom_objects['FocalLoss'] = FocalLoss
    except ImportError:
        try:
            from training.train_v3 import FocalLoss
            custom_objects['FocalLoss'] = FocalLoss
        except ImportError:
            pass

    # Register Keras 3.x ops that may not exist in older TF builds
    try:
        from keras.src.ops.numpy import TrueDivide
        custom_objects['TrueDivide'] = TrueDivide
    except ImportError:
        pass
    try:
        if 'TrueDivide' not in custom_objects:
            class TrueDivide(layers.Layer):
                def call(self, x1, x2):
                    return tf.math.divide(x1, x2)
            custom_objects['TrueDivide'] = TrueDivide
    except Exception:
        pass

    model = None
    model_load_diagnostics = {
        "loaded_from": None,
        "attempted": [],
        "error": None,
    }

    for model_file in candidate_files:
        file_size_mb = os.path.getsize(model_file) / (1024 * 1024)
        model_load_diagnostics["attempted"].append(
            {
                "path": model_file,
                "size_mb": round(file_size_mb, 2),
            }
        )
        print(f"Loading model: {model_file} ({file_size_mb:.1f} MB)")
        try:
            load_kwargs = dict(compile=False, custom_objects=custom_objects)
            # .h5 files with Lambda/custom layers need safe_mode=False
            if model_file.endswith('.h5'):
                load_kwargs['safe_mode'] = False
            model = tf.keras.models.load_model(model_file, **load_kwargs)
            model_load_diagnostics["loaded_from"] = model_file
            print(f"  Model loaded successfully ({model.count_params():,} params)")
            break
        except Exception as e:
            model_load_diagnostics["error"] = f"{type(e).__name__}: {e}"
            print(f"  ERROR loading {os.path.basename(model_file)}: {e}")

    if model is None:
        print("ERROR: Failed to load model from all available files")
        return

    # Load metadata
    if os.path.exists(METADATA_PATH):
        with open(METADATA_PATH, 'r') as f:
            model_metadata = json.load(f)
        class_names = (model_metadata.get('class_names') or
                       model_metadata.get('classes') or [])
        IMG_SIZE = (model_metadata.get('img_size') or
                    model_metadata.get('image_size') or IMG_SIZE)
        print(f"  Classes: {class_names}")
        print(f"  Image size: {IMG_SIZE}")
        print(f"  Accuracy: {model_metadata.get('accuracy', 'N/A')}")
        print(f"  Backbone: {model_metadata.get('backbone', 'N/A')}")
        print(f"  Version: {model_metadata.get('version', 'N/A')}")
    else:
        # Fallback class names (must match model output order)
        class_names = ['deer', 'elephant', 'leopard', 'tiger', 'wolf']
        print(f"  Using default classes: {class_names}")

    # Initialize GradCAM
    try:
        from gradcam_module import GradCAM
        gradcam = GradCAM(model, output_dir=OUTPUTS_DIR)
        print("  GradCAM: initialized")
    except Exception as e:
        print(f"  GradCAM: failed to initialize ({e})")
        gradcam = None


# ============================================
# ANIMAL INFO DATABASE
# ============================================
ANIMAL_INFO = {
    'tiger': {
        'scientific_name': 'Panthera tigris',
        'conservation_status': 'Endangered',
        'weight': '100-300 kg',
        'footprint_size': '12-16 cm',
        'habitat': 'Tropical forests, grasslands, mangroves',
        'description': 'Tigers have large, round paw prints with four toes and no claw marks. '
                       'The pad is large and bilobed at the rear.',
        'distribution': 'India, Southeast Asia, Russia',
    },
    'leopard': {
        'scientific_name': 'Panthera pardus',
        'conservation_status': 'Vulnerable',
        'weight': '30-90 kg',
        'footprint_size': '7-10 cm',
        'habitat': 'Forests, savannas, mountains',
        'description': 'Leopard prints are smaller than tiger prints with four toes. '
                       'Claws are retractable and rarely show in tracks.',
        'distribution': 'Africa, Asia',
    },
    'elephant': {
        'scientific_name': 'Elephas maximus / Loxodonta africana',
        'conservation_status': 'Endangered',
        'weight': '2,700-6,000 kg',
        'footprint_size': '40-50 cm',
        'habitat': 'Forests, savannas, wetlands',
        'description': 'Elephant footprints are the largest of any land animal. '
                       'They are round with a distinctive cracked skin pattern.',
        'distribution': 'Africa, South/Southeast Asia',
    },
    'deer': {
        'scientific_name': 'Cervidae (family)',
        'conservation_status': 'Least Concern (varies)',
        'weight': '30-300 kg',
        'footprint_size': '5-9 cm',
        'habitat': 'Forests, grasslands, wetlands',
        'description': 'Deer have cloven hooves creating two-toed prints. '
                       'Dewclaws may show in soft ground.',
        'distribution': 'Worldwide except Antarctica/Australia',
    },
    'wolf': {
        'scientific_name': 'Canis lupus',
        'conservation_status': 'Least Concern',
        'weight': '30-80 kg',
        'footprint_size': '10-13 cm',
        'habitat': 'Forests, tundra, grasslands',
        'description': 'Wolf tracks show four toes with claws visible. '
                       'Larger than domestic dog prints with a more elongated shape.',
        'distribution': 'North America, Europe, Asia',
    },
    'fox': {
        'scientific_name': 'Vulpes vulpes',
        'conservation_status': 'Least Concern',
        'weight': '3-14 kg',
        'footprint_size': '4-6 cm',
        'habitat': 'Forests, grasslands, urban areas',
        'description': 'Fox tracks are smaller than wolf tracks with four toes. '
                       'Prints often appear in a straight line (direct register).',
        'distribution': 'Worldwide',
    },
    'dog': {
        'scientific_name': 'Canis lupus familiaris',
        'conservation_status': 'Domesticated',
        'weight': '1-90 kg',
        'footprint_size': '3-12 cm',
        'habitat': 'Worldwide, human settlements',
        'description': 'Dog paw prints show four toes with visible claw marks. '
                       'Size varies greatly by breed. Often confused with wolf.',
        'distribution': 'Worldwide',
    },
    'cat': {
        'scientific_name': 'Felis catus',
        'conservation_status': 'Domesticated',
        'weight': '3-7 kg',
        'footprint_size': '2-4 cm',
        'habitat': 'Worldwide, human settlements',
        'description': 'Cat prints show four toes without claw marks (retractable claws). '
                       'Small, round prints with a distinctive tri-lobed pad.',
        'distribution': 'Worldwide',
    },
    'hyena': {
        'scientific_name': 'Crocuta crocuta',
        'conservation_status': 'Least Concern',
        'weight': '40-86 kg',
        'footprint_size': '8-11 cm',
        'habitat': 'Savannas, grasslands, semi-deserts',
        'description': 'Hyena tracks show four toes with blunt claw marks. '
                       'Front feet are larger than rear. Pads are rough.',
        'distribution': 'Africa, parts of Asia',
    },
    'bear': {
        'scientific_name': 'Ursidae (family)',
        'conservation_status': 'Varies by species',
        'weight': '60-600 kg',
        'footprint_size': '15-30 cm',
        'habitat': 'Forests, mountains, tundra',
        'description': 'Bear prints show five toes with long claw marks. '
                       'Hind foot is plantigrade, resembling a human footprint.',
        'distribution': 'North/South America, Europe, Asia',
    },
}

# ============================================
# LIFESPAN (MODEL LOADING)
# ============================================


_startup_time = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Load model on startup."""
    global _startup_time
    _startup_time = datetime.datetime.utcnow()
    load_model()
    yield
    print("Shutting down...")


# ============================================
# FASTAPI APP
# ============================================
app = FastAPI(
    title="WildTrackAI API",
    description="AI-powered animal footprint identification system with MobileNetV2 v4-cpu (85.8% accuracy)",
    version="2.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(chat_router)
app.include_router(chat_db_router)
app.include_router(auth_router)

from routes.mlops import router as mlops_router
app.include_router(mlops_router)

# Serve uploaded avatar images
from fastapi.staticfiles import StaticFiles
_avatar_dir = os.path.join(BASE_DIR, "uploads", "avatars")
os.makedirs(_avatar_dir, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=os.path.join(BASE_DIR, "uploads")), name="uploads")


# ============================================
# UTILITY FUNCTIONS
# ============================================
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
    # Scale to 0-100 for interpretability
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
        return None, 'none'  # Sharp imagery, no warning
    elif blur_level >= 60:
        return (
            "Image clarity is moderate. Footprint features are visible but soft. "
            "If possible, retake from directly above with stronger lighting.",
            'caution'
        )
    elif blur_level >= 45:
        return (
            "Image is significantly blurry. Footprint edge definition is limited. "
            "Classification confidence may be unreliable—field validation recommended.",
            'warning'
        )
    else:
        return (
            "Image is severely blurry or out of focus. Footprint structure is unclear. "
            "Please retake the image. Classification should NOT be trusted without field verification.",
            'critical'
        )


def normalize_contrast(image):
    """Apply CLAHE (Contrast Limited Adaptive Histogram Equalization).
    
    Enhances local contrast without oversaturation.
    Critical for footprints on low-contrast substrates.
    """
    if len(image.shape) == 3:
        # Convert BGR → LAB color space (works on L channel only)
        lab = cv2.cvtColor(image, cv2.COLOR_BGR2LAB)
        l_channel = lab[:, :, 0]
        
        # Apply CLAHE to L channel
        clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
        l_channel_clahe = clahe.apply(l_channel)
        
        # Reconstruct LAB and convert back to BGR
        lab[:, :, 0] = l_channel_clahe
        image = cv2.cvtColor(lab, cv2.COLOR_LAB2BGR)
    else:
        clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
        image = clahe.apply(image)
    
    return image


def enhance_edges(image):
    """Enhance footprint edges using unsharp masking.
    
    Sharpens pad and toe boundaries without introducing artifacts.
    """
    if len(image.shape) == 3:
        # Apply unsharp mask in grayscale, then blend back
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        
        # Gaussian blur for subtraction
        blurred = cv2.GaussianBlur(gray, (5, 5), 1.0)
        sharpened_gray = cv2.addWeighted(gray, 1.5, blurred, -0.5, 0)
        sharpened_gray = np.clip(sharpened_gray, 0, 255).astype(np.uint8)
        
        # Blend back into color image
        # Extract sharpening mask and apply to each channel
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
    """Adaptive brightness and gamma correction for dark/low-contrast images.
    
    Detects mean luminance and applies selective gamma correction.
    Critical for photos taken in jungle/forest conditions with poor lighting.
    
    Returns:
        - corrected_image: brightness-adjusted image
        - gamma_applied: bool (True if correction was significant)
    """
    # Convert to LAB to work on L channel (luminance) only
    if len(image.shape) == 3 and image.shape[2] == 3:
        lab = cv2.cvtColor(image, cv2.COLOR_BGR2LAB)
        l_channel = lab[:, :, 0].astype(np.float32)
    else:
        l_channel = image.astype(np.float32) if len(image.shape) == 2 else cv2.cvtColor(image, cv2.COLOR_BGR2GRAY).astype(np.float32)
    
    mean_luminance = np.mean(l_channel)
    
    # Determine gamma correction needed
    gamma_applied = False
    if mean_luminance < 85:  # Very dark
        gamma = 1.8  # Aggressive brightening
        gamma_applied = True
    elif mean_luminance < 100:  # Dark
        gamma = 1.5  # Moderate brightening
        gamma_applied = True
    elif mean_luminance < 115:  # Slightly dark
        gamma = 1.2  # Gentle brightening
        gamma_applied = True
    else:
        gamma = 1.0  # No correction needed
    
    if gamma_applied:
        # Apply gamma correction: out = in ^ (1/gamma)
        l_channel = np.power(l_channel / 255.0, 1.0 / gamma) * 255.0
        l_channel = np.clip(l_channel, 0, 255).astype(np.uint8)
        
        # Reconstruct LAB and convert back to BGR
        if len(image.shape) == 3 and image.shape[2] == 3:
            lab[:, :, 0] = l_channel
            image = cv2.cvtColor(lab, cv2.COLOR_LAB2BGR)
        else:
            image = l_channel
    
    return image, gamma_applied


def intelligent_resize(image, target_size=300):
    """Resize image intelligently while preserving aspect ratio.
    
    - Detects if footprint is already well-framed
    - Pads with neutral (gray) background if needed
    - Prioritizes footprint centering
    """
    h, w = image.shape[:2]
    aspect_ratio = w / h
    
    # Calculate new dimensions maintaining aspect ratio
    if aspect_ratio > 1:  # wider than tall
        new_w = target_size
        new_h = int(target_size / aspect_ratio)
    else:  # taller than wide
        new_h = target_size
        new_w = int(target_size * aspect_ratio)
    
    # Resize image
    resized = cv2.resize(image, (new_w, new_h), interpolation=cv2.INTER_CUBIC)
    
    # Create square canvas with neutral gray background
    canvas = np.full((target_size, target_size, 3 if len(image.shape) == 3 else 1),
                     128, dtype=np.uint8)
    
    # Calculate padding to center the image
    offset_h = (target_size - new_h) // 2
    offset_w = (target_size - new_w) // 2
    
    # Place resized image in center
    if len(image.shape) == 3:
        canvas[offset_h:offset_h + new_h, offset_w:offset_w + new_w, :] = resized
    else:
        canvas[offset_h:offset_h + new_h, offset_w:offset_w + new_w] = resized
    
    return canvas


def preprocess_image(file_bytes, target_size=None):
    """Preprocess uploaded image to EXACTLY match the training pipeline.
    
    CRITICAL: The model was trained with tf.data using:
        tf.image.decode_image → tf.image.resize → tf.cast(float32)
    
    Any additional preprocessing (CLAHE, edge sharpening, gamma correction)
    creates a domain gap that destroys prediction accuracy.
    
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
    
    # ── Quality metrics (for UI display only — does NOT modify the image) ──
    quality_metrics = {}
    
    # Perceptual hash
    phash = pipeline.generate_phash(img)
    quality_metrics['phash'] = phash
    quality_metrics['is_duplicate'] = pipeline.check_duplicate(phash)

    # Detect blur
    blur_level, is_blurry = pipeline.detect_blur(img)
    quality_metrics['blur_level'] = float(blur_level)
    quality_metrics['is_blurry'] = bool(is_blurry)
    
    # Generate quality warning
    warning_msg, warning_severity = generate_quality_warning(blur_level)
    if warning_msg:
        quality_metrics['quality_warning'] = warning_msg
        quality_metrics['quality_severity'] = warning_severity
    
    quality_metrics['gamma_applied'] = False
    quality_metrics['processing_applied'] = False
    
    # Stage 1: YOLO Object Detection & Crop (operate on BGR)
    img, stage1_meta = pipeline.stage1_detect_and_crop(img)
    
    # ── Match training pipeline exactly ──
    # Step 1: Convert BGR (OpenCV) → RGB (TensorFlow training used tf.image.decode_image which gives RGB)
    img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    
    # Step 2: Simple resize to target_size × target_size (training used tf.image.resize)
    img = cv2.resize(img, (target_size, target_size), interpolation=cv2.INTER_LINEAR)
    
    # Step 3: Cast to float32 (training used tf.cast(img, tf.float32) keeping [0, 255] range)
    img_array = img.astype('float32')
    img_array = np.expand_dims(img_array, axis=0)

    return img_array, original, quality_metrics, stage1_meta


def predict_single(img_array, original_image=None, generate_heatmap=True, use_tta=True, quality_metrics=None, lat=None, lon=None):
    """Run prediction on a single preprocessed image.
    
    Applies Test-Time Augmentation (TTA) for improved accuracy.
    Applies temperature scaling for calibrated softmax confidence.
    If max confidence < CONFIDENCE_THRESHOLD -> unknown.
    """
    if quality_metrics is None:
        quality_metrics = {}
    if model is None:
        raise HTTPException(status_code=503, detail="Model not loaded. Train model first.")

    # Test-Time Augmentation
    if use_tta:
        try:
            from training.train_v4 import tta_predict
            raw_probs = tta_predict(model, img_array, n_augments=3)
        except ImportError:
            raw_probs = model.predict(img_array, verbose=0)[0]
    else:
        raw_probs = model.predict(img_array, verbose=0)[0]

    # Stage 3: Geo-aware logical filtering
    filtered_probs = pipeline.stage3_geo_filter(raw_probs, lat, lon, class_names)

    # Stage 4: Temperature scaling — PROPERLY calibrate confidence
    TEMPERATURE = 1.2
    predictions = pipeline.stage4_calibrate_confidence(filtered_probs, TEMPERATURE)

    # Shannon entropy — uncertainty quantification (bits)
    entropy = float(-np.sum(predictions * np.log2(predictions + 1e-10)))
    max_entropy = float(np.log2(len(predictions)))  # uniform distribution
    entropy_ratio = entropy / max_entropy if max_entropy > 0 else 0.0

    predicted_idx = int(np.argmax(predictions))
    confidence = float(predictions[predicted_idx])
    raw_class = class_names[predicted_idx] if predicted_idx < len(class_names) else "unknown"

    # Unknown threshold: low confidence AND high entropy (both must be true)
    HIGH_ENTROPY_THRESHOLD = 0.90  # 90% of max entropy = very uncertain
    is_unknown = confidence < CONFIDENCE_THRESHOLD and entropy_ratio > HIGH_ENTROPY_THRESHOLD
    predicted_class = "unknown" if is_unknown else raw_class

    # Adaptive confidence scaling based on image quality
    quality_adjusted_confidence = confidence
    confidence_penalty = 1.0
    
    blur_level = quality_metrics.get('blur_level', 100)
    gamma_applied = quality_metrics.get('gamma_applied', False)
    
    # Apply quality-based penalties
    if blur_level < 45:  # Critical blur
        confidence_penalty *= 0.75
    elif blur_level < 60:  # Moderate blur
        confidence_penalty *= 0.90
    
    if gamma_applied:  # Darker images had to be brightened
        confidence_penalty *= 0.95
    
    quality_adjusted_confidence = confidence * confidence_penalty

    # Top 3 with delta confidence
    top_indices = np.argsort(predictions)[::-1][:3]
    top3 = []
    top_confidence = float(predictions[top_indices[0]])
    for rank, idx in enumerate(top_indices):
        cls = class_names[idx] if idx < len(class_names) else "unknown"
        conf = float(predictions[idx])
        top3.append({
            "class": cls,
            "confidence": conf,
            "delta": round(top_confidence - conf, 4) if rank > 0 else 0.0,
            "info": ANIMAL_INFO.get(cls, {})
        })

    # GradCAM heatmap
    heatmap_b64 = None
    if generate_heatmap and gradcam is not None:
        try:
            heatmap_b64 = gradcam.generate_from_array(img_array, original_image, IMG_SIZE, confidence=confidence)
        except Exception as e:
            print(f"GradCAM error: {e}")

    # ── AI CONSENSUS VALIDATION ──────────────────────────────────
    # Second Opinion: Run single-pass (no TTA) for an independent perspective
    try:
        second_opinion_raw = model.predict(img_array, verbose=0)[0]
        # Apply same geo-filter to second opinion
        so_filtered = pipeline.stage3_geo_filter(second_opinion_raw, lat, lon, class_names)
        so_calibrated = pipeline.stage4_calibrate_confidence(so_filtered, TEMPERATURE)
        consensus_result = compute_consensus(predictions, so_calibrated, class_names, CONFIDENCE_THRESHOLD)
    except Exception as e:
        print(f"Consensus validation error: {e}")
        consensus_result = None

    return {
        "predicted_class": predicted_class,
        "raw_class": raw_class,
        "confidence": confidence,
        "quality_adjusted_confidence": round(quality_adjusted_confidence, 4),
        "is_unknown": is_unknown,
        "entropy": round(entropy, 4),
        "entropy_ratio": round(entropy_ratio, 4),
        "max_entropy": round(max_entropy, 4),
        "temperature": TEMPERATURE,
        "top3": top3,
        "heatmap": heatmap_b64,
        "model_version": model_metadata.get("version", "v4"),
        "tta_enabled": use_tta,
        "consensus": consensus_result,
        "all_predictions": {
            class_names[i]: float(predictions[i])
            for i in range(len(class_names))
        } if class_names else {}
    }


# ============================================
# ENDPOINTS
# ============================================

@app.api_route("/", methods=["GET", "HEAD"])
async def root(request: Request):
    """Root endpoint for Render base URL checks."""
    if request.method == "HEAD":
        return Response(status_code=200)
    return {
        "service": "WildTrackAI API",
        "status": "running",
        "version": "2.1.0",
        "endpoints": {
            "health": "/health",
            "readiness": "/ready",
            "system_status": "/api/system/status",
            "docs": "/docs"
        }
    }

@app.api_route("/health", methods=["GET", "HEAD"])
async def health_check(request: Request):
    """System health check with model download status."""
    if request.method == "HEAD":
        return Response(status_code=200)
    # Determine overall health status
    is_healthy = model is not None and model_download_status.get("status") != "partial"
    
    return {
        "status": "healthy" if is_healthy else "degraded",
        "model_loaded": model is not None,
        "model_load_diagnostics": model_load_diagnostics,
        "model_download_status": model_download_status,
        "gradcam_available": gradcam is not None,
        "classes": len(class_names),
        "class_names": class_names if len(class_names) <= 10 else class_names[:10],
        "database": os.path.exists(DB_PATH),
        "gemini_ai": gemini_model is not None,
        "ninja_api": bool(NINJA_API_KEY),
        "timestamp": datetime.datetime.utcnow().isoformat(),
    }


@app.get("/ready")
async def readiness_check():
    """Readiness probe for Render - only returns 200 when model is loaded."""
    if model is None:
        raise HTTPException(status_code=503, detail="Service not ready - model still loading")
    return {"ready": True, "status": "operational"}


@app.get("/api/system/status")
async def system_status():
    """Production system status — model version, accuracy, TTA, uptime."""
    now = datetime.datetime.utcnow()
    uptime_seconds = (now - _startup_time).total_seconds() if _startup_time else 0
    hours, remainder = divmod(int(uptime_seconds), 3600)
    minutes, seconds = divmod(remainder, 60)
    return {
        "model_version": model_metadata.get("version", "unknown"),
        "model_name": model_metadata.get("model_name", "WildTrackAI"),
        "architecture": model_metadata.get("architecture") or model_metadata.get("backbone", "unknown"),
        "validation_accuracy": model_metadata.get("accuracy", 0),
        "precision": model_metadata.get("precision", 0),
        "recall": model_metadata.get("recall", 0),
        "f1_score": model_metadata.get("f1_score", 0),
        "tta_enabled": True,
        "tta_passes": 3,
        "total_classes": len(class_names),
        "class_names": class_names,
        "img_size": IMG_SIZE,
        "uptime": f"{hours}h {minutes}m {seconds}s",
        "uptime_seconds": int(uptime_seconds),
        "status": "operational" if model is not None else "degraded",
        "timestamp": now.isoformat(),
    }


@app.post("/predict")
async def predict(
    file: UploadFile = File(...),
    latitude: Optional[float] = Form(None),
    longitude: Optional[float] = Form(None)
):
    """Predict animal species from footprint image with preprocessing robustness."""
    if model is None:
        download_status = model_download_status.get("status", "unknown")
        if download_status == "downloading":
            raise HTTPException(
                status_code=503,
                detail="Model is still downloading. Please wait a moment and try again."
            )
        elif download_status == "partial":
            raise HTTPException(
                status_code=503,
                detail="Model download incomplete. Some model files failed to download."
            )
        else:
            raise HTTPException(
                status_code=503,
                detail="Model not loaded. Please check server logs or contact support."
            )

    # Read and preprocess (now returns quality metrics and stage1 meta)
    contents = await file.read()
    try:
        img_array, original, quality_metrics, stage1_meta = preprocess_image(contents)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid image: {e}")

    # Predict with quality metrics and geo-aware pipeline
    result = predict_single(img_array, original, quality_metrics=quality_metrics, lat=latitude, lon=longitude)
    
    # Auto-rejection for severely blurry images
    blur_level = quality_metrics.get('blur_level', 100)
    requires_field_validation = blur_level < 45

    # Check Active Learning / HITL rules
    # If final quality adjusted confidence is below threshold, flag for review
    needs_review = 1 if result.get("quality_adjusted_confidence", 1.0) < CONFIDENCE_THRESHOLD or result["is_unknown"] else 0

    pred_id = str(uuid.uuid4())[:8]
    
    # Save to Cloudinary
    image_url = ""
    try:
        import cloudinary
        import cloudinary.uploader
        upload_result = cloudinary.uploader.upload(
            contents,
            public_id=f"pred_{pred_id}",
            folder="wildtrack_predictions",
            overwrite=True
        )
        image_url = upload_result.get("secure_url")
    except Exception as e:
        print(f"Cloudinary upload failed: {e}")

    # Store in database
    db = SessionLocal()
    try:
        prediction = Prediction(
            id=pred_id,
            species=result["predicted_class"],
            confidence=result["confidence"],
            top3=json.dumps(result["top3"]),
            image_path=image_url,
            filename=file.filename,
            heatmap_generated=1 if result["heatmap"] else 0,
            latitude=latitude,
            longitude=longitude,
            needs_review=needs_review,
            is_rejected=1 if requires_field_validation else 0
        )
        db.add(prediction)
        db.commit()
    except Exception as e:
        print(f"DB error: {e}")
    finally:
        db.close()

    return {
        "prediction_id": pred_id,
        "species": result["predicted_class"],
        "confidence": result["confidence"],
        "quality_adjusted_confidence": result.get("quality_adjusted_confidence", result["confidence"]),
        "is_unknown": result["is_unknown"],
        "needs_review": bool(needs_review),
        "stage1_yolo": stage1_meta,
        "raw_class": result.get("raw_class", result["predicted_class"]),
        "requires_field_validation": requires_field_validation,
        "top3": result["top3"],
        "heatmap": result["heatmap"],
        "all_predictions": result["all_predictions"],
        "entropy": result.get("entropy", 0),
        "entropy_ratio": result.get("entropy_ratio", 0),
        "max_entropy": result.get("max_entropy", 0),
        "temperature": result.get("temperature", 1.0),
        "model_version": result.get("model_version", "v4"),
        "tta_enabled": result.get("tta_enabled", True),
        "animal_info": ANIMAL_INFO.get(result.get("raw_class", result["predicted_class"]), {}),
        "filename": file.filename,
        "timestamp": datetime.datetime.utcnow().isoformat(),
        "latitude": latitude,
        "longitude": longitude,
        # Image quality metrics
        "image_quality": quality_metrics,
    }


@app.post("/predict/batch")
async def predict_batch(files: List[UploadFile] = File(...),
                        background_tasks: BackgroundTasks = None):
    """Batch prediction for multiple images with robustness preprocessing."""
    if model is None:
        raise HTTPException(status_code=503, detail="Model not loaded.")

    results = []
    for file in files:
        try:
            contents = await file.read()
            img_array, original, quality_metrics, stage1_meta = preprocess_image(contents)
            result = predict_single(img_array, original, generate_heatmap=False, quality_metrics=quality_metrics)

            pred_id = str(uuid.uuid4())[:8]
            blur_level = quality_metrics.get('blur_level', 100)
            requires_field_validation = blur_level < 45

            # Save to Cloudinary
            image_url = ""
            try:
                import cloudinary
                import cloudinary.uploader
                upload_result = cloudinary.uploader.upload(
                    contents,
                    public_id=f"pred_{pred_id}",
                    folder="wildtrack_predictions",
                    overwrite=True
                )
                image_url = upload_result.get("secure_url")
            except Exception as e:
                print(f"Cloudinary upload failed: {e}")

            # Store in DB
            db = SessionLocal()
            try:
                prediction = Prediction(
                    id=pred_id,
                    species=result["predicted_class"],
                    confidence=result["confidence"],
                    top3=json.dumps(result["top3"]),
                    filename=file.filename,
                    image_path=image_url,
                    heatmap_generated=0,
                )
                db.add(prediction)
                db.commit()
            finally:
                db.close()

            results.append({
                "prediction_id": pred_id,
                "filename": file.filename,
                "species": result["predicted_class"],
                "confidence": result["confidence"],
                "quality_adjusted_confidence": result.get("quality_adjusted_confidence", result["confidence"]),
                "requires_field_validation": requires_field_validation,
                "top3": result["top3"],
                "image_quality": quality_metrics,
            })
        except Exception as e:
            results.append({
                "filename": file.filename,
                "error": str(e),
            })

    return {
        "total": len(files),
        "successful": len([r for r in results if "error" not in r]),
        "failed": len([r for r in results if "error" in r]),
        "results": results,
    }


@app.get("/species")
async def list_species():
    """List all supported species with info."""
    species_list = []

    # Get prediction counts from DB
    db = SessionLocal()
    try:
        from sqlalchemy import func
        counts = dict(
            db.query(Prediction.species, func.count(Prediction.id))
            .group_by(Prediction.species).all()
        )
    except Exception:
        counts = {}
    finally:
        db.close()

    for name in class_names:
        info = ANIMAL_INFO.get(name, {})
        species_list.append({
            "name": name,
            "scientific_name": info.get("scientific_name", "Unknown"),
            "conservation_status": info.get("conservation_status", "Unknown"),
            "prediction_count": counts.get(name, 0),
            "info": info,
        })

    return {"species": species_list, "total": len(species_list)}


@app.get("/species/{name}")
async def get_species(name: str):
    """Get detailed info about a specific species."""
    if name not in ANIMAL_INFO:
        raise HTTPException(status_code=404, detail=f"Species '{name}' not found")
    return {"name": name, "info": ANIMAL_INFO[name]}


# ============================================
# GEMINI-POWERED SPECIES SEARCH ENGINE
# ============================================

# In-memory cache to reduce API calls
_species_search_cache = {}

class SpeciesSearchRequest(BaseModel):
    query: str  # e.g., "rhino", "snow leopard footprint", "african wild dog"

@app.post("/species-search")
async def species_search(req: SpeciesSearchRequest):
    """
    AI-powered wildlife footprint search engine.
    Uses Gemini to generate detailed species info for ANY animal — not limited to trained species.
    Falls back to ANIMAL_INFO for trained species.
    """
    query = req.query.strip().lower()
    
    if not query or len(query) < 2:
        raise HTTPException(status_code=400, detail="Query must be at least 2 characters")
    
    # Check cache first
    if query in _species_search_cache:
        cached = _species_search_cache[query]
        cached["cached"] = True
        return cached
    
    # Check if it's a known trained species
    for name, info in ANIMAL_INFO.items():
        if query in name.lower() or name.lower() in query:
            result = {
                "found": True,
                "source": "local_database",
                "trained_species": name in class_names,
                "species": {
                    "common_name": name.title(),
                    "scientific_name": info.get("scientific_name", "Unknown"),
                    "conservation_status": info.get("conservation_status", "Unknown"),
                    "weight": info.get("weight", "Unknown"),
                    "footprint_size": info.get("footprint_size", "Unknown"),
                    "habitat": info.get("habitat", "Unknown"),
                    "description": info.get("description", ""),
                    "distribution": info.get("distribution", "Unknown"),
                    "fun_facts": [],
                    "tracking_tips": "",
                    "confusion_species": [],
                },
                "cached": False,
            }
            _species_search_cache[query] = result
            return result
    
    # Use Gemini AI for unknown species
    if gemini_model is None:
        raise HTTPException(
            status_code=503,
            detail="Gemini AI not available. Set GEMINI_API_KEY environment variable."
        )
    
    prompt = f"""You are a wildlife tracking expert and zoologist. 
A user searched for: "{req.query}"

Provide detailed information about this animal's footprints and tracks.
Respond ONLY with valid JSON (no markdown, no code blocks, no extra text).
Use this exact structure:

{{
  "common_name": "Animal Name",
  "scientific_name": "Genus species",
  "conservation_status": "e.g., Endangered, Vulnerable, Least Concern",
  "weight": "typical range in kg",
  "footprint_size": "length in cm",
  "habitat": "primary habitats",
  "description": "Detailed description of the animal's footprints/tracks, including shape, toe count, claw visibility, pad patterns, and distinguishing features. 2-3 sentences.",
  "distribution": "geographic range",
  "fun_facts": ["fact 1 about their tracks", "fact 2", "fact 3"],
  "tracking_tips": "Practical advice for identifying this animal's tracks in the field. 2-3 sentences.",
  "confusion_species": ["species 1 whose tracks look similar", "species 2"]
}}

If the query is not a real animal or you can't identify it, respond with:
{{"common_name": null, "error": "Could not identify species"}}
"""
    
    try:
        response = gemini_model.generate_content(
            prompt,
            generation_config=genai.types.GenerationConfig(
                temperature=0.3,
                max_output_tokens=1000,
            )
        )
        
        raw_text = response.text.strip()
        # Clean markdown code blocks if present
        if raw_text.startswith("```"):
            raw_text = raw_text.split("\n", 1)[1] if "\n" in raw_text else raw_text[3:]
            if raw_text.endswith("```"):
                raw_text = raw_text[:-3]
            raw_text = raw_text.strip()
        
        species_data = json.loads(raw_text)
        
        if species_data.get("common_name") is None:
            return {
                "found": False,
                "source": "gemini_ai",
                "error": species_data.get("error", "Species not recognized"),
                "query": req.query,
                "cached": False,
            }
        
        result = {
            "found": True,
            "source": "gemini_ai",
            "trained_species": False,
            "species": species_data,
            "cached": False,
        }
        
        # Cache the result
        _species_search_cache[query] = result
        return result
        
    except json.JSONDecodeError as e:
        print(f"Gemini JSON parse error: {e}")
        print(f"Raw response: {raw_text[:500]}")
        raise HTTPException(status_code=502, detail="AI returned invalid response. Try again.")
    except Exception as e:
        print(f"Gemini species search error: {e}")
        raise HTTPException(status_code=502, detail=f"AI search failed: {str(e)}")


# ============================================
# API NINJAS — ANIMAL INFO ENDPOINT
# ============================================

import requests

@app.get("/api/animal-info")
async def get_animal_info(name: str = Query(..., min_length=1)):
    """
    WildTrackAI Knowledge Engine — structured wildlife intelligence.
    Transforms biological data into curated semantic sections.
    """
    if not NINJA_API_KEY:
        raise HTTPException(status_code=503, detail="Wildlife database not available")
    
    if not name or len(name.strip()) < 1:
        raise HTTPException(status_code=400, detail="Animal name required")
    
    try:
        response = requests.get(
            "https://api.api-ninjas.com/v1/animals",
            params={"name": name.strip()},
            headers={"X-Api-Key": NINJA_API_KEY},
            timeout=5
        )
        
        if response.status_code != 200:
            raise HTTPException(status_code=response.status_code, 
                              detail=f"Unable to retrieve wildlife data: {response.status_code}")
        
        data = response.json()
        
        if not data:
            return {"found": False, "message": f"No species information found for '{name}'"}
        
        animal = data[0]
        
        # Extract raw fields
        name_common = animal.get("name", "").title()
        taxonomy = animal.get("taxonomy", {})
        characteristics = animal.get("characteristics", {})
        locations = animal.get("locations", [])
        
        sci_name = f"{taxonomy.get('genus', '')} {taxonomy.get('species', '')}".strip() or "Unknown"
        habitat = characteristics.get("habitat", "various ecosystems")
        diet = characteristics.get("diet", "unknown diet")
        weight = characteristics.get("weight", "variable")
        height = characteristics.get("height", "not documented")
        lifespan = characteristics.get("lifespan", "not documented")
        skin_type = characteristics.get("skin_type", "")
        raw_color = characteristics.get("color", "variable")
        # Insert spaces between CamelCase color words (e.g. BrownYellowWhite -> Brown, Yellow, White)
        import re as _re
        color = _re.sub(r'(?<=[a-z])(?=[A-Z])', ', ', raw_color) if raw_color else "variable"
        animal_type = characteristics.get("type", "")
        location_str = ", ".join(locations) if locations else "multiple regions"
        family = taxonomy.get("family", "")
        order = taxonomy.get("order", "")
        
        # ── SEMANTIC SECTION 1: Overview ──
        overview = (
            f"{name_common} ({sci_name}) is a {animal_type.lower() or 'vertebrate'} species "
            f"belonging to the family {family or 'unknown'}. "
            f"Found across {location_str}, this species inhabits {habitat} "
            f"and has adapted to thrive within its ecological niche over millennia. "
            f"With a typical weight of {weight}, {name_common} represents a significant "
            f"component of its native ecosystem's biodiversity."
        )
        
        # ── SEMANTIC SECTION 2: Ecology ──
        diet_behavior = {
            "Carnivore": f"As a carnivore, {name_common} occupies a high trophic level, regulating prey populations and maintaining ecosystem equilibrium. Its hunting behavior shapes the movement and vigilance patterns of sympatric herbivores.",
            "Herbivore": f"As a herbivore, {name_common} plays a foundational role in energy transfer within its ecosystem. Through selective grazing and browsing, it influences vegetation structure and facilitates nutrient cycling across {habitat.lower()}.",
            "Omnivore": f"As an omnivore, {name_common} demonstrates remarkable dietary flexibility, consuming both plant and animal matter. This adaptability provides resilience against seasonal resource fluctuations in {habitat.lower()}.",
        }.get(diet, f"{name_common} contributes to its local ecosystem through its feeding habits and interactions with other species in {habitat.lower()}.")
        
        ecology = (
            f"{diet_behavior} "
            f"With a lifespan of {lifespan}, individuals contribute to population stability "
            f"and generational knowledge transfer within their social groups."
        )
        
        # ── SEMANTIC SECTION 3: Physical Traits ──
        physical_traits = (
            f"{name_common} is characterized by {color.lower() if color != 'variable' else 'species-typical'} coloration "
            f"and {skin_type.lower() + ' covering' if skin_type else 'a body plan'} adapted for its environment. "
            f"Adults typically weigh {weight} and reach heights of {height}. "
            f"These physical attributes are optimized for {habitat.lower()}, providing "
            f"{'camouflage and thermoregulation' if diet == 'Carnivore' else 'protection and environmental adaptation'} "
            f"suited to the species' ecological requirements."
        )
        
        # ── SEMANTIC SECTION 4: Field Identification ──
        field_identification = (
            f"When tracking {name_common} in the field, focus on {habitat.lower()} environments "
            f"where {'prey' if diet == 'Carnivore' else 'foraging' if diet == 'Herbivore' else 'food'} sources are abundant. "
            f"Look for signs of activity near water sources and along established trails. "
            f"{'Claw marks, scat, and drag marks from kills may indicate recent presence.' if diet == 'Carnivore' else ''}"
            f"{'Feeding damage on vegetation, droppings, and hoof impressions in soft substrate are reliable indicators.' if diet == 'Herbivore' else ''}"
            f"{'Both foraging damage and opportunistic feeding signs should be monitored.' if diet == 'Omnivore' else ''} "
            f"Track surveys are most productive during dawn and dusk when activity peaks."
        )
        
        # ── SEMANTIC SECTION 5: Distribution Summary ──
        distribution_summary = (
            f"{name_common} ranges across {location_str}. "
            f"Within this geographic range, the species selectively occupies {habitat.lower()}, "
            f"where environmental conditions support its dietary and behavioral requirements. "
            f"Population density varies regionally based on habitat quality, prey availability, "
            f"and anthropogenic pressures."
        )
        
        # ── SEMANTIC SECTION 6: Conservation Note ──
        conservation_role = {
            "Carnivore": "apex predator maintaining ecosystem balance through top-down regulation",
            "Herbivore": "key grazer shaping vegetation structure and facilitating habitat renewal",
            "Omnivore": "versatile forager contributing to seed dispersal and nutrient cycling"
        }.get(diet, "important participant in local ecosystem dynamics")
        
        conservation_note = (
            f"As a {conservation_role}, {name_common} serves as an indicator of ecosystem health. "
            f"Monitoring this species provides insights into broader environmental conditions "
            f"across {location_str}. Conservation efforts should prioritize habitat connectivity "
            f"and sustainable land management within the species' range."
        )
        
        return {
            "found": True,
            "species": {
                "name": name_common,
                "scientific_name": sci_name,
                "overview": overview,
                "ecology": ecology,
                "physical_traits": physical_traits,
                "field_identification": field_identification,
                "distribution_summary": distribution_summary,
                "conservation_note": conservation_note,
                "info_panel": {
                    "habitat": habitat,
                    "region": location_str,
                    "weight": weight,
                    "height": height,
                    "diet": diet,
                    "lifespan": lifespan,
                    "type": animal_type,
                    "color": color,
                    "skin_type": skin_type,
                },
                "classification": {
                    "kingdom": taxonomy.get("kingdom", ""),
                    "phylum": taxonomy.get("phylum", ""),
                    "class": taxonomy.get("class", ""),
                    "order": order,
                    "family": family,
                    "genus": taxonomy.get("genus", ""),
                },
            }
        }
        
    except requests.exceptions.Timeout:
        raise HTTPException(status_code=504, detail="Request timeout")
    except requests.exceptions.RequestException as e:
        raise HTTPException(status_code=502, detail=f"Connection error: {str(e)}")
    except Exception as e:
        print(f"Wildlife info error: {e}")
        raise HTTPException(status_code=500, detail=f"Data retrieval failed: {str(e)}")


@app.get("/history")
async def get_history(limit: int = Query(50, ge=1, le=500),
                      offset: int = Query(0, ge=0),
                      species: Optional[str] = None):
    """Get prediction history with optional filtering."""
    db = SessionLocal()
    try:
        query = db.query(Prediction).order_by(Prediction.timestamp.desc())
        if species:
            query = query.filter(Prediction.species == species)
        total = query.count()
        predictions = query.offset(offset).limit(limit).all()

        return {
            "total": total,
            "offset": offset,
            "limit": limit,
            "predictions": [
                {
                    "id": p.id,
                    "species": p.species,
                    "confidence": p.confidence,
                    "top3": json.loads(p.top3) if p.top3 else [],
                    "timestamp": p.timestamp.isoformat() if p.timestamp else None,
                    "filename": p.filename,
                    "heatmap_generated": bool(p.heatmap_generated),
                    "latitude": p.latitude,
                    "longitude": p.longitude,
                }
                for p in predictions
            ]
        }
    finally:
        db.close()


@app.get("/analytics")
async def get_analytics():
    """Dashboard analytics data."""
    db = SessionLocal()
    try:
        from sqlalchemy import func

        total_predictions = db.query(func.count(Prediction.id)).scalar() or 0
        avg_confidence = db.query(func.avg(Prediction.confidence)).scalar() or 0

        # Species distribution
        distribution = dict(
            db.query(Prediction.species, func.count(Prediction.id))
            .group_by(Prediction.species).all()
        )

        # Most detected
        most_detected = max(distribution, key=distribution.get) if distribution else None

        # Confidence histogram (10 bins)
        all_confs = [p.confidence for p in db.query(Prediction.confidence).all()]
        if all_confs:
            hist, bin_edges = np.histogram(all_confs, bins=10, range=(0, 1))
            confidence_histogram = [
                {"range": f"{bin_edges[i]:.1f}-{bin_edges[i+1]:.1f}",
                 "count": int(hist[i])}
                for i in range(len(hist))
            ]
        else:
            confidence_histogram = []

        # Daily trend (last 30 days)
        thirty_days_ago = datetime.datetime.utcnow() - datetime.timedelta(days=30)
        daily = (
            db.query(
                func.date(Prediction.timestamp).label('date'),
                func.count(Prediction.id).label('count')
            )
            .filter(Prediction.timestamp >= thirty_days_ago)
            .group_by(func.date(Prediction.timestamp))
            .all()
        )
        daily_trend = [{"date": str(d.date), "count": d.count} for d in daily]

        return {
            "total_predictions": total_predictions,
            "avg_confidence": round(float(avg_confidence), 4),
            "species_count": len(class_names),
            "most_detected": most_detected,
            "species_distribution": distribution,
            "confidence_histogram": confidence_histogram,
            "daily_trend": daily_trend,
            "classes": class_names,
        }
    finally:
        db.close()


@app.get("/model-metrics")
async def get_model_metrics():
    """Return model performance metrics from training."""
    if not model_metadata:
        raise HTTPException(status_code=404,
                            detail="No model metadata available. Train model first.")

    # Load evaluation report if available
    eval_report = {}
    report_path = os.path.join(MODELS_DIR, "evaluation", "classification_report.json")
    if os.path.exists(report_path):
        with open(report_path, 'r') as f:
            eval_report = json.load(f)

    return {
        "model_name": model_metadata.get("model_name", "Unknown"),
        "version": model_metadata.get("version", "1.0"),
        "architecture": model_metadata.get("architecture", "Unknown"),
        "accuracy": model_metadata.get("accuracy", 0),
        "precision": model_metadata.get("precision", 0),
        "recall": model_metadata.get("recall", 0),
        "f1_score": model_metadata.get("f1_score", 0),
        "auc": model_metadata.get("auc", 0),
        "total_params": model_metadata.get("total_params", 0),
        "training_samples": model_metadata.get("training_samples", 0),
        "validation_samples": model_metadata.get("validation_samples", 0),
        "training_date": model_metadata.get("training_date", None),
        "img_size": model_metadata.get("img_size", model_metadata.get("image_size", IMG_SIZE)),
        "num_classes": model_metadata.get("num_classes", len(class_names)),
        "class_names": class_names,
        "per_class_report": eval_report,
    }


# ============================================
# GEMINI SYSTEM PROMPT
# ============================================
WILDTRACK_SYSTEM_PROMPT = """You are the WildTrackAI assistant — an expert AI chatbot embedded in a wildlife footprint identification system built as a final-year computer science project.

## About the System
- **Project:** WildTrackAI — AI-powered animal footprint identification
- **Model:** EfficientNetB3 v4 (transfer learning from ImageNet, SE Attention)
- **Input:** 300×300 pixel footprint images
- **Accuracy:** 77.5% on 5 species (with TTA; 74.5% without TTA)
- **Training data:** 2,000 total images (1,600 train + 400 validation, balanced 400/class)
- **Data cleaning:** Perceptual hash deduplication, CLAHE normalization, corrupt image removal
- **Augmentation:** MixUp, CutMix, Random Erasing, SGDR warm restarts
- **Inference:** Test-Time Augmentation (3 passes)
- **Explainability:** Grad-CAM (Gradient-weighted Class Activation Mapping) heatmaps
- **Confidence threshold:** 40% — below this AND high entropy, species is marked "Unknown"
- **Backend:** FastAPI + SQLAlchemy + SQLite
- **Frontend:** React 18 + Vite + Tailwind CSS + Framer Motion

## Supported Species & Their Details
1. **Tiger** (Panthera tigris) — Endangered. Footprint: 12-16cm, round & asymmetric, no claw marks. Weight: 180-300kg. Habitat: tropical forests, mangroves.
2. **Leopard** (Panthera pardus) — Vulnerable. Footprint: 7-10cm, compact & round, no claw marks. Weight: 30-90kg. Habitat: diverse (forests, savannas, mountains).
3. **Elephant** (Elephas maximus) — Endangered. Footprint: 40-50cm, large & round, cracked skin pattern. Weight: 2,700-6,000kg. Habitat: forests, grasslands.
4. **Deer** (Cervidae family) — Least Concern. Footprint: 5-9cm, cloven hoof (two toes). Weight: 30-250kg. Habitat: forests, grasslands.
5. **Wolf** (Canis lupus) — Least Concern. Footprint: 10-13cm, oval with visible claw marks. Weight: 30-80kg. Habitat: forests, tundra, mountains.

## Key Technical Concepts
- **Grad-CAM:** Shows which regions of the image the CNN focused on. Red = high importance, Blue = low importance.
- **Transfer Learning:** EfficientNetB3 v4 pre-trained on ImageNet, fine-tuned on footprint images.
- **Confidence Threshold:** If confidence < 40% AND entropy > 90%, the species is classified as "Unknown" to avoid forced misclassification.
- **Closed-Set Classification:** The model can only predict among its 5 trained species. Unknown species (e.g., lion, bear) will be flagged as Unknown or mapped to the closest known class.
- **Softmax Overconfidence:** A known limitation where CNNs can assign high confidence to out-of-distribution inputs.
- **Per-class F1 scores:** Deer: 0.81, Elephant: 0.84, Leopard: 0.67, Tiger: 0.70, Wolf: 0.71

## Response Format (ALWAYS use this structure when analyzing predictions)
Always respond in these structured sections when a prediction is provided:
### 🔍 Prediction Analysis
### 📊 Confidence Interpretation
### 🧬 Footprint Characteristics
### ⚖️ Alternative Hypotheses
### 🌍 Ecological Insight
### 📌 Suggested Next Steps

For text-only questions, respond naturally but stay structured with markdown.

## Your Behavior Rules
- Be helpful, concise, and technically accurate
- Use Markdown formatting (bold, lists, emojis) for readability
- When discussing predictions, reference the actual data provided
- If asked about species NOT in the system, explain closed-set classification
- Never fabricate accuracy numbers or capabilities
- Stay focused on wildlife, footprints, conservation, and the system — politely redirect off-topic questions
- If a prediction is "unknown" (is_unknown=True), explain the threshold mechanism and suggest possible reasons
- When the user asks "why not X?", compare the predicted species features against X using the species data
"""


# ============================================
# SESSION MEMORY — lightweight conversational context
# ============================================
from collections import defaultdict
import time

_session_store = defaultdict(lambda: {
    "history": [],       # last N exchanges
    "last_prediction": None,
    "last_species": None,
    "created": time.time(),
})

MAX_HISTORY = 10  # keep last 10 exchanges per session


def _get_session(session_id: str) -> dict:
    """Get or create a session."""
    s = _session_store[session_id]
    # Expire sessions older than 1 hour
    if time.time() - s["created"] > 3600:
        _session_store[session_id] = {
            "history": [], "last_prediction": None,
            "last_species": None, "created": time.time(),
        }
    return _session_store[session_id]


def _update_session(session_id: str, user_msg: str, bot_msg: str, prediction: dict = None):
    """Update session with latest exchange."""
    s = _get_session(session_id)
    s["history"].append({"user": user_msg, "bot": bot_msg[:200]})
    if len(s["history"]) > MAX_HISTORY:
        s["history"] = s["history"][-MAX_HISTORY:]
    if prediction:
        s["last_prediction"] = prediction
        s["last_species"] = prediction.get("predicted_class", None)


# ============================================
# SPECIES FEATURE DATA — for structured reasoning
# ============================================
SPECIES_FEATURES = {
    "tiger": {
        "pad_shape": "large, bilobed rear pad",
        "toe_count": 4,
        "claw_marks": False,
        "symmetry": "asymmetric",
        "size_range": "12-16 cm",
        "gait_pattern": "direct register walk",
        "distinguishing": "Largest cat footprint. No claw marks. Asymmetric pad wider than long.",
        "confused_with": ["leopard", "lion"],
        "f1_score": 0.70,
    },
    "leopard": {
        "pad_shape": "compact, round, tri-lobed rear",
        "toe_count": 4,
        "claw_marks": False,
        "symmetry": "round",
        "size_range": "7-10 cm",
        "gait_pattern": "direct register walk",
        "distinguishing": "Smaller than tiger. Proportionally rounder. Retractable claws.",
        "confused_with": ["tiger", "cat"],
        "f1_score": 0.67,
    },
    "elephant": {
        "pad_shape": "large circular with cracked texture",
        "toe_count": 5,
        "claw_marks": False,
        "symmetry": "round",
        "size_range": "40-50 cm",
        "gait_pattern": "ambling",
        "distinguishing": "Largest land animal print. Cracked skin texture. Heavy soil compression.",
        "confused_with": [],
        "f1_score": 0.84,
    },
    "deer": {
        "pad_shape": "cloven hoof, two elongated toes",
        "toe_count": 2,
        "claw_marks": False,
        "symmetry": "bilaterally symmetric",
        "size_range": "5-9 cm",
        "gait_pattern": "bounding/walking",
        "distinguishing": "Two-toed cloven print. Dewclaws visible in soft ground. Pointed tips.",
        "confused_with": ["goat", "sheep"],
        "f1_score": 0.81,
    },
    "wolf": {
        "pad_shape": "oval with triangular heel pad",
        "toe_count": 4,
        "claw_marks": True,
        "symmetry": "oval, elongated",
        "size_range": "10-13 cm",
        "gait_pattern": "direct register trot",
        "distinguishing": "Visible claw marks. More elongated than dog. X-pattern between toes and pad.",
        "confused_with": ["dog", "coyote"],
        "f1_score": 0.71,
    },
}


# ============================================
# STRUCTURED FALLBACK ENGINE
# ============================================

def _confidence_interpretation(confidence: float, species: str) -> str:
    """Generate intelligent confidence interpretation."""
    f1 = SPECIES_FEATURES.get(species, {}).get("f1_score", 0.7)
    if confidence >= 0.85:
        return (f"**Very High Confidence** — The model is {confidence*100:.1f}% certain. "
                f"This species has an F1 score of {f1:.3f}, indicating reliable identification. "
                f"The footprint features strongly align with known {species} characteristics.")
    elif confidence >= 0.70:
        return (f"**High Confidence** — At {confidence*100:.1f}%, the model is fairly certain. "
                f"This is above the reliability threshold. Minor feature ambiguity is possible "
                f"but the primary identification is likely correct.")
    elif confidence >= 0.50:
        return (f"**Moderate Confidence** — At {confidence*100:.1f}%, the model's certainty is above "
                f"our 50% threshold but not conclusive. Consider factors like image quality, "
                f"partial print visibility, or substrate softness that may affect accuracy.")
    else:
        return (f"**Below Threshold** — At {confidence*100:.1f}%, the confidence falls below our "
                f"50% identification threshold. The model cannot reliably determine the species. "
                f"This may indicate an out-of-distribution species or non-footprint image.")


def _get_species_characteristics(species: str) -> str:
    """Generate observed features analysis for a species."""
    feat = SPECIES_FEATURES.get(species, {})
    info = ANIMAL_INFO.get(species, {})
    if not feat:
        return f"Limited feature data available for {species}."

    lines = []
    lines.append(f"• **Pad shape:** {feat['pad_shape']}")
    lines.append(f"• **Toe count:** {feat['toe_count']}")
    lines.append(f"• **Claw marks:** {'Visible' if feat['claw_marks'] else 'Not visible (retractable or absent)'}")
    lines.append(f"• **Print symmetry:** {feat['symmetry']}")
    lines.append(f"• **Expected size:** {feat['size_range']}")
    lines.append(f"• **Key identifier:** {feat['distinguishing']}")
    if info.get('habitat'):
        lines.append(f"• **Typical habitat:** {info['habitat']}")
    return "\n".join(lines)


def _get_alternative_analysis(top3: list, predicted: str) -> str:
    """Analyze alternative species with reasoning."""
    if not top3 or len(top3) < 2:
        return "No significant alternative candidates identified."
    lines = []
    for t in top3[1:]:
        alt = t["class"]
        conf = t["confidence"]
        feat = SPECIES_FEATURES.get(alt, {})
        reason = ""
        if feat:
            # Compare with predicted species
            pred_feat = SPECIES_FEATURES.get(predicted, {})
            if pred_feat:
                similarities = []
                if feat.get("toe_count") == pred_feat.get("toe_count"):
                    similarities.append("same toe count")
                if feat.get("claw_marks") == pred_feat.get("claw_marks"):
                    similarities.append("similar claw pattern")
                if similarities:
                    reason = f" (shares {', '.join(similarities)} with {predicted})"
        lines.append(f"• **{alt.title()}** — {conf*100:.1f}%{reason}")
        if feat.get("distinguishing"):
            lines.append(f"  _{feat['distinguishing']}_")
    return "\n".join(lines)


def _get_ecological_insight(species: str) -> str:
    """Generate ecological context."""
    info = ANIMAL_INFO.get(species, {})
    insights = {
        "tiger": "Tiger footprints are critical for population monitoring in tiger reserves. Each tiger has unique paw pad patterns, enabling individual identification — a key technique in Project Tiger conservation programs across India.",
        "leopard": "Leopards are the most adaptable big cats, found from rainforests to mountains. Their footprints near human settlements indicate corridor connectivity — vital for genetic diversity in fragmented habitats.",
        "elephant": "Elephant footprints can reveal age, size, and movement patterns. Tracking elephant corridors helps prevent human-elephant conflict and guides conservation of migration routes.",
        "deer": "Deer footprints are the most commonly found ungulate tracks. Their abundance indicates ecosystem health and forest regeneration patterns. Multiple deer tracks often signal nearby water sources.",
        "wolf": "Wolf tracks help monitor pack territories and population dynamics. The characteristic direct-register gait (rear paw landing in front paw print) distinguishes wolf trails from domestic dog paths.",
    }
    base = insights.get(species, f"Tracking {species} contributes to understanding population dynamics and habitat usage.")
    if info.get("conservation_status"):
        status = info["conservation_status"]
        if "Endangered" in status:
            base += f"\n\n🔴 **Conservation Alert:** {species.title()} is listed as {status}. Every tracked footprint contributes to population estimates critical for species survival."
        elif "Vulnerable" in status:
            base += f"\n\n🟡 **Conservation Note:** {species.title()} is {status}. Monitoring footprint distribution helps track population trends."
    return base


def _build_structured_prediction_response(prediction_result: dict) -> str:
    """Build a full structured analysis from prediction data — AI-grade without Gemini."""
    species = prediction_result.get("predicted_class", "unknown")
    confidence = prediction_result.get("confidence", 0)
    top3 = prediction_result.get("top3", [])
    is_unknown = prediction_result.get("is_unknown", False)
    raw_class = prediction_result.get("raw_class", species)

    sections = []

    # --- Section 1: Prediction Analysis ---
    sections.append("### 🔍 Prediction Analysis")
    if is_unknown:
        supported_species = ', '.join(c.title() for c in class_names) if class_names else 'N/A'
        sections.append(
            f"⚠️ **Result: Unknown Species**\n\n"
            f"The model could not confidently identify this footprint. "
            f"The highest probability class is **{raw_class.title()}** at only **{confidence*100:.1f}%**, "
            f"which falls below our **{int(CONFIDENCE_THRESHOLD*100)}% confidence threshold**.\n\n"
            f"**This can happen when:**\n"
            f"• The image is not a real animal footprint (cartoons, drawings, or non-footprint content)\n"
            f"• The species is outside our trained classes: **{supported_species}**\n"
            f"• The image quality is poor (blurry, overexposed, or the footprint is not centered)\n"
            f"• The footprint is heavily degraded or partially visible\n\n"
            f"The system marks this as **Unknown** to prevent forced misclassification — "
            f"a responsible AI safety practice."
        )
    else:
        info = ANIMAL_INFO.get(species, {})
        sci_name = info.get("scientific_name", "")
        sections.append(
            f"The model identifies this footprint as **{species.title()}** "
            f"({sci_name}) with **{confidence*100:.1f}%** confidence."
        )

    # --- Section 2: Confidence Interpretation ---
    sections.append("\n### 📊 Confidence Interpretation")
    analysis_species = raw_class if is_unknown else species
    sections.append(_confidence_interpretation(confidence, analysis_species))

    # --- Section 3: Footprint Characteristics ---
    sections.append("\n### 🧬 Key Footprint Characteristics")
    sections.append(_get_species_characteristics(analysis_species))

    # --- Section 4: Alternative Hypotheses ---
    sections.append("\n### ⚖️ Alternative Hypotheses")
    sections.append(_get_alternative_analysis(top3, analysis_species))

    # --- Section 5: Ecological Insight ---
    if not is_unknown:
        sections.append("\n### 🌍 Ecological Insight")
        sections.append(_get_ecological_insight(species))

    # --- Section 6: Suggested Next Steps ---
    sections.append("\n### 📌 Suggested Next Steps")
    if is_unknown:
        supported_species_str = ', '.join(c.title() for c in class_names) if class_names else 'N/A'
        sections.append(
            f"• 📷 Upload a **real footprint photo** (not drawings/cartoons) on natural substrate (soil/mud/sand)\n"
            f"• 📏 Measure the physical footprint size in centimeters for cross-referencing\n"
            f"• 🔍 Check the **Grad-CAM heatmap** — if it highlights background, the image may not contain a clear footprint\n"
            f"• 🐾 Our model supports: **{supported_species_str}** — other species will be marked unknown\n"
            f"• 💡 For best results, ensure the footprint is centered, well-lit, and fills most of the image frame"
        )
    else:
        sections.append(
            f"• Verify by comparing physical footprint size against expected range ({SPECIES_FEATURES.get(species, {}).get('size_range', 'N/A')})\n"
            f"• Check the **Grad-CAM heatmap** to see which features drove this prediction\n"
            f"• Upload additional angles of the same track for confirmation\n"
            f"• Use the **Compare** feature to match against other footprints"
        )

    return "\n".join(sections)


def _handle_contextual_query(message: str, session: dict) -> str:
    """Handle follow-up questions using session memory."""
    msg_lower = message.lower().strip()
    last_pred = session.get("last_prediction")

    if not last_pred:
        return None  # No context to reason about

    species = last_pred.get("predicted_class", "unknown")
    raw_class = last_pred.get("raw_class", species)
    confidence = last_pred.get("confidence", 0)
    top3 = last_pred.get("top3", [])
    is_unknown = last_pred.get("is_unknown", False)

    # "Why not X?" pattern
    why_not_matches = []
    for sp in SPECIES_FEATURES:
        if sp in msg_lower and sp != species and sp != raw_class:
            why_not_matches.append(sp)

    if ("why" in msg_lower or "not" in msg_lower or "instead" in msg_lower or "difference" in msg_lower) and why_not_matches:
        alt = why_not_matches[0]
        pred_sp = raw_class if is_unknown else species
        pred_feat = SPECIES_FEATURES.get(pred_sp, {})
        alt_feat = SPECIES_FEATURES.get(alt, {})

        lines = [f"### 🔬 Why {pred_sp.title()} and not {alt.title()}?\n"]

        # Find the alt's confidence in top3
        alt_conf = 0
        for t in top3:
            if t["class"] == alt:
                alt_conf = t["confidence"]
                break

        lines.append(f"The model assigned **{confidence*100:.1f}%** to {pred_sp.title()} "
                     f"vs **{alt_conf*100:.1f}%** to {alt.title()}.\n")
        lines.append("**Key differences:**\n")

        diffs = []
        if pred_feat.get("claw_marks") != alt_feat.get("claw_marks"):
            diffs.append(f"• **Claw marks:** {pred_sp.title()} {'shows' if pred_feat.get('claw_marks') else 'hides'} claws; "
                        f"{alt.title()} {'shows' if alt_feat.get('claw_marks') else 'hides'} claws")
        if pred_feat.get("toe_count") != alt_feat.get("toe_count"):
            diffs.append(f"• **Toe count:** {pred_sp.title()} has {pred_feat.get('toe_count')} toes; "
                        f"{alt.title()} has {alt_feat.get('toe_count')} toes")
        if pred_feat.get("size_range") != alt_feat.get("size_range"):
            diffs.append(f"• **Size range:** {pred_sp.title()} ({pred_feat.get('size_range', '?')}); "
                        f"{alt.title()} ({alt_feat.get('size_range', '?')})")
        if pred_feat.get("symmetry") != alt_feat.get("symmetry"):
            diffs.append(f"• **Shape:** {pred_sp.title()} is {pred_feat.get('symmetry', '?')}; "
                        f"{alt.title()} is {alt_feat.get('symmetry', '?')}")

        if diffs:
            lines.extend(diffs)
        else:
            lines.append(f"• These species have similar morphological features, which is why "
                        f"the confidence gap is narrow.")

        if pred_feat.get("distinguishing"):
            lines.append(f"\n**{pred_sp.title()} key identifier:** {pred_feat['distinguishing']}")
        if alt_feat.get("distinguishing"):
            lines.append(f"**{alt.title()} key identifier:** {alt_feat['distinguishing']}")

        return "\n".join(lines)

    # "Tell me more" / "more details" about last prediction
    if any(phrase in msg_lower for phrase in ["tell me more", "more detail", "more about", "explain more"]):
        pred_sp = raw_class if is_unknown else species
        info = ANIMAL_INFO.get(pred_sp, {})
        feat = SPECIES_FEATURES.get(pred_sp, {})
        lines = [f"### 📚 Detailed Profile: {pred_sp.title()}\n"]
        if info.get("scientific_name"):
            lines.append(f"**Scientific name:** {info['scientific_name']}")
        if info.get("description"):
            lines.append(f"\n{info['description']}")
        if feat:
            lines.append(f"\n**Track analysis:**")
            lines.append(_get_species_characteristics(pred_sp))
        if info.get("distribution"):
            lines.append(f"\n📍 **Distribution:** {info['distribution']}")
        lines.append(f"\n{_get_ecological_insight(pred_sp)}")
        return "\n".join(lines)

    # "How confident" / "is this reliable"
    if any(phrase in msg_lower for phrase in ["how confident", "reliable", "sure", "certain", "trust"]):
        pred_sp = raw_class if is_unknown else species
        lines = [f"### 📊 Confidence Deep-Dive\n"]
        lines.append(_confidence_interpretation(confidence, pred_sp))
        f1 = SPECIES_FEATURES.get(pred_sp, {}).get("f1_score", 0)
        if f1:
            lines.append(f"\n**Model reliability for {pred_sp.title()}:** F1 score = {f1:.3f}")
            if f1 >= 0.8:
                lines.append("This is one of our best-performing classes — predictions are generally reliable.")
            elif f1 >= 0.7:
                lines.append("Good performance. Occasional confusion with similar species is possible.")
            else:
                lines.append("This class has the most confusion with similar species. Cross-verify with physical measurements.")
        return "\n".join(lines)

    return None  # No contextual match


# ============================================
# CHAT ENDPOINT
# ============================================

def generate_chat_response(message: str, prediction_result: dict = None, session_id: str = "default") -> str:
    """Generate a contextual chat response using tiered intelligence."""
    session = _get_session(session_id)

    # ------ Build context for Gemini ------
    context_parts = []

    if prediction_result:
        species = prediction_result.get("predicted_class", "unknown")
        confidence = prediction_result.get("confidence", 0)
        top3 = prediction_result.get("top3", [])
        is_unknown = prediction_result.get("is_unknown", False)
        raw_class = prediction_result.get("raw_class", species)

        context_parts.append("## Current Prediction Context")
        if is_unknown:
            context_parts.append(f"- **Result:** UNKNOWN (confidence {confidence*100:.1f}% is below 50% threshold)")
            context_parts.append(f"- **Closest match (raw):** {raw_class}")
        else:
            context_parts.append(f"- **Predicted species:** {species}")
            context_parts.append(f"- **Confidence:** {confidence*100:.1f}%")

        if top3:
            context_parts.append("- **Top predictions:** " + ", ".join(
                f"{t['class']} ({t['confidence']*100:.1f}%)" for t in top3
            ))

        info = ANIMAL_INFO.get(raw_class if is_unknown else species, {})
        if info:
            context_parts.append(f"- **Species info:** {json.dumps({k: v for k, v in info.items() if k != 'description'}, default=str)}")

    # Add session history for Gemini context
    if session["history"]:
        context_parts.append("\n## Recent Conversation")
        for h in session["history"][-3:]:
            context_parts.append(f"User: {h['user']}")
            context_parts.append(f"Bot: {h['bot']}")

    prediction_context = "\n".join(context_parts) if context_parts else ""

    # ------ Tier 1: Try Gemini ------
    if gemini_model:
        try:
            user_prompt = message.strip() or "Analyze this footprint"
            if prediction_context:
                user_prompt = f"{prediction_context}\n\n**User message:** {user_prompt}"

            response = gemini_model.generate_content(
                [
                    {"role": "user", "parts": [f"System Instructions:\n{WILDTRACK_SYSTEM_PROMPT}"]},
                    {"role": "model", "parts": ["Understood. I'm the WildTrackAI assistant, ready to help with structured footprint analysis and species information."]},
                    {"role": "user", "parts": [user_prompt]},
                ],
                generation_config=genai.types.GenerationConfig(
                    max_output_tokens=1000,
                    temperature=0.7,
                ),
            )
            if response and response.text:
                result_text = response.text.strip()
                _update_session(session_id, message, result_text, prediction_result)
                return result_text
        except Exception as e:
            print(f"Gemini API error (falling back to local engine): {type(e).__name__}")

    # ------ Tier 2: Structured Local Engine ------

    # If we have a prediction, generate full structured analysis
    if prediction_result:
        result_text = _build_structured_prediction_response(prediction_result)
        _update_session(session_id, message, result_text, prediction_result)
        return result_text

    # Try contextual reasoning from session memory
    contextual = _handle_contextual_query(message, session)
    if contextual:
        _update_session(session_id, message, contextual)
        return contextual

    # ------ Tier 3: Knowledge base fallback ------
    result_text = _generate_knowledge_response(message)
    _update_session(session_id, message, result_text)
    return result_text


def _generate_knowledge_response(message: str) -> str:
    """Knowledge-base response for text-only queries."""
    msg_lower = message.lower().strip()

    if any(w in msg_lower for w in ['hello', 'hi ', 'hey', 'greetings', 'good morning', 'good evening']):
        return ("👋 **Welcome to WildTrackAI!**\n\n"
                "I'm your AI wildlife assistant. Here's what I can do:\n\n"
                "🔍 **Identify footprints** — Upload an image and get structured analysis\n"
                "📊 **Analyze predictions** — Confidence scores, alternatives, and reasoning\n"
                "🧬 **Compare species** — Ask \"why not leopard?\" after a prediction\n"
                "🌍 **Conservation info** — Habitats, status, and ecological insights\n"
                "🔬 **Technical details** — Model architecture, Grad-CAM, and methodology\n\n"
                "Try uploading a footprint image or ask about any species!")

    # Species info queries — enhanced
    for species_name, info in ANIMAL_INFO.items():
        if species_name in msg_lower:
            feat = SPECIES_FEATURES.get(species_name, {})
            lines = [f"### 🐾 {species_name.title()} ({info.get('scientific_name', 'N/A')})\n"]
            if info.get('description'):
                lines.append(info['description'])
            lines.append(f"\n**Track Profile:**")
            if feat:
                lines.append(_get_species_characteristics(species_name))
            if info.get('conservation_status'):
                status = info['conservation_status']
                emoji = '🔴' if 'Endangered' in status else '🟡' if 'Vulnerable' in status else '🟢'
                lines.append(f"\n{emoji} **Conservation status:** {status}")
            if info.get('weight'):
                lines.append(f"⚖️ **Weight:** {info['weight']}")
            if info.get('distribution'):
                lines.append(f"📍 **Range:** {info['distribution']}")
            if feat.get("confused_with"):
                lines.append(f"\n⚠️ **Often confused with:** {', '.join(c.title() for c in feat['confused_with'])}")
            if feat.get("f1_score"):
                lines.append(f"📊 **Model F1 score:** {feat['f1_score']:.3f}")
            return "\n".join(lines)

    # Help queries
    if any(w in msg_lower for w in ['help', 'what can you', 'how to', 'how do', 'features', 'capabilities']):
        return ("### 📖 WildTrackAI Guide\n\n"
                "**Image Analysis:**\n"
                "1. Upload a footprint image using the 📷 button\n"
                "2. Get structured analysis with confidence scores\n"
                "3. View Grad-CAM heatmaps showing model focus areas\n\n"
                "**Conversational Features:**\n"
                "• After a prediction, ask **\"why not leopard?\"** for comparison\n"
                "• Ask **\"tell me more\"** for deeper species info\n"
                "• Ask **\"how confident?\"** for reliability analysis\n\n"
                "**Species Database:**\n"
                f"• Trained on: {', '.join(c.title() for c in class_names)}\n"
                f"• Extended info for: {', '.join(k.title() for k in ANIMAL_INFO.keys())}\n\n"
                "**Technical Questions:**\n"
                "• Model architecture and accuracy\n"
                "• Grad-CAM explainability\n"
                "• Confidence thresholds and unknown detection")

    # Model / accuracy queries
    if any(w in msg_lower for w in ['accuracy', 'model', 'architecture', 'technical', 'how accurate']):
        acc = model_metadata.get('accuracy', 0.745)
        lines = [
            "### 🏗️ Model Architecture\n",
            f"**Base:** EfficientNetB3 v4 (transfer learning from ImageNet)",
            f"**Overall accuracy:** {acc*100:.1f}%",
            f"**Input size:** {IMG_SIZE}×{IMG_SIZE} pixels",
            f"**Classes:** {', '.join(c.title() for c in class_names)}\n",
            "**Per-class F1 Scores:**",
        ]
        for sp, feat in SPECIES_FEATURES.items():
            bar_len = int(feat['f1_score'] * 20)
            bar = '█' * bar_len + '░' * (20 - bar_len)
            lines.append(f"  {sp.title():10s} |{bar}| {feat['f1_score']:.3f}")
        lines.append(f"\n**Training pipeline:** MixUp/CutMix augmentation → CLAHE normalization → "
                     f"perceptual hash dedup → EfficientNetB3 v4 fine-tuning + SGDR + SWA")
        lines.append(f"**Explainability:** Grad-CAM heatmaps")
        lines.append(f"**OOD handling:** {int(CONFIDENCE_THRESHOLD*100)}% confidence threshold → Unknown class")
        return "\n".join(lines)

    # Grad-CAM queries
    if any(w in msg_lower for w in ['gradcam', 'grad-cam', 'heatmap', 'explain', 'xai', 'interpretab']):
        return ("### 🔬 Grad-CAM Explainability\n\n"
                "**Gradient-weighted Class Activation Mapping** visualizes which image regions "
                "influenced the model's prediction.\n\n"
                "**How it works:**\n"
                "1. Forward pass through EfficientNetB3\n"
                "2. Compute gradients of the predicted class w.r.t. final convolutional layer\n"
                "3. Weight feature maps by averaged gradients\n"
                "4. Generate heatmap overlay on original image\n\n"
                "**Reading the heatmap:**\n"
                "• 🔴 **Red/warm** = High importance (model focused here)\n"
                "• 🔵 **Blue/cool** = Low importance\n"
                "• Ideally, warm regions should highlight the footprint, not background\n\n"
                "**Why this matters:**\n"
                "If the heatmap highlights background instead of the footprint, "
                "the prediction may be unreliable — a key quality check for field deployment.")

    # Footprint queries
    if any(w in msg_lower for w in ['footprint', 'track', 'paw', 'print', 'identify']):
        return ("### 🐾 Footprint Identification Guide\n\n"
                "**Key distinguishing features:**\n\n"
                "| Feature | Cat family | Dog family | Ungulates |\n"
                "|---------|-----------|-----------|----------|\n"
                "| Claws | Hidden | Visible | Hooves |\n"
                "| Toes | 4, round | 4, oval | 2 (cloven) |\n"
                "| Pad | Large, bilobed | Triangular | None |\n\n"
                "**Size guide:**\n"
                "• Elephant: 40-50 cm (unmistakable)\n"
                "• Tiger: 12-16 cm\n"
                "• Wolf: 10-13 cm\n"
                "• Leopard: 7-10 cm\n"
                "• Deer: 5-9 cm\n\n"
                "Upload a footprint image for AI-powered identification!")

    # Conservation queries
    if any(w in msg_lower for w in ['conserv', 'endanger', 'protect', 'wildlife', 'iucn']):
        return ("### 🌍 Conservation & WildTrackAI\n\n"
                "**Species Conservation Status:**\n"
                "🔴 **Endangered:** Tiger, Elephant — critical population decline\n"
                "🟡 **Vulnerable:** Leopard — declining across range\n"
                "🟢 **Least Concern:** Deer, Wolf — stable populations\n\n"
                "**How footprint tracking helps:**\n"
                "• Non-invasive population monitoring\n"
                "• Individual identification (unique pad patterns)\n"
                "• Territory mapping and corridor identification\n"
                "• Human-wildlife conflict prevention\n\n"
                "AI-assisted tracking like WildTrackAI makes field surveys faster "
                "and more accessible to conservation teams globally.")

    # Comparison / difference queries
    if any(w in msg_lower for w in ['difference', 'compare', 'vs', 'versus']):
        return ("### 🔬 Species Comparison\n\n"
                "Upload two images using the **Compare** page for side-by-side analysis, "
                "or ask me about specific species:\n\n"
                "• \"What's the difference between tiger and leopard?\"\n"
                "• \"Tiger vs wolf footprints\"\n"
                "• Upload an image, then ask \"why not leopard?\"\n\n"
                "I'll provide detailed morphological comparisons!")

    # Unknown / threshold queries
    if any(w in msg_lower for w in ['unknown', 'threshold', 'reject', 'unseen', 'out of distribution']):
        return ("### ⚠️ Unknown Detection System\n\n"
                f"The model uses a **{int(CONFIDENCE_THRESHOLD*100)}% confidence threshold**:\n\n"
                f"• **Above {int(CONFIDENCE_THRESHOLD*100)}%** → Species identified normally\n"
                f"• **Below {int(CONFIDENCE_THRESHOLD*100)}%** → Marked as **Unknown** (responsible AI)\n\n"
                "**Why this matters:**\n"
                "• Prevents forced misclassification of unseen species\n"
                "• Flags poor-quality or non-footprint images\n"
                "• Shows the closest match and raw confidence for transparency\n\n"
                "**Limitations:**\n"
                "• Softmax can be overconfident on out-of-distribution inputs\n"
                "• Future improvements: temperature scaling, energy-based OOD detection")

    # Default
    return ("I'm your WildTrackAI assistant! I can help with:\n\n"
            "🔍 **Upload a footprint** for structured AI analysis\n"
            "🐾 **Ask about species** — tiger, leopard, elephant, deer, wolf\n"
            "📊 **Technical questions** — model, Grad-CAM, accuracy\n"
            "🌍 **Conservation** — status, tracking methods\n\n"
            "After a prediction, try:\n"
            "• _\"Why not leopard?\"_ — comparative reasoning\n"
            "• _\"Tell me more\"_ — detailed species profile\n"
            "• _\"How confident?\"_ — reliability deep-dive")


@app.post("/chat")
async def chat_endpoint(
    message: str = Form(""),
    file: Optional[UploadFile] = File(None),
    session_id: str = Form("default"),
):
    """Chat endpoint with tiered intelligence: Gemini → Structured Engine → Knowledge Base."""
    prediction = None

    # If image uploaded, run prediction
    if file and file.filename:
        if model is None:
            raise HTTPException(status_code=503,
                                detail="Model not loaded. Train the model first.")

        contents = await file.read()
        try:
            img_array, original, quality_metrics = preprocess_image(contents)
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Invalid image: {e}")

        result = predict_single(img_array, original, quality_metrics=quality_metrics)
        
        blur_level = quality_metrics.get('blur_level', 100)
        requires_field_validation = blur_level < 45

        # Save to DB
        pred_id = str(uuid.uuid4())[:8]
        save_path = os.path.join(UPLOADS_DIR, f"{pred_id}_{file.filename}")
        with open(save_path, 'wb') as f:
            f.write(contents)

        db = SessionLocal()
        try:
            pred = Prediction(
                id=pred_id,
                species=result["predicted_class"],
                confidence=result["confidence"],
                top3=json.dumps(result["top3"]),
                image_path=save_path,
                filename=file.filename,
                heatmap_generated=1 if result["heatmap"] else 0,
            )
            db.add(pred)
            db.commit()
        except Exception as e:
            print(f"DB error: {e}")
        finally:
            db.close()

        prediction = {
            "species": result["predicted_class"],
            "confidence": result["confidence"],
            "quality_adjusted_confidence": result.get("quality_adjusted_confidence", result["confidence"]),
            "requires_field_validation": requires_field_validation,
            "top3": result["top3"],
            "heatmap": result["heatmap"],
            "is_unknown": result.get("is_unknown", False),
            "raw_class": result.get("raw_class", result["predicted_class"]),
            "entropy": result.get("entropy", 0),
            "entropy_ratio": result.get("entropy_ratio", 0),
            "max_entropy": result.get("max_entropy", 0),
            "temperature": result.get("temperature", 1.0),
        }

        response_text = generate_chat_response(message or "Analyze this footprint", result, session_id)
    else:
        response_text = generate_chat_response(message, session_id=session_id)

    return {
        "response": response_text,
        "prediction": prediction,
    }


# ============================================
# PDF FIELD REPORT
# ============================================
@app.post("/report")
async def generate_report(file: UploadFile = File(...)):
    """Generate a PDF field report for a footprint prediction."""
    import io
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.units import mm
        from reportlab.lib.colors import HexColor
        from reportlab.pdfgen import canvas as pdf_canvas
        from reportlab.lib.utils import ImageReader
    except ImportError:
        raise HTTPException(status_code=500, detail="reportlab not installed. Run: pip install reportlab")

    # 1. Run prediction
    contents = await file.read()
    try:
        img_array, original, quality_metrics = preprocess_image(contents)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid image: {e}")
    pred_result = predict_single(img_array, original, quality_metrics=quality_metrics)

    # 2. Use heatmap from predict_single if available
    heatmap_b64 = pred_result.get("heatmap", None)

    # 3. Build PDF
    buf = io.BytesIO()
    c = pdf_canvas.Canvas(buf, pagesize=A4)
    w, h = A4
    orange = HexColor("#f97316")
    dark_gray = HexColor("#1f2937")
    light_gray = HexColor("#6b7280")

    # Header bar
    c.setFillColor(orange)
    c.rect(0, h - 80, w, 80, fill=True, stroke=False)
    c.setFillColor(HexColor("#ffffff"))
    c.setFont("Helvetica-Bold", 24)
    c.drawString(30, h - 50, "WildTrackAI Field Report")
    c.setFont("Helvetica", 10)
    c.drawString(30, h - 68, f"Generated: {datetime.datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')}")

    y = h - 110

    # Original image
    try:
        orig_pil = Image.fromarray(cv2.cvtColor(original, cv2.COLOR_BGR2RGB))
        orig_buf = io.BytesIO()
        orig_pil.resize((IMG_SIZE, IMG_SIZE)).save(orig_buf, format="PNG")
        orig_buf.seek(0)
        orig_reader = ImageReader(orig_buf)
        c.drawImage(orig_reader, 30, y - 180, width=180, height=180)
    except:
        pass

    # Heatmap image
    if heatmap_b64:
        try:
            hm_bytes = base64.b64decode(heatmap_b64)
            hm_reader = ImageReader(io.BytesIO(hm_bytes))
            c.drawImage(hm_reader, 230, y - 180, width=180, height=180)
            c.setFont("Helvetica", 8)
            c.setFillColor(light_gray)
            c.drawString(230, y - 190, "Grad-CAM Heatmap")
        except:
            pass

    y -= 210

    # Prediction details
    c.setFillColor(dark_gray)
    c.setFont("Helvetica-Bold", 16)
    species_label = pred_result.get("predicted_class", "Unknown")
    if pred_result.get("is_unknown"):
        species_label = f"Unknown (closest: {pred_result.get('raw_class', 'N/A')})"
    c.drawString(30, y, f"Species: {species_label.title()}")
    y -= 25

    c.setFont("Helvetica", 12)
    c.setFillColor(light_gray)
    confidence = pred_result.get("confidence", 0)
    c.drawString(30, y, f"Confidence: {confidence * 100:.1f}%")
    y -= 20

    entropy = pred_result.get("entropy", 0)
    entropy_ratio = pred_result.get("entropy_ratio", 0)
    c.drawString(30, y, f"Entropy: {entropy:.3f} bits | Uncertainty Ratio: {entropy_ratio * 100:.1f}%")
    y -= 20
    c.drawString(30, y, f"Temperature Scaling: T={pred_result.get('temperature', 1)}")
    y -= 35

    # Top-3 table
    c.setFillColor(dark_gray)
    c.setFont("Helvetica-Bold", 13)
    c.drawString(30, y, "Top-3 Predictions")
    y -= 5

    c.setStrokeColor(HexColor("#e5e7eb"))
    c.setLineWidth(0.5)
    c.line(30, y, w - 30, y)
    y -= 20

    top3 = pred_result.get("top3", [])
    for i, item in enumerate(top3):
        c.setFont("Helvetica-Bold" if i == 0 else "Helvetica", 11)
        c.setFillColor(orange if i == 0 else dark_gray)
        c.drawString(30, y, f"{i + 1}. {item['class'].title()}")
        c.setFillColor(light_gray)
        c.drawString(200, y, f"{item['confidence'] * 100:.1f}%")
        delta = item.get("delta", 0)
        if delta > 0:
            c.drawString(280, y, f"(\u0394 -{delta * 100:.1f}%)")
        
        # confidence bar
        bar_x, bar_w = 350, 180
        c.setFillColor(HexColor("#e5e7eb"))
        c.rect(bar_x, y - 2, bar_w, 10, fill=True, stroke=False)
        c.setFillColor(orange if i == 0 else HexColor("#9ca3af"))
        c.rect(bar_x, y - 2, bar_w * item["confidence"], 10, fill=True, stroke=False)
        y -= 22

    y -= 15

    # Footer
    c.setFillColor(HexColor("#9ca3af"))
    c.setFont("Helvetica", 8)
    c.drawString(30, 30, "WildTrackAI - AI-Powered Wildlife Footprint Identification System")
    c.drawString(30, 20, f"Model: EfficientNetB3 v4 | Input: {IMG_SIZE}x{IMG_SIZE} | Species: {len(class_names)} | Accuracy: {model_metadata.get('accuracy', 0) * 100:.1f}%")
    c.drawRightString(w - 30, 30, f"File: {file.filename}")

    c.save()
    buf.seek(0)

    return StreamingResponse(
        buf,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename=wildtrack_report_{datetime.datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.pdf"}
    )


# ============================================
# MAIN
# ============================================
if __name__ == "__main__":
    print("=" * 60)
    print("WILDTRACKAI - PRODUCTION SERVER")
    print("=" * 60)
    print(f"  API Docs: http://localhost:8000/docs")
    print(f"  Health:   http://localhost:8000/health")
    print("=" * 60)

    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=False,
    )
