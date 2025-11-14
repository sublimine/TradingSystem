"""
Metrics - Cálculo de KPIs institucionales

Métricas:
- PnL y retornos
- Risk-adjusted (Sharpe, Sortino, Calmar, MAR)
- Drawdown analysis
- Trade stats (hit rate, payoff, expectancy, R múltiplos)
- Riesgo (realized vs allocated, concentration, factor crowding)
- Quality calibration (quality vs return correlation)
- Decay detection
- Slippage y execution

Mandato: MANDATO 11
Fecha: 2025-11-14
"""

import numpy as np
import pandas as pd
from typing import Dict, Tuple


# ========== PnL y Retornos ==========

def calculate_pnl_stats(trades: pd.DataFrame) -> Dict:
    """PnL bruto/neto, retorno %, vol anualizada."""
    if trades.empty:
        return {}

    pnl_gross = trades['pnl_gross'].sum()
    pnl_net = trades['pnl_net'].sum()
    returns = trades['pnl_gross'] / trades['position_size_usd']  # Retorno por trade
    return_pct = returns.mean() * 100
    vol_annualized = returns.std() * np.sqrt(252) * 100  # Asumiendo ~252 trading days

    return {
        'pnl_gross': pnl_gross,
        'pnl_net': pnl_net,
        'return_pct': return_pct,
        'vol_annualized': vol_annualized
    }


def calculate_equity_curve(trades: pd.DataFrame) -> pd.Series:
    """Curva de equity acumulada."""
    if trades.empty:
        return pd.Series()

    trades_sorted = trades.sort_values('timestamp')
    equity_curve = trades_sorted['pnl_gross'].cumsum()
    return equity_curve


# ========== Risk-Adjusted Metrics ==========

def calculate_sharpe_ratio(returns: pd.Series, risk_free_rate: float = 0.0) -> float:
    """Sharpe ratio."""
    if len(returns) == 0 or returns.std() == 0:
        return 0.0

    excess_returns = returns - risk_free_rate
    sharpe = excess_returns.mean() / returns.std()
    return sharpe * np.sqrt(252)  # Annualized


def calculate_sortino_ratio(returns: pd.Series, risk_free_rate: float = 0.0) -> float:
    """Sortino ratio (downside deviation)."""
    if len(returns) == 0:
        return 0.0

    excess_returns = returns - risk_free_rate
    downside_returns = returns[returns < 0]
    if len(downside_returns) == 0 or downside_returns.std() == 0:
        return 0.0

    sortino = excess_returns.mean() / downside_returns.std()
    return sortino * np.sqrt(252)


def calculate_calmar_ratio(returns: pd.Series, max_drawdown_pct: float) -> float:
    """Calmar ratio (annual return / max drawdown)."""
    if max_drawdown_pct == 0:
        return 0.0

    annual_return = returns.mean() * 252
    calmar = annual_return / abs(max_drawdown_pct)
    return calmar


def calculate_mar_ratio(returns: pd.Series, max_drawdown_pct: float) -> float:
    """MAR ratio (CAGR / max drawdown)."""
    if len(returns) == 0 or max_drawdown_pct == 0:
        return 0.0

    cagr = (1 + returns.mean()) ** 252 - 1
    mar = cagr / abs(max_drawdown_pct)
    return mar


# ========== Drawdown Analysis ==========

def calculate_drawdown(equity_curve: pd.Series) -> pd.Series:
    """Serie de drawdown."""
    if equity_curve.empty:
        return pd.Series()

    running_max = equity_curve.cummax()
    drawdown = (equity_curve - running_max) / running_max
    return drawdown


def calculate_max_drawdown(equity_curve: pd.Series) -> Dict:
    """
    Max DD: profundidad, duración, recuperación.

    MANDATO 17 FIX: Maneja correctamente índices DateTime y numéricos.
    Corrige bug 'numpy.int64' object has no attribute 'days'.
    """
    if equity_curve.empty:
        return {'max_dd_pct': 0, 'max_dd_duration_days': 0}

    drawdown = calculate_drawdown(equity_curve)
    max_dd = drawdown.min()

    # Duración del max DD
    dd_periods = (drawdown == max_dd)
    if dd_periods.any():
        dd_start = dd_periods.idxmax()
        dd_end_mask = (equity_curve.index > dd_start) & (drawdown >= 0)
        dd_end = equity_curve.index[dd_end_mask][0] if dd_end_mask.any() else equity_curve.index[-1]

        # MANDATO 17 FIX: Calcular duración según tipo de índice
        if isinstance(equity_curve.index, pd.DatetimeIndex):
            # Index de timestamps → calcular días
            dd_duration = (dd_end - dd_start).days
        else:
            # Index numérico (posiciones) → diferencia directa
            dd_duration = int(dd_end - dd_start)
    else:
        dd_duration = 0

    return {
        'max_dd_pct': max_dd * 100,
        'max_dd_duration_days': dd_duration
    }


# ========== Trade Stats ==========

def calculate_hit_rate(trades: pd.DataFrame) -> float:
    """Win rate (winning trades / total trades)."""
    if len(trades) == 0:
        return 0.0

    wins = (trades['pnl_gross'] > 0).sum()
    hit_rate = wins / len(trades)
    return hit_rate


def calculate_payoff_ratio(trades: pd.DataFrame) -> float:
    """Avg win / Avg loss."""
    wins = trades[trades['pnl_gross'] > 0]['pnl_gross']
    losses = trades[trades['pnl_gross'] <= 0]['pnl_gross'].abs()

    if len(wins) == 0 or len(losses) == 0 or losses.mean() == 0:
        return 0.0

    payoff = wins.mean() / losses.mean()
    return payoff


def calculate_expectancy(trades: pd.DataFrame) -> float:
    """(Win rate * Avg win) - (Loss rate * Avg loss)."""
    if len(trades) == 0:
        return 0.0

    wins = trades[trades['pnl_gross'] > 0]['pnl_gross']
    losses = trades[trades['pnl_gross'] <= 0]['pnl_gross'].abs()

    win_rate = len(wins) / len(trades)
    loss_rate = len(losses) / len(trades)

    avg_win = wins.mean() if len(wins) > 0 else 0
    avg_loss = losses.mean() if len(losses) > 0 else 0

    expectancy = (win_rate * avg_win) - (loss_rate * avg_loss)
    return expectancy


def calculate_avg_r_multiple(trades: pd.DataFrame) -> float:
    """Promedio de R múltiplos."""
    if 'r_multiple' not in trades.columns or len(trades) == 0:
        return 0.0

    return trades['r_multiple'].mean()


# ========== Riesgo ==========

def calculate_realized_risk_vs_allocated(trades: pd.DataFrame) -> Dict:
    """Comparar riesgo realmente perdido vs riesgo asignado."""
    if len(trades) == 0:
        return {'realized_risk_pct': 0, 'allocated_risk_pct': 0, 'utilization': 0}

    # Riesgo asignado = suma de risk_pct de todas las operaciones
    allocated_risk = trades['risk_pct'].sum()

    # Riesgo realizado = pérdidas reales como % del capital
    losses = trades[trades['pnl_gross'] < 0]
    realized_risk = losses['pnl_gross'].abs().sum() / trades['position_size_usd'].sum() * 100 if len(losses) > 0 else 0

    utilization = (realized_risk / allocated_risk * 100) if allocated_risk > 0 else 0

    return {
        'allocated_risk_pct': allocated_risk,
        'realized_risk_pct': realized_risk,
        'utilization_pct': utilization
    }


def calculate_risk_concentration(positions: pd.DataFrame) -> Dict:
    """Herfindahl index de exposición por símbolo/estrategia."""
    if positions.empty:
        return {'herfindahl_symbol': 0, 'herfindahl_strategy': 0}

    # Por símbolo
    symbol_exposure = positions.groupby('symbol')['risk_allocated_pct'].sum()
    symbol_shares = symbol_exposure / symbol_exposure.sum()
    herfindahl_symbol = (symbol_shares ** 2).sum()

    # Por estrategia
    strategy_exposure = positions.groupby('strategy_id')['risk_allocated_pct'].sum()
    strategy_shares = strategy_exposure / strategy_exposure.sum()
    herfindahl_strategy = (strategy_shares ** 2).sum()

    return {
        'herfindahl_symbol': herfindahl_symbol,
        'herfindahl_strategy': herfindahl_strategy
    }


def calculate_factor_crowding(strategies_pnl: pd.DataFrame) -> pd.DataFrame:
    """Matriz de correlación de PnL entre estrategias."""
    if strategies_pnl.empty:
        return pd.DataFrame()

    correlation_matrix = strategies_pnl.corr()
    return correlation_matrix


# ========== Quality Calibration ==========

def calculate_quality_vs_return_correlation(trades: pd.DataFrame) -> float:
    """Correlación entre QualityScore y retorno real."""
    if 'quality_score_total' not in trades.columns or len(trades) < 3:
        return 0.0

    correlation = trades['quality_score_total'].corr(trades['pnl_gross'])
    return correlation


def calculate_quality_distribution_by_outcome(trades: pd.DataFrame) -> Dict:
    """Distribución de QualityScore para wins vs losses."""
    if 'quality_score_total' not in trades.columns or len(trades) == 0:
        return {}

    wins = trades[trades['pnl_gross'] > 0]['quality_score_total']
    losses = trades[trades['pnl_gross'] <= 0]['quality_score_total']

    return {
        'wins_avg_quality': wins.mean() if len(wins) > 0 else 0,
        'losses_avg_quality': losses.mean() if len(losses) > 0 else 0,
        'quality_gap': (wins.mean() - losses.mean()) if len(wins) > 0 and len(losses) > 0 else 0
    }


# ========== Decay Detection ==========

def detect_strategy_decay(strategy_performance: pd.DataFrame, lookback_window: int = 90) -> Dict:
    """Señales de decay: hit rate cayendo, Sharpe bajando, etc."""
    if len(strategy_performance) < 2:
        return {'decay_detected': False, 'signals': []}

    recent = strategy_performance.tail(lookback_window)
    older = strategy_performance.head(len(strategy_performance) - lookback_window)

    decay_signals = []

    # Hit rate cayendo >10%
    if recent['hit_rate'].mean() < older['hit_rate'].mean() - 0.10:
        decay_signals.append('HIT_RATE_DROP')

    # Sharpe cayendo >0.5
    if recent['sharpe_ratio'].mean() < older['sharpe_ratio'].mean() - 0.5:
        decay_signals.append('SHARPE_DROP')

    # Max DD increasing
    if recent['max_drawdown_pct'].max() > older['max_drawdown_pct'].max() * 1.5:
        decay_signals.append('DRAWDOWN_INCREASE')

    return {
        'decay_detected': len(decay_signals) > 0,
        'signals': decay_signals
    }


# ========== Slippage ==========

def calculate_slippage_stats(trades: pd.DataFrame) -> Dict:
    """Slippage promedio, outliers, por símbolo."""
    if 'slippage_bps' not in trades.columns or len(trades) == 0:
        return {}

    return {
        'avg_slippage_bps': trades['slippage_bps'].mean(),
        'max_slippage_bps': trades['slippage_bps'].max(),
        'outliers_count': (trades['slippage_bps'] > trades['slippage_bps'].quantile(0.95)).sum()
    }
