"""
Venue Simulator - Simulador de venue con last-look y probabilidad de fill
Modela comportamiento real de LPs incluyendo rechazos y hold times.
"""

import logging
from typing import Dict, Optional
from datetime import datetime
import numpy as np

logger = logging.getLogger(__name__)


class VenueSimulator:
    """
    Simulador de venue/LP con características realistas.
    
    Modela:
    - Hold time (latencia hasta confirmación)
    - Last-look (rechazo basado en movimiento de precio)
    - Probabilidad de fill condicionada a micro-movimiento
    - Reject rate por tamaño de orden
    """
    
    def __init__(
        self,
        venue_name: str,
        base_fill_probability: float = 0.95,
        base_hold_time_ms: float = 50.0,
        hold_time_std_ms: float = 20.0,
        last_look_threshold_pips: float = 0.5,
        size_penalty_factor: float = 0.1
    ):
        """
        Inicializa venue simulator.
        
        Args:
            venue_name: Nombre del venue
            base_fill_probability: Probabilidad base de fill
            base_hold_time_ms: Hold time medio
            hold_time_std_ms: Desviación estándar de hold time
            last_look_threshold_pips: Umbral de last-look
            size_penalty_factor: Penalización por tamaño
        """
        self.venue_name = venue_name
        self.base_fill_probability = base_fill_probability
        self.base_hold_time_ms = base_hold_time_ms
        self.hold_time_std_ms = hold_time_std_ms
        self.last_look_threshold = last_look_threshold_pips / 10000
        self.size_penalty_factor = size_penalty_factor
        
        logger.info(
            f"VenueSimulator initialized: {venue_name} "
            f"(base_fill={base_fill_probability:.2%}, "
            f"hold_time={base_hold_time_ms:.0f}ms)"
        )
    
    def simulate_execution(
        self,
        instrument: str,
        side: str,
        order_size: float,
        mid_at_send: float,
        volatility: float,
        liquidity_score: float = 1.0
    ) -> Dict:
        """
        Simula ejecución de orden.
        
        Args:
            instrument: Instrumento
            side: 'buy' o 'sell'
            order_size: Tamaño en lotes
            mid_at_send: Mid price al enviar
            volatility: Volatility actual
            liquidity_score: Score de liquidez (0-1, mayor es mejor)
            
        Returns:
            Dict con resultado de simulación
        """
        # Calcular hold time
        hold_time_ms = self._simulate_hold_time()
        
        # Simular movimiento de precio durante hold
        # Movimiento proporcional a volatility y hold time
        price_drift = np.random.normal(
            0,
            volatility * np.sqrt(hold_time_ms / 1000.0)
        )
        
        mid_at_fill = mid_at_send + price_drift
        
        # Calcular probabilidad de fill
        fill_prob = self._calculate_fill_probability(
            order_size,
            price_drift,
            liquidity_score
        )
        
        # Determinar si se llena
        is_filled = np.random.random() < fill_prob
        
        result = {
            'venue': self.venue_name,
            'is_filled': is_filled,
            'hold_time_ms': hold_time_ms,
            'mid_at_send': mid_at_send,
            'mid_at_fill': mid_at_fill,
            'price_drift_pips': price_drift * 10000,
            'fill_probability': fill_prob
        }
        
        if is_filled:
            # Simular fill price (mid + spread/2 + slippage)
            if side == 'buy':
                fill_price = mid_at_fill + self._calculate_slippage(order_size)
            else:
                fill_price = mid_at_fill - self._calculate_slippage(order_size)
            
            result['fill_price'] = fill_price
            result['realized_spread'] = abs(fill_price - mid_at_send)
        else:
            result['reject_reason'] = self._determine_reject_reason(
                price_drift,
                order_size
            )
        
        return result
    
    def _simulate_hold_time(self) -> float:
        """Simula hold time con distribución normal."""
        hold_time = np.random.normal(
            self.base_hold_time_ms,
            self.hold_time_std_ms
        )
        
        # Asegurar que sea positivo
        return max(1.0, hold_time)
    
    def _calculate_fill_probability(
        self,
        order_size: float,
        price_drift: float,
        liquidity_score: float
    ) -> float:
        """
        Calcula probabilidad de fill condicionada.
        
        Probabilidad disminuye si:
        - Orden es grande
        - Precio se movió en contra (last-look)
        - Liquidez es baja
        """
        prob = self.base_fill_probability
        
        # Penalización por tamaño
        size_penalty = self.size_penalty_factor * order_size
        prob *= (1 - size_penalty)
        
        # Last-look: si precio se movió mucho, mayor probabilidad de rechazo
        if abs(price_drift) > self.last_look_threshold:
            # Probabilidad de rechazo aumenta con el movimiento
            last_look_penalty = (abs(price_drift) - self.last_look_threshold) * 10
            prob *= (1 - last_look_penalty)
        
        # Ajuste por liquidez
        prob *= liquidity_score
        
        # Clamp entre 0 y 1
        return np.clip(prob, 0.0, 1.0)
    
    def _calculate_slippage(self, order_size: float) -> float:
        """Calcula slippage basado en tamaño."""
        # Slippage base + componente proporcional a tamaño
        base_slippage = 0.00005  # 0.5 pips
        size_slippage = 0.00002 * order_size  # 0.2 pips por lote
        
        return base_slippage + size_slippage
    
    def _determine_reject_reason(
        self,
        price_drift: float,
        order_size: float
    ) -> str:
        """Determina razón de rechazo."""
        if abs(price_drift) > self.last_look_threshold:
            return "last_look_rejection"
        elif order_size > 5.0:
            return "size_limit_exceeded"
        else:
            return "insufficient_liquidity"