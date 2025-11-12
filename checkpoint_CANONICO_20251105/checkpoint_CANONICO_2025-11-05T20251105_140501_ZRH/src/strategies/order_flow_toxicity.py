"""
Order Flow Toxicity Strategy

Detects toxic order flow using VPIN indicating informed trading activity.
Enters positions in direction of toxic flow anticipating continuation.
"""

import numpy as np
import pandas as pd
from typing import List, Dict, Optional
from datetime import datetime
from .strategy_base import StrategyBase, Signal


class OrderFlowToxicityStrategy(StrategyBase):
    """
    Strategy that identifies and trades toxic order flow periods.

    Entry occurs when VPIN exceeds threshold sustained over multiple buckets,
    indicating persistent informed trading pressure in one direction.
    """

    def __init__(self, config: Dict):
        """
        Initialize order flow toxicity strategy.

        Required config parameters:
            - vpin_threshold: Minimum VPIN level (typically 0.65)
            - min_consecutive_buckets: Minimum buckets with high VPIN (typically 3)
            - flow_direction_threshold: Minimum imbalance to determine direction
            - context_verification_enabled: Whether to verify market context
            - max_extension_atr_multiple: Maximum price extension from entry level
        """
        super().__init__(config)

        self.vpin_threshold = config.get('vpin_threshold', 0.55)
        self.min_consecutive_buckets = config.get('min_consecutive_buckets', 2)
        self.flow_direction_threshold = config.get('flow_direction_threshold', 0.2)
        self.context_verification = config.get('context_verification_enabled', True)
        self.max_extension_multiple = config.get('max_extension_atr_multiple', 2.0)

        self.vpin_history = []

    def evaluate(self, market_data: pd.DataFrame, features: Dict) -> List[Signal]:
        """
        Evaluate market for toxic order flow opportunities.

        Args:
            market_data: Recent OHLCV data
            features: Pre-calculated features including VPIN and flow metrics

        Returns:
            List of signals generated
        """
        if not self.validate_inputs(market_data, features):
            return []

        if 'vpin' not in features or 'order_flow_imbalance' not in features:
            return []

        signals = []

        current_vpin = features['vpin']

        self.vpin_history.append(current_vpin)
        if len(self.vpin_history) > 10:
            self.vpin_history.pop(0)

        if not self._check_sustained_toxicity():
            return []

        flow_direction = self._determine_flow_direction(features)
        if flow_direction == 0:
            return []

        if self.context_verification and not self._verify_market_context(market_data, flow_direction):
            return []

        signal = self._generate_flow_signal(market_data, features, flow_direction)
        if signal:
            signals.append(signal)

        return signals

    def _check_sustained_toxicity(self) -> bool:
        """Check if VPIN has been elevated for minimum consecutive periods."""
        if len(self.vpin_history) < self.min_consecutive_buckets:
            return False

        recent_vpin = self.vpin_history[-self.min_consecutive_buckets:]
        return all(v >= self.vpin_threshold for v in recent_vpin)

    def _determine_flow_direction(self, features: dict) -> int:
        """
        Determine direction of order flow based on imbalance magnitude

        Args:
            features: Dictionary containing order_flow_imbalance

        Returns:
            1 for bullish flow, -1 for bearish flow, 0 for neutral/insufficient
        """
        imbalance = features.get('order_flow_imbalance', 0.0)
        threshold = self.flow_direction_threshold

        if abs(imbalance) < threshold:
            return 0

        return 1 if imbalance > 0 else -1

    def _verify_market_context(self, market_data: pd.DataFrame, flow_direction: int) -> bool:
        """Verify that price movement aligns with flow direction."""
        recent_bars = market_data.tail(5)
        price_change = recent_bars['close'].iloc[-1] - recent_bars['close'].iloc[0]

        price_direction = 1 if price_change > 0 else -1

        return price_direction == flow_direction

    def _generate_flow_signal(self, market_data: pd.DataFrame, features: Dict,
                             flow_direction: int) -> Optional[Signal]:
        """Generate signal based on toxic flow detection."""
        symbol = market_data['symbol'].iloc[-1] if 'symbol' in market_data.columns else 'UNKNOWN'
        current_price = market_data['close'].iloc[-1]
        current_time = market_data['time'].iloc[-1]

        atr = (market_data['high'].tail(14) - market_data['low'].tail(14)).mean()

        if flow_direction > 0:
            direction = 'LONG'
            entry_price = current_price
            stop_loss = current_price - (atr * 2.0)
            take_profit = current_price + (atr * 3.0)
        else:
            direction = 'SHORT'
            entry_price = current_price
            stop_loss = current_price + (atr * 2.0)
            take_profit = current_price - (atr * 3.0)

        metadata = {
            'vpin_current': float(features['vpin']),
            'flow_imbalance': float(features['order_flow_imbalance']),
            'flow_direction': flow_direction,
            'consecutive_toxic_periods': len([v for v in self.vpin_history if v >= self.vpin_threshold]),
            'strategy_version': '1.0'
        }

        signal = Signal(
            timestamp=current_time,
            symbol=symbol,
            strategy_name=self.name,
            direction=direction,
            entry_price=float(entry_price),
            stop_loss=float(stop_loss),
            take_profit=float(take_profit),
            sizing_level=3,
            metadata=metadata
        )

        return signal
