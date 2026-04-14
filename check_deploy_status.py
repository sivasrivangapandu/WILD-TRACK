#!/usr/bin/env python3
"""
Real-time status checker for Render deployment
"""

import urllib.request
import json
import time
import sys

BACKEND_URL = "https://wildtrack-backend-j9n8.onrender.com"
FRONTEND_URL = "https://wildtrack-frontend-iuww.onrender.com"

def check_frontend_deployed():
    """Check if new frontend code is deployed"""
    try:
        with urllib.request.urlopen(f"{FRONTEND_URL}/", timeout=10) as response:
            content = response.read().decode('utf-8', errors='ignore')
            # Check for markers of new build
            if "120_000" in content or "AUTH_RETRY_COUNT: 15" in content:
                return "✅ NEW CODE DEPLOYED"
            elif "/assets/index" in content:
                return "⏳ BUILD IN PROGRESS (old code still live)"
            else:
                return "❓ UNKNOWN STATE"
    except Exception as e:
        return f"❌ Error: {str(e)[:50]}"

def check_backend_health():
    """Check backend status"""
    try:
        with urllib.request.urlopen(f"{BACKEND_URL}/health", timeout=10) as response:
            data = json.loads(response.read().decode())
            if response.status == 200 and data.get('model_loaded'):
                return "✅ BACKEND OK"
            else:
                return "⚠️  BACKEND ISSUE"
    except:
        return "❌ BACKEND DOWN"

print("\n" + "="*60)
print("  WildTrackAI Deployment Status")
print("="*60)

# Check status
backend_status = check_backend_health()
frontend_status = check_frontend_deployed()

print(f"\nBackend:  {backend_status}")
print(f"Frontend: {frontend_status}")

if "NEW CODE DEPLOYED" in frontend_status:
    print("\n✅ DEPLOYMENT COMPLETE!")
    print("\nYou can now:")
    print("1. Refresh browser (Ctrl+F5)")
    print("2. Clear cache (Ctrl+Shift+Delete)")  
    print("3. Try login - should work smoothly")
elif "BUILD IN PROGRESS" in frontend_status:
    print("\n⏳ STILL REBUILDING...")
    print("\nCheck again in 2-3 minutes")
    print("In the meantime, try:")
    print("1. Incognito mode (new private window)")
    print("2. Different browser")
else:
    print(f"\n{frontend_status}")
    print("Please wait and try again in a few minutes")

print("\n" + "="*60 + "\n")
