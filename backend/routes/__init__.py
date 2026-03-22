"""
Routes module — registers all API routers.
"""

from .chat import router as chat_router
from .chat_db import router as chat_db_router
from .auth import router as auth_router
from .predictions import router as predictions_router
from .species import router as species_router
from .analytics import router as analytics_router
from .reports import router as reports_router

__all__ = [
    "chat_router",
    "chat_db_router",
    "auth_router",
    "predictions_router",
    "species_router",
    "analytics_router",
    "reports_router",
]
