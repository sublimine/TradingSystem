"""
Execution Adapter - Base abstraction for execution backends

MANDATO 21: Separates execution logic from trading logic.

ExecutionAdapter provides interface for:
- Placing orders (real or simulated)
- Managing positions
- Getting account info
- Order status tracking

Implementations:
- PaperExecutionAdapter: Simulated execution (NO real broker)
- LiveExecutionAdapter: Real broker execution (MT5, etc.)

Author: SUBLIMINE Institutional Trading System
Date: 2025-11-14
Mandato: MANDATO 21 - Paper Trading Institucional
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class OrderSide(Enum):
    """Order side."""
    BUY = "buy"
    SELL = "sell"


class OrderType(Enum):
    """Order type."""
    MARKET = "market"
    LIMIT = "limit"
    STOP = "stop"
    STOP_LIMIT = "stop_limit"


class OrderStatus(Enum):
    """Order status."""
    PENDING = "pending"
    ACCEPTED = "accepted"
    PARTIALLY_FILLED = "partial"
    FILLED = "filled"
    REJECTED = "rejected"
    CANCELLED = "cancelled"


@dataclass
class ExecutionOrder:
    """Order representation for execution."""
    order_id: str
    instrument: str
    side: OrderSide
    order_type: OrderType
    volume: float
    price: Optional[float]
    stop_loss: Optional[float]
    take_profit: Optional[float]
    status: OrderStatus
    created_at: datetime

    # Execution details
    filled_volume: float = 0.0
    fill_price: Optional[float] = None
    fill_timestamp: Optional[datetime] = None
    commission: float = 0.0

    # Metadata
    magic_number: Optional[int] = None
    comment: Optional[str] = None


@dataclass
class Position:
    """Position representation."""
    position_id: str
    instrument: str
    side: OrderSide
    volume: float
    entry_price: float
    current_price: float
    unrealized_pnl: float
    stop_loss: Optional[float]
    take_profit: Optional[float]
    opened_at: datetime


@dataclass
class AccountInfo:
    """Account information."""
    account_id: str
    balance: float
    equity: float
    margin_free: float
    margin_used: float
    margin_level: float
    num_open_positions: int


class ExecutionAdapter(ABC):
    """
    Base class for execution adapters.

    Provides interface for:
    - Order placement
    - Position management
    - Account queries

    Implementations:
    - PaperExecutionAdapter: Simulated execution
    - LiveExecutionAdapter: Real broker
    """

    def __init__(self, adapter_name: str, config: dict):
        """
        Initialize execution adapter.

        Args:
            adapter_name: Name of adapter (for logging)
            config: Configuration dict
        """
        self.adapter_name = adapter_name
        self.config = config
        self._connected = False

        logger.info(f"ExecutionAdapter initialized: {adapter_name}")

    @abstractmethod
    def connect(self) -> bool:
        """
        Connect to execution backend (broker, simulator, etc.).

        Returns:
            True if connection successful, False otherwise
        """
        pass

    @abstractmethod
    def disconnect(self):
        """Disconnect from execution backend."""
        pass

    @abstractmethod
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
        Place order.

        Args:
            instrument: Trading instrument
            side: BUY or SELL
            volume: Volume in lots
            order_type: Order type
            price: Limit/stop price (if applicable)
            stop_loss: Stop loss price
            take_profit: Take profit price
            magic_number: Magic number for tracking
            comment: Order comment

        Returns:
            ExecutionOrder object

        Raises:
            Exception: If order placement fails
        """
        pass

    @abstractmethod
    def modify_order(
        self,
        order_id: str,
        stop_loss: Optional[float] = None,
        take_profit: Optional[float] = None
    ) -> bool:
        """
        Modify existing order (SL/TP).

        Args:
            order_id: Order ID
            stop_loss: New stop loss (None = no change)
            take_profit: New take profit (None = no change)

        Returns:
            True if modification successful
        """
        pass

    @abstractmethod
    def cancel_order(self, order_id: str) -> bool:
        """
        Cancel pending order.

        Args:
            order_id: Order ID

        Returns:
            True if cancellation successful
        """
        pass

    @abstractmethod
    def close_position(self, position_id: str, volume: Optional[float] = None) -> bool:
        """
        Close position (full or partial).

        Args:
            position_id: Position ID
            volume: Volume to close (None = close all)

        Returns:
            True if close successful
        """
        pass

    @abstractmethod
    def get_order(self, order_id: str) -> Optional[ExecutionOrder]:
        """
        Get order by ID.

        Args:
            order_id: Order ID

        Returns:
            ExecutionOrder if found, None otherwise
        """
        pass

    @abstractmethod
    def get_open_orders(self, instrument: Optional[str] = None) -> List[ExecutionOrder]:
        """
        Get all open orders.

        Args:
            instrument: Filter by instrument (None = all)

        Returns:
            List of open orders
        """
        pass

    @abstractmethod
    def get_positions(self, instrument: Optional[str] = None) -> List[Position]:
        """
        Get all open positions.

        Args:
            instrument: Filter by instrument (None = all)

        Returns:
            List of positions
        """
        pass

    @abstractmethod
    def get_account_info(self) -> AccountInfo:
        """
        Get account information.

        Returns:
            AccountInfo object
        """
        pass

    @abstractmethod
    def get_current_price(self, instrument: str) -> Dict[str, float]:
        """
        Get current market price.

        Args:
            instrument: Trading instrument

        Returns:
            Dict with 'bid', 'ask', 'mid' keys
        """
        pass

    def is_connected(self) -> bool:
        """Check if adapter is connected."""
        return self._connected

    def get_adapter_name(self) -> str:
        """Get adapter name."""
        return self.adapter_name

    def get_statistics(self) -> Dict:
        """
        Get adapter statistics (optional).

        Returns:
            Dict with statistics (implementation-specific)
        """
        return {
            'adapter_name': self.adapter_name,
            'connected': self._connected
        }
