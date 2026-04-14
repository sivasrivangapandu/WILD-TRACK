# RENDER DEPLOYMENT - QUICK FIX CHECKLIST ✅

## 🚨 The Problem
You can't access the app via Render link. This is because:
1. Service URLs may have changed since initial setup
2. Environment variables not properly configured
3. CORS configuration blocking frontend-backend communication

---

## ✅ Quick Fix (5 Steps - 10 Minutes)

### Step 1: Get Your Render Service URLs
1. Go to https://dashboard.render.com/services
2. Find `wildtrack-backend` service
3. Copy the URL (e.g., `https://wildtrack-backend-XXXX.onrender.com`)
4. Find `wildtrack-frontend` service  
5. Copy the URL (e.g., `https://wildtrack-frontend-XXXX.onrender.com`)

### Step 2: Update render.yaml - Backend CORS
```yaml
# Find line ~32, update CORS_ORIGINS:
- key: CORS_ORIGINS
  value: https://wildtrack-frontend-XXXX.onrender.com,http://localhost:3000,http://localhost:8000
```
Replace `XXXX` with your actual frontend service ID.

### Step 3: Update render.yaml - Frontend API URL
```yaml
# Find line ~52, update VITE_API_URL:
- key: VITE_API_URL
  value: https://wildtrack-backend-XXXX.onrender.com
```
Replace `XXXX` with your actual backend service ID.

### Step 4: Set Environment Variables on Render Dashboard
**For Backend Service:**
1. Go to Settings → Environment
2. Add these variables:
   - `GEMINI_API_KEY` = [Your actual key]
   - `NINJA_API_KEY` = [Your actual key]
   - `CLOUDINARY_URL` = [Your actual URL]

**For Frontend Service:**
1. Go to Settings → Environment
2. Add these variables:
   - `VITE_API_URL` = `https://wildtrack-backend-XXXX.onrender.com`
   - `NODE_ENV` = `production`

### Step 5: Deploy
```bash
git add render.yaml
git commit -m "Fix: Update Render service URLs for deployment"
git push origin main
```
Render automatically redeploys on push!

---

## 🔍 Verify It Works

**Wait 2-3 minutes** for services to restart, then:

### Test 1: Backend is alive
```
Open in browser: https://wildtrack-backend-XXXX.onrender.com/health
Should show: {"status": "ok", "model_loaded": true, ...}
```

### Test 2: Frontend loads
```
Open in browser: https://wildtrack-frontend-XXXX.onrender.com
Should show: Login page (no errors)
```

### Test 3: Login works
```
1. Click Login button
2. Should NOT see "Server temporarily unavailable" error
3. Check browser console (F12) - should be clean (no CORS errors)
```

### Test 4: Prediction works
```
1. Login with any credentials
2. Upload an animal footprint image
3. Should get a prediction (class + confidence)
```

---

## ❌ If Still Not Working

### Issue: "Server temporarily unavailable"
- ✅ Wait 2-3 more minutes (TensorFlow model loading)
- ✅ Check backend logs: Render dashboard → wildtrack-backend → Logs
- ✅ Check for errors in logs

### Issue: CORS Error in browser console
- ✅ Verify frontend URL in CORS_ORIGINS is correct
- ✅ Check for typos in service URLs
- ✅ Make sure CORS_ORIGINS is comma-separated without spaces

### Issue: Frontend shows blank page
- ✅ Check frontend build logs: Render → wildtrack-frontend → Logs
- ✅ Verify VITE_API_URL is set in environment variables
- ✅ Check Node.js version (should be 18+)

### Issue: 404 Not Found
- ✅ Verify frontend URL is correct
- ✅ Check that static site is actually deployed (should see dist folder)
- ✅ Clear browser cache (Ctrl+Shift+Delete)

---

## 📝 Configuration Template

**COPY YOUR URLS AND FILL IN:**

Backend Service ID: _________________ (from URL: wildtrack-backend-**XXXX**)
Backend Full URL: https://wildtrack-backend-_________________.onrender.com

Frontend Service ID: _________________ (from URL: wildtrack-frontend-**XXXX**)
Frontend Full URL: https://wildtrack-frontend-_________________.onrender.com

**Then update render.yaml with these values.**

---

## 📞 Support

If you need to rebuild/redeploy:
1. Go to Render dashboard
2. For each service: Click "Manual Deploy" → "Deploy Latest Commit"
3. Wait 3-5 minutes for full deployment

**Current Status:**
- ✅ render.yaml updated with health checks and logging
- ✅ Backend configuration improved (120s timeout, graceful shutdown)
- ⏳ Awaiting your URL updates and environment variable setup
- ⏳ Ready for deployment via git push

---

**Next Step**: Go to Render dashboard, get your URLs, update render.yaml, then `git push`!
