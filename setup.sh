#!/bin/bash
# Cuesync One-Time Setup Script
# Run this once on a fresh server

set -e

echo "🔧 Cuesync Setup - Maestro Deployment Node"
echo "=========================================="
echo ""

# Check if already set up
if [ -d "maestro/.git" ]; then
    echo "⚠️  Maestro already cloned. Run ./sync.sh to update."
    exit 0
fi

# Install dependencies
echo "1️⃣  Installing dependencies..."
sudo apt update
sudo apt install -y python3 python3-venv git curl
echo "✅ Dependencies installed"
echo ""

# Clone maestro repo as submodule
echo "2️⃣  Cloning maestro repository..."
git submodule add https://github.com/nickcottrell/maestro.git maestro 2>/dev/null || git submodule update --init --recursive
echo "✅ Maestro cloned"
echo ""

# Set up Python environment
echo "3️⃣  Setting up Python environment..."
cd maestro
python3 -m venv .venv
source .venv/bin/activate
pip install --quiet pyyaml
cd ..
echo "✅ Python environment ready"
echo ""

# Configure secrets
echo "4️⃣  Configuring secrets..."
if [ ! -f ".env" ]; then
    cp .env.example .env
    echo "📝 Created .env file"
    echo ""
    echo "⚠️  IMPORTANT: Edit .env with your credentials:"
    echo "   nano .env"
    echo ""
    read -p "Press Enter to edit .env now (or Ctrl+C to skip)..."
    nano .env
else
    echo "✅ .env already exists"
fi
echo ""

# Create logs directory
echo "5️⃣  Creating logs directory..."
mkdir -p logs
echo "✅ Logs directory created"
echo ""

# Generate initial cron jobs
echo "6️⃣  Generating cron jobs from schedule.yaml..."
./sync.sh
echo ""

echo "=========================================="
echo "✅ Setup complete!"
echo ""
echo "📋 Next steps:"
echo "  1. Verify .env has your API credentials"
echo "  2. Check cron jobs: crontab -l"
echo "  3. Wait for scheduled execution or test manually:"
echo "     cd maestro && ./hooks run morning-workflow"
echo ""
echo "🔄 Auto-sync enabled: Server pulls updates every 5 minutes"
echo ""
