#!/bin/bash
# =============================================================================
# MONITOR - Real-time trading system monitoring
# =============================================================================

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m'

while true; do
    clear
    echo -e "${BLUE}=========================================================================="
    echo "  INSTITUTIONAL TRADING SYSTEM - LIVE MONITOR"
    echo "==========================================================================${NC}"
    echo ""

    # Show latest log entries
    echo -e "${YELLOW}📊 LATEST ACTIVITY:${NC}"
    tail -20 logs/trading_$(date +%Y%m%d).log | grep -E "(SIGNAL|TRADE|ERROR|WARNING)" || echo "No recent activity"

    echo ""
    echo -e "${YELLOW}💰 SYSTEM STATUS:${NC}"

    # Check if engine is running
    if pgrep -f "live_trading_engine" > /dev/null; then
        echo -e "${GREEN}✅ Trading engine: RUNNING${NC}"
    else
        echo -e "${RED}❌ Trading engine: STOPPED${NC}"
    fi

    # Check database
    if pg_isready -h localhost -p 5432 > /dev/null 2>&1; then
        echo -e "${GREEN}✅ Database: ONLINE${NC}"
    else
        echo -e "${RED}❌ Database: OFFLINE${NC}"
    fi

    # Memory usage
    MEM=$(free -m | awk 'NR==2{printf "%.0f%%", $3*100/$2 }')
    echo -e "${BLUE}💾 Memory usage: $MEM${NC}"

    # Disk space
    DISK=$(df -h / | awk 'NR==2{print $5}')
    echo -e "${BLUE}💿 Disk usage: $DISK${NC}"

    echo ""
    echo -e "${YELLOW}Press Ctrl+C to exit${NC}"
    echo ""

    sleep 5
done
