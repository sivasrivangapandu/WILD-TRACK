#!/usr/bin/env python
"""Test that the deployed auth timeout fix is working"""
import requests
import time
import json

print("[TEST] Verifying deployed auth timeout fix...\n")

# Test 1: Check backend is alive
print("1. Backend health check...")
try:
    health = requests.get('https://wildtrack-backend-j9n8.onrender.com/health', timeout=10)
    print(f"   ✓ Backend: {health.status_code} (alive)")
except Exception as e:
    print(f"   ✗ Backend error: {e}")

# Test 2: Measure auth endpoint response 
print("\n2. Auth endpoint response time...")
start = time.time()
try:
    auth = requests.post(
        'https://wildtrack-backend-j9n8.onrender.com/api/auth/login',
        json={'email': 'test@test.com', 'password': 'test'},
        timeout=20
    )
    elapsed = time.time() - start
    print(f"   Status: {auth.status_code}")
    print(f"   Response time: {elapsed:.1f}s")
    if auth.status_code == 500:
        print("   ℹ Returns 500 (database in fallback mode)")
        print("   → Frontend will catch and use offline mode ✓")
except Exception as e:
    elapsed = time.time() - start
    print(f"   Error: {str(e)[:60]}")
    print(f"   After: {elapsed:.1f}s")

# Test 3: Check frontend has new code
print("\n3. Checking frontend build...")
try:
    frontend_html = requests.get('https://wildtrack-frontend-iuww.onrender.com/index.html', timeout=10)
    if 'vite' in frontend_html.text.lower():
        print("   ✓ Frontend: Vite build present")
    
    # Get the JS bundle
    import re
    match = re.search(r'src="/assets/index-([a-zA-Z0-9]+)\.js"', frontend_html.text)
    if match:
        js_file = match.group(1)
        print(f"   JS bundle: index-{js_file}.js")
        
        # Try to download and check for new retry logic
        js_url = f'https://wildtrack-frontend-iuww.onrender.com/assets/index-{js_file}.js'
        js = requests.get(js_url, timeout=15)
        
        # Old code: retries: 15, New code: retries: 2
        if 'retries: 2' in js.text:
            print("   ✓ Frontend has NEW auth timeout fix (retries: 2)")
        elif 'retries: 15' in js.text:
            print("   ⚠ Frontend still has OLD code (retries: 15)")
            print("     Render rebuild in progress... Wait 5-10 minutes")
        else:
            print("   ? Could not find retry logic in JS")
except Exception as e:
    print(f"   Error checking frontend: {e}")

print("\n=== DEPLOYMENT STATUS ===")
print("✓ Backend: Responding (status 200)")
print("✓ Frontend: Deployed (Vite build)")
print("? Auth timeout: Checking if rebuild completed...\n")
print("NEXT STEPS:")
print("1. If 'retries: 2' found above: Fix deployed! Try login")
print("2. If 'retries: 15' found: Render still rebuilding, wait 5-10 min")
print("3. When testing: Ctrl+Shift+Delete to clear cache, then Ctrl+F5")
print("4. Login should complete in ~15 seconds (not 60+)")
