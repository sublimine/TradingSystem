"""
Microstructure Engine - Composite Microstructure Scoring

Agrega señales de microestructura (VPIN + OFI) en un score unificado [0-1].
Este score alimenta la dimensión 'order_flow' del QualityScorer.

Score alto → Condiciones microestructurales favorables (flujo limpio, balanceado)
Score bajo → Condiciones adversas (flujo tóxico, desequilibrio extremo)
"""

import numpy as np
from typing import Dict, List, Optional
import logging

from .vpin import VPINEstimator
from .order_flow import OrderFlowAnalyzer

logger = logging.getLogger(__name__)


class MicrostructureEngine:
    """
    Motor composite de microestructura.

    Combina:
    - VPIN (toxicidad de flujo)
    - OFI (desequilibrio direccional)

    Output: microstructure_score [0-1]
    """

    def __init__(self, config: Dict):
        """
        Inicializar motor de microestructura.

        Args:
            config: {
                'vpin': {...},  # Config para VPINEstimator
                'order_flow': {...},  # Config para OrderFlowAnalyzer
                'weights': {  # Pesos de componentes
                    'vpin_quality': float,  # default: 0.60
                    'flow_balance': float   # default: 0.40
                }
            }
        """
        vpin_config = config.get('vpin', {
            'bucket_volume': 100,
            'window_buckets': 50
        })
        ofi_config = config.get('order_flow', {
            'window_seconds': 60,
            'min_trades': 5
        })

        self.vpin_estimator = VPINEstimator(vpin_config)
        self.order_flow_analyzer = OrderFlowAnalyzer(ofi_config)

        # Pesos institucionales calibrados
        weights = config.get('weights', {})
        self.weight_vpin = weights.get('vpin_quality', 0.60)
        self.weight_ofi = weights.get('flow_balance', 0.40)

        logger.info(f"MicrostructureEngine initialized: "
                   f"vpin_weight={self.weight_vpin}, ofi_weight={self.weight_ofi}")

    def update_trades(self, symbol: str, trades: List[Dict]):
        """
        Actualiza motores con nuevos trades.

        Args:
            trades: Lista de trades con estructura:
                   [{price, volume, bid, ask, timestamp, side}, ...]
                   'side' puede ser opcional (VPIN lo clasifica)
        """
        # Actualizar VPIN (clasifica automáticamente si no hay 'side')
        vpin_trades = []
        for trade in trades:
            vpin_trades.append({
                'price': trade['price'],
                'volume': trade['volume'],
                'bid': trade.get('bid'),
                'ask': trade.get('ask'),
                'timestamp': trade.get('timestamp')
            })
        self.vpin_estimator.update(symbol, vpin_trades)

        # Actualizar OFI (necesita 'side' clasificado)
        ofi_trades = []
        for trade in trades:
            side = trade.get('side')
            if side is None:
                # Clasificar con VPIN si no viene clasificado
                side = self.vpin_estimator.classify_trade(
                    symbol, trade['price'], trade['volume'],
                    trade.get('bid'), trade.get('ask')
                )
            ofi_trades.append({
                'timestamp': trade.get('timestamp'),
                'side': side,
                'volume': trade['volume']
            })
        self.order_flow_analyzer.update(symbol, ofi_trades)

    def calculate_microstructure_score(self, symbol: str) -> Dict:
        """
        Calcula score composite de microestructura.

        Lógica:
        1. VPIN Quality (60%):
           - VPIN bajo = score alto (inverted)
           - VPIN < 0.30 → score 1.0
           - VPIN > 0.50 → score 0.0
           - Interpolación lineal entre 0.30-0.50

        2. Flow Balance (40%):
           - |OFI| bajo = score alto (flujo balanceado)
           - |OFI| < 0.2 → score 1.0
           - |OFI| > 0.6 → score 0.0
           - Interpolación lineal

        Returns:
            {
                'microstructure_score': float [0-1],
                'vpin': float,
                'vpin_quality': float [0-1],
                'ofi': float,
                'flow_balance': float [0-1],
                'interpretation': str
            }
        """
        vpin = self.vpin_estimator.get_vpin(symbol)
        ofi = self.order_flow_analyzer.get_ofi(symbol)

        # 1. VPIN Quality (invertido: bajo VPIN = alta calidad)
        if vpin <= 0.30:
            vpin_quality = 1.0
        elif vpin >= 0.50:
            vpin_quality = 0.0
        else:
            # Interpolación lineal 0.30-0.50 → 1.0-0.0
            vpin_quality = 1.0 - ((vpin - 0.30) / 0.20)

        # 2. Flow Balance (bajo desequilibrio = alto balance)
        ofi_abs = abs(ofi)
        if ofi_abs <= 0.2:
            flow_balance = 1.0
        elif ofi_abs >= 0.6:
            flow_balance = 0.0
        else:
            # Interpolación lineal 0.2-0.6 → 1.0-0.0
            flow_balance = 1.0 - ((ofi_abs - 0.2) / 0.4)

        # Score composite
        microstructure_score = (
            self.weight_vpin * vpin_quality +
            self.weight_ofi * flow_balance
        )

        # Interpretación
        interpretation = self._interpret_score(microstructure_score, vpin, ofi)

        return {
            'microstructure_score': round(microstructure_score, 4),
            'vpin': round(vpin, 4),
            'vpin_quality': round(vpin_quality, 4),
            'ofi': round(ofi, 4),
            'flow_balance': round(flow_balance, 4),
            'interpretation': interpretation
        }

    def _interpret_score(self, score: float, vpin: float, ofi: float) -> str:
        """Interpreta score de microestructura para logging."""
        vpin_status = self.vpin_estimator.interpret_vpin(vpin)
        ofi_status = self.order_flow_analyzer.interpret_ofi(ofi)

        if score >= 0.7:
            return f"FAVORABLE ({vpin_status}, {ofi_status})"
        elif score >= 0.4:
            return f"MODERATE ({vpin_status}, {ofi_status})"
        else:
            return f"ADVERSE ({vpin_status}, {ofi_status})"

    def get_microstructure_score(self, symbol: str) -> float:
        """
        Obtiene solo el score composite [0-1].

        Returns:
            microstructure_score [0-1]
        """
        result = self.calculate_microstructure_score(symbol)
        return result['microstructure_score']

    def get_detailed_state(self, symbol: str) -> Dict:
        """
        Obtiene estado completo de microestructura para debugging/reporting.

        Returns:
            Diccionario con todos los componentes y scores
        """
        return self.calculate_microstructure_score(symbol)
