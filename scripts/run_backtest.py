#!/usr/bin/env python3
"""
Institutional Backtest CLI - MANDATO 17

CLI para ejecutar backtests institucionales del sistema completo.

Usage:
    python scripts/run_backtest.py \\
        --start-date 2024-01-01 \\
        --end-date 2024-06-30 \\
        --symbols EURUSD.pro GBPUSD.pro \\
        --strategies liquidity_sweep vpin_reversal_extreme \\
        --timeframe M15 \\
        --mode csv

Parameters:
    --start-date: Fecha inicio (YYYY-MM-DD)
    --end-date: Fecha fin (YYYY-MM-DD)
    --symbols: Lista de símbolos
    --strategies: Lista de estrategias a usar
    --timeframe: Timeframe base (M1, M5, M15, H1, H4, D1)
    --mode: Modo de datos ('csv' o 'mt5')
    --config: Ruta a config de backtest (opcional)
    --report: Generar informe al finalizar (default: True)

Respeta:
- config/risk_limits.yaml (0-2% caps)
- SL/TP estructurales (NO ATR)
- Statistical circuit breakers
- Trazabilidad completa (ExecutionEventLogger)
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import argparse
from datetime import datetime
import logging

from src.backtest.engine import BacktestEngine
from src.backtest.runner import BacktestRunner

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    handlers=[
        logging.FileHandler('logs/backtest.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description='Institutional Backtest Engine - MANDATO 17',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Backtest 6 meses con 2 estrategias
  python scripts/run_backtest.py \\
      --start-date 2024-01-01 \\
      --end-date 2024-06-30 \\
      --symbols EURUSD.pro GBPUSD.pro \\
      --strategies liquidity_sweep vpin_reversal_extreme \\
      --timeframe M15

  # Backtest con todas las estrategias core
  python scripts/run_backtest.py \\
      --start-date 2024-01-01 \\
      --end-date 2024-06-30 \\
      --symbols EURUSD.pro GBPUSD.pro USDJPY.pro XAUUSD.pro \\
      --strategies liquidity_sweep order_flow_toxicity ofi_refinement vpin_reversal_extreme breakout_volume_confirmation \\
      --timeframe M15 \\
      --report
        """
    )

    parser.add_argument(
        '--start-date',
        type=str,
        required=True,
        help='Start date (YYYY-MM-DD)'
    )

    parser.add_argument(
        '--end-date',
        type=str,
        required=True,
        help='End date (YYYY-MM-DD)'
    )

    parser.add_argument(
        '--symbols',
        nargs='+',
        required=True,
        help='List of symbols to backtest (e.g., EURUSD.pro GBPUSD.pro)'
    )

    parser.add_argument(
        '--strategies',
        nargs='+',
        default=['liquidity_sweep', 'vpin_reversal_extreme'],
        help='List of strategies to use (default: liquidity_sweep vpin_reversal_extreme)'
    )

    parser.add_argument(
        '--timeframe',
        type=str,
        default='M15',
        choices=['M1', 'M5', 'M15', 'M30', 'H1', 'H4', 'D1'],
        help='Base timeframe (default: M15)'
    )

    parser.add_argument(
        '--mode',
        type=str,
        default='csv',
        choices=['csv', 'mt5'],
        help='Data source mode (default: csv)'
    )

    parser.add_argument(
        '--config',
        type=str,
        default='config/backtest_config.yaml',
        help='Backtest config file (default: config/backtest_config.yaml)'
    )

    parser.add_argument(
        '--report',
        action='store_true',
        default=True,
        help='Generate report after backtest (default: True)'
    )

    parser.add_argument(
        '--no-progress',
        action='store_true',
        help='Disable progress bar'
    )

    return parser.parse_args()


def main():
    """Main entry point."""
    args = parse_args()

    logger.info("="*80)
    logger.info("MANDATO 17 - INSTITUTIONAL BACKTEST ENGINE")
    logger.info("="*80)
    logger.info(f"Start date: {args.start_date}")
    logger.info(f"End date: {args.end_date}")
    logger.info(f"Symbols: {args.symbols}")
    logger.info(f"Strategies: {args.strategies}")
    logger.info(f"Timeframe: {args.timeframe}")
    logger.info(f"Mode: {args.mode}")
    logger.info("="*80)

    # Parse dates
    try:
        start_date = datetime.strptime(args.start_date, '%Y-%m-%d')
        end_date = datetime.strptime(args.end_date, '%Y-%m-%d')
    except ValueError as e:
        logger.error(f"Invalid date format: {e}")
        logger.error("Use format YYYY-MM-DD (e.g., 2024-01-01)")
        sys.exit(1)

    # Validate date range
    if start_date >= end_date:
        logger.error("Start date must be before end date")
        sys.exit(1)

    # Create backtest engine
    try:
        logger.info("Initializing backtest engine...")
        engine = BacktestEngine(config_path=args.config)

        # Override config with CLI args
        engine.config['symbols'] = args.symbols
        engine.config['strategies'] = args.strategies
        engine.config['timeframe'] = args.timeframe
        engine.config['execution_mode'] = 'CLOSE'  # Always close-based for OHLCV

        # Initialize components
        engine.initialize_components()

    except Exception as e:
        logger.error(f"Failed to initialize backtest engine: {e}", exc_info=True)
        sys.exit(1)

    # Load data
    try:
        logger.info("Loading market data...")
        engine.load_data(
            symbols=args.symbols,
            start_date=start_date,
            end_date=end_date,
            timeframe=args.timeframe,
            data_source=args.mode
        )

    except Exception as e:
        logger.error(f"Failed to load market data: {e}", exc_info=True)
        sys.exit(1)

    # Create runner
    try:
        logger.info("Creating backtest runner...")
        runner = BacktestRunner(engine)

    except Exception as e:
        logger.error(f"Failed to create runner: {e}", exc_info=True)
        sys.exit(1)

    # Run backtest
    try:
        logger.info("Starting backtest execution...")
        runner.run(
            start_date=start_date,
            end_date=end_date,
            progress_bar=not args.no_progress
        )

    except KeyboardInterrupt:
        logger.warning("Backtest interrupted by user")
        engine.finalize()
        sys.exit(1)

    except Exception as e:
        logger.error(f"Backtest failed: {e}", exc_info=True)
        engine.finalize()
        sys.exit(1)

    # Generate report
    if args.report:
        try:
            logger.info("Generating backtest report...")
            # TODO: Integrate with scripts/generate_reports.py
            logger.info("Report generation to be implemented (FASE 1.2)")

        except Exception as e:
            logger.error(f"Report generation failed: {e}")

    logger.info("="*80)
    logger.info("✅ BACKTEST COMPLETED SUCCESSFULLY")
    logger.info("="*80)

    # Show summary
    stats = engine.get_statistics()
    logger.info(f"Total signals: {stats['total_signals']}")
    logger.info(f"  Approved: {stats['signals_approved']}")
    logger.info(f"  Rejected: {stats['signals_rejected']}")
    logger.info(f"Trades opened: {stats['trades_opened']}")
    logger.info(f"Trades closed: {stats['trades_closed']}")

    if 'risk_manager' in stats:
        rm_stats = stats['risk_manager']
        logger.info(f"Final equity: ${rm_stats.get('current_equity', 0):,.2f}")
        logger.info(f"Max drawdown: {rm_stats.get('current_drawdown_pct', 0):.2f}%")

    logger.info("="*80)
    logger.info("Events logged to: reports/raw/events_emergency.jsonl")
    logger.info("Logs available at: logs/backtest.log")
    logger.info("="*80)

    sys.exit(0)


if __name__ == '__main__':
    main()
