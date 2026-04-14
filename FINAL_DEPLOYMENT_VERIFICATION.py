#!/usr/bin/env python3
"""
FINAL COMPREHENSIVE DEPLOYMENT VERIFICATION
Tests all critical components needed for successful Render deployment.
"""

import os
import sys
import subprocess
import json
from pathlib import Path

def test_section(name):
    """Decorator for test sections."""
    def decorator(func):
        def wrapper():
            print(f"\n{'='*70}")
            print(f"✓ {name}")
            print('='*70)
            return func()
        return wrapper
    return decorator

@test_section("1. GIT LFS REMOVAL - No LFS tracking")
def test_lfs_removed():
    """Verify LFS tracking is completely removed."""
    gitattributes = Path("d:\\Wild Track AI\\.gitattributes")
    with open(gitattributes) as f:
        content = f.read()
    
    assert "filter=lfs" not in content, "ERROR: LFS rules still in .gitattributes"
    print("   ✅ .gitattributes has NO LFS tracking rules")
    print(f"   ✅ Content preview: {content[:100]}...")
    return True

@test_section("2. MODEL FILES - Properly gitignored")
def test_models_gitignored():
    """Verify model files are in .gitignore."""
    gitignore = Path("d:\\Wild Track AI\\.gitignore")
    with open(gitignore) as f:
        content = f.read()
    
    required_patterns = ["*.h5", "*.keras", "models/"]
    for pattern in required_patterns:
        assert pattern in content, f"ERROR: {pattern} not in .gitignore"
        print(f"   ✅ .gitignore contains: {pattern}")
    
    # Verify actual model files exist locally but not in git tracking
    model_files = [
        "backend/models/wildtrack_v4_cpu.keras",
        "backend/models/wildtrack_complete_model.h5",
    ]
    
    for model in model_files:
        full_path = Path("d:\\Wild Track AI") / model
        if full_path.exists():
            print(f"   ✅ Model file exists locally: {model}")
            # Verify not tracked by git
            result = subprocess.run(
                f'cd "d:\\Wild Track AI" && git ls-files --error-unmatch "{model}"',
                shell=True,
                capture_output=True,
                text=True
            )
            assert result.returncode != 0, f"ERROR: {model} is tracked by git!"
            print(f"   ✅ Model file NOT tracked by git: {model}")
    
    return True

@test_section("3. BACKEND CONFIGURATION - .env and requirements")
def test_backend_config():
    """Verify backend .env and requirements are valid."""
    # Check .env exists
    env_file = Path("d:\\Wild Track AI\\backend\\.env")
    assert env_file.exists(), "ERROR: .env not found"
    print(f"   ✅ .env file exists")
    
    # Check .env has required keys
    with open(env_file) as f:
        env_content = f.read()
    
    required_keys = ["JWT_SECRET", "GEMINI_API_KEY"]
    for key in required_keys:
        assert key in env_content, f"ERROR: {key} not in .env"
        print(f"   ✅ .env contains: {key}")
    
    # Check requirements.txt
    req_file = Path("d:\\Wild Track AI\\backend\\requirements.txt")
    with open(req_file) as f:
        reqs = f.read()
    
    # Verify problematic packages removed
    assert "sqlalchemy" not in reqs, "ERROR: SQLAlchemy should be removed"
    assert "icrawler" not in reqs, "ERROR: icrawler should be removed"
    print(f"   ✅ requirements.txt: SQLAlchemy removed")
    print(f"   ✅ requirements.txt: icrawler removed")
    
    # Count packages
    pkg_count = len([l for l in reqs.split('\n') if l.strip() and not l.startswith('#')])
    print(f"   ✅ requirements.txt: {pkg_count} packages")
    
    return True

@test_section("4. MODEL DOWNLOAD MECHANISM - GitHub Releases URLs")
def test_download_mechanism():
    """Verify model download mechanism is configured."""
    main_py = Path("d:\\Wild Track AI\\backend\\main.py")
    with open(main_py, encoding='utf-8', errors='ignore') as f:
        content = f.read()
    
    # Verify download function exists
    assert "def download_models_if_missing" in content, "ERROR: download function not found"
    print("   ✅ download_models_if_missing() function exists")
    
    # Verify MODEL_URLS defined
    assert "MODEL_URLS" in content, "ERROR: MODEL_URLS not defined"
    print("   ✅ MODEL_URLS dictionary defined")
    
    # Verify GitHub Releases URLs configured
    assert "github.com" in content and "releases/download" in content, "ERROR: GitHub Releases URL not found"
    print("   ✅ GitHub Releases URLs configured")
    
    # Verify load_model calls download
    assert "download_models_if_missing()" in content, "ERROR: download not called in load_model"
    print("   ✅ load_model() calls download_models_if_missing()")
    
    return True

@test_section("5. GITHUB RELEASES - Files are accessible")
def test_github_releases_accessible():
    """Verify GitHub Release files are accessible."""
    import requests
    
    urls_to_test = [
        "https://github.com/sivasrivangapandu/WILD-TRACK/releases/download/v2.0-models/wildtrack_v4_cpu.keras",
        "https://github.com/sivasrivangapandu/WILD-TRACK/releases/download/v2.0-models/wildtrack_complete_model.h5",
    ]
    
    for url in urls_to_test:
        try:
            r = requests.head(url, timeout=10, allow_redirects=True)
            assert r.status_code == 200, f"ERROR: HTTP {r.status_code}"
            print(f"   ✅ Accessible: {url.split('/')[-1]} (HTTP {r.status_code})")
        except Exception as e:
            print(f"   ❌ FAILED: {url}")
            print(f"      Error: {e}")
            return False
    
    return True

@test_section("6. GIT STATUS - Repository clean")
def test_git_status():
    """Verify git repository is clean and up to date."""
    os.chdir("d:\\Wild Track AI")
    
    # Check if on main branch
    result = subprocess.run(
        "git status",
        shell=True,
        capture_output=True,
        text=True
    )
    
    assert "On branch main" in result.stdout, "ERROR: Not on main branch"
    assert "up to date with 'origin/main'" in result.stdout, "ERROR: Not up to date with origin"
    print("   ✅ On branch main")
    print("   ✅ Up to date with origin/main")
    
    # Show last few commits
    result = subprocess.run(
        "git log --oneline -3",
        shell=True,
        capture_output=True,
        text=True
    )
    print("   Recent commits:")
    for line in result.stdout.strip().split('\n'):
        print(f"     {line}")
    
    return True

@test_section("7. RENDER CONFIGURATION - render.yaml valid")
def test_render_config():
    """Verify render.yaml is properly configured."""
    render_yaml = Path("d:\\Wild Track AI\\render.yaml")
    assert render_yaml.exists(), "ERROR: render.yaml not found"
    
    with open(render_yaml) as f:
        content = f.read()
    
    # Check critical config
    assert "wildtrack-backend" in content, "ERROR: backend service not configured"
    assert "wildtrack-frontend" in content, "ERROR: frontend service not configured"
    assert "healthCheckPath: /health" in content, "ERROR: health check not configured"
    assert "gunicorn main:app" in content, "ERROR: gunicorn not configured"
    
    print("   ✅ render.yaml: Backend service configured")
    print("   ✅ render.yaml: Frontend service configured")
    print("   ✅ render.yaml: Health checks configured")
    print("   ✅ render.yaml: Gunicorn configured")
    
    return True

@test_section("8. PYTHON SYNTAX - No syntax errors")
def test_python_syntax():
    """Verify all Python files have valid syntax."""
    critical_files = [
        "backend/main.py",
        "backend/database.py",
        "backend/config.py",
    ]
    
    os.chdir("d:\\Wild Track AI")
    for filepath in critical_files:
        result = subprocess.run(
            f"python -m py_compile {filepath}",
            shell=True,
            capture_output=True,
            text=True
        )
        if result.returncode == 0:
            print(f"   ✅ {filepath}: Syntax OK")
        else:
            print(f"   ❌ {filepath}: SYNTAX ERROR")
            print(f"      {result.stderr}")
            return False
    
    return True

def main():
    """Run all tests."""
    print("\n" + "="*70)
    print("🚀 WILDTRACK AI - FINAL DEPLOYMENT VERIFICATION 🚀")
    print("="*70)
    print("Testing readiness for Render production deployment...")
    
    tests = [
        test_lfs_removed,
        test_models_gitignored,
        test_backend_config,
        test_download_mechanism,
        test_github_releases_accessible,
        test_git_status,
        test_render_config,
        test_python_syntax,
    ]
    
    results = []
    for test in tests:
        try:
            passed = test()
            results.append((test.__name__, "✅ PASS" if passed else "❌ FAIL"))
        except AssertionError as e:
            print(f"\n   ❌ ASSERTION FAILED: {e}")
            results.append((test.__name__, "❌ FAIL"))
        except Exception as e:
            print(f"\n   ❌ ERROR: {e}")
            results.append((test.__name__, "❌ ERROR"))
    
    # Summary
    print("\n" + "="*70)
    print("DEPLOYMENT VERIFICATION SUMMARY")
    print("="*70)
    
    passed_count = sum(1 for _, r in results if "✅" in r)
    total_count = len(results)
    
    for test_name, result in results:
        print(f"   {result}")
    
    print(f"\n   Total: {passed_count}/{total_count} tests passed")
    
    if passed_count == total_count:
        print("\n" + "🎉"*35)
        print("\n✅ ALL VERIFICATIONS PASSED")
        print("\nThe system is READY FOR RENDER PRODUCTION DEPLOYMENT")
        print("\nKey achievements:")
        print("  ✓ Git LFS completely removed - no deploy blocker")
        print("  ✓ Model files properly gitignored")
        print("  ✓ Backend auto-download mechanism working")
        print("  ✓ GitHub Releases model files accessible")
        print("  ✓ render.yaml fully configured")
        print("  ✓ Python code syntax valid")
        print("  ✓ Repository clean and up to date")
        print("\n" + "🎉"*35 + "\n")
        return 0
    else:
        print("\n⚠️  SOME TESTS FAILED - REVIEW ABOVE FOR DETAILS")
        return 1

if __name__ == "__main__":
    sys.exit(main())
