# 📊 PRODUCTION MONITORING & ALERTS GUIDE

## Real-Time Monitoring Dashboard

### Render Dashboard Monitoring

**Access Point:** https://dashboard.render.com

**Key Metrics to Monitor:**

#### Backend Service (wildtrack-backend)
```
Status:
├─ Service Status (Running / Suspended / Failed)
├─ Active Instances (should be 1)
├─ CPU Usage (should be <50% at rest)
├─ Memory Usage (should be <300MB at rest)
└─ Network Traffic (variable with usage)

Logs:
├─ Real-time log stream
├─ Last 100 lines auto-visible
├─ Search by keyword ([MODEL], [ERROR], etc.)
└─ Tail -f functionality

Events:
├─ Deployment history
├─ Restart events
├─ Error events
└─ Timestamps of all changes
```

#### Frontend Service (wildtrack-frontend)
```
Status:
├─ Service Status (Published / Failed)
├─ Build Status (Success / Failed)
├─ Last Deploy time
└─ Coverage information if available

Logs:
├─ Build logs (npm install, npm run build)
├─ Deploy logs (asset upload)
└─ Any build errors
```

---

## Daily Monitoring Checklist

### Morning (Start of Day)

```bash
# 1. Check backend health
curl https://wildtrack-backend-j9n8.onrender.com/health -s | jq .

# Expected:
# {
#   "status": "ok",
#   "model_loaded": true,
#   "uptime_seconds": 86400
# }
```

**Visual Check:**
- [ ] Backend shows "Running" in dashboard
- [ ] No failed deployment indicators
- [ ] Recent logs show normal operation
- [ ] No error messages in last hour

**Database Check (via API):**
```bash
# Check if database is responsive
curl -X GET https://wildtrack-backend-j9n8.onrender.com/history \
  -H "Authorization: Bearer $TOKEN"
# Expected: 200 OK with user's prediction history
```

---

### During Business Hours (Every 4 hours)

1. **Check Resource Usage**
   - Render dashboard → Backend service
   - CPU: Should average 5-20%
   - Memory: Should average 200-400MB
   - Network: Normal for usage level

2. **Review Recent Predictions**
   ```bash
   curl https://wildtrack-backend-j9n8.onrender.com/analytics \
     -H "Authorization: Bearer $ADMIN_TOKEN"
   ```
   - Predictions processed in last 4 hours
   - Average response time
   - Error rate (should be <1%)

3. **Check Error Logs**
   - Render dashboard → Logs
   - Search for: "[ERROR]", "[WARN]", "Exception"
   - Any critical errors? → Take action

---

### Evening (End of Day)

1. **Generate Daily Report**
   ```bash
   # Summary metrics for the day
   - Total predictions: X
   - Average response time: X ms
   - Error rate: X%
   - Uptime: X%
   - Peak concurrent users: X
   ```

2. **Archive Logs**
   - Export Render logs to file
   - Save in daily folder: `logs/2026-04-14/`
   - Keep for 30 days minimum

3. **End-of-Day Status**
   - [ ] No critical errors
   - [ ] Performance acceptable
   - [ ] Resource usage normal
   - [ ] All users can access

---

## Alert Configuration

### Using UptimeRobot (Free Tier)

**Setup Health Check Alerts:**

1. Go to https://uptimerobot.com
2. Create new monitor:
   - URL: https://wildtrack-backend-j9n8.onrender.com/health
   - Type: HTTPS
   - Interval: 5 minutes
   - Notifications: Slack / Email

3. Create notification:
   - Send alert if down
   - Send recovery alert
   - Email: your-email@example.com

**Expected Behavior:**
- Downtime: Alert within 5 minutes
- Recovery: Alert when back online
- False positives: Very rare

---

### DIY Monitoring Script

```python
#!/usr/bin/env python3
"""
Simple monitoring script - run every hour as cron job
"""
import requests
import json
from datetime import datetime

def check_backend():
    try:
        r = requests.get(
            'https://wildtrack-backend-j9n8.onrender.com/health',
            timeout=10
        )
        data = r.json()
        
        alert = False
        if r.status_code != 200:
            alert = True
            print(f"[ALERT] Backend returned HTTP {r.status_code}")
        
        if not data.get('status') == 'ok':
            alert = True
            print(f"[ALERT] Backend status not OK: {data.get('status')}")
        
        model_loaded = data.get('model_loaded', False)
        if not model_loaded:
            print(f"[WARN] Model not loaded (may still be downloading)")
        
        if not alert:
            print(f"[OK] Backend healthy at {datetime.now()}")
        
        return not alert
        
    except Exception as e:
        print(f"[ERROR] Backend check failed: {e}")
        return False

def check_frontend():
    try:
        r = requests.get(
            'https://wildtrack-frontend-iuww.onrender.com/',
            timeout=10
        )
        
        if r.status_code == 200:
            print(f"[OK] Frontend responding at {datetime.now()}")
            return True
        else:
            print(f"[ALERT] Frontend returned HTTP {r.status_code}")
            return False
            
    except Exception as e:
        print(f"[ERROR] Frontend check failed: {e}")
        return False

if __name__ == '__main__':
    backend_ok = check_backend()
    frontend_ok = check_frontend()
    
    if not (backend_ok and frontend_ok):
        print(f"[ALERT] System status: DEGRADED")
        # Send email/Slack alert here
    else:
        print(f"[OK] All systems operational")
```

**Run as hourly cron job:**
```bash
# On Linux/Mac
0 * * * * python /path/to/monitoring.py >> /var/log/wildtrack-monitor.log

# On Windows (Task Scheduler)
# Task: Run every hour
# Action: python "C:\path\to\monitoring.py"
```

---

## Key Metrics to Track

### Performance Metrics

| Metric | Target | Warning | Critical |
|--------|--------|---------|----------|
| Response Time | <2s | >3s | >5s |
| Error Rate | <0.5% | >1% | >5% |
| Uptime | 99%+ | 98% | <98% |
| CPU Usage | <30% | >50% | >80% |
| Memory Usage | <300MB | >400MB | >450MB |

### Business Metrics

| Metric | Good | Fair | Poor |
|--------|------|------|------|
| Daily Predictions | >100 | 50-100 | <50 |
| User Growth | +5%/week | +2%/week | 0%/week |
| Active Users | >20/day | 10-20/day | <10/day |
| Model Accuracy | >90% | 80-90% | <80% |

---

## Incident Response

### Service Down - Immediate Steps

1. **Verify Down Status**
   ```bash
   curl -I https://wildtrack-backend-j9n8.onrender.com/health
   # If connection refused or timeout → Service down
   ```

2. **Check Render Dashboard**
   - Go to https://dashboard.render.com
   - Service status: Running? Suspended? Failed?
   - Last event timestamp

3. **Check Recent Logs**
   - Look for crash, out of memory, or error
   - Screenshot error message
   - Note timestamp

4. **Attempt Recovery**
   - **Option A:** Wait 30 seconds (Render auto-restarts)
   - **Option B:** Manual deploy from dashboard
     - Services → wildtrack-backend → Manual Deploy
     - Select branch: main
     - Click "Deploy"

5. **Verify Recovery**
   ```bash
   # Every 30 seconds, check status
   curl https://wildtrack-backend-j9n8.onrender.com/health
   # Should return HTTP 200 after recovery
   ```

6. **Document Incident**
   - Time down: [exact time]
   - Time resolved: [exact time]
   - Duration: [minutes]
   - Cause: [from logs]
   - Resolution: [what fixed it]

### High Error Rate - Diagnostics

**If error rate > 5% within 1 hour:**

1. Check backend logs for pattern:
   ```
   [ERROR] → Type of error?
   [MODEL] → Model loading issues?
   [DATABASE] → Database connection problems?
   ```

2. Common causes:
   - **Image Processing Error** → User uploaded invalid format
   - **Model Loading** → Still downloading on startup
   - **Database** → SQLite locked,upgrade needed
   - **Memory** → Running out of RAM, restart needed

3. Resolution options:
   - Restart service if memory issue
   - Wait if model downloading
   - Check user uploaded file format
   - Upgrade to Starter tier if persistent

### High Resource Usage - Actions

**If CPU > 80% or Memory > 90%:**

1. Quick fixes:
   - Reduce concurrent users (polite message)
   - Restart service (clears memory)
   - Enable query caching

2. Longer term:
   - Upgrade to Starter tier (+$7/month)
   - Optimize database queries
   - Add request rate limiting

---

## Logging Strategy

### What to Log

**Backend logs to track:**
- [BUILD] Build phase events
- [START] Startup messages
- [MODEL] Model loading progress
- [REQUEST] API requests
- [PROCESS] Image processing
- [RESPONSE] Predictions
- [ERROR] Any errors
- [WARN] Warnings

**Frontend logs to track:**
- Page load times
- API requests/responses
- JavaScript errors
- Network issues
- User interactions

### Log Retention

- **Current**: Always visible in Render dashboard
- **Archive**: Download daily
- **Analysis**: Keep for 7 days minimum
- **Compliance**: Keep for 30 days + deletion policy

### Log Analysis

Daily quick scan:
```bash
# Count errors in last hour
grep "\[ERROR\]" logs/wildtrack-backend.log | wc -l

# Find slow requests
grep "\[RESPONSE\]" logs/wildtrack-backend.log | grep "time_ms:[50-99][0-9][0-9]"

# Find all model errors
grep "\[MODEL\].*error" logs/wildtrack-backend.log
```

---

## Weekly Maintenance

Every Monday morning:

- [ ] Review last week's metrics
- [ ] Check for trends (uptime, errors, performance)
- [ ] Rotate secrets if needed
- [ ] Update documentation
- [ ] Plan maintenance windows if needed
- [ ] Brief team on status

**Generate weekly report:**
```markdown
# Week of April 14-20, 2026

## Metrics
- Uptime: 99.8%
- Avg Response Time: 1.2 seconds
- Total Predictions: 1,234
- Error Rate: 0.3%
- Active Users: 45

## Incidents
- None critical

## Performance
- No bottlenecks identified
- Model loading time stable
- Database queries optimized

## Next Week
- Monitor user growth
- Consider Starter tier upgrade
```

---

## Quarterly Review

Every 3 months, conduct full system review:

1. **Security Audit**
   - Check for exposed credentials
   - Rotate API keys
   - Review access logs

2. **Performance Review**
   - Analyze quarterly trends
   - Identify bottlenecks
   - Plan optimizations

3. **Capacity Planning**
   - Project user growth
   - Forecast resource needs
   - Plan tier upgrades

4. **Documentation Update**
   - Update all guides
   - Add lessons learned
   - Record best practices

---

## Alert Notification Setup

### Email Alerts

**Configure in Render:**
- Services → Select service → Settings
- Notifications tab
- Add email for critical alerts
- Test email delivery

### Slack Integration

**Setup Slack bot:**
```
1. Create incoming webhook: https://api.slack.com/messaging/webhooks
2. Add webhook URL to monitoring script
3. Script posts alerts to channel
4. Team sees alerts in real-time
```

### SMS Alerts (Optional)

**Using Twilio (paid):**
- Setup Twilio account
- Add phone number
- Configure for critical alerts only
- Keep for on-call alerts

---

## Success Indicators

A healthy production system shows:

✅ **Uptime > 99%** (only brief scheduled maintenance downtime)
✅ **Response Time < 2 seconds** (99th percentile)
✅ **Error Rate < 0.5%** (mostly user errors, not system)
✅ **User Growth** (week-over-week increase)
✅ **Prediction Accuracy > 90%** (model performing well)
✅ **No Critical Security Issues** (logs clean)

---

*Last Updated: April 14, 2026*
*Next Review: July 14, 2026*
