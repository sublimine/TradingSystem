"""
Factor Limits - Límites operativos por factor de riesgo
Implementa límites de pérdida y exposición por factor además de globales.
"""

from typing import Dict, Optional, List
from dataclasses import dataclass
from datetime import datetime, date
import logging

logger = logging.getLogger(__name__)


@dataclass
class FactorLimit:
    """Límite operativo para un factor de riesgo."""
    factor_name: str
    max_daily_loss_usd: float  # Pérdida máxima diaria en USD
    max_exposure_pct: float     # Exposición máxima como % del capital
    current_loss_usd: float = 0.0
    current_exposure_pct: float = 0.0
    breached: bool = False
    breach_timestamp: Optional[datetime] = None
    

class FactorLimitsManager:
    """
    Gestor de límites operativos por factor de riesgo.
    
    Rastrea pérdidas realizadas y exposición neta por factor,
    enforce límites configurados, y dispara circuit breakers
    cuando se violan.
    """
    
    def __init__(
        self,
        total_capital: float,
        factor_limits_config: Dict[str, Dict[str, float]]
    ):
        """
        Inicializa gestor de límites factoriales.
        
        Args:
            total_capital: Capital total del portfolio
            factor_limits_config: Dict con límites por factor:
                {
                    'USD': {'max_daily_loss_pct': 0.02, 'max_exposure_pct': 0.20},
                    'rates_diff': {'max_daily_loss_pct': 0.015, 'max_exposure_pct': 0.15},
                    ...
                }
        """
        self.total_capital = total_capital
        self.factor_limits: Dict[str, FactorLimit] = {}
        
        # Inicializar límites
        for factor_name, config in factor_limits_config.items():
            max_daily_loss_usd = total_capital * config['max_daily_loss_pct']
            max_exposure_pct = config['max_exposure_pct']
            
            self.factor_limits[factor_name] = FactorLimit(
                factor_name=factor_name,
                max_daily_loss_usd=max_daily_loss_usd,
                max_exposure_pct=max_exposure_pct
            )
        
        self.current_date = date.today()
        self._breached_factors: List[str] = []
        
        logger.info(
            f"FactorLimitsManager inicializado: capital=${total_capital:,.2f}, "
            f"factors={len(self.factor_limits)}"
        )
    
    def update_factor_loss(self, factor_name: str, loss_usd: float):
        """
        Actualiza pérdida realizada para un factor.
        
        Args:
            factor_name: Nombre del factor
            loss_usd: Pérdida en USD (positivo = pérdida, negativo = ganancia)
        """
        if factor_name not in self.factor_limits:
            logger.warning(f"Factor desconocido: {factor_name}")
            return
        
        # Reset diario si cambió la fecha
        today = date.today()
        if today != self.current_date:
            self._reset_daily_counters()
            self.current_date = today
        
        limit = self.factor_limits[factor_name]
        limit.current_loss_usd += loss_usd
        
        # Check si violamos límite
        if limit.current_loss_usd >= limit.max_daily_loss_usd:
            if not limit.breached:
                limit.breached = True
                limit.breach_timestamp = datetime.now()
                self._breached_factors.append(factor_name)
                
                logger.error(
                    f"FACTOR_LIMIT_BREACHED: {factor_name} "
                    f"loss=${limit.current_loss_usd:,.2f} "
                    f"limit=${limit.max_daily_loss_usd:,.2f}"
                )
    
    def update_factor_exposure(self, factor_name: str, exposure_pct: float):
        """
        Actualiza exposición neta para un factor.
        
        Args:
            factor_name: Nombre del factor
            exposure_pct: Exposición neta como % del capital
        """
        if factor_name not in self.factor_limits:
            logger.warning(f"Factor desconocido: {factor_name}")
            return
        
        limit = self.factor_limits[factor_name]
        limit.current_exposure_pct = exposure_pct
        
        # Check si excedemos límite de exposición
        if abs(exposure_pct) > limit.max_exposure_pct:
            logger.warning(
                f"FACTOR_EXPOSURE_WARNING: {factor_name} "
                f"exposure={exposure_pct:.2%} "
                f"limit={limit.max_exposure_pct:.2%}"
            )
    
    def can_add_exposure(
        self,
        factor_name: str,
        additional_exposure_pct: float
    ) -> bool:
        """
        Verifica si se puede añadir exposición adicional a un factor.
        
        Args:
            factor_name: Nombre del factor
            additional_exposure_pct: Exposición adicional propuesta
            
        Returns:
            True si la exposición resultante está dentro del límite
        """
        if factor_name not in self.factor_limits:
            return True  # Factor no limitado
        
        limit = self.factor_limits[factor_name]
        
        # Si ya violamos límite de pérdida, no permitir más exposición
        if limit.breached:
            return False
        
        # Check exposición resultante
        new_exposure = limit.current_exposure_pct + additional_exposure_pct
        return abs(new_exposure) <= limit.max_exposure_pct
    
    def get_remaining_capacity(self, factor_name: str) -> Dict[str, float]:
        """
        Obtiene capacidad restante para un factor.
        
        Args:
            factor_name: Nombre del factor
            
        Returns:
            Dict con remaining loss budget y exposure capacity
        """
        if factor_name not in self.factor_limits:
            return {
                'remaining_loss_usd': float('inf'),
                'remaining_exposure_pct': float('inf')
            }
        
        limit = self.factor_limits[factor_name]
        
        remaining_loss = limit.max_daily_loss_usd - limit.current_loss_usd
        remaining_exposure = limit.max_exposure_pct - abs(limit.current_exposure_pct)
        
        return {
            'remaining_loss_usd': max(0, remaining_loss),
            'remaining_exposure_pct': max(0, remaining_exposure)
        }
    
    def is_any_factor_breached(self) -> bool:
        """Retorna True si cualquier factor ha violado su límite."""
        return len(self._breached_factors) > 0
    
    def get_breached_factors(self) -> List[str]:
        """Retorna lista de factores que han violado límites."""
        return self._breached_factors.copy()
    
    def get_all_limits_status(self) -> Dict[str, Dict]:
        """
        Obtiene status completo de todos los límites.
        
        Returns:
            Dict con status de cada factor
        """
        status = {}
        
        for factor_name, limit in self.factor_limits.items():
            status[factor_name] = {
                'current_loss_usd': limit.current_loss_usd,
                'max_loss_usd': limit.max_daily_loss_usd,
                'loss_utilization_pct': (
                    limit.current_loss_usd / limit.max_daily_loss_usd
                    if limit.max_daily_loss_usd > 0 else 0
                ),
                'current_exposure_pct': limit.current_exposure_pct,
                'max_exposure_pct': limit.max_exposure_pct,
                'exposure_utilization_pct': (
                    abs(limit.current_exposure_pct) / limit.max_exposure_pct
                    if limit.max_exposure_pct > 0 else 0
                ),
                'breached': limit.breached,
                'breach_timestamp': (
                    limit.breach_timestamp.isoformat()
                    if limit.breach_timestamp else None
                )
            }
        
        return status
    
    def _reset_daily_counters(self):
        """Reset contadores diarios al inicio de nuevo día."""
        logger.info(f"Resetting daily factor limits for {date.today()}")
        
        for limit in self.factor_limits.values():
            limit.current_loss_usd = 0.0
            limit.breached = False
            limit.breach_timestamp = None
        
        self._breached_factors.clear()
    
    def export_status(self) -> Dict:
        """
        Exporta status completo para persistencia.
        
        Returns:
            Dict serializable con todo el estado
        """
        return {
            'total_capital': self.total_capital,
            'current_date': self.current_date.isoformat(),
            'breached_factors': self._breached_factors,
            'limits': self.get_all_limits_status()
        }
