"""
Microstructure Engine - Institutional Market Microstructure Analysis

MANDATO 15: Implementación real de análisis de microestructura.

Componentes:
- VPINEstimator: Volume-Synchronized Probability of Informed Trading
- OrderFlowAnalyzer: Order Flow Imbalance (OFI) analysis
- Level2DepthMonitor: Book depth and liquidity analysis
- SpoofingDetector: Detection of manipulation patterns
- MicrostructureEngine: Main orchestrator

Research basis:
- Easley, López de Prado, O'Hara (2012): Flow Toxicity and Liquidity
- Lee & Ready (1991): Inferring Trade Direction
- Cartea, Jaimungal, Penalva (2015): Algorithmic and HFT
"""

from .vpin import VPINEstimator
from .order_flow import OrderFlowAnalyzer
from .depth import Level2DepthMonitor
from .spoofing import SpoofingDetector
from .engine import MicrostructureEngine

__all__ = [
    'VPINEstimator',
    'OrderFlowAnalyzer',
    'Level2DepthMonitor',
    'SpoofingDetector',
    'MicrostructureEngine'
]
