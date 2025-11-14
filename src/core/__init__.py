"""
Core institutional components.

Architecture:
- mtf_data_manager: Multi-timeframe data management
- risk_manager: Institutional risk management with statistical circuit breakers
- position_manager: Market structure-based position management
- regime_detector: Market regime detection and classification
- brain: Advanced orchestration layer
- ml_adaptive_engine: Machine Learning adaptive engine for continuous learning
"""

# MTF Data Manager requires MT5 (optional dependency)
try:
    from .mtf_data_manager import MultiTimeframeDataManager
except ImportError:
    MultiTimeframeDataManager = None

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
from .ml_adaptive_engine import (
    MLAdaptiveEngine,
    TradeMemoryDatabase,
    PerformanceAttributionAnalyzer,
    AdaptiveParameterOptimizer,
    TradeRecord,
    SignalRecord
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

    # ML Adaptive Engine
    'MLAdaptiveEngine',
    'TradeMemoryDatabase',
    'PerformanceAttributionAnalyzer',
    'AdaptiveParameterOptimizer',
    'TradeRecord',
    'SignalRecord',
]
