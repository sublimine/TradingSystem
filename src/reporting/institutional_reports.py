"""
Institutional Reporting System - Elite Performance Analytics

Generates comprehensive institutional-grade reports:
- Daily performance summary
- Weekly analysis with strategy attribution
- Monthly metrics and optimization recommendations
- Quarterly review with regime analysis
- Annual statistics and year-over-year comparison

Research Basis:
- Institutional risk management standards (Basel III)
- Sharpe (1966): Risk-adjusted performance
- Sortino (1994): Downside risk metrics
- Calmar (1991): Drawdown-adjusted returns

Author: Elite Trading System
Version: 1.0
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
from pathlib import Path
import json
import logging

logger = logging.getLogger(__name__)


class InstitutionalReportingSystem:
    """
    Generate institutional-grade performance reports.

    Reports include:
    - Performance metrics (Sharpe, Sortino, Calmar)
    - Strategy attribution
    - Risk metrics (VaR, CVaR, Max DD)
    - Trade analysis (win rate, profit factor, R-expectancy)
    - Regime performance breakdown
    - Recommendations for optimization
    """

    def __init__(self, output_dir: str = 'reports/'):
        """
        Initialize reporting system.

        Args:
            output_dir: Directory to save reports
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        self.logger = logging.getLogger(self.__class__.__name__)

    def generate_daily_report(self, trades: List[Dict], date: datetime) -> Dict:
        """
        Generate daily performance report.

        Args:
            trades: List of trades executed today
            date: Report date

        Returns:
            Dict with daily metrics
        """
        if not trades:
            return {
                'date': date.strftime('%Y-%m-%d'),
                'total_trades': 0,
                'message': 'No trades executed today'
            }

        df = pd.DataFrame(trades)

        report = {
            'date': date.strftime('%Y-%m-%d'),
            'total_trades': len(df),
            'winning_trades': len(df[df['pnl_r'] > 0]),
            'losing_trades': len(df[df['pnl_r'] < 0]),
            'win_rate': len(df[df['pnl_r'] > 0]) / len(df) if len(df) > 0 else 0,
            'total_pnl_r': df['pnl_r'].sum(),
            'avg_win_r': df[df['pnl_r'] > 0]['pnl_r'].mean() if len(df[df['pnl_r'] > 0]) > 0 else 0,
            'avg_loss_r': df[df['pnl_r'] < 0]['pnl_r'].mean() if len(df[df['pnl_r'] < 0]) > 0 else 0,
            'largest_win_r': df['pnl_r'].max(),
            'largest_loss_r': df['pnl_r'].min(),
            'expectancy_r': df['pnl_r'].mean(),
        }

        # Strategy breakdown
        strategy_pnl = df.groupby('strategy')['pnl_r'].agg(['count', 'sum', 'mean']).to_dict('index')
        report['strategy_breakdown'] = strategy_pnl

        # Save to file
        self._save_report(report, f"daily_{date.strftime('%Y%m%d')}.json")

        self.logger.info(f"📊 Daily report generated: {len(df)} trades, {report['total_pnl_r']:.2f}R")

        return report

    def generate_weekly_report(self, trades: List[Dict], week_end: datetime) -> Dict:
        """
        Generate weekly performance report with deeper analysis.

        Args:
            trades: List of trades from past week
            week_end: Week ending date

        Returns:
            Dict with weekly metrics
        """
        if not trades:
            return {
                'week_ending': week_end.strftime('%Y-%m-%d'),
                'total_trades': 0,
                'message': 'No trades this week'
            }

        df = pd.DataFrame(trades)

        # Basic metrics
        report = {
            'week_ending': week_end.strftime('%Y-%m-%d'),
            'total_trades': len(df),
            'winning_trades': len(df[df['pnl_r'] > 0]),
            'losing_trades': len(df[df['pnl_r'] < 0]),
            'win_rate': len(df[df['pnl_r'] > 0]) / len(df) if len(df) > 0 else 0,
            'total_pnl_r': df['pnl_r'].sum(),
            'expectancy_r': df['pnl_r'].mean(),
        }

        # Risk metrics
        if len(df) > 0:
            returns = df['pnl_r'].values
            report['sharpe_ratio'] = self._calculate_sharpe(returns)
            report['sortino_ratio'] = self._calculate_sortino(returns)
            report['max_drawdown_r'] = self._calculate_max_dd(returns)
            report['profit_factor'] = self._calculate_profit_factor(returns)

        # Strategy attribution
        strategy_metrics = df.groupby('strategy').agg({
            'pnl_r': ['count', 'sum', 'mean'],
        }).to_dict()
        report['strategy_attribution'] = strategy_metrics

        # Best/worst trades
        report['best_trade'] = {
            'strategy': df.loc[df['pnl_r'].idxmax(), 'strategy'],
            'symbol': df.loc[df['pnl_r'].idxmax(), 'symbol'],
            'pnl_r': df['pnl_r'].max()
        }
        report['worst_trade'] = {
            'strategy': df.loc[df['pnl_r'].idxmin(), 'strategy'],
            'symbol': df.loc[df['pnl_r'].idxmin(), 'symbol'],
            'pnl_r': df['pnl_r'].min()
        }

        self._save_report(report, f"weekly_{week_end.strftime('%Y%m%d')}.json")

        self.logger.info(f"📊 Weekly report: {report['total_pnl_r']:.2f}R, "
                        f"Sharpe={report.get('sharpe_ratio', 0):.2f}")

        return report

    def generate_monthly_report(self, trades: List[Dict], month_end: datetime) -> Dict:
        """
        Generate monthly report with optimization recommendations.

        Args:
            trades: List of trades from past month
            month_end: Month ending date

        Returns:
            Dict with monthly metrics and recommendations
        """
        if not trades:
            return {
                'month_ending': month_end.strftime('%Y-%m'),
                'total_trades': 0,
                'message': 'No trades this month'
            }

        df = pd.DataFrame(trades)

        # Comprehensive metrics
        report = {
            'month_ending': month_end.strftime('%Y-%m'),
            'total_trades': len(df),
            'win_rate': len(df[df['pnl_r'] > 0]) / len(df) if len(df) > 0 else 0,
            'total_pnl_r': df['pnl_r'].sum(),
            'expectancy_r': df['pnl_r'].mean(),
            'sharpe_ratio': self._calculate_sharpe(df['pnl_r'].values),
            'sortino_ratio': self._calculate_sortino(df['pnl_r'].values),
            'calmar_ratio': self._calculate_calmar(df['pnl_r'].values),
            'max_drawdown_r': self._calculate_max_dd(df['pnl_r'].values),
            'profit_factor': self._calculate_profit_factor(df['pnl_r'].values),
        }

        # Strategy performance ranking
        strategy_performance = df.groupby('strategy').agg({
            'pnl_r': ['count', 'sum', 'mean', lambda x: (x > 0).sum() / len(x)]
        }).sort_values(('pnl_r', 'sum'), ascending=False)

        report['top_strategies'] = strategy_performance.head(5).to_dict()
        report['worst_strategies'] = strategy_performance.tail(3).to_dict()

        # Regime analysis
        if 'entry_regime' in df.columns:
            regime_performance = df.groupby('entry_regime')['pnl_r'].agg(['count', 'sum', 'mean'])
            report['regime_performance'] = regime_performance.to_dict()

        # Recommendations
        report['recommendations'] = self._generate_recommendations(df)

        self._save_report(report, f"monthly_{month_end.strftime('%Y%m')}.json")

        self.logger.info(f"📊 Monthly report: {report['total_pnl_r']:.2f}R, "
                        f"Sharpe={report['sharpe_ratio']:.2f}, "
                        f"Win Rate={report['win_rate']:.1%}")

        return report

    def generate_quarterly_report(self, trades: List[Dict], quarter_end: datetime) -> Dict:
        """
        Generate quarterly strategic review.

        Args:
            trades: List of trades from past quarter
            quarter_end: Quarter ending date

        Returns:
            Dict with quarterly analysis
        """
        # Similar to monthly but with more strategic insights
        df = pd.DataFrame(trades) if trades else pd.DataFrame()

        if df.empty:
            return {'quarter_ending': quarter_end.strftime('%Y-Q%q'), 'message': 'No data'}

        # Calculate quarter number
        quarter = (quarter_end.month - 1) // 3 + 1

        report = {
            'quarter_ending': f"{quarter_end.year}-Q{quarter}",
            'total_trades': len(df),
            'total_pnl_r': df['pnl_r'].sum(),
            'sharpe_ratio': self._calculate_sharpe(df['pnl_r'].values),
            'max_drawdown_r': self._calculate_max_dd(df['pnl_r'].values),
        }

        # Strategic insights
        report['strategic_insights'] = {
            'most_profitable_month': df.groupby(pd.to_datetime(df['entry_time']).dt.to_period('M'))['pnl_r'].sum().idxmax(),
            'most_active_strategy': df['strategy'].value_counts().idxmax(),
            'avg_trade_duration_minutes': df['duration_minutes'].mean(),
        }

        self._save_report(report, f"quarterly_{quarter_end.year}_Q{quarter}.json")

        return report

    def generate_annual_report(self, trades: List[Dict], year: int) -> Dict:
        """
        Generate annual comprehensive review.

        Args:
            trades: List of all trades from year
            year: Report year

        Returns:
            Dict with annual metrics
        """
        df = pd.DataFrame(trades) if trades else pd.DataFrame()

        if df.empty:
            return {'year': year, 'message': 'No data'}

        report = {
            'year': year,
            'total_trades': len(df),
            'total_pnl_r': df['pnl_r'].sum(),
            'win_rate': (df['pnl_r'] > 0).sum() / len(df),
            'sharpe_ratio': self._calculate_sharpe(df['pnl_r'].values),
            'sortino_ratio': self._calculate_sortino(df['pnl_r'].values),
            'calmar_ratio': self._calculate_calmar(df['pnl_r'].values),
            'max_drawdown_r': self._calculate_max_dd(df['pnl_r'].values),
            'profit_factor': self._calculate_profit_factor(df['pnl_r'].values),
        }

        # Year-over-year comparison (if previous year data available)
        # This would require loading previous year data

        # Monthly breakdown
        df['month'] = pd.to_datetime(df['entry_time']).dt.to_period('M')
        monthly_pnl = df.groupby('month')['pnl_r'].sum()
        report['monthly_pnl'] = monthly_pnl.to_dict()

        self._save_report(report, f"annual_{year}.json")

        self.logger.info(f"📊 Annual report {year}: {report['total_pnl_r']:.2f}R, "
                        f"Sharpe={report['sharpe_ratio']:.2f}")

        return report

    def _calculate_sharpe(self, returns: np.ndarray, risk_free_rate: float = 0.0) -> float:
        """Calculate Sharpe ratio."""
        if len(returns) == 0:
            return 0.0

        excess_returns = returns - risk_free_rate
        if np.std(returns) == 0:
            return 0.0

        return np.mean(excess_returns) / np.std(returns) * np.sqrt(252)  # Annualized

    def _calculate_sortino(self, returns: np.ndarray, risk_free_rate: float = 0.0) -> float:
        """Calculate Sortino ratio (downside deviation)."""
        if len(returns) == 0:
            return 0.0

        excess_returns = returns - risk_free_rate
        downside_returns = returns[returns < 0]

        if len(downside_returns) == 0 or np.std(downside_returns) == 0:
            return 0.0

        return np.mean(excess_returns) / np.std(downside_returns) * np.sqrt(252)

    def _calculate_calmar(self, returns: np.ndarray) -> float:
        """Calculate Calmar ratio (return / max drawdown)."""
        if len(returns) == 0:
            return 0.0

        max_dd = abs(self._calculate_max_dd(returns))
        if max_dd == 0:
            return 0.0

        return np.sum(returns) / max_dd

    def _calculate_max_dd(self, returns: np.ndarray) -> float:
        """Calculate maximum drawdown in R."""
        if len(returns) == 0:
            return 0.0

        cumulative = np.cumsum(returns)
        running_max = np.maximum.accumulate(cumulative)
        drawdown = cumulative - running_max

        return np.min(drawdown)

    def _calculate_profit_factor(self, returns: np.ndarray) -> float:
        """Calculate profit factor (gross profit / gross loss)."""
        if len(returns) == 0:
            return 0.0

        gross_profit = np.sum(returns[returns > 0])
        gross_loss = abs(np.sum(returns[returns < 0]))

        if gross_loss == 0:
            return float('inf') if gross_profit > 0 else 0.0

        return gross_profit / gross_loss

    def _generate_recommendations(self, df: pd.DataFrame) -> List[str]:
        """
        Generate optimization recommendations based on trade data.

        Args:
            df: DataFrame of trades

        Returns:
            List of recommendation strings
        """
        recommendations = []

        # Check win rate
        win_rate = (df['pnl_r'] > 0).sum() / len(df)
        if win_rate < 0.55:
            recommendations.append(
                f"⚠️  Win rate below 55% ({win_rate:.1%}). Consider: "
                "1) Tighten entry filters, 2) Review stop placement, 3) Reduce strategy count"
            )

        # Check profit factor
        pf = self._calculate_profit_factor(df['pnl_r'].values)
        if pf < 1.5:
            recommendations.append(
                f"⚠️  Profit factor below 1.5 ({pf:.2f}). Consider: "
                "1) Extend targets, 2) Trail stops more aggressively, 3) Cut losses faster"
            )

        # Check worst strategies
        strategy_pnl = df.groupby('strategy')['pnl_r'].sum().sort_values()
        if len(strategy_pnl) > 0 and strategy_pnl.iloc[0] < -5.0:
            worst_strategy = strategy_pnl.index[0]
            recommendations.append(
                f"🔴 Strategy '{worst_strategy}' lost {strategy_pnl.iloc[0]:.1f}R. "
                "Consider: 1) Disable temporarily, 2) Review parameters, 3) Analyze regime fit"
            )

        # Check max drawdown
        max_dd = abs(self._calculate_max_dd(df['pnl_r'].values))
        if max_dd > 20.0:
            recommendations.append(
                f"⚠️  Max drawdown {max_dd:.1f}R exceeds 20R. Consider: "
                "1) Reduce position sizes, 2) Add correlation filters, 3) Strengthen regime detection"
            )

        if not recommendations:
            recommendations.append("✅ Performance within acceptable parameters. Continue monitoring.")

        return recommendations

    def _save_report(self, report: Dict, filename: str):
        """Save report to JSON file."""
        filepath = self.output_dir / filename

        try:
            with open(filepath, 'w') as f:
                json.dump(report, f, indent=2, default=str)

            self.logger.debug(f"Report saved: {filepath}")
        except Exception as e:
            self.logger.error(f"Failed to save report: {e}")
