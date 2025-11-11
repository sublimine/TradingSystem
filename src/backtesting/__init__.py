"""
Elite Backtesting Framework

Professional-grade backtesting and performance analysis tools.

Components:
- BacktestEngine: Historical simulation with transaction costs
- PerformanceAnalyzer: Advanced metrics and reporting
- Walk-forward optimization
- Monte Carlo simulation
- Multi-strategy portfolio testing

Usage:
    from src.backtesting import BacktestEngine, PerformanceAnalyzer

    # Initialize engine
    engine = BacktestEngine(
        strategies=strategy_list,
        initial_capital=10000,
        risk_per_trade=0.01,
        commission_per_lot=7.0,
        slippage_pips=0.5
    )

    # Run backtest
    results = engine.run_backtest(
        historical_data=data_dict,
        start_date=datetime(2023, 1, 1),
        end_date=datetime(2024, 1, 1)
    )

    # Analyze performance
    analyzer = PerformanceAnalyzer()
    analysis = analyzer.analyze_backtest(results)

    # Generate recommendations
    recommendations = analyzer.generate_recommendations(analysis)

Author: Elite Trading System
Version: 1.0
"""

from .backtest_engine import BacktestEngine
from .performance_analyzer import PerformanceAnalyzer

__all__ = [
    'BacktestEngine',
    'PerformanceAnalyzer',
]

__version__ = '1.0.0'
