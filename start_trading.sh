#!/bin/bash
# =============================================================================
# INSTITUTIONAL TRADING SYSTEM - AUTO LAUNCHER
# Lanzamiento automatizado con checks de seguridad
# =============================================================================

set -e  # Exit on error

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}"
echo "============================================================================="
echo "  INSTITUTIONAL TRADING SYSTEM - AUTO LAUNCHER"
echo "============================================================================="
echo -e "${NC}"

# =============================================================================
# PHASE 1: PRE-FLIGHT CHECKS
# =============================================================================

echo -e "${YELLOW}[1/5] Running pre-flight checks...${NC}"
python3 scripts/pre_flight_check.py
if [ $? -ne 0 ]; then
    echo -e "${RED}❌ Pre-flight checks FAILED. Fix errors before launching.${NC}"
    exit 1
fi
echo -e "${GREEN}✅ Pre-flight checks passed${NC}\n"

# =============================================================================
# PHASE 2: ENVIRONMENT SETUP
# =============================================================================

echo -e "${YELLOW}[2/5] Setting up environment...${NC}"

# Set Python path
export PYTHONPATH="/home/user/TradingSystem:/home/user/TradingSystem/src:$PYTHONPATH"

# Create necessary directories
mkdir -p logs
mkdir -p data/history
mkdir -p models/saved
mkdir -p checkpoints

echo -e "${GREEN}✅ Environment configured${NC}\n"

# =============================================================================
# PHASE 3: DATABASE CHECK
# =============================================================================

echo -e "${YELLOW}[3/5] Checking database connection...${NC}"

python3 << 'EOFPY'
import sys
try:
    import psycopg2
    conn = psycopg2.connect(
        host='localhost',
        port=5432,
        database='trading_system',
        user='trading_user',
        password='abc'
    )
    conn.close()
    print("✅ Database connection OK")
except Exception as e:
    print(f"❌ Database connection FAILED: {e}")
    sys.exit(1)
EOFPY

if [ $? -ne 0 ]; then
    echo -e "${RED}❌ Database not available${NC}"
    exit 1
fi
echo -e "${GREEN}✅ Database ready${NC}\n"

# =============================================================================
# PHASE 4: METATRADER 5 CHECK
# =============================================================================

echo -e "${YELLOW}[4/5] Checking MetaTrader 5...${NC}"

python3 << 'EOFPY'
import sys
try:
    import MetaTrader5 as mt5
    if not mt5.initialize():
        print(f"❌ MT5 initialization failed: {mt5.last_error()}")
        sys.exit(1)

    account_info = mt5.account_info()
    if account_info is None:
        print("❌ MT5 not logged in")
        sys.exit(1)

    print(f"✅ MT5 connected - Account: {account_info.login}, Balance: ${account_info.balance:.2f}")
    mt5.shutdown()
except Exception as e:
    print(f"❌ MT5 error: {e}")
    sys.exit(1)
EOFPY

if [ $? -ne 0 ]; then
    echo -e "${RED}❌ MetaTrader 5 not ready${NC}"
    exit 1
fi
echo -e "${GREEN}✅ MT5 ready${NC}\n"

# =============================================================================
# PHASE 5: LAUNCH TRADING ENGINE
# =============================================================================

echo -e "${YELLOW}[5/5] Launching trading engine...${NC}"
echo ""
echo -e "${GREEN}=========================================================================="
echo "  SISTEMA EN VIVO - Trading institucional activo"
echo "==========================================================================${NC}"
echo ""

# Launch with auto-restart on crash
while true; do
    python3 scripts/live_trading_engine_institutional.py 2>&1 | tee -a logs/trading_$(date +%Y%m%d).log

    EXIT_CODE=$?

    if [ $EXIT_CODE -eq 0 ]; then
        echo -e "${BLUE}Trading engine stopped gracefully${NC}"
        break
    else
        echo -e "${RED}Trading engine crashed with code $EXIT_CODE${NC}"
        echo -e "${YELLOW}Restarting in 10 seconds...${NC}"
        sleep 10
    fi
done

echo -e "${BLUE}Trading session ended${NC}"
