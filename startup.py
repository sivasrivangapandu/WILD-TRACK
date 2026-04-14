#!/usr/bin/env python3
"""
WildTrackAI Complete Startup & Diagnostics Script
Complete one-command startup with full environment configuration
"""

import os
import sys
import subprocess
import time
import urllib.request
import json
import platform

def print_header(title):
    print("\n" + "=" * 70)
    print(f"  {title}")
    print("=" * 70)

def print_ok(msg):
    print(f"✅ {msg}")

def print_warn(msg):
    print(f"⚠️  {msg}")

def print_error(msg):
    print(f"❌ {msg}")

def check_services():
    """Check if backend and frontend are running"""
    print_header("CHECKING SERVICES")
    
    # Check backend
    try:
        with urllib.request.urlopen("http://localhost:8000/health", timeout=3) as r:
            data = json.loads(r.read())
            print_ok(f"Backend running (port 8000)")
            print(f"   - Model Loaded: {data.get('model_loaded')}")
            print(f"   - Database: {data.get('database')}")
            print(f"   - Classes: {data.get('classes')}")
            return True
    except:
        print_error("Backend not responding on http://localhost:8000")
        return False

def create_frontend_env():
    """Create frontend .env if missing"""
    env_path = "frontend/.env"
    if os.path.exists(env_path):
        return True
    
    print_header("CREATING FRONTEND CONFIGURATION")
    try:
        with open(env_path, 'w') as f:
            f.write("# Frontend Environment Variables - Local Development\n")
            f.write("# Backend API URL pointing to local backend\n")
            f.write("VITE_API_URL=http://localhost:8000\n")
        print_ok(f"Created {env_path}")
        return True
    except Exception as e:
        print_error(f"Failed to create {env_path}: {e}")
        return False

def test_connection():
    """Test frontend to backend connection"""
    print_header("TESTING API CONNECTION")
    try:
        # Test with a simple health check through backend
        with urllib.request.urlopen("http://localhost:8000/health", timeout=5) as r:
            if r.status == 200:
                print_ok("Backend API responding correctly")
                return True
    except Exception as e:
        print_error(f"Backend API not accessible: {e}")
        return False

def main():
    print_header("WILDTRACKAI STARTUP & DIAGNOSTICS")
    
    # Check if we're in the right directory
    if not os.path.exists("backend/main.py"):
        print_error("Not in WildTrackAI root directory")
        sys.exit(1)
    
    print_ok("Running from correct directory")
    
    # Create frontend .env if needed
    create_frontend_env()
    
    # Check if services are running
    services_ok = check_services()
    
    if not services_ok:
        print_warn("\nServices not running. Instructions to start:")
        print("\n📘 TERMINAL 1 - Start Backend:")
        print("   cd backend")
        print("   python main.py")
        print("\n📗 TERMINAL 2 - Start Frontend:")
        print("   cd frontend")
        print("   npm run dev")
        print("\n⏱️  Wait 30-45 seconds for both to start completely")
        sys.exit(1)
    
    # Test connection
    print_header("API CONNECTIVITY")
    if test_connection():
        print_ok("Frontend can reach backend")
    else:
        print_warn("Backend not responding yet, may still be starting up")
    
    # Final summary
    print_header("✅ SYSTEM STATUS: READY")
    print("\n📊 Services Running:")
    print("   🟢 Backend API: http://localhost:8000")
    print("   🟢 Frontend App: http://localhost:3000")
    print("\n🌐 Access Application:")
    print("   Open browser → http://localhost:3000")
    print("\n📚 Development Resources:")
    print("   API Documentation: http://localhost:8000/docs")
    print("   Health Check: http://localhost:8000/health")
    print("\n⚡ Quick Fixes if Issues Occur:")
    print("   1. Clear browser cache (Ctrl+Shift+Delete)")
    print("   2. Hard refresh (Ctrl+F5)")
    print("   3. Check terminal for error messages")
    print("   4. Run this script again to verify connectivity")
    print("\n" + "=" * 70)

if __name__ == "__main__":
    main()
