"""
Order Flow Analyzer - OFI and Flow Intensity

MANDATO 15: Análisis institucional de order flow.

Mide presión compradora vs vendedora en ventana deslizante.
OFI normalizado [-1, +1]: negativo = presión vendedora, positivo = presión compradora.
"""

import numpy as np
from collections import deque
from typing import Dict, Optional
import logging

logger = logging.getLogger(__name__)


class OrderFlowAnalyzer:
    """
    Analiza Order Flow Imbalance (OFI) y cambios de régimen.
    """

    def __init__(self, config: Dict):
        """
        Args:
            config: {
                'window_trades': Ventana de trades para OFI (típico 100),
                'regime_threshold_sigma': Umbral en sigmas para cambio de régimen (típico 2.0)
            }
        """
        self.window_trades = config.get('window_trades', 100)
        self.regime_threshold = config.get('regime_threshold_sigma', 2.0)

        # Estado por símbolo
        self.symbols_state: Dict[str, Dict] = {}

        logger.info(f"OrderFlowAnalyzer init: window={self.window_trades}")

    def update(self, symbol: str, side: str, volume: float):
        """
        Actualizar con nuevo trade clasificado.

        Args:
            symbol: Símbolo
            side: 'BUY' o 'SELL'
            volume: Volumen del trade
        """
        if symbol not in self.symbols_state:
            self.symbols_state[symbol] = {
                'trades': deque(maxlen=self.window_trades),
                'ofi_history': deque(maxlen=50)  # Para calcular mean/std
            }

        state = self.symbols_state[symbol]

        # Registrar trade con signo
        signed_volume = volume if side == 'BUY' else -volume
        state['trades'].append(signed_volume)

        # Calcular OFI si hay suficiente historia
        if len(state['trades']) >= self.window_trades:
            ofi = self._calculate_ofi(state['trades'])
            state['ofi_history'].append(ofi)

    def _calculate_ofi(self, trades: deque) -> float:
        """
        OFI = (Σ buy_volume - Σ sell_volume) / Σ total_volume

        Returns:
            OFI normalizado [-1, +1]
        """
        total_signed = sum(trades)
        total_abs = sum(abs(t) for t in trades)

        if total_abs == 0:
            return 0.0

        ofi = total_signed / total_abs
        return np.clip(ofi, -1.0, 1.0)

    def get_ofi(self, symbol: str) -> Optional[float]:
        """Get OFI actual."""
        if symbol not in self.symbols_state:
            return None

        state = self.symbols_state[symbol]
        if len(state['trades']) < self.window_trades:
            return None

        return self._calculate_ofi(state['trades'])

    def detect_regime_change(self, symbol: str) -> bool:
        """
        Detectar cambio de régimen: OFI actual > threshold_sigma * std.

        Returns:
            True si hay cambio significativo de régimen
        """
        if symbol not in self.symbols_state:
            return False

        state = self.symbols_state[symbol]
        if len(state['ofi_history']) < 20:
            return False

        ofi_current = self.get_ofi(symbol)
        if ofi_current is None:
            return False

        # Calcular desviación histórica
        ofi_mean = np.mean(state['ofi_history'])
        ofi_std = np.std(state['ofi_history'])

        if ofi_std == 0:
            return False

        # Detectar si OFI actual está a >threshold sigmas de la media
        z_score = abs(ofi_current - ofi_mean) / ofi_std
        return z_score > self.regime_threshold

    def get_score(self, symbol: str) -> float:
        """
        Convertir OFI a score [0-1].

        OFI balanceado (cerca de 0) → score alto (buena calidad).
        OFI extremo (cerca de ±1) → score bajo (presión unilateral).

        Returns:
            Score [0-1] donde 1 = mejor
        """
        ofi = self.get_ofi(symbol)
        if ofi is None:
            return 0.5

        # Invertir: OFI extremo → score bajo
        # |OFI| = 0 → score = 1.0
        # |OFI| = 1 → score = 0.0
        return 1.0 - abs(ofi)
