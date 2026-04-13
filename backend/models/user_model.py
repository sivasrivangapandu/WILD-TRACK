"""
User model (fallback implementation).
"""
from datetime import datetime, timezone
import uuid

from database import Base


def _gen_id():
    return str(uuid.uuid4())


class User(Base):
    """User model - fallback implementation."""
    __tablename__ = "users"

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
        self.created_at = datetime.now(timezone.utc)
        self.updated_at = datetime.now(timezone.utc)
