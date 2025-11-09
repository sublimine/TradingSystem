"""
Circuit Breakers - Sistema de circuit breakers para prevenir pérdidas catastróficas
Monitorea condiciones anómalas y pausa trading automáticamente.
"""

import logging
from typing import Dict, Optional, Callable
from datetime import datetime, date
from enum import Enum
from dataclasses import dataclass

logger = logging.getLogger(__name__)


class BreakerType(Enum):
    """Tipos de circuit breaker."""
    DAILY_LOSS = "daily_loss"
    REJECT_RATE = "reject_rate"
    EXPOSURE = "exposure"
    CLOCK_SKEW = "clock_skew"
    DATA_QUALITY = "data_quality"
    POSITION_LIMIT = "position_limit"


@dataclass
class BreakerConfig:
    """Configuración de un breaker."""
    breaker_type: BreakerType
    threshold: float
    window_minutes: int
    auto_reset: bool
    cooldown_minutes: int


class CircuitBreakerManager:
    """
    Gestor de circuit breakers institucional.
    
    Monitorea:
    - Pérdida diaria máxima
    - Tasa de rechazo de órdenes
    - Exposición total excesiva
    - Clock skew (desincronización)
    - Calidad de datos
    - Límites de posición
    """
    
    def __init__(
        self,
        total_capital: float,
        max_daily_loss_pct: float = 0.02,
        max_reject_rate_pct: float = 0.30,
        max_exposure_pct: float = 0.50,
        max_clock_skew_seconds: float = 1.0,
        min_data_quality_pct: float = 0.80
    ):
        """
        Inicializa circuit breaker manager.
        
        Args:
            total_capital: Capital total
            max_daily_loss_pct: Pérdida diaria máxima (% del capital)
            max_reject_rate_pct: Tasa de rechazo máxima permitida
            max_exposure_pct: Exposición máxima permitida
            max_clock_skew_seconds: Desincronización máxima de reloj
            min_data_quality_pct: Calidad mínima de datos
        """
        self.total_capital = total_capital
        self.max_daily_loss_usd = total_capital * max_daily_loss_pct
        self.max_reject_rate = max_reject_rate_pct
        self.max_exposure_usd = total_capital * max_exposure_pct
        self.max_clock_skew = max_clock_skew_seconds
        self.min_data_quality = min_data_quality_pct
        
        # Estado de breakers
        self._breakers_tripped: Dict[BreakerType, datetime] = {}
        self._daily_pnl = 0.0
        self._current_date = date.today()
        
        # Estadísticas
        self._orders_sent = 0
        self._orders_rejected = 0
        self._data_ticks_received = 0
        self._data_ticks_invalid = 0
        
        logger.info(
            f"CircuitBreakerManager initialized: "
            f"max_daily_loss=${self.max_daily_loss_usd:.2f}, "
            f"max_reject_rate={self.max_reject_rate:.0%}"
        )
    
    def check_all(
        self,
        current_pnl: float,
        current_exposure: float,
        clock_skew_seconds: float
    ) -> tuple[bool, list[BreakerType]]:
        """
        Verifica todos los circuit breakers.
        
        Args:
            current_pnl: P&L realizado actual
            current_exposure: Exposición total actual
            clock_skew_seconds: Desincronización de reloj
            
        Returns:
            (is_trading_allowed, list_of_tripped_breakers)
        """
        tripped = []
        
        # Reset diario
        today = date.today()
        if today != self._current_date:
            self._reset_daily()
            self._current_date = today
        
        # Check daily loss
        if current_pnl <= -self.max_daily_loss_usd:
            if BreakerType.DAILY_LOSS not in self._breakers_tripped:
                self._trip_breaker(
                    BreakerType.DAILY_LOSS,
                    f"Daily loss ${abs(current_pnl):.2f} exceeds limit ${self.max_daily_loss_usd:.2f}"
                )
            tripped.append(BreakerType.DAILY_LOSS)
        
        # Check reject rate
        if self._orders_sent > 0:
            reject_rate = self._orders_rejected / self._orders_sent
            if reject_rate > self.max_reject_rate:
                if BreakerType.REJECT_RATE not in self._breakers_tripped:
                    self._trip_breaker(
                        BreakerType.REJECT_RATE,
                        f"Reject rate {reject_rate:.1%} exceeds limit {self.max_reject_rate:.1%}"
                    )
                tripped.append(BreakerType.REJECT_RATE)
        
        # Check exposure
        if current_exposure > self.max_exposure_usd:
            if BreakerType.EXPOSURE not in self._breakers_tripped:
                self._trip_breaker(
                    BreakerType.EXPOSURE,
                    f"Exposure ${current_exposure:.2f} exceeds limit ${self.max_exposure_usd:.2f}"
                )
            tripped.append(BreakerType.EXPOSURE)
        
        # Check clock skew
        if abs(clock_skew_seconds) > self.max_clock_skew:
            if BreakerType.CLOCK_SKEW not in self._breakers_tripped:
                self._trip_breaker(
                    BreakerType.CLOCK_SKEW,
                    f"Clock skew {clock_skew_seconds:.3f}s exceeds limit {self.max_clock_skew:.3f}s"
                )
            tripped.append(BreakerType.CLOCK_SKEW)
        
        # Check data quality
        if self._data_ticks_received > 0:
            quality = (self._data_ticks_received - self._data_ticks_invalid) / self._data_ticks_received
            if quality < self.min_data_quality:
                if BreakerType.DATA_QUALITY not in self._breakers_tripped:
                    self._trip_breaker(
                        BreakerType.DATA_QUALITY,
                        f"Data quality {quality:.1%} below minimum {self.min_data_quality:.1%}"
                    )
                tripped.append(BreakerType.DATA_QUALITY)
        
        is_allowed = len(tripped) == 0
        
        return is_allowed, tripped
    
    def record_order_sent(self):
        """Registra orden enviada."""
        self._orders_sent += 1
    
    def record_order_rejected(self):
        """Registra orden rechazada."""
        self._orders_rejected += 1
    
    def record_data_tick(self, is_valid: bool):
        """Registra tick de datos."""
        self._data_ticks_received += 1
        if not is_valid:
            self._data_ticks_invalid += 1
    
    def manual_trip(self, reason: str):
        """Dispara kill switch manual."""
        logger.critical(f"MANUAL KILL SWITCH: {reason}")
        self._trip_breaker(BreakerType.POSITION_LIMIT, reason)
    
    def reset_breaker(self, breaker_type: BreakerType):
        """Reset manual de un breaker."""
        if breaker_type in self._breakers_tripped:
            del self._breakers_tripped[breaker_type]
            logger.info(f"Circuit breaker reset: {breaker_type.value}")
    
    def _trip_breaker(self, breaker_type: BreakerType, reason: str):
        """Dispara un circuit breaker."""
        self._breakers_tripped[breaker_type] = datetime.now()
        
        logger.critical(
            f"CIRCUIT BREAKER TRIPPED: {breaker_type.value} - {reason}"
        )
    
    def _reset_daily(self):
        """Reset contadores diarios."""
        logger.info(f"Daily reset for {date.today()}")
        
        self._daily_pnl = 0.0
        self._orders_sent = 0
        self._orders_rejected = 0
        self._data_ticks_received = 0
        self._data_ticks_invalid = 0
        
        # Reset breakers con auto-reset
        # DAILY_LOSS no resetea automáticamente
        if BreakerType.REJECT_RATE in self._breakers_tripped:
            del self._breakers_tripped[BreakerType.REJECT_RATE]
        if BreakerType.DATA_QUALITY in self._breakers_tripped:
            del self._breakers_tripped[BreakerType.DATA_QUALITY]
    
    def get_status(self) -> Dict:
        """Obtiene status de todos los breakers."""
        return {
            'trading_allowed': len(self._breakers_tripped) == 0,
            'tripped_breakers': [b.value for b in self._breakers_tripped.keys()],
            'daily_pnl': self._daily_pnl,
            'orders_sent': self._orders_sent,
            'orders_rejected': self._orders_rejected,
            'reject_rate': (
                self._orders_rejected / self._orders_sent
                if self._orders_sent > 0 else 0
            ),
            'data_quality': (
                (self._data_ticks_received - self._data_ticks_invalid) / self._data_ticks_received
                if self._data_ticks_received > 0 else 1.0
            )
        }