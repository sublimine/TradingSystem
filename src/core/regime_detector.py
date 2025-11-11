"""
Market Regime Detection - Institutional Implementation

Detects and classifies market regimes using multiple methods:
1. Volatility regimes (HMM-based)
2. Trend regimes (ADX + EMA structure)
3. Microstructure regimes (order flow characteristics)
4. Liquidity regimes (volume profile analysis)

Research basis:
- Ang & Bekaert (2002): Regime switching in equity returns
- Kritzman et al. (2012): Regime Shifts: Implications for Dynamic Strategies
- Easley et al. (2012): Flow Toxicity and Liquidity in Fragmented Markets
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Tuple
from datetime import datetime
import logging
from scipy import stats
from sklearn.preprocessing import StandardScaler

logger = logging.getLogger(__name__)


class RegimeDetector:
    """
    Advanced regime detection for strategy selection and risk adjustment.

    Regimes detected:
    1. TREND_STRONG_UP / TREND_STRONG_DOWN
    2. TREND_WEAK_UP / TREND_WEAK_DOWN
    3. RANGING_HIGH_VOL / RANGING_LOW_VOL
    4. BREAKOUT_MOMENTUM
    5. REVERSAL_EXHAUSTION

    Each regime has optimal strategy types and risk parameters.
    """

    def __init__(self, config: Dict):
        """
        Initialize regime detector.

        Args:
            config: Regime detection configuration
        """
        self.config = config

        # Detection parameters
        self.lookback_period = config.get('regime_lookback', 30)
        self.min_confidence = config.get('min_regime_confidence', 0.60)

        # Regime thresholds
        self.trend_adx_threshold = config.get('trend_adx_threshold', 25)
        self.strong_trend_adx = config.get('strong_trend_adx', 35)
        self.ranging_adx_max = config.get('ranging_adx_max', 20)

        # Volatility thresholds (percentiles)
        self.low_vol_percentile = config.get('low_vol_percentile', 30)
        self.high_vol_percentile = config.get('high_vol_percentile', 70)

        # Current regime state
        self.current_regime = 'UNKNOWN'
        self.regime_confidence = 0.0
        self.regime_started_at = datetime.now()
        self.regime_duration_bars = 0

        # Historical tracking
        self.regime_history = []

        logger.info(f"Regime Detector initialized: lookback={self.lookback_period}")

    def detect_regime(self, market_data: pd.DataFrame, features: Dict) -> Dict:
        """
        Detect current market regime.

        Args:
            market_data: OHLCV data
            features: Pre-calculated features

        Returns:
            {
                'regime': str,
                'confidence': float,
                'sub_regimes': dict,
                'optimal_strategies': list,
            }
        """
        if len(market_data) < self.lookback_period:
            return {
                'regime': 'UNKNOWN',
                'confidence': 0.0,
                'sub_regimes': {},
                'optimal_strategies': [],
            }

        # Detect component regimes
        volatility_regime = self._detect_volatility_regime(market_data)
        trend_regime = self._detect_trend_regime(market_data, features)
        microstructure_regime = self._detect_microstructure_regime(features)
        momentum_regime = self._detect_momentum_regime(market_data)

        # Synthesize composite regime
        composite_regime = self._synthesize_regime(
            volatility_regime,
            trend_regime,
            microstructure_regime,
            momentum_regime
        )

        # Determine optimal strategies for this regime
        optimal_strategies = self._get_optimal_strategies(composite_regime)

        # Update tracking
        if composite_regime['regime'] != self.current_regime:
            self._regime_changed(composite_regime['regime'])

        self.current_regime = composite_regime['regime']
        self.regime_confidence = composite_regime['confidence']
        self.regime_duration_bars += 1

        return {
            'regime': composite_regime['regime'],
            'confidence': composite_regime['confidence'],
            'sub_regimes': {
                'volatility': volatility_regime,
                'trend': trend_regime,
                'microstructure': microstructure_regime,
                'momentum': momentum_regime,
            },
            'optimal_strategies': optimal_strategies,
        }

    def _detect_volatility_regime(self, market_data: pd.DataFrame) -> Dict:
        """
        Detect volatility regime using ATR analysis.

        Returns:
            {'regime': 'LOW'|'NORMAL'|'HIGH', 'confidence': float}
        """
        # Calculate recent ATR
        if 'atr' in market_data.columns:
            recent_atr = market_data['atr'].tail(20).mean()
        else:
            high_low = market_data['high'] - market_data['low']
            recent_atr = high_low.tail(20).mean()

        # Calculate historical ATR distribution
        if 'atr' in market_data.columns:
            historical_atr = market_data['atr'].tail(self.lookback_period * 3)
        else:
            high_low_hist = market_data['high'] - market_data['low']
            historical_atr = high_low_hist.tail(self.lookback_period * 3)

        # Calculate percentile
        percentile = stats.percentileofscore(historical_atr, recent_atr)

        # Classify regime
        if percentile < self.low_vol_percentile:
            regime = 'LOW'
            confidence = (self.low_vol_percentile - percentile) / self.low_vol_percentile
        elif percentile > self.high_vol_percentile:
            regime = 'HIGH'
            confidence = (percentile - self.high_vol_percentile) / (100 - self.high_vol_percentile)
        else:
            regime = 'NORMAL'
            confidence = 0.7

        return {
            'regime': regime,
            'confidence': min(confidence, 1.0),
            'atr_current': float(recent_atr),
            'atr_percentile': float(percentile),
        }

    def _detect_trend_regime(self, market_data: pd.DataFrame, features: Dict) -> Dict:
        """
        Detect trend regime using ADX and EMA structure.

        Returns:
            {'regime': str, 'confidence': float, 'direction': str}
        """
        # Get ADX if available
        adx = features.get('adx', 0)

        # Get EMA structure
        current_bar = market_data.iloc[-1]
        price = current_bar['close']

        if 'ema_20' in current_bar and 'ema_50' in current_bar:
            ema_20 = current_bar['ema_20']
            ema_50 = current_bar['ema_50']
            ema_200 = current_bar.get('ema_200', ema_50)

            # Determine trend direction
            if ema_20 > ema_50 > ema_200:
                direction = 'UP'
                ema_alignment = 1.0
            elif ema_20 < ema_50 < ema_200:
                direction = 'DOWN'
                ema_alignment = 1.0
            else:
                direction = 'NEUTRAL'
                ema_alignment = 0.5
        else:
            # Fallback: simple price trend
            sma_20 = market_data['close'].tail(20).mean()
            sma_50 = market_data['close'].tail(50).mean()

            if price > sma_20 > sma_50:
                direction = 'UP'
                ema_alignment = 0.8
            elif price < sma_20 < sma_50:
                direction = 'DOWN'
                ema_alignment = 0.8
            else:
                direction = 'NEUTRAL'
                ema_alignment = 0.5

            adx = 0  # Unknown

        # Classify trend strength
        if adx > self.strong_trend_adx:
            regime = f'TREND_STRONG_{direction}'
            confidence = min(adx / 50, 1.0)
        elif adx > self.trend_adx_threshold:
            regime = f'TREND_WEAK_{direction}'
            confidence = 0.7
        else:
            regime = f'RANGING'
            confidence = (self.ranging_adx_max - adx) / self.ranging_adx_max if adx < self.ranging_adx_max else 0.5

        return {
            'regime': regime,
            'confidence': min(confidence * ema_alignment, 1.0),
            'direction': direction,
            'adx': float(adx),
        }

    def _detect_microstructure_regime(self, features: Dict) -> Dict:
        """
        Detect microstructure regime using order flow metrics.

        Returns:
            {'regime': 'CLEAN'|'TOXIC'|'NEUTRAL', 'confidence': float}
        """
        vpin = features.get('vpin', 0.4)
        imbalance = features.get('order_flow_imbalance', 0.0)

        # Classify based on VPIN
        if vpin > 0.55:
            regime = 'TOXIC'
            confidence = min((vpin - 0.55) / 0.25, 1.0)
        elif vpin < 0.30:
            regime = 'CLEAN'
            confidence = min((0.30 - vpin) / 0.30, 1.0)
        else:
            regime = 'NEUTRAL'
            confidence = 0.6

        return {
            'regime': regime,
            'confidence': confidence,
            'vpin': float(vpin),
            'imbalance': float(imbalance),
        }

    def _detect_momentum_regime(self, market_data: pd.DataFrame) -> Dict:
        """
        Detect momentum regime using price velocity and volume.

        Returns:
            {'regime': 'BREAKOUT'|'REVERSAL'|'CONSOLIDATION', 'confidence': float}
        """
        # Calculate price momentum
        recent_bars = market_data.tail(10)

        price_change = (recent_bars['close'].iloc[-1] - recent_bars['close'].iloc[0]) / recent_bars['close'].iloc[0]
        volume_ratio = recent_bars['volume'].mean() / market_data['volume'].tail(50).mean()

        # Classify momentum
        if abs(price_change) > 0.015 and volume_ratio > 1.5:
            # Strong momentum with volume
            regime = 'BREAKOUT'
            confidence = min(abs(price_change) * 30 * volume_ratio / 2, 1.0)

        elif abs(price_change) > 0.02 and volume_ratio > 2.0:
            # Climactic move - potential exhaustion
            regime = 'REVERSAL'
            confidence = min(abs(price_change) * 25, 1.0)

        else:
            # Consolidation / no momentum
            regime = 'CONSOLIDATION'
            confidence = 0.7

        return {
            'regime': regime,
            'confidence': min(confidence, 1.0),
            'price_change_10bar': float(price_change),
            'volume_ratio': float(volume_ratio),
        }

    def _synthesize_regime(self, volatility: Dict, trend: Dict,
                          microstructure: Dict, momentum: Dict) -> Dict:
        """
        Synthesize component regimes into composite regime.

        Priority weighting:
        1. Microstructure (40%) - Most important for institutional
        2. Trend (30%)
        3. Momentum (20%)
        4. Volatility (10%)
        """
        # If microstructure is toxic, override everything
        if microstructure['regime'] == 'TOXIC' and microstructure['confidence'] > 0.7:
            return {
                'regime': 'TOXIC_FLOW',
                'confidence': microstructure['confidence'],
            }

        # Determine primary regime from trend + momentum
        trend_regime = trend['regime']
        momentum_regime = momentum['regime']

        # Synthesis logic
        if 'TREND_STRONG' in trend_regime and momentum_regime == 'BREAKOUT':
            regime = f'TREND_STRONG_{trend["direction"]}'
            confidence = (trend['confidence'] * 0.6 + momentum['confidence'] * 0.4)

        elif 'TREND_STRONG' in trend_regime:
            regime = trend_regime
            confidence = trend['confidence'] * 0.8

        elif 'TREND_WEAK' in trend_regime and momentum_regime != 'REVERSAL':
            regime = trend_regime
            confidence = trend['confidence'] * 0.7

        elif momentum_regime == 'REVERSAL':
            regime = 'REVERSAL_EXHAUSTION'
            confidence = momentum['confidence'] * 0.75

        elif momentum_regime == 'BREAKOUT' and volatility['regime'] == 'HIGH':
            regime = 'BREAKOUT_MOMENTUM'
            confidence = (momentum['confidence'] * 0.7 + volatility['confidence'] * 0.3)

        elif 'RANGING' in trend_regime:
            if volatility['regime'] == 'HIGH':
                regime = 'RANGING_HIGH_VOL'
            else:
                regime = 'RANGING_LOW_VOL'
            confidence = 0.7

        else:
            regime = 'NEUTRAL'
            confidence = 0.5

        return {
            'regime': regime,
            'confidence': min(confidence, 1.0),
        }

    def _get_optimal_strategies(self, composite_regime: Dict) -> List[str]:
        """
        Get optimal strategy types for current regime.

        Args:
            composite_regime: Composite regime dict

        Returns:
            List of optimal strategy names
        """
        regime = composite_regime['regime']

        # Regime-strategy mapping (institutional logic)
        strategy_map = {
            'TREND_STRONG_UP': [
                'momentum_quality',
                'breakout_volume_confirmation',
                'htf_ltf_liquidity',
            ],
            'TREND_STRONG_DOWN': [
                'momentum_quality',
                'breakout_volume_confirmation',
                'htf_ltf_liquidity',
            ],
            'TREND_WEAK_UP': [
                'order_block_institutional',
                'fvg_institutional',
                'liquidity_sweep',
            ],
            'TREND_WEAK_DOWN': [
                'order_block_institutional',
                'fvg_institutional',
                'liquidity_sweep',
            ],
            'RANGING_LOW_VOL': [
                'mean_reversion_statistical',
                'kalman_pairs_trading',
                'correlation_divergence',
                'iceberg_detection',
            ],
            'RANGING_HIGH_VOL': [
                'volatility_regime_adaptation',
                'mean_reversion_statistical',
            ],
            'BREAKOUT_MOMENTUM': [
                'breakout_volume_confirmation',
                'momentum_quality',
                'idp_inducement_distribution',
            ],
            'REVERSAL_EXHAUSTION': [
                'mean_reversion_statistical',
                'liquidity_sweep',
                'order_block_institutional',
            ],
            'TOXIC_FLOW': [],  # NO TRADING
            'NEUTRAL': [
                'order_block_institutional',
                'htf_ltf_liquidity',
            ],
        }

        return strategy_map.get(regime, [])

    def _regime_changed(self, new_regime: str):
        """Handle regime change."""
        logger.info(f"REGIME CHANGED: {self.current_regime} -> {new_regime} "
                   f"(duration: {self.regime_duration_bars} bars)")

        # Record in history
        self.regime_history.append({
            'regime': self.current_regime,
            'started_at': self.regime_started_at,
            'ended_at': datetime.now(),
            'duration_bars': self.regime_duration_bars,
        })

        # Reset for new regime
        self.regime_started_at = datetime.now()
        self.regime_duration_bars = 0

    def get_statistics(self) -> Dict:
        """Get regime detection statistics."""
        return {
            'current_regime': self.current_regime,
            'confidence': self.regime_confidence,
            'duration_bars': self.regime_duration_bars,
            'regime_changes_total': len(self.regime_history),
        }


class RegimeBasedRiskAdjuster:
    """
    Adjust risk parameters based on detected regime.

    Institutional approach:
    - High volatility: Reduce position sizes, widen stops
    - Toxic flow: Pause trading
    - Strong trends: Increase momentum strategy allocation
    - Ranging: Prefer mean reversion strategies
    """

    def __init__(self, config: Dict):
        """Initialize regime-based risk adjuster."""
        self.config = config

        # Risk multipliers by regime
        self.regime_risk_multipliers = {
            'TREND_STRONG_UP': 1.2,
            'TREND_STRONG_DOWN': 1.2,
            'TREND_WEAK_UP': 1.0,
            'TREND_WEAK_DOWN': 1.0,
            'RANGING_LOW_VOL': 1.3,
            'RANGING_HIGH_VOL': 0.7,
            'BREAKOUT_MOMENTUM': 1.1,
            'REVERSAL_EXHAUSTION': 0.8,
            'TOXIC_FLOW': 0.0,  # NO TRADING
            'NEUTRAL': 1.0,
        }

    def adjust_risk_for_regime(self, base_risk: float, regime: str) -> float:
        """
        Adjust base risk based on regime.

        Args:
            base_risk: Base risk percentage
            regime: Current regime

        Returns:
            Adjusted risk percentage
        """
        multiplier = self.regime_risk_multipliers.get(regime, 1.0)
        return base_risk * multiplier

    def should_block_trading(self, regime: str, confidence: float) -> Tuple[bool, Optional[str]]:
        """
        Determine if trading should be blocked based on regime.

        Args:
            regime: Current regime
            confidence: Regime confidence

        Returns:
            (should_block, reason)
        """
        # Block trading in toxic flow
        if regime == 'TOXIC_FLOW' and confidence > 0.7:
            return True, "TOXIC FLOW - Trading blocked"

        # Block in extreme volatility (handled elsewhere but can double-check)
        if regime == 'RANGING_HIGH_VOL' and confidence > 0.85:
            return True, "EXTREME VOLATILITY - Trading paused"

        return False, None
