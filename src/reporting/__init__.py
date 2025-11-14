"""
Reporting Engine Institucional - SUBLIMINE TradingSystem

Módulos:
- event_logger: ExecutionEventLogger (log de trades en tiempo real)
- aggregators: Agregación de datos por fecha/estrategia/símbolo/clase
- metrics: Cálculo de KPIs institucionales (Sharpe, Sortino, DD, etc.)
- generators: Generación de informes (diario/semanal/mensual/trimestral/anual)

Mandato: MANDATO 11
Fecha: 2025-11-14
"""

__version__ = "1.0.0"
__all__ = ["ExecutionEventLogger", "aggregators", "metrics", "generators"]
