#!/usr/bin/env python3
"""
Emergency Stop - Activación manual del Kill Switch

MANDATO 23: Live Execution & Kill Switch

Activa el Kill Switch para BLOQUEAR TODAS las órdenes nuevas.
NO cierra posiciones existentes automáticamente.

Usage:
    python scripts/emergency_stop_live.py --reason "Market volatility extreme"

Author: SUBLIMINE Institutional Trading System
Date: 2025-11-14
"""

import sys
import os
import argparse
import yaml
from pathlib import Path
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))


class EmergencyStop:
    """
    Emergency stop handler.
    """

    def __init__(self, reason: str):
        """
        Inicializa emergency stop.

        Args:
            reason: Razón del emergency stop
        """
        self.reason = reason

    def execute(self):
        """
        Ejecuta emergency stop.
        """
        print("=" * 80)
        print("🚨🚨🚨  EMERGENCY STOP  🚨🚨🚨")
        print("=" * 80)

        print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Reason: {self.reason}")
        print("")

        # Confirm
        print("This will BLOCK ALL NEW ORDERS.")
        print("Existing positions will NOT be closed automatically.")
        print("")

        confirm = input("Type 'EMERGENCY' to confirm: ")

        if confirm != 'EMERGENCY':
            print("Emergency stop cancelled")
            return False

        # Disable live trading in config
        self._disable_live_trading_in_config()

        # Log event
        self._log_emergency_event()

        print("")
        print("=" * 80)
        print("✅ EMERGENCY STOP ACTIVATED")
        print("=" * 80)
        print("")
        print("Next steps:")
        print("1. All NEW orders are now BLOCKED")
        print("2. Existing positions remain OPEN with their SL/TP")
        print("3. Review positions manually")
        print("4. Close positions manually if needed")
        print("5. To re-enable, edit config/live_trading_config.yaml")
        print("")

        return True

    def _disable_live_trading_in_config(self):
        """
        Desactiva LIVE trading en config.
        """
        config_path = 'config/live_trading_config.yaml'

        try:
            # Read config
            with open(config_path, 'r') as f:
                config = yaml.safe_load(f)

            # Disable
            if 'live_trading' not in config:
                config['live_trading'] = {}

            config['live_trading']['enabled'] = False

            # Write back
            with open(config_path, 'w') as f:
                yaml.dump(config, f, default_flow_style=False)

            print(f"✓ Live trading disabled in {config_path}")

        except Exception as e:
            print(f"⚠️  Could not update config: {e}")
            print("⚠️  Please manually set 'live_trading.enabled: false'")

    def _log_emergency_event(self):
        """
        Log emergency event.
        """
        log_file = 'logs/emergency_events.log'

        # Create logs directory if not exists
        os.makedirs('logs', exist_ok=True)

        with open(log_file, 'a') as f:
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            f.write(f"{timestamp} - EMERGENCY STOP - {self.reason}\n")

        print(f"✓ Event logged to {log_file}")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='Emergency stop - Block all new LIVE orders'
    )

    parser.add_argument(
        '--reason',
        type=str,
        required=True,
        help='Reason for emergency stop'
    )

    args = parser.parse_args()

    emergency_stop = EmergencyStop(reason=args.reason)

    try:
        emergency_stop.execute()
    except Exception as e:
        print(f"FATAL ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
