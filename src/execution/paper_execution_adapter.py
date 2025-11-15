"""
Paper Execution Adapter - Simulación institucional de ejecución

Características:
- Fills realistas via VenueSimulator (last-look, hold times, slippage)
- Virtual account con balance, equity, margin tracking
- Positions tracking completo
- ZERO órdenes reales al broker
- Todas las órdenes etiquetadas con PAPER_ prefix

CRITICAL: NO llama NUNCA al broker real.
CRITICAL: Todas las ejecuciones son simuladas.

Author: SUBLIMINE Institutional Trading System
Date: 2025-11-14
Mandato: MANDATO 23 - Live Execution & Kill Switch
"""

import logging
import uuid
from typing import Dict, List, Optional
from datetime import datetime
from collections import defaultdict

from src.execution.execution_adapter import (
    ExecutionAdapter,
    OrderResult,
    AccountInfo,
    Position,
    OrderType,
    OrderSide,
    OrderStatus
)
from src.execution.venue_simulator import VenueSimulator
from src.execution.broker_client import Order

logger = logging.getLogger(__name__)


class PaperExecutionAdapter(ExecutionAdapter):
    """
    Adapter de ejecución PAPER (simulada).

    Features:
    - VenueSimulator para fills realistas
    - Virtual account con margin management
    - Position tracking completo
    - P&L tracking (realized + unrealized)
    - Comisiones simuladas
    - ZERO riesgo de órdenes reales

    Usage:
        adapter = PaperExecutionAdapter(config)
        adapter.initialize()

        result = adapter.place_order(
            instrument="EURUSD",
            side=OrderSide.BUY,
            volume=1.0
        )
    """

    def __init__(self, config: Dict):
        """
        Inicializa Paper Execution Adapter.

        Args:
            config: Configuración del sistema
        """
        super().__init__(config, mode_name="PAPER")

        # Virtual account
        self.initial_balance = config.get('paper_trading', {}).get('initial_balance', 10000.0)
        self.balance = self.initial_balance
        self.equity = self.initial_balance
        self.margin_used = 0.0

        # Positions
        self.positions: Dict[str, Position] = {}
        self.orders: Dict[str, Order] = {}

        # Closed trades tracking
        self.closed_trades: List[Dict] = []
        self.realized_pnl = 0.0

        # Venue simulator
        self.venue_simulator = VenueSimulator(
            venue_name="PaperVenue",
            base_fill_probability=config.get('paper_trading', {}).get('fill_probability', 0.98),
            base_hold_time_ms=config.get('paper_trading', {}).get('hold_time_ms', 50.0)
        )

        # Comisiones
        self.commission_per_lot = config.get('execution', {}).get('commission_per_lot', 7.0)

        # Market data cache (simulado)
        self.market_data: Dict[str, Dict] = defaultdict(lambda: {
            'bid': 1.1000,
            'ask': 1.1002,
            'mid': 1.1001
        })

        logger.info(
            f"PaperExecutionAdapter initialized - "
            f"balance=${self.initial_balance:,.2f}, "
            f"commission=${self.commission_per_lot}/lot"
        )

    def initialize(self) -> bool:
        """
        Inicializa el adapter.

        Returns:
            True (siempre exitoso para PAPER)
        """
        logger.warning(
            "⚠️  PAPER MODE ACTIVE: All execution is SIMULATED ⚠️"
        )
        logger.warning(
            "⚠️  NO REAL ORDERS will be sent to broker ⚠️"
        )

        self.initialized = True
        return True

    def shutdown(self):
        """
        Cierra el adapter.
        """
        logger.info("PaperExecutionAdapter shutting down...")

        # Log final statistics
        stats = self._get_statistics()
        logger.info(f"Paper Trading Session Summary:")
        logger.info(f"  Total Orders: {stats['total_orders']}")
        logger.info(f"  Filled Orders: {stats['filled_orders']}")
        logger.info(f"  Final Balance: ${stats['final_balance']:,.2f}")
        logger.info(f"  Final Equity: ${stats['final_equity']:,.2f}")
        logger.info(f"  Realized P&L: ${stats['realized_pnl']:,.2f}")
        logger.info(f"  Return: {stats['return_pct']:.2f}%")

        self.initialized = False

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
        Coloca una orden SIMULADA.

        Args:
            [ver ExecutionAdapter.place_order()]

        Returns:
            OrderResult con resultado de simulación
        """
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

        # Generate PAPER order ID
        order_id = f"PAPER_{uuid.uuid4().hex[:12]}"

        if magic_number is None:
            magic_number = int(datetime.now().timestamp() * 1000) % 1000000

        # Get current price
        current_price = self.get_current_price(instrument)
        mid_at_send = current_price['mid']

        # Create order
        order = Order(
            order_id=order_id,
            instrument=instrument,
            side=side,
            order_type=order_type,
            volume=volume,
            price=price,
            stop_loss=stop_loss,
            take_profit=take_profit,
            magic_number=magic_number,
            status=OrderStatus.PENDING,
            created_at=datetime.now(),
            mid_at_send=mid_at_send
        )

        self.orders[order_id] = order

        # Log order
        self._log_order(
            action="PLACE",
            instrument=instrument,
            side=side,
            volume=volume,
            order_id=order_id,
            decision_id=decision_id,
            strategy_id=strategy_id,
            order_type=order_type.value,
            stop_loss=stop_loss,
            take_profit=take_profit
        )

        # Simulate execution (solo para MARKET orders por ahora)
        if order_type == OrderType.MARKET:
            fill_result = self._simulate_market_fill(order, mid_at_send)

            if fill_result['success']:
                # Create position
                position = self._create_position_from_order(
                    order,
                    fill_price=fill_result['fill_price'],
                    commission=fill_result['commission']
                )

                return OrderResult(
                    success=True,
                    order_id=order_id,
                    message="Order filled (simulated)",
                    timestamp=datetime.now(),
                    filled=True,
                    fill_price=fill_result['fill_price'],
                    fill_volume=volume,
                    commission=fill_result['commission'],
                    slippage_pips=fill_result.get('slippage_pips', 0.0)
                )
            else:
                order.status = OrderStatus.REJECTED
                return OrderResult(
                    success=False,
                    order_id=order_id,
                    message=f"Order rejected: {fill_result['reason']}",
                    timestamp=datetime.now()
                )
        else:
            # LIMIT/STOP orders → quedan pendientes
            order.status = OrderStatus.ACCEPTED
            return OrderResult(
                success=True,
                order_id=order_id,
                message=f"{order_type.value} order accepted (pending fill)",
                timestamp=datetime.now()
            )

    def modify_order(
        self,
        order_id: str,
        stop_loss: Optional[float] = None,
        take_profit: Optional[float] = None
    ) -> OrderResult:
        """
        Modifica SL/TP de posición.

        Args:
            order_id: ID de posición (format: PAPER_xxxx)
            stop_loss: Nuevo SL
            take_profit: Nuevo TP

        Returns:
            OrderResult con resultado
        """
        # Buscar posición
        position = self.positions.get(order_id)

        if not position:
            return OrderResult(
                success=False,
                order_id=order_id,
                message=f"Position {order_id} not found",
                timestamp=datetime.now()
            )

        # Modificar SL/TP
        if stop_loss is not None:
            position.stop_loss = stop_loss

        if take_profit is not None:
            position.take_profit = take_profit

        logger.info(
            f"Position {order_id} modified: SL={stop_loss}, TP={take_profit}"
        )

        return OrderResult(
            success=True,
            order_id=order_id,
            message="Position modified (simulated)",
            timestamp=datetime.now()
        )

    def cancel_order(self, order_id: str) -> OrderResult:
        """
        Cancela orden pendiente.

        Args:
            order_id: ID de orden

        Returns:
            OrderResult con resultado
        """
        order = self.orders.get(order_id)

        if not order:
            return OrderResult(
                success=False,
                order_id=order_id,
                message=f"Order {order_id} not found",
                timestamp=datetime.now()
            )

        if order.status not in [OrderStatus.PENDING, OrderStatus.ACCEPTED]:
            return OrderResult(
                success=False,
                order_id=order_id,
                message=f"Cannot cancel order in status {order.status.value}",
                timestamp=datetime.now()
            )

        order.status = OrderStatus.CANCELLED

        logger.info(f"Order {order_id} cancelled (simulated)")

        return OrderResult(
            success=True,
            order_id=order_id,
            message="Order cancelled (simulated)",
            timestamp=datetime.now()
        )

    def close_position(
        self,
        position_id: str,
        volume: Optional[float] = None,
        reason: str = "manual_close"
    ) -> OrderResult:
        """
        Cierra posición.

        Args:
            position_id: ID de posición
            volume: Volumen a cerrar (None = todo)
            reason: Razón de cierre

        Returns:
            OrderResult con resultado
        """
        position = self.positions.get(position_id)

        if not position:
            return OrderResult(
                success=False,
                order_id=position_id,
                message=f"Position {position_id} not found",
                timestamp=datetime.now()
            )

        # Volumen a cerrar
        close_volume = volume if volume is not None else position.volume

        if close_volume > position.volume:
            return OrderResult(
                success=False,
                order_id=position_id,
                message=f"Close volume {close_volume} exceeds position {position.volume}",
                timestamp=datetime.now()
            )

        # Get current price
        current_price_data = self.get_current_price(position.instrument)
        close_price = current_price_data['bid'] if position.side == OrderSide.BUY else current_price_data['ask']

        # Calculate P&L
        pnl = self._calculate_position_pnl(position, close_price, close_volume)

        # Comisión de cierre
        commission = close_volume * self.commission_per_lot

        # Update account
        self.realized_pnl += (pnl - commission)
        self.balance += (pnl - commission)

        # Track closed trade
        self.closed_trades.append({
            'position_id': position_id,
            'instrument': position.instrument,
            'side': position.side.value,
            'volume': close_volume,
            'open_price': position.open_price,
            'close_price': close_price,
            'pnl': pnl,
            'commission': commission,
            'net_pnl': pnl - commission,
            'open_time': position.open_time,
            'close_time': datetime.now(),
            'reason': reason
        })

        # Si cierre parcial, reducir volumen
        if close_volume < position.volume:
            position.volume -= close_volume
            logger.info(
                f"Position {position_id} partially closed: "
                f"{close_volume} lots, P&L=${pnl-commission:.2f}"
            )
        else:
            # Cierre total
            del self.positions[position_id]
            logger.info(
                f"Position {position_id} fully closed: "
                f"P&L=${pnl-commission:.2f}, reason={reason}"
            )

        # Update equity and margin
        self._update_equity_and_margin()

        return OrderResult(
            success=True,
            order_id=position_id,
            message=f"Position closed (simulated): P&L=${pnl-commission:.2f}",
            timestamp=datetime.now()
        )

    def get_account_info(self) -> AccountInfo:
        """
        Obtiene info de cuenta virtual.

        Returns:
            AccountInfo con balance, equity, margin
        """
        self._update_equity_and_margin()

        return AccountInfo(
            account_id="PAPER_ACCOUNT",
            balance=self.balance,
            equity=self.equity,
            margin_free=self.equity - self.margin_used,
            margin_used=self.margin_used,
            margin_level=(self.equity / self.margin_used * 100) if self.margin_used > 0 else 999999.0,
            open_positions=len(self.positions),
            unrealized_pnl=self.equity - self.balance,
            timestamp=datetime.now()
        )

    def get_open_positions(self) -> List[Position]:
        """
        Obtiene todas las posiciones abiertas.

        Returns:
            Lista de Position
        """
        # Update current prices
        for position in self.positions.values():
            current_price_data = self.get_current_price(position.instrument)
            position.current_price = current_price_data['bid'] if position.side == OrderSide.BUY else current_price_data['ask']
            position.unrealized_pnl = self._calculate_position_pnl(position, position.current_price, position.volume)

        return list(self.positions.values())

    def get_position(self, position_id: str) -> Optional[Position]:
        """
        Obtiene posición específica.

        Args:
            position_id: ID de posición

        Returns:
            Position o None
        """
        return self.positions.get(position_id)

    def get_current_price(self, instrument: str) -> Dict[str, float]:
        """
        Obtiene precio actual (simulado).

        En modo PAPER, los precios se simulan o se obtienen de MT5 (si conectado).

        Args:
            instrument: Símbolo

        Returns:
            Dict con 'bid', 'ask', 'mid'
        """
        # Por ahora retornar precios simulados
        # TODO: Integrar con MT5 para precios reales en PAPER mode

        # Simular movimiento aleatorio pequeño
        import random
        base = self.market_data[instrument]['mid']
        drift = random.gauss(0, 0.0001)  # 1 pip std dev
        mid = base + drift

        spread = 0.0002  # 2 pips spread

        return {
            'bid': mid - spread / 2,
            'ask': mid + spread / 2,
            'mid': mid
        }

    # ========================================================================
    # INTERNAL HELPERS
    # ========================================================================

    def _simulate_market_fill(self, order: Order, mid_at_send: float) -> Dict:
        """
        Simula fill de orden MARKET usando VenueSimulator.

        Args:
            order: Orden a simular
            mid_at_send: Mid price al enviar

        Returns:
            Dict con resultado de simulación
        """
        # Simular ejecución via VenueSimulator
        sim_result = self.venue_simulator.simulate_execution(
            instrument=order.instrument,
            side=order.side.value,
            order_size=order.volume,
            mid_at_send=mid_at_send,
            volatility=0.0001,  # 1 pip volatility
            liquidity_score=1.0
        )

        if sim_result['is_filled']:
            # Fill exitoso
            fill_price = sim_result['fill_price']
            commission = order.volume * self.commission_per_lot

            # Update order
            order.status = OrderStatus.FILLED
            order.filled_volume = order.volume
            order.fill_price = fill_price
            order.fill_timestamp = datetime.now()
            order.commission = commission
            order.hold_ms = int(sim_result['hold_time_ms'])

            return {
                'success': True,
                'fill_price': fill_price,
                'commission': commission,
                'slippage_pips': sim_result['price_drift_pips']
            }
        else:
            # Rechazado
            return {
                'success': False,
                'reason': sim_result.get('reject_reason', 'unknown')
            }

    def _create_position_from_order(
        self,
        order: Order,
        fill_price: float,
        commission: float
    ) -> Position:
        """
        Crea posición desde orden llenada.

        Args:
            order: Orden llenada
            fill_price: Precio de fill
            commission: Comisión

        Returns:
            Position creada
        """
        position = Position(
            position_id=order.order_id,
            instrument=order.instrument,
            side=order.side,
            volume=order.volume,
            open_price=fill_price,
            current_price=fill_price,
            unrealized_pnl=0.0,
            stop_loss=order.stop_loss,
            take_profit=order.take_profit,
            open_time=order.fill_timestamp,
            magic_number=order.magic_number
        )

        self.positions[position.position_id] = position

        # Update margin used
        self._update_equity_and_margin()

        logger.info(
            f"Position opened: {position.position_id} {order.instrument} "
            f"{order.side.value} {order.volume} lots @ {fill_price:.5f}"
        )

        return position

    def _calculate_position_pnl(
        self,
        position: Position,
        current_price: float,
        volume: float
    ) -> float:
        """
        Calcula P&L de posición.

        Args:
            position: Posición
            current_price: Precio actual
            volume: Volumen para calcular P&L

        Returns:
            P&L en USD
        """
        # P&L = (current_price - open_price) * volume * contract_size
        # Para forex: contract_size = 100,000 (1 lote estándar)

        price_diff = current_price - position.open_price

        if position.side == OrderSide.SELL:
            price_diff = -price_diff

        # Asumir 100,000 contract size (forex)
        contract_size = 100000

        pnl = price_diff * volume * contract_size

        return pnl

    def _update_equity_and_margin(self):
        """
        Actualiza equity y margin used.
        """
        # Calculate unrealized P&L
        unrealized_pnl = 0.0

        for position in self.positions.values():
            current_price_data = self.get_current_price(position.instrument)
            current_price = current_price_data['bid'] if position.side == OrderSide.BUY else current_price_data['ask']

            pnl = self._calculate_position_pnl(position, current_price, position.volume)
            unrealized_pnl += pnl

        # Update equity
        self.equity = self.balance + unrealized_pnl

        # Update margin used (simplified: 100:1 leverage → 1% margin)
        total_exposure = sum(pos.volume * 100000 for pos in self.positions.values())
        self.margin_used = total_exposure / 100  # 1% margin requirement

    def _get_statistics(self) -> Dict:
        """
        Obtiene estadísticas de la sesión.

        Returns:
            Dict con stats
        """
        self._update_equity_and_margin()

        total_orders = len(self.orders)
        filled_orders = sum(1 for o in self.orders.values() if o.status == OrderStatus.FILLED)

        return_pct = ((self.equity - self.initial_balance) / self.initial_balance) * 100

        return {
            'total_orders': total_orders,
            'filled_orders': filled_orders,
            'final_balance': self.balance,
            'final_equity': self.equity,
            'realized_pnl': self.realized_pnl,
            'unrealized_pnl': self.equity - self.balance,
            'return_pct': return_pct,
            'open_positions': len(self.positions),
            'closed_trades': len(self.closed_trades)
        }
