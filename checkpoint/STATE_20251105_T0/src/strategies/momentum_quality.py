"""
Momentum Quality Strategy

Evaluates quality of momentum movements through confluence analysis.
Generates signals only when momentum is supported by multiple confirming factors
including price strength, volume confirmation, and order flow toxicity.
"""

import numpy as np
import pandas as pd
from typing import List, Dict, Optional
from datetime import datetime
from .strategy_base import StrategyBase, Signal


class MomentumQuality(StrategyBase):
    """
    Strategy that filters momentum trades by quality score.
    
    Enters positions only when momentum shows high quality through confluence
    of price movement, volume support, and order flow confirmation.
    """

    def __init__(self, config: Dict):
        """
        Initialize momentum quality strategy.

        Required config parameters:
            - momentum_period: Period for momentum calculation (typically 14)
            - price_threshold: Minimum price movement percentage (typically 0.5)
            - volume_threshold: Volume multiplier for confirmation (typically 1.5)
            - vpin_threshold: VPIN level indicating toxic flow (typically 0.60)
            - min_quality_score: Minimum quality score for entry (typically 0.70)
            - lookback_window: Window for context analysis (typically 20)
            - use_regime_filter: Whether to filter by volatility regime (typically True)
        """
        super().__init__(config)

        self.momentum_period = config.get('momentum_period', 14)
        self.price_threshold = config.get('price_threshold', 0.35)
        self.volume_threshold = config.get('volume_threshold', 1.5)
        self.vpin_threshold = config.get('vpin_threshold', 0.60)
        self.min_quality_score = config.get('min_quality_score', 0.60)
        self.lookback_window = config.get('lookback_window', 20)
        self.use_regime_filter = config.get('use_regime_filter', True)

    def evaluate(self, market_data: pd.DataFrame, features: Dict) -> List[Signal]:
        """
        Evaluate market for high-quality momentum opportunities.

        Args:
            market_data: Recent OHLCV data
            features: Pre-calculated features including momentum indicators

        Returns:
            List of signals for high-quality momentum setups
        """
        if not self.validate_inputs(market_data, features):
            return []

        if len(market_data) < self.momentum_period:
            return []

        signals = []

        momentum_analysis = self._analyze_momentum_quality(market_data, features)
        
        if momentum_analysis is None:
            return []

        if momentum_analysis['quality_score'] >= self.min_quality_score:
            if self.use_regime_filter:
                regime_check = self._check_regime_compatibility(features, momentum_analysis)
                if not regime_check:
                    return []

            signal = self._generate_momentum_signal(market_data, momentum_analysis)
            if signal:
                signals.append(signal)

        return signals

    def _analyze_momentum_quality(self, market_data: pd.DataFrame, features: Dict) -> Optional[Dict]:
        """Analyze momentum quality using multiple confirmation factors."""
        closes = market_data['close'].tail(self.momentum_period + 1).values
        volumes = market_data['volume'].tail(self.momentum_period).values

        if len(closes) < self.momentum_period + 1:
            return None

        price_change_pct = ((closes[-1] - closes[0]) / closes[0]) * 100
        direction = 1 if price_change_pct > 0 else -1

        if abs(price_change_pct) < self.price_threshold:
            return None

        price_strength = min(abs(price_change_pct) / (self.price_threshold * 3), 1.0)

        recent_volume_avg = np.mean(volumes[:-5]) if len(volumes) > 5 else np.mean(volumes)
        current_volume_avg = np.mean(volumes[-5:]) if len(volumes) >= 5 else volumes[-1]

        volume_increasing = current_volume_avg > (recent_volume_avg * self.volume_threshold)
        volume_confirmation = 1.0 if volume_increasing else 0.3

        flow_confirmation = 0.5
        if 'vpin' in features:
            vpin_current = features['vpin']
            if vpin_current >= self.vpin_threshold:
                if 'order_flow_imbalance' in features:
                    imbalance = features['order_flow_imbalance']
                    imbalance_direction = 1 if imbalance > 0 else -1
                    if imbalance_direction == direction:
                        flow_confirmation = 1.0
                    else:
                        flow_confirmation = 0.2
                else:
                    flow_confirmation = 0.8
            else:
                flow_confirmation = 0.4

        quality_score = (price_strength * 0.4) + (volume_confirmation * 0.3) + (flow_confirmation * 0.3)

        analysis = {
            'direction': direction,
            'price_change_pct': float(price_change_pct),
            'price_strength': float(price_strength),
            'volume_confirmation': float(volume_confirmation),
            'flow_confirmation': float(flow_confirmation),
            'quality_score': float(quality_score),
            'volume_increasing': volume_increasing,
            'vpin_value': float(features.get('vpin', 0.0))
        }

        return analysis

    def _check_regime_compatibility(self, features: Dict, momentum_analysis: Dict) -> bool:
        """Check if current regime is compatible with momentum trading."""
        if 'volatility_regime' not in features:
            return True

        regime = features['volatility_regime']
        
        if regime == 'HIGH_VOLATILITY':
            if momentum_analysis['quality_score'] < 0.75:
                return False

        return True

    def _generate_momentum_signal(self, market_data: pd.DataFrame, analysis: Dict) -> Optional[Signal]:
        """Generate signal for high-quality momentum setup."""
        symbol = market_data['symbol'].iloc[-1] if 'symbol' in market_data.columns else 'UNKNOWN'
        current_time = market_data['time'].iloc[-1]
        current_price = market_data['close'].iloc[-1]
        direction = 'LONG' if analysis['direction'] > 0 else 'SHORT'

        atr = (market_data['high'].tail(14) - market_data['low'].tail(14)).mean()

        recent_swing_points = self._identify_recent_swing_points(market_data)
        
        if direction == 'LONG':
            if recent_swing_points['swing_low'] is not None:
                stop_loss = recent_swing_points['swing_low'] - (atr * 0.5)
            else:
                stop_loss = current_price - (atr * 2.0)
            
            price_move = abs(analysis['price_change_pct']) / 100 * current_price
            take_profit = current_price + (price_move * 1.5)
        else:
            if recent_swing_points['swing_high'] is not None:
                stop_loss = recent_swing_points['swing_high'] + (atr * 0.5)
            else:
                stop_loss = current_price + (atr * 2.0)
            
            price_move = abs(analysis['price_change_pct']) / 100 * current_price
            take_profit = current_price - (price_move * 1.5)

        quality_score = analysis['quality_score']
        if quality_score >= 0.85:
            sizing_level = 5
        elif quality_score >= 0.80:
            sizing_level = 4
        else:
            sizing_level = 3

        metadata = {
            'momentum_direction': analysis['direction'],
            'price_change_pct': analysis['price_change_pct'],
            'price_strength': analysis['price_strength'],
            'volume_confirmation': analysis['volume_confirmation'],
            'flow_confirmation': analysis['flow_confirmation'],
            'quality_score': analysis['quality_score'],
            'volume_increasing': analysis['volume_increasing'],
            'vpin_value': analysis['vpin_value'],
            'stop_type': 'swing_point' if recent_swing_points.get('swing_low' if direction == 'LONG' else 'swing_high') else 'atr_based',
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

    def _identify_recent_swing_points(self, market_data: pd.DataFrame) -> Dict:
        """Identify recent swing high and swing low points."""
        lookback = min(self.lookback_window, len(market_data))
        recent_data = market_data.tail(lookback)

        highs = recent_data['high'].values
        lows = recent_data['low'].values

        swing_high = None
        swing_low = None

        if len(highs) >= 5:
            for i in range(len(highs) - 3, 1, -1):
                if highs[i] > highs[i-1] and highs[i] > highs[i-2] and \
                   highs[i] > highs[i+1] and highs[i] > highs[i+2]:
                    swing_high = highs[i]
                    break

        if len(lows) >= 5:
            for i in range(len(lows) - 3, 1, -1):
                if lows[i] < lows[i-1] and lows[i] < lows[i-2] and \
                   lows[i] < lows[i+1] and lows[i] < lows[i+2]:
                    swing_low = lows[i]
                    break

        return {
            'swing_high': swing_high,
            'swing_low': swing_low
        }

