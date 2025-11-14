"""
VPIN Estimator - Volume-Synchronized Probability of Informed Trading

Implementación institucional basada en Easley, López de Prado, O'Hara (2012).
Clasifica trades como agresivos (buy/sell) y calcula desequilibrio en buckets de volumen.

VPIN alto → flujo tóxico, evitar ejecución.
VPIN bajo → flujo balanceado, condiciones favorables.
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Tuple
from collections import deque
import logging

logger = logging.getLogger(__name__)


class VPINEstimator:
    """
    Estimador de VPIN en buckets de volumen constante.

    Calibración institucional:
    - bucket_volume: Volumen fijo por bucket (ej: 50 lots para EURUSD)
    - window_buckets: Ventana deslizante de buckets para VPIN (típicamente 50)
    - Thresholds: <0.30 (clean), 0.30-0.50 (moderate), >0.50 (toxic)
    """

    def __init__(self, config: Dict):
        """
        Inicializar estimador VPIN.

        Args:
            config: {
                'bucket_volume': int - Volumen por bucket,
                'window_buckets': int - Número de buckets en ventana,
                'classify_method': str - 'tick' o 'quote' (default: tick)
            }
        """
        self.bucket_volume = config.get('bucket_volume', 100)
        self.window_buckets = config.get('window_buckets', 50)
        self.classify_method = config.get('classify_method', 'tick')

        # Estado interno por símbolo
        self.buckets = {}  # {symbol: deque of {buy_vol, sell_vol, total_vol}}
        self.current_bucket = {}  # {symbol: {buy_vol, sell_vol, current_vol}}
        self.last_price = {}  # Para tick classification

        logger.info(f"VPINEstimator initialized: bucket_vol={self.bucket_volume}, "
                   f"window={self.window_buckets}, method={self.classify_method}")

    def classify_trade(self, symbol: str, price: float, volume: float,
                      bid: Optional[float] = None, ask: Optional[float] = None) -> str:
        """
        Clasifica trade como BUY o SELL agresivo.

        Lee-Ready algorithm:
        - Si price > mid → BUY
        - Si price < mid → SELL
        - Si price == mid → usar tick test (comparar con precio previo)

        Args:
            symbol: Símbolo
            price: Precio del trade
            volume: Volumen del trade
            bid: Best bid (opcional)
            ask: Best ask (opcional)

        Returns:
            'BUY' o 'SELL'
        """
        if bid is not None and ask is not None and bid > 0 and ask > 0:
            mid = (bid + ask) / 2.0
            if price > mid:
                self.last_price[symbol] = price
                return 'BUY'
            elif price < mid:
                self.last_price[symbol] = price
                return 'SELL'

        # Tick test: comparar con precio previo
        prev_price = self.last_price.get(symbol, price)
        self.last_price[symbol] = price

        if price > prev_price:
            return 'BUY'
        elif price < prev_price:
            return 'SELL'
        else:
            # Si no hay movimiento, asumir distribución 50/50 (neutral)
            return 'BUY' if np.random.rand() > 0.5 else 'SELL'

    def update(self, symbol: str, trades: List[Dict]) -> Optional[float]:
        """
        Actualiza VPIN con nuevos trades.

        Args:
            trades: Lista de trades [{price, volume, bid, ask, timestamp}, ...]

        Returns:
            VPIN actual [0-1] o None si no hay suficientes buckets
        """
        if symbol not in self.buckets:
            self.buckets[symbol] = deque(maxlen=self.window_buckets)
            self.current_bucket[symbol] = {'buy_vol': 0.0, 'sell_vol': 0.0, 'current_vol': 0.0}

        for trade in trades:
            price = trade['price']
            volume = trade['volume']
            bid = trade.get('bid')
            ask = trade.get('ask')

            # Clasificar trade
            side = self.classify_trade(symbol, price, volume, bid, ask)

            # Acumular en bucket actual
            bucket = self.current_bucket[symbol]
            bucket['current_vol'] += volume
            if side == 'BUY':
                bucket['buy_vol'] += volume
            else:
                bucket['sell_vol'] += volume

            # Si bucket lleno, cerrarlo y crear uno nuevo
            if bucket['current_vol'] >= self.bucket_volume:
                self.buckets[symbol].append({
                    'buy_vol': bucket['buy_vol'],
                    'sell_vol': bucket['sell_vol'],
                    'total_vol': bucket['current_vol']
                })
                self.current_bucket[symbol] = {'buy_vol': 0.0, 'sell_vol': 0.0, 'current_vol': 0.0}

        return self.calculate_vpin(symbol)

    def calculate_vpin(self, symbol: str) -> Optional[float]:
        """
        Calcula VPIN actual en ventana deslizante.

        VPIN = Σ|V_buy - V_sell| / ΣV_total

        Returns:
            VPIN [0-1] o None si no hay suficientes buckets
        """
        if symbol not in self.buckets or len(self.buckets[symbol]) < self.window_buckets:
            return None

        buckets_list = list(self.buckets[symbol])
        total_imbalance = sum(abs(b['buy_vol'] - b['sell_vol']) for b in buckets_list)
        total_volume = sum(b['total_vol'] for b in buckets_list)

        if total_volume == 0:
            return None

        vpin = total_imbalance / total_volume
        return min(vpin, 1.0)  # Cap en 1.0

    def get_vpin(self, symbol: str) -> float:
        """
        Obtiene VPIN actual (o valor por defecto si no disponible).

        Returns:
            VPIN [0-1], default 0.4 si no hay datos suficientes
        """
        vpin = self.calculate_vpin(symbol)
        return vpin if vpin is not None else 0.4  # Default neutral

    def interpret_vpin(self, vpin: float) -> str:
        """
        Interpreta nivel de VPIN.

        Returns:
            'CLEAN' (<0.30), 'MODERATE' (0.30-0.50), 'TOXIC' (>0.50)
        """
        if vpin < 0.30:
            return 'CLEAN'
        elif vpin < 0.50:
            return 'MODERATE'
        else:
            return 'TOXIC'
