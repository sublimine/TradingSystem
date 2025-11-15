"""
Live Execution Adapter - Ejecución REAL institucional

CRITICAL: Este es el ÚNICO lugar donde se envían órdenes REALES al broker.
CRITICAL: Requiere KillSwitch OPERACIONAL antes de CADA orden.
CRITICAL: Logging exhaustivo de TODAS las acciones.

Características:
- Integración con MT5Connector para conexión broker
- Integración con BrokerClient para envío de órdenes
- KillSwitch check ANTES de cada orden
- Mapeo de IDs internos a tickets broker
- Manejo robusto de errores broker
- Trazabilidad completa (decision_id, strategy_id, metadata)
- Auditoría LIVE_EXECUTION en reporting

MONEY AT RISK - Handle with extreme care.

Author: SUBLIMINE Institutional Trading System
Date: 2025-11-14
Mandato: MANDATO 23 - Live Execution & Kill Switch
"""

import logging
import MetaTrader5 as mt5
from typing import Dict, List, Optional
from datetime import datetime
import time

from src.execution.execution_adapter import (
    ExecutionAdapter,
    OrderResult,
    AccountInfo,
    Position,
    OrderType,
    OrderSide,
    OrderStatus
)
from src.execution.kill_switch import KillSwitch, KillSwitchState
from src.mt5_connector import MT5Connector

logger = logging.getLogger(__name__)


class LiveExecutionAdapter(ExecutionAdapter):
    """
    Adapter de ejecución LIVE (REAL BROKER).

    Features:
    - Conexión real a MT5 via MT5Connector
    - Kill Switch validation ANTES de CADA orden
    - Manejo de errores broker con retry logic
    - Mapeo de position_id interno a ticket broker
    - Logging CRÍTICO de todas las operaciones
    - Integración con reporting para auditoría

    Usage:
        kill_switch = KillSwitch(config)
        adapter = LiveExecutionAdapter(config, kill_switch)

        # Kill switch DEBE estar OPERATIONAL
        if adapter.initialize():
            result = adapter.place_order(...)
    """

    def __init__(self, config: Dict, kill_switch: KillSwitch):
        """
        Inicializa Live Execution Adapter.

        Args:
            config: Configuración del sistema
            kill_switch: KillSwitch instance (REQUIRED)

        Raises:
            ValueError: Si kill_switch no está provisto
        """
        super().__init__(config, mode_name="LIVE")

        if kill_switch is None:
            raise ValueError("KillSwitch is REQUIRED for LiveExecutionAdapter")

        self.kill_switch = kill_switch
        self.mt5_connector = MT5Connector(
            max_retries=config.get('mt5', {}).get('max_retries', 5),
            base_delay=config.get('mt5', {}).get('base_delay', 2.0)
        )

        # ID mapping: internal position_id → MT5 ticket
        self.position_id_to_ticket: Dict[str, int] = {}
        self.ticket_to_position_id: Dict[int, str] = {}

        # Retry config
        self.max_order_retries = config.get('live_trading', {}).get('max_order_retries', 3)
        self.retry_delay_ms = config.get('live_trading', {}).get('retry_delay_ms', 100)

        # Comisiones
        self.commission_per_lot = config.get('execution', {}).get('commission_per_lot', 7.0)

        logger.critical(
            "⚠️⚠️⚠️  LiveExecutionAdapter initialized - REAL MONEY AT RISK  ⚠️⚠️⚠️"
        )

    def initialize(self) -> bool:
        """
        Inicializa el adapter.

        Verifica:
        1. KillSwitch está OPERATIONAL
        2. MT5 conectado exitosamente
        3. Cuenta válida

        Returns:
            True si inicialización exitosa, False si falla

        Raises:
            Exception: Si falla de forma crítica
        """
        logger.critical("=" * 80)
        logger.critical("INITIALIZING LIVE EXECUTION ADAPTER")
        logger.critical("=" * 80)

        # Check 1: Kill Switch
        if not self.kill_switch.can_send_orders():
            logger.critical(
                f"INITIALIZATION BLOCKED: KillSwitch state = {self.kill_switch.get_state().value}"
            )
            status = self.kill_switch.get_status()
            logger.critical(f"Failed layers: {status.failed_layers}")
            logger.critical(f"Reason: {status.reason}")
            return False

        logger.info("✓ Kill Switch: OPERATIONAL")

        # Check 2: MT5 Connection
        if not self.mt5_connector.connect():
            logger.critical("INITIALIZATION FAILED: Cannot connect to MT5")
            return False

        logger.info("✓ MT5: Connected")

        # Check 3: Account Info
        account_info = mt5.account_info()
        if account_info is None:
            logger.critical("INITIALIZATION FAILED: Cannot get account info")
            return False

        logger.critical(f"MT5 Account: {account_info.login}")
        logger.critical(f"Server: {account_info.server}")
        logger.critical(f"Balance: ${account_info.balance:,.2f}")
        logger.critical(f"Equity: ${account_info.equity:,.2f}")
        logger.critical(f"Margin Level: {account_info.margin_level:.2f}%")

        # Ping broker for health check
        ping_start = time.time()
        _ = mt5.symbol_info_tick("EURUSD")
        ping_latency_ms = (time.time() - ping_start) * 1000

        self.kill_switch.record_broker_ping(
            latency_ms=ping_latency_ms,
            is_connected=True
        )

        logger.info(f"✓ Broker Ping: {ping_latency_ms:.1f}ms")

        logger.critical("=" * 80)
        logger.critical("LIVE EXECUTION ADAPTER READY")
        logger.critical("⚠️  ALL ORDERS WILL BE REAL  ⚠️")
        logger.critical("=" * 80)

        self.initialized = True
        return True

    def shutdown(self):
        """
        Cierra el adapter.
        """
        logger.critical("=" * 80)
        logger.critical("SHUTTING DOWN LIVE EXECUTION ADAPTER")
        logger.critical("=" * 80)

        # Get final account info
        account_info = mt5.account_info()
        if account_info:
            logger.critical(f"Final Balance: ${account_info.balance:,.2f}")
            logger.critical(f"Final Equity: ${account_info.equity:,.2f}")

        # Disconnect MT5
        self.mt5_connector.disconnect()
        logger.info("✓ MT5 disconnected")

        self.initialized = False

        logger.critical("=" * 80)
        logger.critical("LIVE EXECUTION ADAPTER SHUTDOWN COMPLETE")
        logger.critical("=" * 80)

    def place_order(
        self,
        instrument: str,
        side: OrderSide,
        volume: float,
        order_type: OrderType = OrderType.MARKET,
        price: Optional[float] = None,
        stop_loss: Optional[float] = None,
        take_profit: Optional[float] = None,
        magic_number: Optional[int] = None,
        decision_id: Optional[str] = None,
        strategy_id: Optional[str] = None,
        metadata: Optional[Dict] = None
    ) -> OrderResult:
        """
        Coloca una orden REAL al broker.

        CRITICAL: Verifica KillSwitch ANTES de enviar.

        Args:
            [ver ExecutionAdapter.place_order()]

        Returns:
            OrderResult con resultado de ejecución REAL
        """
        # CRITICAL: Kill Switch Check
        if not self.kill_switch.can_send_orders():
            logger.critical(
                f"ORDER BLOCKED BY KILL SWITCH: {self.kill_switch.get_state().value}"
            )
            return OrderResult(
                success=False,
                order_id=None,
                message=f"Kill Switch blocked order: {self.kill_switch.get_state().value}",
                timestamp=datetime.now()
            )

        # Validate params
        is_valid, error_msg = self._validate_order_params(
            instrument, side, volume, order_type, price, stop_loss, take_profit
        )

        if not is_valid:
            logger.error(f"Order validation failed: {error_msg}")
            return OrderResult(
                success=False,
                order_id=None,
                message=f"Validation failed: {error_msg}",
                timestamp=datetime.now()
            )

        # Ensure connected
        if not self.mt5_connector.ensure_connected():
            logger.critical("Cannot send order: MT5 not connected")
            return OrderResult(
                success=False,
                order_id=None,
                message="MT5 connection lost",
                timestamp=datetime.now()
            )

        # Log CRITICAL - LIVE ORDER
        logger.critical(
            f"🚨 LIVE ORDER: {instrument} {side.value} {volume} lots "
            f"(type={order_type.value}, SL={stop_loss}, TP={take_profit})"
        )

        self._log_order(
            action="PLACE_LIVE",
            instrument=instrument,
            side=side,
            volume=volume,
            decision_id=decision_id,
            strategy_id=strategy_id,
            order_type=order_type.value,
            stop_loss=stop_loss,
            take_profit=take_profit,
            metadata=metadata
        )

        # Send order to MT5 with retry
        for attempt in range(self.max_order_retries):
            try:
                # Build MT5 request
                request = self._build_mt5_request(
                    instrument=instrument,
                    side=side,
                    volume=volume,
                    order_type=order_type,
                    price=price,
                    stop_loss=stop_loss,
                    take_profit=take_profit,
                    magic_number=magic_number
                )

                # Send order
                logger.info(f"Sending order to MT5 (attempt {attempt+1}/{self.max_order_retries})...")
                result = mt5.order_send(request)

                if result is None:
                    logger.error("MT5 order_send returned None")
                    if attempt < self.max_order_retries - 1:
                        time.sleep(self.retry_delay_ms / 1000.0)
                        continue
                    else:
                        return OrderResult(
                            success=False,
                            order_id=None,
                            message="MT5 order_send failed (None result)",
                            timestamp=datetime.now()
                        )

                # Check result
                if result.retcode != mt5.TRADE_RETCODE_DONE:
                    logger.error(
                        f"Order failed: retcode={result.retcode}, "
                        f"comment={result.comment}"
                    )

                    # Retry on transient errors
                    if result.retcode in [mt5.TRADE_RETCODE_REQUOTE, mt5.TRADE_RETCODE_TIMEOUT]:
                        if attempt < self.max_order_retries - 1:
                            logger.warning(f"Retrying due to {result.retcode}...")
                            time.sleep(self.retry_delay_ms / 1000.0)
                            continue

                    return OrderResult(
                        success=False,
                        order_id=None,
                        message=f"MT5 error: {result.retcode} - {result.comment}",
                        timestamp=datetime.now()
                    )

                # SUCCESS
                ticket = result.order
                position_id = f"LIVE_{ticket}"

                # Store mapping
                self.position_id_to_ticket[position_id] = ticket
                self.ticket_to_position_id[ticket] = position_id

                logger.critical(
                    f"✅ LIVE ORDER FILLED: ticket={ticket}, "
                    f"price={result.price:.5f}, volume={result.volume}"
                )

                return OrderResult(
                    success=True,
                    order_id=position_id,
                    message=f"Order filled: ticket={ticket}",
                    timestamp=datetime.now(),
                    filled=True,
                    fill_price=result.price,
                    fill_volume=result.volume,
                    commission=result.volume * self.commission_per_lot
                )

            except Exception as e:
                logger.critical(f"Exception sending order: {e}")

                if attempt < self.max_order_retries - 1:
                    time.sleep(self.retry_delay_ms / 1000.0)
                    continue
                else:
                    return OrderResult(
                        success=False,
                        order_id=None,
                        message=f"Exception: {str(e)}",
                        timestamp=datetime.now()
                    )

        # Should not reach here
        return OrderResult(
            success=False,
            order_id=None,
            message="Max retries exceeded",
            timestamp=datetime.now()
        )

    def modify_order(
        self,
        order_id: str,
        stop_loss: Optional[float] = None,
        take_profit: Optional[float] = None
    ) -> OrderResult:
        """
        Modifica SL/TP de posición LIVE.

        Args:
            order_id: ID de posición (format: LIVE_ticket)
            stop_loss: Nuevo SL
            take_profit: Nuevo TP

        Returns:
            OrderResult con resultado
        """
        # Get MT5 ticket
        ticket = self.position_id_to_ticket.get(order_id)

        if ticket is None:
            return OrderResult(
                success=False,
                order_id=order_id,
                message=f"Position {order_id} not found in mapping",
                timestamp=datetime.now()
            )

        # Get position from MT5
        positions = mt5.positions_get(ticket=ticket)

        if positions is None or len(positions) == 0:
            return OrderResult(
                success=False,
                order_id=order_id,
                message=f"Position ticket={ticket} not found in MT5",
                timestamp=datetime.now()
            )

        position = positions[0]

        # Build modify request
        request = {
            "action": mt5.TRADE_ACTION_SLTP,
            "position": ticket,
            "symbol": position.symbol,
            "sl": stop_loss if stop_loss is not None else position.sl,
            "tp": take_profit if take_profit is not None else position.tp,
        }

        logger.info(f"Modifying position {ticket}: SL={stop_loss}, TP={take_profit}")

        # Send modify
        result = mt5.order_send(request)

        if result is None or result.retcode != mt5.TRADE_RETCODE_DONE:
            error_msg = f"Modify failed: {result.comment if result else 'None result'}"
            logger.error(error_msg)
            return OrderResult(
                success=False,
                order_id=order_id,
                message=error_msg,
                timestamp=datetime.now()
            )

        logger.info(f"Position {ticket} modified successfully")

        return OrderResult(
            success=True,
            order_id=order_id,
            message=f"Position modified: ticket={ticket}",
            timestamp=datetime.now()
        )

    def cancel_order(self, order_id: str) -> OrderResult:
        """
        Cancela orden pendiente LIVE.

        Args:
            order_id: ID de orden

        Returns:
            OrderResult con resultado
        """
        # Get MT5 ticket
        ticket = self.position_id_to_ticket.get(order_id)

        if ticket is None:
            return OrderResult(
                success=False,
                order_id=order_id,
                message=f"Order {order_id} not found in mapping",
                timestamp=datetime.now()
            )

        # Build cancel request
        request = {
            "action": mt5.TRADE_ACTION_REMOVE,
            "order": ticket,
        }

        logger.info(f"Cancelling order {ticket}")

        # Send cancel
        result = mt5.order_send(request)

        if result is None or result.retcode != mt5.TRADE_RETCODE_DONE:
            error_msg = f"Cancel failed: {result.comment if result else 'None result'}"
            logger.error(error_msg)
            return OrderResult(
                success=False,
                order_id=order_id,
                message=error_msg,
                timestamp=datetime.now()
            )

        logger.info(f"Order {ticket} cancelled successfully")

        return OrderResult(
            success=True,
            order_id=order_id,
            message=f"Order cancelled: ticket={ticket}",
            timestamp=datetime.now()
        )

    def close_position(
        self,
        position_id: str,
        volume: Optional[float] = None,
        reason: str = "manual_close"
    ) -> OrderResult:
        """
        Cierra posición LIVE.

        Args:
            position_id: ID de posición (format: LIVE_ticket)
            volume: Volumen a cerrar (None = todo)
            reason: Razón de cierre

        Returns:
            OrderResult con resultado
        """
        # Get MT5 ticket
        ticket = self.position_id_to_ticket.get(position_id)

        if ticket is None:
            return OrderResult(
                success=False,
                order_id=position_id,
                message=f"Position {position_id} not found in mapping",
                timestamp=datetime.now()
            )

        # Get position from MT5
        positions = mt5.positions_get(ticket=ticket)

        if positions is None or len(positions) == 0:
            return OrderResult(
                success=False,
                order_id=position_id,
                message=f"Position ticket={ticket} not found in MT5",
                timestamp=datetime.now()
            )

        position = positions[0]

        # Determine close volume
        close_volume = volume if volume is not None else position.volume

        # Determine close side (opposite of open)
        close_type = mt5.ORDER_TYPE_SELL if position.type == mt5.ORDER_TYPE_BUY else mt5.ORDER_TYPE_BUY

        # Build close request
        request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "position": ticket,
            "symbol": position.symbol,
            "volume": close_volume,
            "type": close_type,
            "deviation": 10,
            "comment": f"Close: {reason}",
        }

        logger.critical(f"🚨 CLOSING LIVE POSITION: ticket={ticket}, volume={close_volume}, reason={reason}")

        # Send close
        result = mt5.order_send(request)

        if result is None or result.retcode != mt5.TRADE_RETCODE_DONE:
            error_msg = f"Close failed: {result.comment if result else 'None result'}"
            logger.critical(error_msg)
            return OrderResult(
                success=False,
                order_id=position_id,
                message=error_msg,
                timestamp=datetime.now()
            )

        logger.critical(f"✅ LIVE POSITION CLOSED: ticket={ticket}, price={result.price:.5f}")

        # Remove from mapping if fully closed
        if close_volume >= position.volume:
            del self.position_id_to_ticket[position_id]
            del self.ticket_to_position_id[ticket]

        return OrderResult(
            success=True,
            order_id=position_id,
            message=f"Position closed: ticket={ticket}",
            timestamp=datetime.now()
        )

    def get_account_info(self) -> AccountInfo:
        """
        Obtiene info de cuenta REAL desde MT5.

        Returns:
            AccountInfo con datos reales
        """
        account_info = mt5.account_info()

        if account_info is None:
            logger.error("Cannot get account info from MT5")
            return AccountInfo(
                account_id="UNKNOWN",
                balance=0.0,
                equity=0.0,
                margin_free=0.0,
                margin_used=0.0,
                margin_level=0.0,
                open_positions=0,
                unrealized_pnl=0.0,
                timestamp=datetime.now()
            )

        return AccountInfo(
            account_id=str(account_info.login),
            balance=float(account_info.balance),
            equity=float(account_info.equity),
            margin_free=float(account_info.margin_free),
            margin_used=float(account_info.margin),
            margin_level=float(account_info.margin_level),
            open_positions=len(mt5.positions_get() or []),
            unrealized_pnl=float(account_info.equity - account_info.balance),
            timestamp=datetime.now()
        )

    def get_open_positions(self) -> List[Position]:
        """
        Obtiene todas las posiciones abiertas LIVE desde MT5.

        Returns:
            Lista de Position
        """
        mt5_positions = mt5.positions_get()

        if mt5_positions is None:
            logger.warning("Cannot get positions from MT5")
            return []

        positions = []

        for mt5_pos in mt5_positions:
            position_id = self.ticket_to_position_id.get(mt5_pos.ticket, f"LIVE_{mt5_pos.ticket}")

            # Ensure mapping
            if position_id not in self.position_id_to_ticket:
                self.position_id_to_ticket[position_id] = mt5_pos.ticket
                self.ticket_to_position_id[mt5_pos.ticket] = position_id

            # Get current price
            tick = mt5.symbol_info_tick(mt5_pos.symbol)
            current_price = tick.bid if mt5_pos.type == mt5.ORDER_TYPE_BUY else tick.ask

            position = Position(
                position_id=position_id,
                instrument=mt5_pos.symbol,
                side=OrderSide.BUY if mt5_pos.type == mt5.ORDER_TYPE_BUY else OrderSide.SELL,
                volume=float(mt5_pos.volume),
                open_price=float(mt5_pos.price_open),
                current_price=float(current_price),
                unrealized_pnl=float(mt5_pos.profit),
                stop_loss=float(mt5_pos.sl) if mt5_pos.sl > 0 else None,
                take_profit=float(mt5_pos.tp) if mt5_pos.tp > 0 else None,
                open_time=datetime.fromtimestamp(mt5_pos.time),
                magic_number=mt5_pos.magic
            )

            positions.append(position)

        return positions

    def get_position(self, position_id: str) -> Optional[Position]:
        """
        Obtiene posición específica LIVE desde MT5.

        Args:
            position_id: ID de posición

        Returns:
            Position o None
        """
        ticket = self.position_id_to_ticket.get(position_id)

        if ticket is None:
            return None

        mt5_positions = mt5.positions_get(ticket=ticket)

        if mt5_positions is None or len(mt5_positions) == 0:
            return None

        mt5_pos = mt5_positions[0]

        # Get current price
        tick = mt5.symbol_info_tick(mt5_pos.symbol)
        current_price = tick.bid if mt5_pos.type == mt5.ORDER_TYPE_BUY else tick.ask

        return Position(
            position_id=position_id,
            instrument=mt5_pos.symbol,
            side=OrderSide.BUY if mt5_pos.type == mt5.ORDER_TYPE_BUY else OrderSide.SELL,
            volume=float(mt5_pos.volume),
            open_price=float(mt5_pos.price_open),
            current_price=float(current_price),
            unrealized_pnl=float(mt5_pos.profit),
            stop_loss=float(mt5_pos.sl) if mt5_pos.sl > 0 else None,
            take_profit=float(mt5_pos.tp) if mt5_pos.tp > 0 else None,
            open_time=datetime.fromtimestamp(mt5_pos.time),
            magic_number=mt5_pos.magic
        )

    def get_current_price(self, instrument: str) -> Dict[str, float]:
        """
        Obtiene precio actual REAL desde MT5.

        Args:
            instrument: Símbolo

        Returns:
            Dict con 'bid', 'ask', 'mid'
        """
        tick = mt5.symbol_info_tick(instrument)

        if tick is None:
            logger.error(f"Cannot get tick for {instrument}")
            return {'bid': 0.0, 'ask': 0.0, 'mid': 0.0}

        # Validate tick
        self.kill_switch.validate_tick(
            symbol=instrument,
            bid=tick.bid,
            ask=tick.ask,
            timestamp=datetime.fromtimestamp(tick.time)
        )

        return {
            'bid': float(tick.bid),
            'ask': float(tick.ask),
            'mid': float((tick.bid + tick.ask) / 2)
        }

    # ========================================================================
    # INTERNAL HELPERS
    # ========================================================================

    def _build_mt5_request(
        self,
        instrument: str,
        side: OrderSide,
        volume: float,
        order_type: OrderType,
        price: Optional[float],
        stop_loss: Optional[float],
        take_profit: Optional[float],
        magic_number: Optional[int]
    ) -> dict:
        """
        Construye request para MT5.

        Args:
            [parámetros de orden]

        Returns:
            Dict con request MT5
        """
        # Map OrderType to MT5 type
        type_map = {
            OrderType.MARKET: mt5.ORDER_TYPE_BUY if side == OrderSide.BUY else mt5.ORDER_TYPE_SELL,
            OrderType.LIMIT: mt5.ORDER_TYPE_BUY_LIMIT if side == OrderSide.BUY else mt5.ORDER_TYPE_SELL_LIMIT,
            OrderType.STOP: mt5.ORDER_TYPE_BUY_STOP if side == OrderSide.BUY else mt5.ORDER_TYPE_SELL_STOP,
        }

        request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": instrument,
            "volume": volume,
            "type": type_map.get(order_type, mt5.ORDER_TYPE_BUY),
            "deviation": 10,
            "magic": magic_number if magic_number else 0,
            "comment": "LIVE_ORDER",
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": mt5.ORDER_FILLING_IOC,
        }

        # Price for LIMIT/STOP
        if order_type in [OrderType.LIMIT, OrderType.STOP] and price is not None:
            request["price"] = price

        # SL/TP
        if stop_loss is not None:
            request["sl"] = stop_loss

        if take_profit is not None:
            request["tp"] = take_profit

        return request
