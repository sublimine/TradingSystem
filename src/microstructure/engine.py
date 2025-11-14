"""
Microstructure Engine - Main Orchestrator

MANDATO 15: Motor principal de microestructura institucional.

Orquesta VPINEstimator, OrderFlowAnalyzer, Level2DepthMonitor, SpoofingDetector.
Output: microstructure_score [0-1] para QualityScorer.
"""

import logging
from typing import Dict, List, Optional, Tuple
from .vpin import VPINEstimator
from .order_flow import OrderFlowAnalyzer
from .depth import Level2DepthMonitor
from .spoofing import SpoofingDetector

logger = logging.getLogger(__name__)


class MicrostructureEngine:
    """
    Motor institucional de análisis de microestructura.

    Agrega scores de VPIN, OFI, Depth, Spoofing en microstructure_score [0-1].
    """

    def __init__(self, config: Dict):
        """
        Args:
            config: Configuración completa de microestructura (ver config/microstructure.yaml)
        """
        self.config = config

        # Inicializar componentes
        self.vpin = VPINEstimator(config.get('vpin', {}))
        self.order_flow = OrderFlowAnalyzer(config.get('order_flow', {}))
        self.depth = Level2DepthMonitor(config.get('depth', {}))
        self.spoofing = SpoofingDetector(config.get('spoofing', {}))

        # Pesos de agregación (configurables por símbolo/clase)
        default_weights = config.get('aggregation_weights', {})
        self.weight_vpin = default_weights.get('vpin', 0.40)
        self.weight_ofi = default_weights.get('order_flow', 0.30)
        self.weight_depth = default_weights.get('depth', 0.20)
        self.weight_spoofing = default_weights.get('spoofing', 0.10)

        # Validar suma de pesos = 1.0
        total_weight = self.weight_vpin + self.weight_ofi + self.weight_depth + self.weight_spoofing
        if abs(total_weight - 1.0) > 0.01:
            logger.warning(f"Aggregation weights sum to {total_weight}, not 1.0. Normalizing.")
            self.weight_vpin /= total_weight
            self.weight_ofi /= total_weight
            self.weight_depth /= total_weight
            self.weight_spoofing /= total_weight

        logger.info(f"MicrostructureEngine init: weights (VPIN={self.weight_vpin:.2f}, "
                   f"OFI={self.weight_ofi:.2f}, Depth={self.weight_depth:.2f}, "
                   f"Spoofing={self.weight_spoofing:.2f})")

    def update_tick(self, symbol: str, trade_price: float, trade_volume: float,
                    bid_price: float, ask_price: float):
        """
        Actualizar con nuevo tick de trade.

        Args:
            symbol: Símbolo
            trade_price: Precio del trade
            trade_volume: Volumen del trade
            bid_price: Mejor bid
            ask_price: Mejor ask
        """
        # Actualizar VPIN
        self.vpin.update(symbol, trade_price, trade_volume, bid_price, ask_price)

        # Actualizar Order Flow (clasificar trade primero)
        mid_price = (bid_price + ask_price) / 2
        side = 'BUY' if trade_price >= mid_price else 'SELL'
        self.order_flow.update(symbol, side, trade_volume)

    def update_book(self, symbol: str, bids: List[Tuple[float, float]],
                   asks: List[Tuple[float, float]]):
        """
        Actualizar con snapshot del order book.

        Args:
            symbol: Símbolo
            bids: Lista de (price, quantity) bids
            asks: Lista de (price, quantity) asks
        """
        self.depth.update(symbol, bids, asks)

    def track_order_event(self, symbol: str, event_type: str, order_id: str,
                         price: float = 0, quantity: float = 0, side: str = ''):
        """
        Track orden añadida/cancelada para spoofing detection.

        Args:
            event_type: 'ADD' o 'CANCEL'
            order_id: ID único de la orden
        """
        if event_type == 'ADD':
            self.spoofing.track_order_add(symbol, order_id, price, quantity, side)
        elif event_type == 'CANCEL':
            self.spoofing.track_order_cancel(symbol, order_id)

    def get_microstructure_score(self, symbol: str) -> float:
        """
        Calcular microstructure_score agregado [0-1].

        Score alto = buenas condiciones de microestructura (bajo VPIN, flow balanceado, etc).

        Returns:
            Score [0-1]
        """
        # Obtener scores individuales
        vpin_score = self.vpin.get_score(symbol)
        ofi_score = self.order_flow.get_score(symbol)
        depth_score = self.depth.get_score(symbol)
        spoofing_score = self.spoofing.get_score(symbol)

        # Agregar con pesos
        micro_score = (
            self.weight_vpin * vpin_score +
            self.weight_ofi * ofi_score +
            self.weight_depth * depth_score +
            self.weight_spoofing * spoofing_score
        )

        return max(0.0, min(1.0, micro_score))

    def get_diagnostic_info(self, symbol: str) -> Dict:
        """
        Obtener info de diagnóstico detallada.

        Returns:
            Dict con todos los scores y métricas individuales
        """
        return {
            'microstructure_score': self.get_microstructure_score(symbol),
            'vpin': {
                'value': self.vpin.get_vpin(symbol),
                'score': self.vpin.get_score(symbol),
                'weight': self.weight_vpin
            },
            'order_flow': {
                'ofi': self.order_flow.get_ofi(symbol),
                'score': self.order_flow.get_score(symbol),
                'regime_change': self.order_flow.detect_regime_change(symbol),
                'weight': self.weight_ofi
            },
            'depth': {
                'imbalance': self.depth.get_imbalance(symbol),
                'liquidity_wall': self.depth.detect_liquidity_wall(symbol),
                'score': self.depth.get_score(symbol),
                'weight': self.weight_depth
            },
            'spoofing': {
                'spoof_rate': self.spoofing.get_spoof_rate(symbol),
                'score': self.spoofing.get_score(symbol),
                'weight': self.weight_spoofing
            }
        }
