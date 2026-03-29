"""Startup validation for WildTrack AI backend."""

import os
import sys
import sqlite3
from pathlib import Path


def check_environment() -> bool:
	"""Check environment variables and report optional/missing values."""
	required = ["JWT_SECRET"]
	optional = ["GEMINI_API_KEY", "NINJA_API_KEY", "CLOUDINARY_URL"]

	print("[CHECK] Environment variables...")

	for var in required:
		if os.getenv(var):
			print(f"  [OK] {var} is set")
		else:
			print(f"  [WARN] {var} not set - using development fallback")

	for var in optional:
		if os.getenv(var):
			print(f"  [OK] {var} is set")
		else:
			print(f"  [INFO] {var} not set - related features may be limited")

	return True


def check_directories() -> bool:
	"""Ensure required runtime directories exist."""
	print("[CHECK] Required directories...")

	base = Path(__file__).parent
	required_dirs = [
		base / "models",
		base / "uploads",
		base / "uploads" / "avatars",
		base / "outputs",
		base / "logs",
	]

	for directory in required_dirs:
		if not directory.exists():
			directory.mkdir(parents=True, exist_ok=True)
			print(f"  [CREATE] {directory.name}/")
		else:
			print(f"  [OK] {directory.name}/")

	return True


def check_models() -> bool:
	"""Check that at least one supported model artifact exists."""
	print("[CHECK] Model files...")

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
			print(f"  [OK] {model_name} ({size_mb:.1f} MB)")
			found_any = True

	if not found_any:
		print(f"  [ERROR] No model files found in {models_dir}")
		print("  [INFO] Download model files from project releases")
		return False

	return True


def check_database() -> bool:
	"""Check DB file accessibility with a short sqlite timeout."""
	print("[CHECK] Database...")

	try:
		db_path = Path(__file__).parent / "wildtrack.db"
		conn = sqlite3.connect(str(db_path), timeout=2)
		cur = conn.cursor()
		cur.execute("SELECT 1")
		cur.fetchone()
		conn.close()
		print(f"  [OK] Database reachable at {db_path.name}")
		return True
	except Exception as exc:
		print(f"  [ERROR] Database check failed: {exc}")
		return False


def main() -> int:
	"""Run all startup checks and return process code."""
	print("\n" + "=" * 60)
	print("WildTrack AI - STARTUP VALIDATION")
	print("=" * 60 + "\n")

	checks = [
		("environment", check_environment),
		("directories", check_directories),
		("models", check_models),
		("database", check_database),
	]

	results = []
	for check_name, check_fn in checks:
		try:
			ok = check_fn()
		except Exception as exc:
			print(f"  [ERROR] {check_name} check crashed: {exc}")
			ok = False
		results.append((check_name, ok))
		print()

	passed = sum(1 for _, ok in results if ok)
	total = len(results)

	print("=" * 60)
	print(f"SUMMARY: {passed}/{total} checks passed")
	print("=" * 60 + "\n")

	if passed == total:
		print("[OK] Backend startup prerequisites are satisfied")
		return 0

	print("[ERROR] Resolve the issues above and run this check again")
	return 1


if __name__ == "__main__":
	sys.exit(main())
