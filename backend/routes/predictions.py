"""
WildTrackAI — Prediction Routes
=================================
POST /predict          - Single image prediction
POST /predict/batch    - Batch prediction
"""

import os
import json
import uuid
import datetime
from typing import List, Optional, Any

from fastapi import APIRouter, UploadFile, File, Form, HTTPException, BackgroundTasks, Depends

from config import UPLOADS_DIR, CONFIDENCE_THRESHOLD, ANIMAL_INFO
from database import get_db
from models import Prediction
from services.image_processing import preprocess_image
from services.prediction_service import (
    model, model_metadata, class_names, model_download_status,
    predict_single, upload_to_cloudinary,
)

# Type alias for database connection (using sqlite3 in fallback mode)
Session = Any

router = APIRouter()


@router.post("/predict")
async def predict(
    file: UploadFile = File(...),
    latitude: Optional[float] = Form(None),
    longitude: Optional[float] = Form(None),
    db: Session = Depends(get_db),
):
    """Predict animal species from footprint image with preprocessing robustness."""
    if model is None:
        download_status = model_download_status.get("status", "unknown")
        if download_status == "downloading":
            raise HTTPException(status_code=503, detail="Model is still downloading. Please wait.")
        elif download_status == "partial":
            raise HTTPException(status_code=503, detail="Model download incomplete.")
        else:
            raise HTTPException(status_code=503, detail="Model not loaded. Check server logs.")

    contents = await file.read()
    try:
        img_array, original, quality_metrics, stage1_meta = preprocess_image(contents, expansion_margin=0.15)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid image: {e}")

    result = predict_single(img_array, original, quality_metrics=quality_metrics, lat=latitude, lon=longitude)

    # Dynamic crop evaluation for ambiguous snow tracks
    if (stage1_meta.get("yolo_used") and result.get("confidence", 0) < 0.60
            and result.get("predicted_class") in ["leopard", "wolf", "tiger", "dog", "fox", "cat", "unknown"]):
        try:
            print("  [DIAG] Ambiguous track detected. Running fallback evaluation...")
            img_array_fb, original_fb, quality_metrics_fb, stage1_meta_fb = preprocess_image(contents, expansion_margin=0.0)
            result_fb = predict_single(img_array_fb, original_fb, quality_metrics=quality_metrics_fb, lat=latitude, lon=longitude)

            result["fallback_meta"] = {
                "initial_pred": result.get("predicted_class"),
                "initial_conf": result.get("confidence", 0),
                "fb_pred": result_fb.get("predicted_class"),
                "fb_conf": result_fb.get("confidence", 0)
            }

            if result_fb.get("confidence", 0) > result.get("confidence", 0):
                result_fb["fallback_meta"] = result["fallback_meta"]
                result_fb["fallback_used"] = True
                result = result_fb
        except Exception as e:
            print(f"  [DIAG] Fallback evaluation failed: {e}")

    # Snow track heuristic
    if result.get("predicted_class") in ["leopard", "tiger"]:
        wolf_item = next((item for item in result.get("top3", []) if item["class"] == "wolf"), None)
        if wolf_item and wolf_item["confidence"] > 0.15:
            brightness = quality_metrics.get("brightness", 0) if quality_metrics else 0
            if brightness > 130:
                print(f"  [DIAG] Snow/Wolf heuristic triggered. Brightness: {brightness:.1f}.")
                result["predicted_class"] = "wolf"
                result["species"] = "wolf"
                result["raw_class"] = "wolf"
                result["confidence"] = float(wolf_item["confidence"])
                result["quality_adjusted_confidence"] = round(float(wolf_item["confidence"]), 4)
                result["heuristic_applied"] = "snow_wolf_correction"

                top3 = result.get("top3", [])
                for item in top3:
                    item["_sort_conf"] = 1.0 if item["class"] == "wolf" else item["confidence"]
                top3.sort(key=lambda x: x["_sort_conf"], reverse=True)
                top_conf = top3[0]["confidence"]
                for item in top3:
                    item.pop("_sort_conf", None)
                    item["delta"] = round(top_conf - item["confidence"], 4)
                result["top3"] = top3

    blur_level = quality_metrics.get('blur_level', 100)
    requires_field_validation = blur_level < 45

    needs_review = 1 if result.get("quality_adjusted_confidence", 1.0) < CONFIDENCE_THRESHOLD or result["is_unknown"] else 0

    pred_id = str(uuid.uuid4())[:8]
    image_url = upload_to_cloudinary(contents, pred_id)

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
            is_rejected=1 if requires_field_validation else 0,
        )
        db.add(prediction)
        db.commit()
    except Exception as e:
        print(f"DB error: {e}")

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
        "image_quality": quality_metrics,
    }


@router.post("/predict/batch")
async def predict_batch(
    files: List[UploadFile] = File(...),
    db: Session = Depends(get_db),
):
    """Batch prediction for multiple images."""
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

            image_url = upload_to_cloudinary(contents, pred_id)

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
            except Exception as e:
                print(f"DB error: {e}")

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
            results.append({"filename": file.filename, "error": str(e)})

    return {
        "total": len(files),
        "successful": len([r for r in results if "error" not in r]),
        "failed": len([r for r in results if "error" in r]),
        "results": results,
    }
