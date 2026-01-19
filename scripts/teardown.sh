#!/bin/bash
# CueSync Complete Teardown (Layer 3)
# Destroys EVERYTHING: instance + static IP
# Use when: Shutting down project or moving to new region

set -e

echo "=== CueSync Complete Teardown (Layer 3) ==="
echo "⚠️  This will DESTROY:"
echo "   - Lightsail instance"
echo "   - Static IP"
echo "   - All CueSync data"
echo

# Configuration
STATIC_IP_NAME=${STATIC_IP_NAME:-"cuesync-static-ip"}
INSTANCE_NAME=${INSTANCE_NAME:-"cuesync-node"}

echo "Instance: $INSTANCE_NAME"
echo "Static IP: $STATIC_IP_NAME"
echo

# Triple confirmation for complete destruction
read -p "⚠️  Are you ABSOLUTELY SURE you want to destroy everything? (type 'destroy'): " -r
if [[ ! $REPLY == "destroy" ]]; then
    echo "Aborted."
    exit 0
fi

echo

# 1. Detach static IP
echo "[1/4] Detaching static IP..."
aws lightsail detach-static-ip --static-ip-name "$STATIC_IP_NAME" 2>/dev/null || true
sleep 5

# 2. Delete instance
echo "[2/4] Deleting instance..."
aws lightsail delete-instance --instance-name "$INSTANCE_NAME"
echo "  Waiting for deletion..."
aws lightsail wait instance-not-found --instance-name "$INSTANCE_NAME" 2>/dev/null || sleep 30

# 3. Release static IP
echo "[3/4] Releasing static IP..."
aws lightsail release-static-ip --static-ip-name "$STATIC_IP_NAME"

# 4. Clean up local files (optional)
echo "[4/4] Cleaning up local files..."
read -p "Delete local .rotation-info and backup files? (y/N): " -r
if [[ $REPLY =~ ^[Yy]$ ]]; then
    rm -f .rotation-info
    rm -f config.yaml.backup.*
    echo "  ✓ Local files cleaned"
else
    echo "  Local files kept"
fi

echo
echo "=== Teardown Complete ==="
echo
echo "✅ CueSync infrastructure destroyed"
echo "   - Instance: $INSTANCE_NAME (deleted)"
echo "   - Static IP: $STATIC_IP_NAME (released)"
echo
echo "📝 To redeploy from scratch:"
echo "   1. Edit config.yaml with new config"
echo "   2. Run: aws lightsail create-instances ..."
echo "   3. Run: ./scripts/deploy.sh"
echo
