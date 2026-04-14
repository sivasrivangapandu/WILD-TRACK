# 🔧 RENDER ENVIRONMENT SETUP CHECKLIST

## Pre-Deployment Environment Preparation

### Step 1: Prepare Your Backend Variables

**Generate JWT_SECRET (32+ characters):**
```bash
# On Windows PowerShell:
[System.Convert]::ToBase64String([System.Text.Encoding]::UTF8.GetBytes((1..32 | Get-Random -SetSeed (Get-Date).Ticks | %{[char](33..126 | Get-Random)})-join ''))

# Or use online generator: https://www.uuidgenerator.com/
```

**Get your Gemini API Key:**
1. Go to https://makersuite.google.com/app/apikey
2. Create new API key
3. Copy and save securely

**Get your Ninja API Key:**
1. Go to https://api.api-ninjas.com
2. Sign up / login
3. Go to Account Settings
4. Copy your API key

**Setup Cloudinary (Optional but recommended):**
1. Sign up at https://cloudinary.com
2. Get Cloud Name from dashboard
3. Get API Key from Account Settings
4. Get API Secret from Account Settings

### Step 2: Prepare Frontend Variables

**VITE_API_URL:**
- After backend deployed, get URL from Render dashboard
- Format: `https://wildtrack-backend-XXXXX.onrender.com`
- Add to frontend environment

### Step 3: Create .env.local for Local Testing (Optional)

Before deploying to Render, test locally:

**d:\Wild Track AI\backend\.env.local:**
```
JWT_SECRET=your-32-char-secret-here
GEMINI_API_KEY=AIzaSyD-rz0mo81f7H6wFjJZ-TeG-yLLKmjxOXY
NINJA_API_KEY=28hgS0UqtEDtFKhughV9fRQx7tVogcXZ5XbNkGNZ
CLOUDINARY_CLOUD_NAME=your-cloud-name
CLOUDINARY_API_KEY=your-api-key
CLOUDINARY_API_SECRET=your-secret
CORS_ORIGINS=http://localhost:3000,http://localhost:8000
```

**d:\Wild Track AI\frontend\.env.local:**
```
VITE_API_URL=http://localhost:8000
VITE_NODE_ENV=development
```

### Step 4: Security Best Practices

⚠️ **IMPORTANT: Never commit .env files to git!**

✅ Do this:
- Generate strong JWT_SECRET (32+ characters, mix of letters/numbers/symbols)
- Use different secrets for dev and production
- Rotate keys periodically
- Store in Render dashboard, not in code

❌ Don't do this:
- Commit .env files to GitHub
- Share API keys in chat or email
- Use same key for development and production
- Store secrets in render.yaml

### Step 5: Render Service Setup

#### Backend Service Configuration
```yaml
Service Type: Web Service
Name: wildtrack-backend
Environment: Python 3
Build Command: cd backend && pip install -r requirements.txt
Start Command: cd backend && gunicorn main:app --workers 2 --worker-class uvicorn.workers.UvicornWorker --bind 0.0.0.0:$PORT --timeout 120
Region: Oregon
Plan: Free (or Starter)
Health Check Path: /health
Health Check Interval: 30s
```

**Environment Variables:**
| Key | Value | Secret? |
|-----|-------|---------|
| JWT_SECRET | (generate 32-char) | ✅ Yes |
| GEMINI_API_KEY | (from Google) | ✅ Yes |
| NINJA_API_KEY | (from API Ninjas) | ✅ Yes |
| CLOUDINARY_CLOUD_NAME | (from Cloudinary) | ❌ No |
| CLOUDINARY_API_KEY | (from Cloudinary) | ✅ Yes |
| CLOUDINARY_API_SECRET | (from Cloudinary) | ✅ Yes |
| CORS_ORIGINS | https://wildtrack-frontend-iuww.onrender.com,http://localhost:3000 | ❌ No |
| PYTHON_VERSION | 3.10.0 | ❌ No |
| PORT | 8000 | ❌ No |

#### Frontend Service Configuration
```yaml
Service Type: Static Site
Name: wildtrack-frontend
Build Command: cd frontend && npm install && npm ci --prefer-offline --no-audit && npm run build
Publish Directory: frontend/dist
Region: Oregon
Plan: Free
```

**Environment Variables:**
| Key | Value |
|-----|-------|
| VITE_API_URL | https://wildtrack-backend-j9n8.onrender.com |
| NODE_ENV | production |

### Step 6: GitHub Integration

✅ **Already configured in repository:**
- render.yaml exists with both services
- .gitignore ignores .env files
- Backend code has environment variable handling
- Frontend has VITE_API_URL configuration

### Step 7: Pre-Deployment Verification

Run these commands before deploying:

```bash
# Check backend syntax
python -m py_compile backend/main.py
python -m py_compile backend/database.py
python -m py_compile backend/config.py

# Check frontend build locally (optional)
cd frontend
npm install
npm run build
# Should create dist/ directory

# Verify requirements.txt
pip install -r backend/requirements.txt --dry-run
# Should install 22 packages without errors
```

### Step 8: Deployment Checklist

| Item | Status | Notes |
|------|--------|-------|
| JWT_SECRET generated | ☐ | 32+ characters, mix of char types |
| GEMINI_API_KEY obtained | ☐ | From makersuite.google.com |
| NINJA_API_KEY obtained | ☐ | From api-ninjas.com |
| Cloudinary setup (optional) | ☐ | Can skip for MVP |
| GitHub repo connected | ☐ | Already done |
| .env files NOT committed | ☐ | Check git status |
| Backend syntax verified | ☐ | Run py_compile checks |
| render.yaml exists | ☐ | In project root |
| Backend service created | ☐ | In Render dashboard |
| Frontend service created | ☐ | In Render dashboard |
| Environment vars added | ☐ | All keys entered in Render |
| Initial deployment started | ☐ | Watch logs during build |

### Step 9: Expected Deployment Timeline

```
Total Time: ~20-25 minutes

Timeline:
┌─────────────────────────────────────────────────────┐
│ 0-2 min    │ Backend clone            │ ████          │
│ 2-7 min    │ Backend dependencies     │ ████████      │
│ 7-8 min    │ Gunicorn startup         │ ███           │
│ 8-18 min   │ Model download (async)   │ ██████████    │
│ 18-20 min  │ Frontend clone & build   │ █████         │
│ 20-25 min  │ Final setup & cooling    │ ████          │
└─────────────────────────────────────────────────────┘

Note: Backend and Frontend deploy in parallel, both finish ~20 min
Model download happens in background after startup (~8-18 min)
```

### Step 10: Post-Deployment Verification

After services show "Live" in Render dashboard:

```bash
# 1. Test backend health
curl https://wildtrack-backend-j9n8.onrender.com/health

# 2. Check backend logs
# Go to Render dashboard → wildtrack-backend → Logs
# Look for: "[MODEL] Loaded successfully"

# 3. Open frontend
# Navigate to: https://wildtrack-frontend-iuww.onrender.com

# 4. Test login
# Click Sign Up, create account, login

# 5. Test prediction
# Upload image, receive prediction
```

---

## ENVIRONMENT VARIABLE SECURITY

### Keeping Secrets Safe

**In Development (Local):**
- Store in `.env` file (gitignored)
- Never share or commit

**In Production (Render):**
- Store only in Render dashboard
- Mark sensitive ones as "Secret"
- Render encrypts secret values
- Not visible in logs or URL

**Rotation Schedule:**
- JWT_SECRET: Every 3 months
- API Keys: Every 6 months
- Or immediately if compromised

### Detecting Compromised Keys

If an API key is exposed:
1. Immediately revoke it (in provider's dashboard)
2. Generate new key
3. Update in Render environment variables
4. Render automatically redeploys services
5. Old key no longer works

---

## TROUBLESHOOTING ENVIRONMENT ISSUES

### Issue: "TypeError: string indices must be integers"
**Cause:** Environment variable not set
**Solution:** Check all vars are added in Render dashboard, not just render.yaml

### Issue: "CORS error on frontend"
**Cause:** CORS_ORIGINS not set or incorrect value
**Solution:** Add to backend environment: `CORS_ORIGINS=https://wildtrack-frontend-iuww.onrender.com,http://localhost:3000`

### Issue: "Models not downloading"
**Cause:** GitHub API rate limit or network issue
**Solution:** Backend retries automatically (3 attempts), wait 2 minutes and check logs

### Issue: "TensorFlow memory error"
**Cause:** Free tier only has 512MB RAM
**Solution:** Upgrade to Starter tier ($7/month) or accept demo mode

---

## QUICK START CHECKLIST

```
Ready to deploy? Follow this order:

1. ☐ Generate JWT_SECRET
2. ☐ Get GEMINI_API_KEY
3. ☐ Get NINJA_API_KEY
4. ☐ Setup Cloudinary (optional)
5. ☐ Go to https://dashboard.render.com
6. ☐ Create backend service
7. ☐ Add backend environment variables
8. ☐ Create frontend service
9. ☐ Add frontend environment variables
10. ☐ Monitor deployment (20 min)
11. ☐ Test health endpoint
12. ☐ Test login
13. ☐ Test prediction
14. ☐ Celebrate! 🎉
```

---

For detailed deployment steps, see: **PRODUCTION_DEPLOYMENT_GUIDE.md**
