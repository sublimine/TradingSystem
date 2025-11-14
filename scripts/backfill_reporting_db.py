#!/usr/bin/env python3
"""
Backfill Historical Data - Institutional Reporting System

Popula database con datos históricos de trades desde:
- JSONL logs (reports/raw/*.jsonl)
- MT5 history (via MetaTrader5.history_deals_get())
- CSV exports (custom format)

Mandato: MANDATO 12 - FASE 2
Fecha: 2025-11-14

Uso:
    # Backfill desde JSONL
    python scripts/backfill_reporting_db.py --source jsonl --start-date 2025-01-01

    # Backfill desde MT5 (últimos 90 días)
    python scripts/backfill_reporting_db.py --source mt5 --days 90

    # Backfill desde CSV
    python scripts/backfill_reporting_db.py --source csv --file data/trades_history.csv
"""

import sys
import os
from pathlib import Path
from datetime import datetime, timedelta
import logging
import json
import argparse
from typing import List, Dict, Optional

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.reporting.db import ReportingDatabase

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class BackfillReportingDB:
    """Backfill historical data into reporting database."""

    def __init__(self, config_path: str = 'config/reporting_db.yaml'):
        """
        Args:
            config_path: Path to reporting DB config
        """
        self.db = ReportingDatabase(config_path)
        self.stats = {
            'total_processed': 0,
            'total_inserted': 0,
            'total_skipped': 0,
            'total_errors': 0
        }

    def backfill_from_jsonl(self, jsonl_dir: str = 'reports/raw',
                           start_date: Optional[datetime] = None,
                           end_date: Optional[datetime] = None):
        """
        Backfill desde archivos JSONL.

        Args:
            jsonl_dir: Directorio con archivos .jsonl
            start_date: Fecha inicio (inclusive)
            end_date: Fecha fin (inclusive)
        """
        logger.info(f"Backfilling from JSONL files in: {jsonl_dir}")

        jsonl_path = Path(jsonl_dir)
        if not jsonl_path.exists():
            logger.warning(f"Directory not found: {jsonl_dir}")
            return

        # Find all .jsonl files
        jsonl_files = list(jsonl_path.glob('*.jsonl'))

        if not jsonl_files:
            logger.warning(f"No .jsonl files found in {jsonl_dir}")
            return

        logger.info(f"Found {len(jsonl_files)} JSONL files")

        for jsonl_file in jsonl_files:
            logger.info(f"Processing: {jsonl_file.name}")

            try:
                with open(jsonl_file, 'r') as f:
                    events = []

                    for line_num, line in enumerate(f, 1):
                        try:
                            event = json.loads(line.strip())

                            # Filter by date if specified
                            if start_date or end_date:
                                event_time = self._parse_timestamp(event.get('timestamp'))
                                if event_time:
                                    if start_date and event_time < start_date:
                                        continue
                                    if end_date and event_time > end_date:
                                        continue

                            # Convert timestamp strings to datetime objects
                            event = self._normalize_event(event)

                            events.append(event)
                            self.stats['total_processed'] += 1

                            # Batch insert every 100 events
                            if len(events) >= 100:
                                self._insert_events_batch(events)
                                events = []

                        except json.JSONDecodeError as e:
                            logger.error(f"  Line {line_num}: JSON decode error: {e}")
                            self.stats['total_errors'] += 1
                        except Exception as e:
                            logger.error(f"  Line {line_num}: Error processing event: {e}")
                            self.stats['total_errors'] += 1

                    # Insert remaining events
                    if events:
                        self._insert_events_batch(events)

                logger.info(f"  ✓ Processed {jsonl_file.name}")

            except Exception as e:
                logger.error(f"  ✗ Error reading {jsonl_file.name}: {e}")
                self.stats['total_errors'] += 1

    def backfill_from_mt5(self, days: int = 90):
        """
        Backfill desde historial de MT5.

        Args:
            days: Número de días hacia atrás
        """
        logger.info(f"Backfilling from MT5 history (last {days} days)")

        try:
            import MetaTrader5 as mt5

            # Initialize MT5
            if not mt5.initialize():
                logger.error("MT5 initialization failed")
                return

            # Get deals from last N days
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days)

            logger.info(f"Fetching deals from {start_date.date()} to {end_date.date()}")

            deals = mt5.history_deals_get(start_date, end_date)

            if deals is None or len(deals) == 0:
                logger.warning("No deals found in MT5 history")
                mt5.shutdown()
                return

            logger.info(f"Found {len(deals)} deals in MT5 history")

            # Convert MT5 deals to trade events
            events = []

            for deal in deals:
                try:
                    # Convert MT5 deal to event format
                    event = self._mt5_deal_to_event(deal)

                    if event:
                        events.append(event)
                        self.stats['total_processed'] += 1

                        # Batch insert every 100 events
                        if len(events) >= 100:
                            self._insert_events_batch(events)
                            events = []

                except Exception as e:
                    logger.error(f"Error converting MT5 deal: {e}")
                    self.stats['total_errors'] += 1

            # Insert remaining events
            if events:
                self._insert_events_batch(events)

            mt5.shutdown()
            logger.info("✓ MT5 backfill complete")

        except ImportError:
            logger.error("MetaTrader5 module not available. Install with: pip install MetaTrader5")
        except Exception as e:
            logger.error(f"MT5 backfill failed: {e}")

    def backfill_from_csv(self, csv_file: str):
        """
        Backfill desde archivo CSV.

        Args:
            csv_file: Path al CSV
        """
        logger.info(f"Backfilling from CSV: {csv_file}")

        try:
            import pandas as pd

            df = pd.read_csv(csv_file)
            logger.info(f"Loaded {len(df)} rows from CSV")

            # TODO: Implement CSV parsing logic based on actual CSV format
            logger.warning("CSV backfill not fully implemented - requires custom CSV format definition")

        except Exception as e:
            logger.error(f"CSV backfill failed: {e}")

    def _insert_events_batch(self, events: List[Dict]) -> bool:
        """
        Insert batch of events to DB.

        Args:
            events: List of event dictionaries

        Returns:
            True if successful
        """
        try:
            success = self.db.insert_trade_events(events)

            if success:
                self.stats['total_inserted'] += len(events)
                logger.debug(f"  Inserted batch of {len(events)} events")
            else:
                self.stats['total_skipped'] += len(events)
                logger.warning(f"  Skipped batch of {len(events)} events (fallback mode)")

            return success

        except Exception as e:
            logger.error(f"Batch insert failed: {e}")
            self.stats['total_errors'] += len(events)
            return False

    def _normalize_event(self, event: Dict) -> Dict:
        """
        Normalize event data (convert timestamps, etc).

        Args:
            event: Raw event dictionary

        Returns:
            Normalized event
        """
        # Convert timestamp string to datetime if needed
        if 'timestamp' in event and isinstance(event['timestamp'], str):
            event['timestamp'] = self._parse_timestamp(event['timestamp'])

        return event

    def _parse_timestamp(self, ts_str: str) -> Optional[datetime]:
        """Parse timestamp string to datetime."""
        if not ts_str:
            return None

        try:
            # Try ISO format first
            return datetime.fromisoformat(ts_str.replace('Z', '+00:00'))
        except:
            try:
                # Try common formats
                return datetime.strptime(ts_str, '%Y-%m-%d %H:%M:%S')
            except:
                return None

    def _mt5_deal_to_event(self, deal) -> Optional[Dict]:
        """
        Convert MT5 deal to trade event.

        Args:
            deal: MT5 deal object

        Returns:
            Event dictionary or None
        """
        try:
            # Extract relevant fields from MT5 deal
            # NOTE: This is a simplified conversion
            # Full implementation would parse comment field for strategy info

            event = {
                'event_type': 'EXIT' if deal.entry == 1 else 'ENTRY',  # 1 = out, 0 = in
                'timestamp': datetime.fromtimestamp(deal.time),
                'trade_id': f"MT5_{deal.ticket}",
                'symbol': deal.symbol,
                'strategy_id': 'UNKNOWN',  # Extract from comment if available
                'price': deal.price,
                'quantity': deal.volume,
                'pnl_gross': deal.profit,
                'notes': f"MT5 backfill: {deal.comment}"
            }

            return event

        except Exception as e:
            logger.error(f"Error converting MT5 deal: {e}")
            return None

    def print_stats(self):
        """Print backfill statistics."""
        logger.info("\n" + "=" * 80)
        logger.info("BACKFILL STATISTICS")
        logger.info("=" * 80)
        logger.info(f"Total processed:  {self.stats['total_processed']}")
        logger.info(f"Total inserted:   {self.stats['total_inserted']}")
        logger.info(f"Total skipped:    {self.stats['total_skipped']}")
        logger.info(f"Total errors:     {self.stats['total_errors']}")
        logger.info("=" * 80)

    def close(self):
        """Close database connection."""
        if self.db:
            self.db.close()


def main():
    """Entry point."""
    parser = argparse.ArgumentParser(description='Backfill historical data to reporting DB')

    parser.add_argument('--source', choices=['jsonl', 'mt5', 'csv'], required=True,
                       help='Data source for backfill')

    parser.add_argument('--start-date', type=str,
                       help='Start date (YYYY-MM-DD) for filtering')
    parser.add_argument('--end-date', type=str,
                       help='End date (YYYY-MM-DD) for filtering')

    parser.add_argument('--days', type=int, default=90,
                       help='Number of days for MT5 history (default: 90)')

    parser.add_argument('--jsonl-dir', type=str, default='reports/raw',
                       help='Directory for JSONL files (default: reports/raw)')

    parser.add_argument('--csv-file', type=str,
                       help='Path to CSV file for backfill')

    args = parser.parse_args()

    # Parse dates
    start_date = datetime.strptime(args.start_date, '%Y-%m-%d') if args.start_date else None
    end_date = datetime.strptime(args.end_date, '%Y-%m-%d') if args.end_date else None

    # Run backfill
    backfill = BackfillReportingDB()

    try:
        if args.source == 'jsonl':
            backfill.backfill_from_jsonl(
                jsonl_dir=args.jsonl_dir,
                start_date=start_date,
                end_date=end_date
            )

        elif args.source == 'mt5':
            backfill.backfill_from_mt5(days=args.days)

        elif args.source == 'csv':
            if not args.csv_file:
                logger.error("--csv-file required for CSV backfill")
                return 1
            backfill.backfill_from_csv(csv_file=args.csv_file)

        # Print stats
        backfill.print_stats()

    finally:
        backfill.close()

    return 0


if __name__ == '__main__':
    sys.exit(main())
