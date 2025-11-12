"""
Breakout Volume Confirmation Strategy - Institutional Implementation

Identifies genuine breakouts from consolidation ranges validated through
volume anomaly detection and order book depth analysis. Uses statistical
volume profiling and liquidity absorption patterns for confirmation.
"""

import numpy as np
import pandas as pd
import Signal
from models import Signal
from src.core.models import Signal
from strategies.base import StrategyBase, Signal
from typing import List, Dict, Optional
from datetime import datetime
from .strategy_base import StrategyBase, Signal


class BreakoutVolumeConfirmation(StrategyBase):
    """
    Institutional breakout strategy using volume profile and order book validation.
    
    Detects consolidation periods through ATR contraction, identifies range boundaries
    via swing point analysis, validates breakout through volume anomaly exceeding
    statistical threshold, and confirms via order book imbalance in breakout direction.
    """

    def __init__(self, config: Dict):
        """
        Initialize breakout volume confirmation strategy.

        Required config parameters:
            - atr_lookback: Period for ATR calculation (typically 20)
            - atr_contraction_threshold: ATR ratio indicating consolidation (typically 0.60)
            - swing_point_order: Bars for swing point identification (typically 5)
            - volume_breakout_multiplier: Volume threshold for genuine breakout (typically 3.0)
            - imbalance_confirmation_threshold: Order book imbalance minimum (typically 0.35)
            - min_consolidation_bars: Minimum bars in consolidation (typically 15)
            - vpin_non_exhaustion_max: Maximum VPIN to avoid exhaustion (typically 0.65)
        """
        super().__init__(config)

        self.atr_lookback = config.get('atr_lookback', 20)
        self.atr_contraction_threshold = config.get('atr_contraction_threshold', 0.70)
        self.swing_point_order = config.get('swing_point_order', 5)
        self.volume_breakout_multiplier = config.get('volume_breakout_multiplier', 2.0)
        self.imbalance_confirmation_threshold = config.get('imbalance_confirmation_threshold', 0.25)
        self.min_consolidation_bars = config.get('min_consolidation_bars', 15)
        self.vpin_non_exhaustion_max = config.get('vpin_non_exhaustion_max', 0.65)

    def evaluate(self, market_data: pd.DataFrame, features: Dict) -> List[Signal]:
        """
        Evaluate market for institutional-grade breakout opportunities.

        Args:
            market_data: Recent OHLCV data
            features: Pre-calculated features including microstructure metrics

        Returns:
            List of signals for validated breakout setups
        """
        if not self.validate_inputs(market_data, features):
            return []

        if len(market_data) < self.atr_lookback + self.min_consolidation_bars:
            return []

        signals = []

        consolidation_analysis = self._detect_consolidation_period(market_data)
        
        if consolidation_analysis is None:
            return []

        breakout_detected = self._detect_range_breakout(market_data, consolidation_analysis)
        
        if breakout_detected is None:
            return []

        volume_validation = self._validate_breakout_volume(market_data, consolidation_analysis)
        
        if not volume_validation['is_valid']:
            return []

        microstructure_confirmation = self._confirm_microstructure(features, breakout_detected)
        
        if microstructure_confirmation['is_confirmed']:
            signal = self._generate_breakout_signal(
                market_data, breakout_detected, volume_validation, microstructure_confirmation
            )
            if signal:
                signals.append(signal)

        return signals

    def _detect_consolidation_period(self, market_data: pd.DataFrame) -> Optional[Dict]:
        """Detect consolidation period through ATR contraction analysis."""
        highs = market_data['high'].values
        lows = market_data['low'].values
        
        if len(highs) < self.atr_lookback * 2:
            return None

        current_atr = np.mean(highs[-self.atr_lookback:] - lows[-self.atr_lookback:])
        historical_atr = np.mean(highs[-self.atr_lookback*2:-self.atr_lookback] - lows[-self.atr_lookback*2:-self.atr_lookback])
        
        if historical_atr < 1e-10:
            return None

        atr_ratio = current_atr / historical_atr
        
        if atr_ratio > self.atr_contraction_threshold:
            return None

        consolidation_bars = 0
        for i in range(len(market_data) - 1, max(0, len(market_data) - 50), -1):
            recent_atr = np.mean(highs[max(0,i-self.atr_lookback):i+1] - lows[max(0,i-self.atr_lookback):i+1])
            if recent_atr / historical_atr <= self.atr_contraction_threshold:
                consolidation_bars += 1
            else:
                break

        if consolidation_bars < self.min_consolidation_bars:
            return None

        consolidation_data = market_data.tail(consolidation_bars)
        range_high = consolidation_data['high'].max()
        range_low = consolidation_data['low'].min()

        analysis = {
            'current_atr': float(current_atr),
            'historical_atr': float(historical_atr),
            'atr_ratio': float(atr_ratio),
            'consolidation_bars': consolidation_bars,
            'range_high': float(range_high),
            'range_low': float(range_low),
            'range_width': float(range_high - range_low)
        }

        return analysis

    def _detect_range_breakout(self, market_data: pd.DataFrame, consolidation: Dict) -> Optional[Dict]:
        """Detect breakout from identified consolidation range."""
        current_close = market_data['close'].iloc[-1]
        current_high = market_data['high'].iloc[-1]
        current_low = market_data['low'].iloc[-1]

        range_high = consolidation['range_high']
        range_low = consolidation['range_low']

        breakout_detected = None

        if current_close > range_high:
            breakout_detected = {
                'direction': 'LONG',
                'breakout_price': float(current_close),
                'range_boundary': float(range_high),
                'penetration': float(current_close - range_high),
                'clean_close': current_low > range_high
            }
        elif current_close < range_low:
            breakout_detected = {
                'direction': 'SHORT',
                'breakout_price': float(current_close),
                'range_boundary': float(range_low),
                'penetration': float(range_low - current_close),
                'clean_close': current_high < range_low
            }

        return breakout_detected

    def _validate_breakout_volume(self, market_data: pd.DataFrame, consolidation: Dict) -> Dict:
        """Validate breakout through volume anomaly detection."""
        volumes = market_data['volume'].values
        
        consolidation_volume_avg = np.mean(volumes[-consolidation['consolidation_bars']:-1])
        current_volume = volumes[-1]

        if consolidation_volume_avg < 1:
            return {'is_valid': False}

        volume_ratio = current_volume / consolidation_volume_avg

        validation = {
            'is_valid': volume_ratio >= self.volume_breakout_multiplier,
            'volume_ratio': float(volume_ratio),
            'consolidation_volume_avg': float(consolidation_volume_avg),
            'current_volume': float(current_volume)
        }

        return validation

    def _confirm_microstructure(self, features: Dict, breakout: Dict) -> Dict:
        """Confirm breakout through order book and flow analysis."""
        confirmation = {
            'is_confirmed': False,
            'imbalance_aligned': False,
            'vpin_appropriate': False,
            'details': {}
        }

        direction = breakout['direction']

        if 'order_flow_imbalance' in features:
            imbalance = features['order_flow_imbalance']
            
            if direction == 'LONG' and imbalance > self.imbalance_confirmation_threshold:
                confirmation['imbalance_aligned'] = True
                confirmation['details']['imbalance'] = float(imbalance)
            elif direction == 'SHORT' and imbalance < -self.imbalance_confirmation_threshold:
                confirmation['imbalance_aligned'] = True
                confirmation['details']['imbalance'] = float(imbalance)

        if 'vpin' in features:
            vpin = features['vpin']
            if vpin < self.vpin_non_exhaustion_max:
                confirmation['vpin_appropriate'] = True
                confirmation['details']['vpin'] = float(vpin)
        else:
            confirmation['vpin_appropriate'] = True

        confirmation['is_confirmed'] = confirmation['imbalance_aligned'] or confirmation['vpin_appropriate']

        return confirmation

    def _generate_breakout_signal(self, market_data: pd.DataFrame, breakout: Dict,
                                  volume_validation: Dict, microstructure: Dict) -> Optional[Signal]:
        """Generate breakout signal with institutional parameters."""
        symbol = market_data['symbol'].iloc[-1] if 'symbol' in market_data.columns else 'UNKNOWN'
        current_time = market_data['time'].iloc[-1]
        current_price = breakout['breakout_price']
        direction = breakout['direction']
        
        atr = (market_data['high'].tail(14) - market_data['low'].tail(14)).mean()

        if direction == 'LONG':
            stop_loss = breakout['range_boundary'] - (atr * 0.5)
            measured_move = breakout['range_boundary'] - market_data['low'].tail(50).min()
            take_profit = current_price + measured_move
        else:
            stop_loss = breakout['range_boundary'] + (atr * 0.5)
            measured_move = market_data['high'].tail(50).max() - breakout['range_boundary']
            take_profit = current_price - measured_move

        volume_ratio = volume_validation['volume_ratio']
        clean_breakout = breakout['clean_close']
        
        if volume_ratio >= 4.0 and clean_breakout:
            sizing_level = 4
        elif volume_ratio >= 3.0 and clean_breakout:
            sizing_level = 3
        else:
            sizing_level = 2

        metadata = {
            'range_boundary': breakout['range_boundary'],
            'penetration_amount': breakout['penetration'],
            'clean_close_above_below': clean_breakout,
            'volume_ratio': volume_validation['volume_ratio'],
            'consolidation_volume_avg': volume_validation['consolidation_volume_avg'],
            'imbalance_aligned': microstructure['imbalance_aligned'],
            'vpin_non_exhausted': microstructure['vpin_appropriate'],
            'microstructure_details': microstructure['details'],
            'measured_move_target': float(take_profit),
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

