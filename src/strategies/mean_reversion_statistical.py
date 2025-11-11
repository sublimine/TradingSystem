"""
Mean Reversion Statistical Strategy - Institutional Implementation

Implements institutional mean reversion based on statistical price extremes
with microstructure and order flow validation. Uses order book imbalance,
liquidity absorption patterns, and toxic flow detection for confirmation.
"""

import numpy as np
import pandas as pd
from typing import List, Dict, Optional
import logging
from datetime import datetime
from .strategy_base import StrategyBase, Signal


class MeanReversionStatistical(StrategyBase):
    """
    Institutional mean reversion strategy using statistical extremes.
    
    Identifies price deviations beyond statistical thresholds, validates through
    order flow toxicity indicating exhaustion, confirms via order book imbalance
    showing absorption, and enters anticipating reversion to equilibrium.
    """

    def __init__(self, config: Dict):
        """
        Initialize mean reversion statistical strategy.

        Required config parameters:
            - lookback_period: Period for statistical calculation (typically 200)
            - entry_sigma_threshold: Std deviations for entry (typically 3.0)
            - exit_sigma_threshold: Std deviations for exit (typically 0.8)
            - vpin_exhaustion_threshold: VPIN indicating exhaustion (typically 0.70)
            - imbalance_reversal_threshold: Order book imbalance for reversal (typically 0.40)
            - volume_spike_multiplier: Volume spike indicating climax (typically 2.5)
            - min_liquidity_score: Minimum liquidity for execution (typically 0.60)
            - reversal_velocity_min: Minimum velocity of snap-back (typically 8 pips/min)
        """
        super().__init__(config)

        self.lookback_period = config.get('lookback_period', 200)
        self.entry_sigma_threshold = config.get('entry_sigma_threshold', 2.8)
        self.exit_sigma_threshold = config.get('exit_sigma_threshold', 0.8)
        self.vpin_exhaustion_threshold = config.get('vpin_exhaustion_threshold', 0.40)
        self.imbalance_reversal_threshold = config.get('imbalance_reversal_threshold', 0.30)
        self.volume_spike_multiplier = config.get('volume_spike_multiplier', 3.2)
        self.min_liquidity_score = config.get('min_liquidity_score', 0.60)
        self.reversal_velocity_min = config.get('reversal_velocity_min', 18.0)
        self.adx_max_for_entry = config.get('adx_max_for_entry', 22)
        self.use_vwap_mean = config.get('use_vwap_mean', True)
        self.confirmations_required_pct = config.get('confirmations_required_pct', 0.80)
        self.logger = logging.getLogger(self.__class__.__name__)

    def evaluate(self, market_data: pd.DataFrame, features: Dict) -> List[Signal]:
        """
        Evaluate market for institutional mean reversion setups.

        Args:
            market_data: Recent OHLCV data
            features: Pre-calculated features including microstructure metrics

        Returns:
            List of signals for statistically validated mean reversion opportunities
        """
        if not self.validate_inputs(market_data, features):
            return []

        if len(market_data) < self.lookback_period:
            return []

        signals = []

        statistical_extreme = self._detect_statistical_extreme(market_data)
        
        if statistical_extreme is None:
            return []

        if abs(statistical_extreme['z_score']) >= self.entry_sigma_threshold:
            microstructure_validation = self._validate_microstructure_conditions(market_data, features, statistical_extreme)
            
            if microstructure_validation['is_valid']:
                signal = self._generate_institutional_reversion_signal(
                    market_data, statistical_extreme, microstructure_validation
                )
                if signal:
                    signals.append(signal)

        return signals

    def _detect_statistical_extreme(self, market_data: pd.DataFrame) -> Optional[Dict]:
        """Detect price deviation beyond statistical threshold."""
        closes = market_data['close'].values
        
        if len(closes) < self.lookback_period:
            return None

        equilibrium_mean = np.mean(closes[-self.lookback_period:])
        equilibrium_std = np.std(closes[-self.lookback_period:], ddof=1)
        
        if equilibrium_std < 1e-10:
            return None

        current_price = closes[-1]
        deviation = current_price - equilibrium_mean
        z_score = deviation / equilibrium_std

        if abs(z_score) < self.entry_sigma_threshold:
            return None

        volumes = market_data['volume'].tail(self.lookback_period).values
        volume_avg = np.mean(volumes[:-20])
        recent_volume_avg = np.mean(volumes[-20:])
        volume_spike_ratio = recent_volume_avg / volume_avg if volume_avg > 0 else 1.0

        extreme_analysis = {
            'current_price': float(current_price),
            'equilibrium_mean': float(equilibrium_mean),
            'equilibrium_std': float(equilibrium_std),
            'z_score': float(z_score),
            'direction': 'LONG' if z_score < 0 else 'SHORT',
            'volume_spike_ratio': float(volume_spike_ratio),
            'is_volume_climax': volume_spike_ratio >= self.volume_spike_multiplier
        }

        return extreme_analysis

    def _validate_microstructure_conditions(self, market_data: pd.DataFrame, features: Dict,
                                           extreme: Dict) -> Dict:
        """Validate mean reversion setup through microstructure analysis."""
        validation = {
            'is_valid': False,
            'vpin_exhaustion': False,
            'imbalance_reversal': False,
            'liquidity_adequate': False,
            'reversal_initiated': False,
            'confidence_score': 0.0,
            'details': {}
        }

        direction = extreme['direction']

        if 'vpin' in features:
            vpin = features['vpin']
            if vpin >= self.vpin_exhaustion_threshold:
                validation['vpin_exhaustion'] = True
                validation['details']['vpin'] = float(vpin)

        if 'order_flow_imbalance' in features:
            imbalance = features['order_flow_imbalance']
            
            if direction == 'LONG' and imbalance < -self.imbalance_reversal_threshold:
                recent_price_action = self._analyze_recent_price_action(market_data)
                if recent_price_action['showing_absorption']:
                    validation['imbalance_reversal'] = True
                    validation['details']['imbalance'] = float(imbalance)
            
            elif direction == 'SHORT' and imbalance > self.imbalance_reversal_threshold:
                recent_price_action = self._analyze_recent_price_action(market_data)
                if recent_price_action['showing_absorption']:
                    validation['imbalance_reversal'] = True
                    validation['details']['imbalance'] = float(imbalance)

        if 'liquidity_score' in features:
            liquidity = features['liquidity_score']
            if liquidity >= self.min_liquidity_score:
                validation['liquidity_adequate'] = True
                validation['details']['liquidity_score'] = float(liquidity)
        else:
            validation['liquidity_adequate'] = True

        reversal_velocity = self._calculate_reversal_velocity(market_data, direction)
        if reversal_velocity >= self.reversal_velocity_min:
            validation['reversal_initiated'] = True
            validation['details']['reversal_velocity'] = float(reversal_velocity)

        factors_met = sum([
            validation['vpin_exhaustion'],
            validation['imbalance_reversal'],
            validation['liquidity_adequate'],
            validation['reversal_initiated'],
            extreme['is_volume_climax']
        ])

        validation['confidence_score'] = factors_met / 5.0
        validation['is_valid'] = factors_met >= 2

        return validation

    def _analyze_recent_price_action(self, market_data: pd.DataFrame) -> Dict:
        """Analyze recent price action for absorption patterns."""
        recent_bars = market_data.tail(10)
        
        if len(recent_bars) < 5:
            return {'showing_absorption': False}

        closes = recent_bars['close'].values
        highs = recent_bars['high'].values
        lows = recent_bars['low'].values
        volumes = recent_bars['volume'].values

        price_range_recent = np.max(highs[-3:]) - np.min(lows[-3:])
        volume_recent = np.mean(volumes[-3:])
        volume_previous = np.mean(volumes[-10:-3])

        high_volume_small_range = (volume_recent > volume_previous * 1.3) and (price_range_recent < np.mean(highs - lows))

        return {
            'showing_absorption': high_volume_small_range,
            'price_range_compression': float(price_range_recent)
        }

    def _calculate_reversal_velocity(self, market_data: pd.DataFrame, direction: str) -> float:
        """Calculate velocity of price reversal from extreme."""
        recent_bars = market_data.tail(5)
        
        if len(recent_bars) < 3:
            return 0.0

        closes = recent_bars['close'].values
        
        if direction == 'LONG':
            lowest_price = np.min(closes)
            current_price = closes[-1]
            price_recovery = current_price - lowest_price
        else:
            highest_price = np.max(closes)
            current_price = closes[-1]
            price_recovery = highest_price - current_price

        bars_elapsed = len(closes)
        velocity = (price_recovery * 10000) / bars_elapsed if bars_elapsed > 0 else 0.0

        return float(velocity)

    def _generate_institutional_reversion_signal(self, market_data: pd.DataFrame,
                                                 extreme: Dict, validation: Dict) -> Optional[Signal]:
        """Generate mean reversion signal with institutional parameters."""
        symbol = market_data['symbol'].iloc[-1] if 'symbol' in market_data.columns else 'UNKNOWN'
        current_time = market_data['time'].iloc[-1]
        current_price = extreme['current_price']
        direction = extreme['direction']
        
        atr = (market_data['high'].tail(14) - market_data['low'].tail(14)).mean()
        equilibrium = extreme['equilibrium_mean']

        if direction == 'LONG':
            stop_loss = current_price - (atr * 2.5)
            take_profit_primary = equilibrium - (atr * 0.3)
            take_profit_extended = equilibrium + (atr * 0.5)
        else:
            stop_loss = current_price + (atr * 2.5)
            take_profit_primary = equilibrium + (atr * 0.3)
            take_profit_extended = equilibrium - (atr * 0.5)

        z_score_magnitude = abs(extreme['z_score'])
        confidence = validation['confidence_score']
        
        if z_score_magnitude >= 4.0 and confidence >= 0.80:
            sizing_level = 5
        elif z_score_magnitude >= 3.5 and confidence >= 0.70:
            sizing_level = 4
        elif z_score_magnitude >= 2.0 and confidence >= 0.60:
            sizing_level = 3
        else:
            sizing_level = 2

        metadata = {
            'z_score': extreme['z_score'],
            'equilibrium_mean': extreme['equilibrium_mean'],
            'equilibrium_std': extreme['equilibrium_std'],
            'statistical_extreme_sigma': float(z_score_magnitude),
            'volume_spike_ratio': extreme['volume_spike_ratio'],
            'volume_climax_detected': extreme['is_volume_climax'],
            'vpin_exhaustion': validation['vpin_exhaustion'],
            'imbalance_reversal_confirmed': validation['imbalance_reversal'],
            'liquidity_adequate': validation['liquidity_adequate'],
            'reversal_velocity_detected': validation['reversal_initiated'],
            'microstructure_confidence': validation['confidence_score'],
            'validation_details': validation['details'],
            'take_profit_primary': float(take_profit_primary),
            'take_profit_extended': float(take_profit_extended),
            'strategy_version': '1.0'
        }

        signal = Signal(
            timestamp=current_time,
            symbol=symbol,
            strategy_name=self.name,
            direction=direction,
            entry_price=float(current_price),
            stop_loss=float(stop_loss),
            take_profit=float(take_profit_primary),
            sizing_level=sizing_level,
            metadata=metadata
        )

        return signal


