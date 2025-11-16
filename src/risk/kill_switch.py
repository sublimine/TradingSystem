"""
KillSwitch 4-Layer System - PLAN OMEGA FASE 3.3

Sistema de protección de riesgo en 4 capas:
- Layer 1: Per-Trade Risk Limits
- Layer 2: Daily Drawdown Cutoff
- Layer 3: Strategy-Level Circuit Breaker
- Layer 4: Portfolio-Level Emergency Stop

Author: Elite Institutional Trading System
Version: 1.0
"""

from typing import Dict, List, Optional
from datetime import datetime, date, timedelta
from enum import Enum
import logging
from dataclasses import dataclass

logger = logging.getLogger(__name__)


class KillSwitchLayer(Enum):
    """Capas del KillSwitch."""
    LAYER_1_TRADE = "layer_1_trade"
    LAYER_2_DAILY = "layer_2_daily"
    LAYER_3_STRATEGY = "layer_3_strategy"
    LAYER_4_EMERGENCY = "layer_4_emergency"


class KillSwitchStatus(Enum):
    """Estados del KillSwitch."""
    ACTIVE = "active"          # Trading permitido
    LAYER_1_BLOCKED = "layer_1_blocked"  # Trade específico bloqueado
    LAYER_2_BLOCKED = "layer_2_blocked"  # Día bloqueado
    LAYER_3_BLOCKED = "layer_3_blocked"  # Estrategia bloqueada
    LAYER_4_EMERGENCY = "layer_4_emergency"  # Sistema bloqueado


@dataclass
class StrategyStats:
    """Estadísticas de una estrategia para circuit breaker."""
    strategy_name: str
    consecutive_losses: int = 0
    total_trades: int = 0
    winning_trades: int = 0
    losing_trades: int = 0
    total_pnl: float = 0.0
    last_trade_time: Optional[datetime] = None
    is_disabled: bool = False
    disabled_reason: Optional[str] = None
    disabled_until: Optional[datetime] = None


class KillSwitch:
    """
    Sistema KillSwitch de 4 capas para protección de riesgo.

    LAYER 1: Per-Trade Risk Limits
    - Valida cada trade individualmente
    - Rechaza trades con riesgo > 2.5%

    LAYER 2: Daily Drawdown Cutoff
    - Monitorea pérdida diaria
    - Detiene trading si pérdida > límite (default: 5%)
    - Reset automático al día siguiente

    LAYER 3: Strategy-Level Circuit Breaker
    - Deshabilita estrategias con performance pobre
    - Criterios:
      * 5+ pérdidas consecutivas
      * Pérdida acumulada > -200R
      * Win rate < 30% (con min 20 trades)

    LAYER 4: Portfolio-Level Emergency Stop
    - Detiene TODO si drawdown total > límite crítico
    - Default: 15% pérdida total
    - Requiere reset manual
    """

    def __init__(self, config: Dict):
        """
        Inicializar KillSwitch.

        Args:
            config: Configuración del KillSwitch
                - initial_balance: Balance inicial
                - max_risk_per_trade: Riesgo máximo por trade (0.025 = 2.5%)
                - max_daily_loss_pct: Pérdida diaria máxima (0.05 = 5%)
                - max_consecutive_losses: Pérdidas consecutivas antes de deshabilitar (5)
                - max_strategy_loss: Pérdida máxima de estrategia en R (-200)
                - min_win_rate: Win rate mínimo (0.30 = 30%)
                - min_trades_for_wr: Trades mínimos para validar WR (20)
                - emergency_drawdown_pct: Drawdown para emergency stop (0.15 = 15%)
        """
        self.config = config

        # Layer 1: Per-Trade Risk Limits
        self.max_risk_per_trade = config.get('max_risk_per_trade', 0.025)  # 2.5%

        # Layer 2: Daily Drawdown Cutoff
        self.max_daily_loss_pct = config.get('max_daily_loss_pct', 0.05)  # 5%
        self.current_date = date.today()
        self.daily_pnl = 0.0
        self.daily_start_balance = config.get('initial_balance', 10000.0)

        # Layer 3: Strategy-Level Circuit Breaker
        self.max_consecutive_losses = config.get('max_consecutive_losses', 5)
        self.max_strategy_loss = config.get('max_strategy_loss', -200.0)  # -200R
        self.min_win_rate = config.get('min_win_rate', 0.30)  # 30%
        self.min_trades_for_wr = config.get('min_trades_for_wr', 20)
        self.strategy_stats: Dict[str, StrategyStats] = {}

        # Layer 4: Portfolio-Level Emergency Stop
        self.emergency_drawdown_pct = config.get('emergency_drawdown_pct', 0.15)  # 15%
        self.initial_balance = config.get('initial_balance', 10000.0)
        self.current_balance = self.initial_balance
        self.peak_balance = self.initial_balance
        self.emergency_stop_active = False

        # Estado global
        self.status = KillSwitchStatus.ACTIVE
        self.blocked_layers: List[KillSwitchLayer] = []

        logger.info(f"KillSwitch initialized:")
        logger.info(f"  Layer 1: Max risk per trade = {self.max_risk_per_trade:.1%}")
        logger.info(f"  Layer 2: Max daily loss = {self.max_daily_loss_pct:.1%}")
        logger.info(f"  Layer 3: Max consecutive losses = {self.max_consecutive_losses}")
        logger.info(f"  Layer 4: Emergency drawdown = {self.emergency_drawdown_pct:.1%}")

    def validate_trade(self, strategy_name: str, risk_amount: float,
                      entry_price: float) -> tuple[bool, Optional[str]]:
        """
        Validar trade contra TODAS las 4 capas del KillSwitch.

        Args:
            strategy_name: Nombre de la estrategia
            risk_amount: Riesgo del trade en USD
            entry_price: Precio de entrada

        Returns:
            (is_allowed, rejection_reason)
        """
        # LAYER 4: Emergency Stop (check first - overrides everything)
        if self.emergency_stop_active:
            return False, "LAYER 4: Emergency stop active - ALL TRADING DISABLED"

        # LAYER 2: Daily Drawdown Check
        if not self._check_daily_limit():
            return False, f"LAYER 2: Daily loss limit reached ({self.max_daily_loss_pct:.1%})"

        # LAYER 3: Strategy Circuit Breaker
        if self._is_strategy_disabled(strategy_name):
            stats = self.strategy_stats.get(strategy_name)
            return False, f"LAYER 3: Strategy '{strategy_name}' disabled - {stats.disabled_reason}"

        # LAYER 1: Per-Trade Risk Limit
        risk_pct = risk_amount / self.current_balance
        if risk_pct > self.max_risk_per_trade:
            return False, (f"LAYER 1: Trade risk ({risk_pct:.2%}) exceeds maximum "
                          f"({self.max_risk_per_trade:.2%})")

        # Todas las capas pasaron
        return True, None

    def _check_daily_limit(self) -> bool:
        """
        Check Layer 2: Daily drawdown limit.

        Returns:
            True if trading allowed for the day
        """
        # Reset diario si cambió la fecha
        today = date.today()
        if today != self.current_date:
            self._reset_daily()

        # Calcular pérdida del día
        daily_loss_pct = abs(self.daily_pnl) / self.daily_start_balance

        # Si pérdida excede límite, bloquear día
        if self.daily_pnl < 0 and daily_loss_pct >= self.max_daily_loss_pct:
            if KillSwitchStatus.LAYER_2_BLOCKED not in self.blocked_layers:
                logger.warning(f"⚠️  LAYER 2 TRIGGERED: Daily loss {daily_loss_pct:.2%} "
                             f">= limit {self.max_daily_loss_pct:.2%}")
                logger.warning(f"   Trading DISABLED for rest of day")
                self.status = KillSwitchStatus.LAYER_2_BLOCKED
                self.blocked_layers.append(KillSwitchLayer.LAYER_2_DAILY)
            return False

        return True

    def _is_strategy_disabled(self, strategy_name: str) -> bool:
        """
        Check Layer 3: Strategy circuit breaker.

        Returns:
            True if strategy is disabled
        """
        if strategy_name not in self.strategy_stats:
            return False

        stats = self.strategy_stats[strategy_name]

        # Si está deshabilitada, verificar si ya pasó el tiempo
        if stats.is_disabled:
            if stats.disabled_until and datetime.now() >= stats.disabled_until:
                # Re-habilitar estrategia
                logger.info(f"✅ Strategy '{strategy_name}' re-enabled (timeout expired)")
                stats.is_disabled = False
                stats.disabled_reason = None
                stats.disabled_until = None
                return False
            return True

        return False

    def record_trade_result(self, strategy_name: str, pnl: float,
                           is_winner: bool) -> None:
        """
        Registrar resultado de trade y actualizar KillSwitch.

        Args:
            strategy_name: Nombre de la estrategia
            pnl: P&L del trade en USD
            is_winner: True si fue ganador
        """
        # Actualizar balance y daily P&L
        self.current_balance += pnl
        self.daily_pnl += pnl

        # Actualizar peak balance (para Layer 4)
        if self.current_balance > self.peak_balance:
            self.peak_balance = self.current_balance

        # Actualizar estadísticas de estrategia
        if strategy_name not in self.strategy_stats:
            self.strategy_stats[strategy_name] = StrategyStats(strategy_name=strategy_name)

        stats = self.strategy_stats[strategy_name]
        stats.total_trades += 1
        stats.total_pnl += pnl
        stats.last_trade_time = datetime.now()

        if is_winner:
            stats.winning_trades += 1
            stats.consecutive_losses = 0  # Reset racha perdedora
        else:
            stats.losing_trades += 1
            stats.consecutive_losses += 1

        # LAYER 3: Check strategy circuit breaker conditions
        self._check_strategy_circuit_breaker(strategy_name)

        # LAYER 4: Check emergency stop
        self._check_emergency_stop()

    def _check_strategy_circuit_breaker(self, strategy_name: str) -> None:
        """
        Verificar si estrategia debe ser deshabilitada (Layer 3).

        Criterios:
        1. Pérdidas consecutivas >= max_consecutive_losses
        2. Pérdida total <= max_strategy_loss (en R o USD)
        3. Win rate < min_win_rate (con min trades)
        """
        stats = self.strategy_stats[strategy_name]

        if stats.is_disabled:
            return  # Ya deshabilitada

        # Criterio 1: Pérdidas consecutivas
        if stats.consecutive_losses >= self.max_consecutive_losses:
            reason = f"{stats.consecutive_losses} consecutive losses"
            self._disable_strategy(strategy_name, reason, hours=24)
            return

        # Criterio 2: Pérdida total excesiva
        if stats.total_pnl <= self.max_strategy_loss:
            reason = f"Total loss ${stats.total_pnl:.2f} <= ${self.max_strategy_loss:.2f}"
            self._disable_strategy(strategy_name, reason, hours=48)
            return

        # Criterio 3: Win rate muy bajo
        if stats.total_trades >= self.min_trades_for_wr:
            win_rate = stats.winning_trades / stats.total_trades
            if win_rate < self.min_win_rate:
                reason = f"Win rate {win_rate:.1%} < {self.min_win_rate:.1%}"
                self._disable_strategy(strategy_name, reason, hours=72)
                return

    def _disable_strategy(self, strategy_name: str, reason: str, hours: int = 24) -> None:
        """
        Deshabilitar estrategia (Layer 3).

        Args:
            strategy_name: Nombre de la estrategia
            reason: Razón de deshabilitación
            hours: Horas hasta re-habilitación automática
        """
        stats = self.strategy_stats[strategy_name]
        stats.is_disabled = True
        stats.disabled_reason = reason
        stats.disabled_until = datetime.now() + timedelta(hours=hours)

        logger.warning(f"🚨 LAYER 3 TRIGGERED: Strategy '{strategy_name}' DISABLED")
        logger.warning(f"   Reason: {reason}")
        logger.warning(f"   Disabled until: {stats.disabled_until.strftime('%Y-%m-%d %H:%M')}")
        logger.warning(f"   Stats: {stats.total_trades} trades, "
                      f"{stats.winning_trades}W-{stats.losing_trades}L, "
                      f"P&L=${stats.total_pnl:.2f}")

    def _check_emergency_stop(self) -> None:
        """
        Verificar condiciones para emergency stop (Layer 4).

        Emergency stop si drawdown >= emergency_drawdown_pct
        """
        if self.emergency_stop_active:
            return  # Ya activo

        # Calcular drawdown actual
        drawdown = (self.peak_balance - self.current_balance) / self.peak_balance

        if drawdown >= self.emergency_drawdown_pct:
            self.emergency_stop_active = True
            self.status = KillSwitchStatus.LAYER_4_EMERGENCY
            self.blocked_layers.append(KillSwitchLayer.LAYER_4_EMERGENCY)

            logger.critical(f"🛑 LAYER 4 EMERGENCY STOP TRIGGERED!")
            logger.critical(f"   Drawdown: {drawdown:.2%} >= {self.emergency_drawdown_pct:.2%}")
            logger.critical(f"   Peak balance: ${self.peak_balance:.2f}")
            logger.critical(f"   Current balance: ${self.current_balance:.2f}")
            logger.critical(f"   Loss: ${self.peak_balance - self.current_balance:.2f}")
            logger.critical(f"   ⛔ ALL TRADING STOPPED - MANUAL RESET REQUIRED")

    def _reset_daily(self) -> None:
        """Reset diario para Layer 2."""
        old_date = self.current_date
        self.current_date = date.today()
        self.daily_pnl = 0.0
        self.daily_start_balance = self.current_balance

        # Remover bloqueo Layer 2 si estaba activo
        if KillSwitchLayer.LAYER_2_DAILY in self.blocked_layers:
            self.blocked_layers.remove(KillSwitchLayer.LAYER_2_DAILY)
            logger.info(f"✅ Daily reset: Layer 2 unblocked (new day)")

        # Si solo Layer 2 estaba bloqueado, reactivar
        if not self.blocked_layers:
            self.status = KillSwitchStatus.ACTIVE

        logger.info(f"Daily reset: {old_date} → {self.current_date}")
        logger.info(f"  Starting balance: ${self.daily_start_balance:.2f}")

    def reset_emergency_stop(self, reason: str) -> bool:
        """
        Reset manual del emergency stop (Layer 4).

        ⚠️ SOLO usar después de análisis exhaustivo.

        Args:
            reason: Razón del reset (logged)

        Returns:
            True si reset exitoso
        """
        if not self.emergency_stop_active:
            logger.warning("Emergency stop not active - nothing to reset")
            return False

        logger.warning(f"⚠️  EMERGENCY STOP RESET REQUESTED")
        logger.warning(f"   Reason: {reason}")
        logger.warning(f"   Resetting by: MANUAL INTERVENTION")

        self.emergency_stop_active = False

        if KillSwitchLayer.LAYER_4_EMERGENCY in self.blocked_layers:
            self.blocked_layers.remove(KillSwitchLayer.LAYER_4_EMERGENCY)

        # Reactivar si no hay otros bloqueos
        if not self.blocked_layers:
            self.status = KillSwitchStatus.ACTIVE

        logger.info("✅ Emergency stop reset - trading re-enabled")
        return True

    def get_status(self) -> Dict:
        """
        Obtener estado completo del KillSwitch.

        Returns:
            Dict con status de todas las capas
        """
        return {
            'status': self.status.value,
            'emergency_stop_active': self.emergency_stop_active,
            'blocked_layers': [layer.value for layer in self.blocked_layers],

            # Layer 1
            'layer_1': {
                'max_risk_per_trade': self.max_risk_per_trade,
            },

            # Layer 2
            'layer_2': {
                'current_date': str(self.current_date),
                'daily_pnl': self.daily_pnl,
                'daily_start_balance': self.daily_start_balance,
                'max_daily_loss_pct': self.max_daily_loss_pct,
                'daily_loss_pct': abs(self.daily_pnl) / self.daily_start_balance if self.daily_pnl < 0 else 0.0,
            },

            # Layer 3
            'layer_3': {
                'total_strategies': len(self.strategy_stats),
                'disabled_strategies': sum(1 for s in self.strategy_stats.values() if s.is_disabled),
                'strategies': {
                    name: {
                        'total_trades': stats.total_trades,
                        'winning_trades': stats.winning_trades,
                        'losing_trades': stats.losing_trades,
                        'consecutive_losses': stats.consecutive_losses,
                        'total_pnl': stats.total_pnl,
                        'win_rate': stats.winning_trades / stats.total_trades if stats.total_trades > 0 else 0.0,
                        'is_disabled': stats.is_disabled,
                        'disabled_reason': stats.disabled_reason,
                        'disabled_until': str(stats.disabled_until) if stats.disabled_until else None
                    }
                    for name, stats in self.strategy_stats.items()
                }
            },

            # Layer 4
            'layer_4': {
                'initial_balance': self.initial_balance,
                'current_balance': self.current_balance,
                'peak_balance': self.peak_balance,
                'drawdown_pct': (self.peak_balance - self.current_balance) / self.peak_balance,
                'emergency_drawdown_pct': self.emergency_drawdown_pct,
            }
        }

    def is_trading_allowed(self) -> bool:
        """
        Verificar si trading está permitido globalmente.

        Returns:
            True si se puede operar
        """
        return self.status == KillSwitchStatus.ACTIVE and not self.emergency_stop_active
