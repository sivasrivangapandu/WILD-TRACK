# 🚀 WildTrack AI - Render Deployment Guide

**Status:** Production Ready  
**Last Updated:** April 14, 2026  
**Time to Deploy:** 15-20 minutes

---

## Quick Start (3 options)

### Option 1: Interactive Wizard (Recommended for first-time users)
```bash
# Windows
DEPLOY.bat

# macOS/Linux
python deployment_wizard.py
```
The wizard will guide you step-by-step through the entire deployment process.

### Option 2: Manual Deployment (If you prefer to use Render dashboard directly)
See: **PRODUCTION_DEPLOYMENT_GUIDE.md**

### Option 3: Automated (If you have experience with Render)
```bash
git push origin main
# Go to https://dashboard.render.com
# Services will auto-deploy from render.yaml
```

---

## What You'll Need

Before deploying, gather these credentials:

| Item | Where to Get | Required? |
|------|-------------|-----------|
| **GEMINI_API_KEY** | https://makersuite.google.com/app/apikey | ✅ Yes |
| **NINJA_API_KEY** | https://api.api-ninjas.com/account | ✅ Yes |
| **Cloudinary Cloud Name** | https://cloudinary.com (optional) | ❌ No |
| **Cloudinary API Key** | https://cloudinary.com (optional) | ❌ No |
| **Cloudinary API Secret** | https://cloudinary.com (optional) | ❌ No |
| **GitHub Account** | https://github.com (for Render integration) | ✅ Yes |
| **Render Account** | https://render.com (free) | ✅ Yes |

---

## Deployment Process

### Phase 1: Preparation (5 minutes)
- [ ] Gather all credentials listed above
- [ ] Create Render account
- [ ] Log into GitHub
- [ ] Run deployment wizard (or follow manual guide)

### Phase 2: Create Services (5 minutes)
- [ ] Create backend service in Render
- [ ] Add backend environment variables
- [ ] Create frontend service in Render
- [ ] Add frontend environment variables

### Phase 3: Deployment (10-15 minutes)
- [ ] Backend builds and starts (5-10 min)
- [ ] Models auto-download from GitHub (5 min)
- [ ] Frontend builds (3-5 min)
- [ ] Both services go "Live" ✅

### Phase 4: Testing (5 minutes)
- [ ] Check backend health endpoint
- [ ] Open frontend in browser
- [ ] Create test account
- [ ] Upload test image
- [ ] See prediction result

---

## Deployment Files

### Documentation
- **PRODUCTION_DEPLOYMENT_GUIDE.md** - Complete step-by-step guide
- **ENVIRONMENT_SETUP_CHECKLIST.md** - Credentials and configuration
- **POST_DEPLOYMENT_TESTING.md** - Testing procedures (15 tests)
- **PRODUCTION_MONITORING_GUIDE.md** - Operations and monitoring
- **DEPLOYMENT_PACKAGE_COMPLETE.md** - Executive summary

### Scripts & Tools
- **DEPLOY.bat** - Windows batch file to launch wizard
- **deployment_wizard.py** - Interactive deployment wizard
- **FINAL_DEPLOYMENT_VERIFICATION.py** - System verification (8 tests)
- **ULTIMATE_DEPLOYMENT_TEST.py** - End-to-end deployment test

---

## Expected Timeline

```
Total Deployment Time: 15-25 minutes

Phase breakdown:
├─ 0-2 min:    Backend repository clone
├─ 2-7 min:    Backend dependency installation (pip install)
├─ 7-8 min:    Gunicorn startup
├─ 8-18 min:   Model auto-download from GitHub (parallel)
├─ 18-20 min:  Frontend repository clone
├─ 20-23 min:  Frontend npm install
├─ 23-26 min:  Frontend build (npm run build)
└─ 26+ min:    Services live and ready!
```

**Note:** Backend and frontend deploy in parallel, so total time is ~20 minutes, not 30+

---

## How It Works

### Architecture

```
┌─────────────────────────────────────────────────┐
│          RENDER CLOUD PLATFORM                   │
├─────────────────────────────────────────────────┤
│                                                   │
│  ┌──────────────────────┐  ┌─────────────────┐  │
│  │  BACKEND SERVICE     │  │ FRONTEND SERVICE│  │
│  │  (FastAPI)           │  │ (React + Vite)  │  │
│  │                      │  │                 │  │
│  │ • Python 3.10        │  │ • Node.js       │  │
│  │ • Gunicorn           │  │ • Static Site   │  │
│  │ • Auto-downloads     │  │ • SPA routing   │  │
│  │   models from GitHub │  │                 │  │
│  │ • Runs predictions   │  │ • User interface│  │
│  │ • /health endpoint   │  │ • API client    │  │
│  └──────────────────────┘  └─────────────────┘  │
│         ↓ Port 8000 ←─────────────────────      │
│                                                   │
│  ✨ GitHub Releases (Model Storage)              │
│     Auto-downloaded on first boot                │
└─────────────────────────────────────────────────┘
```

### Model Download Process

1. **First Boot:** Backend starts
2. **Check:** Looks for model files locally
3. **Download:** If missing, downloads from GitHub Releases:
   - wildtrack_v4_cpu.keras (700 MB)
   - wildtrack_complete_model.h5 (520 MB)
4. **Load:** Model loads into memory
5. **Ready:** Backend accepts prediction requests

---

## Cost

### Free Tier (No Initial Cost)
- Backend: Free with limitations
  - Service puts to sleep after 15 min inactivity
  - Good for MVP and testing
- Frontend: Free
- **Total: $0/month**

### Starter Tier (Production)
- Backend: $7/month
  - Always-on service (never sleeps)
  - Better performance
  - More stable for production
- Frontend: $0/month (free tier)
- **Total: ~$7/month for production**

---

## Common Issues & Solutions

### "LFS budget exceeded"
**Status:** ✅ FIXED
- Solution: Models now auto-download from GitHub instead of using Git LFS
- No action needed - this is already handled!

### "Backend not responding"
**Cause:** Still downloading models on first boot  
**Solution:** Wait 5-10 minutes, then try again

### "Login not working"
**Possible causes:**
1. Backend not fully loaded
2. JWT_SECRET not set
3. Database initialization issue

**Solutions:**
- Check backend logs in Render dashboard
- Verify JWT_SECRET is set in environment variables
- Look for database error messages

### "Frontend shows 'API Unavailable'"
**Cause:** Backend service URL incorrect  
**Solution:** Verify VITE_API_URL points to correct backend URL

### "Models taking too long to download"
**Cause:** GitHub Rate limits or network issues  
**Solution:** Backend retries automatically. Wait or restart service.

---

## Monitoring Your Deployment

### Health Check
```bash
curl https://wildtrack-backend-j9n8.onrender.com/health
# Should return:
# {"status": "ok", "model_loaded": true, "uptime_seconds": 123}
```

### Log Monitoring
Go to Render dashboard → Select service → Logs
Look for:
- `[MODEL] Loaded successfully` - Model ready ✅
- `[ERROR]` - Any errors to investigate
- `[REQUEST]` - Prediction requests being processed

### Uptime Monitoring
Recommended: Setup UptimeRobot or similar
- Monitor: `https://wildtrack-backend-j9n8.onrender.com/health`
- Interval: Every 5 minutes
- Notifications: Email/Slack alerts

---

## Next Steps After Deployment

1. **Test** (First hour)
   - Run all tests from POST_DEPLOYMENT_TESTING.md
   - Verify predictions work

2. **Monitor** (First 24 hours)
   - Check logs regularly
   - Verify no error spikes
   - Test with different image types

3. **Optimize** (Week 1)
   - Review performance metrics
   - Check response times
   - Identify bottlenecks

4. **Share** (When confident)
   - Invite beta testers
   - Gather feedback
   - Plan improvements

5. **Promote** (Ready for users)
   - Share public URL
   - Setup monitoring alerts
   - Keep documentation updated

---

## Support & Documentation

### Quick Help
- **Stuck on step X?** → See PRODUCTION_DEPLOYMENT_GUIDE.md
- **Testing questions?** → See POST_DEPLOYMENT_TESTING.md
- **Operations help?** → See PRODUCTION_MONITORING_GUIDE.md
- **Environment setup?** → See ENVIRONMENT_SETUP_CHECKLIST.md

### External Resources
- **Render Docs:** https://render.com/docs
- **FastAPI Docs:** https://fastapi.tiangolo.com
- **GitHub Docs:** https://docs.github.com

### Troubleshooting
1. Check relevant documentation guide
2. Review backend logs on Render dashboard
3. Search GitHub for similar issues
4. Create GitHub issue if stuck

---

## Security Notes

⚠️ **Important:**
- Never commit `.env` files to git
- All secrets stored in Render dashboard
- Environment variables marked secret are encrypted
- JWT_SECRET should be unique and strong (32+ characters)
- Regenerate API keys periodically

---

## Summary

✅ **Your WildTrack AI system is ready to deploy!**

**To get started:**
```bash
# Windows
DEPLOY.bat

# macOS/Linux  
python deployment_wizard.py
```

**Expected result:** Your live application at:
- Frontend: https://wildtrack-frontend-iuww.onrender.com
- Backend: https://wildtrack-backend-j9n8.onrender.com

**Time required:** 15-20 minutes

**Good luck! 🚀**

---

*For complete information, see the documentation files in the project root directory.*
