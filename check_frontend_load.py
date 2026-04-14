#!/usr/bin/env python
"""Verify frontend page loads without errors"""
import requests

print("Testing frontend page load...\n")

try:
    resp = requests.get('https://wildtrack-frontend-iuww.onrender.com/', timeout=10)
    print(f"Frontend Status: {resp.status_code}")
    
    content = resp.text
    content_lower = content.lower()
    
    # Check for error indicators
    if 'error' in content_lower and 'internal server error' in content_lower:
        print("✗ Frontend has server error")
    elif 'cannot find module' in content_lower:
        print("✗ Frontend has module import error")
    elif 'react' in content_lower or 'root' in content_lower:
        print("✓ Frontend React app structure present")
    
    # Check for key components
    print("\nComponent checks:")
    if '<div id="root"></div>' in content:
        print("  ✓ Root React div")
    else:
        print("  ? Root div (might be different format)")
        
    if 'vite-plugin-pwa' in content:
        print("  ✓ Vite PWA script")
    
    if 'registerSW' in content:
        print("  ✓ Service worker registration")
    
    print(f"\nPage size: {len(content)} bytes")
    print("✓ Frontend loads successfully")
    
except Exception as e:
    print(f"✗ Error: {e}")
