import os
import shutil
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from database import SessionLocal
from models import Prediction
from typing import List, Optional

router = APIRouter(prefix="/mlops", tags=["MLOps & Active Learning"])

# Paths for Hard Negative mining
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HARD_NEGATIVES_DIR = os.path.join(BASE_DIR, "dataset_hard_negatives")
os.makedirs(HARD_NEGATIVES_DIR, exist_ok=True)


class ReviewUpdate(BaseModel):
    action: str  # "approve", "reject", "correct"
    corrected_species: Optional[str] = None


@router.get("/review-queue")
async def get_review_queue(limit: int = 50, offset: int = 0):
    """Fetch images that fell below the confidence threshold and need human review."""
    db = SessionLocal()
    try:
        # Get items needing review, sorted by lowest confidence first to prioritize hard cases
        query = db.query(Prediction).filter(Prediction.needs_review == 1)
        total = query.count()
        items = query.order_by(Prediction.confidence.asc()).offset(offset).limit(limit).all()
        
        return {
            "total": total,
            "items": [
                {
                    "id": item.id,
                    "filename": item.filename,
                    "image_path": f"/uploads/{os.path.basename(item.image_path)}" if item.image_path else None,
                    "predicted_species": item.species,
                    "confidence": item.confidence,
                    "timestamp": item.timestamp.isoformat() if item.timestamp else None
                } for item in items
            ]
        }
    finally:
        db.close()

@router.post("/review/{pred_id}")
async def submit_review(pred_id: str, review: ReviewUpdate):
    """
    Human-in-the-Loop review endpoint.
    If corrected, the image is moved to the hard negatives dataset for active learning.
    """
    db = SessionLocal()
    try:
        prediction = db.query(Prediction).filter(Prediction.id == pred_id).first()
        if not prediction:
            raise HTTPException(status_code=404, detail="Prediction not found")
            
        if review.action == "approve":
            prediction.needs_review = 0
            prediction.is_rejected = 0
            # Kept original prediction
        elif review.action == "reject":
            prediction.needs_review = 0
            prediction.is_rejected = 1
        elif review.action == "correct":
            if not review.corrected_species:
                raise HTTPException(status_code=400, detail="Must provide corrected_species")
            
            old_species = prediction.species
            prediction.species = review.corrected_species
            prediction.needs_review = 0
            prediction.is_rejected = 0
            
            # ACTIVE LEARNING: Hard Negative Mining
            # Move the image to the hard_negatives folder for the next training cycle
            if prediction.image_path and os.path.exists(prediction.image_path):
                species_dir = os.path.join(HARD_NEGATIVES_DIR, review.corrected_species)
                os.makedirs(species_dir, exist_ok=True)
                
                # Copy file prefixed with 'hn_' (hard negative)
                new_filename = f"hn_{os.path.basename(prediction.image_path)}"
                dest_path = os.path.join(species_dir, new_filename)
                
                try:
                    shutil.copy2(prediction.image_path, dest_path)
                    print(f"🎯 Hard Negative saved: {dest_path}")
                except Exception as e:
                    print(f"Error saving hard negative: {e}")

        db.commit()
        return {"status": "success", "action": review.action, "id": pred_id}
    finally:
        db.close()


@router.get("/analytics")
async def get_analytics():
    """Research-grade analytics for the ML Dashboard."""
    db = SessionLocal()
    try:
        from sqlalchemy import func
        
        total_predictions = db.query(Prediction).count()
        total_rejected = db.query(Prediction).filter(Prediction.is_rejected == 1).count()
        total_needs_review = db.query(Prediction).filter(Prediction.needs_review == 1).count()
        
        # Average confidence per species
        conf_by_species = db.query(
            Prediction.species, 
            func.avg(Prediction.confidence).label('avg_conf')
        ).filter(Prediction.is_rejected == 0).group_by(Prediction.species).all()
        
        # Hard negatives collected
        hard_negatives_count = sum([len(files) for r, d, files in os.walk(HARD_NEGATIVES_DIR)])
        
        return {
            "total_predictions": total_predictions,
            "total_rejected": total_rejected,
            "total_needs_review": total_needs_review,
            "rejection_rate": round(total_rejected / total_predictions * 100, 2) if total_predictions > 0 else 0,
            "hard_negatives_mined": hard_negatives_count,
            "average_confidence_by_species": {
                species: round(float(conf), 4) for species, conf in conf_by_species if conf is not None
            }
        }
    finally:
        db.close()
