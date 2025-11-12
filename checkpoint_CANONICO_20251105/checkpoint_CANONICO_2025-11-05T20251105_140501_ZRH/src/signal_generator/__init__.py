"""
Strategies package initialization.

This package contains all trading strategy implementations that generate signals
based on market data and calculated features.
"""

from .strategy_base import StrategyBase, Signal
from .liquidity_sweep import LiquiditySweepStrategy
from .order_flow_toxicity import OrderFlowToxicityStrategy
from .kalman_pairs_trading import KalmanPairsTrading

__all__ = [
    'StrategyBase',
    'Signal',
    'LiquiditySweepStrategy',
    'OrderFlowToxicityStrategy',
    'KalmanPairsTrading'
]