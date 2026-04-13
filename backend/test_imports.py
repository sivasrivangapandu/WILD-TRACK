print("[1] Test database", flush=True)
from database import get_db
print("[2] OK database", flush=True)

print("[3] Test schemas", flush=True)
from schemas import ChatStreamRequest
print("[4] OK schemas", flush=True)

print("[5] Test services", flush=True)
from services import get_model_tokens
print("[6] OK services", flush=True)

print("[7] Done")
#!/usr/bin/env python3
"""Test imports with timing to find hang."""
import sys
import time

def log(msg):
    """Print timestamped message."""
    print(f"[{time.time():.2f}] {msg}", flush=True)

log("🔷 Startfile")

try:
    log("Importing os, dotenv...")
    import os
    from dotenv import load_dotenv
    load_dotenv()
    log("✓ load_dotenv done")
except Exception as e:
    log(f"✗ dotenv ERROR: {e}")
    sys.exit(1)

try:
    log("Importing database...")
    from database import SessionLocal, init_db, DB_PATH
    log("✓ database done")
except Exception as e:
    log(f"✗ database ERROR: {e}")
    sys.exit(1)

try:
    log("Importing models...")
    from models import Prediction
    log("✓ models done")
except Exception as e:
    log(f"✗ models ERROR: {e}")
    sys.exit(1)

try:
    log("Importing services.gemini_provider...")
    from services.gemini_provider import is_gemini_available, generate_gemini_text
    log("✓ gemini_provider done")
except Exception as e:
    log(f"✗ gemini_provider ERROR: {e}")
    sys.exit(1)

try:
    log("Importing routes...")
    from routes import chat_router, chat_db_router, auth_router
    log("✓ routes done")
except Exception as e:
    log(f"✗ routes ERROR: {e}")
    sys.exit(1)

try:
    log("Importing pipeline...")
    from pipeline import pipeline
    log("✓ pipeline done")
except Exception as e:
    log(f"✗ pipeline ERROR: {e}") 
    sys.exit(1)

try:
    log("Importing FastAPI...")
    from fastapi import FastAPI
    log("✓ FastAPI done")
except Exception as e:
    log(f"✗ FastAPI ERROR: {e}")
    sys.exit(1)

log("✓✓✓ All imports successful!")
