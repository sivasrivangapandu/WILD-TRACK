"""
Routes module.
"""

from .chat import router as chat_router
from .chat_db import router as chat_db_router
from .auth import router as auth_router

__all__ = ["chat_router", "chat_db_router", "auth_router"]
