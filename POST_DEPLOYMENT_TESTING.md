# ✅ POST-DEPLOYMENT TESTING GUIDE

## Immediate Post-Deployment (Within 1 hour)

### Test 1: Backend Health Check

**What to test:** Backend is running and responsive

```bash
# Test health endpoint
curl -X GET https://wildtrack-backend-j9n8.onrender.com/health

# Expected response:
{
  "status": "ok",
  "model_loaded": true,
  "uptime_seconds": 345
}

# OR (if model still downloading):
{
  "status": "ok", 
  "model_loaded": false,
  "uptime_seconds": 45
}
```

**What to check:**
- ✅ HTTP 200 status code (not 502, 503, or 504)
- ✅ "status": "ok" present
- ✅ Response time < 2 seconds
- ✅ uptime_seconds increasing (server running)

**If it fails:**
- If 502/503: Backend still starting, wait 2 minutes
- If timeout: Check Render dashboard logs
- If 400: CORS or environment variable issue

---

### Test 2: Frontend Access

**What to test:** Frontend loads and displays correctly

1. Open browser: https://wildtrack-frontend-iuww.onrender.com
2. Should see: WildTrack AI login/signup page
3. Check browser console (F12) for errors

**Visual checks:**
- ✅ Page loads within 5 seconds
- ✅ WildTrack AI logo visible
- ✅ Login/Signup buttons visible
- ✅ No error messages in red
- ✅ No JavaScript errors in console

**If page doesn't load:**
- Clear browser cache (Ctrl+Shift+Del)
- Try different browser
- Check Render frontend logs
- Verify VITE_API_URL set correctly

---

### Test 3: Authentication Flow

**What to test:** User account creation and login work

**Create Account:**
1. Click "Sign Up"
2. Enter email: `test@wildtrack.local`
3. Enter password: `TestPassword123!`
4. Click "Create Account"

**Expected behavior:**
- ✅ Account created successfully
- ✅ Automatically logged in
- ✅ Redirected to dashboard

**If signup fails:**
- Check backend logs for database errors
- Verify JWT_SECRET is set
- Check SQLite database exists

**Login Flow:**
1. Choose any existing account
2. Enter credentials
3. Click "Sign In"

**Expected behavior:**
- ✅ Login successful
- ✅ Session created
- ✅ Redirected to prediction page

---

### Test 4: Model Verification

**What to test:** ML model loaded and ready for predictions

**In backend logs:**
- Go to Render dashboard → wildtrack-backend → Logs
- Look for these messages:

```
[MODEL] Checking for models in backend/models/
[MODEL] Model files needed:
  - wildtrack_v4_cpu.keras
  - wildtrack_complete_model.h5
[MODEL] Downloading models...
[MODEL] Downloaded wildtrack_v4_cpu.keras (700.5 MB) ✓
[MODEL] Downloaded wildtrack_complete_model.h5 (520.2 MB) ✓
[MODEL] Loading model from wildtrack_v4_cpu.keras...
[MODEL] Model loaded successfully in 5.23 seconds ✓
```

**If models not loading:**
- Wait 5-10 min (download takes time)
- Check for GitHub network errors
- Verify model download retry attempts

---

### Test 5: Single Prediction

**What to test:** End-to-end prediction pipeline works

**Setup:**
1. Login to application
2. Have a footprint image ready (or find one online)

**Upload & Predict:**
1. Click "Upload Image" or drop image
2. Image should preview
3. Click "Identify Species"
4. Wait 3-5 seconds

**Expected response:**
```
Species: Leopard
Confidence: 94.2%
Additional attributes:
- Size: Large
- Pattern: Rosette spots
- Region: Africa/Asia
```

**Check backend logs for:**
- `[REQUEST] POST /predict` - Request received
- `[PROCESS] Image loaded: 1024x768 pixels`
- `[MODEL] Running inference...`
- `[RESPONSE] Prediction sent: Leopard (94.2%)`

**If prediction fails:**
- Image format issue: Try different image
- Model inference error: Upgrade to Starter tier
- Check for errors in backend logs

---

## Functional Testing (Hour 2-12)

### Test 6: Prediction History

**What to test:** Predictions saved and retrievable

**Steps:**
1. Login to application
2. Make 3-5 predictions
3. View "History" or "Past Predictions"

**Expected:**
- ✅ All predictions listed
- ✅ Species name, date, confidence visible
- ✅ Can view past images
- ✅ Sorted by most recent

**If history empty:**
- Database might not be persisting
- Check if SQLite file exists in Render
- Might need to restart service

---

### Test 7: User Management

**What to test:** Multiple users can login independently

**Steps:**
1. Create account 1: user1@test.com / Pass123!
2. Make a prediction as user1
3. Logout
4. Create account 2: user2@test.com / Pass456!
5. Make a prediction as user2
6. Verify each user sees only their history

**Expected:**
- ✅ User1 sees only user1's predictions
- ✅ User2 sees only user2's predictions
- ✅ No cross-user data leakage

---

### Test 8: File Upload Edge Cases

**What to test:** Upload robustness

**Test cases:**
1. **Large image** (>10MB)
   - Expected: Upload completes in reasonable time
   
2. **Different formats** (PNG, JPG, BMP, GIF)
   - Expected: All work or show clear error

3. **Invalid file** (TXT, PDF, ZIP)
   - Expected: Rejection with error message

4. **Corrupted image**
   - Expected: Failed upload with explanation

5. **Rapid uploads** (5 images in 10 seconds)
   - Expected: Queue processed without crashes

**If issues found:**
- File validation in backend/services/image_processing.py
- Check error messages in API response

---

### Test 9: API Rate Limiting

**What to test:** System handles heavy load

**Simulate heavy usage:**
```bash
# Script to test 10 rapid predictions
for i in {1..10}; do
  curl -X POST https://wildtrack-backend-j9n8.onrender.com/predict \
    -F "image=@image$i.jpg" \
    -H "Authorization: Bearer $JWT_TOKEN"
  sleep 0.5
done
```

**Expected:**
- ✅ All requests process without 429 (Too Many Requests)
- ✅ Slight slowdown acceptable but no crashes
- ✅ Responses remain valid

**If rate limited:**
- May need rate limiting configuration
- Document user limits
- Upgrade to Starter tier for better resources

---

### Test 10: Error Recovery

**What to test:** System handles errors gracefully

**Simulate errors:**
1. Kill backend service on Render dashboard
2. Try to use app (should show error)
3. Wait 30 seconds for Render to restart
4. Retry prediction (should work)

**Expected:**
- ✅ On error: Clear error message to user
- ✅ Not a white screen or cryptic error
- ✅ Option to retry
- ✅ System auto-recovers

---

## Performance Testing (Hour 12-24)

### Test 11: Load Testing

**What to test:** Performance under realistic load

**Using Apache Bench (ab):**
```bash
# 100 requests, 10 concurrent
ab -n 100 -c 10 https://wildtrack-backend-j9n8.onrender.com/health

# Expected results:
# Requests per second: 10-50 (free tier)
# Average response time: 50-200ms
# Failed requests: 0
```

**Using LoadForge or similar:**
- Simulate 50 concurrent users
- Each makes 5 predictions
- Expected: System stays responsive, no crashes

**Watch for:**
- Memory usage (should not exceed 512MB on free tier)
- Response time degradation
- Error rate increase

---

### Test 12: Uptime Monitoring

**What to test:** Service reliability over time

**Setup monitoring:**
1. Use Render's built-in health checks (already configured)
2. Or use external service: https://www.uptimerobot.com
   - Add: https://wildtrack-frontend-iuww.onrender.com
   - Add: https://wildtrack-backend-j9n8.onrender.com/health

**Expected:**
- ✅ Frontend: 99.5%+ uptime
- ✅ Backend: 99%+ uptime (may sleep on free tier every 15 min)

**Track for 24+ hours:**
- Health checks passing
- No unexpected restarts
- Response times consistent

---

## Security Testing (Hour 24+)

### Test 13: Authentication Security

**What to test:** Passwords protected, sessions valid

```bash
# Test 1: Can't access without login
curl https://wildtrack-backend-j9n8.onrender.com/predict
# Expected: 401 Unauthorized

# Test 2: Invalid token rejected
curl -H "Authorization: Bearer invalid-token" \
  https://wildtrack-backend-j9n8.onrender.com/predict
# Expected: 401 Unauthorized

# Test 3: Token expires
# Get token, wait 24+ hours, try to use
# Expected: 401 Unauthorized or refresh required
```

---

### Test 14: Data Validation

**What to test:** SQL injection and other attacks prevented

**Try SQL injection:**
```bash
curl -X POST https://wildtrack-backend-j9n8.onrender.com/login \
  -d "email=test' OR '1'='1&password=anything"
# Expected: Invalid credentials, not database error
```

---

### Test 15: CORS Security

**What to test:** Only allowed origins can access API

**From command line:**
```bash
curl -X GET https://wildtrack-backend-j9n8.onrender.com/health \
  -H "Origin: https://malicious.com"
# Expected: CORS error or rejection
```

---

## Deployment Success Checklist

```
IMMEDIATE TESTS (1 hour):
☐ Test 1: Backend health check (HTTP 200)
☐ Test 2: Frontend loads (no errors)
☐ Test 3: Can create account
☐ Test 4: Model loaded (check logs)
☐ Test 5: Prediction works end-to-end

FUNCTIONAL TESTS (2-12 hours):
☐ Test 6: Prediction history saves
☐ Test 7: Multi-user isolation works
☐ Test 8: File uploads handle edge cases
☐ Test 9: API handles high load
☐ Test 10: Error recovery works

EXTENDED TESTS (12-24+ hours):
☐ Test 11: Load test passes
☐ Test 12: Uptime monitoring running
☐ Test 13: Authentication secure
☐ Test 14: Data validation secure
☐ Test 15: CORS working properly

SIGN-OFF:
☐ All tests passed
☐ No critical issues
☐ Documentation updated
☐ Ready for public launch
```

---

## Reporting Issues

If tests fail, document:
1. **Test name**: Which test failed?
2. **Expected**: What should happen?
3. **Actual**: What actually happened?
4. **Error message**: Full error text
5. **Logs**: Relevant log entries
6. **Screenshot**: Image of the issue

**Where to report:**
- GitHub Issues: https://github.com/sivasrivangapandu/WILD-TRACK/issues
- Include all information from above
- Tag as "deployment" or "production"

---

**🎉 If all tests pass, deployment is successful!**
