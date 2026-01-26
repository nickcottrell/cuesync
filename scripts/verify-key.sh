#!/bin/bash
# Verify dispatcher key matches CueSync server configuration
# Usage: ./scripts/verify-key.sh

set -e

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🔑 CUESYNC KEY VERIFICATION"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Check dispatcher key exists
DISPATCHER_ENV="/Users/nickcottrell/Repositories/maestro/cue-dispatcher/.env"
if [ ! -f "$DISPATCHER_ENV" ]; then
    echo "❌ Dispatcher .env not found at: $DISPATCHER_ENV"
    exit 1
fi

# Extract key from dispatcher
UPSTREAM_KEY=$(grep "^UPSTREAM_KEY=" "$DISPATCHER_ENV" | cut -d'=' -f2)
if [ -z "$UPSTREAM_KEY" ]; then
    echo "❌ UPSTREAM_KEY not found in dispatcher .env"
    exit 1
fi

# Get expected hash from CueSync server
echo "Fetching CueSync configuration..."
EXPECTED_HASH=$(ssh cuesync-node 'grep upstream_key_hash /home/ubuntu/cuesync/config.yaml' | cut -d'"' -f2)
if [ -z "$EXPECTED_HASH" ]; then
    echo "❌ Could not fetch hash from CueSync server"
    exit 1
fi

# Compute hash of dispatcher key
COMPUTED_HASH=$(python3 -c "import hashlib; print(hashlib.sha256('$UPSTREAM_KEY'.encode()).hexdigest())")

echo "Dispatcher key: $UPSTREAM_KEY"
echo "Computed hash:  $COMPUTED_HASH"
echo "Expected hash:  $EXPECTED_HASH"
echo ""

# Verify match
if [ "$COMPUTED_HASH" = "$EXPECTED_HASH" ]; then
    echo "✅ KEY IS CORRECT - Hashes match!"
    echo ""

    # Test actual connection
    echo "Testing dispatcher connection..."
    cd /Users/nickcottrell/Repositories/maestro
    if ./cue-dispatcher/dispatch.sh --tools > /dev/null 2>&1; then
        echo "✅ DISPATCHER CAN CONNECT to CueSync"
        echo ""
        echo "Available tools:"
        ./cue-dispatcher/dispatch.sh --tools 2>/dev/null | grep -E "^\s*-"
    else
        echo "⚠️  Hash matches but connection failed"
        echo "Check network connectivity to CueSync server"
    fi
else
    echo "❌ KEY IS WRONG - Hashes don't match!"
    echo ""
    echo "The dispatcher will receive 403 Forbidden errors."
    echo ""
    echo "To fix:"
    echo "  1. Check /tmp/cuesync-pending-alerts.log for rotation info"
    echo "  2. Or rotate CueSync and update dispatcher: ./hooks rotate"
    exit 1
fi

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
