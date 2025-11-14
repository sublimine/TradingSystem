"""
Institutional Backtest Engine - MANDATO 17

Motor de backtest institucional que ejecuta el sistema REAL:
- Estrategias → Microestructura + Multiframe → QualityScorer → RiskManager → PositionManager → Reporting

NO versión simplificada. Usa los mismos componentes que producción.

Componentes:
- data_loader: Carga históricos (CSV/MT5)
- engine: Orquestador del backtest
- runner: Loop de ejecución (candle por candle)

Respeta:
- 0-2% risk caps (config/risk_limits.yaml)
- SL/TP estructurales (NO ATR)
- Brain-layer governance
- ExecutionEventLogger para trazabilidad completa
"""

from .data_loader import BacktestDataLoader
from .engine import BacktestEngine
from .runner import BacktestRunner

__all__ = ['BacktestDataLoader', 'BacktestEngine', 'BacktestRunner']
