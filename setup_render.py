#!/usr/bin/env python3
"""
WildTrackAI Render Deployment Configuration Helper
Helps you identify your actual service URLs and update render.yaml correctly
"""

import re
import os

def display_render_setup():
    """Display instructions for setting up Render deployment"""
    
    print("\n" + "="*70)
    print("  WILDTRACKAI RENDER DEPLOYMENT SETUP")
    print("="*70)
    
    print("""
This tool helps you configure Render deployment properly.

IMPORTANT STEPS:
================

1. GO TO RENDER DASHBOARD
   URL: https://dashboard.render.com/services
   
2. FIND YOUR SERVICES
   Backend Service:
   - Name: "wildtrack-backend" (or similar)
   - Type: "Web Service"
   - Copy the full URL (should be like https://wildtrack-backend-xxxx.onrender.com)
   
   Frontend Service:
   - Name: "wildtrack-frontend" (or similar)
   - Type: "Static Site"
   - Copy the full URL (should be like https://wildtrack-frontend-xxxx.onrender.com)

3. UPDATE YOUR CONFIGURATION
   Edit the file: render.yaml
   
   Find and replace:
   
   OLD BACKEND URL:
   https://wildtrack-backend-j9n8.onrender.com
   
   NEW BACKEND URL: (paste what you copied)
   https://wildtrack-backend-XXXX.onrender.com
   
   Find and replace BOTH occurrences:
   a) Line ~32: In CORS_ORIGINS
   b) Line ~52: In VITE_API_URL

4. UPDATE ENVIRONMENT VARIABLES ON RENDER
   
   Backend Service:
   - Go to Settings → Environment
   - Add/Update:
     * GEMINI_API_KEY = [your key]
     * NINJA_API_KEY = [your key]
     * CLOUDINARY_URL = [your key]
   
   Frontend Service:
   - Go to Settings → Environment
   - Add/Update:
     * VITE_API_URL = https://your-backend-url.onrender.com
     * NODE_ENV = production

5. DEPLOY
   Once render.yaml is updated with correct URLs:
   
   git add render.yaml
   git commit -m "Update Render deployment URLs"
   git push origin main
   
   Render will automatically redeploy!

VERIFICATION
============

After deployment, check:

✓ Backend health check:
  https://wildtrack-backend-XXXX.onrender.com/health
  
  Should return:
  {
    "status": "ok",
    "model_loaded": true,
    "database": true,
    "classes": 5
  }

✓ Frontend loads:
  https://wildtrack-frontend-XXXX.onrender.com
  
  Should show login page without errors

✓ Test login:
  1. Open https://wildtrack-frontend-XXXX.onrender.com
  2. Try to login
  3. Should NOT see "Server temporarily unavailable" error
  4. Check browser console (F12) for any CORS errors

TROUBLESHOOTING
===============

If backend shows "Service unavailable":
- It's still loading (takes 2-3 minutes first time)
- Check backend logs on Render dashboard

If frontend shows blank page:
- Check frontend build logs
- Check browser console (F12) for errors
- Verify VITE_API_URL is set correctly

If CORS errors in console:
- Verify CORS_ORIGINS in backend includes frontend URL
- Ensure it includes http://localhost:3000 for local testing

Need help?
- Check backend logs: Render dashboard → Services → wildtrack-backend → Logs
- Check frontend logs: Render dashboard → Services → wildtrack-frontend → Logs
""")
    
    print("="*70)
    print("\n✅ Run this script again after deployment to verify\n")

if __name__ == "__main__":
    display_render_setup()
