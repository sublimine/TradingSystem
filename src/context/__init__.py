"""
Context package - Multi-timeframe context analysis.

Components:
- HTFStructureAnalyzer: High timeframe structure (H4/D1)
- MTFContextValidator: Medium timeframe validation (M15/M5)
- MultiFrameOrchestrator: Multi-timeframe synthesis

Usage:
    from src.context import MultiFrameOrchestrator

    orchestrator = MultiFrameOrchestrator(config)
    result = orchestrator.analyze_multiframe(symbol, htf_ohlcv, mtf_ohlcv, current_price)
    multiframe_score = result['multiframe_score']
"""

from .htf_analyzer import HTFStructureAnalyzer
from .mtf_validator import MTFContextValidator
from .orchestrator import MultiFrameOrchestrator

__all__ = [
    'HTFStructureAnalyzer',
    'MTFContextValidator',
    'MultiFrameOrchestrator',
]
