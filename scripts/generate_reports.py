#!/usr/bin/env python3
"""
Script de Generación de Informes Institucionales

Genera informes diarios/semanales/mensuales/trimestrales/anuales
del sistema de trading SUBLIMINE.

Uso:
    python scripts/generate_reports.py --frequency daily --date 2025-11-14
    python scripts/generate_reports.py --frequency weekly --start 2025-11-08 --end 2025-11-14
    python scripts/generate_reports.py --frequency monthly --month 2025-11
    python scripts/generate_reports.py --auto

Mandato: MANDATO 11
Fecha: 2025-11-14
"""

import argparse
import sys
import os
from datetime import datetime, timedelta
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

# Import reporting modules
try:
    from reporting import aggregators, metrics, generators
    from reporting.event_logger import ExecutionEventLogger
except ImportError as e:
    print(f"❌ Error importing reporting modules: {e}")
    print("Ensure src/reporting is in PYTHONPATH")
    sys.exit(1)


def load_trades_from_db(start_date, end_date):
    """Load trades from database for date range."""
    # TODO: Implement DB connection and query
    # For now, return empty DataFrame for MVP
    import pandas as pd
    return pd.DataFrame()


def load_positions_snapshot():
    """Load current positions from database."""
    import pandas as pd
    return pd.DataFrame()


def load_risk_snapshot():
    """Load current risk snapshot."""
    return {
        'total_risk_used_pct': 0.0,
        'total_risk_available_pct': 100.0
    }


def generate_daily(date: datetime, output_dir: Path):
    """Generar informe diario."""
    print(f"📊 Generando informe diario para {date.strftime('%Y-%m-%d')}...")

    # Load data
    trades = load_trades_from_db(date, date + timedelta(days=1))
    positions = load_positions_snapshot()
    risk_snapshot = load_risk_snapshot()

    # Generate report
    report_md = generators.generate_daily_report(date, trades, positions, risk_snapshot)

    # Save
    output_file = output_dir / f"report_{date.strftime('%Y%m%d')}.md"
    output_file.write_text(report_md)

    print(f"✅ Informe diario guardado: {output_file}")
    return output_file


def generate_weekly(start_date: datetime, end_date: datetime, output_dir: Path):
    """Generar informe semanal."""
    print(f"📊 Generando informe semanal {start_date.strftime('%Y-%m-%d')} - {end_date.strftime('%Y-%m-%d')}...")

    # Load data
    trades = load_trades_from_db(start_date, end_date)
    equity_curve = metrics.calculate_equity_curve(trades)

    # Generate report
    report_md = generators.generate_weekly_report(start_date, end_date, trades, equity_curve)

    # Save
    output_file = output_dir / f"report_{start_date.strftime('%Y%m%d')}_to_{end_date.strftime('%Y%m%d')}.md"
    output_file.write_text(report_md)

    print(f"✅ Informe semanal guardado: {output_file}")
    return output_file


def generate_monthly(month_start: datetime, output_dir: Path):
    """Generar informe mensual."""
    print(f"📊 Generando informe mensual {month_start.strftime('%Y-%m')}...")

    # Calculate month end
    if month_start.month == 12:
        month_end = datetime(month_start.year + 1, 1, 1)
    else:
        month_end = datetime(month_start.year, month_start.month + 1, 1)

    # Load data
    trades = load_trades_from_db(month_start, month_end)
    strategy_perf = aggregators.aggregate_by_strategy(trades)

    # Generate report
    report_md = generators.generate_monthly_report(month_start, month_end, trades, strategy_perf)

    # Save
    output_file = output_dir / f"report_{month_start.strftime('%Y%m')}.md"
    output_file.write_text(report_md)

    print(f"✅ Informe mensual guardado: {output_file}")
    return output_file


def generate_auto():
    """Generar todos los informes pendientes automáticamente."""
    print("🤖 Modo automático: generando informes pendientes...")

    base_dir = Path(__file__).parent.parent / "reports"

    # Daily (ayer)
    yesterday = datetime.now() - timedelta(days=1)
    daily_dir = base_dir / "daily"
    daily_dir.mkdir(parents=True, exist_ok=True)
    generate_daily(yesterday, daily_dir)

    # Weekly (si es domingo)
    if datetime.now().weekday() == 6:  # Sunday
        week_end = datetime.now()
        week_start = week_end - timedelta(days=7)
        weekly_dir = base_dir / "weekly"
        weekly_dir.mkdir(parents=True, exist_ok=True)
        generate_weekly(week_start, week_end, weekly_dir)

    # Monthly (si es primer día del mes)
    if datetime.now().day == 1:
        last_month = datetime.now() - timedelta(days=1)
        month_start = datetime(last_month.year, last_month.month, 1)
        monthly_dir = base_dir / "monthly"
        monthly_dir.mkdir(parents=True, exist_ok=True)
        generate_monthly(month_start, monthly_dir)

    print("✅ Modo automático completado")


def main():
    parser = argparse.ArgumentParser(description="Generar informes institucionales SUBLIMINE")

    parser.add_argument("--frequency", choices=["daily", "weekly", "monthly", "quarterly", "annual", "auto"],
                       help="Frecuencia del informe")
    parser.add_argument("--date", help="Fecha para informe diario (YYYY-MM-DD)")
    parser.add_argument("--start", help="Fecha inicio para informe semanal (YYYY-MM-DD)")
    parser.add_argument("--end", help="Fecha fin para informe semanal (YYYY-MM-DD)")
    parser.add_argument("--month", help="Mes para informe mensual (YYYY-MM)")
    parser.add_argument("--auto", action="store_true", help="Generar automáticamente informes pendientes")

    args = parser.parse_args()

    # Base directory for reports
    base_dir = Path(__file__).parent.parent / "reports"

    try:
        if args.auto or args.frequency == "auto":
            generate_auto()

        elif args.frequency == "daily":
            if not args.date:
                print("❌ Error: --date requerido para informe diario")
                sys.exit(1)
            date = datetime.strptime(args.date, "%Y-%m-%d")
            daily_dir = base_dir / "daily"
            daily_dir.mkdir(parents=True, exist_ok=True)
            generate_daily(date, daily_dir)

        elif args.frequency == "weekly":
            if not args.start or not args.end:
                print("❌ Error: --start y --end requeridos para informe semanal")
                sys.exit(1)
            start = datetime.strptime(args.start, "%Y-%m-%d")
            end = datetime.strptime(args.end, "%Y-%m-%d")
            weekly_dir = base_dir / "weekly"
            weekly_dir.mkdir(parents=True, exist_ok=True)
            generate_weekly(start, end, weekly_dir)

        elif args.frequency == "monthly":
            if not args.month:
                print("❌ Error: --month requerido para informe mensual")
                sys.exit(1)
            month_start = datetime.strptime(args.month, "%Y-%m")
            monthly_dir = base_dir / "monthly"
            monthly_dir.mkdir(parents=True, exist_ok=True)
            generate_monthly(month_start, monthly_dir)

        else:
            parser.print_help()
            sys.exit(1)

    except Exception as e:
        print(f"❌ Error generando informe: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
