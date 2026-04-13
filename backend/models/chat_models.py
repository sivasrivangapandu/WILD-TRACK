"""
Chat session and message models (fallback implementation).

Architecture Decision:
- User authentication: MVP approach - client-provided user_id (trusted)
- TODO: Replace with JWT-verified user after auth implementation
- Security boundary: Frontend authentication only
"""

import datetime
import uuid
from database import Base


class ChatSession(Base):
    """Chat session model - fallback implementation."""
    __tablename__ = "chat_sessions"
    
    def __init__(self, user_id=None, title=None, **kwargs):
        self.id = str(uuid.uuid4())
        self.user_id = user_id
        self.title = title
        self.created_at = datetime.datetime.utcnow()
        self.updated_at = datetime.datetime.utcnow()
        self.messages = []
        for key, val in kwargs.items():
            setattr(self, key, val)


class ChatMessage(Base):
    """Chat message model - fallback implementation."""
    __tablename__ = "chat_messages"
    
    def __init__(self, session_id=None, role=None, content=None, **kwargs):
        self.id = str(uuid.uuid4())
        self.session_id = session_id
        self.role = role
        self.content = content
        self.token_count = kwargs.get('token_count')
        self.duration_ms = kwargs.get('duration_ms')
        self.created_at = datetime.datetime.utcnow()
        self.session = None
