"""
WildTrackAI — Production FastAPI Backend
==========================================
Slim application entry point.
All business logic is in services/ and routes/.

Usage:
    python main.py
    uvicorn main:app --host 0.0.0.0 --port 8000
"""

import os
import datetime
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import uvicorn

from config import BASE_DIR, CORS_ORIGINS, NINJA_API_KEY
from database import SessionLocal, init_db, DB_PATH

# ── Database Initialization ──────────────────────────────────────
init_db()

# ── Startup / Shutdown ───────────────────────────────────────────
_startup_time = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Load model on startup."""
    global _startup_time
    _startup_time = datetime.datetime.utcnow()

    # Import here to avoid circular imports at module level
    from services.prediction_service import load_model
    load_model()

    yield
    print("Shutting down...")


# ── FastAPI App ──────────────────────────────────────────────────
app = FastAPI(
    title="WildTrackAI API",
    description="AI-powered animal footprint identification system with MobileNetV2 v4-cpu (85.8% accuracy)",
    version="2.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Register Routers ─────────────────────────────────────────────
from routes import (
    chat_router, chat_db_router, auth_router,
    predictions_router, species_router, analytics_router, reports_router,
)
from routes.mlops import router as mlops_router

app.include_router(chat_router)
app.include_router(chat_db_router)
app.include_router(auth_router)
app.include_router(predictions_router)
app.include_router(species_router)
app.include_router(analytics_router)
app.include_router(reports_router)
app.include_router(mlops_router)

# ── Static Files ─────────────────────────────────────────────────
_avatar_dir = os.path.join(BASE_DIR, "uploads", "avatars")
os.makedirs(_avatar_dir, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=os.path.join(BASE_DIR, "uploads")), name="uploads")


# ── Core Endpoints (kept inline — they reference app-level state) ─


@app.api_route("/", methods=["GET", "HEAD"])
async def root(request: Request):
    """Root endpoint for Render base URL checks."""
    if request.method == "HEAD":
        return Response(status_code=200)
    return {
        "service": "WildTrackAI API",
        "status": "running",
        "version": "2.1.0",
        "endpoints": {
            "health": "/health",
            "readiness": "/ready",
            "system_status": "/api/system/status",
            "docs": "/docs",
        }
    }


@app.api_route("/health", methods=["GET", "HEAD"])
async def health_check(request: Request):
    """System health check with model download status."""
    from services.prediction_service import (
        model, model_load_diagnostics, model_download_status,
        class_names, gradcam,
    )
    from services.chat_service import gemini_model

    if request.method == "HEAD":
        return Response(status_code=200)

    is_healthy = model is not None and model_download_status.get("status") != "partial"

    return {
        "status": "healthy" if is_healthy else "degraded",
        "model_loaded": model is not None,
        "model_load_diagnostics": model_load_diagnostics,
        "model_download_status": model_download_status,
        "gradcam_available": gradcam is not None,
        "classes": len(class_names),
        "class_names": class_names if len(class_names) <= 10 else class_names[:10],
        "database": os.path.exists(DB_PATH),
        "gemini_ai": gemini_model is not None,
        "ninja_api": bool(NINJA_API_KEY),
        "timestamp": datetime.datetime.utcnow().isoformat(),
    }


@app.get("/ready")
async def readiness_check():
    """Readiness probe — only returns 200 when model is loaded."""
    from services.prediction_service import model
    from fastapi import HTTPException

    if model is None:
        raise HTTPException(status_code=503, detail="Service not ready - model still loading")
    return {"ready": True, "status": "operational"}


@app.get("/api/system/status")
async def system_status():
    """Production system status — model version, accuracy, TTA, uptime."""
    from services.prediction_service import model, model_metadata, class_names, IMG_SIZE

    now = datetime.datetime.utcnow()
    uptime_seconds = (now - _startup_time).total_seconds() if _startup_time else 0
    hours, remainder = divmod(int(uptime_seconds), 3600)
    minutes, seconds = divmod(remainder, 60)
    return {
        "model_version": model_metadata.get("version", "unknown"),
        "model_name": model_metadata.get("model_name", "WildTrackAI"),
        "architecture": model_metadata.get("architecture") or model_metadata.get("backbone", "unknown"),
        "validation_accuracy": model_metadata.get("accuracy", 0),
        "precision": model_metadata.get("precision", 0),
        "recall": model_metadata.get("recall", 0),
        "f1_score": model_metadata.get("f1_score", 0),
        "tta_enabled": True,
        "tta_passes": 3,
        "total_classes": len(class_names),
        "class_names": class_names,
        "img_size": IMG_SIZE,
        "uptime": f"{hours}h {minutes}m {seconds}s",
        "uptime_seconds": int(uptime_seconds),
        "status": "operational" if model is not None else "degraded",
        "timestamp": now.isoformat(),
    }


# ── Main ─────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("=" * 60)
    print("WILDTRACKAI - PRODUCTION SERVER")
    print("=" * 60)
    print(f"  API Docs: http://localhost:8000/docs")
    print(f"  Health:   http://localhost:8000/health")
    print("=" * 60)

    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=False,
    )
