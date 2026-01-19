#!/bin/bash
# CueSync Deployment Script
# Deploys the minimal relay to a server

set -e

# Configuration (override with environment variables)
SERVER_HOST=${SERVER_HOST:-"your-server.example.com"}
SERVER_USER=${SERVER_USER:-"ubuntu"}
SERVER_PORT=${SERVER_PORT:-"22"}
REMOTE_DIR=${REMOTE_DIR:-"/opt/cuesync"}
CUESYNC_PORT=${CUESYNC_PORT:-"8080"}

echo "=== CueSync Deployment ==="
echo "Server: $SERVER_USER@$SERVER_HOST:$SERVER_PORT"
echo "Remote directory: $REMOTE_DIR"
echo "CueSync port: $CUESYNC_PORT"
echo

# Create remote directory
ssh -p "$SERVER_PORT" "$SERVER_USER@$SERVER_HOST" "mkdir -p $REMOTE_DIR"

# Copy files
echo "Copying files..."
scp -P "$SERVER_PORT" \
    relay.py \
    requirements.txt \
    config.yaml \
    "$SERVER_USER@$SERVER_HOST:$REMOTE_DIR/"

# Install dependencies and create systemd service
echo "Setting up relay service..."
ssh -p "$SERVER_PORT" "$SERVER_USER@$SERVER_HOST" bash <<EOF
cd $REMOTE_DIR

# Install Python and dependencies
sudo apt-get update
sudo apt-get install -y python3 python3-pip python3-venv

# Create virtual environment
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Create systemd service
sudo tee /etc/systemd/system/cuesync.service > /dev/null <<SERVICE
[Unit]
Description=CueSync Relay - Minimal Disposable Cue Relay
After=network.target

[Service]
Type=simple
User=$SERVER_USER
WorkingDirectory=$REMOTE_DIR
Environment="PATH=$REMOTE_DIR/venv/bin:/usr/bin"
Environment="CUESYNC_CONFIG=$REMOTE_DIR/config.yaml"
Environment="CUESYNC_PORT=$CUESYNC_PORT"
ExecStart=$REMOTE_DIR/venv/bin/python3 $REMOTE_DIR/relay.py
Restart=on-failure
RestartSec=10

[Install]
WantedBy=multi-user.target
SERVICE

# Reload systemd and restart service
sudo systemctl daemon-reload
sudo systemctl enable cuesync
sudo systemctl restart cuesync

# Show status
sudo systemctl status cuesync --no-pager
EOF

echo
echo "=== Deployment Complete ==="
echo "Relay endpoint: http://$SERVER_HOST:$CUESYNC_PORT/cuesheet"
echo "Health check: http://$SERVER_HOST:$CUESYNC_PORT/health"
echo
echo "View logs: ssh $SERVER_USER@$SERVER_HOST 'sudo journalctl -u cuesync -f'"
echo "Stop relay: ssh $SERVER_USER@$SERVER_HOST 'sudo systemctl stop cuesync'"
echo "Destroy relay: ssh $SERVER_USER@$SERVER_HOST 'sudo systemctl disable cuesync && sudo rm -rf $REMOTE_DIR'"
