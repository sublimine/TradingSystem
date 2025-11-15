#!/usr/bin/env python3
"""
Monitor Live Trading - Monitoreo en tiempo real de LIVE trading

MANDATO 23: Live Execution & Kill Switch

Monitorea:
- Kill Switch status
- Account info (balance, equity, margin)
- Open positions
- Daily P&L
- Broker health

Usage:
    python scripts/monitor_live_trading.py

Author: SUBLIMINE Institutional Trading System
Date: 2025-11-14
"""

import sys
import os
import time
import argparse
from pathlib import Path
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

import MetaTrader5 as mt5
from src.mt5_connector import MT5Connector


class LiveTradingMonitor:
    """
    Monitor para LIVE trading.
    """

    def __init__(self, refresh_interval: int = 10):
        """
        Inicializa monitor.

        Args:
            refresh_interval: Intervalo de refresh en segundos
        """
        self.refresh_interval = refresh_interval
        self.connector = MT5Connector()
        self.initial_balance = None

    def run(self):
        """
        Ejecuta monitoreo continuo.
        """
        print("=" * 80)
        print("LIVE TRADING MONITOR - MANDATO 23")
        print("=" * 80)

        # Connect to MT5
        if not self.connector.connect():
            print("❌ Cannot connect to MT5")
            return

        # Get initial balance
        account_info = mt5.account_info()
        if account_info:
            self.initial_balance = account_info.balance

        print(f"Monitoring LIVE trading (refresh every {self.refresh_interval}s)")
        print("Press Ctrl+C to stop")
        print("")

        try:
            while True:
                self._display_status()
                time.sleep(self.refresh_interval)

        except KeyboardInterrupt:
            print("\nMonitoring stopped")
            self.connector.disconnect()

    def _display_status(self):
        """
        Muestra status actual.
        """
        os.system('clear' if os.name == 'posix' else 'cls')

        print("=" * 80)
        print(f"LIVE TRADING STATUS - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 80)

        # Account info
        self._display_account_info()

        print("")

        # Positions
        self._display_positions()

        print("")

        # Broker health
        self._display_broker_health()

        print("")
        print(f"Last updated: {datetime.now().strftime('%H:%M:%S')}")
        print(f"Next refresh in {self.refresh_interval}s (Ctrl+C to stop)")

    def _display_account_info(self):
        """
        Muestra info de cuenta.
        """
        account_info = mt5.account_info()

        if account_info is None:
            print("❌ Cannot get account info")
            return

        # Calculate daily P&L
        daily_pnl = account_info.balance - self.initial_balance if self.initial_balance else 0
        daily_pnl_pct = (daily_pnl / self.initial_balance * 100) if self.initial_balance else 0

        print("ACCOUNT INFO:")
        print(f"  Account:       {account_info.login}")
        print(f"  Server:        {account_info.server}")
        print(f"  Balance:       ${account_info.balance:,.2f}")
        print(f"  Equity:        ${account_info.equity:,.2f}")
        print(f"  Margin Used:   ${account_info.margin:,.2f}")
        print(f"  Margin Free:   ${account_info.margin_free:,.2f}")
        print(f"  Margin Level:  {account_info.margin_level:.2f}%")

        # Daily P&L
        pnl_color = "+" if daily_pnl >= 0 else "-"
        print(f"  Daily P&L:     {pnl_color}${abs(daily_pnl):,.2f} ({daily_pnl_pct:+.2f}%)")

        # Unrealized P&L
        unrealized_pnl = account_info.equity - account_info.balance
        print(f"  Unrealized:    ${unrealized_pnl:+,.2f}")

    def _display_positions(self):
        """
        Muestra posiciones abiertas.
        """
        positions = mt5.positions_get()

        if positions is None or len(positions) == 0:
            print("OPEN POSITIONS: None")
            return

        print(f"OPEN POSITIONS: {len(positions)}")

        for i, pos in enumerate(positions, 1):
            side = "BUY" if pos.type == mt5.ORDER_TYPE_BUY else "SELL"
            pnl_sign = "+" if pos.profit >= 0 else ""

            print(f"  [{i}] {pos.symbol} {side} {pos.volume} lots @ {pos.price_open:.5f}")
            print(f"      Current: {pos.price_current:.5f} | P&L: {pnl_sign}${pos.profit:.2f}")

            if pos.sl > 0:
                print(f"      SL: {pos.sl:.5f}", end="")
            if pos.tp > 0:
                print(f" | TP: {pos.tp:.5f}", end="")
            print("")

    def _display_broker_health(self):
        """
        Muestra estado del broker.
        """
        # Ping broker
        ping_start = time.time()
        tick = mt5.symbol_info_tick("EURUSD")
        ping_latency_ms = (time.time() - ping_start) * 1000

        if tick is None:
            print("BROKER HEALTH: ❌ UNHEALTHY (cannot get tick)")
            return

        health_status = "✅ HEALTHY" if ping_latency_ms < 500 else "⚠️ DEGRADED"

        print(f"BROKER HEALTH: {health_status}")
        print(f"  Latency:       {ping_latency_ms:.0f}ms")
        print(f"  Last Tick:     {datetime.fromtimestamp(tick.time).strftime('%H:%M:%S')}")
        print(f"  Connection:    ✅ CONNECTED" if self.connector.is_connected() else "❌ DISCONNECTED")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='Monitor LIVE trading'
    )

    parser.add_argument(
        '--refresh',
        type=int,
        default=10,
        help='Refresh interval in seconds (default: 10)'
    )

    args = parser.parse_args()

    monitor = LiveTradingMonitor(refresh_interval=args.refresh)

    try:
        monitor.run()
    except Exception as e:
        print(f"FATAL ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
