#!/bin/bash
# CueSync Key Rotation Script (Layer 1)
# Rotates keys and config on existing instance (fast, ~30 seconds)
# For full VM rotation, use: rotate-instance.sh

set -e

echo "=== CueSync Key Rotation (Layer 1) ==="
echo

# Configuration
EXPIRES_DAYS=${EXPIRES_DAYS:-30}  # Can be set to months or years (e.g., EXPIRES_DAYS=365)
STATIC_IP=${STATIC_IP:-"3.138.41.20"}
SERVER_HOST=${SERVER_HOST:-"cuesync-node"}
SERVER_USER=${SERVER_USER:-"ubuntu"}
REMOTE_DIR=${REMOTE_DIR:-"/home/ubuntu/cuesync"}

# 1. Generate new upstream key
echo "[1/7] Generating new upstream key..."
NEW_KEY=$(openssl rand -hex 32)
echo "  Key: $NEW_KEY"

# 2. Generate hash
echo "[2/7] Generating key hash..."
NEW_HASH=$(echo -n "$NEW_KEY" | openssl dgst -sha256 | awk '{print $2}')
echo "  Hash: $NEW_HASH"

# 3. Calculate new expiration
echo "[3/7] Setting expiration..."
if [[ "$OSTYPE" == "darwin"* ]]; then
    NEW_EXPIRES=$(date -u -v+${EXPIRES_DAYS}d +"%Y-%m-%dT%H:%M:%SZ")
else
    NEW_EXPIRES=$(date -u -d "+${EXPIRES_DAYS} days" +"%Y-%m-%dT%H:%M:%SZ")
fi
echo "  Expires: $NEW_EXPIRES"

# 4. Backup old config (just in case)
echo "[4/7] Backing up old config..."
if [ -f config.yaml ]; then
    cp config.yaml "config.yaml.backup.$(date +%Y%m%d-%H%M%S)"
fi

# 5. Update config.yaml
echo "[5/7] Updating config.yaml..."
cat > config.yaml.tmp <<EOF
# CueSync Configuration - Rotated $(date -u +"%Y-%m-%d %H:%M:%S UTC")
# This relay is disposable. If compromised, destroy and recreate.

cuesync_id: cuesync-$(date +%s)
expires_at: "$NEW_EXPIRES"

# Authentication
auth:
  upstream_key_hash: "$NEW_HASH"

# Tool Mapping (webhook URLs are secret)
tools:
$(grep -A 100 "^tools:" config.yaml | grep -v "^tools:" | head -n -1 || echo "  tool1: https://httpbin.org/post")

# Storage
db_path: "cuesync.db"

# Execution
worker_interval_seconds: 10
max_retry_attempts: 3

# Optional
renewal_window_seconds: 86400
EOF

mv config.yaml.tmp config.yaml
echo "  ✓ Config updated"

# 6. Deploy to server
echo "[6/7] Deploying to server..."
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [ -f "$SCRIPT_DIR/deploy.sh" ]; then
    export SERVER_HOST SERVER_USER REMOTE_DIR
    "$SCRIPT_DIR/deploy.sh"
else
    echo "  ⚠ deploy.sh not found, skipping deployment"
fi

# 7. Save credentials for dispatcher
echo "[7/7] Saving dispatcher credentials..."
cat > .rotation-info <<EOF
# CueSync Rotation - $(date -u +"%Y-%m-%d %H:%M:%S UTC")
# IMPORTANT: Update your cue-dispatcher with these values

export UPSTREAM_KEY="$NEW_KEY"
export CUESYNC_URL="http://${STATIC_IP}:8080"

# Update dispatcher:
# cd /path/to/your-repo/.cue-dispatcher
# echo 'UPSTREAM_KEY=$NEW_KEY' > .env
# echo 'CUESYNC_URL=http://${SERVER_HOST}:8080' >> .env
EOF

echo
echo "=== Rotation Complete ==="
echo
echo "✅ New CueSync deployed"
echo "   ID: cuesync-$(date +%s)"
echo "   Expires: $NEW_EXPIRES"
echo
echo "⚠️  NEXT STEPS:"
echo "   1. Update dispatcher in each repo using CueSync:"
echo
echo "      cd /path/to/maestro/.cue-dispatcher"
echo "      cat > .env <<ENV"
echo "CUESYNC_URL=http://${SERVER_HOST}:8080"
echo "UPSTREAM_KEY=$NEW_KEY"
echo "ENV"
echo
echo "   2. Test dispatcher:"
echo "      .cue-dispatcher/dispatch.sh cues/test.json"
echo
echo "   3. Verify old relay destroyed:"
echo "      ssh ${SERVER_USER}@${SERVER_HOST} 'ps aux | grep relay.py'"
echo
echo "📝 Credentials saved to: .rotation-info"
echo "   (gitignored - delete after updating dispatchers)"
echo
