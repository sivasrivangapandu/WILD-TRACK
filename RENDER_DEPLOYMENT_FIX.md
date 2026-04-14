# WildTrackAI Render Deployment - Complete Fix Guide

## 🔴 Problems Identified

1. **Backend Service Name Mismatch**: 
   - `render.yaml` defines service as `wildtrack-backend`
   - But CORS config references `wildtrack-backend-j9n8.onrender.com`
   - These may not match - Render generates URLs based on service name

2. **CORS Origins Not Including Frontend**:
   - CORS_ORIGINS: `https://wildtrack-frontend-iuww.onrender.com,https://wildtrack-ai.onrender.com`
   - Missing localhost fallback for testing
   - May be missing actual frontend URL if Render regenerated it

3. **Frontend Environment Variables Not Set on Render**:
   - `render.yaml` sets `VITE_API_URL` but Render static site builds may not use it properly
   - Need to ensure the variable is available during `npm run build`

4. **No Health Check Endpoint Configuration**:
   - Render doesn't know backend is healthy
   - May keep restarting it

5. **Missing Production Environment**:
   - No `.env` file included in Render deployment
   - Backend needs API keys (GEMINI_API_KEY, NINJA_API_KEY, CLOUDINARY_URL)

---

## ✅ Solution: Update Deployment Configuration

### Step 1: Get Your Actual Render Service URLs

Go to Render dashboard:
1. Get backend service URL: https://dashboard.render.com/services
2. Find your backend service (should be `wildtrack-backend` or similar)
3. Copy the full URL (e.g., `https://wildtrack-backend-xxxx.onrender.com`)
4. Do the same for frontend if it exists

### Step 2: Update `render.yaml`

Replace the current `render.yaml` with the corrected version below:

```yaml
services:
  # Backend: FastAPI Service
  - type: web
    name: wildtrack-backend
    env: python
    region: oregon
    buildCommand: |
      cd backend
      pip install -r requirements.txt
    startCommand: |
      cd backend
      gunicorn main:app \
        --workers 2 \
        --worker-class uvicorn.workers.UvicornWorker \
        --bind 0.0.0.0:$PORT \
        --timeout 120 \
        --graceful-timeout 120 \
        --keep-alive 5 \
        --access-logfile - \
        --error-logfile -
    
    # Health check configuration
    healthCheckPath: /health
    healthCheckInterval: 30  # Check every 30s
    
    envVars:
      - key: PYTHON_VERSION
        value: 3.10.0
      - key: PORT
        value: 8000
      - key: RENDER_EXTERNAL_URL
        fromService:
          name: wildtrack-backend
          type: web
          property: url
      # IMPORTANT: Add frontend URL here
      # Replace with your actual frontend URL from Render dashboard
      - key: CORS_ORIGINS
        value: https://wildtrack-frontend-iuww.onrender.com,http://localhost:3000,http://localhost:8000
      - key: JWT_SECRET
        generateValue: true
      - key: GEMINI_API_KEY
        sync: false  # Set via dashboard
      - key: NINJA_API_KEY
        sync: false  # Set via dashboard
      - key: CLOUDINARY_URL
        sync: false  # Set via dashboard

  # Frontend: React/Vite Static Site
  - type: static_site
    name: wildtrack-frontend
    region: oregon
    buildCommand: |
      cd frontend
      npm install
      npm ci --prefer-offline --no-audit
      # Explicitly set environment variable for Vite build
      export VITE_API_URL="https://wildtrack-backend-j9n8.onrender.com"
      npm run build
    publishPath: frontend/dist
    
    # Use build environment variables
    envVars:
      - key: VITE_API_URL
        # Replace with your actual backend URL
        value: https://wildtrack-backend-j9n8.onrender.com
      - key: NODE_ENV
        value: production
    
    routes:
      # React SPA routing - serve index.html for all routes
      - type: rewrite
        source: /*
        destination: /index.html

# Use Render native SQLite database directory
# This ensures data persists across deployments
databases:
  - name: wildtrack-db
    dbName: wildtrack
```

### Step 3: Get Correct Service URLs and Update CORS

**⚠️ CRITICAL**: You need to update the actual service URLs:

1. **Backend URL**: Go to your Render backend service dashboard, copy the URL
2. **Frontend URL**: Go to your Render frontend service dashboard, copy the URL

Update both in `render.yaml`:
- Line 33: Replace `https://wildtrack-backend-j9n8.onrender.com` with YOUR backend URL in CORS_ORIGINS
- Line 61: Replace `https://wildtrack-backend-j9n8.onrender.com` with YOUR backend URL in frontend build
- Line 72: Replace `https://wildtrack-backend-j9n8.onrender.com` with YOUR backend URL in VITE_API_URL

### Step 4: Set Environment Variables on Render Dashboard

Go to each service on Render dashboard:

**Backend Service:**
1. Settings → Environment
2. Add/update these variables:
   - `GEMINI_API_KEY`: [Your actual key]
   - `NINJA_API_KEY`: [Your actual key]
   - `CLOUDINARY_URL`: [Your actual URL]

**Frontend Service:**
1. Settings → Environment
2. Add/update:
   - `VITE_API_URL`: `https://your-backend-url.onrender.com`
   - `NODE_ENV`: `production`

### Step 5: Deploy

```bash
# Commit changes
git add render.yaml
git commit -m "Fix: Update Render deployment with correct service URLs and CORS configuration

- Add health check endpoint configuration
- Set CORS_ORIGINS to include both frontend and fallback URLs
- Ensure environment variables available during build
- Add proper start command with logging
- Include NODE_ENV for frontend optimization"

# Push to GitHub (this triggers Render redeploy)
git push origin main
```

---

## 🔍 Troubleshooting

### ❌ "Backend not responding" on Frontend

**Check backend logs in Render:**
1. Go to backend service
2. Click "Logs"
3. Look for errors

**Common issues:**
- API keys not set (GEMINI_API_KEY, etc.)
- CORS_ORIGINS doesn't include frontend URL
- Port binding issue (PORT env var not set)

### ❌ "Mixed Content" error in browser

**Cause**: Frontend is HTTPS but trying to access HTTP backend  
**Fix**: Ensure backend URL in VITE_API_URL is `https://`, not `http://`

### ❌ Frontend showing blank page or 404

**Check frontend build logs:**
1. Go to frontend service
2. Click "Logs"
3. Look for build errors

**Common issues:**
- `npm install` failed
- VITE_API_URL not set during build
- Missing environment variables

### ❌ Timeout/504 errors

**Cause**: Backend not fully loaded (TensorFlow model takes time)  
**Solution**: Already configured with:
- 120s timeout in gunicorn
- 5-minute timeout for predict endpoint
- Health check every 30s

Wait 2-3 minutes after deployment for model to load.

---

## 📋 Verification Checklist

After deployment, verify:

- [ ] Backend service is running (green light on Render)
- [ ] Frontend service is running (green light on Render)
- [ ] Backend `/health` endpoint returns 200 (visit `https://your-backend-url.onrender.com/health` in browser)
- [ ] Frontend loads without CORS errors (check browser console F12)
- [ ] Can access login page
- [ ] Can click login button without connection errors
- [ ] Can upload image and get prediction

---

## 🚀 Quick Debug Commands

Test backend availability (replace with your URL):
```bash
curl -v https://wildtrack-backend-xxxx.onrender.com/health
```

Expected response:
```json
{
  "status": "ok",
  "model_loaded": true,
  "database": true,
  "classes": 5
}
```

---

## 📞 If Still Not Working

1. **Verify render.yaml syntax**: Check YAML indentation (spaces, not tabs)
2. **Check Render account limits**: Free tier has restrictions
3. **Rebuild services**: On Render, go to each service → Manual Deploy → Deploy Latest Commit
4. **Check for typos**: Service names, URLs, environment variable keys
5. **Wait for model load**: First deployment takes 2-3 minutes for TensorFlow model

---

**Last Updated**: April 14, 2026  
**Status**: Ready for deployment
