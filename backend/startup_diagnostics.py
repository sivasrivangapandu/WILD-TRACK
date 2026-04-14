"""
Comprehensive startup diagnostics and validation for WildTrackAI backend.
Run this before starting the main server to catch issues early.
"""

import os
import sys
import sqlite3
import subprocess
from pathlib import Path
import json
import time

def print_header(title):
    print("\n" + "="*60)
    print(f"  {title}")
    print("="*60)

def print_ok(msg):
    print(f"✓ {msg}")

def print_warn(msg):
    print(f"⚠ {msg}")

def print_error(msg):
    print(f"✗ {msg}")

def check_python_version():
    """Verify Python 3.8+"""
    print_header("PYTHON VERSION")
    version = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
    if sys.version_info >= (3, 8):
        print_ok(f"Python {version}")
        return True
    else:
        print_error(f"Python {version} - Need 3.8+")
        return False

def check_required_packages():
    """Verify all required packages are installed."""
    print_header("REQUIRED PACKAGES")
    required = [
        'tensorflow',
        'keras',
        'fastapi',
        'uvicorn',
        'pillow',
        'numpy',
        'opencv-python',
        'requests',
        'pydantic',
        'python-dotenv',
        'bcrypt',
        'pyjwt',
    ]
    
    missing = []
    for pkg in required:
        try:
            __import__(pkg.replace('-', '_'))
            print_ok(f"{pkg}")
        except ImportError:
            print_error(f"{pkg} - NOT INSTALLED")
            missing.append(pkg)
    
    return len(missing) == 0, missing

def check_directories():
    """Ensure all required directories exist and are writable."""
    print_header("DIRECTORIES")
    base = Path(__file__).parent
    dirs_to_check = {
        "models": base / "models",
        "uploads": base / "uploads",
        "outputs": base / "outputs",
        "logs": base / "logs",
        "dataset": base / "dataset",
    }
    
    all_good = True
    for name, directory in dirs_to_check.items():
        if directory.exists():
            if os.access(directory, os.W_OK):
                print_ok(f"{name}/ - exists and writable")
            else:
                print_error(f"{name}/ - exists but NOT writable")
                all_good = False
        else:
            try:
                directory.mkdir(parents=True, exist_ok=True)
                print_ok(f"{name}/ - created")
            except Exception as e:
                print_error(f"{name}/ - failed to create: {e}")
                all_good = False
    
    return all_good

def check_model_files():
    """Check that at least one model file exists."""
    print_header("MODEL FILES")
    base = Path(__file__).parent
    models_dir = base / "models"
    model_files = [
        "wildtrack_v4_cpu.keras",
        "wildtrack_complete_model.h5",
        "wildtrack_final.h5",
        "wildtrack_v4.h5",
    ]
    
    found = []
    for model_name in model_files:
        path = models_dir / model_name
        if path.exists():
            size_mb = path.stat().st_size / (1024 * 1024)
            print_ok(f"{model_name} ({size_mb:.1f} MB)")
            found.append(model_name)
    
    if not found:
        print_warn("No model files found - will download on startup")
        return True  # Not a critical error
    
    return True

def check_database():
    """Test database connectivity."""
    print_header("DATABASE")
    base = Path(__file__).parent
    db_path = base / "database.db"
    
    try:
        conn = sqlite3.connect(str(db_path), timeout=2)
        cursor = conn.cursor()
        cursor.execute("SELECT 1")
        conn.close()
        print_ok(f"SQLite database connected")
        return True
    except Exception as e:
        print_warn(f"Database check failed: {e}")
        return True  # Not critical, will be created on startup

def check_environment_vars():
    """Check environment variables."""
    print_header("ENVIRONMENT VARIABLES")
    from dotenv import load_dotenv
    load_dotenv()
    
    required = ["JWT_SECRET"]
    optional = ["GEMINI_API_KEY", "NINJA_API_KEY", "CLOUDINARY_URL", "RENDER_EXTERNAL_URL"]
    
    for var in required:
        val = os.getenv(var)
        if val and len(val) > 0:
            masked = val[:5] + "..." if len(val) > 20 else val
            print_ok(f"{var} is set")
        else:
            print_warn(f"{var} is not set")
    
    for var in optional:
        val = os.getenv(var)
        if val and len(val) > 0:
            print_ok(f"{var} is set")
        else:
            print_warn(f"{var} is not set (optional)")

def check_ports():
    """Check if required ports are available."""
    print_header("PORTS")
    import socket
    
    ports_to_check = {"Backend (8000)": 8000, "Frontend dev (5173)": 5173}
    
    for name, port in ports_to_check.items():
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            result = sock.connect_ex(('127.0.0.1', port))
            if result == 0:
                print_warn(f"{name} - port {port} IN USE (may conflict)")
            else:
                print_ok(f"{name} - port {port} available")
            sock.close()
        except Exception as e:
            print_warn(f"{name} - check failed: {e}")

def test_tensorflow():
    """Quick TensorFlow import test."""
    print_header("TENSORFLOW")
    try:
        import tensorflow as tf
        print_ok(f"TensorFlow {tf.__version__}")
        
        # Test GPU availability
        gpus = tf.config.list_physical_devices('GPU')
        if gpus:
            print_ok(f"GPU detected: {len(gpus)} device(s)")
        else:
            print_warn("No GPU found - using CPU (predictions will be slower)")
        
        return True
    except Exception as e:
        print_error(f"TensorFlow import failed: {e}")
        return False

def main():
    print("\n" + "🔍 WILDTRACKAI BACKEND STARTUP DIAGNOSTICS" + "\n")
    
    checks = [
        ("Python Version", check_python_version),
        ("Required Packages", lambda: check_required_packages()[0]),
        ("Directories", check_directories),
        ("Model Files", check_model_files),
        ("Database", check_database),
        ("Environment Variables", lambda: (check_environment_vars(), True)[1]),
        ("Ports", lambda: (check_ports(), True)[1]),
        ("TensorFlow", test_tensorflow),
    ]
    
    results = {}
    for name, check_fn in checks:
        try:
            result = check_fn()
            results[name] = result
        except Exception as e:
            print_error(f"{name}: {e}")
            results[name] = False
    
    print_header("SUMMARY")
    passed = sum(1 for v in results.values() if v)
    total = len(results)
    print(f"\nPassed: {passed}/{total}")
    
    if passed == total:
        print_ok("All checks passed! Backend is ready to start.")
        return 0
    else:
        print_warn("Some checks failed - see above for details.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
