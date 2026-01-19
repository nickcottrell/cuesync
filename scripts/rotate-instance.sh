#!/bin/bash
# CueSync Instance Rotation Script (Layer 2)
# Destroys and recreates entire Lightsail instance with fresh Ubuntu
# Keeps static IP constant (no dispatcher updates needed)
# Use when: Instance compromised or deep clean needed

set -e

echo "=== CueSync Instance Rotation (Layer 2) ==="
echo "⚠️  This will DESTROY the Lightsail instance and create a new one"
echo

# Configuration
EXPIRES_DAYS=${EXPIRES_DAYS:-30}
STATIC_IP_NAME=${STATIC_IP_NAME:-"cuesync-static-ip"}
INSTANCE_NAME=${INSTANCE_NAME:-"cuesync-node"}
NEW_INSTANCE_NAME=${NEW_INSTANCE_NAME:-"cuesync-node-$(date +%s)"}
BLUEPRINT_ID=${BLUEPRINT_ID:-"ubuntu_22_04"}
BUNDLE_ID=${BUNDLE_ID:-"nano_3_0"}
AVAILABILITY_ZONE=${AVAILABILITY_ZONE:-"us-east-2a"}
REGION=${REGION:-"us-east-2"}
SSH_KEY_NAME=${SSH_KEY_NAME:-"cuesync-key"}

echo "Current instance: $INSTANCE_NAME"
echo "New instance: $NEW_INSTANCE_NAME"
echo "Static IP: $STATIC_IP_NAME"
echo

# Confirm destruction
read -p "⚠️  Proceed with instance destruction? (yes/no): " -r
if [[ ! $REPLY =~ ^yes$ ]]; then
    echo "Aborted."
    exit 0
fi

# 1. Generate new keys
echo
echo "[1/8] Generating new upstream key..."
NEW_KEY=$(openssl rand -hex 32)
echo "  Key: $NEW_KEY"

echo "[2/8] Generating key hash..."
NEW_HASH=$(echo -n "$NEW_KEY" | openssl dgst -sha256 | awk '{print $2}')
echo "  Hash: $NEW_HASH"

# 2. Calculate expiration
echo "[3/8] Setting expiration..."
if [[ "$OSTYPE" == "darwin"* ]]; then
    NEW_EXPIRES=$(date -u -v+${EXPIRES_DAYS}d +"%Y-%m-%dT%H:%M:%SZ")
else
    NEW_EXPIRES=$(date -u -d "+${EXPIRES_DAYS} days" +"%Y-%m-%dT%H:%M:%SZ")
fi
echo "  Expires: $NEW_EXPIRES"

# 3. Detach static IP from old instance
echo "[4/8] Detaching static IP from old instance..."
aws lightsail detach-static-ip --static-ip-name "$STATIC_IP_NAME" || true
sleep 5

# 4. Destroy old instance
echo "[5/8] Destroying old instance..."
aws lightsail delete-instance --instance-name "$INSTANCE_NAME"
echo "  Waiting for deletion..."
aws lightsail wait instance-not-found --instance-name "$INSTANCE_NAME" 2>/dev/null || sleep 30

# 5. Create new instance
echo "[6/8] Creating new instance..."
aws lightsail create-instances \
    --instance-names "$NEW_INSTANCE_NAME" \
    --availability-zone "$AVAILABILITY_ZONE" \
    --blueprint-id "$BLUEPRINT_ID" \
    --bundle-id "$BUNDLE_ID" \
    --key-pair-name "$SSH_KEY_NAME"

echo "  Waiting for instance to be running..."
sleep 30
aws lightsail wait instance-running --instance-name "$NEW_INSTANCE_NAME" 2>/dev/null || sleep 30

# 6. Attach static IP to new instance
echo "[7/8] Attaching static IP to new instance..."
sleep 10
aws lightsail attach-static-ip \
    --static-ip-name "$STATIC_IP_NAME" \
    --instance-name "$NEW_INSTANCE_NAME"

# Get static IP address
STATIC_IP=$(aws lightsail get-static-ip --static-ip-name "$STATIC_IP_NAME" --query 'staticIp.ipAddress' --output text)
echo "  Static IP: $STATIC_IP"

# 7. Open firewall ports
echo "  Opening port 8080..."
aws lightsail open-instance-public-ports \
    --instance-name "$NEW_INSTANCE_NAME" \
    --port-info fromPort=8080,toPort=8080,protocol=tcp

# 8. Update local SSH config
echo "  Updating SSH config..."
if grep -q "Host $NEW_INSTANCE_NAME" ~/.ssh/config 2>/dev/null; then
    sed -i '' "s/Host cuesync-node/Host $NEW_INSTANCE_NAME/" ~/.ssh/config
fi

cat >> ~/.ssh/config <<EOF

# CueSync Instance (rotated $(date +%Y-%m-%d))
Host $NEW_INSTANCE_NAME
    HostName $STATIC_IP
    User ubuntu
    IdentityFile ~/.ssh/cuesync-key.pem
    StrictHostKeyChecking no
EOF

# Wait for SSH to be ready
echo "  Waiting for SSH..."
sleep 45

# 9. Update config.yaml locally
echo "[8/8] Updating config.yaml..."
if [ -f config.yaml ]; then
    cp config.yaml "config.yaml.backup.$(date +%Y%m%d-%H%M%S)"
fi

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
$(grep -A 100 "^tools:" config.yaml 2>/dev/null | grep -v "^tools:" | head -n -1 || echo "  tool1: https://httpbin.org/post")

# Storage
db_path: "cuesync.db"

# Execution
worker_interval_seconds: 60
max_retry_attempts: 3

# Optional
renewal_window_seconds: 86400
EOF

mv config.yaml.tmp config.yaml
echo "  ✓ Config updated"

# 10. Deploy CueSync to new instance
echo
echo "Deploying CueSync to new instance..."
export SERVER_HOST="$NEW_INSTANCE_NAME"
export SERVER_USER="ubuntu"
export REMOTE_DIR="/home/ubuntu/cuesync"
export CUESYNC_PORT="8080"
./scripts/deploy.sh

# 11. Save credentials
cat > .rotation-info <<EOF
# CueSync Instance Rotation - $(date -u +"%Y-%m-%d %H:%M:%S UTC")
# IMPORTANT: Update your cue-dispatcher with these values

export UPSTREAM_KEY="$NEW_KEY"
export CUESYNC_URL="http://${STATIC_IP}:8080"

# Old instance destroyed: $INSTANCE_NAME
# New instance created: $NEW_INSTANCE_NAME
# Static IP (unchanged): $STATIC_IP

# Update dispatcher:
# cd /path/to/maestro/.cue-dispatcher
# cat > .env <<ENV
# CUESYNC_URL=http://${STATIC_IP}:8080
# UPSTREAM_KEY=$NEW_KEY
# ENV
EOF

echo
echo "=== Instance Rotation Complete ==="
echo
echo "✅ New instance deployed"
echo "   Old: $INSTANCE_NAME (destroyed)"
echo "   New: $NEW_INSTANCE_NAME"
echo "   Static IP: $STATIC_IP (unchanged)"
echo "   Expires: $NEW_EXPIRES"
echo
echo "⚠️  NEXT STEPS:"
echo "   1. Update dispatcher in each repo:"
echo
echo "      cd /path/to/maestro/.cue-dispatcher"
echo "      cat > .env <<ENV"
echo "CUESYNC_URL=http://${STATIC_IP}:8080"
echo "UPSTREAM_KEY=$NEW_KEY"
echo "ENV"
echo
echo "   2. Test dispatcher:"
echo "      .cue-dispatcher/dispatch.sh .cue-dispatcher/examples/test.json"
echo
echo "   3. Clean up old SSH config entry for $INSTANCE_NAME if needed"
echo
echo "📝 Credentials saved to: .rotation-info"
echo
