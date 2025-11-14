"""
Microstructure package - Volume-based market microstructure analysis.

Components:
- VPINEstimator: Volume-Synchronized Probability of Informed Trading
- OrderFlowAnalyzer: Order Flow Imbalance calculation
- MicrostructureEngine: Composite microstructure scoring

Usage:
    from src.microstructure import MicrostructureEngine

    engine = MicrostructureEngine(config)
    engine.update_trades(symbol, trades)
    score = engine.get_microstructure_score(symbol)
"""

from .vpin import VPINEstimator
from .order_flow import OrderFlowAnalyzer
from .engine import MicrostructureEngine

__all__ = [
    'VPINEstimator',
    'OrderFlowAnalyzer',
    'MicrostructureEngine',
]
