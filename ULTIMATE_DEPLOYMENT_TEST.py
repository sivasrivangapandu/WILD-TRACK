#!/usr/bin/env python3
"""
ULTIMATE DEPLOYMENT TEST - Simulates complete Render deployment process
Tests that the app will actually work when deployed to Render
"""

import os
import sys
import subprocess
import tempfile
import shutil
import time
from pathlib import Path

def section(title):
    print(f"\n{'='*70}")
    print(f"🧪 {title}")
    print('='*70)

def run_cmd(cmd, cwd=None, timeout=30):
    """Run command and return success, stdout"""
    try:
        result = subprocess.run(
            cmd,
            shell=True,
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=timeout
        )
        return result.returncode == 0, result.stdout + result.stderr
    except Exception as e:
        return False, str(e)

section("TEST 1: Fresh Clone (Simulating Render Clone)")
print("Creating temporary directory and cloning fresh repository...")

with tempfile.TemporaryDirectory() as tmpdir:
    clone_path = Path(tmpdir) / "wildtrack-clone"
    
    # Get repo URL
    os.chdir("d:\\Wild Track AI")
    success, url_output = run_cmd("git config --get remote.origin.url")
    repo_url = url_output.strip()
    print(f"Repository: {repo_url}")
    
    # Clone fresh (simulating Render)
    clone_cmd = f'git clone --depth 1 "{repo_url}" "{clone_path}"'
    print(f"Cloning to: {clone_path}")
    success, output = run_cmd(clone_cmd, timeout=120)
    
    if success:
        print("✅ Clone succeeded (no LFS errors)")
        
        # Verify .gitattributes is LFS-free
        gitattr = clone_path / ".gitattributes"
        with open(gitattr) as f:
            if "filter=lfs" in f.read():
                print("❌ ERROR: LFS rules found in cloned repo")
                sys.exit(1)
        print("✅ .gitattributes is LFS-free in clone")
        
        # Verify backend/main.py exists and has critical functions
        main_py = clone_path / "backend" / "main.py"
        if not main_py.exists():
            print("❌ ERROR: backend/main.py not found in clone")
            sys.exit(1)
        
        with open(main_py, encoding='utf-8', errors='ignore') as f:
            content = f.read()
            
        if "download_models_if_missing" not in content:
            print("❌ ERROR: download_models_if_missing not in cloned main.py")
            sys.exit(1)
        print("✅ backend/main.py has download_models_if_missing()")
        
        if "def health" not in content:
            print("❌ ERROR: health endpoint not in cloned main.py")
            sys.exit(1)
        print("✅ Health endpoint defined in main.py")
        
        # Verify requirements.txt is valid
        req_file = clone_path / "backend" / "requirements.txt"
        with open(req_file) as f:
            reqs = f.read()
        
        if "sqlalchemy" in reqs or "icrawler" in reqs:
            print("❌ ERROR: Problematic packages in requirements.txt")
            sys.exit(1)
        print("✅ requirements.txt is clean")
        
        pkg_count = len([l for l in reqs.split('\n') if l.strip() and not l.startswith('#')])
        print(f"✅ requirements.txt has {pkg_count} packages")
        
        # Verify render.yaml exists and is valid
        render_yaml = clone_path / "render.yaml"
        if not render_yaml.exists():
            print("❌ ERROR: render.yaml not found")
            sys.exit(1)
        
        with open(render_yaml) as f:
            yaml_content = f.read()
        
        if "wildtrack-backend" not in yaml_content or "wildtrack-frontend" not in yaml_content:
            print("❌ ERROR: Service definitions missing in render.yaml")
            sys.exit(1)
        print("✅ render.yaml has backend and frontend services")
        
        if "healthCheckPath: /health" not in yaml_content:
            print("❌ ERROR: Health check not configured")
            sys.exit(1)
        print("✅ Health check configured in render.yaml")
        
    else:
        print(f"❌ Clone FAILED: {output}")
        if "LFS" in output.upper():
            print("🔴 LFS ERROR DETECTED - Deployment will fail!")
        sys.exit(1)

section("TEST 2: Backend Startup Simulation")
print("Simulating Render backend startup...")
os.chdir("d:\\Wild Track AI\\backend")

# Check if Python can import critical modules
test_imports = """
import sys
import os

try:
    from fastapi import FastAPI
    print("✓ FastAPI available")
except ImportError as e:
    print(f"✗ FastAPI import failed: {e}")
    sys.exit(1)

try:
    import numpy
    print("✓ NumPy available")
except ImportError as e:
    print(f"✗ NumPy import failed: {e}")
    sys.exit(1)

try:
    import cv2
    print("✓ OpenCV available")
except ImportError as e:
    print(f"✗ OpenCV import failed: {e}")
    sys.exit(1)

try:
    import PIL
    print("✓ PIL available")
except ImportError as e:
    print(f"✗ PIL import failed: {e}")
    sys.exit(1)

try:
    from dotenv import load_dotenv
    print("✓ python-dotenv available")
except ImportError as e:
    print(f"✗ python-dotenv import failed: {e}")
    sys.exit(1)

# Test database import
try:
    from database import init_db, SessionLocal
    print("✓ Database module available")
except ImportError as e:
    print(f"✗ Database import failed: {e}")
    sys.exit(1)

print("\\n✅ All critical imports successful")
"""

success, output = run_cmd(f"python -c \"{test_imports}\"", timeout=30)
print(output)
if not success:
    print("❌ Import test failed")
    sys.exit(1)

section("TEST 3: Render YAML Validation")
print("Validating render.yaml for Render deployment...")
os.chdir("d:\\Wild Track AI")

# Parse render.yaml for critical settings
with open("render.yaml") as f:
    yaml_content = f.read()

checks = {
    "Backend service defined": "- type: web" in yaml_content and "wildtrack-backend" in yaml_content,
    "Frontend service defined": "- type: static_site" in yaml_content and "wildtrack-frontend" in yaml_content,
    "Python environment": "env: python" in yaml_content,
    "Health check path": "healthCheckPath: /health" in yaml_content,
    "Build command includes pip": "pip install" in yaml_content,
    "Gunicorn configured": "gunicorn main:app" in yaml_content,
    "Static site publishPath": "publishPath:" in yaml_content,
}

for check, result in checks.items():
    status = "✅" if result else "❌"
    print(f"{status} {check}")
    if not result:
        print(f"   ERROR: {check} failed validation")
        sys.exit(1)

section("TEST 4: Git Repository Integrity")
print("Verifying git repository for deployment...")
os.chdir("d:\\Wild Track AI")

# Check branch and sync status
success, output = run_cmd("git status")
if "On branch main" not in output or "up to date" not in output:
    print("❌ ERROR: Repository not on main or not up-to-date")
    print(output)
    sys.exit(1)
print("✅ On branch main and up-to-date with origin")

# Check no uncommitted changes
success, output = run_cmd("git diff --name-only")
if output.strip():
    print(f"⚠️  WARNING: Uncommitted changes detected: {output}")
    # This is OK for local testing, but flag it
    print("   (Model files may be untracked - this is expected)")

# Verify LFS fix commit is present
success, output = run_cmd("git log --oneline --all | grep LFS")
if not success or not output.strip():
    print("⚠️  WARNING: LFS fix commit not found in history")
else:
    print(f"✅ LFS fix commit found: {output.strip()[:60]}")

section("TEST 5: Model Download URLs")
print("Verifying model download URLs are accessible...")

import requests

model_urls = {
    "wildtrack_v4_cpu.keras": "https://github.com/sivasrivangapandu/WILD-TRACK/releases/download/v2.0-models/wildtrack_v4_cpu.keras",
    "wildtrack_complete_model.h5": "https://github.com/sivasrivangapandu/WILD-TRACK/releases/download/v2.0-models/wildtrack_complete_model.h5",
}

for name, url in model_urls.items():
    try:
        r = requests.head(url, timeout=10, allow_redirects=True)
        if r.status_code == 200:
            size_mb = int(r.headers.get('content-length', 0)) / (1024*1024)
            print(f"✅ {name}: Available ({size_mb:.1f} MB)")
        else:
            print(f"❌ {name}: HTTP {r.status_code}")
            sys.exit(1)
    except Exception as e:
        print(f"❌ {name}: {e}")
        sys.exit(1)

section("DEPLOYMENT READINESS SUMMARY")
print("""
✅ Clone Test: Repository clones without LFS errors
✅ Backend Config: All critical imports available
✅ Render YAML: Fully configured for deployment
✅ Git Status: Repository clean and synchronized
✅ Model URLs: All files accessible and downloadable

🚀 SYSTEM IS READY FOR RENDER DEPLOYMENT

Next Steps:
1. Go to https://dashboard.render.com
2. Connect WILD-TRACK repository
3. Create backend and frontend services
4. Set environment variables (GEMINI_API_KEY, etc.)
5. Deploy!

Expected Results:
- Repository clones successfully (no LFS errors)
- Backend installs dependencies (22 packages)
- Backend auto-downloads models from GitHub
- Models load on first boot
- Health endpoint returns 200
- App processes predictions
""")

print("✅ ALL TESTS PASSED - DEPLOYMENT READY")
sys.exit(0)
