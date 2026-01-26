#!/bin/bash
# Daily/Weekly CueSync Monitoring Summary
# Shows issues that need attention in log review

set -e

MONITOR_LOG="/Users/nickcottrell/Repositories/maestro/logs/cuesync-monitor.log"
ALERT_QUEUE="/tmp/cuesync-pending-alerts.log"
DAYS="${1:-1}"  # Default: last 1 day

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📊 CUESYNC MONITORING SUMMARY - Last $DAYS day(s)"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Check if log exists
if [ ! -f "$MONITOR_LOG" ]; then
    echo "No monitoring log found at: $MONITOR_LOG"
    echo "Run './hooks monitor' to start monitoring"
    exit 0
fi

# Calculate date cutoff
if [ "$DAYS" -eq 1 ]; then
    SINCE=$(date -v-1d -u +"%Y-%m-%d")
elif [ "$DAYS" -eq 7 ]; then
    SINCE=$(date -v-7d -u +"%Y-%m-%d")
else
    SINCE=$(date -v-${DAYS}d -u +"%Y-%m-%d")
fi

# Count health checks run
TOTAL_CHECKS=$(grep -c "Testing basic health endpoint" "$MONITOR_LOG" 2>/dev/null || echo "0")
FAILED_CHECKS=$(grep -c "❌" "$MONITOR_LOG" 2>/dev/null || echo "0")
PASSED_CHECKS=$((TOTAL_CHECKS - FAILED_CHECKS))

echo "Health Checks:"
echo "  Total runs:    $TOTAL_CHECKS"
echo "  Passed:        $PASSED_CHECKS ✅"
echo "  Failed:        $FAILED_CHECKS ❌"
echo ""

# Performance stats
if grep -q "concurrent:" "$MONITOR_LOG" 2>/dev/null; then
    AVG_RESPONSE=$(grep "concurrent:" "$MONITOR_LOG" | \
        sed 's/.*concurrent: \([0-9]*\)ms.*/\1/' | \
        awk '{ sum += $1; count++ } END { if(count > 0) print int(sum/count); else print 0 }')
    echo "Performance:"
    echo "  Avg response:  ${AVG_RESPONSE}ms"
    echo ""
fi

# Show any failures
if [ "$FAILED_CHECKS" -gt 0 ]; then
    echo "Recent Failures:"
    grep "❌" "$MONITOR_LOG" | tail -5
    echo ""
fi

# Show queued alerts (the important part!)
if [ -f "$ALERT_QUEUE" ] && [ -s "$ALERT_QUEUE" ]; then
    ALERT_COUNT=$(grep -c "^REASON:" "$ALERT_QUEUE" || echo "0")
    echo "⚠️  PENDING ALERTS: $ALERT_COUNT"
    echo ""
    echo "Issues requiring attention:"
    grep "^REASON:" "$ALERT_QUEUE" | sed 's/REASON: /  • /'
    echo ""
    echo "🔔 Run './hooks review-alerts' to review and dispatch"
else
    echo "✅ No pending alerts"
fi

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "View full log: cat $MONITOR_LOG"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
