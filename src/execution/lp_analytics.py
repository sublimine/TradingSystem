"""
LP Analytics Module - AnÃ¡lisis de performance por Liquidity Provider
Rastrea mÃ©tricas de ejecuciÃ³n por LP para routing inteligente.
"""

import logging
from typing import Dict, List, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass, field
import numpy as np

logger = logging.getLogger(__name__)


@dataclass
class LPMetrics:
    """MÃ©tricas de un LP."""
    lp_name: str
    
    # Fill metrics
    orders_sent: int = 0
    orders_filled: int = 0
    orders_rejected: int = 0
    orders_partial: int = 0
    
    # Timing metrics
    hold_times_ms: List[float] = field(default_factory=list)
    
    # Price metrics
    realized_spreads: List[float] = field(default_factory=list)
    adverse_selections: List[float] = field(default_factory=list)
    slippages: List[float] = field(default_factory=list)
    
    # Por instrumento
    metrics_by_instrument: Dict[str, Dict] = field(default_factory=dict)
    
    # Por tamaÃ±o de orden
    metrics_by_size: Dict[str, Dict] = field(default_factory=dict)
    
    # Timestamp Ãºltima actualizaciÃ³n
    last_updated: datetime = field(default_factory=datetime.now)


class LPAnalytics:
    """
    Analytics de Liquidity Providers.
    
    Rastrea y analiza:
    - Fill probability por LP
    - Reject rate desagregado por razÃ³n
    - Hold time (latencia de fill)
    - Realized spread
    - Adverse selection
    - Slippage agregado
    
    MÃ©tricas desagregadas por:
    - Instrumento
    - TamaÃ±o de orden
    - Hora del dÃ­a
    - RÃ©gimen de mercado
    """
    
    def __init__(self, window_size: int = 1000):
        """
        Inicializa LP analytics.
        
        Args:
            window_size: TamaÃ±o de ventana rolling para mÃ©tricas
        """
        self.window_size = window_size
        self._lp_metrics: Dict[str, LPMetrics] = {}
        
        logger.info(f"LPAnalytics initialized with window={window_size}")
    
    def record_order_sent(
        self,
        lp_name: str,
        instrument: str,
        order_size: float,
        mid_at_send: float
    ):
        """Registra orden enviada a LP."""
        metrics = self._get_or_create_metrics(lp_name)
        metrics.orders_sent += 1
        
        # Inicializar mÃ©tricas por instrumento si no existe
        if instrument not in metrics.metrics_by_instrument:
            metrics.metrics_by_instrument[instrument] = {
                'orders_sent': 0,
                'orders_filled': 0,
                'orders_rejected': 0
            }
        
        metrics.metrics_by_instrument[instrument]['orders_sent'] += 1
        
        # Categorizar por tamaÃ±o
        size_bucket = self._get_size_bucket(order_size)
        if size_bucket not in metrics.metrics_by_size:
            metrics.metrics_by_size[size_bucket] = {
                'orders_sent': 0,
                'orders_filled': 0
            }
        
        metrics.metrics_by_size[size_bucket]['orders_sent'] += 1
        metrics.last_updated = datetime.now()
    
    def record_order_filled(
        self,
        lp_name: str,
        instrument: str,
        order_size: float,
        hold_time_ms: float,
        mid_at_send: float,
        mid_at_fill: float,
        fill_price: float,
        side: str  # 'buy' or 'sell'
    ):
        """Registra orden llenada."""
        metrics = self._get_or_create_metrics(lp_name)
        metrics.orders_filled += 1
        
        # Hold time
        metrics.hold_times_ms.append(hold_time_ms)
        if len(metrics.hold_times_ms) > self.window_size:
            metrics.hold_times_ms.pop(0)
        
        # Realized spread (diferencia entre fill y mid al enviar)
        realized_spread = abs(fill_price - mid_at_send)
        metrics.realized_spreads.append(realized_spread)
        if len(metrics.realized_spreads) > self.window_size:
            metrics.realized_spreads.pop(0)
        
        # Adverse selection (movimiento del mid despuÃ©s del fill)
        adverse_selection = abs(mid_at_fill - mid_at_send)
        if side == 'buy':
            # Si compramos y el mid subiÃ³, fue adverse
            adverse_selection = max(0, mid_at_fill - mid_at_send)
        else:
            # Si vendimos y el mid bajÃ³, fue adverse
            adverse_selection = max(0, mid_at_send - mid_at_fill)
        
        metrics.adverse_selections.append(adverse_selection)
        if len(metrics.adverse_selections) > self.window_size:
            metrics.adverse_selections.pop(0)
        
        # Slippage (diferencia entre esperado y real)
        expected_fill = mid_at_send
        slippage = abs(fill_price - expected_fill)
        metrics.slippages.append(slippage)
        if len(metrics.slippages) > self.window_size:
            metrics.slippages.pop(0)
        
        # Por instrumento
        if instrument in metrics.metrics_by_instrument:
            metrics.metrics_by_instrument[instrument]['orders_filled'] += 1
        
        # Por tamaÃ±o
        size_bucket = self._get_size_bucket(order_size)
        if size_bucket in metrics.metrics_by_size:
            metrics.metrics_by_size[size_bucket]['orders_filled'] += 1
        
        metrics.last_updated = datetime.now()
    
    def record_order_rejected(
        self,
        lp_name: str,
        instrument: str,
        order_size: float,
        reject_reason: str
    ):
        """Registra orden rechazada."""
        metrics = self._get_or_create_metrics(lp_name)
        metrics.orders_rejected += 1
        
        # Por instrumento
        if instrument in metrics.metrics_by_instrument:
            metrics.metrics_by_instrument[instrument]['orders_rejected'] += 1
        
        metrics.last_updated = datetime.now()
    
    def record_order_partial(
        self,
        lp_name: str,
        instrument: str,
        requested_size: float,
        filled_size: float
    ):
        """Registra fill parcial."""
        metrics = self._get_or_create_metrics(lp_name)
        metrics.orders_partial += 1
        metrics.last_updated = datetime.now()
    
    def get_lp_score(
        self,
        lp_name: str,
        instrument: Optional[str] = None,
        order_size: Optional[float] = None
    ) -> float:
        """
        Calcula score de un LP para routing.
        
        Score considera:
        - Fill probability (peso alto)
        - Hold time (menor es mejor)
        - Realized spread (menor es mejor)
        - Adverse selection (menor es mejor)
        
        Args:
            lp_name: Nombre del LP
            instrument: Filtrar por instrumento
            order_size: Filtrar por tamaÃ±o de orden
            
        Returns:
            Score 0-100 (mayor es mejor)
        """
        metrics = self._lp_metrics.get(lp_name)
        if not metrics:
            return 0.0
        
        # Filtrar por instrumento si se especifica
        if instrument and instrument in metrics.metrics_by_instrument:
            inst_metrics = metrics.metrics_by_instrument[instrument]
            orders_sent = inst_metrics['orders_sent']
            orders_filled = inst_metrics['orders_filled']
        else:
            orders_sent = metrics.orders_sent
            orders_filled = metrics.orders_filled
        
        if orders_sent == 0:
            return 0.0
        
        # Fill probability (peso 50%)
        fill_prob = orders_filled / orders_sent
        fill_score = fill_prob * 50.0
        
        # Hold time (peso 20%, normalizado)
        if metrics.hold_times_ms:
            avg_hold = np.mean(metrics.hold_times_ms)
            # Normalizar: 0-100ms = 20pts, >500ms = 0pts
            hold_score = max(0, 20.0 * (1 - avg_hold / 500.0))
        else:
            hold_score = 0.0
        
        # Realized spread (peso 15%, normalizado)
        if metrics.realized_spreads:
            avg_spread = np.mean(metrics.realized_spreads)
            # Normalizar: 0 spread = 15pts, >0.0005 = 0pts
            spread_score = max(0, 15.0 * (1 - avg_spread / 0.0005))
        else:
            spread_score = 0.0
        
        # Adverse selection (peso 15%, normalizado)
        if metrics.adverse_selections:
            avg_adverse = np.mean(metrics.adverse_selections)
            # Normalizar: 0 adverse = 15pts, >0.0003 = 0pts
            adverse_score = max(0, 15.0 * (1 - avg_adverse / 0.0003))
        else:
            adverse_score = 0.0
        
        total_score = fill_score + hold_score + spread_score + adverse_score
        
        return min(100.0, total_score)
    
    def get_best_lp(
        self,
        instrument: str,
        order_size: float,
        available_lps: List[str]
    ) -> Optional[str]:
        """
        Selecciona el mejor LP para una orden.
        
        Args:
            instrument: Instrumento
            order_size: TamaÃ±o de orden
            available_lps: Lista de LPs disponibles
            
        Returns:
            Nombre del mejor LP o None
        """
        if not available_lps:
            return None
        
        scores = {}
        for lp_name in available_lps:
            score = self.get_lp_score(lp_name, instrument, order_size)
            scores[lp_name] = score
        
        # Seleccionar LP con mejor score
        best_lp = max(scores.items(), key=lambda x: x[1])
        
        logger.debug(
            f"LP selection for {instrument}: {best_lp[0]} "
            f"(score={best_lp[1]:.1f})"
        )
        
        return best_lp[0]
    
    def get_lp_report(self, lp_name: str) -> Dict:
        """Genera reporte completo de un LP."""
        metrics = self._lp_metrics.get(lp_name)
        if not metrics:
            return {}
        
        fill_prob = (
            metrics.orders_filled / metrics.orders_sent * 100
            if metrics.orders_sent > 0 else 0
        )
        
        reject_rate = (
            metrics.orders_rejected / metrics.orders_sent * 100
            if metrics.orders_sent > 0 else 0
        )
        
        return {
            'lp_name': lp_name,
            'orders_sent': metrics.orders_sent,
            'orders_filled': metrics.orders_filled,
            'orders_rejected': metrics.orders_rejected,
            'orders_partial': metrics.orders_partial,
            'fill_probability_pct': fill_prob,
            'reject_rate_pct': reject_rate,
            'avg_hold_time_ms': (
                np.mean(metrics.hold_times_ms)
                if metrics.hold_times_ms else 0
            ),
            'avg_realized_spread': (
                np.mean(metrics.realized_spreads)
                if metrics.realized_spreads else 0
            ),
            'avg_adverse_selection': (
                np.mean(metrics.adverse_selections)
                if metrics.adverse_selections else 0
            ),
            'avg_slippage': (
                np.mean(metrics.slippages)
                if metrics.slippages else 0
            ),
            'overall_score': self.get_lp_score(lp_name),
            'by_instrument': metrics.metrics_by_instrument,
            'by_size': metrics.metrics_by_size,
            'last_updated': metrics.last_updated.isoformat()
        }
    
    def _get_or_create_metrics(self, lp_name: str) -> LPMetrics:
        """Obtiene o crea mÃ©tricas para un LP."""
        if lp_name not in self._lp_metrics:
            self._lp_metrics[lp_name] = LPMetrics(lp_name=lp_name)
        
        return self._lp_metrics[lp_name]
    
    def _get_size_bucket(self, order_size: float) -> str:
        """Categoriza tamaÃ±o de orden."""
        if order_size < 0.1:
            return 'micro'
        elif order_size < 1.0:
            return 'small'
        elif order_size < 5.0:
            return 'medium'
        elif order_size < 10.0:
            return 'large'
        else:
            return 'xlarge'