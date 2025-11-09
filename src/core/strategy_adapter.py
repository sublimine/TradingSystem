"""
Strategy Adapter - Adaptador base para estrategias que publican señales

Las estrategias heredan de esta clase y sobrescriben evaluate()
para generar InstitutionalSignal cuando detectan setups.
"""

import logging
from datetime import datetime
from typing import Dict, Optional
import pandas as pd
import ulid

from core.signal_schema import InstitutionalSignal
from core.signal_bus import get_signal_bus

logger = logging.getLogger(__name__)


class StrategyAdapter:
    """
    Clase base para estrategias que publican señales al SignalBus.
    
    Las estrategias concretas heredan de esta clase e implementan
    el método evaluate() para detectar setups y generar señales.
    """
    
    def __init__(self, strategy_id: str, strategy_version: str, bus=None):
        """
        Args:
            strategy_id: ID único de la estrategia
            strategy_version: Versión de la estrategia
            bus: SignalBus opcional (para testing), usa singleton si None
        """
        self.strategy_id = strategy_id
        self.strategy_version = strategy_version
        self._bus = bus
        
        self.signals_generated = 0
        self.signals_published = 0
    
    def evaluate(self, data: pd.DataFrame, features: Dict, 
                 instrument: str, horizon: str) -> Optional[InstitutionalSignal]:
        """
        Evalúa setup y genera señal si detecta oportunidad.
        
        DEBE SER SOBRESCRITO por cada estrategia concreta.
        
        Args:
            data: DataFrame OHLCV
            features: Dict de features calculados
            instrument: Instrumento a evaluar
            horizon: Horizonte temporal ('scalp', 'intraday', 'swing')
            
        Returns:
            InstitutionalSignal si hay setup, None si no
        """
        raise NotImplementedError("Estrategia debe implementar evaluate()")
    
    def create_signal(self, 
                      instrument: str,
                      horizon: str,
                      direction: int,
                      confidence: float,
                      entry_price: float,
                      stop_distance_points: float,
                      target_profile: Dict[str, float],
                      regime_sensitivity: Dict[str, float],
                      quality_metrics: Dict[str, float],
                      expected_half_life_seconds: int = 3600,
                      ttl_milliseconds: int = 300000,
                      metadata: Optional[Dict] = None) -> InstitutionalSignal:
        """
        Helper para crear InstitutionalSignal correctamente formateado.
        
        Args:
            instrument: Instrumento
            horizon: Horizonte temporal
            direction: +1 LONG, -1 SHORT
            confidence: Confianza [0, 1]
            entry_price: Precio de entrada
            stop_distance_points: Distancia al stop en points
            target_profile: Dict de targets {name: ratio_R}
            regime_sensitivity: Sensibilidad por régimen
            quality_metrics: Métricas de calidad
            expected_half_life_seconds: Half-life esperado
            ttl_milliseconds: TTL de la señal
            metadata: Metadata adicional
            
        Returns:
            InstitutionalSignal lista para publicar
        """
        # Generar signal_id único
        signal_id = str(ulid.new())
        
        # Metadata con claves obligatorias
        if metadata is None:
            metadata = {}
        
        metadata.setdefault('signal_id', signal_id)
        metadata.setdefault('risk_reward_ratio', list(target_profile.values())[0] if target_profile else 1.5)
        metadata.setdefault('execution_style', 'aggressive')
        
        signal = InstitutionalSignal(
            instrument=instrument,
            timestamp=datetime.now(),
            horizon=horizon,
            strategy_id=self.strategy_id,
            strategy_version=self.strategy_version,
            direction=direction,
            confidence=confidence,
            expected_half_life_seconds=expected_half_life_seconds,
            ttl_milliseconds=ttl_milliseconds,
            entry_price=entry_price,
            stop_distance_points=stop_distance_points,
            target_profile=target_profile,
            regime_sensitivity=regime_sensitivity,
            quality_metrics=quality_metrics,
            metadata=metadata
        )
        
        self.signals_generated += 1
        
        return signal
    
    def publish_signal(self, signal: InstitutionalSignal) -> bool:
        """
        Publica señal al Signal Bus.
        
        Args:
            signal: Señal a publicar
            
        Returns:
            True si aceptada, False si rechazada
        """
        bus = self._bus or get_signal_bus()
        
        if bus.publish(signal):
            self.signals_published += 1
            logger.info(
                f"STRATEGY_SIGNAL: {self.strategy_id} publicó señal "
                f"{signal.instrument} {signal.direction:+d}"
            )
            return True
        else:
            logger.warning(
                f"STRATEGY_SIGNAL_REJECTED: {self.strategy_id} señal rechazada por bus"
            )
            return False
    
    def get_stats(self) -> Dict:
        """Retorna estadísticas de la estrategia."""
        return {
            'strategy_id': self.strategy_id,
            'signals_generated': self.signals_generated,
            'signals_published': self.signals_published,
            'publish_rate': self.signals_published / self.signals_generated if self.signals_generated > 0 else 0.0
        }

