"""
Level 2 Depth Monitor - Order Book Analysis

MANDATO 15: Análisis institucional de profundidad del book.

Mide imbalance bid/ask, detecta liquidity walls, analiza spread.
"""

import numpy as np
from typing import Dict, List, Optional, Tuple
import logging

logger = logging.getLogger(__name__)


class Level2DepthMonitor:
    """
    Monitorea profundidad del order book (Level 2).
    """

    def __init__(self, config: Dict):
        """
        Args:
            config: {
                'levels_to_analyze': Número de niveles a analizar (típico 5-10),
                'imbalance_threshold': Umbral para detectar imbalance significativo (típico 0.65)
            }
        """
        self.levels_to_analyze = config.get('levels_to_analyze', 5)
        self.imbalance_threshold = config.get('imbalance_threshold', 0.65)

        # Estado por símbolo
        self.symbols_state: Dict[str, Dict] = {}

        logger.info(f"Level2DepthMonitor init: levels={self.levels_to_analyze}")

    def update(self, symbol: str, bids: List[Tuple[float, float]],
               asks: List[Tuple[float, float]]):
        """
        Actualizar con snapshot del book.

        Args:
            symbol: Símbolo
            bids: Lista de (price, quantity) ordenada descendente
            asks: Lista de (price, quantity) ordenada ascendente
        """
        if symbol not in self.symbols_state:
            self.symbols_state[symbol] = {
                'last_bids': [],
                'last_asks': [],
                'last_imbalance': 0.5
            }

        state = self.symbols_state[symbol]
        state['last_bids'] = bids[:self.levels_to_analyze]
        state['last_asks'] = asks[:self.levels_to_analyze]

        # Calcular imbalance
        imbalance = self._calculate_imbalance(state['last_bids'], state['last_asks'])
        state['last_imbalance'] = imbalance

    def _calculate_imbalance(self, bids: List[Tuple[float, float]],
                            asks: List[Tuple[float, float]]) -> float:
        """
        Imbalance = bid_volume / (bid_volume + ask_volume)

        Returns:
            [0-1]: 0.5 = balanceado, >0.5 = presión compradora, <0.5 = vendedora
        """
        if not bids or not asks:
            return 0.5

        bid_volume = sum(qty for _, qty in bids)
        ask_volume = sum(qty for _, qty in asks)

        if bid_volume + ask_volume == 0:
            return 0.5

        return bid_volume / (bid_volume + ask_volume)

    def detect_liquidity_wall(self, symbol: str) -> Optional[str]:
        """
        Detectar liquidity wall (concentración de liquidez en un nivel).

        Returns:
            'BID' si hay wall de bids, 'ASK' si hay wall de asks, None si no
        """
        if symbol not in self.symbols_state:
            return None

        state = self.symbols_state[symbol]
        if not state['last_bids'] or not state['last_asks']:
            return None

        # Analizar bids
        bid_volumes = [qty for _, qty in state['last_bids']]
        if bid_volumes and max(bid_volumes) > sum(bid_volumes) * 0.5:
            return 'BID'

        # Analizar asks
        ask_volumes = [qty for _, qty in state['last_asks']]
        if ask_volumes and max(ask_volumes) > sum(ask_volumes) * 0.5:
            return 'ASK'

        return None

    def get_imbalance(self, symbol: str) -> float:
        """Get imbalance actual."""
        if symbol not in self.symbols_state:
            return 0.5

        return self.symbols_state[symbol]['last_imbalance']

    def get_score(self, symbol: str) -> float:
        """
        Convertir imbalance a score [0-1].

        Imbalance balanceado (0.5) → score alto.
        Imbalance extremo → score bajo.

        Returns:
            Score [0-1] donde 1 = mejor
        """
        imbalance = self.get_imbalance(symbol)

        # Invertir: imbalance extremo → score bajo
        # |imbalance - 0.5| = 0 → score = 1.0
        # |imbalance - 0.5| = 0.5 → score = 0.0
        deviation = abs(imbalance - 0.5) * 2  # Normalizar a [0-1]
        return 1.0 - deviation
