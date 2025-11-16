"""
ExecutionManager - PLAN OMEGA FASE 3.2

Gestor centralizado de ejecución de órdenes.
Coordina el uso de brokers PAPER o LIVE según ExecutionMode.

Features:
- Gestión unificada de órdenes
- Conversión de señales a órdenes
- Validación de riesgo pre-ejecución
- Tracking de posiciones
- Estadísticas de trading

Author: Elite Institutional Trading System
Version: 1.0
"""

from typing import Dict, List, Optional
from datetime import datetime
import logging
import uuid

from .execution_mode import ExecutionMode, ExecutionConfig
from .broker_adapter import BrokerAdapter, Order, Position
from .paper_broker import PaperBrokerAdapter
from .live_broker import LiveBrokerAdapter
from src.strategies.strategy_base import Signal
from src.risk import KillSwitch

logger = logging.getLogger(__name__)


class ExecutionManager:
    """
    Gestor de ejecución de órdenes.

    Coordina la ejecución de señales de trading en modo PAPER o LIVE.
    Proporciona interfaz unificada independiente del broker usado.
    """

    def __init__(self, execution_config: ExecutionConfig, enable_kill_switch: bool = True):
        """
        Inicializar gestor de ejecución.

        Args:
            execution_config: Configuración de ejecución
            enable_kill_switch: Si True, activa KillSwitch 4-Layer (default: True)
        """
        self.config = execution_config
        self.mode = execution_config.mode
        self.broker: Optional[BrokerAdapter] = None

        # Inicializar broker según modo
        self._initialize_broker()

        # Initialize KillSwitch (PLAN OMEGA FASE 3.3)
        self.kill_switch: Optional[KillSwitch] = None
        if enable_kill_switch:
            kill_switch_config = {
                'initial_balance': execution_config.initial_capital,
                'max_risk_per_trade': execution_config.max_risk_per_trade,
                'max_daily_loss_pct': execution_config.max_daily_loss,
                'max_consecutive_losses': 5,
                'max_strategy_loss': -200.0,
                'min_win_rate': 0.30,
                'min_trades_for_wr': 20,
                'emergency_drawdown_pct': 0.15
            }
            self.kill_switch = KillSwitch(kill_switch_config)
            logger.info("✅ KillSwitch 4-Layer System activated")
        else:
            logger.warning("⚠️  KillSwitch DISABLED - trading without protection")

        # Tracking
        self.signals_received = 0
        self.orders_submitted = 0
        self.orders_rejected = 0

        logger.info(f"ExecutionManager initialized in {self.mode} mode")

    def _initialize_broker(self):
        """Inicializar broker según ExecutionMode."""
        if self.mode == ExecutionMode.PAPER:
            # Modo PAPER - usar broker simulado
            broker_config = {
                'initial_capital': self.config.initial_capital,
                'slippage_pips': 0.5,
                'spread_pips': {'EURUSD': 1.0, 'GBPUSD': 1.5, 'USDJPY': 1.0},
                'commission_per_lot': 7.0
            }
            self.broker = PaperBrokerAdapter(broker_config)
            logger.info("✅ PaperBroker initialized")

        elif self.mode == ExecutionMode.LIVE:
            # Modo LIVE - usar broker real
            if not self.config.broker_config:
                raise ValueError("broker_config required for LIVE mode")

            self.broker = LiveBrokerAdapter(self.config.broker_config)
            logger.warning("⚠️  LiveBroker initialized - REAL MONEY MODE")

        else:
            raise ValueError(f"Invalid execution mode: {self.mode}")

        # Conectar al broker
        if not self.broker.connect():
            raise RuntimeError(f"Failed to connect to {self.mode} broker")

    def execute_signal(self, signal: Signal, current_price: float) -> bool:
        """
        Ejecutar señal de trading.

        Convierte señal a orden y la envía al broker.

        PLAN OMEGA FASE 3.3: Validación con KillSwitch 4-Layer

        Args:
            signal: Señal generada por estrategia
            current_price: Precio actual del mercado

        Returns:
            True si orden ejecutada exitosamente
        """
        self.signals_received += 1

        try:
            # Validar señal
            if not self._validate_signal(signal):
                logger.warning(f"Signal validation failed: {signal.strategy_name}")
                self.orders_rejected += 1
                return False

            # Calcular tamaño de posición y riesgo
            position_size = self._calculate_position_size(signal, current_price)

            if position_size <= 0:
                logger.warning(f"Invalid position size: {position_size}")
                self.orders_rejected += 1
                return False

            # Calcular riesgo en USD
            risk_amount = abs(current_price - signal.stop_loss) * position_size * 100000

            # KILLSWITCH VALIDATION (FASE 3.3)
            if self.kill_switch:
                is_allowed, rejection_reason = self.kill_switch.validate_trade(
                    strategy_name=signal.strategy_name,
                    risk_amount=risk_amount,
                    entry_price=current_price
                )

                if not is_allowed:
                    logger.warning(f"🛑 KILLSWITCH BLOCKED: {rejection_reason}")
                    self.orders_rejected += 1
                    return False

            # Crear orden
            order = Order(
                order_id=f"ORD_{uuid.uuid4().hex[:12]}",
                symbol=signal.symbol,
                direction=signal.direction,
                entry_price=current_price,
                stop_loss=signal.stop_loss,
                take_profit=signal.take_profit,
                position_size=position_size,
                strategy_name=signal.strategy_name,
                timestamp=datetime.now(),
                metadata=signal.metadata
            )

            # Enviar orden al broker
            success = self.broker.submit_order(order)

            if success:
                self.orders_submitted += 1
                logger.info(f"✅ Signal executed: {signal.strategy_name} - {signal.direction} {signal.symbol}")
            else:
                self.orders_rejected += 1
                logger.warning(f"❌ Order rejected by broker: {signal.strategy_name}")

            return success

        except Exception as e:
            logger.error(f"Failed to execute signal: {e}", exc_info=True)
            self.orders_rejected += 1
            return False

    def execute_signals(self, signals: List[Signal], market_prices: Dict[str, float]) -> int:
        """
        Ejecutar múltiples señales.

        Args:
            signals: Lista de señales
            market_prices: Precios actuales {symbol: price}

        Returns:
            Número de señales ejecutadas exitosamente
        """
        executed = 0

        for signal in signals:
            # Obtener precio actual del símbolo
            current_price = market_prices.get(signal.symbol)

            if current_price is None:
                logger.warning(f"No market price for {signal.symbol} - skipping signal")
                continue

            # Validar límite de posiciones
            if len(self.broker.get_positions()) >= self.config.max_positions:
                logger.warning(f"Max positions reached ({self.config.max_positions}) - skipping signal")
                continue

            # Ejecutar señal
            if self.execute_signal(signal, current_price):
                executed += 1

        return executed

    def update_positions(self, market_data: Dict):
        """
        Actualizar posiciones con datos de mercado.

        Args:
            market_data: Datos actuales del mercado
        """
        if self.broker:
            # Guardar cantidad de posiciones antes
            positions_before = len(self.broker.get_positions())

            # Actualizar posiciones (puede cerrar posiciones por SL/TP)
            self.broker.update_positions(market_data)

            # Sincronizar con KillSwitch si hay posiciones cerradas
            positions_after = len(self.broker.get_positions())
            if positions_before > positions_after:
                self._sync_killswitch_with_broker()

    def _sync_killswitch_with_broker(self):
        """
        Sincronizar KillSwitch con posiciones cerradas del broker.

        PLAN OMEGA FASE 3.3: Actualizar KillSwitch con resultados de trades
        """
        if not self.kill_switch:
            return

        # Solo funciona con PaperBroker por ahora
        if not isinstance(self.broker, PaperBrokerAdapter):
            return

        # Obtener posiciones cerradas recientes
        if hasattr(self.broker, 'closed_positions'):
            for closed_pos in self.broker.closed_positions:
                # Verificar si ya fue procesada por KillSwitch
                if closed_pos.get('_killswitch_processed'):
                    continue

                strategy_name = closed_pos.get('strategy_name', 'unknown')
                pnl = closed_pos.get('pnl', 0.0)
                is_winner = pnl > 0

                # Registrar en KillSwitch
                self.kill_switch.record_trade_result(
                    strategy_name=strategy_name,
                    pnl=pnl,
                    is_winner=is_winner
                )

                # Marcar como procesada
                closed_pos['_killswitch_processed'] = True

                logger.debug(f"KillSwitch updated: {strategy_name}, P&L=${pnl:.2f}, "
                           f"Winner={is_winner}")

    def get_positions(self) -> List[Position]:
        """
        Obtener todas las posiciones abiertas.

        Returns:
            Lista de posiciones
        """
        if self.broker:
            return self.broker.get_positions()
        return []

    def close_position(self, position_id: str) -> bool:
        """
        Cerrar posición manualmente.

        Args:
            position_id: ID de la posición

        Returns:
            True si posición cerrada
        """
        if self.broker:
            return self.broker.close_position(position_id)
        return False

    def close_all_positions(self) -> int:
        """
        Cerrar todas las posiciones abiertas.

        Returns:
            Número de posiciones cerradas
        """
        positions = self.get_positions()
        closed = 0

        for position in positions:
            if self.close_position(position.position_id):
                closed += 1

        logger.info(f"Closed {closed}/{len(positions)} positions")
        return closed

    def get_account_balance(self) -> float:
        """Obtener balance de la cuenta."""
        if self.broker:
            return self.broker.get_account_balance()
        return 0.0

    def get_account_equity(self) -> float:
        """Obtener equity de la cuenta."""
        if self.broker:
            return self.broker.get_account_equity()
        return 0.0

    def _validate_signal(self, signal: Signal) -> bool:
        """
        Validar señal antes de ejecutar.

        Args:
            signal: Señal a validar

        Returns:
            True si señal es válida
        """
        # Validar campos obligatorios
        if not signal.symbol or not signal.direction:
            return False

        if signal.direction not in ['LONG', 'SHORT']:
            return False

        # Validar SL y TP
        if signal.direction == 'LONG':
            if signal.stop_loss >= signal.entry_price:
                logger.warning(f"Invalid SL for LONG: SL ({signal.stop_loss}) >= entry ({signal.entry_price})")
                return False
            if signal.take_profit <= signal.entry_price:
                logger.warning(f"Invalid TP for LONG: TP ({signal.take_profit}) <= entry ({signal.entry_price})")
                return False
        else:  # SHORT
            if signal.stop_loss <= signal.entry_price:
                logger.warning(f"Invalid SL for SHORT: SL ({signal.stop_loss}) <= entry ({signal.entry_price})")
                return False
            if signal.take_profit >= signal.entry_price:
                logger.warning(f"Invalid TP for SHORT: TP ({signal.take_profit}) >= entry ({signal.entry_price})")
                return False

        # Validar riesgo máximo (2.5% PLAN OMEGA)
        risk = abs(signal.entry_price - signal.stop_loss)
        risk_pct = risk / signal.entry_price

        if risk_pct > 0.025:  # 2.5% max
            logger.warning(f"Signal risk ({risk_pct:.2%}) exceeds maximum (2.5%)")
            return False

        return True

    def _calculate_position_size(self, signal: Signal, current_price: float) -> float:
        """
        Calcular tamaño de posición basado en riesgo.

        Args:
            signal: Señal de trading
            current_price: Precio actual

        Returns:
            Tamaño de posición en lotes
        """
        # Obtener balance disponible
        balance = self.get_account_balance()

        # Calcular riesgo en USD (según max_risk_per_trade)
        risk_amount = balance * self.config.max_risk_per_trade

        # Calcular distancia al stop en pips
        stop_distance = abs(current_price - signal.stop_loss)
        stop_distance_pips = stop_distance * 10000  # Assuming 4-digit pricing

        if stop_distance_pips == 0:
            return 0.0

        # Calcular tamaño de posición
        # Formula: Risk_USD = Position_Size_Lots * Pips_Risk * Value_Per_Pip
        # Value_Per_Pip ≈ $10 for standard lot on EURUSD
        value_per_pip = 10.0
        position_size = risk_amount / (stop_distance_pips * value_per_pip)

        # Limitar entre 0.01 y 10 lotes
        position_size = max(0.01, min(position_size, 10.0))

        # Ajustar según sizing_level de la señal (1-5)
        if hasattr(signal, 'sizing_level'):
            sizing_multiplier = signal.sizing_level / 3.0  # 1→0.33x, 3→1x, 5→1.67x
            position_size *= sizing_multiplier

        # Redondear a 2 decimales
        position_size = round(position_size, 2)

        logger.debug(f"Position size calculated: {position_size:.2f} lots "
                    f"(risk=${risk_amount:.2f}, stop={stop_distance_pips:.1f} pips)")

        return position_size

    def get_statistics(self) -> Dict:
        """
        Obtener estadísticas de ejecución.

        Returns:
            Diccionario con estadísticas
        """
        stats = {
            'execution_mode': str(self.mode),
            'signals_received': self.signals_received,
            'orders_submitted': self.orders_submitted,
            'orders_rejected': self.orders_rejected,
            'execution_rate': self.orders_submitted / self.signals_received if self.signals_received > 0 else 0.0,
            'balance': self.get_account_balance(),
            'equity': self.get_account_equity(),
            'open_positions': len(self.get_positions())
        }

        # Agregar estadísticas del broker (si es PaperBroker)
        if isinstance(self.broker, PaperBrokerAdapter):
            stats.update(self.broker.get_statistics())

        # Agregar estado del KillSwitch (PLAN OMEGA FASE 3.3)
        if self.kill_switch:
            stats['killswitch'] = self.kill_switch.get_status()

        return stats

    def get_killswitch_status(self) -> Optional[Dict]:
        """
        Obtener estado del KillSwitch.

        Returns:
            Dict con estado o None si KillSwitch no activo
        """
        if self.kill_switch:
            return self.kill_switch.get_status()
        return None

    def is_trading_allowed(self) -> bool:
        """
        Verificar si trading está permitido.

        Verifica KillSwitch si está activo.

        Returns:
            True si se puede operar
        """
        if self.kill_switch:
            return self.kill_switch.is_trading_allowed()
        return True  # Si no hay KillSwitch, permitir trading

    def shutdown(self):
        """Apagar gestor de ejecución."""
        logger.info("ExecutionManager shutting down...")

        # Cerrar todas las posiciones (opcional - comentado por seguridad)
        # self.close_all_positions()

        # Desconectar broker
        if self.broker:
            self.broker.disconnect()

        logger.info("ExecutionManager shutdown complete")
