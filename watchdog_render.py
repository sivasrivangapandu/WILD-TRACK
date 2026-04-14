#!/usr/bin/env python3
"""
WildTrackAI Backend Watchdog - Keep Render service alive
Prevents free-tier Render services from going idle
"""

import urllib.request
import json
import time
import sys

BACKEND_URL = "https://wildtrack-backend-j9n8.onrender.com"
HEALTH_ENDPOINT = f"{BACKEND_URL}/health"
PING_INTERVAL = 60  # Ping every 60 seconds
MAX_RETRIES = 5

def ping_backend():
    """Send a health check ping to keep backend alive"""
    try:
        with urllib.request.urlopen(HEALTH_ENDPOINT, timeout=10) as response:
            if response.status == 200:
                print(f"✅ [{time.strftime('%H:%M:%S')}] Backend alive")
                return True
    except Exception as e:
        print(f"❌ [{time.strftime('%H:%M:%S')}] Ping failed: {e}")
        return False
    return False

def force_backend_startup():
    """Attempt multiple pings to force backend startup"""
    print(f"\n🚀 Forcing backend startup...")
    for i in range(MAX_RETRIES):
        print(f"   Attempt {i+1}/{MAX_RETRIES}...")
        if ping_backend():
            print(f"\n✅ Backend is now responsive!")
            return True
        if i < MAX_RETRIES - 1:
            time.sleep(10)  # Wait 10 seconds between attempts
    
    print(f"\n⚠️  Backend not responding after {MAX_RETRIES} attempts")
    return False

def main():
    print("="*60)
    print("  WildTrackAI Backend Watchdog")
    print("="*60)
    print(f"\nBackend URL: {BACKEND_URL}")
    print(f"Health Check: {HEALTH_ENDPOINT}")
    print(f"Ping Interval: {PING_INTERVAL}s")
    print(f"\nNote: Run this in background to keep Render free tier alive")
    print("      Ctrl+C to stop\n")
    
    if force_backend_startup():
        print("\n" + "="*60)
        print("  Backend Watchdog Active")
        print(f"  Next ping: {time.strftime('%H:%M:%S', time.localtime(time.time() + PING_INTERVAL))}")
        print("="*60 + "\n")
        
        # Continuous monitoring loop
        try:
            attempt = 0
            while True:
                time.sleep(PING_INTERVAL)
                attempt += 1
                ping_backend()
                
                # Full health check every 5 pings
                if attempt % 5 == 0:
                    try:
                        with urllib.request.urlopen(HEALTH_ENDPOINT, timeout=10) as response:
                            data = json.loads(response.read().decode())
                            print(f"   Model: {'✅' if data.get('model_loaded') else '⏳'} | "
                                  f"DB: {'✅' if data.get('database') else '❌'} | "
                                  f"Classes: {data.get('classes', 0)}")
                    except:
                        pass
        except KeyboardInterrupt:
            print("\n\n👋 Watchdog stopped")
    else:
        print("\n❌ Could not reach backend. Try:")
        print(f"   1. Visit: {BACKEND_URL}/health")
        print("   2. Check Render dashboard for backend service logs")
        print("   3. Manually restart backend service on Render")
        sys.exit(1)

if __name__ == "__main__":
    main()
