"""
WildTrackAI — Analytics & History Routes
==========================================
GET /history        - Prediction history
GET /analytics      - Dashboard analytics
GET /model-metrics  - Model performance metrics
"""

import os
import json
import datetime

import numpy as np
from fastapi import APIRouter, HTTPException, Query, Depends
from typing import Optional

from config import MODELS_DIR
from database import get_db
from models import Prediction
from services.prediction_service import model_metadata, class_names, IMG_SIZE

router = APIRouter()


@router.get("/history")
async def get_history(
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    species: Optional[str] = None,
    db: Session = Depends(get_db),
):
    """Get prediction history with optional filtering."""
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


@router.get("/analytics")
async def get_analytics(db: Session = Depends(get_db)):
    """Dashboard analytics data."""
    total_predictions = db.query(func.count(Prediction.id)).scalar() or 0
    avg_confidence = db.query(func.avg(Prediction.confidence)).scalar() or 0

    distribution = dict(
        db.query(Prediction.species, func.count(Prediction.id))
        .group_by(Prediction.species).all()
    )

    most_detected = max(distribution, key=distribution.get) if distribution else None

    all_confs = [p.confidence for p in db.query(Prediction.confidence).all()]
    if all_confs:
        hist, bin_edges = np.histogram(all_confs, bins=10, range=(0, 1))
        confidence_histogram = [
            {"range": f"{bin_edges[i]:.1f}-{bin_edges[i+1]:.1f}", "count": int(hist[i])}
            for i in range(len(hist))
        ]
    else:
        confidence_histogram = []

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


@router.get("/model-metrics")
async def get_model_metrics():
    """Return model performance metrics from training."""
    if not model_metadata:
        raise HTTPException(status_code=404, detail="No model metadata available.")

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
