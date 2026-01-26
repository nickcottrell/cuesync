#!/bin/bash
# Review and dispatch queued CueSync alerts
# Part of manual log review workflow

set -e

ALERT_QUEUE="/tmp/cuesync-pending-alerts.log"
MAESTRO_DIR="/Users/nickcottrell/Repositories/maestro"

# Check if there are pending alerts
if [ ! -f "$ALERT_QUEUE" ] || [ ! -s "$ALERT_QUEUE" ]; then
    echo "✅ No pending alerts"
    exit 0
fi

# Show pending alerts
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🚨 PENDING CUESYNC ALERTS"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
cat "$ALERT_QUEUE"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# Count alerts
ALERT_COUNT=$(grep -c "^REASON:" "$ALERT_QUEUE" || echo "0")
echo "Total alerts: $ALERT_COUNT"
echo ""

# Options
echo "Actions:"
echo "  1) Dispatch all alerts via email-me"
echo "  2) View full details and decide"
echo "  3) Clear all alerts (mark as reviewed)"
echo "  4) Exit (keep alerts queued)"
echo ""
read -p "Choose action [1-4]: " action

case "$action" in
    1)
        echo ""
        echo "Dispatching $ALERT_COUNT alerts..."

        # Create a summary cue
        SUMMARY_CUE=$(mktemp)
        cat > "$SUMMARY_CUE" <<EOF
{
  "cue_id": "cuesync-alert-summary-$(date +%s)",
  "tool": "email-me",
  "payload": {
    "intent_type": "alert_summary",
    "subject": "🚨 CueSync Health Alerts ($ALERT_COUNT issues)",
    "body": "CueSync monitoring detected the following issues:\n\n$(cat "$ALERT_QUEUE")\n\nReview complete log at: maestro/logs/cuesync-monitor.log\n\nGenerated: $(date)",
    "priority": "high"
  }
}
EOF

        if [ -f "$MAESTRO_DIR/cue-dispatcher/dispatch.sh" ]; then
            cd "$MAESTRO_DIR"
            ./cue-dispatcher/dispatch.sh "$SUMMARY_CUE"
            rm "$SUMMARY_CUE"

            # Clear the queue
            > "$ALERT_QUEUE"
            echo "✅ Alerts dispatched and queue cleared"
        else
            echo "❌ Error: Maestro dispatcher not found"
            rm "$SUMMARY_CUE"
            exit 1
        fi
        ;;

    2)
        echo ""
        less "$ALERT_QUEUE"
        echo ""
        read -p "Dispatch these alerts? [y/N]: " confirm
        if [[ "$confirm" =~ ^[Yy]$ ]]; then
            $0  # Re-run this script
        fi
        ;;

    3)
        > "$ALERT_QUEUE"
        echo "✅ Alert queue cleared (marked as reviewed)"
        ;;

    4)
        echo "Alerts remain queued"
        exit 0
        ;;

    *)
        echo "Invalid choice"
        exit 1
        ;;
esac
