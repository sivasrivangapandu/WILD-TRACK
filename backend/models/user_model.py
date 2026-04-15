"""
User model (fallback implementation - plain Python class, no SQLAlchemy).
"""
from datetime import datetime, timezone
import uuid


def _gen_id():
    return str(uuid.uuid4())


class User:
    """User model - fallback implementation (plain Python class)."""
    __tablename__ = "users"

    def __init__(self, name=None, email=None, hashed_password=None, **kwargs):
        """Initialize User with provided attributes."""
        self.id = kwargs.get('id', _gen_id())
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
        self.created_at = kwargs.get('created_at') or datetime.now(timezone.utc)
        self.updated_at = kwargs.get('updated_at') or datetime.now(timezone.utc)
        
        # Set any additional attributes
        for key, val in kwargs.items():
            if not hasattr(self, key):
                setattr(self, key, val)
