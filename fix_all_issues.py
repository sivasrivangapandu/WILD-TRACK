#!/usr/bin/env python3
"""
WildTrack AI - Comprehensive Issue Finder & Fixer
Identifies and attempts to resolve all known project issues
"""

import os
import sys
import importlib.util
import sqlite3
from pathlib import Path

# Set UTF-8 encoding
os.environ['PYTHONIOENCODING'] = 'utf-8'

BASE_DIR = Path(__file__).parent
BACKEND_DIR = BASE_DIR / "backend"
FRONTEND_DIR = BASE_DIR / "frontend"

def check_backend_structure():
    """Verify backend directory structure."""
    print("\n[1] BACKEND STRUCTURE CHECK")
    print("=" * 60)
    
    required_dirs = [
        BACKEND_DIR / "models",
        BACKEND_DIR / "uploads",
        BACKEND_DIR / "uploads" / "avatars",
        BACKEND_DIR / "outputs",
        BACKEND_DIR / "logs",
        BACKEND_DIR / "routes",
        BACKEND_DIR / "services",
        BACKEND_DIR / "schemas",
    ]
    
    issues = []
    for d in required_dirs:
        if not d.exists():
            print(f"  [MISSING] {d.relative_to(BASE_DIR)}")
            d.mkdir(parents=True, exist_ok=True)
            print(f"    -> Created")
        else:
            print(f"  [OK] {d.relative_to(BASE_DIR)}")
    
    return len(issues) == 0

def check_frontend_structure():
    """Verify frontend structure."""
    print("\n[2] FRONTEND STRUCTURE CHECK")
    print("=" * 60)
    
    required_paths = [
        FRONTEND_DIR / "package.json",
        FRONTEND_DIR / "vite.config.js",
        FRONTEND_DIR / "tailwind.config.cjs",
        FRONTEND_DIR / "src",
        FRONTEND_DIR / "src" / "App.jsx",
    ]
    
    all_ok = True
    for p in required_paths:
        if p.exists():
            print(f"  [OK] {p.relative_to(BASE_DIR)}")
        else:
            print(f"  [MISSING] {p.relative_to(BASE_DIR)}")
            all_ok = False
    
    return all_ok

def check_python_imports():
    """Test critical Python imports."""
    print("\n[3] PYTHON DEPENDENCIES CHECK")
    print("=" * 60)
    
    required_packages = [
        ("fastapi", "FastAPI Web Framework"),
        ("tensorflow", "TensorFlow/Keras"),
        ("cv2", "OpenCV (CV2)"),
        ("sqlalchemy", "SQLAlchemy ORM"),
        ("uvicorn", "Uvicorn ASGI Server"),
        ("bcrypt", "Password Hashing"),
        ("jose", "JWT Tokens"),
        ("pydantic", "Validation"),
    ]
    
    missing = []
    for pkg, name in required_packages:
        if importlib.util.find_spec(pkg) is not None:
            print(f"  [OK] {name}")
        else:
            print(f"  [MISSING] {name} ({pkg})")
            missing.append(pkg)
    
    if missing:
        print(f"\n  To install missing packages, run:")
        print(f"    pip install {' '.join(missing)}")
    
    return len(missing) == 0

def check_environment_variables():
    """Check critical environment variables."""
    print("\n[4] ENVIRONMENT VARIABLES CHECK")
    print("=" * 60)
    
    optional_env_vars = [
        ("JWT_SECRET", "JWT secret key"),
        ("GEMINI_API_KEY", "Google Gemini API key"),
        ("NINJA_API_KEY", "API Ninjas key"),
        ("CLOUDINARY_URL", "Cloudinary storage"),
    ]
    
    for var, desc in optional_env_vars:
        if os.getenv(var):
            print(f"  [SET] {var:20s} - {desc}")
        else:
            print(f"  [NOT SET] {var:20s} - {desc} (optional)")

def check_database():
    """Check database connectivity."""
    print("\n[5] DATABASE CHECK")
    print("=" * 60)
    
    db_path = BACKEND_DIR / "wildtrack.db"
    
    try:
        conn = sqlite3.connect(str(db_path), timeout=2)
        cursor = conn.cursor()
        cursor.execute("SELECT 1")
        cursor.fetchone()
        conn.close()
        print(f"  [OK] Database reachable at {db_path.relative_to(BASE_DIR)}")
        
        return True
    except Exception as e:
        print(f"  [ERROR] Database connectivity failed: {e}")
        return False

def check_model_files():
    """Check for model files."""
    print("\n[6] MODEL FILE CHECK")
    print("=" * 60)
    
    models_dir = BACKEND_DIR / "models"
    model_files = [
        "wildtrack_v4_cpu.keras",
        "wildtrack_complete_model.h5",
        "wildtrack_final.h5",
        "model_metadata.json",
    ]
    
    found = False
    for mf in model_files:
        model_path = models_dir / mf
        if model_path.exists():
            size_mb = model_path.stat().st_size / (1024 * 1024)
            print(f"  [OK] {mf} ({size_mb:.1f} MB)")
            found = True
        else:
            print(f"  [MISSING] {mf}")
    
    if not found:
        print("\n  [INFO] No model files found. Download from GitHub Releases:")
        print("    https://github.com/sivasrivangapandu/WILD-TRACK/releases")
    
    return found

def check_unicode_issues():
    """Check for Unicode encoding issues in code."""
    print("\n[7] UNICODE ENCODING CHECK")
    print("=" * 60)
    
    # Check for problematic emoji characters
    problematic_files = [
        BACKEND_DIR / "auth.py",
        BACKEND_DIR / "main.py",
    ]
    
    unicode_issues = []
    for fp in problematic_files:
        if fp.exists():
            try:
                with open(fp, 'r', encoding='utf-8') as f:
                    content = f.read()
                    if '⚠️' in content or '✓' in content or '✗' in content:
                        unicode_issues.append(f"  [FOUND] {fp.name} contains emoji characters (may cause Windows encoding issues)")
            except Exception as e:
                pass
    
    if unicode_issues:
        for issue in unicode_issues:
            print(issue)
        print("\n  These files should use ASCII-safe replacements for Windows compatibility")
        return False
    else:
        print("  [OK] No problematic Unicode characters found")
        return True

def check_npm_dependencies():
    """Check npm dependencies for frontend."""
    print("\n[8] NPM DEPENDENCIES CHECK")
    print("=" * 60)
    
    node_modules = FRONTEND_DIR / "node_modules"
    if node_modules.exists():
        num_packages = len(list(node_modules.glob("*")))
        print(f"  [OK] npm packages installed ({num_packages} packages)")
        return True
    else:
        print(f"  [NOT INSTALLED] npm packages not installed")
        print(f"    Run: cd frontend && npm install")
        return False

def check_git_status():
    """Check git status."""
    print("\n[9] GIT STATUS CHECK")
    print("=" * 60)
    
    git_dir = BASE_DIR / ".git"
    if git_dir.exists():
        print(f"  [OK] Git repository initialized")
        
        # Check for staged changes
        import subprocess
        try:
            result = subprocess.run(
                ["git", "status", "--porcelain"],
                cwd=BASE_DIR,
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                lines = result.stdout.strip().split("\n") if result.stdout.strip() else []
                print(f"  [INFO] {len(lines)} files with changes")
                for line in lines[:5]:
                    if line:
                        print(f"    {line}")
                if len(lines) > 5:
                    print(f"    ... and {len(lines) - 5} more")
        except Exception as e:
            print(f"  [WARN] Could not check git status: {e}")
    else:
        print(f"  [NOT INITIALIZED] Git repository not found")

def check_port_availability():
    """Check if development ports are available."""
    print("\n[10] PORT AVAILABILITY CHECK")
    print("=" * 60)
    
    import socket
    
    ports_to_check = [
        (8000, "Backend API (FastAPI/Uvicorn)"),
        (3000, "Frontend (Vite dev server)"),
    ]
    
    for port, service in ports_to_check:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        result = sock.connect_ex(('127.0.0.1', port))
        sock.close()
        
        if result == 0:
            print(f"  [IN USE] Port {port} - {service} (already running)")
        else:
            print(f"  [AVAILABLE] Port {port} - {service}")

def generate_summary():
    """Generate summary report."""
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    
    checks = [
        ("Backend Structure", check_backend_structure()),
        ("Frontend Structure", check_frontend_structure()),
        ("Python Dependencies", check_python_imports()),
        ("Database", check_database()),
        ("Model Files", check_model_files()),
        ("Unicode Encoding", check_unicode_issues()),
        ("NPM Dependencies", check_npm_dependencies()),
        ("Git Repository", True),  # Not critical
    ]
    
    print("\nCRITICAL STATUS:")
    passed = sum(1 for _, result in checks if result)
    total = len(checks)
    print(f"  {passed}/{total} critical checks passed")
    
    for name, result in checks:
        status = "[PASS]" if result else "[FAIL]"
        print(f"  {status} {name}")
    
    print("\nRECOMMENDATIONS:")
    if not all(r for _, r in checks):
        print("  1. Install missing Python packages with: pip install -r backend/requirements.txt")
        print("  2. Install Node dependencies with: cd frontend && npm install")
        print("  3. Download model files from GitHub Releases")
        print("  4. Set environment variables (e.g., JWT_SECRET, GEMINI_API_KEY)")
    
    print("\nTO RUN THE PROJECT:")
    print("  Backend:  cd backend && uvicorn main:app --host 0.0.0.0 --port 8000")
    print("  Frontend: cd frontend && npm run dev")
    print("  Docs:     Backend API docs at http://localhost:8000/docs")

if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("WildTrack AI - COMPREHENSIVE PROJECT HEALTH CHECK")
    print("=" * 60)
    
    # Run all checks
    check_backend_structure()
    check_frontend_structure()
    check_python_imports()
    check_environment_variables()
    check_database()
    check_model_files()
    check_unicode_issues()
    check_npm_dependencies()
    check_git_status()
    check_port_availability()
    
    # Generate summary
    generate_summary()
    
    print("\n" + "=" * 60)
    print("Check complete!")
    print("=" * 60 + "\n")
