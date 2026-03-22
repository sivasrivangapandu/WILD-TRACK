"""
WildTrackAI — Prediction Service
==================================
Model loading, downloading, prediction logic, and Cloudinary upload.
All ML-related globals are managed here.
"""

import os
import json

import numpy as np
from fastapi import HTTPException

from config import (
    MODELS_DIR, OUTPUTS_DIR, METADATA_PATH,
    MODEL_PATH_KERAS, MODEL_PATH, MODEL_PATH_LEGACY,
    MODEL_PATH_V4, MODEL_PATH_V3, MODEL_URLS,
    CONFIDENCE_THRESHOLD, ANIMAL_INFO, SPECIES_FEATURES,
    CLOUDINARY_URL, CLOUDINARY_CLOUD_NAME,
    CLOUDINARY_API_KEY, CLOUDINARY_API_SECRET,
)
from pipeline import pipeline
from consensus import compute_consensus

# ── Module-level globals ──────────────────────────────────────────
model = None
model_metadata = {}
class_names = []
gradcam = None
IMG_SIZE = 300  # Overridden by metadata

model_load_diagnostics = {
    "loaded_from": None,
    "attempted": [],
    "error": None,
}

model_download_status = {"status": "pending", "downloaded": [], "failed": []}

_cloudinary_initialized = False
_cloudinary_warned = False


# ── Cloudinary Upload ─────────────────────────────────────────────

def upload_to_cloudinary(contents: bytes, pred_id: str) -> str:
    """Upload bytes to Cloudinary when configured; otherwise return empty URL."""
    global _cloudinary_initialized, _cloudinary_warned

    if not CLOUDINARY_URL and not (CLOUDINARY_CLOUD_NAME and CLOUDINARY_API_KEY and CLOUDINARY_API_SECRET):
        if not _cloudinary_warned:
            print("  [WARN] Cloudinary credentials not set -- skipping Cloudinary uploads")
            _cloudinary_warned = True
        return ""

    try:
        import cloudinary
        import cloudinary.uploader

        if not _cloudinary_initialized:
            if CLOUDINARY_URL:
                cloudinary.config(cloudinary_url=CLOUDINARY_URL)
            else:
                normalized_cloud_name = CLOUDINARY_CLOUD_NAME.strip().lower().replace(" ", "")
                cloudinary.config(
                    cloud_name=normalized_cloud_name,
                    api_key=CLOUDINARY_API_KEY,
                    api_secret=CLOUDINARY_API_SECRET,
                    secure=True,
                )
            _cloudinary_initialized = True

        upload_result = cloudinary.uploader.upload(
            contents,
            public_id=f"pred_{pred_id}",
            folder="wildtrack_predictions",
            overwrite=True,
        )
        return upload_result.get("secure_url", "")
    except Exception as e:
        if not _cloudinary_warned:
            print(f"  [WARN] Cloudinary unavailable -- continuing without upload ({e})")
            _cloudinary_warned = True
        return ""


# ── Model Download ────────────────────────────────────────────────

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
            print(f"  OK Model exists: {filename} ({file_size:.1f} MB)")
            model_download_status["downloaded"].append(filename)
            continue

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
                print(f"  [OK] Downloaded {filename} ({size_mb:.1f} MB)")
                model_download_status["downloaded"].append(filename)
                break

            except Exception as e:
                print(f"  [ERROR] Attempt {attempt} failed: {e}")
                if attempt < max_retries:
                    wait_time = 2 ** attempt
                    print(f"  Retrying in {wait_time}s...")
                    sleep(wait_time)
                else:
                    print(f"  [ERROR] All download attempts failed for {filename}")
                    model_download_status["failed"].append(filename)
                    if os.path.exists(filepath):
                        os.remove(filepath)

    model_download_status["status"] = "completed" if not model_download_status["failed"] else "partial"


# ── Model Loading ─────────────────────────────────────────────────

def load_model():
    """Load the trained model and metadata at startup."""
    global model, model_metadata, class_names, gradcam, IMG_SIZE, model_load_diagnostics

    download_models_if_missing()

    import tensorflow as tf
    from tensorflow import keras
    from tensorflow.keras import layers

    @keras.utils.register_keras_serializable(package='WildTrackAI')
    class MobileNetPreprocess(layers.Layer):
        """MobileNetV2 preprocessing: scale [0,255] -> [-1,1]."""
        def call(self, x):
            x = tf.cast(x, tf.float32)
            return (x / 127.5) - 1.0

    candidate_files = [
        p for p in [MODEL_PATH_KERAS, MODEL_PATH, MODEL_PATH_LEGACY, MODEL_PATH_V4, MODEL_PATH_V3]
        if os.path.exists(p)
    ]

    if not candidate_files:
        print("WARNING: No trained model found!")
        for p in [MODEL_PATH_KERAS, MODEL_PATH, MODEL_PATH_LEGACY, MODEL_PATH_V4, MODEL_PATH_V3]:
            print(f"  Checked: {p}")
        print("  Run training first: python training/train.py")
        model_load_diagnostics = {
            "loaded_from": None, "attempted": [], "error": "No trained model file found",
        }
        return

    custom_objects = {'MobileNetPreprocess': MobileNetPreprocess}

    try:
        from training.train_v4 import FocalLoss
        custom_objects['FocalLoss'] = FocalLoss
    except ImportError:
        try:
            from training.train_v3 import FocalLoss
            custom_objects['FocalLoss'] = FocalLoss
        except ImportError:
            pass

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
    model_load_diagnostics = {"loaded_from": None, "attempted": [], "error": None}

    for model_file in candidate_files:
        file_size_mb = os.path.getsize(model_file) / (1024 * 1024)
        model_load_diagnostics["attempted"].append({
            "path": model_file, "size_mb": round(file_size_mb, 2),
        })
        print(f"Loading model: {model_file} ({file_size_mb:.1f} MB)")
        try:
            load_kwargs = dict(compile=False, custom_objects=custom_objects)
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


# ── Prediction Logic ──────────────────────────────────────────────

def predict_single(img_array, original_image=None, generate_heatmap=True, use_tta=True,
                   quality_metrics=None, lat=None, lon=None):
    """Run prediction on a single preprocessed image.

    Applies Test-Time Augmentation (TTA) for improved accuracy.
    Applies temperature scaling for calibrated softmax confidence.
    If max confidence < CONFIDENCE_THRESHOLD -> unknown.
    """
    if quality_metrics is None:
        quality_metrics = {}
    if model is None:
        raise HTTPException(status_code=503, detail="Model not loaded. Train model first.")

    def class_threshold(class_name: str, base_threshold: float) -> float:
        """Per-class confidence floor: harder classes require stronger evidence."""
        f1 = SPECIES_FEATURES.get(class_name, {}).get("f1_score", 0.72)
        if f1 >= 0.82:
            return max(base_threshold, 0.46)
        if f1 >= 0.76:
            return max(base_threshold, 0.50)
        if f1 >= 0.70:
            return max(base_threshold, 0.55)
        return max(base_threshold, 0.60)

    # Test-Time Augmentation
    tta_predict_fn = None
    if use_tta:
        try:
            from training.train_v4 import tta_predict
            tta_predict_fn = tta_predict
            raw_probs = tta_predict_fn(model, img_array, n_augments=3)
        except ImportError:
            raw_probs = model.predict(img_array, verbose=0)[0]
    else:
        raw_probs = model.predict(img_array, verbose=0)[0]

    # Stage 3: Geo-aware logical filtering
    filtered_probs = pipeline.stage3_geo_filter(raw_probs, lat, lon, class_names)

    # Stage 4: Temperature scaling
    TEMPERATURE = 1.2
    predictions = pipeline.stage4_calibrate_confidence(filtered_probs, TEMPERATURE)

    # Shannon entropy — uncertainty quantification
    entropy = float(-np.sum(predictions * np.log2(predictions + 1e-10)))
    max_entropy = float(np.log2(len(predictions)))
    entropy_ratio = entropy / max_entropy if max_entropy > 0 else 0.0

    print(f"\n[DIAG] Raw Probs (TTA={use_tta}):")
    for i, p in enumerate(raw_probs):
        print(f"  {class_names[i]}: {p:.4f}")
    print(f"[DIAG] Calibrated Probs (T=1.2):")
    for i, p in enumerate(predictions):
        print(f"  {class_names[i]}: {p:.4f}")

    predicted_idx = int(np.argmax(predictions))
    confidence = float(predictions[predicted_idx])
    sorted_idx = np.argsort(predictions)[::-1]
    second_confidence = float(predictions[sorted_idx[1]]) if len(sorted_idx) > 1 else 0.0
    margin = confidence - second_confidence

    if use_tta and tta_predict_fn is not None and (confidence < 0.62 or margin < 0.10):
        try:
            extra_raw_probs = tta_predict_fn(model, img_array, n_augments=7)
            extra_filtered_probs = pipeline.stage3_geo_filter(extra_raw_probs, lat, lon, class_names)
            extra_predictions = pipeline.stage4_calibrate_confidence(extra_filtered_probs, TEMPERATURE)
            predictions = (predictions + extra_predictions) / 2.0
            predictions = predictions / np.sum(predictions)

            predicted_idx = int(np.argmax(predictions))
            confidence = float(predictions[predicted_idx])
            sorted_idx = np.argsort(predictions)[::-1]
            second_confidence = float(predictions[sorted_idx[1]]) if len(sorted_idx) > 1 else 0.0
            margin = confidence - second_confidence
        except Exception as e:
            print(f"[DIAG] Adaptive TTA refinement skipped: {e}")

    raw_class = class_names[predicted_idx] if predicted_idx < len(class_names) else "unknown"

    # Adaptive confidence scaling
    quality_adjusted_confidence = confidence
    confidence_penalty = 1.0

    blur_level = quality_metrics.get('blur_level', 100)
    gamma_applied = quality_metrics.get('gamma_applied', False)

    if blur_level < 45:
        confidence_penalty *= 0.75
    elif blur_level < 60:
        confidence_penalty *= 0.90

    if gamma_applied:
        confidence_penalty *= 0.95

    quality_adjusted_confidence = confidence * confidence_penalty

    # Unknown threshold with ambiguity-aware gating.
    HIGH_ENTROPY_THRESHOLD = 0.90
    dynamic_conf_threshold = CONFIDENCE_THRESHOLD
    if blur_level < 45:
        dynamic_conf_threshold = max(dynamic_conf_threshold, 0.55)
    elif blur_level < 60:
        dynamic_conf_threshold = max(dynamic_conf_threshold, 0.50)

    if entropy_ratio > 0.82:
        dynamic_conf_threshold = max(dynamic_conf_threshold, 0.55)
    if margin < 0.08:
        dynamic_conf_threshold = max(dynamic_conf_threshold, 0.58)
    elif margin < 0.15:
        dynamic_conf_threshold = max(dynamic_conf_threshold, 0.50)

    dynamic_conf_threshold = max(dynamic_conf_threshold, class_threshold(raw_class, CONFIDENCE_THRESHOLD))
    if raw_class in {"tiger", "leopard", "wolf"} and margin < 0.18:
        dynamic_conf_threshold = max(dynamic_conf_threshold, 0.60)

    base_unknown = confidence < CONFIDENCE_THRESHOLD and entropy_ratio > HIGH_ENTROPY_THRESHOLD
    ambiguous_unknown = quality_adjusted_confidence < dynamic_conf_threshold and (entropy_ratio > 0.78 or margin < 0.12)
    is_unknown = base_unknown or ambiguous_unknown
    predicted_class = "unknown" if is_unknown else raw_class

    # Top 3
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

    # AI Consensus Validation
    try:
        second_opinion_raw = model.predict(img_array, verbose=0)[0]
        so_filtered = pipeline.stage3_geo_filter(second_opinion_raw, lat, lon, class_names)
        so_calibrated = pipeline.stage4_calibrate_confidence(so_filtered, TEMPERATURE)
        consensus_result = compute_consensus(predictions, so_calibrated, class_names, CONFIDENCE_THRESHOLD)

        if consensus_result and consensus_result.get("verdict_level") == "ambiguous":
            if quality_adjusted_confidence < 0.65 or margin < 0.12:
                is_unknown = True
                predicted_class = "unknown"
    except Exception as e:
        print(f"Consensus validation error: {e}")
        consensus_result = None

    return {
        "predicted_class": predicted_class,
        "raw_class": raw_class,
        "confidence": confidence,
        "quality_adjusted_confidence": round(quality_adjusted_confidence, 4),
        "is_unknown": is_unknown,
        "margin": round(margin, 4),
        "dynamic_conf_threshold": round(dynamic_conf_threshold, 4),
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
