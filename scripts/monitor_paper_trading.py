#!/usr/bin/env python3
"""
Monitor Paper Trading - MANDATO 21

Monitors active paper trading session.

Checks:
- Log file activity (last update time)
- Recent trades (from logs)
- System health indicators

Usage:
    python scripts/monitor_paper_trading.py

Author: SUBLIMINE Institutional Trading System
Date: 2025-11-14
Mandato: MANDATO 21 - Paper Trading Institucional
"""

import sys
import os
from pathlib import Path
from datetime import datetime, timedelta
import re

# Colors for terminal output
class Colors:
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BLUE = '\033[94m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'


def find_latest_log(log_dir: str = 'logs') -> Path:
    """Find latest paper trading log file."""
    log_path = Path(log_dir)

    if not log_path.exists():
        return None

    # Find paper_trading_*.log files
    paper_logs = list(log_path.glob('paper_trading_*.log'))

    if not paper_logs:
        # Fallback to trading_system.log
        system_log = log_path / 'trading_system.log'
        if system_log.exists():
            return system_log
        return None

    # Return most recent
    return max(paper_logs, key=lambda p: p.stat().st_mtime)


def check_log_activity(log_file: Path) -> dict:
    """Check if log file has recent activity."""
    if not log_file or not log_file.exists():
        return {
            'status': 'ERROR',
            'message': 'Log file not found'
        }

    # Get last modification time
    last_mod = datetime.fromtimestamp(log_file.stat().st_mtime)
    age = datetime.now() - last_mod

    # Read last few lines
    try:
        with open(log_file, 'r') as f:
            lines = f.readlines()
            last_lines = lines[-10:] if len(lines) >= 10 else lines
    except Exception as e:
        return {
            'status': 'ERROR',
            'message': f'Cannot read log: {e}'
        }

    # Check for recent activity
    if age < timedelta(minutes=5):
        status = 'ACTIVE'
    elif age < timedelta(minutes=30):
        status = 'IDLE'
    else:
        status = 'STALE'

    # Check for errors in last lines
    has_errors = any('ERROR' in line or 'CRITICAL' in line for line in last_lines)

    return {
        'status': status,
        'last_update': last_mod.strftime('%Y-%m-%d %H:%M:%S'),
        'age_minutes': int(age.total_seconds() / 60),
        'has_errors': has_errors,
        'last_lines': last_lines
    }


def parse_recent_trades(log_file: Path, minutes: int = 60) -> list:
    """Parse recent trades from log."""
    if not log_file or not log_file.exists():
        return []

    trades = []

    try:
        with open(log_file, 'r') as f:
            for line in f:
                # Look for paper trade fills
                if 'PAPER FILL' in line or 'PAPER ORDER' in line:
                    trades.append(line.strip())

        # Return last N trades
        return trades[-10:]

    except Exception as e:
        print(f"{Colors.RED}Error parsing trades: {e}{Colors.ENDC}")
        return []


def main():
    """Monitor paper trading session."""
    print(f"{Colors.BOLD}=" * 80)
    print("MANDATO 21 - PAPER TRADING MONITOR")
    print("=" * 80 + Colors.ENDC)
    print(f"Check time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("")

    # Find latest log
    log_file = find_latest_log()

    if not log_file:
        print(f"{Colors.RED}❌ No paper trading logs found{Colors.ENDC}")
        print(f"{Colors.YELLOW}⚠️  Paper trading may not be running{Colors.ENDC}")
        sys.exit(1)

    print(f"{Colors.BLUE}📄 Log file: {log_file}{Colors.ENDC}")
    print("")

    # Check activity
    activity = check_log_activity(log_file)

    print(f"{Colors.BOLD}System Status:{Colors.ENDC}")
    print("─" * 80)

    status = activity['status']
    if status == 'ACTIVE':
        color = Colors.GREEN
        symbol = "✅"
    elif status == 'IDLE':
        color = Colors.YELLOW
        symbol = "⏸️ "
    else:
        color = Colors.RED
        symbol = "❌"

    print(f"  Status: {color}{symbol} {status}{Colors.ENDC}")
    print(f"  Last update: {activity.get('last_update', 'Unknown')}")
    print(f"  Age: {activity.get('age_minutes', 0)} minutes")

    if activity.get('has_errors'):
        print(f"  {Colors.RED}⚠️  Errors detected in recent logs{Colors.ENDC}")

    print("")

    # Recent trades
    trades = parse_recent_trades(log_file, minutes=60)

    print(f"{Colors.BOLD}Recent Activity:{Colors.ENDC}")
    print("─" * 80)

    if trades:
        print(f"  Found {len(trades)} recent trades/orders:")
        for trade in trades[-5:]:  # Show last 5
            # Extract key info
            if 'FILL' in trade:
                print(f"  {Colors.GREEN}✓ {trade[-100:]}{Colors.ENDC}")
            else:
                print(f"  {Colors.BLUE}→ {trade[-100:]}{Colors.ENDC}")
    else:
        print(f"  {Colors.YELLOW}No recent trades found{Colors.ENDC}")

    print("")

    # Last log lines
    print(f"{Colors.BOLD}Last Log Entries:{Colors.ENDC}")
    print("─" * 80)

    last_lines = activity.get('last_lines', [])
    for line in last_lines[-5:]:
        # Color code by level
        if 'ERROR' in line or 'CRITICAL' in line:
            color = Colors.RED
        elif 'WARNING' in line:
            color = Colors.YELLOW
        elif 'INFO' in line:
            color = Colors.BLUE
        else:
            color = ''

        print(f"  {color}{line.strip()[-120:]}{Colors.ENDC}")

    print("")
    print(f"{Colors.BOLD}=" * 80 + Colors.ENDC)

    # Exit code based on status
    if status == 'ACTIVE':
        sys.exit(0)
    elif status == 'IDLE':
        sys.exit(0)  # Still OK
    else:
        sys.exit(1)  # Stale or error


if __name__ == "__main__":
    main()
