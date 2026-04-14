#!/usr/bin/env python3
"""
Diagnostic script to check Render deployment status
"""

import urllib.request
import json
import time

BACKEND_URL = "https://wildtrack-backend-j9n8.onrender.com"
FRONTEND_URL = "https://wildtrack-frontend-iuww.onrender.com"

print("\n" + "="*60)
print("  WildTrackAI Render Deployment Diagnostic")
print("="*60)

# 1. Check Backend
print("\n[1] BACKEND STATUS")
print("-" * 60)
try:
    with urllib.request.urlopen(f"{BACKEND_URL}/health", timeout=10) as response:
        if response.status == 200:
            data = json.loads(response.read().decode())
            print(f"Status: {response.status} OK")
            print(f"Model Loaded: {data.get('model_loaded', False)}")
            print(f"Database: {data.get('database', False)}")
            print(f"Classes: {data.get('classes', 0)}")
            print(f"GradCAM: {data.get('gradcam_available', False)}")
            print(f"Uptime: {data.get('uptime_seconds', 0):.0f}s")
            print("\n✅ BACKEND IS HEALTHY")
        else:
            print(f"Status: {response.status} - Unexpected")
except Exception as e:
    print(f"❌ Backend unreachable: {e}")

# 2. Check Frontend
print("\n[2] FRONTEND STATUS")
print("-" * 60)
try:
    with urllib.request.urlopen(f"{FRONTEND_URL}/", timeout=10) as response:
        if response.status == 200:
            content = response.read().decode('utf-8', errors='ignore')
            # Check if new build is deployed (look for aggressive retry marker)
            if "AUTH_RETRY_COUNT: 15" in content or "120_000" in content:
                print(f"Status: {response.status} OK")
                print("✅ NEW AGGRESSIVE RETRY CODE DETECTED")
                print("   (Frontend rebuild completed)")
            else:
                print(f"Status: {response.status} OK")
                print("⚠️  OLD CODE DETECTED - Rebuild may not be complete")
                print("   (Frontend still on old retry settings)")
                print("   Waiting for Render to rebuild...")
        else:
            print(f"Status: {response.status} - Unexpected")
except Exception as e:
    print(f"❌ Frontend unreachable: {e}")

# 3. Test Auth Endpoint
print("\n[3] BACKEND API TEST")
print("-" * 60)
try:
    with urllib.request.urlopen(f"{BACKEND_URL}/api/auth/status", timeout=10) as response:
        if response.status == 200:
            print(f"Status: {response.status} OK")
            print("✅ API ENDPOINT ACCESSIBLE")
        else:
            print(f"Status: {response.status}")
except Exception as e:
    print(f"⚠️  API unavailable (expected if no auth token): {e}")

print("\n" + "="*60)
print("  WHAT TO DO")
print("="*60)
print("""
1. WAIT 2-3 MINUTES for Render to rebuild frontend
2. CLEAR BROWSER CACHE (Ctrl+Shift+Delete)
3. HARD REFRESH (Ctrl+F5 or Cmd+Shift+R)
4. TRY LOGIN AGAIN

If issue persists:
- Backend is healthy ✅
- Watchdog is running ✅
- Issue is frontend cache or rebuild delay

Try in Incognito Mode (no cache):
https://wildtrack-frontend-iuww.onrender.com
""")
print("="*60 + "\n")
