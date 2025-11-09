"""
Capacity Model - Curvas de impacto y lÃ­mites dinÃ¡micos
Define lÃ­mites de trading basados en liquidez y market impact.
"""

import logging
from typing import Dict, Optional
from datetime import datetime, time
import numpy as np

logger = logging.getLogger(__name__)


class CapacityModel:
    """
    Modelo de capacidad institucional.
    
    Define curvas de impacto por:
    - Instrumento
    - Hora del dÃ­a
    - TamaÃ±o de orden
    
    Establece lÃ­mites dinÃ¡micos de notional.
    """
    
    def __init__(self):
        """Inicializa capacity model."""
        # ParÃ¡metros de impacto por instrumento
        self._impact_params: Dict[str, Dict] = {
            'EURUSD.pro': {
                'base_spread': 0.00001,
                'impact_coefficient': 0.001,
                'max_size_lots': 10.0,
                'avg_volume_per_minute': 100.0
            },
            'GBPUSD.pro': {
                'base_spread': 0.00015,
                'impact_coefficient': 0.002,
                'max_size_lots': 5.0,
                'avg_volume_per_minute': 50.0
            },
            'XAUUSD.pro': {
                'base_spread': 0.30,
                'impact_coefficient': 0.003,
                'max_size_lots': 2.0,
                'avg_volume_per_minute': 20.0
            }
        }
        
        # Ajustes por hora del dÃ­a
        self._hour_multipliers = self._initialize_hour_multipliers()
        
        logger.info("CapacityModel initialized")
    
    def _initialize_hour_multipliers(self) -> Dict[int, float]:
        """Inicializa multiplicadores de liquidez por hora."""
        # Multipliers para liquidez (1.0 = normal)
        multipliers = {}
        
        # Horas asiÃ¡ticas (baja liquidez FX)
        for hour in range(0, 7):
            multipliers[hour] = 0.5
        
        # Overlap London (alta liquidez)
        for hour in range(7, 12):
            multipliers[hour] = 1.2
        
        # Overlap London-NY (mÃ¡xima liquidez)
        for hour in range(12, 17):
            multipliers[hour] = 1.5
        
        # NY afternoon
        for hour in range(17, 22):
            multipliers[hour] = 0.8
        
        # Late hours
        for hour in range(22, 24):
            multipliers[hour] = 0.6
        
        return multipliers
    
    def calculate_market_impact(
        self,
        instrument: str,
        order_size: float,
        current_hour: int
    ) -> float:
        """
        Calcula market impact esperado.
        
        Modelo: impact = base_spread + k * sqrt(size / avg_volume)
        
        Args:
            instrument: Instrumento
            order_size: TamaÃ±o en lotes
            current_hour: Hora actual (0-23)
            
        Returns:
            Market impact esperado en precio (no bps)
        """
        if instrument not in self._impact_params:
            # ParÃ¡metros default para instrumentos no configurados
            logger.warning(f"No impact params for {instrument}, using defaults")
            return 0.0001 * order_size
        
        params = self._impact_params[instrument]
        
        base_spread = params['base_spread']
        k = params['impact_coefficient']
        avg_volume = params['avg_volume_per_minute']
        
        # Ajustar por hora del dÃ­a
        hour_mult = self._hour_multipliers.get(current_hour, 1.0)
        effective_volume = avg_volume * hour_mult
        
        # Modelo de impacto: proporcional a sqrt(size/volume)
        if effective_volume > 0:
            volume_ratio = order_size / effective_volume
            impact = base_spread + k * np.sqrt(volume_ratio)
        else:
            impact = base_spread + k * order_size
        
        return impact
    
    def get_max_order_size(
        self,
        instrument: str,
        current_hour: int,
        max_impact_bps: float = 5.0
    ) -> float:
        """
        Calcula tamaÃ±o mÃ¡ximo de orden dado lÃ­mite de impacto.
        
        Args:
            instrument: Instrumento
            current_hour: Hora actual
            max_impact_bps: Impacto mÃ¡ximo permitido (en bps)
            
        Returns:
            TamaÃ±o mÃ¡ximo en lotes
        """
        if instrument not in self._impact_params:
            return 1.0  # Default conservador
        
        params = self._impact_params[instrument]
        max_size = params['max_size_lots']
        
        # Ajustar por hora del dÃ­a
        hour_mult = self._hour_multipliers.get(current_hour, 1.0)
        adjusted_max = max_size * hour_mult
        
        return adjusted_max
    
    def check_capacity_constraint(
        self,
        instrument: str,
        order_size: float,
        current_hour: int,
        max_impact_bps: float = 5.0
    ) -> tuple[bool, Optional[str]]:
        """
        Verifica si orden respeta constraints de capacidad.
        
        Args:
            instrument: Instrumento
            order_size: TamaÃ±o propuesto
            current_hour: Hora actual
            max_impact_bps: Impacto mÃ¡ximo permitido
            
        Returns:
            (is_allowed, reason_if_rejected)
        """
        # Check 1: TamaÃ±o mÃ¡ximo absoluto
        max_size = self.get_max_order_size(instrument, current_hour)
        
        if order_size > max_size:
            return False, f"Order size {order_size:.2f} exceeds max {max_size:.2f} for {instrument}"
        
        # Check 2: Market impact
        impact = self.calculate_market_impact(instrument, order_size, current_hour)
        
        # Convertir a bps (asumiendo precio ~1.0 para simplificaciÃ³n)
        impact_bps = impact * 10000
        
        if impact_bps > max_impact_bps:
            return False, f"Market impact {impact_bps:.1f} bps exceeds limit {max_impact_bps:.1f} bps"
        
        return True, None
    
    def get_optimal_size(
        self,
        instrument: str,
        desired_size: float,
        current_hour: int,
        max_impact_bps: float = 5.0
    ) -> float:
        """
        Obtiene tamaÃ±o Ã³ptimo respetando constraints.
        
        Args:
            instrument: Instrumento
            desired_size: TamaÃ±o deseado
            current_hour: Hora actual
            max_impact_bps: Impacto mÃ¡ximo
            
        Returns:
            TamaÃ±o ajustado que respeta constraints
        """
        # Verificar si tamaÃ±o deseado es vÃ¡lido
        is_valid, reason = self.check_capacity_constraint(
            instrument,
            desired_size,
            current_hour,
            max_impact_bps
        )
        
        if is_valid:
            return desired_size
        
        # Si no es vÃ¡lido, reducir hasta encontrar tamaÃ±o aceptable
        max_allowed = self.get_max_order_size(instrument, current_hour, max_impact_bps)
        
        # Buscar binariamente tamaÃ±o Ã³ptimo
        optimal_size = min(desired_size, max_allowed)
        
        logger.debug(
            f"Size adjusted for {instrument}: "
            f"{desired_size:.2f} -> {optimal_size:.2f} (reason: {reason})"
        )
        
        return optimal_size
    
    def get_capacity_report(self, instrument: str) -> Dict:
        """Genera reporte de capacidad para un instrumento."""
        if instrument not in self._impact_params:
            return {}
        
        params = self._impact_params[instrument]
        
        # Calcular capacidad por hora
        capacity_by_hour = {}
        for hour in range(24):
            max_size = self.get_max_order_size(instrument, hour)
            capacity_by_hour[hour] = max_size
        
        return {
            'instrument': instrument,
            'base_spread': params['base_spread'],
            'impact_coefficient': params['impact_coefficient'],
            'max_size_lots': params['max_size_lots'],
            'avg_volume_per_minute': params['avg_volume_per_minute'],
            'capacity_by_hour': capacity_by_hour,
            'best_hours': sorted(
                capacity_by_hour.items(),
                key=lambda x: x[1],
                reverse=True
            )[:5]
        }