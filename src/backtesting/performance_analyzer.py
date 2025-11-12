"""
Advanced Performance Analyzer - Elite Reporting System

Comprehensive performance analysis with:
- Advanced risk metrics (Sharpe, Sortino, Calmar, Omega, Kappa)
- Strategy attribution and correlation
- Drawdown analysis and recovery
- Trade distribution analysis
- Regime performance breakdown
- Parameter sensitivity testing
- Detailed HTML/PDF report generation

Research Basis:
- Sharpe (1994): The Sharpe Ratio
- Sortino & Price (1994): Performance Measurement in a Downside Risk Framework
- Young (1991): Calmar Ratio
- Keating & Shadwick (2002): Omega Ratio
- Kaplan & Knowles (2004): Kappa 3 Ratio
- Bailey et al. (2017): Stock Portfolio Design and Backtest Overfitting

Author: Elite Trading System
Version: 1.0
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple
from datetime import datetime
import json
import logging
from pathlib import Path
from scipy import stats
from collections import defaultdict

logger = logging.getLogger(__name__)


class PerformanceAnalyzer:
    """
    Advanced performance analysis for backtesting results.

    Generates comprehensive reports with:
    - Risk-adjusted returns (Sharpe, Sortino, Calmar, Omega, Kappa)
    - Strategy attribution and correlation matrix
    - Drawdown analysis (max DD, recovery time, DD distribution)
    - Win/loss distribution and streaks
    - Regime-based performance
    - Monthly/quarterly returns
    - Trade clustering and time-of-day analysis
    """

    def __init__(self, output_dir: str = 'backtest_reports/'):
        """
        Initialize performance analyzer.

        Args:
            output_dir: Directory to save reports
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        self.logger = logging.getLogger(self.__class__.__name__)

    def analyze_backtest(self, backtest_results: Dict, save_report: bool = True) -> Dict:
        """
        Comprehensive analysis of backtest results.

        Args:
            backtest_results: Results from BacktestEngine
            save_report: Whether to save report to file

        Returns:
            Dict with complete analysis
        """
        if 'error' in backtest_results:
            return backtest_results

        trades_df = pd.DataFrame(backtest_results['trades'])
        equity_df = pd.DataFrame(backtest_results['equity_curve'])

        self.logger.info(f"📊 Analyzing {len(trades_df)} trades...")

        analysis = {
            'summary': self._generate_summary(backtest_results),
            'risk_metrics': self._calculate_risk_metrics(trades_df),
            'strategy_attribution': self._analyze_strategy_attribution(trades_df),
            'strategy_correlation': self._calculate_strategy_correlation(trades_df),
            'drawdown_analysis': self._analyze_drawdowns(trades_df['pnl_r'].values),
            'trade_distribution': self._analyze_trade_distribution(trades_df),
            'win_loss_streaks': self._analyze_streaks(trades_df),
            'monthly_returns': self._calculate_monthly_returns(trades_df),
            'time_analysis': self._analyze_time_patterns(trades_df),
            'symbol_performance': self._analyze_by_symbol(trades_df),
        }

        # Add regime analysis if available
        if 'entry_regime' in trades_df.columns:
            analysis['regime_performance'] = self._analyze_by_regime(trades_df)

        if save_report:
            self._save_analysis_report(analysis)

        self.logger.info(f"✅ Analysis complete. Sharpe: {analysis['risk_metrics']['sharpe_ratio']:.2f}")

        return analysis

    def compare_strategies(self, results_dict: Dict[str, Dict]) -> Dict:
        """
        Compare multiple strategy results side-by-side.

        Args:
            results_dict: Dict of {strategy_name: backtest_results}

        Returns:
            Comparison table and rankings
        """
        comparison = {
            'strategies': [],
            'metrics': {}
        }

        for name, results in results_dict.items():
            if 'error' in results:
                continue

            comparison['strategies'].append({
                'name': name,
                'total_return_r': results.get('total_return_r', 0),
                'win_rate': results.get('win_rate', 0),
                'sharpe': results.get('sharpe_ratio', 0),
                'max_dd': results.get('max_drawdown_r', 0),
                'profit_factor': results.get('profit_factor', 0),
                'total_trades': results.get('total_trades', 0),
            })

        # Rank by Sharpe ratio
        comparison['strategies'] = sorted(
            comparison['strategies'],
            key=lambda x: x['sharpe'],
            reverse=True
        )

        return comparison

    def generate_recommendations(self, analysis: Dict) -> List[str]:
        """
        Generate actionable recommendations based on analysis.

        Args:
            analysis: Analysis results from analyze_backtest

        Returns:
            List of recommendation strings
        """
        recommendations = []

        # Check Sharpe ratio
        sharpe = analysis['risk_metrics']['sharpe_ratio']
        if sharpe < 1.0:
            recommendations.append(
                f"⚠️  Sharpe ratio {sharpe:.2f} below 1.0. "
                "Actions: 1) Review entry filters, 2) Optimize position sizing, 3) Reduce trade frequency"
            )
        elif sharpe > 2.0:
            recommendations.append(
                f"✅ Excellent Sharpe {sharpe:.2f}. Consider: 1) Increase position sizing, 2) Deploy to live"
            )

        # Check win rate
        win_rate = analysis['summary']['win_rate']
        if win_rate < 0.50:
            recommendations.append(
                f"⚠️  Win rate {win_rate:.1%} below 50%. "
                "Actions: 1) Tighten entry criteria, 2) Review stop placement, 3) Trail profits sooner"
            )

        # Check profit factor
        pf = analysis['risk_metrics']['profit_factor']
        if pf < 1.5:
            recommendations.append(
                f"⚠️  Profit factor {pf:.2f} below 1.5. "
                "Actions: 1) Extend targets, 2) Cut losses faster, 3) Improve win rate"
            )
        elif pf > 2.0:
            recommendations.append(
                f"✅ Strong profit factor {pf:.2f}. System is robust."
            )

        # Check max drawdown
        max_dd = abs(analysis['drawdown_analysis']['max_drawdown_r'])
        if max_dd > 20:
            recommendations.append(
                f"🔴 Max drawdown {max_dd:.1f}R exceeds 20R. CRITICAL. "
                "Actions: 1) Reduce position sizes, 2) Add correlation filters, 3) Implement circuit breakers"
            )
        elif max_dd > 15:
            recommendations.append(
                f"⚠️  Max drawdown {max_dd:.1f}R above 15R. "
                "Actions: 1) Review worst losing streak, 2) Consider regime filters"
            )

        # Check expectancy
        expectancy = analysis['summary']['expectancy_r']
        if expectancy < 0.2:
            recommendations.append(
                f"⚠️  Low expectancy {expectancy:.2f}R. "
                "Actions: 1) Focus on high-probability setups, 2) Reduce trade count, 3) Improve R:R"
            )

        # Strategy-specific recommendations
        if 'strategy_attribution' in analysis:
            strat_attr = analysis['strategy_attribution']
            worst_strategies = sorted(strat_attr.items(), key=lambda x: x[1]['total_pnl_r'])[:3]

            for strat_name, metrics in worst_strategies:
                if metrics['total_pnl_r'] < -5.0:
                    recommendations.append(
                        f"🔴 Strategy '{strat_name}' lost {metrics['total_pnl_r']:.1f}R. "
                        "Consider: 1) Disable, 2) Optimize parameters, 3) Review regime fit"
                    )

        # Trade frequency
        total_trades = analysis['summary']['total_trades']
        if total_trades < 30:
            recommendations.append(
                f"⚠️  Only {total_trades} trades. Insufficient for statistical significance. "
                "Actions: 1) Extend backtest period, 2) Add more symbols, 3) Relax filters"
            )

        if not recommendations:
            recommendations.append(
                "✅ Performance metrics within acceptable parameters. System ready for paper trading."
            )

        return recommendations

    def _generate_summary(self, results: Dict) -> Dict:
        """Generate summary statistics."""
        return {
            'initial_capital': results['initial_capital'],
            'final_equity': results['final_equity'],
            'total_return_pct': results['total_return_pct'],
            'total_return_r': results['total_return_r'],
            'total_trades': results['total_trades'],
            'win_rate': results['win_rate'],
            'expectancy_r': results['expectancy_r'],
        }

    def _calculate_risk_metrics(self, trades_df: pd.DataFrame) -> Dict:
        """Calculate comprehensive risk metrics."""
        returns = trades_df['pnl_r'].values

        metrics = {
            'sharpe_ratio': self._sharpe(returns),
            'sortino_ratio': self._sortino(returns),
            'calmar_ratio': self._calmar(returns),
            'omega_ratio': self._omega(returns),
            'kappa_3_ratio': self._kappa_3(returns),
            'profit_factor': self._profit_factor(returns),
            'payoff_ratio': self._payoff_ratio(returns),
            'recovery_factor': self._recovery_factor(returns),
            'ulcer_index': self._ulcer_index(returns),
        }

        return metrics

    def _analyze_strategy_attribution(self, trades_df: pd.DataFrame) -> Dict:
        """Analyze performance by strategy."""
        attribution = {}

        for strategy, group in trades_df.groupby('strategy'):
            returns = group['pnl_r'].values

            attribution[strategy] = {
                'total_trades': len(group),
                'win_rate': (returns > 0).sum() / len(returns),
                'total_pnl_r': returns.sum(),
                'avg_pnl_r': returns.mean(),
                'sharpe': self._sharpe(returns),
                'profit_factor': self._profit_factor(returns),
                'max_win_r': returns.max(),
                'max_loss_r': returns.min(),
            }

        return attribution

    def _calculate_strategy_correlation(self, trades_df: pd.DataFrame) -> Dict:
        """Calculate correlation matrix between strategies."""
        # Pivot trades by strategy
        strategies = trades_df['strategy'].unique()

        if len(strategies) < 2:
            return {}

        # Create time-aligned returns matrix
        returns_matrix = {}

        for strategy in strategies:
            strategy_trades = trades_df[trades_df['strategy'] == strategy]
            returns_matrix[strategy] = strategy_trades.set_index('exit_time')['pnl_r']

        # Calculate correlation
        df_returns = pd.DataFrame(returns_matrix)
        corr_matrix = df_returns.corr()

        return corr_matrix.to_dict()

    def _analyze_drawdowns(self, returns: np.ndarray) -> Dict:
        """Detailed drawdown analysis."""
        cumulative = np.cumsum(returns)
        running_max = np.maximum.accumulate(cumulative)
        drawdown = cumulative - running_max

        # Find all drawdown periods
        in_drawdown = drawdown < 0
        drawdown_periods = []

        start_idx = None
        for i, is_dd in enumerate(in_drawdown):
            if is_dd and start_idx is None:
                start_idx = i
            elif not is_dd and start_idx is not None:
                # End of drawdown period
                dd_depth = drawdown[start_idx:i].min()
                dd_length = i - start_idx
                drawdown_periods.append({
                    'depth_r': dd_depth,
                    'length_trades': dd_length,
                    'start_idx': start_idx,
                    'end_idx': i
                })
                start_idx = None

        # Sort by depth
        drawdown_periods = sorted(drawdown_periods, key=lambda x: x['depth_r'])

        return {
            'max_drawdown_r': drawdown.min(),
            'current_drawdown_r': drawdown[-1],
            'num_drawdown_periods': len(drawdown_periods),
            'avg_drawdown_depth_r': np.mean([dd['depth_r'] for dd in drawdown_periods]) if drawdown_periods else 0,
            'avg_recovery_trades': np.mean([dd['length_trades'] for dd in drawdown_periods]) if drawdown_periods else 0,
            'top_5_drawdowns': drawdown_periods[:5],
        }

    def _analyze_trade_distribution(self, trades_df: pd.DataFrame) -> Dict:
        """Analyze win/loss distribution."""
        returns = trades_df['pnl_r'].values
        wins = returns[returns > 0]
        losses = returns[returns < 0]

        return {
            'avg_win_r': wins.mean() if len(wins) > 0 else 0,
            'avg_loss_r': losses.mean() if len(losses) > 0 else 0,
            'median_win_r': np.median(wins) if len(wins) > 0 else 0,
            'median_loss_r': np.median(losses) if len(losses) > 0 else 0,
            'largest_win_r': wins.max() if len(wins) > 0 else 0,
            'largest_loss_r': losses.min() if len(losses) > 0 else 0,
            'win_std': wins.std() if len(wins) > 0 else 0,
            'loss_std': losses.std() if len(losses) > 0 else 0,
            'skewness': stats.skew(returns),
            'kurtosis': stats.kurtosis(returns),
        }

    def _analyze_streaks(self, trades_df: pd.DataFrame) -> Dict:
        """Analyze winning and losing streaks."""
        returns = trades_df['pnl_r'].values
        is_win = returns > 0

        # Calculate streaks
        current_streak = 1
        max_win_streak = 0
        max_loss_streak = 0
        current_win_streak = 0
        current_loss_streak = 0

        for i in range(1, len(is_win)):
            if is_win[i] == is_win[i-1]:
                current_streak += 1
            else:
                if is_win[i-1]:
                    max_win_streak = max(max_win_streak, current_streak)
                else:
                    max_loss_streak = max(max_loss_streak, current_streak)
                current_streak = 1

        return {
            'max_win_streak': max_win_streak,
            'max_loss_streak': max_loss_streak,
            'current_streak': current_streak,
            'current_streak_type': 'win' if is_win[-1] else 'loss',
        }

    def _calculate_monthly_returns(self, trades_df: pd.DataFrame) -> Dict:
        """Calculate monthly return breakdown."""
        trades_df['exit_month'] = pd.to_datetime(trades_df['exit_time']).dt.to_period('M')

        monthly = trades_df.groupby('exit_month')['pnl_r'].agg([
            'count', 'sum', 'mean',
            lambda x: (x > 0).sum() / len(x)
        ])

        monthly.columns = ['trades', 'total_r', 'avg_r', 'win_rate']

        return monthly.to_dict('index')

    def _analyze_time_patterns(self, trades_df: pd.DataFrame) -> Dict:
        """Analyze performance by time of day, day of week."""
        trades_df['hour'] = pd.to_datetime(trades_df['entry_time']).dt.hour
        trades_df['day_of_week'] = pd.to_datetime(trades_df['entry_time']).dt.dayofweek

        hourly = trades_df.groupby('hour')['pnl_r'].agg(['count', 'mean', 'sum'])
        daily = trades_df.groupby('day_of_week')['pnl_r'].agg(['count', 'mean', 'sum'])

        return {
            'by_hour': hourly.to_dict('index'),
            'by_day_of_week': daily.to_dict('index'),
            'best_hour': hourly['sum'].idxmax() if len(hourly) > 0 else None,
            'worst_hour': hourly['sum'].idxmin() if len(hourly) > 0 else None,
            'best_day': daily['sum'].idxmax() if len(daily) > 0 else None,
            'worst_day': daily['sum'].idxmin() if len(daily) > 0 else None,
        }

    def _analyze_by_symbol(self, trades_df: pd.DataFrame) -> Dict:
        """Performance breakdown by symbol."""
        by_symbol = {}

        for symbol, group in trades_df.groupby('symbol'):
            returns = group['pnl_r'].values

            by_symbol[symbol] = {
                'trades': len(group),
                'win_rate': (returns > 0).sum() / len(returns),
                'total_r': returns.sum(),
                'avg_r': returns.mean(),
                'sharpe': self._sharpe(returns),
            }

        return by_symbol

    def _analyze_by_regime(self, trades_df: pd.DataFrame) -> Dict:
        """Performance breakdown by regime."""
        by_regime = {}

        for regime, group in trades_df.groupby('entry_regime'):
            returns = group['pnl_r'].values

            by_regime[regime] = {
                'trades': len(group),
                'win_rate': (returns > 0).sum() / len(returns),
                'total_r': returns.sum(),
                'avg_r': returns.mean(),
                'sharpe': self._sharpe(returns),
            }

        return by_regime

    # Risk metric calculations
    def _sharpe(self, returns: np.ndarray) -> float:
        """Sharpe ratio (annualized)."""
        if len(returns) == 0 or np.std(returns) == 0:
            return 0.0
        return np.mean(returns) / np.std(returns) * np.sqrt(252)

    def _sortino(self, returns: np.ndarray) -> float:
        """Sortino ratio (downside deviation)."""
        downside = returns[returns < 0]
        if len(downside) == 0 or np.std(downside) == 0:
            return 0.0
        return np.mean(returns) / np.std(downside) * np.sqrt(252)

    def _calmar(self, returns: np.ndarray) -> float:
        """Calmar ratio (return / max DD)."""
        cumulative = np.cumsum(returns)
        running_max = np.maximum.accumulate(cumulative)
        drawdown = cumulative - running_max
        max_dd = abs(drawdown.min())

        if max_dd == 0:
            return 0.0

        return returns.sum() / max_dd

    def _omega(self, returns: np.ndarray, threshold: float = 0.0) -> float:
        """Omega ratio (probability-weighted gains vs losses)."""
        gains = returns[returns > threshold].sum()
        losses = abs(returns[returns <= threshold].sum())

        if losses == 0:
            return float('inf') if gains > 0 else 0.0

        return gains / losses

    def _kappa_3(self, returns: np.ndarray) -> float:
        """Kappa 3 ratio (focuses on third moment)."""
        if len(returns) == 0:
            return 0.0

        downside = returns[returns < 0]
        if len(downside) == 0:
            return 0.0

        lpm3 = np.mean(downside ** 3)
        if lpm3 == 0:
            return 0.0

        return np.mean(returns) / (abs(lpm3) ** (1/3))

    def _profit_factor(self, returns: np.ndarray) -> float:
        """Profit factor (gross profit / gross loss)."""
        gross_profit = returns[returns > 0].sum()
        gross_loss = abs(returns[returns < 0].sum())

        if gross_loss == 0:
            return float('inf') if gross_profit > 0 else 0.0

        return gross_profit / gross_loss

    def _payoff_ratio(self, returns: np.ndarray) -> float:
        """Payoff ratio (avg win / avg loss)."""
        wins = returns[returns > 0]
        losses = returns[returns < 0]

        if len(losses) == 0:
            return float('inf') if len(wins) > 0 else 0.0

        return abs(wins.mean() / losses.mean())

    def _recovery_factor(self, returns: np.ndarray) -> float:
        """Recovery factor (total return / max DD)."""
        cumulative = np.cumsum(returns)
        running_max = np.maximum.accumulate(cumulative)
        drawdown = cumulative - running_max
        max_dd = abs(drawdown.min())

        if max_dd == 0:
            return 0.0

        return cumulative[-1] / max_dd

    def _ulcer_index(self, returns: np.ndarray) -> float:
        """Ulcer Index (RMS of drawdown)."""
        cumulative = np.cumsum(returns)
        running_max = np.maximum.accumulate(cumulative)
        drawdown_pct = (cumulative - running_max) / (running_max + 1e-10) * 100

        return np.sqrt(np.mean(drawdown_pct ** 2))

    def _save_analysis_report(self, analysis: Dict):
        """Save comprehensive analysis to JSON."""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filepath = self.output_dir / f"analysis_{timestamp}.json"

        try:
            with open(filepath, 'w') as f:
                json.dump(analysis, f, indent=2, default=str)

            self.logger.info(f"📄 Analysis report saved: {filepath}")
        except Exception as e:
            self.logger.error(f"Failed to save analysis: {e}")
