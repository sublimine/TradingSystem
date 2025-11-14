"""
Order Flow Analyzer - Análisis de presión compradora/vendedora

Calcula Order Flow Imbalance (OFI) en ventana deslizante temporal.
OFI positivo → presión compradora neta.
OFI negativo → presión vendedora neta.

Implementación basada en investigación de flujo de órdenes institucional.
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Optional
from collections import deque
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)


class OrderFlowAnalyzer:
    """
    Analiza desequilibrio de flujo de órdenes en ventana temporal.

    OFI (Order Flow Imbalance):
    OFI_t = (V_buy - V_sell) / (V_buy + V_sell)

    Valores:
    - OFI ∈ [-1, 1]
    - OFI > 0.3 → Presión compradora fuerte
    - OFI < -0.3 → Presión vendedora fuerte
    - -0.3 ≤ OFI ≤ 0.3 → Flujo balanceado
    """

    def __init__(self, config: Dict):
        """
        Inicializar analizador de order flow.

        Args:
            config: {
                'window_seconds': int - Ventana temporal para OFI (default: 60),
                'min_trades': int - Mínimo de trades para cálculo válido (default: 5)
            }
        """
        self.window_seconds = config.get('window_seconds', 60)
        self.min_trades = config.get('min_trades', 5)

        # Estado interno por símbolo
        self.trade_history = {}  # {symbol: deque of {timestamp, side, volume}}

        logger.info(f"OrderFlowAnalyzer initialized: window={self.window_seconds}s, "
                   f"min_trades={self.min_trades}")

    def update(self, symbol: str, trades: List[Dict]):
        """
        Actualiza historial de trades para OFI.

        Args:
            trades: Lista de trades [{timestamp, side, volume}, ...]
                   side debe ser 'BUY' o 'SELL'
        """
        if symbol not in self.trade_history:
            self.trade_history[symbol] = deque()

        current_time = datetime.now()

        for trade in trades:
            self.trade_history[symbol].append({
                'timestamp': trade.get('timestamp', current_time),
                'side': trade['side'],
                'volume': trade['volume']
            })

        # Limpiar trades fuera de ventana
        self._cleanup_old_trades(symbol, current_time)

    def _cleanup_old_trades(self, symbol: str, current_time: datetime):
        """Elimina trades fuera de la ventana temporal."""
        if symbol not in self.trade_history:
            return

        cutoff_time = current_time - timedelta(seconds=self.window_seconds)
        history = self.trade_history[symbol]

        while history and history[0]['timestamp'] < cutoff_time:
            history.popleft()

    def calculate_ofi(self, symbol: str) -> Optional[float]:
        """
        Calcula Order Flow Imbalance actual.

        OFI = (V_buy - V_sell) / (V_buy + V_sell)

        Returns:
            OFI ∈ [-1, 1] o None si no hay suficientes datos
        """
        if symbol not in self.trade_history:
            return None

        history = list(self.trade_history[symbol])

        if len(history) < self.min_trades:
            return None

        buy_volume = sum(t['volume'] for t in history if t['side'] == 'BUY')
        sell_volume = sum(t['volume'] for t in history if t['side'] == 'SELL')

        total_volume = buy_volume + sell_volume
        if total_volume == 0:
            return 0.0

        ofi = (buy_volume - sell_volume) / total_volume
        return np.clip(ofi, -1.0, 1.0)

    def get_ofi(self, symbol: str) -> float:
        """
        Obtiene OFI actual (o valor por defecto).

        Returns:
            OFI ∈ [-1, 1], default 0.0 si no hay datos
        """
        ofi = self.calculate_ofi(symbol)
        return ofi if ofi is not None else 0.0

    def interpret_ofi(self, ofi: float) -> str:
        """
        Interpreta nivel de OFI.

        Returns:
            'STRONG_BUY' (>0.3), 'BALANCED' (±0.3), 'STRONG_SELL' (<-0.3)
        """
        if ofi > 0.3:
            return 'STRONG_BUY'
        elif ofi < -0.3:
            return 'STRONG_SELL'
        else:
            return 'BALANCED'

    def get_flow_strength(self, symbol: str) -> float:
        """
        Obtiene magnitud de flujo (sin dirección).

        Returns:
            Strength [0-1]
        """
        ofi = self.get_ofi(symbol)
        return abs(ofi)

    def get_flow_direction(self, symbol: str) -> int:
        """
        Obtiene dirección de flujo.

        Returns:
            1 (buy pressure), -1 (sell pressure), 0 (neutral)
        """
        ofi = self.get_ofi(symbol)
        if ofi > 0.1:
            return 1
        elif ofi < -0.1:
            return -1
        else:
            return 0
