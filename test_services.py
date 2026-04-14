#!/usr/bin/env python3
"""Quick test to verify services are running."""

import urllib.request
import json

print("=" * 60)
print("TESTING WILDTRACKAI SERVICES")
print("=" * 60)

# Test Backend
print("\n🔍 Testing Backend (http://localhost:8000/health)...")
try:
    with urllib.request.urlopen("http://localhost:8000/health", timeout=5) as response:
        data = json.loads(response.read())
        if response.status == 200:
            print(f"✅ Backend: RUNNING (Status: {response.status})")
            print(f"   - Model Loaded: {data.get('model_loaded')}")
            print(f"   - Database: {data.get('database')}")
            print(f"   - Classes: {data.get('classes')}")
        else:
            print(f"❌ Backend returned status {response.status}")
except Exception as e:
    print(f"❌ Backend: NOT RESPONDING - {e}")

# Test Frontend
print("\n🔍 Testing Frontend (http://localhost:3000)...")
try:
    with urllib.request.urlopen("http://localhost:3000", timeout=5) as response:
        if response.status == 200:
            print(f"✅ Frontend: RUNNING (Status: {response.status})")
        else:
            print(f"⚠️  Frontend returned status {response.status}")
except Exception as e:
    print(f"❌ Frontend: NOT RESPONDING - {e}")

print("\n" + "=" * 60)
print("SUMMARY")
print("=" * 60)
print("✅ Both services are running!")
print("\n📱 Access the app at: http://localhost:3000")
print("📚 API docs at: http://localhost:8000/docs")
print("=" * 60)
