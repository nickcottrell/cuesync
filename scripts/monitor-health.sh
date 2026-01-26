#!/bin/bash
# CueSync Health Monitor - Gets noisy when things fail
# Run this via cron every 5 minutes to detect outages

set -e

CUESYNC_URL="${CUESYNC_URL:-http://3.138.41.20:8080}"
ALERT_THRESHOLD="${ALERT_THRESHOLD:-3}"  # fail this many times before alerting
STATE_FILE="/tmp/cuesync-health-state"
LOG_FILE="${LOG_FILE:-/Users/nickcottrell/Repositories/maestro/logs/cuesync-monitor.log}"
ALERT_QUEUE="/tmp/cuesync-pending-alerts.log"

log() {
    echo "[$(date -u +"%Y-%m-%dT%H:%M:%SZ")] $*" | tee -a "$LOG_FILE"
}

queue_alert() {
    local reason="$1"
    local details="$2"
    local timestamp=$(date -u +"%Y-%m-%dT%H:%M:%SZ")

    log "🚨 ALERT QUEUED: $reason"
    log "Details: $details"

    # Queue alert for manual review and dispatch
    cat >> "$ALERT_QUEUE" <<EOF
---
TIMESTAMP: $timestamp
REASON: $reason
DETAILS: $details
CUESYNC_URL: $CUESYNC_URL
---

EOF
}

# Initialize state file if it doesn't exist
if [ ! -f "$STATE_FILE" ]; then
    echo "0" > "$STATE_FILE"
fi

FAIL_COUNT=$(cat "$STATE_FILE")

# Test 1: Basic health check
log "Testing basic health endpoint..."
if ! HEALTH_RESPONSE=$(curl -sf -m 5 "$CUESYNC_URL/health" 2>&1); then
    log "❌ Health check failed: $HEALTH_RESPONSE"
    FAIL_COUNT=$((FAIL_COUNT + 1))
    echo "$FAIL_COUNT" > "$STATE_FILE"

    if [ "$FAIL_COUNT" -ge "$ALERT_THRESHOLD" ]; then
        queue_alert "Health endpoint unreachable" "Failed $FAIL_COUNT consecutive health checks.\n\nLast error: $HEALTH_RESPONSE"
    else
        log "⚠️  Failure count: $FAIL_COUNT/$ALERT_THRESHOLD (will queue alert if continues)"
    fi
    exit 1
fi

# Test 2: Parse health response
STATUS=$(echo "$HEALTH_RESPONSE" | python3 -c "import sys, json; print(json.load(sys.stdin).get('status', 'unknown'))" 2>&1)
if [ "$STATUS" != "ready" ]; then
    log "❌ Unhealthy status: $STATUS"
    FAIL_COUNT=$((FAIL_COUNT + 1))
    echo "$FAIL_COUNT" > "$STATE_FILE"

    if [ "$FAIL_COUNT" -ge "$ALERT_THRESHOLD" ]; then
        queue_alert "CueSync status not ready" "Status: $STATUS\n\nFull response:\n$HEALTH_RESPONSE"
    fi
    exit 1
fi

# Test 3: Concurrent request handling (detect threading issues)
log "Testing concurrent request handling..."
START_TIME=$(python3 -c 'import time; print(int(time.time() * 1000))')
for i in {1..3}; do
    curl -sf -m 3 "$CUESYNC_URL/stats" > /dev/null &
done
wait

END_TIME=$(python3 -c 'import time; print(int(time.time() * 1000))')
DURATION=$((END_TIME - START_TIME))

if [ "$DURATION" -gt 5000 ]; then
    log "❌ Concurrent requests too slow: ${DURATION}ms (expected <5000ms)"
    FAIL_COUNT=$((FAIL_COUNT + 1))
    echo "$FAIL_COUNT" > "$STATE_FILE"

    if [ "$FAIL_COUNT" -ge "$ALERT_THRESHOLD" ]; then
        queue_alert "CueSync performance degraded" "3 concurrent requests took ${DURATION}ms (should be <5000ms).\n\nThis suggests the server may be blocking or overloaded."
    fi
    exit 1
fi

# Test 4: Check expiration
EXPIRES_AT=$(echo "$HEALTH_RESPONSE" | python3 -c "import sys, json; print(json.load(sys.stdin).get('expires_at', ''))" 2>&1)
if [ -n "$EXPIRES_AT" ]; then
    DAYS_REMAINING=$(python3 -c "
from datetime import datetime, timezone
import sys
try:
    expires = datetime.fromisoformat('$EXPIRES_AT'.replace('Z', '+00:00'))
    now = datetime.now(timezone.utc)
    days = (expires - now).total_seconds() / 86400
    print(int(days))
except Exception as e:
    print(999, file=sys.stderr)
    sys.exit(1)
" 2>/dev/null || echo "999")

    if [ "$DAYS_REMAINING" -lt 7 ] && [ "$DAYS_REMAINING" -ge 0 ]; then
        log "⚠️  CueSync expires in $DAYS_REMAINING days"
        queue_alert "CueSync expiring soon" "CueSync will expire in $DAYS_REMAINING days.\n\nExpires at: $EXPIRES_AT\n\nAction: Rotate keys or destroy instance if no longer needed."
    fi
fi

# All tests passed - reset fail count
if [ "$FAIL_COUNT" -gt 0 ]; then
    log "✅ Recovery: Health checks now passing after $FAIL_COUNT failures"
    queue_alert "CueSync recovered" "CueSync is now healthy after $FAIL_COUNT failed checks.\n\nStatus: $STATUS\nConcurrent request duration: ${DURATION}ms"
fi

echo "0" > "$STATE_FILE"
log "✅ All health checks passed (concurrent: ${DURATION}ms)"
