#!/bin/bash
# CueSync Health Check - Detect Compromise Indicators
# Run this regularly to check for suspicious activity

set -e

DB_PATH=${DB_PATH:-"cuesync.db"}
ALERT_THRESHOLD=${ALERT_THRESHOLD:-10}  # Alert if more than N failures in last hour

echo "=== CueSync Health Check ==="
echo "Time: $(date -u +"%Y-%m-%d %H:%M:%S UTC")"
echo

# Check if database exists
if [ ! -f "$DB_PATH" ]; then
    echo "⚠️  WARNING: Database not found at $DB_PATH"
    exit 1
fi

# 1. Check for unusual volume
echo "[1] Checking cue volume..."
TOTAL_CUES=$(sqlite3 "$DB_PATH" "SELECT COUNT(*) FROM cues;")
RECENT_CUES=$(sqlite3 "$DB_PATH" "SELECT COUNT(*) FROM cues WHERE received_at > datetime('now', '-1 hour');")
echo "  Total cues: $TOTAL_CUES"
echo "  Last hour: $RECENT_CUES"

if [ "$RECENT_CUES" -gt 100 ]; then
    echo "  🚨 ALERT: High volume detected ($RECENT_CUES cues in last hour)"
fi

# 2. Check failure rate
echo
echo "[2] Checking failure rate..."
TOTAL_FAILED=$(sqlite3 "$DB_PATH" "SELECT COUNT(*) FROM cues WHERE status = 'failed';")
RECENT_FAILED=$(sqlite3 "$DB_PATH" "SELECT COUNT(*) FROM cues WHERE status = 'failed' AND received_at > datetime('now', '-1 hour');")
echo "  Total failures: $TOTAL_FAILED"
echo "  Last hour: $RECENT_FAILED"

if [ "$RECENT_FAILED" -gt "$ALERT_THRESHOLD" ]; then
    echo "  🚨 ALERT: High failure rate ($RECENT_FAILED failures in last hour)"
fi

# 3. Check for duplicate attempts
echo
echo "[3] Checking for spam patterns..."
SPAM_SOURCES=$(sqlite3 "$DB_PATH" "
    SELECT json_extract(metadata, '$.source'), COUNT(*) as count
    FROM cues
    WHERE received_at > datetime('now', '-1 hour')
    GROUP BY json_extract(metadata, '$.source')
    HAVING count > 20;
")

if [ -n "$SPAM_SOURCES" ]; then
    echo "  🚨 ALERT: Suspicious source detected:"
    echo "$SPAM_SOURCES"
else
    echo "  ✓ No spam patterns detected"
fi

# 4. Check for unknown tools
echo
echo "[4] Checking for unknown tools..."
UNKNOWN_TOOLS=$(sqlite3 "$DB_PATH" "
    SELECT DISTINCT tool, COUNT(*) as count
    FROM cues
    WHERE status = 'failed' AND error_message LIKE '%not found%'
    GROUP BY tool;
")

if [ -n "$UNKNOWN_TOOLS" ]; then
    echo "  ⚠️  Cues sent to unknown tools:"
    echo "$UNKNOWN_TOOLS"
else
    echo "  ✓ All tools recognized"
fi

# 5. Check expiration
echo
echo "[5] Checking expiration..."
if [ -f "config.yaml" ]; then
    EXPIRES_AT=$(grep "expires_at:" config.yaml | awk '{print $2}' | tr -d '"')
    EXPIRES_EPOCH=$(date -j -f "%Y-%m-%dT%H:%M:%SZ" "$EXPIRES_AT" +%s 2>/dev/null || echo "0")
    NOW_EPOCH=$(date +%s)
    DAYS_LEFT=$(( ($EXPIRES_EPOCH - $NOW_EPOCH) / 86400 ))

    echo "  Expires: $EXPIRES_AT"
    echo "  Days remaining: $DAYS_LEFT"

    if [ "$DAYS_LEFT" -lt 7 ]; then
        echo "  ⚠️  WARNING: Expiring soon, consider rotating"
    fi
else
    echo "  ⚠️  WARNING: config.yaml not found"
fi

# 6. Check recent errors
echo
echo "[6] Recent errors (last 5)..."
RECENT_ERRORS=$(sqlite3 "$DB_PATH" "
    SELECT cue_id, tool, error_message, received_at
    FROM cues
    WHERE status = 'failed'
    ORDER BY received_at DESC
    LIMIT 5;
" | head -n 5)

if [ -n "$RECENT_ERRORS" ]; then
    echo "$RECENT_ERRORS"
else
    echo "  ✓ No recent errors"
fi

echo
echo "=== Health Check Complete ==="
echo
echo "Recommendations:"
echo "  - Run this check regularly (cron: 0 * * * *)"
echo "  - Rotate if suspicious activity detected"
echo "  - Monitor webhook responses separately"
echo "  - Rotate before expiration"
echo
