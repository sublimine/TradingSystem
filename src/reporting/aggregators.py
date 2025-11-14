"""
Aggregators - Agregación de datos de trading por dimensiones

Funciones para agrupar trades/positions/risk por:
- Fecha
- Estrategia
- Símbolo
- Clase de activo
- Región
- Cluster de riesgo
- Régimen de volatilidad

Mandato: MANDATO 11
Fecha: 2025-11-14
"""

import pandas as pd
from datetime import datetime
from typing import List, Dict


def aggregate_by_date(trades: pd.DataFrame) -> pd.DataFrame:
    """Agregar trades por fecha (PnL diario, trades count, etc.)."""
    if trades.empty:
        return pd.DataFrame()

    daily = trades.groupby(trades['timestamp'].dt.date).agg({
        'pnl_gross': ['sum', 'mean', 'std'],
        'pnl_net': 'sum',
        'trade_id': 'count',
        'r_multiple': 'mean',
        'quality_score_total': 'mean',
        'risk_pct': 'mean'
    })

    daily.columns = ['pnl_gross_sum', 'pnl_gross_mean', 'pnl_gross_std',
                     'pnl_net_sum', 'trade_count', 'avg_r_multiple',
                     'avg_quality_score', 'avg_risk_pct']

    # Calcular wins/losses
    wins = trades[trades['pnl_gross'] > 0].groupby(trades['timestamp'].dt.date).size()
    losses = trades[trades['pnl_gross'] <= 0].groupby(trades['timestamp'].dt.date).size()
    daily['wins'] = wins
    daily['losses'] = losses
    daily['hit_rate'] = daily['wins'] / daily['trade_count']

    return daily


def aggregate_by_strategy(trades: pd.DataFrame) -> pd.DataFrame:
    """Agregar por estrategia (PnL, hit rate, avg risk, etc.)."""
    if trades.empty:
        return pd.DataFrame()

    strategy = trades.groupby('strategy_name').agg({
        'pnl_gross': ['sum', 'mean', 'std', 'count'],
        'pnl_net': 'sum',
        'r_multiple': 'mean',
        'quality_score_total': 'mean',
        'risk_pct': 'mean',
        'holding_time_minutes': 'mean'
    })

    strategy.columns = ['pnl_gross_sum', 'pnl_gross_mean', 'pnl_gross_std', 'trade_count',
                        'pnl_net_sum', 'avg_r_multiple', 'avg_quality_score',
                        'avg_risk_pct', 'avg_holding_time']

    # Wins/losses por estrategia
    for strategy_name in strategy.index:
        strat_trades = trades[trades['strategy_name'] == strategy_name]
        wins = (strat_trades['pnl_gross'] > 0).sum()
        losses = (strat_trades['pnl_gross'] <= 0).sum()
        strategy.loc[strategy_name, 'wins'] = wins
        strategy.loc[strategy_name, 'losses'] = losses
        strategy.loc[strategy_name, 'hit_rate'] = wins / len(strat_trades) if len(strat_trades) > 0 else 0

    return strategy


def aggregate_by_symbol(trades: pd.DataFrame) -> pd.DataFrame:
    """Agregar por símbolo."""
    if trades.empty:
        return pd.DataFrame()

    symbol = trades.groupby('symbol').agg({
        'pnl_gross': ['sum', 'count'],
        'pnl_net': 'sum',
        'r_multiple': 'mean',
        'risk_pct': 'mean'
    })

    symbol.columns = ['pnl_gross_sum', 'trade_count', 'pnl_net_sum',
                      'avg_r_multiple', 'avg_risk_pct']

    return symbol


def aggregate_by_asset_class(trades: pd.DataFrame) -> pd.DataFrame:
    """Agregar por clase de activo (FX/INDEX/COMMODITY/CRYPTO)."""
    if trades.empty:
        return pd.DataFrame()

    asset_class = trades.groupby('asset_class').agg({
        'pnl_gross': ['sum', 'count'],
        'risk_pct': 'sum',
        'r_multiple': 'mean'
    })

    asset_class.columns = ['pnl_gross_sum', 'trade_count', 'total_risk_pct', 'avg_r_multiple']

    return asset_class


def aggregate_by_risk_cluster(trades: pd.DataFrame) -> pd.DataFrame:
    """Agregar por cluster de riesgo (order_flow, liquidity, pairs, etc.)."""
    if trades.empty:
        return pd.DataFrame()

    cluster = trades.groupby('risk_cluster').agg({
        'pnl_gross': ['sum', 'count'],
        'risk_pct': 'sum',
        'quality_score_total': 'mean'
    })

    cluster.columns = ['pnl_gross_sum', 'trade_count', 'total_risk_pct', 'avg_quality_score']

    return cluster


def aggregate_by_regime(trades: pd.DataFrame) -> pd.DataFrame:
    """Agregar por régimen de volatilidad."""
    if trades.empty:
        return pd.DataFrame()

    regime = trades.groupby('regime').agg({
        'pnl_gross': ['sum', 'count', 'mean'],
        'r_multiple': 'mean',
        'quality_score_total': 'mean'
    })

    regime.columns = ['pnl_gross_sum', 'trade_count', 'pnl_gross_mean',
                      'avg_r_multiple', 'avg_quality_score']

    return regime
