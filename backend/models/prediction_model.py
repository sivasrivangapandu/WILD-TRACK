import datetime
import uuid
from sqlalchemy import Column, String, Float, Integer, DateTime, Text

from database import Base


class Prediction(Base):
    __tablename__ = "predictions"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    species = Column(String, nullable=False)
    confidence = Column(Float, nullable=False)
    top3 = Column(Text, nullable=True)
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)
    image_path = Column(String, nullable=True)
    filename = Column(String, nullable=True)
    heatmap_generated = Column(Integer, default=0)
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    
    # V4 Research-Grade Metadata
    model_version = Column(String, nullable=True, default="v4")
    dataset_version = Column(String, nullable=True, default="v1.2-cleaned")
    accuracy_benchmark = Column(String, nullable=True)
    is_rejected = Column(Integer, default=0) # SQLite boolean equivalent
    needs_review = Column(Integer, default=0)
