#!/usr/bin/env python3
"""
Start Paper Trading - MANDATO 21

Launches trading system in PAPER mode with institutional config.

Usage:
    python scripts/start_paper_trading.py [--config PATH]

Features:
- Loads runtime_profile_paper.yaml
- Initializes system in PAPER mode
- Confirms NO real orders will be sent
- Logs startup diagnostics

Author: SUBLIMINE Institutional Trading System
Date: 2025-11-14
Mandato: MANDATO 21 - Paper Trading Institucional
"""

import argparse
import logging
import sys
from pathlib import Path
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Import main system
from main import EliteTradingSystem

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(f'logs/paper_trading_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log'),
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)


def main():
    """Start paper trading session."""
    parser = argparse.ArgumentParser(
        description='Start Paper Trading Mode - MANDATO 21'
    )

    parser.add_argument(
        '--config',
        type=str,
        default='config/runtime_profile_paper.yaml',
        help='Runtime profile config (default: runtime_profile_paper.yaml)'
    )

    parser.add_argument(
        '--no-ml',
        action='store_true',
        help='Disable ML adaptive engine'
    )

    args = parser.parse_args()

    # Banner
    logger.info("=" * 80)
    logger.info("MANDATO 21 - PAPER TRADING MODE")
    logger.info("=" * 80)
    logger.info(f"Config: {args.config}")
    logger.info(f"ML Enabled: {not args.no_ml}")
    logger.info(f"Start Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info("=" * 80)

    # Confirm paper mode
    logger.warning("")
    logger.warning("⚠️  PAPER TRADING MODE ⚠️")
    logger.warning("")
    logger.warning("This mode uses SIMULATED execution:")
    logger.warning("  - NO real broker orders will be sent")
    logger.warning("  - Virtual positions and balance only")
    logger.warning("  - All trades are for testing purposes")
    logger.warning("")
    logger.warning("Risk management (0-2% caps) is ACTIVE")
    logger.warning("Institutional reporting is ACTIVE (tagged as PAPER)")
    logger.warning("")
    logger.info("=" * 80)

    # Initialize system in PAPER mode
    try:
        logger.info("Initializing trading system in PAPER mode...")

        system = EliteTradingSystem(
            config_path=args.config,
            auto_ml=not args.no_ml,
            execution_mode='paper'  # Force PAPER mode
        )

        logger.info("✅ System initialized successfully")
        logger.info("")
        logger.info("Starting paper trading loop...")
        logger.info("Press Ctrl+C to stop gracefully")
        logger.info("=" * 80)

        # Run paper trading
        system.run_paper_trading()

    except KeyboardInterrupt:
        logger.info("")
        logger.info("=" * 80)
        logger.info("⚠️  SHUTDOWN REQUESTED BY USER")
        logger.info("=" * 80)
        sys.exit(0)

    except Exception as e:
        logger.error("=" * 80)
        logger.error(f"❌ CRITICAL ERROR: {e}")
        logger.error("=" * 80)
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
