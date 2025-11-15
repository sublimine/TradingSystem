#!/usr/bin/env python3
"""
Export Metrics Snapshot - MANDATO 26

CLI tool to generate JSON snapshot of system metrics.

Usage:
    python scripts/export_metrics_snapshot.py
    python scripts/export_metrics_snapshot.py --output /path/to/snapshot.json
    python scripts/export_metrics_snapshot.py --mode LIVE --capital 50000

Author: SUBLIMINE SRE Team
Date: 2025-11-15
Mandate: M26 - Production Hardening
"""

import sys
import argparse
import json
import logging
from pathlib import Path
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.monitoring import MetricsExporter

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


def generate_demo_snapshot(capital: float, mode: str) -> dict:
    """
    Generate demo snapshot (no live data).

    Used when system is not running - creates snapshot with sample data
    for testing monitoring dashboards/alerts.

    Args:
        capital: Capital amount
        mode: Trading mode

    Returns:
        Metrics snapshot dict
    """
    logger.warning("Generating DEMO snapshot (system not running)")

    exporter = MetricsExporter(capital=capital)

    # Demo data
    kill_switch_status = {
        'state': 'ACTIVE',
        'reason': None,
        'blocked_since': None,
        'total_blocks': 0
    }

    snapshot = exporter.export_snapshot(
        kill_switch_status=kill_switch_status,
        position_manager=None,  # No live data
        trade_history=None,
        signal_history=None,
        microstructure_engine=None,
        mode=mode
    )

    # Add demo marker
    snapshot['demo_mode'] = True
    snapshot['note'] = 'Demo snapshot - system not running'

    return snapshot


def generate_live_snapshot(capital: float, mode: str) -> dict:
    """
    Generate snapshot from live system data.

    Args:
        capital: Capital amount
        mode: Trading mode

    Returns:
        Metrics snapshot dict
    """
    logger.info("Generating LIVE snapshot (connecting to system)")

    exporter = MetricsExporter(capital=capital)

    # TODO: Connect to actual running system and collect metrics
    # For now, return demo snapshot
    logger.warning("Live snapshot not yet implemented - using demo")
    return generate_demo_snapshot(capital, mode)


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='Export system metrics snapshot to JSON'
    )

    parser.add_argument(
        '--output',
        type=str,
        help='Output filepath (default: reports/health/metrics_snapshot_<timestamp>.json)'
    )

    parser.add_argument(
        '--mode',
        type=str,
        default='UNKNOWN',
        choices=['RESEARCH', 'PAPER', 'LIVE', 'UNKNOWN'],
        help='Trading mode (default: UNKNOWN)'
    )

    parser.add_argument(
        '--capital',
        type=float,
        default=10000.0,
        help='System capital for % calculations (default: 10000)'
    )

    parser.add_argument(
        '--demo',
        action='store_true',
        help='Generate demo snapshot (no live data)'
    )

    args = parser.parse_args()

    logger.info("=" * 80)
    logger.info("METRICS SNAPSHOT EXPORT - MANDATO 26")
    logger.info("=" * 80)
    logger.info(f"Mode: {args.mode}")
    logger.info(f"Capital: ${args.capital:,.2f}")
    logger.info(f"Demo: {args.demo}")
    logger.info("=" * 80)
    logger.info("")

    try:
        # Generate snapshot
        if args.demo:
            snapshot = generate_demo_snapshot(args.capital, args.mode)
        else:
            snapshot = generate_live_snapshot(args.capital, args.mode)

        # Save to file
        exporter = MetricsExporter(capital=args.capital)

        if args.output:
            filepath = Path(args.output)
        else:
            filepath = None  # Use default

        saved_path = exporter.save_snapshot(snapshot, filepath)

        # Print summary
        logger.info("")
        logger.info("=" * 80)
        logger.info("SNAPSHOT SUMMARY")
        logger.info("=" * 80)
        logger.info(f"Timestamp: {snapshot['timestamp']}")
        logger.info(f"Mode: {snapshot['mode']}")
        logger.info(f"Uptime: {snapshot['uptime_seconds']:.1f}s")
        logger.info("")
        logger.info("Kill Switch:")
        logger.info(f"  State: {snapshot['kill_switch']['state']}")
        logger.info(f"  Total Blocks: {snapshot['kill_switch']['total_blocks']}")
        logger.info("")
        logger.info("Positions:")
        logger.info(f"  Open: {snapshot['positions']['open_positions']}")
        logger.info(f"  Total Exposure: {snapshot['positions']['total_exposure_pct']:.1f}%")
        logger.info("")
        logger.info("P&L:")
        logger.info(f"  Daily: ${snapshot['pnl']['daily_pnl']:.2f} ({snapshot['pnl']['daily_pnl_pct']:.2f}%)")
        logger.info(f"  Drawdown: ${snapshot['pnl']['current_drawdown']:.2f}")
        logger.info(f"  Trades Today: {snapshot['pnl']['total_trades_today']}")
        logger.info("")
        logger.info("Signals:")
        logger.info(f"  Generated: {snapshot['signals']['signals_generated']}")
        logger.info(f"  Rejected: {snapshot['signals']['signals_rejected']} ({snapshot['signals']['reject_rate_pct']:.1f}%)")
        logger.info(f"  Avg Quality: {snapshot['signals']['avg_signal_quality']:.2f}")
        logger.info("")
        logger.info("Microstructure:")
        logger.info(f"  Symbols: {len(snapshot['microstructure']['symbols'])}")
        logger.info(f"  Avg VPIN: {snapshot['microstructure']['avg_vpin']:.3f}")
        logger.info(f"  Extreme VPIN: {snapshot['microstructure']['extreme_vpin_count']}")
        logger.info("")

        if snapshot['alerts']:
            logger.warning("=" * 80)
            logger.warning("⚠️  ACTIVE ALERTS")
            logger.warning("=" * 80)
            for alert in snapshot['alerts']:
                logger.warning(f"  {alert}")
            logger.warning("=" * 80)
            logger.warning("")

        logger.info(f"Snapshot saved: {saved_path}")
        logger.info("=" * 80)

        # Exit code 0 = success
        sys.exit(0)

    except Exception as e:
        logger.error("")
        logger.error("=" * 80)
        logger.error(f"❌ Snapshot export failed: {e}")
        logger.error("=" * 80)
        import traceback
        traceback.print_exc()

        # Exit code 1 = failure
        sys.exit(1)


if __name__ == '__main__':
    main()
