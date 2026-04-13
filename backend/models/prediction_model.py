import datetime
import uuid

from database import Base


class Prediction(Base):
    """Prediction model - fallback implementation."""
    __tablename__ = "predictions"

    def __init__(self, species=None, confidence=None, **kwargs):
        self.id = str(uuid.uuid4())
        self.species = species
        self.confidence = confidence
        self.timestamp = datetime.datetime.utcnow()
        for key, val in kwargs.items():
            setattr(self, key, val)
