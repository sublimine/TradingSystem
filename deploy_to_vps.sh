#!/bin/bash

#############################################################################
# ELITE TRADING SYSTEM - VPS DEPLOYMENT SCRIPT
#
# This script automates the complete deployment of the trading system to VPS.
# NO MANUAL FILE COPYING REQUIRED.
#
# Usage:
#   1. On your VPS, run:
#      bash <(curl -s https://raw.githubusercontent.com/YOUR_REPO/deploy_to_vps.sh)
#
#   2. Or download and run:
#      wget https://raw.githubusercontent.com/YOUR_REPO/deploy_to_vps.sh
#      chmod +x deploy_to_vps.sh
#      ./deploy_to_vps.sh
#
# Author: Elite Trading System
# Version: 1.0
#############################################################################

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
REPO_URL="https://github.com/YOUR_USERNAME/TradingSystem.git"  # UPDATE THIS
INSTALL_DIR="$HOME/TradingSystem"
PYTHON_VERSION="3.8"

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}ELITE TRADING SYSTEM - VPS DEPLOYMENT${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""

# Step 1: Check if running on Linux
if [[ "$OSTYPE" != "linux-gnu"* ]]; then
    echo -e "${RED}ERROR: This script is designed for Linux VPS${NC}"
    echo "Detected OS: $OSTYPE"
    exit 1
fi

echo -e "${GREEN}✓${NC} OS check passed (Linux)"

# Step 2: Check Python version
echo ""
echo "Checking Python installation..."

if command -v python3 &> /dev/null; then
    PYTHON_CMD="python3"
    PYTHON_INSTALLED_VERSION=$(python3 --version | awk '{print $2}')
    echo -e "${GREEN}✓${NC} Python3 found: $PYTHON_INSTALLED_VERSION"
else
    echo -e "${RED}✗${NC} Python3 not found"
    echo "Installing Python3..."
    sudo apt-get update
    sudo apt-get install -y python3 python3-pip python3-venv
    PYTHON_CMD="python3"
fi

# Step 3: Check git
echo ""
echo "Checking git installation..."

if ! command -v git &> /dev/null; then
    echo -e "${RED}✗${NC} Git not found"
    echo "Installing git..."
    sudo apt-get install -y git
fi

echo -e "${GREEN}✓${NC} Git installed"

# Step 4: Clone or update repository
echo ""
echo "Setting up trading system..."

if [ -d "$INSTALL_DIR" ]; then
    echo -e "${YELLOW}⚠${NC}  Directory exists: $INSTALL_DIR"
    read -p "Do you want to update (pull latest) or reinstall (delete and clone)? [update/reinstall]: " choice

    if [ "$choice" == "reinstall" ]; then
        echo "Removing old installation..."
        rm -rf "$INSTALL_DIR"
        echo "Cloning repository..."
        git clone "$REPO_URL" "$INSTALL_DIR"
    else
        echo "Pulling latest changes..."
        cd "$INSTALL_DIR"
        git pull
    fi
else
    echo "Cloning repository..."
    git clone "$REPO_URL" "$INSTALL_DIR"
fi

cd "$INSTALL_DIR"
echo -e "${GREEN}✓${NC} Repository ready: $INSTALL_DIR"

# Step 5: Create virtual environment
echo ""
echo "Creating Python virtual environment..."

if [ ! -d "venv" ]; then
    $PYTHON_CMD -m venv venv
    echo -e "${GREEN}✓${NC} Virtual environment created"
else
    echo -e "${GREEN}✓${NC} Virtual environment exists"
fi

# Activate virtual environment
source venv/bin/activate

# Step 6: Install dependencies
echo ""
echo "Installing Python dependencies..."

if [ -f "requirements.txt" ]; then
    pip install --upgrade pip
    pip install -r requirements.txt
    echo -e "${GREEN}✓${NC} Dependencies installed"
else
    echo -e "${YELLOW}⚠${NC}  requirements.txt not found, installing core packages..."
    pip install --upgrade pip
    pip install pandas numpy scipy scikit-learn PyYAML MetaTrader5
fi

# Step 7: Create necessary directories
echo ""
echo "Creating output directories..."

mkdir -p logs
mkdir -p reports
mkdir -p backtest_reports
mkdir -p ml_data
mkdir -p trade_history
mkdir -p config

echo -e "${GREEN}✓${NC} Directories created"

# Step 8: Check MetaTrader 5 installation
echo ""
echo "Checking MetaTrader 5..."

if command -v wine &> /dev/null; then
    echo -e "${GREEN}✓${NC} Wine installed (for MT5 on Linux)"
else
    echo -e "${YELLOW}⚠${NC}  Wine not found (required for MT5 on Linux)"
    echo "Installing Wine..."
    sudo dpkg --add-architecture i386
    sudo apt-get update
    sudo apt-get install -y wine wine32 wine64
fi

# Step 9: Set up systemd service (optional)
echo ""
read -p "Do you want to set up the system as a systemd service (auto-start on boot)? [y/n]: " setup_service

if [ "$setup_service" == "y" ]; then
    echo "Creating systemd service..."

    SERVICE_FILE="/etc/systemd/system/elite-trading.service"

    sudo bash -c "cat > $SERVICE_FILE" <<EOF
[Unit]
Description=Elite Trading System
After=network.target

[Service]
Type=simple
User=$USER
WorkingDirectory=$INSTALL_DIR
ExecStart=$INSTALL_DIR/venv/bin/python $INSTALL_DIR/main.py --mode paper
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

    sudo systemctl daemon-reload
    sudo systemctl enable elite-trading.service

    echo -e "${GREEN}✓${NC} Systemd service created"
    echo "  Start: sudo systemctl start elite-trading"
    echo "  Stop:  sudo systemctl stop elite-trading"
    echo "  Logs:  sudo journalctl -u elite-trading -f"
fi

# Step 10: Configuration check
echo ""
echo "Checking configuration..."

if [ ! -f "config/system_config.yaml" ]; then
    echo -e "${YELLOW}⚠${NC}  system_config.yaml not found"
    echo "Please ensure config files are in the repository"
fi

if [ ! -f "config/strategies_institutional.yaml" ]; then
    echo -e "${YELLOW}⚠${NC}  strategies_institutional.yaml not found"
    echo "Please ensure config files are in the repository"
fi

# Step 11: Run verification
echo ""
echo "Running system verification..."

$PYTHON_CMD -c "
import sys
try:
    import pandas
    import numpy
    import scipy
    import sklearn
    import yaml
    print('✓ All core dependencies imported successfully')
except ImportError as e:
    print(f'✗ Import error: {e}')
    sys.exit(1)
"

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓${NC} System verification passed"
else
    echo -e "${RED}✗${NC} System verification failed"
    exit 1
fi

# Step 12: Final instructions
echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}DEPLOYMENT COMPLETE!${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo "Installation directory: $INSTALL_DIR"
echo ""
echo "Next steps:"
echo ""
echo "1. Configure MT5 login credentials:"
echo "   Edit: config/mt5_credentials.yaml"
echo ""
echo "2. Review system configuration:"
echo "   Edit: config/system_config.yaml"
echo ""
echo "3. Run backtesting (REQUIRED before live):"
echo "   cd $INSTALL_DIR"
echo "   source venv/bin/activate"
echo "   python main.py --mode backtest --days 90"
echo ""
echo "4. Start paper trading:"
echo "   python main.py --mode paper"
echo ""
echo "5. Monitor logs:"
echo "   tail -f logs/trading_system.log"
echo ""
echo "If you set up systemd service:"
echo "   sudo systemctl start elite-trading"
echo "   sudo journalctl -u elite-trading -f"
echo ""
echo -e "${YELLOW}IMPORTANT:${NC} Always backtest before live trading!"
echo ""
