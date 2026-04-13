"""
WildTrackAI — Reports & Legacy Chat Routes
=============================================
POST /report   - PDF field report generation
POST /chat     - Legacy chat endpoint
"""

import os
import io
import json
import uuid
import base64
import datetime
from typing import Optional

import cv2
import numpy as np
from PIL import Image
from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Depends
from fastapi.responses import StreamingResponse

from config import UPLOADS_DIR
from database import get_db
from models import Prediction
from services.image_processing import preprocess_image
from services.prediction_service import (
    model, model_metadata, class_names, predict_single, IMG_SIZE,
)
from services.chat_service import generate_chat_response

router = APIRouter()


@router.post("/report")
async def generate_report(file: UploadFile = File(...)):
    """Generate a PDF field report for a footprint prediction."""
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.units import mm
        from reportlab.lib.colors import HexColor
        from reportlab.pdfgen import canvas as pdf_canvas
        from reportlab.lib.utils import ImageReader
    except ImportError:
        raise HTTPException(status_code=500, detail="reportlab not installed. Run: pip install reportlab")

    contents = await file.read()
    try:
        img_array, original, quality_metrics, _stage1_meta = preprocess_image(contents)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid image: {e}")
    pred_result = predict_single(img_array, original, quality_metrics=quality_metrics)

    heatmap_b64 = pred_result.get("heatmap", None)

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
    except Exception:
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
        except Exception:
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


@router.post("/chat")
async def chat_endpoint(
    message: str = Form(""),
    file: Optional[UploadFile] = File(None),
    session_id: str = Form("default"),
    db: Session = Depends(get_db),
):
    """Chat endpoint with tiered intelligence: Gemini → Structured Engine → Knowledge Base."""
    prediction = None

    if file and file.filename:
        if model is None:
            raise HTTPException(status_code=503, detail="Model not loaded. Train the model first.")

        contents = await file.read()
        try:
            img_array, original, quality_metrics, _stage1_meta = preprocess_image(contents)
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Invalid image: {e}")

        result = predict_single(img_array, original, quality_metrics=quality_metrics)

        blur_level = quality_metrics.get('blur_level', 100)
        requires_field_validation = blur_level < 45

        pred_id = str(uuid.uuid4())[:8]
        save_path = os.path.join(UPLOADS_DIR, f"{pred_id}_{file.filename}")
        with open(save_path, 'wb') as f:
            f.write(contents)

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

        response_text = generate_chat_response(
            message or "Analyze this footprint", result, session_id, class_names=class_names
        )
    else:
        response_text = generate_chat_response(message, session_id=session_id, class_names=class_names)

    return {
        "response": response_text,
        "prediction": prediction,
    }
