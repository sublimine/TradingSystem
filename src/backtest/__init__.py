"""
Institutional Backtest Engine - MANDATO 17

Motor de backtest institucional que ejecuta el sistema REAL:
- Estrategias â†’ Microestructura + Multiframe â†’ QualityScorer â†’ RiskManager â†’ PositionManager â†’ Reporting

NO versiÃ³n simplificada. Usa los mismos componentes que producciÃ³n.

Componentes:
- data_loader: Carga histÃ³ricos (CSV/MT5)
- engine: Orquestador del backtest
- runner: Loop de ejecuciÃ³n (candle por candle)

Respeta:
- 0-2% risk caps (config/risk_limits.yaml)
- SL/TP estructurales (sin indicadores de rango)
- Brain-layer governance
- ExecutionEventLogger para trazabilidad completa
"""

from .data_loader import BacktestDataLoader
from .engine import BacktestEngine
from .runner import BacktestRunner

__all__ = ['BacktestDataLoader', 'BacktestEngine', 'BacktestRunner']
