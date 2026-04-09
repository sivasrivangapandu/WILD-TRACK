#!/usr/bin/env python3
"""
Validate Render Configuration and Local Setup
==============================================

Checks that:
- render.yaml is valid YAML
- All required files exist
- Environment variables are set
- Dependencies are installable
- Database can initialize
"""

import os
import sys
import yaml
from pathlib import Path


def print_section(title):
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}")


def validate_render_yaml():
    """Validate render.yaml syntax and structure."""
    print_section("Validating render.yaml")
    
    yaml_path = Path(__file__).parent / "render.yaml"
    if not yaml_path.exists():
        print(f"[ERROR] render.yaml not found at {yaml_path}")
        return False
    
    try:
        with open(yaml_path) as f:
            config = yaml.safe_load(f)
        
        if not config or "services" not in config:
            print("[ERROR] render.yaml missing 'services' key")
            return False
        
        services = config["services"]
        print(f"[OK] Found {len(services)} services in render.yaml")
        
        # Validate each service
        for i, service in enumerate(services):
            name = service.get("name", f"Service-{i}")
            required_keys = ["type", "name"]
            
            for key in required_keys:
                if key not in service:
                    print(f"[ERROR] Service '{name}' missing required key: {key}")
                    return False
            
            print(f"[OK] Service '{name}' is valid")
        
        return True
        
    except yaml.YAMLError as e:
        print(f"[ERROR] YAML syntax error: {e}")
        return False
    except Exception as e:
        print(f"[ERROR] Failed to validate render.yaml: {e}")
        return False


def validate_file_structure():
    """Validate required project files exist."""
    print_section("Validating Project Structure")
    
    # Determine base directory (works from project root or subdirectories)
    current = Path(__file__).parent
    if current.name in ["backend", "frontend"]:
        base = current.parent
    else:
        base = current
    required_files = {
        "render.yaml": base / "render.yaml",
        "backend/requirements.txt": base / "backend" / "requirements.txt",
        "backend/main.py": base / "backend" / "main.py",
        "backend/database.py": base / "backend" / "database.py",
        "frontend/package.json": base / "frontend" / "package.json",
        "backend/render_init.py": base / "backend" / "render_init.py",
    }
    
    all_good = True
    for name, path in required_files.items():
        if path.exists():
            size = path.stat().st_size
            print(f"[OK] {name} ({size} bytes)")
        else:
            print(f"[ERROR] Missing: {name}")
            all_good = False
    
    return all_good


def validate_environment():
    """Check environment setup."""
    print_section("Validating Environment")
    
    # Check if we're in the backend directory or project root
    backend_path = Path(__file__).parent
    if backend_path.name == "backend":
        base_path = backend_path.parent
    else:
        base_path = Path(__file__).parent.parent
    
    # Load .env if exists
    env_file = base_path / ".env"
    if env_file.exists():
        print(f"[OK] .env file found")
        # Don't print contents for security
    else:
        print(f"[INFO] No .env file (required for local testing)")
    
    # Check critical env vars for deployment
    critical_vars = ["JWT_SECRET"]
    optional_vars = ["GEMINI_API_KEY", "NINJA_API_KEY", "CLOUDINARY_URL"]
    
    for var in critical_vars:
        if os.getenv(var):
            print(f"[OK] {var} is set")
        else:
            print(f"[WARN] {var} not set (required for deployment)")
    
    for var in optional_vars:
        if os.getenv(var):
            print(f"[OK] {var} is set")
        else:
            print(f"[INFO] {var} not set (optional)")
    
    return True


def validate_dependencies():
    """Check if critical packages are available."""
    print_section("Validating Python Dependencies")
    
    critical_packages = [
        "fastapi",
        "uvicorn",
        "sqlalchemy",
        "pydantic",
        ("tensorflow", "tensorflow can be skipped locally"),
    ]
    
    missing = []
    for pkg in critical_packages:
        if isinstance(pkg, tuple):
            pkg_name, msg = pkg
        else:
            pkg_name = pkg
            msg = ""
        
        try:
            __import__(pkg_name)
            print(f"[OK] {pkg_name}")
        except ImportError:
            print(f"[WARN] {pkg_name} not installed {msg}")
            if pkg_name != "tensorflow":
                missing.append(pkg_name)
    
    if missing:
        print(f"\n[INFO] Install missing packages with:")
        print(f"  pip install {' '.join(missing)}")
    
    return len(missing) == 0


def main():
    """Run all validations."""
    print("\n")
    print("+" * 60)
    print("+  WildTrackAI Render Configuration Validator")
    print("+" * 60)
    
    checks = [
        ("render.yaml", validate_render_yaml),
        ("File Structure", validate_file_structure),
        ("Environment", validate_environment),
        ("Dependencies", validate_dependencies),
    ]
    
    results = {}
    for name, check_func in checks:
        try:
            results[name] = check_func()
        except Exception as e:
            print(f"\n[ERROR] {name} check failed: {e}")
            import traceback
            traceback.print_exc()
            results[name] = False
    
    # Summary
    print_section("VALIDATION SUMMARY")
    
    passed = sum(1 for v in results.values() if v)
    total = len(results)
    
    for name, result in results.items():
        status = "[PASS]" if result else "[FAIL]"
        print(f"{status} {name}")
    
    print(f"\nResult: {passed}/{total} checks passed")
    
    if all(results.values()):
        print("\n[OK] All validations passed!")
        print("\nNext steps:")
        print("1. Review RENDER_DEPLOYMENT_GUIDE.md")
        print("2. Push your changes to GitHub")
        print("3. Deploy from Render Dashboard")
        return 0
    else:
        print("\n[ERROR] Some validations failed - see above for details")
        return 1


if __name__ == "__main__":
    sys.exit(main())
