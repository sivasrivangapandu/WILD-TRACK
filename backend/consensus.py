"""
WildTrackAI — AI Consensus Validation System
=============================================
Implements "Second Opinion" via multi-path inference:
  Path A: TTA-augmented prediction (primary model)
  Path B: Single-pass prediction (second opinion)

If both paths agree → "Verified Detection"
If they disagree → "Ambiguous – Requires Review"

This simulates an internal panel of AI experts debating the result.
"""
import numpy as np
from typing import Dict, Any, List


def compute_consensus(
    primary_probs: np.ndarray,
    second_opinion_probs: np.ndarray,
    class_names: List[str],
    confidence_threshold: float = 0.40,
) -> Dict[str, Any]:
    """
    Compare two independent prediction paths and produce a consensus verdict.

    Args:
        primary_probs:       Calibrated probabilities from TTA path (float32 array)
        second_opinion_probs: Raw probabilities from single-pass path (float32 array)
        class_names:         List of class label strings
        confidence_threshold: Minimum confidence for a valid detection

    Returns:
        Dict with consensus analysis fields.
    """
    primary_probs = np.array(primary_probs)
    second_opinion_probs = np.array(second_opinion_probs)

    # Primary prediction
    primary_idx = int(np.argmax(primary_probs))
    primary_class = class_names[primary_idx] if primary_idx < len(class_names) else "unknown"
    primary_conf = float(primary_probs[primary_idx])

    # Second opinion prediction
    so_idx = int(np.argmax(second_opinion_probs))
    so_class = class_names[so_idx] if so_idx < len(class_names) else "unknown"
    so_conf = float(second_opinion_probs[so_idx])

    # Agreement check
    agreement = primary_class == so_class

    # Disagreement score: difference between the two models' max confidences
    disagreement_score = abs(primary_conf - so_conf)

    # Cross-model confidence: what does the second opinion think about the primary's choice?
    cross_confidence = float(second_opinion_probs[primary_idx]) if primary_idx < len(second_opinion_probs) else 0.0

    # Confidence stability: are both models similarly confident?
    confidence_stable = disagreement_score < 0.15

    # ── Final verdict logic ──
    if agreement and primary_conf >= 0.75 and confidence_stable:
        verdict = "Verified Detection"
        verdict_level = "verified"
    elif agreement and primary_conf >= 0.60:
        verdict = "Consensus Reached"
        verdict_level = "consensus"
    elif agreement and primary_conf >= confidence_threshold:
        verdict = "Weak Consensus"
        verdict_level = "weak"
    elif not agreement and primary_conf >= 0.70 and cross_confidence >= 0.50:
        verdict = "Primary Dominant"
        verdict_level = "dominant"
    elif not agreement:
        verdict = "Ambiguous – Requires Review"
        verdict_level = "ambiguous"
    else:
        verdict = "Insufficient Confidence"
        verdict_level = "insufficient"

    # Find the alternative species (second opinion's top pick if different)
    alternative = None
    if not agreement:
        alternative = {
            "species": so_class,
            "confidence": round(so_conf, 4),
        }

    return {
        "primary_prediction": primary_class,
        "primary_confidence": round(primary_conf, 4),
        "second_opinion_prediction": so_class,
        "second_opinion_confidence": round(so_conf, 4),
        "agreement": agreement,
        "disagreement_score": round(disagreement_score, 4),
        "cross_confidence": round(cross_confidence, 4),
        "confidence_stable": confidence_stable,
        "alternative": alternative,
        "verdict": verdict,
        "verdict_level": verdict_level,
    }
