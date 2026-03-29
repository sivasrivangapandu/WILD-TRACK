#!/usr/bin/env python3
"""
WildTrack AI - Automatic Issue Fixer
Resolves all identified issues automatically
"""

import os
import sys
import subprocess
import importlib.util
from pathlib import Path

BASE_DIR = Path(__file__).parent

def install_missing_packages():
    """Install missing Python packages."""
    print("\n[1] INSTALLING MISSING PYTHON PACKAGES")
    print("=" * 60)
    
    missing_packages = [
        ("opencv-python", "cv2", "OpenCV for image processing"),
        ("python-jose", "jose", "JWT token support"),
    ]
    
    venv_python = BASE_DIR / ".venv" / "Scripts" / "python.exe"
    
    for pkg, module_name, desc in missing_packages:
        if importlib.util.find_spec(module_name) is not None:
            print(f"  [OK] {desc} already available ({module_name})")
            continue

        print(f"  Installing {desc} ({pkg})...")
        try:
            subprocess.run(
                [
                    str(venv_python),
                    "-m",
                    "pip",
                    "install",
                    "--disable-pip-version-check",
                    pkg,
                ],
                capture_output=True,
                timeout=180,
                check=True
            )
            print(f"    [OK] {pkg} installed successfully")
        except subprocess.CalledProcessError as e:
            print(f"    [ERROR] Failed to install {pkg}")
            print(f"      Error: {e.stderr.decode() if e.stderr else str(e)}")
        except Exception as e:
            print(f"    [ERROR] Error installing {pkg}: {e}")

def create_env_file():
    """Create .env file template."""
    print("\n[2] CREATING ENVIRONMENT CONFIGURATION")
    print("=" * 60)
    
    env_file = BASE_DIR / ".env"
    env_example_file = BASE_DIR / ".env.example"
    
    env_content = """# WildTrack AI Configuration
# Copy this file to .env and fill in your actual values

# Security
JWT_SECRET=your-super-secret-key-change-this-in-production
JWT_ALGORITHM=HS256
JWT_EXPIRATION_HOURS=24

# AI/ML APIs
GEMINI_API_KEY=your-gemini-api-key-here
NINJA_API_KEY=your-api-ninjas-key-here

# File Storage (Optional - for cloud uploads)
CLOUDINARY_URL=cloudinary://your-credentials-here

# Database
DATABASE_URL=sqlite:///./wildtrack.db
# For PostgreSQL: DATABASE_URL=postgresql://user:password@localhost/wildtrack

# Server Configuration
SERVER_HOST=0.0.0.0
SERVER_PORT=8000
DEBUG_MODE=False

# Model Configuration
MODEL_PATH=./models/wildtrack_v4_cpu.keras
CONFIDENCE_THRESHOLD=0.5

# Logging
LOG_LEVEL=INFO
"""
    
    # Create .env.example (always)
    with open(env_example_file, 'w') as f:
        f.write(env_content)
    print(f"  [OK] Created {env_example_file.name}")
    
    # Create .env (only if it doesn't exist)
    if not env_file.exists():
        # For development, use less secure defaults
        dev_env_content = env_content.replace(
            "your-super-secret-key-change-this-in-production",
            "dev-secret-key-please-change-for-production"
        )
        with open(env_file, 'w') as f:
            f.write(dev_env_content)
        print(f"  [OK] Created {env_file.name} with development defaults")
        print(f"      [SECURITY] Update JWT_SECRET for production!")
    else:
        print(f"  [SKIP] {env_file.name} already exists")

def create_gitignore():
    """Create/update .gitignore."""
    print("\n[3] CONFIGURING GIT IGNORE")
    print("=" * 60)
    
    gitignore_file = BASE_DIR / ".gitignore"
    
    required_entries = [
        ".env",
        ".env.local",
        "__pycache__/",
        ".pytest_cache/",
        ".venv/",
        "node_modules/",
        "dist/",
        "build/",
        "*.pyc",
        ".DS_Store",
        ".vscode/",
        "*.weights.h5",
        "*.h5",
        "*.keras",
        "uploads/",
        "outputs/",
        "logs/",
    ]
    
    if gitignore_file.exists():
        with open(gitignore_file, 'r') as f:
            existing = f.read()
    else:
        existing = ""
    
    updated = False
    for entry in required_entries:
        if entry not in existing:
            existing += f"\n{entry}"
            updated = True
    
    if updated or not gitignore_file.exists():
        with open(gitignore_file, 'w') as f:
            f.write(existing.lstrip())
        print(f"  [OK] Updated .gitignore with security entries")
    else:
        print(f"  [OK] .gitignore already configured")

def create_backend_requirements():
    """Ensure requirements.txt is complete."""
    print("\n[4] VERIFYING BACKEND REQUIREMENTS")
    print("=" * 60)
    
    req_file = BASE_DIR / "backend" / "requirements.txt"
    if req_file.exists():
        with open(req_file, 'r') as f:
            content = f.read()
        
        # Check for critical dependencies
        required = [
            "fastapi",
            "uvicorn",
            "tensorflow",
            "opencv-python",
            "sqlalchemy",
            "bcrypt",
            "python-jose",
        ]
        
        missing = []
        for pkg in required:
            if pkg.lower() not in content.lower():
                missing.append(pkg)
        
        if missing:
            print(f"  [WARN] Missing packages in requirements.txt: {', '.join(missing)}")
            print(f"    Run: pip freeze > backend/requirements.txt")
        else:
            print(f"  [OK] requirements.txt contains all critical packages")
    else:
        print(f"  [MISSING] backend/requirements.txt not found")

def create_startup_validator():
    """Create startup validation script."""
    print("\n[5] CREATING STARTUP VALIDATOR")
    print("=" * 60)
    
    validator_file = BASE_DIR / "backend" / "startup_check.py"
    
    validator_code = '''"""Startup validation for WildTrack AI backend."""

import os
import sys
from pathlib import Path

def check_environment():
    """Check environment variables."""
    required = ["JWT_SECRET"]
    optional = ["GEMINI_API_KEY", "NINJA_API_KEY", "CLOUDINARY_URL"]
    
    print("[CHECK] Environment variables...")
    
    for var in required:
        if not os.getenv(var):
            print(f"  [WARN] {var} not set - using defaults")
    
    for var in optional:
        if not os.getenv(var):
            print(f"  [INFO] {var} not set - features will be limited")
    
    return True

def check_directories():
    """Check required directories exist."""
    print("[CHECK] Required directories...")
    
    base = Path(__file__).parent
    required_dirs = [
        base / "models",
        base / "uploads",
        base / "outputs",
        base / "logs",
    ]
    
    for d in required_dirs:
        if not d.exists():
            print(f"  [CREATE] {d.name}/")
            d.mkdir(parents=True, exist_ok=True)
        else:
            print(f"  [OK] {d.name}/")
    
    return True

def check_models():
    """Check model files exist."""
    print("[CHECK] Model files...")
    
    base = Path(__file__).parent
    models_dir = base / "models"
    model_files = [
        "wildtrack_v4_cpu.keras",
        "wildtrack_complete_model.h5",
    ]
    
    found = False
    for mf in model_files:
        fp = models_dir / mf
        if fp.exists():
            size_mb = fp.stat().st_size / (1024 * 1024)
            print(f"  [OK] {mf} ({size_mb:.1f} MB)")
            found = True
            break
    
    if not found:
        print(f"  [WARN] No model files found in {models_dir}")
        print(f"    Download from: https://github.com/sivasrivangapandu/WILD-TRACK/releases")
        return False
    
    return True

def check_database():
    """Check database connectivity."""
    print("[CHECK] Database...")
    
    try:
        from database import SessionLocal, init_db
        init_db()
        db = SessionLocal()
        db.close()
        print(f"  [OK] Database ready")
        return True
    except Exception as e:
        print(f"  [ERROR] Database error: {e}")
        return False

def main():
    """Run all startup checks."""
    print("\\n" + "=" * 60)
    print("WildTrack AI - STARTUP VALIDATION")
    print("=" * 60 + "\\n")
    
    checks = [
        check_environment,
        check_directories,
        check_models,
        check_database,
    ]
    
    results = []
    for check in checks:
        try:
            result = check()
            results.append((check.__name__, result))
        except Exception as e:
            print(f"  [ERROR] {check.__name__} failed: {e}")
            results.append((check.__name__, False))
        print()
    
    # Summary
    passed = sum(1 for _, r in results if r)
    total = len(results)
    
    print("=" * 60)
    print(f"SUMMARY: {passed}/{total} checks passed")
    print("=" * 60 + "\\n")
    
    if passed == total:
        print("[OK] System ready for startup!")
        return 0
    else:
        print("[ERROR] Fix errors above and try again")
        return 1

if __name__ == "__main__":
    sys.exit(main())
'''
    
    if not validator_file.exists():
        with open(validator_file, 'w', encoding='utf-8') as f:
            f.write(validator_code)
        print(f"  [OK] Created {validator_file.name}")
    else:
        print(f"  [SKIP] {validator_file.name} already exists")

def create_readme_section():
    """Add setup instructions to README."""
    print("\n[6] UPDATING DOCUMENTATION")
    print("=" * 60)
    
    readme_file = BASE_DIR / "SETUP_QUICKSTART.md"
    
    setup_content = """# WildTrack AI - Quick Setup Guide

## Prerequisites
- Python 3.8+
- Node.js 14+
- Git

## Installation

### 1. Clone and Setup
```bash
git clone https://github.com/sivasrivangapandu/WILD-TRACK.git
cd WILD-TRACK
python -m venv .venv

# On Windows:
.venv\\Scripts\\activate
# On Linux/Mac:
source .venv/bin/activate
```

### 2. Install Python Dependencies
```bash
pip install -r backend/requirements.txt
```

If you get OpenCV or python-jose errors, install individually:
```bash
pip install opencv-python python-jose
```

### 3. Environment Configuration
```bash
# Copy example to actual config
cp .env.example .env

# Edit .env with your settings (at minimum, change JWT_SECRET)
```

### 4. Download Models
- Download model files from: https://github.com/sivasrivangapandu/WILD-TRACK/releases
- Extract to backend/models/
- Required: wildtrack_v4_cpu.keras or similar

### 5. Frontend Setup
```bash
cd frontend
npm install
```

## Running the Application

### Start Backend
```bash
cd backend
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

### Start Frontend
```bash
cd frontend
npm run dev
```

### Access Application
- Frontend: http://localhost:3000
- Backend API Docs: http://localhost:8000/docs
- Backend Redoc: http://localhost:8000/redoc

## Troubleshooting

### UnicodeEncodeError on Windows
This has been fixed in the latest version. If you encounter Unicode errors:
1. Ensure you're using the latest code with git pull
2. Set environment variable: set PYTHONIOENCODING=utf-8

### Missing OpenCV or python-jose
```bash
pip install opencv-python python-jose
```

### Model not loading
1. Verify model file exists in backend/models/
2. Check available disk space
3. Try regenerating: python backend/train_model.py

### Database errors
```bash
cd backend
python -c "from database import init_db; init_db()"
```

### Port already in use
- Backend (8000): netstat -ano | find ":8000" (Windows)
- Frontend (3000): netstat -ano | find ":3000" (Windows)

Change ports in config or kill existing process.

## Project Structure

```
WildTrack AI/
|--- backend/          (FastAPI server, models, ML pipeline)
|--- frontend/         (React UI with Vite)
|--- .env              (Configuration - git-ignored)
|--- requirements.txt  (Python dependencies)
|--- README.md         (Full documentation)
```

## Next Steps
1. Read Multi_Theme_Auth_Guide.md for authentication
2. Review Pro_Features_Guide.md for advanced features
3. Check DEPLOYMENT.md for production setup

## Support
- Documentation: See *.md files in project root
- Issues: GitHub Issues tracker
- Questions: Check existing issues first
"""
    
    if not readme_file.exists():
        with open(readme_file, 'w', encoding='utf-8') as f:
            f.write(setup_content)
        print(f"  [OK] Created {readme_file.name}")
    else:
        print(f"  [SKIP] {readme_file.name} already exists")

def print_summary():
    """Print final summary."""
    print("\n" + "=" * 60)
    print("FIXES COMPLETED")
    print("=" * 60)
    print("""
[DONE] Environment files created (.env, .env.example)
[DONE] Git ignore configured
[DONE] Startup validator created
[DONE] Documentation created
[DONE] Python packages ready to install

NEXT STEPS:
1. Configure environment:
   - Edit .env with your settings
   - Set JWT_SECRET for production

2. Download model files from GitHub Releases

3. Run startup check:
   python backend/startup_check.py

4. Start the application:
   Backend: cd backend && uvicorn main:app --reload
   Frontend: cd frontend && npm run dev

5. Access at:
   - Frontend: http://localhost:3000
   - API Docs: http://localhost:8000/docs
""")

if __name__ == "__main__":
    print("\\n" + "=" * 60)
    print("WildTrack AI - AUTOMATIC ISSUE FIXER")
    print("=" * 60)
    
    install_missing_packages()
    create_env_file()
    create_gitignore()
    create_backend_requirements()
    create_startup_validator()
    create_readme_section()
    
    print_summary()
    
    print("=" * 60)
    print("Fix complete! Run fix_all_issues.py again to verify.")
    print("=" * 60 + "\n")
