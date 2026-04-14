# 🚀 WILDTRACK AI - PRODUCTION DEPLOYMENT GUIDE

## Pre-Deployment Checklist

### 1. Repository Status
- ✅ Git LFS blocker removed
- ✅ Model files gitignored
- ✅ Backend download mechanism working
- ✅ All code committed and pushed to GitHub
- ✅ Branch: main, Status: up-to-date with origin

### 2. Environment Variables Required

Create these in Render dashboard for each service:

**Backend Service (FastAPI):**
```
JWT_SECRET=<generate-32-character-random-string>
GEMINI_API_KEY=AIzaSyD-rz0mo81f7H6wFjJZ-TeG-yLLKmjxOXY
NINJA_API_KEY=28hgS0UqtEDtFKhughV9fRQx7tVogcXZ5XbNkGNZ
CLOUDINARY_CLOUD_NAME=<your-cloudinary-name>
CLOUDINARY_API_KEY=<your-cloudinary-api-key>
CLOUDINARY_API_SECRET=<your-cloudinary-secret>
CORS_ORIGINS=https://wildtrack-frontend-iuww.onrender.com,http://localhost:3000,http://localhost:8000
PYTHON_VERSION=3.10.0
PORT=8000
```

**Frontend Service (React/Vite):**
```
VITE_API_URL=https://wildtrack-backend-j9n8.onrender.com
NODE_ENV=production
```

### 3. GitHub Integration

Repository already configured:
- URL: https://github.com/sivasrivangapandu/WILD-TRACK.git
- Branch: main
- Deploy on: commit to main

---

## STEP-BY-STEP DEPLOYMENT

### Phase 1: Render Dashboard Setup (5 minutes)

1. **Go to Render Dashboard**
   - URL: https://dashboard.render.com
   - Sign in with GitHub

2. **Create New Service (Backend)**
   - Click "New +" → "Web Service"
   - Select repository: WILD-TRACK
   - Branch: main
   - Name: wildtrack-backend
   - Environment: Python 3
   - Build Command: `cd backend && pip install -r requirements.txt`
   - Start Command: `cd backend && gunicorn main:app --workers 2 --worker-class uvicorn.workers.UvicornWorker --bind 0.0.0.0:$PORT --timeout 120`
   - Region: Oregon
   - Plan: Free (or Starter for production)

3. **Add Environment Variables (Backend)**
   - Copy all backend variables from section 2 above
   - Save and deploy

4. **Create New Service (Frontend)**
   - Click "New +" → "Static Site"
   - Select repository: WILD-TRACK
   - Branch: main
   - Name: wildtrack-frontend
   - Build Command: `cd frontend && npm install && npm ci --prefer-offline --no-audit && npm run build`
   - Publish Directory: frontend/dist
   - Region: Oregon
   - Plan: Free

5. **Add Environment Variables (Frontend)**
   - Add VITE_API_URL and NODE_ENV from section 2
   - Save and deploy

### Phase 2: Monitor Initial Deployment (15-20 minutes)

**Backend Deployment Progress:**
1. Render clones repository (1-2 min) → ✅ No LFS errors
2. Installs dependencies (3-5 min) → pip install 22 packages
3. Starts Gunicorn (1 min)
4. Backend listens on $PORT → ✅ Ready
5. Model download starts → Downloads from GitHub (5-10 min)
6. Model loads into memory → ✅ Ready for predictions

**Frontend Deployment Progress:**
1. Render clones repository (1-2 min)
2. npm install (3-5 min)
3. npm run build creates dist/ (2-3 min)
4. Static site deployed → ✅ Ready to serve

**Check Deployment Status:**
- Backend logs: Look for "[MODEL] Loaded successfully" message
- Frontend: Should be accessible at https://wildtrack-frontend-iuww.onrender.com
- Backend: Should respond to curl https://wildtrack-backend-j9n8.onrender.com/health

### Phase 3: Post-Deployment Testing (5 minutes)

**Test Backend Health:**
```bash
curl https://wildtrack-backend-j9n8.onrender.com/health
# Expected response:
# {
#   "status": "ok",
#   "model_loaded": true,
#   "uptime_seconds": 123
# }
```

**Test Frontend Access:**
- Open https://wildtrack-frontend-iuww.onrender.com
- Should load the WildTrack AI application
- Login page should be visible

**Test Login Flow:**
1. Click "Sign Up" or "Login"
2. Create account or login
3. Should show prediction interface

**Test Prediction:**
1. Upload a footprint image
2. Should process and return species prediction
3. Check backend logs for successful prediction

---

## DEPLOYMENT ARCHITECTURE

```
┌─────────────────────────────────────────────────────────┐
│                    RENDER SERVICES                      │
├─────────────────────────────────────────────────────────┤
│                                                          │
│  ┌──────────────────────┐    ┌──────────────────────┐  │
│  │   BACKEND SERVICE    │    │  FRONTEND SERVICE    │  │
│  │   (FastAPI)          │    │  (React/Vite)        │  │
│  │                      │    │                      │  │
│  │ - Python 3.10        │    │ - Node.js            │  │
│  │ - Gunicorn           │    │ - Static Site        │  │
│  │ - Uvicorn Workers    │    │                      │  │
│  │ - Health: /health    │    │ - Routes to /        │  │
│  │                      │    │                      │  │
│  │ On startup:          │    │ Environment:         │  │
│  │ 1. Clone repo        │    │ VITE_API_URL=        │  │
│  │ 2. Install deps      │    │   <backend-url>      │  │
│  │ 3. Download models   │    │                      │  │
│  │    from GitHub       │    │ Serves dist/         │  │
│  │ 4. Load model        │    │ All traffic → React  │  │
│  │ 5. Start server      │    │                      │  │
│  │ 6. Accept requests   │    │                      │  │
│  └──────────────────────┘    └──────────────────────┘  │
│        ↓ API Calls ←────────────────────────────────    │
│        ↓ Port 8000                                      │
│                                                          │
│  ┌──────────────────────────────────────────────────┐  │
│  │         GitHub Releases (Model Storage)          │  │
│  │  wildtrack_v4_cpu.keras (700 MB)                │  │
│  │  wildtrack_complete_model.h5 (520 MB)           │  │
│  │  - Auto-downloaded by backend on startup         │  │
│  └──────────────────────────────────────────────────┘  │
│                                                          │
└─────────────────────────────────────────────────────────┘
```

---

## TROUBLESHOOTING

### Issue: Backend stuck on "Installing dependencies"
- **Cause**: pip install taking too long
- **Solution**: Increase build timeout in Render settings to 60-90 min

### Issue: Model download timeout
- **Cause**: GitHub download interrupted
- **Solution**: Backend has retry logic (3 attempts). Check backend logs for "Downloading..."

### Issue: "Model failed to load"
- **Cause**: TensorFlow memory issue on free tier
- **Solution**: Model will run in demo mode. Predictions will fail gracefully

### Issue: Frontend shows "Backend unavailable"
- **Cause**: Backend still downloading models
- **Solution**: Wait 2-5 minutes and refresh. Check backend logs at https://dashboard.render.com

### Issue: CORS errors on login
- **Cause**: CORS_ORIGINS not set in backend environment
- **Solution**: Add CORS_ORIGINS in Render backend env vars

---

## PRODUCTION MONITORING

### Health Check Endpoint
- **URL**: https://wildtrack-backend-j9n8.onrender.com/health
- **Frequency**: Every 30 seconds (Render default)
- **Expected**: HTTP 200, JSON response with model_loaded status

### Key Log Messages to Watch
```
[BUILD] Installing dependencies... ← Build phase
[START] Backend startup... ← Server starting
[MODEL] Downloading models... ← Model download starting
[MODEL] Loaded successfully ← Backend ready
[REQUEST] POST /predict ← Prediction received
```

### Performance Metrics
- **Cold start time**: 5-10 minutes (first deployment)
- **Warm start time**: 30 seconds (subsequent restarts)
- **Model load time**: 3-5 minutes
- **Prediction time**: 2-5 seconds per image

---

## SCALING & UPGRADES

### When to upgrade from Free tier:
- Backend continuously sleeping (Render puts free services to sleep)
- Need custom domain
- Need SSL certificate
- Need more computing power

### Upgrade Steps:
1. Go to Render dashboard
2. Select backend service
3. Change plan to "Starter" or "Standard"
4. Increase workers if needed (default is 2)

---

## EMERGENCY PROCEDURES

### Rollback to Previous Version
```bash
git revert <commit-hash>
git push origin main
# Render will auto-deploy new commit
```

### Force Restart Backend
1. Go to https://dashboard.render.com
2. Select wildtrack-backend
3. Click "Manual deploy"
4. Select branch: main
5. Click "Deploy latest commit"

### Clear Render Cache
- Backend: No cache to clear (models in memory)
- Frontend: Render auto-caches dist/ files
  - To clear: Use "Clear render cache" button in Render dashboard

---

## SUCCESS INDICATORS

After deployment, you should see:

✅ **Backend running:**
- Logs show "Model loaded successfully"
- /health endpoint responds with 200
- Can see "Processing..." on prediction screen

✅ **Frontend running:**
- Website loads at https://wildtrack-frontend-iuww.onrender.com
- Can navigate to login/signup
- API calls appear in backend logs

✅ **Full system working:**
- Can create account
- Can upload footprint image
- See prediction result (species name)
- Result appears in history

---

## NEXT STEPS AFTER DEPLOYMENT

1. **Test in production** - Try to break it
2. **Monitor logs** - Check for errors
3. **Collect user feedback** - What works well?
4. **Plan improvements** - What features next?
5. **Setup alerts** - Get notified of issues

---

## COST ESTIMATES

**Render Free Tier:**
- Backend: ~$0/month (sleeps after 15 min inactivity)
- Frontend: ~$0/month (no usage cost)
- **Total: FREE** ✅

**Render Starter Tier (recommended for production):**
- Backend: ~$7/month (always running, 0.5 CPU, 512MB RAM)
- Frontend: ~$0/month
- **Total: ~$7/month**

---

**Ready to deploy? Start with Phase 1: Render Dashboard Setup above.** 🚀
