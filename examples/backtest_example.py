"""
Complete Backtesting Example - Elite Trading System

This example demonstrates:
1. Loading historical data
2. Initializing strategies
3. Running backtests
4. Analyzing performance
5. Walk-forward optimization
6. Monte Carlo simulation
7. Generating actionable recommendations

Run this on historical data to validate strategies before live deployment.

Author: Elite Trading System
Version: 1.0
"""

import pandas as pd
import MetaTrader5 as mt5
from datetime import datetime, timedelta
import logging
from pathlib import Path

# Import backtesting framework
from src.backtesting import BacktestEngine, PerformanceAnalyzer

# Import strategies
from src.strategies import (
    OrderBlockStrategy,
    FVGStrategy,
    StopHuntReversal,
    IcebergDetection,
    FootprintClusters,
    StatisticalArbitrageJohansen,
    CrisisModeVolatilitySpike,
    NFPNewsEventHandler,
)

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


def load_historical_data(symbol: str, start_date: datetime, end_date: datetime, timeframe=mt5.TIMEFRAME_M5):
    """
    Load historical data from MT5.

    Args:
        symbol: Trading symbol (e.g., 'EURUSD')
        start_date: Start date
        end_date: End date
        timeframe: MT5 timeframe constant

    Returns:
        DataFrame with OHLCV data
    """
    if not mt5.initialize():
        logger.error(f"MT5 initialization failed: {mt5.last_error()}")
        return None

    # Get rates
    rates = mt5.copy_rates_range(symbol, timeframe, start_date, end_date)

    if rates is None or len(rates) == 0:
        logger.error(f"No data retrieved for {symbol}")
        return None

    # Convert to DataFrame
    df = pd.DataFrame(rates)
    df['time'] = pd.to_datetime(df['time'], unit='s')
    df.set_index('time', inplace=True)

    logger.info(f"Loaded {len(df)} bars for {symbol}")

    return df


def prepare_strategies():
    """
    Initialize strategies to test.

    Returns:
        List of strategy instances
    """
    # Load config
    # (In production, load from config/strategies_institutional.yaml)

    strategies = [
        # Structure strategies
        OrderBlockStrategy(config={'enabled': True}),
        FVGStrategy(config={'enabled': True}),

        # Liquidity strategies
        StopHuntReversal(config={'enabled': True}),
        IcebergDetection(config={'enabled': True}),
        FootprintClusters(config={'enabled': True}),

        # Statistical strategies
        StatisticalArbitrageJohansen(config={'enabled': True}),

        # Crisis/Event strategies
        CrisisModeVolatilitySpike(config={'enabled': True}),
        NFPNewsEventHandler(config={'enabled': True}),
    ]

    logger.info(f"Initialized {len(strategies)} strategies")

    return strategies


def run_simple_backtest():
    """
    Example 1: Simple backtest on single symbol.
    """
    logger.info("=" * 80)
    logger.info("EXAMPLE 1: Simple Backtest")
    logger.info("=" * 80)

    # Define backtest period
    end_date = datetime.now()
    start_date = end_date - timedelta(days=90)  # 3 months

    # Load data
    logger.info(f"Loading data: {start_date} to {end_date}")
    eurusd_data = load_historical_data('EURUSD', start_date, end_date)

    if eurusd_data is None:
        logger.error("Failed to load data")
        return

    # Prepare strategies
    strategies = prepare_strategies()

    # Initialize backtest engine
    engine = BacktestEngine(
        strategies=strategies,
        initial_capital=10000.0,        # $10,000 starting capital
        risk_per_trade=0.01,             # 1% risk per trade
        commission_per_lot=7.0,          # $7 round-trip commission
        slippage_pips=0.5,               # 0.5 pip slippage
        spread_pips={'EURUSD': 1.2}      # 1.2 pip average spread
    )

    # Run backtest
    logger.info("Running backtest...")
    results = engine.run_backtest(
        historical_data={'EURUSD': eurusd_data},
        start_date=start_date,
        end_date=end_date
    )

    # Analyze performance
    analyzer = PerformanceAnalyzer(output_dir='backtest_reports/')
    analysis = analyzer.analyze_backtest(results, save_report=True)

    # Print summary
    print("\n" + "=" * 80)
    print("BACKTEST RESULTS")
    print("=" * 80)
    print(f"Initial Capital:    ${results['initial_capital']:,.2f}")
    print(f"Final Equity:       ${results['final_equity']:,.2f}")
    print(f"Total Return:       {results['total_return_pct']:.2f}%")
    print(f"Total Return (R):   {results['total_return_r']:.2f}R")
    print(f"Total Trades:       {results['total_trades']}")
    print(f"Win Rate:           {results['win_rate']:.2%}")
    print(f"Expectancy:         {results['expectancy_r']:.3f}R")
    print(f"Sharpe Ratio:       {analysis['risk_metrics']['sharpe_ratio']:.2f}")
    print(f"Sortino Ratio:      {analysis['risk_metrics']['sortino_ratio']:.2f}")
    print(f"Max Drawdown:       {abs(analysis['drawdown_analysis']['max_drawdown_r']):.2f}R")
    print(f"Profit Factor:      {analysis['risk_metrics']['profit_factor']:.2f}")
    print("=" * 80)

    # Generate recommendations
    recommendations = analyzer.generate_recommendations(analysis)

    print("\nRECOMMENDATIONS:")
    print("-" * 80)
    for i, rec in enumerate(recommendations, 1):
        print(f"{i}. {rec}")
    print("=" * 80)

    return results, analysis


def run_walk_forward():
    """
    Example 2: Walk-forward optimization.
    """
    logger.info("=" * 80)
    logger.info("EXAMPLE 2: Walk-Forward Optimization")
    logger.info("=" * 80)

    # Load longer historical period (1 year)
    end_date = datetime.now()
    start_date = end_date - timedelta(days=365)

    logger.info(f"Loading data: {start_date} to {end_date}")
    eurusd_data = load_historical_data('EURUSD', start_date, end_date)

    if eurusd_data is None:
        logger.error("Failed to load data")
        return

    strategies = prepare_strategies()

    engine = BacktestEngine(
        strategies=strategies,
        initial_capital=10000.0,
        risk_per_trade=0.01
    )

    # Run walk-forward (4 periods: 3 months in-sample, 1 month out-sample)
    logger.info("Running walk-forward optimization...")
    wf_results = engine.run_walk_forward(
        historical_data={'EURUSD': eurusd_data},
        in_sample_months=3,
        out_sample_months=1,
        total_periods=4
    )

    print("\n" + "=" * 80)
    print("WALK-FORWARD RESULTS")
    print("=" * 80)
    print(f"In-Sample Total:    {wf_results['in_sample_total_r']:.2f}R")
    print(f"Out-Sample Total:   {wf_results['out_sample_total_r']:.2f}R")
    print(f"WF Efficiency:      {wf_results['wf_efficiency']:.2%}")
    print("\nInterpretation:")
    if wf_results['wf_efficiency'] > 0.7:
        print("✅ EXCELLENT - Out-sample performance strong (>70% of in-sample)")
    elif wf_results['wf_efficiency'] > 0.5:
        print("✓ GOOD - Out-sample performance acceptable (>50% of in-sample)")
    elif wf_results['wf_efficiency'] > 0.3:
        print("⚠️  MARGINAL - Out-sample degradation significant")
    else:
        print("🔴 POOR - Severe overfitting detected")
    print("=" * 80)

    return wf_results


def run_monte_carlo():
    """
    Example 3: Monte Carlo simulation.
    """
    logger.info("=" * 80)
    logger.info("EXAMPLE 3: Monte Carlo Simulation")
    logger.info("=" * 80)

    # First run a backtest to get trade results
    end_date = datetime.now()
    start_date = end_date - timedelta(days=90)

    eurusd_data = load_historical_data('EURUSD', start_date, end_date)

    if eurusd_data is None:
        return

    strategies = prepare_strategies()

    engine = BacktestEngine(
        strategies=strategies,
        initial_capital=10000.0,
        risk_per_trade=0.01
    )

    results = engine.run_backtest(
        historical_data={'EURUSD': eurusd_data},
        start_date=start_date,
        end_date=end_date
    )

    if results.get('total_trades', 0) < 10:
        logger.warning("Insufficient trades for Monte Carlo")
        return

    # Extract trade returns
    trades_df = pd.DataFrame(results['trades'])
    trade_returns = trades_df['pnl_r'].values

    # Run Monte Carlo
    logger.info("Running 1000 Monte Carlo simulations...")
    mc_results = engine.run_monte_carlo(
        trade_results=trade_returns,
        num_simulations=1000,
        confidence_level=0.95
    )

    print("\n" + "=" * 80)
    print("MONTE CARLO RESULTS (1000 simulations)")
    print("=" * 80)
    print(f"Mean Return:         {mc_results['mean_return_r']:.2f}R")
    print(f"Median Return:       {mc_results['median_return_r']:.2f}R")
    print(f"Std Deviation:       {mc_results['std_return_r']:.2f}R")
    print(f"P(Profit):           {mc_results['probability_positive']:.2%}")
    print(f"VaR (95%):           {mc_results['var_95']:.2f}R")
    print(f"CVaR (95%):          {mc_results['cvar_95']:.2f}R")
    print(f"5th Percentile:      {mc_results['percentile_5_return']:.2f}R")
    print(f"95th Percentile:     {mc_results['percentile_95_return']:.2f}R")
    print(f"Worst DD:            {mc_results['worst_case_dd']:.2f}R")
    print(f"Mean DD:             {mc_results['mean_dd']:.2f}R")
    print("=" * 80)

    return mc_results


def main():
    """
    Run all backtest examples.
    """
    print("\n")
    print("=" * 80)
    print("ELITE TRADING SYSTEM - BACKTESTING EXAMPLES")
    print("=" * 80)
    print("\n")

    # Example 1: Simple backtest
    try:
        results, analysis = run_simple_backtest()
    except Exception as e:
        logger.error(f"Simple backtest failed: {e}")

    input("\nPress Enter to continue to Walk-Forward...")

    # Example 2: Walk-forward
    try:
        wf_results = run_walk_forward()
    except Exception as e:
        logger.error(f"Walk-forward failed: {e}")

    input("\nPress Enter to continue to Monte Carlo...")

    # Example 3: Monte Carlo
    try:
        mc_results = run_monte_carlo()
    except Exception as e:
        logger.error(f"Monte Carlo failed: {e}")

    print("\n")
    print("=" * 80)
    print("ALL EXAMPLES COMPLETED")
    print("=" * 80)
    print("\nNext Steps:")
    print("1. Review backtest reports in backtest_reports/ directory")
    print("2. Analyze which strategies performed best")
    print("3. Disable/optimize underperforming strategies")
    print("4. Run longer historical backtests (1-2 years)")
    print("5. Paper trade for 3-6 months before live deployment")
    print("=" * 80)


if __name__ == "__main__":
    main()
