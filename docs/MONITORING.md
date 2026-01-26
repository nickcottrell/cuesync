# CueSync Monitoring

**Automated health monitoring with email alerts when failures are detected.**

---

## Quick Start

```bash
# Run health check manually
./hooks monitor

# Set up automated monitoring (cron every 5 minutes)
crontab -e
# Add this line:
*/5 * * * * cd /Users/nickcottrell/Repositories/clean-cuesync && ./hooks monitor >> /tmp/cuesync-monitor.log 2>&1
```

---

## How It Works

The monitoring script (`scripts/monitor-health.sh`) runs 4 tests:

1. **Health endpoint** - Checks if `/health` responds
2. **Status check** - Verifies status is "ready"
3. **Concurrent requests** - Sends 3 parallel requests to detect threading issues
4. **Expiration warning** - Alerts if expiring within 7 days

### Failure Threshold

**Failures are tracked across runs:**
- Failure 1: Warning logged, no alert
- Failure 2: Warning logged, no alert
- Failure 3: **Alert sent via email-me tool**

This prevents false alarms from transient network issues.

### Recovery Detection

When service recovers after failures, an alert is sent confirming recovery.

---

## Alert Mechanism

Alerts are sent via the **email-me** tool through the maestro dispatcher:

```json
{
  "subject": "🚨 CueSync Health Alert: [reason]",
  "body": "Details about the failure...",
  "priority": "high"
}
```

**Prerequisites:**
- Maestro dispatcher must be configured at `/Users/nickcottrell/Repositories/maestro/cue-dispatcher/`
- The `email-me` tool must be configured in CueSync

---

## What Gets Monitored

### Health Endpoint Unreachable
```
ALERT: Health endpoint unreachable
Details: Failed 3 consecutive health checks
```

**Causes:**
- CueSync service stopped
- Network connectivity issues
- Server is down
- Port 8080 blocked

**Action:** Check service status with `./hooks status` or `./hooks ssh`

### Unhealthy Status
```
ALERT: CueSync status not ready
Status: expired
```

**Causes:**
- CueSync has expired
- Configuration issue

**Action:** Check expiration with `./hooks health`

### Performance Degraded
```
ALERT: CueSync performance degraded
Details: 3 concurrent requests took 8532ms (should be <5000ms)
```

**Causes:**
- Server blocking (threading issue)
- Resource exhaustion
- Heavy load

**Action:**
- Check server resources: `./hooks ssh` → `htop`
- Review recent logs: `./hooks logs 100`
- Consider instance rotation if persistent

### Expiring Soon
```
ALERT: CueSync expiring soon
Details: CueSync will expire in 5 days
```

**Causes:**
- Normal expiration approaching

**Action:**
- Rotate keys: `./hooks rotate 30`
- Or rotate instance: `./hooks rotate-instance 90`

---

## Cron Setup

**Check every 5 minutes:**
```bash
*/5 * * * * cd /Users/nickcottrell/Repositories/clean-cuesync && ./hooks monitor >> /tmp/cuesync-monitor.log 2>&1
```

**Check every hour:**
```bash
0 * * * * cd /Users/nickcottrell/Repositories/clean-cuesync && ./hooks monitor >> /tmp/cuesync-monitor.log 2>&1
```

**Check during business hours only (9am-6pm weekdays):**
```bash
0 9-18 * * 1-5 cd /Users/nickcottrell/Repositories/clean-cuesync && ./hooks monitor >> /tmp/cuesync-monitor.log 2>&1
```

---

## Configuration

Environment variables (optional):

```bash
# Override CueSync URL
export CUESYNC_URL=http://custom-url:8080

# Change alert threshold (default: 3)
export ALERT_THRESHOLD=5

# Custom log file
export LOG_FILE=/var/log/cuesync-monitor.log
```

---

## Logs

**View monitoring log:**
```bash
cat /tmp/cuesync-health.log
```

**View cron output:**
```bash
cat /tmp/cuesync-monitor.log
```

**Sample log entry (success):**
```
[2026-01-26T06:59:31Z] Testing basic health endpoint...
[2026-01-26T06:59:31Z] Testing concurrent request handling...
[2026-01-26T06:59:31Z] ✅ All health checks passed (concurrent: 208ms)
```

**Sample log entry (failure):**
```
[2026-01-26T07:00:08Z] Testing basic health endpoint...
[2026-01-26T07:00:08Z] ❌ Health check failed: curl: (7) Failed to connect
[2026-01-26T07:00:08Z] ⚠️  Failure count: 1/3 (will alert if continues)
```

---

## Testing

**Test successful health check:**
```bash
./hooks monitor
```

**Test failure scenario:**
```bash
CUESYNC_URL=http://localhost:9999 ./hooks monitor
# Run 3 times to trigger alert
```

**Reset failure count:**
```bash
rm /tmp/cuesync-health-state
```

---

## State Files

**Failure counter:**
- Location: `/tmp/cuesync-health-state`
- Contains: Number of consecutive failures
- Resets to 0 on successful check

**Log file:**
- Location: `/tmp/cuesync-health.log`
- Contains: All health check results with timestamps

---

## Troubleshooting

**Monitoring script not found:**
```bash
# Ensure you're in the correct directory
cd /Users/nickcottrell/Repositories/clean-cuesync
./hooks monitor
```

**Alerts not sending:**
- Verify maestro dispatcher exists: `ls /Users/nickcottrell/Repositories/maestro/cue-dispatcher/`
- Check CueSync health manually: `curl http://3.138.41.20:8080/health`
- Test dispatcher: `cd /Users/nickcottrell/Repositories/maestro && ./cue-dispatcher/dispatch.sh --tools`

**False positive alerts:**
- Increase `ALERT_THRESHOLD` to require more consecutive failures
- Check network connectivity to CueSync server

---

## Integration with Other Tools

**Send to Slack instead of email:**
Modify `send_alert()` in `scripts/monitor-health.sh` to use a different tool:
```bash
"tool": "slack-notify",  # Instead of email-me
```

**Run from systemd timer instead of cron:**
```ini
[Unit]
Description=CueSync Health Monitor

[Timer]
OnCalendar=*:0/5
Persistent=true

[Install]
WantedBy=timers.target
```

---

**Last Updated:** 2026-01-26
