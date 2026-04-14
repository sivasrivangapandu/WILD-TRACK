"""
Enhanced Prediction Service
============================
Provides:
1. Image type classification (animal/human/thing/other)
2. Confidence-based filtering
3. Multi-model ensemble predictions
4. Improved accuracy with preprocessing
"""

import numpy as np
import cv2
from PIL import Image
from typing import Dict, List, Tuple, Optional
import logging

logger = logging.getLogger(__name__)

# Image type categories
IMAGE_TYPES = {
    "animal": ["deer", "elephant", "leopard", "tiger", "wolf"],
    "human": ["person", "human", "face", "people"],
    "thing": ["vehicle", "object", "building", "structure", "tool", "equipment"],
    "other": ["landscape", "plant", "water", "sky", "unknown"]
}

class ImageTypeClassifier:
    """Classify images into: animal/human/thing/other"""
    
    @staticmethod
    def classify_by_features(predictions: Dict) -> str:
        """Classify image type based on model predictions and confidence"""
        if not predictions or "predictions" not in predictions:
            return "other"
        
        preds = predictions["predictions"]
        if not preds:
            return "other"
        
        top_class = preds[0].get("class", "").lower()
        confidence = preds[0].get("confidence", 0)
        
        # If high confidence with known classes
        if confidence > 0.7:
            for category, classes in IMAGE_TYPES.items():
                if any(c in top_class for c in classes):
                    return category
        
        return "other"
    
    @staticmethod
    def classify_by_image_analysis(image_array: np.ndarray) -> Tuple[str, float]:
        """Heuristic image analysis to detect humans/animals/things"""
        try:
            # Convert to HSV for better color detection
            if len(image_array.shape) == 3:
                hsv = cv2.cvtColor(image_array, cv2.COLOR_RGB2HSV)
            else:
                return "thing", 0.5
            
            # Detect skin tones (for humans)
            lower_skin = np.array([0, 20, 70], dtype=np.uint8)
            upper_skin = np.array([20, 255, 255], dtype=np.uint8)
            skin_mask = cv2.inRange(hsv, lower_skin, upper_skin)
            skin_ratio = np.sum(skin_mask) / (image_array.shape[0] * image_array.shape[1])
            
            if skin_ratio > 0.15:
                return "human", 0.7 + (skin_ratio * 0.2)
            
            # Detect fur/natural colors (for animals)
            # Browns, tans, grays typical of animals
            lower_natural = np.array([8, 30, 40], dtype=np.uint8)
            upper_natural = np.array([35, 200, 200], dtype=np.uint8)
            natural_mask = cv2.inRange(hsv, lower_natural, upper_natural)
            natural_ratio = np.sum(natural_mask) / (image_array.shape[0] * image_array.shape[1])
            
            if natural_ratio > 0.25:
                return "animal", 0.6 + (natural_ratio * 0.3)
            
            # High saturation and bright colors indicate objects/things
            saturation = hsv[:,:,1].mean() / 255.0
            brightness = hsv[:,:,2].mean() / 255.0
            
            if saturation > 0.5 and brightness > 0.4:
                return "thing", 0.65
            
            return "other", 0.5
            
        except Exception as e:
            logger.warning(f"Error in image analysis: {e}")
            return "other", 0.5


class ConfidenceFilter:
    """Filter predictions based on confidence thresholds"""
    
    # Minimum confidence thresholds by prediction type
    THRESHOLDS = {
        "animal": 0.4,      # Lower for animals - harder to detect
        "human": 0.3,       # Very low for humans
        "thing": 0.35,      # Lower for objects
        "other": 0.3        # Low confidence for unknowns
    }
    
    # What to do when confidence is low
    MIN_CONFIDENCE_FOR_PREDICTION = 0.4
    MIN_CONFIDENCE_FOR_SPECIES = 0.5
    
    @staticmethod
    def is_confident(predictions: List[Dict], image_type: str = "animal") -> bool:
        """Check if predictions meet confidence threshold"""
        if not predictions:
            return False
        
        top_pred = predictions[0]
        confidence = top_pred.get("confidence", 0)
        threshold = ConfidenceFilter.THRESHOLDS.get(image_type, 0.4)
        
        return confidence >= threshold
    
    @staticmethod
    def filter_predictions(predictions: List[Dict], image_type: str = "animal", 
                          top_k: int = 5) -> List[Dict]:
        """Filter and rank predictions by confidence"""
        if not predictions:
            return []
        
        threshold = ConfidenceFilter.THRESHOLDS.get(image_type, 0.4)
        
        # Filter by threshold
        filtered = [p for p in predictions if p.get("confidence", 0) >= threshold]
        
        # Sort by confidence (descending)
        filtered.sort(key=lambda x: x.get("confidence", 0), reverse=True)
        
        # Return top K
        return filtered[:top_k]
    
    @staticmethod
    def boost_confidence(confidence: float, image_type: str, quality_score: float = 1.0) -> float:
        """Boost confidence based on image quality and type"""
        boosted = confidence * (0.95 + quality_score * 0.05)
        
        # Cap at 0.99 to avoid overconfidence
        return min(boosted, 0.99)


class PredictionEnhancer:
    """Enhance predictions with multiple strategies"""
    
    @staticmethod
    def apply_ensemble_boost(predictions: List[Dict], weights: List[float] = None) -> List[Dict]:
        """Combine multiple model predictions (if available)"""
        if not predictions or len(predictions) < 2:
            return predictions
        
        if weights is None:
            # Equal weights by default
            weights = [1/len(predictions) for _ in predictions]
        
        # Group by class
        class_scores = {}
        for pred, weight in zip(predictions, weights):
            class_name = pred.get("class", "unknown")
            confidence = pred.get("confidence", 0)
            
            if class_name not in class_scores:
                class_scores[class_name] = 0
            class_scores[class_name] += confidence * weight
        
        # Create ensemble predictions
        ensemble_preds = [
            {
                "class": class_name,
                "confidence": min(score, 0.99),  # Cap at 0.99
                "method": "ensemble",
                "boost_factor": 1.2
            }
            for class_name, score in sorted(
                class_scores.items(), 
                key=lambda x: x[1], 
                reverse=True
            )
        ]
        
        return ensemble_preds
    
    @staticmethod
    def calculate_image_quality(image_array: np.ndarray) -> float:
        """Calculate image quality score (0-1)"""
        try:
            # Check sharpness (Laplacian variance)
            if len(image_array.shape) == 3:
                gray = cv2.cvtColor(image_array, cv2.COLOR_RGB2GRAY)
            else:
                gray = image_array
            
            laplacian_var = cv2.Laplacian(gray, cv2.CV_64F).var()
            sharpness_score = min(laplacian_var / 500, 1.0)  # Normalize
            
            # Check brightness (not too dark, not too bright)
            brightness = np.mean(gray) / 255.0
            brightness_score = 1.0 - abs(0.5 - brightness) * 2  # Peak at 0.5
            brightness_score = max(brightness_score, 0)
            
            # Check contrast
            contrast = np.std(gray) / 255.0
            contrast_score = min(contrast / 0.3, 1.0)
            
            # Combine scores
            quality = (sharpness_score * 0.4 + brightness_score * 0.3 + contrast_score * 0.3)
            
            return quality
        except Exception as e:
            logger.warning(f"Error calculating image quality: {e}")
            return 0.5


class PredictionPostProcessor:
    """Post-process predictions for better results"""
    
    @staticmethod
    def enrich_prediction(prediction: Dict, image_array: np.ndarray = None,
                         image_type: str = "animal") -> Dict:
        """Enrich prediction with additional metadata"""
        
        enriched = prediction.copy()
        
        if image_array is not None:
            # Add image quality score
            quality = PredictionEnhancer.calculate_image_quality(image_array)
            enriched["image_quality"] = round(quality, 3)
            
            # Boost confidence based on quality
            original_conf = enriched.get("confidence", 0)
            boosted_conf = ConfidenceFilter.boost_confidence(original_conf, image_type, quality)
            enriched["confidence_boosted"] = round(boosted_conf, 3)
            enriched["confidence_boost_factor"] = round(boosted_conf / original_conf, 2)
        
        # Add interpretation
        confidence = enriched.get("confidence", 0)
        if confidence > 0.8:
            enriched["certainty_level"] = "Very High"
        elif confidence > 0.6:
            enriched["certainty_level"] = "High"
        elif confidence > 0.4:
            enriched["certainty_level"] = "Medium"
        else:
            enriched["certainty_level"] = "Low"
        
        return enriched
    
    @staticmethod
    def create_response(predictions: List[Dict], image_type: str = "animal",
                       quality_score: float = 1.0) -> Dict:
        """Create a comprehensive prediction response"""
        
        # Filter by confidence
        filtered = ConfidenceFilter.filter_predictions(predictions, image_type)
        
        if not filtered:
            return {
                "success": False,
                "message": f"Low confidence predictions for {image_type} - please try another image",
                "image_type": image_type,
                "confidence_threshold_failed": True,
                "predictions": []
            }
        
        # Enrich top predictions
        enriched = [
            PredictionPostProcessor.enrich_prediction(pred, image_type=image_type)
            for pred in filtered
        ]
        
        # Get top prediction
        top_pred = enriched[0]
        
        return {
            "success": True,
            "primary_prediction": {
                "class": top_pred.get("class"),
                "confidence": top_pred.get("confidence"),
                "confidence_boosted": top_pred.get("confidence_boosted"),
                "certainty_level": top_pred.get("certainty_level"),
                "image_quality": top_pred.get("image_quality")
            },
            "alternative_predictions": enriched[1:6],  # Top 5 alternatives
            "image_type": image_type,
            "quality_score": round(quality_score, 3),
            "predictions": enriched
        }
