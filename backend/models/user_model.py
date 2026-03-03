"""
User model — SQLAlchemy ORM for authentication.
"""
from sqlalchemy import Column, String, DateTime, Boolean, Text
from datetime import datetime, timezone
import uuid

from database import Base


def _gen_id():
    return str(uuid.uuid4())


class User(Base):
    __tablename__ = "users"

    id = Column(String, primary_key=True, default=_gen_id)
    name = Column(String(120), nullable=False)
    email = Column(String(255), nullable=False, unique=True, index=True)
    hashed_password = Column(String(255), nullable=False)
    avatar_url = Column(Text, nullable=True)
    role = Column(String(30), default="researcher")
    is_active = Column(Boolean, default=True)

    # Notification preferences (JSON-like simple columns)
    notify_predictions = Column(Boolean, default=True)
    notify_updates = Column(Boolean, default=True)
    notify_emails = Column(Boolean, default=False)

    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
