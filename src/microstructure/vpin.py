"""
VPIN Estimator - Volume-Synchronized Probability of Informed Trading

MANDATO 15: Implementación institucional de VPIN.

Research basis:
- Easley, López de Prado, O'Hara (2012): "Flow Toxicity and Liquidity in a High-Frequency World"
- Lee & Ready (1991): "Inferring Trade Direction"

VPIN [0-1]: probabilidad de informed trading.
- < 0.30: mercado balanceado
- 0.30-0.50: presencia moderada de informed traders
- > 0.50: alto riesgo adverse selection → EVITAR
"""

import numpy as np
from collections import deque
from typing import Dict, Optional, Tuple
import logging

logger = logging.getLogger(__name__)


class VPINEstimator:
    """
    Volume-Synchronized Probability of Informed Trading (VPIN).

    Calcula VPIN en buckets de volumen constante (NO tiempo).
    """

    def __init__(self, config: Dict):
        """
        Args:
            config: {
                'bucket_volume': Volumen por bucket (ej. 10000 para FX major),
                'num_buckets': Ventana de buckets para VPIN (típico 50),
                'vpin_threshold_low': 0.30,
                'vpin_threshold_high': 0.50
            }
        """
        self.bucket_volume = config.get('bucket_volume', 10000)
        self.num_buckets = config.get('num_buckets', 50)
        self.threshold_low = config.get('vpin_threshold_low', 0.30)
        self.threshold_high = config.get('vpin_threshold_high', 0.50)

        # Estado por símbolo
        self.symbols_state: Dict[str, Dict] = {}

        logger.info(f"VPINEstimator init: bucket_vol={self.bucket_volume}, "
                   f"n_buckets={self.num_buckets}")

    def update(self, symbol: str, trade_price: float, trade_volume: float,
               bid_price: float, ask_price: float) -> Optional[float]:
        """
        Actualizar VPIN con nuevo trade.

        Args:
            symbol: Símbolo
            trade_price: Precio del trade
            trade_volume: Volumen del trade
            bid_price: Mejor bid en el momento del trade
            ask_price: Mejor ask en el momento del trade

        Returns:
            VPIN actual si hay suficiente historia, None si aún no
        """
        if symbol not in self.symbols_state:
            self.symbols_state[symbol] = {
                'current_bucket': {'buy': 0, 'sell': 0, 'total': 0},
                'buckets': deque(maxlen=self.num_buckets),
                'last_mid': (bid_price + ask_price) / 2
            }

        state = self.symbols_state[symbol]

        # Clasificar trade (Lee-Ready simplificado)
        mid_price = (bid_price + ask_price) / 2
        side = self._classify_trade(trade_price, mid_price, state['last_mid'])
        state['last_mid'] = mid_price

        # Acumular en bucket actual
        state['current_bucket']['total'] += trade_volume
        if side == 'BUY':
            state['current_bucket']['buy'] += trade_volume
        else:
            state['current_bucket']['sell'] += trade_volume

        # Completar bucket si alcanza volumen target
        if state['current_bucket']['total'] >= self.bucket_volume:
            state['buckets'].append({
                'buy': state['current_bucket']['buy'],
                'sell': state['current_bucket']['sell'],
                'total': state['current_bucket']['total']
            })
            state['current_bucket'] = {'buy': 0, 'sell': 0, 'total': 0}

        # Calcular VPIN si hay suficientes buckets
        if len(state['buckets']) >= self.num_buckets:
            return self._calculate_vpin(state['buckets'])

        return None

    def _classify_trade(self, trade_price: float, mid_price: float,
                       prev_mid: float) -> str:
        """
        Lee-Ready algorithm simplificado.

        Returns:
            'BUY' o 'SELL'
        """
        # Tick test
        if trade_price > mid_price:
            return 'BUY'
        elif trade_price < mid_price:
            return 'SELL'
        else:
            # Zero-tick test
            if trade_price > prev_mid:
                return 'BUY'
            elif trade_price < prev_mid:
                return 'SELL'
            else:
                return 'BUY'  # Default en empate

    def _calculate_vpin(self, buckets: deque) -> float:
        """
        VPIN = Σ|V_buy - V_sell| / ΣV_total
        """
        imbalance_sum = sum(abs(b['buy'] - b['sell']) for b in buckets)
        total_volume = sum(b['total'] for b in buckets)

        if total_volume == 0:
            return 0.0

        vpin = imbalance_sum / total_volume
        return min(vpin, 1.0)

    def get_vpin(self, symbol: str) -> Optional[float]:
        """Get VPIN actual de un símbolo."""
        if symbol not in self.symbols_state:
            return None

        state = self.symbols_state[symbol]
        if len(state['buckets']) < self.num_buckets:
            return None

        return self._calculate_vpin(state['buckets'])

    def get_score(self, symbol: str) -> float:
        """
        Convertir VPIN a score [0-1] donde 1 = mejor (bajo VPIN).

        Returns:
            1.0 si VPIN bajo (bueno), 0.0 si VPIN alto (malo)
        """
        vpin = self.get_vpin(symbol)
        if vpin is None:
            return 0.5  # Neutral sin datos

        # Invertir: VPIN alto → score bajo
        if vpin < self.threshold_low:
            return 1.0
        elif vpin > self.threshold_high:
            return 0.0
        else:
            # Interpolación lineal
            return 1.0 - (vpin - self.threshold_low) / (self.threshold_high - self.threshold_low)
