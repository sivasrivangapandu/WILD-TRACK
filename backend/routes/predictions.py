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
import base64
import re
from typing import List, Optional, Any

from fastapi import APIRouter, UploadFile, File, Form, HTTPException, BackgroundTasks, Depends
import cv2
import numpy as np
import google.generativeai as genai

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


def _extract_json_object(text: str) -> Optional[dict]:
    """Extract JSON object from Gemini text that may include markdown wrappers."""
    if not text:
        return None

    cleaned = text.strip().replace("```json", "").replace("```", "").strip()
    try:
        parsed = json.loads(cleaned)
        if isinstance(parsed, dict):
            return parsed
    except Exception:
        pass

    match = re.search(r"\{[\s\S]*\}", cleaned)
    if match:
        try:
            parsed = json.loads(match.group(0))
            if isinstance(parsed, dict):
                return parsed
        except Exception:
            return None
    return None


def _normalize_is_footprint(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    if isinstance(value, str):
        return value.strip().lower() in {"true", "yes", "1"}
    return False


def _is_obvious_non_footprint(image_bytes: bytes) -> Optional[str]:
    """Fast local block for obvious non-footprint uploads (faces/people/screenshots)."""
    nparr = np.frombuffer(image_bytes, np.uint8)
    img_color = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    if img_color is None:
        return "Unreadable image data"

    gray = cv2.cvtColor(img_color, cv2.COLOR_BGR2GRAY)

    face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")
    profile_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_profileface.xml")
    body_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_upperbody.xml")

    if not face_cascade.empty():
        faces = face_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=4, minSize=(40, 40))
        if len(faces) > 0:
            return "Human face detected"

    if not profile_cascade.empty():
        profiles = profile_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=4, minSize=(40, 40))
        if len(profiles) > 0:
            return "Human profile detected"

    if not body_cascade.empty():
        bodies = body_cascade.detectMultiScale(gray, scaleFactor=1.08, minNeighbors=4, minSize=(60, 60))
        if len(bodies) > 0:
            return "Human upper body detected"

    # Screenshot-like images often have many long straight edges.
    edges = cv2.Canny(gray, 80, 180)
    lines = cv2.HoughLinesP(edges, 1, np.pi / 180, threshold=120, minLineLength=90, maxLineGap=8)
    line_count = len(lines) if lines is not None else 0
    if line_count > 80:
        return "Likely screenshot or UI image"

    return None


def validate_is_footprint_strict(image_bytes: bytes) -> dict:
    """Strict validator: reject non-footprints and fail closed on validation errors."""
    local_reason = _is_obvious_non_footprint(image_bytes)
    if local_reason:
        return {"is_footprint": False, "reason": local_reason}

    gemini_api_key = os.getenv("GEMINI_API_KEY", "").strip()
    if not gemini_api_key:
        return {"is_footprint": False, "reason": "Footprint validation unavailable (missing Gemini key)"}

    try:
        genai.configure(api_key=gemini_api_key)

        nparr = np.frombuffer(image_bytes, np.uint8)
        img_cv = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        if img_cv is not None:
            h, w = img_cv.shape[:2]
            scale = min(1.0, 512 / max(h, w))
            if scale < 1.0:
                img_cv = cv2.resize(img_cv, (int(w * scale), int(h * scale)), interpolation=cv2.INTER_AREA)
            _, buffer = cv2.imencode(".jpg", img_cv, [cv2.IMWRITE_JPEG_QUALITY, 85])
            image_b64 = base64.b64encode(buffer).decode("utf-8")
        else:
            image_b64 = base64.b64encode(image_bytes).decode("utf-8")

        gemini_model = genai.GenerativeModel("gemini-1.5-flash")
        prompt = (
            "Analyze this image strictly. Reply ONLY with a raw JSON object and nothing else. "
            "Format: {\"is_footprint\": true_or_false, \"reason\": \"one sentence\"}. "
            "Set is_footprint=true only for clear animal paw/hoof/claw tracks in natural substrate. "
            "Set is_footprint=false for people, human faces, selfies, screenshots, UI, drawings, "
            "vehicles, buildings, indoor scenes, or any non-footprint content."
        )

        response = gemini_model.generate_content(
            [{"mime_type": "image/jpeg", "data": image_b64}, prompt],
            generation_config=genai.types.GenerationConfig(temperature=0.0),
        )

        text = (getattr(response, "text", "") or "").strip()
        parsed = _extract_json_object(text)

        if parsed is not None:
            return {
                "is_footprint": _normalize_is_footprint(parsed.get("is_footprint", False)),
                "reason": str(parsed.get("reason", "Validation complete")),
            }

        lowered = text.lower()
        if "not" in lowered and "footprint" in lowered:
            return {"is_footprint": False, "reason": "Model marked image as non-footprint"}
        if "footprint" in lowered and "not" not in lowered:
            return {"is_footprint": True, "reason": "Model marked image as footprint"}

        return {"is_footprint": False, "reason": "Invalid validator response format"}
    except Exception as exc:
        print(f"[Validation Error] {exc}")
        return {"is_footprint": False, "reason": "Footprint validation failed"}


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
    

    validation = validate_is_footprint_strict(contents)
    if not validation.get("is_footprint", False):
        raise HTTPException(
            status_code=422,
            detail={
                "error": "not_a_footprint",
                "message": f"Footprint not detected. {validation.get('reason', '')}",
            },
        )

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
    # Note: increased brightness threshold to 210 (actual snow) and removed tiger to prevent false swaps.
    if result.get("predicted_class") in ["leopard"]:
        wolf_item = next((item for item in result.get("top3", []) if item["class"] == "wolf"), None)
        if wolf_item and wolf_item["confidence"] > 0.25:
            brightness = quality_metrics.get("brightness", 0) if quality_metrics else 0
            if brightness > 210:
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
            validation = validate_is_footprint_strict(contents)
            if not validation.get("is_footprint", False):
                raise HTTPException(
                    status_code=422,
                    detail={
                        "error": "not_a_footprint",
                        "message": f"Footprint not detected. {validation.get('reason', '')}",
                    },
                )

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
        except HTTPException as e:
            results.append({"filename": file.filename, "error": e.detail})
        except Exception as e:
            results.append({"filename": file.filename, "error": str(e)})

    return {
        "total": len(files),
        "successful": len([r for r in results if "error" not in r]),
        "failed": len([r for r in results if "error" in r]),
        "results": results,
    }
