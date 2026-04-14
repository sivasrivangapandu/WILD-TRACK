"""
User model (SQLAlchemy ORM with fallback implementation).
"""
from datetime import datetime, timezone
import uuid

from sqlalchemy import Column, String, Boolean, DateTime, Text
from database import Base


def _gen_id():
    return str(uuid.uuid4())


class User(Base):
    """User model - SQLAlchemy ORM implementation."""
    __tablename__ = "users"

    # Define columns for SQLAlchemy ORM
    id = Column(String(36), primary_key=True, default=_gen_id)
    name = Column(String(255), nullable=False)
    email = Column(String(255), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=False)
    avatar_url = Column(String(500))
    role = Column(String(50), default="researcher")
    is_active = Column(Boolean, default=True)
    notify_predictions = Column(Boolean, default=True)
    notify_updates = Column(Boolean, default=True)
    notify_emails = Column(Boolean, default=False)
    bio = Column(Text)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    def __init__(self, name=None, email=None, hashed_password=None, **kwargs):
        self.id = _gen_id()
        self.name = name
        self.email = email
        self.hashed_password = hashed_password
        self.avatar_url = kwargs.get('avatar_url')
        self.role = kwargs.get('role', 'researcher')
        self.is_active = kwargs.get('is_active', True)
        self.notify_predictions = kwargs.get('notify_predictions', True)
        self.notify_updates = kwargs.get('notify_updates', True)
        self.notify_emails = kwargs.get('notify_emails', False)
        self.bio = kwargs.get('bio')
        self.created_at = datetime.now(timezone.utc)
        self.updated_at = datetime.now(timezone.utc)
