import os
import cv2
import numpy as np
import imagehash
from PIL import Image
from typing import Tuple, Dict, Any, Optional

# YOLO is imported lazily to avoid slow startup
YOLO_AVAILABLE = False
YOLO = None

def _load_yolo_class():
    """Lazy-load ultralytics YOLO to avoid blocking server startup."""
    global YOLO_AVAILABLE, YOLO
    if YOLO is not None:
        return
    try:
        from ultralytics import YOLO as _YOLO
        YOLO = _YOLO
        YOLO_AVAILABLE = True
    except ImportError:
        YOLO_AVAILABLE = False


class InferencePipeline:
    """
    WildTrackAI Multi-Stage Inference Pipeline.
    
    Stages:
    1. Data Quality (Blur & pHash Duplicate Detection)
    2. Stage 1: YOLO Object Detection (crop to footprint)
    3. Stage 2: Classifier (pass cropped image to ResNet/EfficientNet)
    4. Stage 3: Geo-Aware Filtering logic
    5. Stage 4: Confidence Calibration (Temperature Scaling)
    """

    def __init__(self, yolo_model_path: Optional[str] = None):
        self.yolo_model = None
        if yolo_model_path and os.path.exists(yolo_model_path):
            _load_yolo_class()  # Lazy import
            if YOLO_AVAILABLE and YOLO is not None:
                try:
                    self.yolo_model = YOLO(yolo_model_path)
                    print(f"✅ YOLO Object Detector initialized: {yolo_model_path}")
                except Exception as e:
                    print(f"⚠️ Failed to load YOLO model: {e}")
            else:
                print("⚠️ ultralytics not installed. Stage 1 detection will be bypassed.")
        else:
            print("⚠️ YOLO not initialized. Stage 1 detection will be bypassed.")

        # Cache of seen hashes for duplicate detection (In production, use Redis/DB)
        self.seen_hashes = set()

    def generate_phash(self, image: np.ndarray) -> str:
        """Generate Perceptual Hash for duplicate detection."""
        # Convert CV2 BGR to PIL Image
        img_pil = Image.fromarray(cv2.cvtColor(image, cv2.COLOR_BGR2RGB))
        return str(imagehash.phash(img_pil))

    def check_duplicate(self, phash: str) -> bool:
        """Check if image hash has been processed recently (avoids redundant inference)."""
        if phash in self.seen_hashes:
            return True
        self.seen_hashes.add(phash)
        return False

    def detect_blur(self, image: np.ndarray, threshold: float = 100.0) -> Tuple[float, bool]:
        """Detect image blurriness using Laplacian variance."""
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if len(image.shape) == 3 else image
        laplacian_var = cv2.Laplacian(gray, cv2.CV_64F).var()
        blur_level = min(100.0, max(0.0, laplacian_var / 5.0))
        is_blurry = blur_level < threshold
        return blur_level, is_blurry

    def stage1_detect_and_crop(self, image: np.ndarray) -> Tuple[np.ndarray, Dict[str, Any]]:
        """
        Stage 1: Use YOLO to detect the footprint and crop the image.
        If YOLO is not available or detects nothing, return original image.
        """
        stage1_meta = {"yolo_used": False, "bounding_box": None, "confidence": 0.0}

        if self.yolo_model is None:
            return image, stage1_meta

        # Run YOLO inference
        results = self.yolo_model(image, verbose=False)
        if len(results) > 0 and len(results[0].boxes) > 0:
            # Get highest confidence box
            boxes = results[0].boxes
            best_box = boxes[0]  # Assuming highest conf is first, or sort by conf
            
            x1, y1, x2, y2 = map(int, best_box.xyxy[0].tolist())
            conf = float(best_box.conf[0])
            
            # Crop image
            cropped_image = image[y1:y2, x1:x2]
            
            stage1_meta["yolo_used"] = True
            stage1_meta["bounding_box"] = [x1, y1, x2, y2]
            stage1_meta["confidence"] = conf
            return cropped_image, stage1_meta
            
        return image, stage1_meta

    def stage3_geo_filter(self, predictions: list, lat: Optional[float], lon: Optional[float], class_names: list) -> list:
        """
        Stage 3: Geo-Aware Filtering.
        If GPS is provided, zero out probabilities for species physiologically impossible in that region.
        """
        if lat is None or lon is None:
            return predictions

        # Simple bounding box logic for continents (Placeholder logic)
        # e.g., India roughly: Lat 8 to 37, Lon 68 to 97
        is_india = (8.0 <= lat <= 37.0) and (68.0 <= lon <= 97.0)
        # e.g., Africa roughly: Lat -35 to 37, Lon -17 to 51
        is_africa = (-35.0 <= lat <= 37.0) and (-17.0 <= lon <= 51.0)
        
        filtered_probs = np.array(predictions)
        
        for idx, cls in enumerate(class_names):
            if cls == "tiger" and is_africa:
                filtered_probs[idx] = 0.0  # Tigers are not in Africa
            elif cls == "elephant" and not (is_india or is_africa):
                filtered_probs[idx] = 0.0  # Wild elephants only in Africa/Asia

        # Re-normalize if we changed anything
        if np.sum(filtered_probs) > 0:
            filtered_probs = filtered_probs / np.sum(filtered_probs)
            
        return filtered_probs.tolist()

    def stage4_calibrate_confidence(self, raw_probs: np.ndarray, temperature: float = 1.2) -> np.ndarray:
        """
        Stage 4: Temperature scaling to calibrate confidence output.
        Reverses softmax, scales logits, and reapplies softmax.
        """
        # Add epsilon to prevent log(0)
        logits = np.log(np.array(raw_probs) + 1e-10)
        scaled_logits = logits / temperature
        
        # Softmax
        exp_logits = np.exp(scaled_logits - np.max(scaled_logits))
        calibrated_probs = exp_logits / np.sum(exp_logits)
        
        return calibrated_probs

# Instantiate a global pipeline object to be used by the app
# In production, we'd provide a real path to a footprint YOLO model
pipeline = InferencePipeline(yolo_model_path=None)
