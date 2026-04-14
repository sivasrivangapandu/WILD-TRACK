#!/usr/bin/env python3
"""
WildTrackAI Render Deployment Verification
Tests both frontend and backend services on Render
"""

import urllib.request
import json
import sys
import time

BACKEND_URL = "https://wildtrack-backend-j9n8.onrender.com"
FRONTEND_URL = "https://wildtrack-frontend-iuww.onrender.com"

def test_service(url, service_name, is_health_check=False):
    """Test if a service is responding"""
    try:
        print(f"\n🔍 Testing {service_name}...")
        print(f"   URL: {url}")
        
        start = time.time()
        with urllib.request.urlopen(url, timeout=30) as response:
            elapsed = time.time() - start
            status = response.status
            
            if is_health_check:
                data = json.loads(response.read().decode())
                print(f"   ✅ Status: {status}")
                print(f"   Response time: {elapsed:.2f}s")
                print(f"   Data: {json.dumps(data, indent=6)}")
                return True
            else:
                print(f"   ✅ Status: {status}")
                print(f"   Response time: {elapsed:.2f}s")
                return True
                
    except urllib.error.URLError as e:
        print(f"   ❌ Connection Error: {e.reason}")
        return False
    except urllib.error.HTTPError as e:
        print(f"   ❌ HTTP Error {e.code}: {e.reason}")
        return False
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return False

def main():
    print("\n" + "="*70)
    print("  WILDTRACKAI RENDER DEPLOYMENT VERIFICATION")
    print("="*70)
    
    print("\n📋 Configuration:")
    print(f"   Backend:  {BACKEND_URL}")
    print(f"   Frontend: {FRONTEND_URL}")
    
    print("\n" + "="*70)
    print("  TESTING SERVICES")
    print("="*70)
    
    # Test backend health endpoint
    backend_health = test_service(
        f"{BACKEND_URL}/health",
        "Backend Health Check",
        is_health_check=True
    )
    
    # Test frontend
    frontend_ok = test_service(
        FRONTEND_URL,
        "Frontend"
    )
    
    # Summary
    print("\n" + "="*70)
    print("  VERIFICATION RESULTS")
    print("="*70)
    
    print("\n✅ SYSTEM STATUS:")
    print(f"   Backend:  {'✅ ONLINE' if backend_health else '⏳ LOADING or ❌ OFFLINE'}")
    print(f"   Frontend: {'✅ ONLINE' if frontend_ok else '⏳ LOADING or ❌ OFFLINE'}")
    
    if backend_health and frontend_ok:
        print("\n🎉 DEPLOYMENT SUCCESSFUL!")
        print("\n✅ Next Steps:")
        print(f"   1. Visit: {FRONTEND_URL}")
        print("   2. Login with your credentials")
        print("   3. Upload an animal footprint image")
        print("   4. Get AI prediction!")
        sys.exit(0)
    else:
        print("\n⏳ SERVICES STILL INITIALIZING")
        print("\n📌 Note:")
        print("   - First deployment takes 2-3 minutes")
        print("   - TensorFlow model loads on first backend request")
        print("   - Wait 60 seconds and try again")
        print("\n   To monitor:")
        print("   - Backend logs: https://dashboard.render.com/services")
        print("   - Click 'wildtrack-backend' → 'Logs'")
        sys.exit(1)

if __name__ == "__main__":
    main()
