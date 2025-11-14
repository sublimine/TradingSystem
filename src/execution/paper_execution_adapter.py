"""
Paper Execution Adapter - MANDATO 21

Simulated execution for paper trading mode.

Features:
- NO real broker orders (100% simulated)
- Uses VenueSimulator for realistic fills
- Maintains virtual positions and account
- Full TCA and slippage modeling
- Same risk management as LIVE

CRITICAL: This adapter NEVER sends orders to real broker.

Author: SUBLIMINE Institutional Trading System
Date: 2025-11-14
Mandato: MANDATO 21 - Paper Trading Institucional
"""

import logging
from typing import Dict, List, Optional
from datetime import datetime
import uuid
import time
import numpy as np

from .execution_adapter import (
    ExecutionAdapter,
    ExecutionOrder,
    Position,
    AccountInfo,
    OrderSide,
    OrderType,
    OrderStatus
)
from .venue_simulator import VenueSimulator

logger = logging.getLogger(__name__)


class PaperExecutionAdapter(ExecutionAdapter):
    """
    Paper trading execution adapter.

    Simulates execution using VenueSimulator.
    NO REAL BROKER ORDERS.

    Features:
    - Simulated fills with realistic slippage
    - Virtual position tracking
    - Virtual account (balance, equity, margin)
    - Simulated commission and fees
    """

    def __init__(
        self,
        config: dict,
        initial_balance: float = 10000.0,
        use_venue_simulator: bool = True
    ):
        """
        Initialize paper execution adapter.

        Args:
            config: System configuration
            initial_balance: Starting virtual balance
            use_venue_simulator: Use VenueSimulator for fills (vs instant fills)
        """
        super().__init__(adapter_name="PaperExecutionAdapter", config=config)

        self.initial_balance = initial_balance
        self.balance = initial_balance
        self.equity = initial_balance
        self.use_venue_simulator = use_venue_simulator

        # Storage
        self._orders: Dict[str, ExecutionOrder] = {}
        self._positions: Dict[str, Position] = {}

        # Simulated market prices (updated externally or via simulator)
        self._market_prices: Dict[str, Dict[str, float]] = {}

        # Venue simulator (if enabled)
        self.venue_simulator = None
        if use_venue_simulator:
            self.venue_simulator = VenueSimulator(
                venue_name="PaperVenue",
                base_fill_probability=0.98,  # Higher than live (paper is optimistic)
                base_hold_time_ms=30.0,  # Faster than live
                last_look_threshold_pips=0.3,
                size_penalty_factor=0.05
            )

        logger.info(
            f"PaperExecutionAdapter initialized: "
            f"balance=${initial_balance:,.2f}, "
            f"venue_sim={use_venue_simulator}"
        )

        logger.warning(
            "⚠️  PAPER MODE: Simulated execution only - NO REAL BROKER ORDERS"
        )

    def connect(self) -> bool:
        """
        Connect to paper execution backend (no-op for paper mode).

        Returns:
            Always True
        """
        self._connected = True
        logger.info("✅ Paper execution adapter connected (simulated)")
        return True

    def disconnect(self):
        """Disconnect from paper backend (no-op)."""
        self._connected = False
        logger.info("Paper execution adapter disconnected")

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
        comment: Optional[str] = None
    ) -> ExecutionOrder:
        """
        Place simulated order.

        CRITICAL: This does NOT send to real broker.

        Args:
            instrument: Trading instrument
            side: BUY or SELL
            volume: Volume in lots
            order_type: Order type
            price: Limit/stop price
            stop_loss: Stop loss price
            take_profit: Take profit price
            magic_number: Magic number
            comment: Comment

        Returns:
            ExecutionOrder object
        """
        if not self._connected:
            raise RuntimeError("Paper adapter not connected")

        # Generate order ID
        order_id = f"PAPER_{uuid.uuid4().hex[:12]}"

        if magic_number is None:
            magic_number = int(time.time() * 1000) % 1000000

        # Create order
        order = ExecutionOrder(
            order_id=order_id,
            instrument=instrument,
            side=side,
            order_type=order_type,
            volume=volume,
            price=price,
            stop_loss=stop_loss,
            take_profit=take_profit,
            status=OrderStatus.PENDING,
            created_at=datetime.now(),
            magic_number=magic_number,
            comment=comment or "PAPER"
        )

        self._orders[order_id] = order

        logger.info(
            f"📝 PAPER ORDER placed: {order_id} {instrument} {side.value.upper()} "
            f"{volume} lots (type={order_type.value})"
        )

        # Simulate fill (immediate for market orders in paper mode)
        if order_type == OrderType.MARKET:
            self._simulate_fill(order)
        else:
            # Limit/stop orders would need price monitoring
            logger.warning(f"Limit/stop orders not fully supported in paper mode yet")
            order.status = OrderStatus.ACCEPTED

        return order

    def _simulate_fill(self, order: ExecutionOrder):
        """
        Simulate order fill.

        Uses VenueSimulator if enabled, otherwise instant fill.
        """
        # Get current market price
        prices = self._market_prices.get(order.instrument, {})
        if not prices:
            # Default prices for testing
            prices = {'bid': 1.1000, 'ask': 1.1002, 'mid': 1.1001}
            logger.warning(
                f"No market price for {order.instrument}, using defaults"
            )

        mid_price = prices['mid']

        # Simulate fill
        if self.venue_simulator:
            # Use sophisticated simulator
            result = self.venue_simulator.simulate_execution(
                instrument=order.instrument,
                side=order.side.value,
                order_size=order.volume,
                mid_at_send=mid_price,
                volatility=0.0001,  # Default volatility
                liquidity_score=1.0
            )

            if result.get('is_filled', False):
                order.status = OrderStatus.FILLED
                order.filled_volume = order.volume
                order.fill_price = result['fill_price']
                order.fill_timestamp = datetime.now()
                order.commission = order.volume * 7.0  # $7 per lot

                slippage_pips = result.get('price_drift_pips', 0.0)
                logger.info(
                    f"✅ PAPER FILL: {order.order_id} {order.filled_volume} lots "
                    f"@ {order.fill_price:.5f} (drift={slippage_pips:.2f} pips)"
                )

                # Create position
                self._create_position_from_order(order)

            else:
                order.status = OrderStatus.REJECTED
                logger.warning(
                    f"⚠️  PAPER REJECT: {order.order_id} (last-look)"
                )

        else:
            # Simple instant fill
            fill_price = prices['ask'] if order.side == OrderSide.BUY else prices['bid']
            order.status = OrderStatus.FILLED
            order.filled_volume = order.volume
            order.fill_price = fill_price
            order.fill_timestamp = datetime.now()
            order.commission = order.volume * 7.0

            logger.info(
                f"✅ PAPER FILL (instant): {order.order_id} {order.filled_volume} lots "
                f"@ {order.fill_price:.5f}"
            )

            self._create_position_from_order(order)

    def _create_position_from_order(self, order: ExecutionOrder):
        """Create virtual position from filled order."""
        position_id = f"POS_{order.order_id}"

        position = Position(
            position_id=position_id,
            instrument=order.instrument,
            side=order.side,
            volume=order.filled_volume,
            entry_price=order.fill_price,
            current_price=order.fill_price,
            unrealized_pnl=0.0,
            stop_loss=order.stop_loss,
            take_profit=order.take_profit,
            opened_at=order.fill_timestamp
        )

        self._positions[position_id] = position

        logger.info(
            f"📊 PAPER POSITION opened: {position_id} {order.instrument} "
            f"{order.side.value.upper()} {order.filled_volume} lots @ {order.fill_price:.5f}"
        )

    def modify_order(
        self,
        order_id: str,
        stop_loss: Optional[float] = None,
        take_profit: Optional[float] = None
    ) -> bool:
        """Modify order SL/TP (simulated)."""
        order = self._orders.get(order_id)
        if not order:
            logger.error(f"Order {order_id} not found")
            return False

        if stop_loss is not None:
            order.stop_loss = stop_loss
        if take_profit is not None:
            order.take_profit = take_profit

        logger.info(f"✏️  PAPER ORDER modified: {order_id} SL={stop_loss} TP={take_profit}")
        return True

    def cancel_order(self, order_id: str) -> bool:
        """Cancel order (simulated)."""
        order = self._orders.get(order_id)
        if not order:
            return False

        if order.status not in [OrderStatus.PENDING, OrderStatus.ACCEPTED]:
            logger.warning(f"Cannot cancel order {order_id} in status {order.status.value}")
            return False

        order.status = OrderStatus.CANCELLED
        logger.info(f"❌ PAPER ORDER cancelled: {order_id}")
        return True

    def close_position(self, position_id: str, volume: Optional[float] = None) -> bool:
        """Close position (simulated)."""
        position = self._positions.get(position_id)
        if not position:
            logger.error(f"Position {position_id} not found")
            return False

        close_volume = volume if volume is not None else position.volume

        # Get current price
        prices = self._market_prices.get(position.instrument, {})
        if not prices:
            prices = {'bid': position.current_price, 'ask': position.current_price}

        # Close price (opposite of entry side)
        close_price = prices['bid'] if position.side == OrderSide.BUY else prices['ask']

        # Calculate PnL
        if position.side == OrderSide.BUY:
            pnl = (close_price - position.entry_price) * close_volume * 100000  # Assuming FX
        else:
            pnl = (position.entry_price - close_price) * close_volume * 100000

        # Update balance
        self.balance += pnl
        self.equity = self.balance

        logger.info(
            f"🔒 PAPER POSITION closed: {position_id} {close_volume} lots "
            f"@ {close_price:.5f} (PnL=${pnl:.2f})"
        )

        # Remove position
        if close_volume >= position.volume:
            del self._positions[position_id]
        else:
            position.volume -= close_volume

        return True

    def get_order(self, order_id: str) -> Optional[ExecutionOrder]:
        """Get order by ID."""
        return self._orders.get(order_id)

    def get_open_orders(self, instrument: Optional[str] = None) -> List[ExecutionOrder]:
        """Get open orders."""
        orders = [
            o for o in self._orders.values()
            if o.status in [OrderStatus.PENDING, OrderStatus.ACCEPTED]
        ]

        if instrument:
            orders = [o for o in orders if o.instrument == instrument]

        return orders

    def get_positions(self, instrument: Optional[str] = None) -> List[Position]:
        """Get open positions."""
        positions = list(self._positions.values())

        if instrument:
            positions = [p for p in positions if p.instrument == instrument]

        return positions

    def get_account_info(self) -> AccountInfo:
        """Get virtual account info."""
        # Calculate margin used (simplified)
        margin_used = sum(p.volume * 1000 for p in self._positions.values())
        margin_free = self.equity - margin_used
        margin_level = (self.equity / margin_used * 100) if margin_used > 0 else 100.0

        return AccountInfo(
            account_id="PAPER_ACCOUNT",
            balance=self.balance,
            equity=self.equity,
            margin_free=margin_free,
            margin_used=margin_used,
            margin_level=margin_level,
            num_open_positions=len(self._positions)
        )

    def get_current_price(self, instrument: str) -> Dict[str, float]:
        """Get current market price."""
        return self._market_prices.get(
            instrument,
            {'bid': 1.1000, 'ask': 1.1002, 'mid': 1.1001}
        )

    def update_market_price(self, instrument: str, bid: float, ask: float):
        """
        Update simulated market price.

        Call this from market data feed to update prices.

        Args:
            instrument: Trading instrument
            bid: Bid price
            ask: Ask price
        """
        self._market_prices[instrument] = {
            'bid': bid,
            'ask': ask,
            'mid': (bid + ask) / 2
        }

        # Update unrealized PnL for open positions
        for position in self._positions.values():
            if position.instrument == instrument:
                current_price = bid if position.side == OrderSide.BUY else ask
                position.current_price = current_price

                if position.side == OrderSide.BUY:
                    position.unrealized_pnl = (
                        (current_price - position.entry_price) *
                        position.volume * 100000
                    )
                else:
                    position.unrealized_pnl = (
                        (position.entry_price - current_price) *
                        position.volume * 100000
                    )

        # Update equity
        total_unrealized = sum(p.unrealized_pnl for p in self._positions.values())
        self.equity = self.balance + total_unrealized

    def get_statistics(self) -> Dict:
        """Get paper trading statistics."""
        base_stats = super().get_statistics()

        filled_orders = [
            o for o in self._orders.values()
            if o.status == OrderStatus.FILLED
        ]

        return {
            **base_stats,
            'total_orders': len(self._orders),
            'filled_orders': len(filled_orders),
            'open_positions': len(self._positions),
            'balance': self.balance,
            'equity': self.equity,
            'pnl': self.equity - self.initial_balance,
            'pnl_pct': ((self.equity - self.initial_balance) / self.initial_balance * 100),
            'mode': 'PAPER (SIMULATED - NO REAL ORDERS)'
        }
