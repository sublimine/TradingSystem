"""
News Event Positioning Strategy - Institutional Implementation

Manages exposure around scheduled high-impact macroeconomic events through
volatility analysis, order book positioning, and systematic risk reduction.
"""

import numpy as np
import pandas as pd
from typing import List, Dict, Optional
from datetime import datetime, timedelta
from .strategy_base import StrategyBase, Signal


class NewsEventPositioning(StrategyBase):
    """
    Institutional event risk management strategy.
    
    Monitors scheduled macro events, reduces or closes exposure during high-risk windows,
    analyzes post-event price action and order flow for continuation opportunities.
    """

    def __init__(self, config: Dict):
        """
        Initialize news event positioning strategy.

        Required config parameters:
            - event_calendar: List of scheduled events with timestamps and impact levels
            - pre_event_window_minutes: Minutes before event to reduce exposure (typically 30)
            - post_event_window_minutes: Minutes after event before resuming (typically 15)
            - high_impact_threshold: Impact level requiring action (typically 3 on 1-5 scale)
            - position_reduction_factor: Exposure reduction multiplier (typically 0.5)
            - volatility_expansion_threshold: Vol increase indicating event impact (typically 2.0)
        """
        super().__init__(config)

        self.event_calendar = config.get('event_calendar', [])
        self.pre_event_window = config.get('pre_event_window_minutes', 30)
        self.post_event_window = config.get('post_event_window_minutes', 15)
        self.high_impact_threshold = config.get('high_impact_threshold', 3)
        self.position_reduction_factor = config.get('position_reduction_factor', 0.5)
        self.volatility_expansion_threshold = config.get('volatility_expansion_threshold', 2.0)

    def evaluate(self, market_data: pd.DataFrame, features: Dict) -> List[Signal]:
        """
        Evaluate event risk and generate risk management signals.

        Args:
            market_data: Recent OHLCV data
            features: Pre-calculated features

        Returns:
            List of risk management signals (typically empty or protective)
        """
        if not self.validate_inputs(market_data, features):
            return []

        signals = []

        current_time = market_data['time'].iloc[-1]

        upcoming_events = self._get_upcoming_events(current_time)

        if len(upcoming_events) > 0:
            return signals

        recent_events = self._get_recent_events(current_time)

        if len(recent_events) > 0:
            post_event_analysis = self._analyze_post_event_behavior(market_data, features, recent_events[0])

            if post_event_analysis['continuation_detected']:
                signal = self._generate_continuation_signal(market_data, post_event_analysis)
                if signal:
                    signals.append(signal)

        return signals

    def _get_upcoming_events(self, current_time: datetime) -> List[Dict]:
        """Identify events within pre-event window."""
        upcoming = []

        for event in self.event_calendar:
            event_time = event['timestamp']
            minutes_until = (event_time - current_time).total_seconds() / 60

            if 0 <= minutes_until <= self.pre_event_window:
                if event['impact_level'] >= self.high_impact_threshold:
                    upcoming.append(event)

        return upcoming

    def _get_recent_events(self, current_time: datetime) -> List[Dict]:
        """Identify events within post-event window."""
        recent = []

        for event in self.event_calendar:
            event_time = event['timestamp']
            minutes_since = (current_time - event_time).total_seconds() / 60

            if 0 <= minutes_since <= self.post_event_window:
                if event['impact_level'] >= self.high_impact_threshold:
                    recent.append(event)

        return recent

    def _analyze_post_event_behavior(self, market_data: pd.DataFrame, features: Dict, event: Dict) -> Dict:
        """Analyze price action following event release."""
        post_event_bars = market_data.tail(10)

        if len(post_event_bars) < 5:
            return {'continuation_detected': False}

        price_change = ((post_event_bars['close'].iloc[-1] - post_event_bars['close'].iloc[0]) / post_event_bars['close'].iloc[0]) * 100

        volume_avg_post = post_event_bars['volume'].mean()
        volume_avg_pre = market_data['volume'].tail(30).head(20).mean()

        volume_increase = volume_avg_post / volume_avg_pre if volume_avg_pre > 0 else 1.0

        decisive_move = abs(price_change) > 0.3
        elevated_volume = volume_increase > 1.5

        continuation_detected = decisive_move and elevated_volume

        analysis = {
            'continuation_detected': continuation_detected,
            'price_change_pct': float(price_change),
            'volume_increase_ratio': float(volume_increase),
            'event_name': event.get('name', 'Unknown'),
            'event_impact': event.get('impact_level', 0)
        }

        return analysis

    def _generate_continuation_signal(self, market_data: pd.DataFrame, analysis: Dict) -> Optional[Signal]:
        """Generate signal for post-event continuation trade."""
        symbol = market_data['symbol'].iloc[-1] if 'symbol' in market_data.columns else 'UNKNOWN'
        current_time = market_data['time'].iloc[-1]
        current_price = market_data['close'].iloc[-1]

        direction = 'LONG' if analysis['price_change_pct'] > 0 else 'SHORT'

        atr = (market_data['high'].tail(14) - market_data['low'].tail(14)).mean()

        if direction == 'LONG':
            stop_loss = current_price - (atr * 1.5)
            take_profit = current_price + (atr * 2.5)
        else:
            stop_loss = current_price + (atr * 1.5)
            take_profit = current_price - (atr * 2.5)

        sizing_level = 2

        metadata = {
            'event_driven_trade': True,
            'event_name': analysis['event_name'],
            'event_impact_level': analysis['event_impact'],
            'post_event_price_change_pct': analysis['price_change_pct'],
            'post_event_volume_increase': analysis['volume_increase_ratio'],
            'trade_type': 'continuation_momentum',
            'strategy_version': '1.0'
        }

        signal = Signal(
            timestamp=current_time,
            symbol=symbol,
            strategy_name=self.name,
            direction=direction,
            entry_price=float(current_price),
            stop_loss=float(stop_loss),
            take_profit=float(take_profit),
            sizing_level=sizing_level,
            metadata=metadata
        )

        return signal
