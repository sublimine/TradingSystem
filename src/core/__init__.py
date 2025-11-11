"""
Core institutional components.

Architecture:
- mtf_data_manager: Multi-timeframe data management
- risk_manager: Institutional risk management with statistical circuit breakers
- position_manager: Market structure-based position management
- regime_detector: Market regime detection and classification
- brain: Advanced orchestration layer
"""

from .mtf_data_manager import MultiTimeframeDataManager
from .risk_manager import (
    InstitutionalRiskManager,
    QualityScorer,
    StatisticalCircuitBreaker
)
from .position_manager import (
    MarketStructurePositionManager,
    PositionTracker,
    StructureLevel
)
from .regime_detector import (
    RegimeDetector,
    RegimeBasedRiskAdjuster
)
from .brain import (
    InstitutionalBrain,
    SignalArbitrator,
    PortfolioOrchestrator
)

__all__ = [
    # MTF Data
    'MultiTimeframeDataManager',

    # Risk Management
    'InstitutionalRiskManager',
    'QualityScorer',
    'StatisticalCircuitBreaker',

    # Position Management
    'MarketStructurePositionManager',
    'PositionTracker',
    'StructureLevel',

    # Regime Detection
    'RegimeDetector',
    'RegimeBasedRiskAdjuster',

    # Brain
    'InstitutionalBrain',
    'SignalArbitrator',
    'PortfolioOrchestrator',
]
