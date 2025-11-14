"""
Spoofing Detector - Detection of Market Manipulation

MANDATO 15: Detección institucional de spoofing y layering.

Identifica órdenes fantasma: grandes órdenes añadidas y canceladas rápidamente.
"""

import numpy as np
from collections import deque
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import logging

logger = logging.getLogger(__name__)


class SpoofingDetector:
    """
    Detecta patrones de spoofing y layering en el order book.
    """

    def __init__(self, config: Dict):
        """
        Args:
            config: {
                'cancel_time_threshold_sec': Tiempo máximo para considerar cancel rápido (típico 5s),
                'volume_threshold_multiplier': Multiplicador sobre volumen promedio para detectar gran orden (típico 3.0)
            }
        """
        self.cancel_time_threshold = timedelta(
            seconds=config.get('cancel_time_threshold_sec', 5)
        )
        self.volume_threshold = config.get('volume_threshold_multiplier', 3.0)

        # Estado por símbolo
        self.symbols_state: Dict[str, Dict] = {}

        logger.info(f"SpoofingDetector init: cancel_threshold={self.cancel_time_threshold}")

    def track_order_add(self, symbol: str, order_id: str, price: float,
                       quantity: float, side: str):
        """
        Registrar nueva orden en el book.

        Args:
            symbol: Símbolo
            order_id: ID único de la orden
            price: Precio
            quantity: Cantidad
            side: 'BID' o 'ASK'
        """
        if symbol not in self.symbols_state:
            self.symbols_state[symbol] = {
                'active_orders': {},
                'spoof_events': deque(maxlen=100),
                'recent_volumes': deque(maxlen=50)
            }

        state = self.symbols_state[symbol]
        state['active_orders'][order_id] = {
            'price': price,
            'quantity': quantity,
            'side': side,
            'timestamp': datetime.now()
        }
        state['recent_volumes'].append(quantity)

    def track_order_cancel(self, symbol: str, order_id: str) -> bool:
        """
        Registrar cancelación de orden y detectar si es spoofing.

        Returns:
            True si se detectó spoofing
        """
        if symbol not in self.symbols_state:
            return False

        state = self.symbols_state[symbol]

        if order_id not in state['active_orders']:
            return False

        order = state['active_orders'][order_id]
        cancel_time = datetime.now()
        elapsed = cancel_time - order['timestamp']

        # Verificar si es cancel rápido
        if elapsed <= self.cancel_time_threshold:
            # Verificar si volumen es significativo
            avg_volume = np.mean(state['recent_volumes']) if state['recent_volumes'] else 0
            if avg_volume > 0 and order['quantity'] > avg_volume * self.volume_threshold:
                # Detectado spoofing
                state['spoof_events'].append({
                    'timestamp': cancel_time,
                    'side': order['side'],
                    'quantity': order['quantity'],
                    'duration_sec': elapsed.total_seconds()
                })

                logger.debug(f"Spoofing detected: {symbol} {order['side']} "
                           f"{order['quantity']} canceled after {elapsed.total_seconds():.1f}s")

                del state['active_orders'][order_id]
                return True

        del state['active_orders'][order_id]
        return False

    def get_spoof_rate(self, symbol: str, window_seconds: int = 60) -> float:
        """
        Calcular tasa de eventos de spoofing recientes.

        Args:
            window_seconds: Ventana de tiempo en segundos

        Returns:
            Número de eventos de spoofing por minuto
        """
        if symbol not in self.symbols_state:
            return 0.0

        state = self.symbols_state[symbol]
        cutoff = datetime.now() - timedelta(seconds=window_seconds)

        recent_spoofs = sum(
            1 for event in state['spoof_events']
            if event['timestamp'] > cutoff
        )

        return recent_spoofs / (window_seconds / 60)

    def get_score(self, symbol: str) -> float:
        """
        Convertir spoof rate a score [0-1].

        Sin spoofing → score alto.
        Alto spoofing → score bajo (mercado manipulado).

        Returns:
            Score [0-1] donde 1 = mejor
        """
        spoof_rate = self.get_spoof_rate(symbol)

        # 0 spoofs/min → score = 1.0
        # 5+ spoofs/min → score = 0.0
        if spoof_rate == 0:
            return 1.0
        elif spoof_rate >= 5:
            return 0.0
        else:
            return 1.0 - (spoof_rate / 5.0)
