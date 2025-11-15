"""
Microstructure Module - MANDATO 24

Componentes de análisis de microestructura de mercado:
- MicrostructureEngine: Motor centralizado de feature calculation
- Level2DepthMonitor: Monitor de profundidad L2 (TODO - MANDATO 25)
- SpoofingDetector: Detector de spoofing L2 (TODO - MANDATO 25)

Author: SUBLIMINE Institutional Trading System
Date: 2025-11-15
Version: 1.0
"""

from .engine import (
    MicrostructureEngine,
    MicrostructureFeatures
)

__all__ = [
    'MicrostructureEngine',
    'MicrostructureFeatures'
]
