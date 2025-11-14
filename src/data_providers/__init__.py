"""
MANDATO 20 - Data Providers Module

Proveedores de datos institucionales para backtesting y calibración.

Proveedores disponibles:
- MT5DataClient: Descarga históricos desde MetaTrader 5
- (Futuro) AlphaVantageClient, YahooFinanceClient, etc.

Autor: SUBLIMINE Institutional Trading System
Fecha: 2025-11-14
Mandato: MANDATO 20 - Data Pipeline Institucional
"""

__all__ = ['MT5DataClient']

from .mt5_data_client import MT5DataClient
