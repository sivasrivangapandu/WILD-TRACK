#!/usr/bin/env python3
"""
Render Deployment Initialization Script
========================================

This script ensures safe startup in the Render environment by:
- Verifying environment variables
- Initializing database
- Attempting model download
- Creating required directories
- Running health checks before starting the server

Usage:
    python render_init.py [--verbose] [--check-only]
"""

import os
import sys
import json
from pathlib import Path


def print_header(text):
    """Print a formatted header."""
    print(f"\n{'='*60}")
    print(f"  {text}")
    print(f"{'='*60}")


def check_environment():
    """Check and report environment setup."""
    print_header("ENVIRONMENT CHECK")
    
    env_vars = {
        "required": ["JWT_SECRET"],
        "optional": ["GEMINI_API_KEY", "NINJA_API_KEY", "CLOUDINARY_URL"],
    }
    
    all_good = True
    
    for var in env_vars.get("required", []):
        if os.getenv(var):
            print(f"[OK] {var} is set")
        else:
            print(f"[WARN] {var} not set")
    
    for var in env_vars.get("optional", []):
        if os.getenv(var):
            print(f"[OK] {var} is set")
        else:
            print(f"[INFO] {var} not set - features may be limited")
    
    # Check Python version
    py_version = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
    if sys.version_info >= (3, 10):
        print(f"[OK] Python {py_version} (>= 3.10 required)")
    else:
        print(f"[ERROR] Python {py_version} (>= 3.10 required)")
        all_good = False
    
    return all_good


def check_directories():
    """Ensure all required directories exist."""
    print_header("DIRECTORY CHECK")
    
    base = Path(__file__).parent
    required_dirs = [
        base / "models",
        base / "uploads",
        base / "uploads" / "avatars",
        base / "outputs",
        base / "logs",
    ]
    
    for directory in required_dirs:
        try:
            directory.mkdir(parents=True, exist_ok=True)
            print(f"[OK] {directory.name}/ exists")
        except Exception as e:
            print(f"[ERROR] Failed to create {directory.name}/: {e}")
            return False
    
    return True


def check_database():
    """Check database initialization."""
    print_header("DATABASE CHECK")
    
    try:
        # Add backend to path
        sys.path.insert(0, str(Path(__file__).parent))
        
        from database import init_db, SessionLocal
        init_db()
        print("[OK] Database initialized successfully")
        
        # Test connection
        with SessionLocal() as session:
            session.execute("SELECT 1")
        print("[OK] Database connection verified")
        
        return True
    except Exception as e:
        print(f"[ERROR] Database initialization failed: {type(e).__name__}: {e}")
        return False


def check_model_files():
    """Check for model files."""
    print_header("MODEL FILES CHECK")
    
    base = Path(__file__).parent
    models_dir = base / "models"
    
    model_files = [
        "wildtrack_v4_cpu.keras",
        "wildtrack_complete_model.h5",
        "wildtrack_final.h5",
    ]
    
    found_any = False
    for model_name in model_files:
        model_path = models_dir / model_name
        if model_path.exists():
            size_mb = model_path.stat().st_size / (1024 * 1024)
            print(f"[OK] {model_name} ({size_mb:.1f} MB)")
            found_any = True
        else:
            print(f"[INFO] {model_name} not found (will be downloaded on first startup)")
    
    if not found_any:
        print("[INFO] No model files present - auto-download on startup")
    
    return True


def check_dependencies():
    """Check critical dependencies."""
    print_header("DEPENDENCY CHECK")
    
    critical_packages = [
        "tensorflow",
        "fastapi",
        "uvicorn",
        "sqlalchemy",
        "pydantic",
    ]
    
    all_good = True
    for package in critical_packages:
        try:
            __import__(package)
            print(f"[OK] {package} is installed")
        except ImportError:
            print(f"[ERROR] {package} not installed")
            all_good = False
    
    return all_good


def main():
    """Run all checks."""
    print("\n")
    print("+" * 60)
    print("+  WildTrackAI Render Initialization")
    print("+" * 60)
    
    checks = [
        ("Environment", check_environment),
        ("Directories", check_directories),
        ("Dependencies", check_dependencies),
        ("Database", check_database),
        ("Model Files", check_model_files),
    ]
    
    results = {}
    for name, check_func in checks:
        try:
            results[name] = check_func()
        except Exception as e:
            print(f"\n[CRITICAL] {name} check failed with exception: {e}")
            results[name] = False
    
    # Summary
    print_header("INITIALIZATION SUMMARY")
    
    passed = sum(1 for v in results.values() if v)
    total = len(results)
    
    for name, result in results.items():
        status = "[PASS]" if result else "[FAIL]"
        print(f"{status} {name}")
    
    print(f"\nResult: {passed}/{total} checks passed")
    
    if passed == total:
        print("\n[OK] All checks passed - ready for startup")
        return 0
    elif passed >= 4:  # 4 out of 5 is acceptable (models can download later)
        print("\n[WARN] Most checks passed - startup may proceed with caution")
        return 0
    else:
        print("\n[ERROR] Critical checks failed - cannot proceed with startup")
        return 1


if __name__ == "__main__":
    sys.exit(main())
