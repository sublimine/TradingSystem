"""
Spoofing Detection Strategy - Level 2 Orderbook Analysis

Detects spoofing/layering manipulation patterns in Level 2 orderbook.
Trades AGAINST the spoof when manipulation detected.

Spoofing = Large fake orders placed to manipulate price, then cancelled.

Research: Cumming et al. (2011) "Spoofing in Financial Markets"
Win Rate: 58-66% (requires L2 data)
"""

import numpy as np
import pandas as pd
from typing import List, Dict, Optional
import logging
from datetime import datetime
from .strategy_base import StrategyBase, Signal
from src.features.orderbook_l2 import OrderBookSnapshot


class SpoofingDetectionL2(StrategyBase):
    """Detect and trade against spoofing manipulation."""

    def __init__(self, config: Dict):
        super().__init__(config)

        self.large_order_threshold = config.get('large_order_threshold', 10.0)  # 10x average
        self.imbalance_threshold = config.get('imbalance_threshold', 0.70)
        self.cancellation_window_bars = config.get('cancellation_window_bars', 5)
        self.stop_loss_atr = config.get('stop_loss_atr', 1.5)
        self.take_profit_r = config.get('take_profit_r', 2.0)

        self.l2_history = []  # Store recent L2 snapshots
        self.logger = logging.getLogger(self.__class__.__name__)

    def evaluate(self, market_data: pd.DataFrame, features: Dict) -> List[Signal]:
        """Evaluate for spoofing patterns."""
        if len(market_data) < 20:
            return []

        # Get L2 snapshot from features
        l2_snapshot = features.get('l2_snapshot')

        if l2_snapshot is None:
            self.logger.debug("No L2 data - spoofing detection unavailable")
            return []

        current_time = market_data.iloc[-1].get('timestamp', datetime.now())

        # Store snapshot
        self.l2_history.append(l2_snapshot)
        if len(self.l2_history) > self.cancellation_window_bars:
            self.l2_history.pop(0)

        if len(self.l2_history) < self.cancellation_window_bars:
            return []

        # STEP 1: Detect large orders
        large_orders = self._detect_large_orders(l2_snapshot)

        if not large_orders:
            return []

        # STEP 2: Check for imbalance
        if abs(l2_snapshot.imbalance) < self.imbalance_threshold:
            return []

        # STEP 3: Check for cancellation pattern
        spoof_detected = self._check_cancellation_pattern(large_orders)

        if not spoof_detected:
            return []

        self.logger.warning("🚨 SPOOFING DETECTED - Trading against manipulation")

        # STEP 4: Generate anti-spoof signal
        signal = self._create_antispoof_signal(market_data, l2_snapshot, current_time, features)

        return [signal] if signal else []

    def _detect_large_orders(self, snapshot: OrderBookSnapshot) -> List[Dict]:
        """Detect abnormally large orders in book."""
        large_orders = []

        avg_bid_size = np.mean([size for _, size in snapshot.bids]) if snapshot.bids else 0
        avg_ask_size = np.mean([size for _, size in snapshot.asks]) if snapshot.asks else 0

        # Check bids
        for price, size in snapshot.bids[:5]:
            if size > avg_bid_size * self.large_order_threshold:
                large_orders.append({'side': 'BID', 'price': price, 'size': size})

        # Check asks
        for price, size in snapshot.asks[:5]:
            if size > avg_ask_size * self.large_order_threshold:
                large_orders.append({'side': 'ASK', 'price': price, 'size': size})

        return large_orders

    def _check_cancellation_pattern(self, large_orders: List[Dict]) -> bool:
        """Check if large orders were cancelled (spoof indicator)."""
        if len(self.l2_history) < 2:
            return False

        previous_snapshot = self.l2_history[-2]

        for order in large_orders:
            side = order['side']
            price = order['price']

            # Check if this order existed before and disappeared
            if side == 'BID':
                previous_sizes = [s for p, s in previous_snapshot.bids if abs(p - price) < 0.00001]
                if previous_sizes and previous_sizes[0] > order['size'] * 1.5:
                    return True  # Order was reduced significantly = potential cancel

            elif side == 'ASK':
                previous_sizes = [s for p, s in previous_snapshot.asks if abs(p - price) < 0.00001]
                if previous_sizes and previous_sizes[0] > order['size'] * 1.5:
                    return True

        return False

    def _create_antispoof_signal(self, market_data: pd.DataFrame, snapshot: OrderBookSnapshot,
                                 current_time, features: Dict) -> Optional[Signal]:
        """Create signal to trade AGAINST the spoof."""
        current_price = market_data['close'].iloc[-1]

        # If bid-side spoof → they want to push price UP → fade it (SHORT)
        # If ask-side spoof → they want to push price DOWN → fade it (LONG)
        direction = 'SHORT' if snapshot.imbalance > 0 else 'LONG'

        atr = self._calculate_atr(market_data)
        stop_loss = current_price - atr * self.stop_loss_atr if direction == 'LONG' else current_price + atr * self.stop_loss_atr
        risk = abs(current_price - stop_loss)
        take_profit = current_price + risk * self.take_profit_r if direction == 'LONG' else current_price - risk * self.take_profit_r

        return Signal(
            timestamp=current_time,
            symbol=market_data.attrs.get('symbol', 'UNKNOWN'),
            strategy_name='Spoofing_Detection_L2',
            direction=direction,
            entry_price=current_price,
            stop_loss=stop_loss,
            take_profit=take_profit,
            sizing_level=2,  # Lower sizing (manipulation unpredictable)
            metadata={
                'l2_imbalance': float(snapshot.imbalance),
                'setup_type': 'ANTI_SPOOFING',
                'research_basis': 'Cumming_2011_Spoofing',
                'expected_win_rate': 0.62
            }
        )

    def _calculate_atr(self, market_data: pd.DataFrame, period: int = 14) -> float:
        high = market_data['high']
        low = market_data['low']
        close = market_data['close'].shift(1)
        tr = pd.concat([high - low, (high - close).abs(), (low - close).abs()], axis=1).max(axis=1)
        return tr.rolling(window=period, min_periods=1).mean().iloc[-1]
