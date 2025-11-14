#!/usr/bin/env python3
"""
MANDATO 20 - Download MT5 Historical Data (REAL)

Descarga datos históricos REALES desde MetaTrader 5.

Usage:
    # Check connection
    python scripts/download_mt5_history.py --check-connection

    # Download específico
    python scripts/download_mt5_history.py \\
        --symbols EURUSD,XAUUSD,US500 \\
        --timeframe M15 \\
        --start 2023-01-01 \\
        --end 2024-12-31 \\
        --dest data/historical/REAL

    # Download desde config
    python scripts/download_mt5_history.py --use-config config/mt5_data_config.yaml

NON-NEGOTIABLES:
- Solo descarga datos REALES (no sintéticos)
- Credenciales desde ENV vars (NUNCA en código)
- Validación de datos institucional
- Logging detallado

Autor: SUBLIMINE Institutional Trading System
Fecha: 2025-11-14
Mandato: MANDATO 20
"""

import sys
import os
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import argparse
import logging
from datetime import datetime
import yaml

from src.data_providers import MT5DataClient

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s'
)
logger = logging.getLogger(__name__)


def check_connection():
    """Verificar conexión MT5."""
    logger.info("="*80)
    logger.info("MANDATO 20 - MT5 CONNECTION CHECK")
    logger.info("="*80)

    client = MT5DataClient()

    if not client.available:
        logger.critical("❌ MT5 NOT AVAILABLE")
        logger.critical("Install with: pip install MetaTrader5")
        logger.critical("Cannot proceed without MT5 module")
        return False

    if client.check_connection():
        logger.info("="*80)
        logger.info("✅ MT5 CONNECTION OK")
        logger.info("="*80)
        client.disconnect()
        return True
    else:
        logger.error("="*80)
        logger.error("❌ MT5 CONNECTION FAILED")
        logger.error("="*80)
        logger.error("Troubleshooting:")
        logger.error("1. Ensure MT5 terminal is running and logged in")
        logger.error("2. Enable auto-trading in MT5 terminal")
        logger.error("3. Check firewall/antivirus settings")
        client.disconnect()
        return False


def download_historical(symbols: list, timeframe: str, start_date: datetime,
                       end_date: datetime, dest_dir: str):
    """
    Descargar históricos para múltiples símbolos.

    Args:
        symbols: Lista de símbolos (ej: ['EURUSD', 'XAUUSD'])
        timeframe: Timeframe ('M1', 'M5', 'M15', 'H1', 'H4', 'D1')
        start_date: Fecha inicio
        end_date: Fecha fin
        dest_dir: Directorio destino
    """
    logger.info("="*80)
    logger.info("MANDATO 20 - MT5 HISTORICAL DATA DOWNLOAD (REAL)")
    logger.info("="*80)
    logger.info(f"Symbols: {symbols}")
    logger.info(f"Timeframe: {timeframe}")
    logger.info(f"Period: {start_date.date()} to {end_date.date()}")
    logger.info(f"Destination: {dest_dir}")
    logger.info("="*80)

    client = MT5DataClient()

    if not client.available:
        logger.critical("❌ MT5 NOT AVAILABLE - Cannot download")
        logger.critical("MANDATO 20 BLOCKED: MetaTrader5 module not installed")
        sys.exit(1)

    if not client.check_connection():
        logger.critical("❌ MT5 CONNECTION FAILED - Cannot download")
        logger.critical("MANDATO 20 BLOCKED: No connection to MT5")
        sys.exit(1)

    # Download each symbol
    results = {
        'success': [],
        'failed': []
    }

    for symbol in symbols:
        logger.info(f"\n[{symbol}] Downloading {timeframe} data...")

        try:
            df = client.download_ohlcv(
                symbol=symbol,
                timeframe=timeframe,
                start_date=start_date,
                end_date=end_date
            )

            filepath = client.save_to_csv(
                df=df,
                symbol=symbol,
                timeframe=timeframe,
                output_dir=dest_dir
            )

            results['success'].append({
                'symbol': symbol,
                'bars': len(df),
                'file': str(filepath)
            })

            logger.info(f"✅ [{symbol}] Downloaded {len(df)} bars → {filepath}")

        except Exception as e:
            logger.error(f"❌ [{symbol}] Download failed: {e}")
            results['failed'].append({
                'symbol': symbol,
                'error': str(e)
            })

    # Disconnect
    client.disconnect()

    # Summary
    logger.info("\n" + "="*80)
    logger.info("DOWNLOAD SUMMARY")
    logger.info("="*80)

    if results['success']:
        logger.info(f"✅ SUCCESS: {len(results['success'])} symbols")
        for r in results['success']:
            logger.info(f"   {r['symbol']}: {r['bars']} bars → {r['file']}")

    if results['failed']:
        logger.error(f"❌ FAILED: {len(results['failed'])} symbols")
        for r in results['failed']:
            logger.error(f"   {r['symbol']}: {r['error']}")

    logger.info("="*80)

    if results['failed']:
        logger.warning("Some downloads failed - review logs above")
        sys.exit(1)
    else:
        logger.info("All downloads completed successfully")
        sys.exit(0)


def main():
    parser = argparse.ArgumentParser(
        description='MANDATO 20 - Download MT5 Historical Data (REAL)'
    )

    parser.add_argument('--check-connection', action='store_true',
                       help='Only check MT5 connection (no download)')

    parser.add_argument('--symbols', type=str,
                       help='Comma-separated symbols (e.g., EURUSD,XAUUSD,US500)')

    parser.add_argument('--timeframe', type=str, default='M15',
                       help='Timeframe (M1, M5, M15, H1, H4, D1)')

    parser.add_argument('--start', type=str,
                       help='Start date (YYYY-MM-DD)')

    parser.add_argument('--end', type=str,
                       help='End date (YYYY-MM-DD)')

    parser.add_argument('--dest', type=str, default='data/historical/REAL',
                       help='Destination directory')

    args = parser.parse_args()

    # Check connection only
    if args.check_connection:
        success = check_connection()
        sys.exit(0 if success else 1)

    # Download mode
    if not args.symbols or not args.start or not args.end:
        parser.error("--symbols, --start, and --end are required for download mode")

    symbols = [s.strip() for s in args.symbols.split(',')]
    start_date = datetime.strptime(args.start, '%Y-%m-%d')
    end_date = datetime.strptime(args.end, '%Y-%m-%d')

    download_historical(
        symbols=symbols,
        timeframe=args.timeframe,
        start_date=start_date,
        end_date=end_date,
        dest_dir=args.dest
    )


if __name__ == '__main__':
    main()
