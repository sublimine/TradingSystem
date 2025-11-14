"""
Multi-Timeframe Context Engine

MANDATO 15: Implementación institucional de análisis multi-timeframe.

Componentes:
- HTFStructureAnalyzer: Análisis HTF (H4/D1) - estructura y key levels
- MTFContextValidator: Validación MTF (M15/M5) - zones y BOS
- LTFTimingExecutor: Timing LTF (M1) - entry triggers
- MultiFrameOrchestrator: Orquestador principal

Output: multiframe_score [0-1] y POIs para QualityScorer.
"""

from .htf_structure import HTFStructureAnalyzer
from .mtf_context import MTFContextValidator
from .ltf_timing import LTFTimingExecutor
from .orchestrator import MultiFrameOrchestrator

__all__ = [
    'HTFStructureAnalyzer',
    'MTFContextValidator',
    'LTFTimingExecutor',
    'MultiFrameOrchestrator'
]
