"""
Kill Switch Institucional - Sistema de seguridad multi-capa para LIVE trading

Sistema de protección con 4 capas independientes:
1. Operador (flag manual)
2. Risk/Drawdown (circuit breakers)
3. Broker Health (conectividad, latencia, heartbeat)
4. Data Integrity (validación de ticks, microestructura)

CRITICAL: Todas las capas deben estar OK para permitir órdenes LIVE.
Si CUALQUIER capa falla → KILL SWITCH ACTIVADO → NO se envían órdenes reales.

Author: SUBLIMINE Institutional Trading System
Date: 2025-11-14
Mandato: MANDATO 23 - Live Execution & Kill Switch
"""

import logging
from typing import Dict, List, Optional
from datetime import datetime, timedelta
from enum import Enum
from dataclasses import dataclass
import time

logger = logging.getLogger(__name__)


class KillSwitchState(Enum):
    """Estados del kill switch."""
    OPERATIONAL = "operational"                    # Todo OK, trading permitido
    DISABLED_BY_OPERATOR = "disabled_by_operator"  # Operador desactivó LIVE
    RISK_BREACH = "risk_breach"                    # Circuit breaker activado
    BROKER_UNHEALTHY = "broker_unhealthy"          # Problema conectividad broker
    DATA_INTEGRITY_FAIL = "data_integrity_fail"    # Datos corruptos/inconsistentes
    EMERGENCY_STOP = "emergency_stop"              # Stop manual de emergencia


class HealthCheckResult(Enum):
    """Resultados de health check."""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"


@dataclass
class KillSwitchStatus:
    """Status completo del kill switch."""
    state: KillSwitchState
    is_trading_allowed: bool
    timestamp: datetime
    operator_enabled: bool
    risk_healthy: bool
    broker_healthy: bool
    data_healthy: bool
    failed_layers: List[str]
    reason: Optional[str] = None


class KillSwitch:
    """
    Kill Switch Institucional Multi-Capa.

    Features:
    - 4 capas de validación independientes
    - Logging crítico de todos los cambios de estado
    - Heartbeat tracking para broker
    - Validación de integridad de datos
    - Stop manual de emergencia
    - Integración con CircuitBreakerManager

    Usage:
        kill_switch = KillSwitch(config)

        # Antes de CADA orden LIVE:
        if kill_switch.can_send_orders():
            # Enviar orden al broker
            pass
        else:
            logger.critical(f"KILL SWITCH ACTIVE: {kill_switch.get_state()}")
    """

    def __init__(
        self,
        config: Dict,
        circuit_breaker_manager: Optional[object] = None
    ):
        """
        Inicializa Kill Switch.

        Args:
            config: Configuración del sistema
            circuit_breaker_manager: CircuitBreakerManager existente (opcional)
        """
        self.config = config
        self.circuit_breaker_manager = circuit_breaker_manager

        # Capa 1: Operador
        self.operator_enabled = config.get('live_trading', {}).get('enabled', False)

        # Capa 2: Risk (delegado a CircuitBreakerManager)
        self.risk_healthy = True

        # Capa 3: Broker Health
        self.broker_healthy = False
        self.last_broker_ping_time = None
        self.last_broker_latency_ms = None
        self.max_allowed_latency_ms = config.get('live_trading', {}).get('max_latency_ms', 500)
        self.max_ping_age_seconds = config.get('live_trading', {}).get('max_ping_age_seconds', 30)

        # Capa 4: Data Integrity
        self.data_healthy = True
        self.last_tick_validation_time = None
        self.corrupted_ticks_count = 0
        self.max_corrupted_ticks = config.get('live_trading', {}).get('max_corrupted_ticks', 10)

        # Emergency stop
        self.emergency_stop_active = False
        self.emergency_stop_reason = None

        # Estado actual
        self.current_state = KillSwitchState.DISABLED_BY_OPERATOR if not self.operator_enabled else KillSwitchState.OPERATIONAL

        logger.info(
            f"KillSwitch initialized - "
            f"operator_enabled={self.operator_enabled}, "
            f"max_latency={self.max_allowed_latency_ms}ms"
        )

        if not self.operator_enabled:
            logger.critical(
                "⚠️  KILL SWITCH: LIVE TRADING DISABLED BY CONFIG ⚠️"
            )

    def can_send_orders(self) -> bool:
        """
        Verifica si se pueden enviar órdenes LIVE.

        CRITICAL: Este método DEBE ser llamado ANTES de cada orden LIVE.

        Returns:
            True si TODAS las capas están OK, False si CUALQUIERA falla
        """
        # Update state
        self._update_state()

        # Trading permitido SOLO si estado es OPERATIONAL
        allowed = (self.current_state == KillSwitchState.OPERATIONAL)

        if not allowed:
            logger.warning(
                f"KILL SWITCH BLOCKING ORDERS: {self.current_state.value}"
            )

        return allowed

    def get_state(self) -> KillSwitchState:
        """
        Obtiene estado actual del kill switch.

        Returns:
            KillSwitchState actual
        """
        self._update_state()
        return self.current_state

    def get_status(self) -> KillSwitchStatus:
        """
        Obtiene status completo y detallado.

        Returns:
            KillSwitchStatus con todos los detalles
        """
        self._update_state()

        failed_layers = []
        reason = None

        if not self.operator_enabled:
            failed_layers.append("OPERATOR")
            reason = "Live trading disabled by operator config"

        if not self.risk_healthy:
            failed_layers.append("RISK")
            reason = "Circuit breaker tripped"

        if not self.broker_healthy:
            failed_layers.append("BROKER")
            reason = f"Broker unhealthy (last ping: {self.last_broker_ping_time})"

        if not self.data_healthy:
            failed_layers.append("DATA")
            reason = f"Data integrity fail ({self.corrupted_ticks_count} corrupted ticks)"

        if self.emergency_stop_active:
            failed_layers.append("EMERGENCY")
            reason = f"Emergency stop: {self.emergency_stop_reason}"

        return KillSwitchStatus(
            state=self.current_state,
            is_trading_allowed=(self.current_state == KillSwitchState.OPERATIONAL),
            timestamp=datetime.now(),
            operator_enabled=self.operator_enabled,
            risk_healthy=self.risk_healthy,
            broker_healthy=self.broker_healthy,
            data_healthy=self.data_healthy,
            failed_layers=failed_layers,
            reason=reason if failed_layers else "All layers operational"
        )

    # ========================================================================
    # CAPA 1: OPERADOR
    # ========================================================================

    def enable_live_trading(self):
        """
        Habilita LIVE trading (requiere confirmación manual).

        WARNING: Solo debe ser llamado por operador autorizado.
        """
        logger.critical(
            "⚠️⚠️⚠️  LIVE TRADING BEING ENABLED BY OPERATOR  ⚠️⚠️⚠️"
        )
        self.operator_enabled = True
        self._update_state()

    def disable_live_trading(self, reason: str = "Manual disable"):
        """
        Desactiva LIVE trading.

        Args:
            reason: Razón de desactivación
        """
        logger.critical(
            f"⚠️  LIVE TRADING DISABLED BY OPERATOR: {reason}  ⚠️"
        )
        self.operator_enabled = False
        self._update_state()

    # ========================================================================
    # CAPA 2: RISK / CIRCUIT BREAKERS
    # ========================================================================

    def update_risk_health(
        self,
        current_pnl: float,
        current_exposure: float,
        tripped_breakers: List
    ):
        """
        Actualiza estado de riesgo.

        Args:
            current_pnl: P&L actual
            current_exposure: Exposición actual
            tripped_breakers: Lista de breakers activados
        """
        # Si hay algún breaker activado → RISK UNHEALTHY
        if len(tripped_breakers) > 0:
            if self.risk_healthy:
                logger.critical(
                    f"KILL SWITCH - RISK BREACH: {tripped_breakers}"
                )
            self.risk_healthy = False
        else:
            if not self.risk_healthy:
                logger.info("Risk health restored")
            self.risk_healthy = True

        self._update_state()

    # ========================================================================
    # CAPA 3: BROKER HEALTH
    # ========================================================================

    def record_broker_ping(self, latency_ms: float, is_connected: bool):
        """
        Registra ping al broker.

        Args:
            latency_ms: Latencia en ms
            is_connected: Si la conexión está activa
        """
        self.last_broker_ping_time = datetime.now()
        self.last_broker_latency_ms = latency_ms

        # Check latency
        if latency_ms > self.max_allowed_latency_ms:
            logger.warning(
                f"High broker latency: {latency_ms:.0f}ms "
                f"(max={self.max_allowed_latency_ms}ms)"
            )
            self.broker_healthy = False
        elif not is_connected:
            logger.critical("Broker disconnected")
            self.broker_healthy = False
        else:
            self.broker_healthy = True

        self._update_state()

    def check_broker_heartbeat(self) -> bool:
        """
        Verifica que el heartbeat del broker sea reciente.

        Returns:
            True si heartbeat es reciente, False si está stale
        """
        if self.last_broker_ping_time is None:
            logger.warning("No broker ping recorded yet")
            return False

        age = (datetime.now() - self.last_broker_ping_time).total_seconds()

        if age > self.max_ping_age_seconds:
            logger.critical(
                f"Broker heartbeat stale: {age:.1f}s "
                f"(max={self.max_ping_age_seconds}s)"
            )
            self.broker_healthy = False
            self._update_state()
            return False

        return True

    # ========================================================================
    # CAPA 4: DATA INTEGRITY
    # ========================================================================

    def validate_tick(
        self,
        symbol: str,
        bid: float,
        ask: float,
        timestamp: datetime
    ) -> bool:
        """
        Valida integridad de un tick.

        Args:
            symbol: Símbolo
            bid: Precio bid
            ask: Precio ask
            timestamp: Timestamp del tick

        Returns:
            True si tick es válido, False si está corrupto
        """
        self.last_tick_validation_time = datetime.now()

        is_valid = True

        # Validaciones básicas
        if bid <= 0 or ask <= 0:
            logger.error(f"Invalid prices: bid={bid}, ask={ask}")
            is_valid = False

        if bid >= ask:
            logger.error(f"Inverted spread: bid={bid} >= ask={ask}")
            is_valid = False

        # Check spread anormal
        spread_pct = (ask - bid) / bid
        if spread_pct > 0.01:  # 1% spread = anormal
            logger.warning(f"Abnormal spread: {spread_pct:.2%}")
            is_valid = False

        # Check timestamp
        tick_age = (datetime.now() - timestamp).total_seconds()
        if tick_age > 10:  # Tick de más de 10s
            logger.warning(f"Stale tick: {tick_age:.1f}s old")
            is_valid = False

        # Update counter
        if not is_valid:
            self.corrupted_ticks_count += 1

            if self.corrupted_ticks_count >= self.max_corrupted_ticks:
                logger.critical(
                    f"DATA INTEGRITY FAIL: {self.corrupted_ticks_count} "
                    f"corrupted ticks"
                )
                self.data_healthy = False
        else:
            # Decaer contador de ticks corruptos
            self.corrupted_ticks_count = max(0, self.corrupted_ticks_count - 1)

            # Restaurar health si estaba degradado
            if self.corrupted_ticks_count < self.max_corrupted_ticks / 2:
                if not self.data_healthy:
                    logger.info("Data integrity restored")
                self.data_healthy = True

        self._update_state()
        return is_valid

    def validate_multiframe_consistency(
        self,
        htf_data: Dict,
        mtf_data: Dict,
        ltf_data: Dict
    ) -> bool:
        """
        Valida consistencia entre timeframes.

        Args:
            htf_data: Datos HTF
            mtf_data: Datos MTF
            ltf_data: Datos LTF

        Returns:
            True si datos son consistentes, False si inconsistentes
        """
        # Placeholder: implementar validación de consistencia
        # Por ahora retorna True
        return True

    # ========================================================================
    # EMERGENCY STOP
    # ========================================================================

    def emergency_stop(self, reason: str):
        """
        Activa stop de emergencia INMEDIATO.

        Args:
            reason: Razón del emergency stop
        """
        logger.critical(
            f"🚨🚨🚨  EMERGENCY STOP ACTIVATED: {reason}  🚨🚨🚨"
        )

        self.emergency_stop_active = True
        self.emergency_stop_reason = reason
        self._update_state()

    def reset_emergency_stop(self):
        """
        Resetea emergency stop (requiere confirmación operador).
        """
        logger.critical(
            "Emergency stop being RESET by operator"
        )

        self.emergency_stop_active = False
        self.emergency_stop_reason = None
        self._update_state()

    # ========================================================================
    # INTERNAL
    # ========================================================================

    def _update_state(self):
        """Actualiza estado del kill switch basado en todas las capas."""
        old_state = self.current_state

        # Priority order (más crítico primero):
        if self.emergency_stop_active:
            self.current_state = KillSwitchState.EMERGENCY_STOP
        elif not self.operator_enabled:
            self.current_state = KillSwitchState.DISABLED_BY_OPERATOR
        elif not self.risk_healthy:
            self.current_state = KillSwitchState.RISK_BREACH
        elif not self.broker_healthy:
            self.current_state = KillSwitchState.BROKER_UNHEALTHY
        elif not self.data_healthy:
            self.current_state = KillSwitchState.DATA_INTEGRITY_FAIL
        else:
            # TODAS las capas OK
            self.current_state = KillSwitchState.OPERATIONAL

        # Log si cambió el estado
        if old_state != self.current_state:
            logger.critical(
                f"KILL SWITCH STATE CHANGE: {old_state.value} → {self.current_state.value}"
            )

    def get_diagnostics(self) -> Dict:
        """
        Obtiene diagnóstico completo para debugging.

        Returns:
            Dict con todos los detalles internos
        """
        return {
            'current_state': self.current_state.value,
            'is_trading_allowed': self.can_send_orders(),
            'layers': {
                'operator': {
                    'enabled': self.operator_enabled
                },
                'risk': {
                    'healthy': self.risk_healthy
                },
                'broker': {
                    'healthy': self.broker_healthy,
                    'last_ping': self.last_broker_ping_time.isoformat() if self.last_broker_ping_time else None,
                    'latency_ms': self.last_broker_latency_ms,
                    'max_latency_ms': self.max_allowed_latency_ms
                },
                'data': {
                    'healthy': self.data_healthy,
                    'corrupted_ticks': self.corrupted_ticks_count,
                    'max_corrupted_ticks': self.max_corrupted_ticks,
                    'last_validation': self.last_tick_validation_time.isoformat() if self.last_tick_validation_time else None
                },
                'emergency': {
                    'active': self.emergency_stop_active,
                    'reason': self.emergency_stop_reason
                }
            },
            'timestamp': datetime.now().isoformat()
        }
