"""
Live Execution Adapter - MANDATO 21 (Stub)

Real broker execution for LIVE mode.

CRITICAL: This is a STUB for MANDATO 21.
Full implementation will be in MANDATO 23.

For MANDATO 21 (paper trading), this adapter should NOT be used.

Author: SUBLIMINE Institutional Trading System
Date: 2025-11-14
Mandato: MANDATO 21 - Paper Trading Institucional
"""

import logging
from typing import Dict, List, Optional

from .execution_adapter import (
    ExecutionAdapter,
    ExecutionOrder,
    Position,
    AccountInfo,
    OrderSide,
    OrderType,
    OrderStatus
)

logger = logging.getLogger(__name__)


class LiveExecutionAdapter(ExecutionAdapter):
    """
    Live execution adapter (STUB).

    TODO (MANDATO 23):
    - MT5 integration for real orders
    - Real position tracking
    - Real account queries
    - Risk checks before sending to broker
    - Confirmation prompts

    For MANDATO 21, this should NOT be used.
    """

    def __init__(self, config: dict):
        """
        Initialize live execution adapter.

        Args:
            config: System configuration
        """
        super().__init__(adapter_name="LiveExecutionAdapter", config=config)

        logger.warning(
            "⚠️  LiveExecutionAdapter is a STUB - "
            "full implementation in MANDATO 23"
        )

        raise NotImplementedError(
            "LiveExecutionAdapter not implemented yet. "
            "Use PaperExecutionAdapter for MANDATO 21. "
            "Live trading will be implemented in MANDATO 23."
        )

    def connect(self) -> bool:
        """Connect to real broker (NOT IMPLEMENTED)."""
        raise NotImplementedError("Live execution not implemented yet (MANDATO 23)")

    def disconnect(self):
        """Disconnect from broker (NOT IMPLEMENTED)."""
        raise NotImplementedError("Live execution not implemented yet (MANDATO 23)")

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
        """Place real order (NOT IMPLEMENTED)."""
        raise NotImplementedError("Live execution not implemented yet (MANDATO 23)")

    def modify_order(
        self,
        order_id: str,
        stop_loss: Optional[float] = None,
        take_profit: Optional[float] = None
    ) -> bool:
        """Modify order (NOT IMPLEMENTED)."""
        raise NotImplementedError("Live execution not implemented yet (MANDATO 23)")

    def cancel_order(self, order_id: str) -> bool:
        """Cancel order (NOT IMPLEMENTED)."""
        raise NotImplementedError("Live execution not implemented yet (MANDATO 23)")

    def close_position(self, position_id: str, volume: Optional[float] = None) -> bool:
        """Close position (NOT IMPLEMENTED)."""
        raise NotImplementedError("Live execution not implemented yet (MANDATO 23)")

    def get_order(self, order_id: str) -> Optional[ExecutionOrder]:
        """Get order (NOT IMPLEMENTED)."""
        raise NotImplementedError("Live execution not implemented yet (MANDATO 23)")

    def get_open_orders(self, instrument: Optional[str] = None) -> List[ExecutionOrder]:
        """Get open orders (NOT IMPLEMENTED)."""
        raise NotImplementedError("Live execution not implemented yet (MANDATO 23)")

    def get_positions(self, instrument: Optional[str] = None) -> List[Position]:
        """Get positions (NOT IMPLEMENTED)."""
        raise NotImplementedError("Live execution not implemented yet (MANDATO 23)")

    def get_account_info(self) -> AccountInfo:
        """Get account info (NOT IMPLEMENTED)."""
        raise NotImplementedError("Live execution not implemented yet (MANDATO 23)")

    def get_current_price(self, instrument: str) -> Dict[str, float]:
        """Get current price (NOT IMPLEMENTED)."""
        raise NotImplementedError("Live execution not implemented yet (MANDATO 23)")
