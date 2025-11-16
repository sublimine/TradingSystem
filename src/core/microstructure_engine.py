"""
Microstructure Engine - INSTITUTIONAL GRADE

Centralizes institutional microstructure features:
- OFI (Order Flow Imbalance)
- VPIN (Volume-Synchronized Probability of Informed Trading)
- CVD (Cumulative Volume Delta)
- Spread analytics
- Volume profile

Provides unified interface for all strategies to access institutional features.

PLAN OMEGA - FASE 3.1: MicrostructureEngine MVP
Author: Elite Institutional Trading System
Version: 1.0
"""

import pandas as pd
import numpy as np
from typing import Dict, Optional, Tuple
from collections import deque
import logging

from src.features.ofi import calculate_ofi, classify_trades_lee_ready
from src.features.order_flow import (
    VPINCalculator,
    calculate_signed_volume,
    calculate_cumulative_volume_delta,
    OFICalculator
)
from src.features.microstructure import (
    calculate_microprice,
    calculate_mid_price,
    calculate_spread,
    calculate_order_book_imbalance
)
from src.features.technical_indicators import calculate_atr

logger = logging.getLogger(__name__)


class MicrostructureEngine:
    """
    INSTITUTIONAL Microstructure Engine.

    Centralizes calculation of institutional features with caching and
    consistent interfaces. All 24 strategies access microstructure through
    this engine for consistency.

    Features Provided:
    - OFI: Order Flow Imbalance (institutional flow direction)
    - VPIN: Flow toxicity (informed vs uninformed trading)
    - CVD: Cumulative Volume Delta (directional pressure)
    - Spread: Bid-ask dynamics
    - Order Book Imbalance: Estimated from price action
    - ATR: Average True Range (TYPE B - descriptive metric only)

    Usage:
        engine = MicrostructureEngine()
        features = engine.calculate_features(market_data)

        # Access features:
        ofi = features['ofi']
        vpin = features['vpin']
        cvd = features['cvd']
    """

    def __init__(self, config: Optional[Dict] = None):
        """
        Initialize Microstructure Engine.

        Args:
            config: Optional configuration dictionary
        """
        config = config or {}

        # OFI parameters
        self.ofi_window = config.get('ofi_window', 20)

        # VPIN parameters
        self.vpin_bucket_size = config.get('vpin_bucket_size', 50000)
        self.vpin_num_buckets = config.get('vpin_num_buckets', 50)
        self.vpin_calculator = VPINCalculator(
            bucket_size=self.vpin_bucket_size,
            num_buckets=self.vpin_num_buckets
        )

        # CVD parameters
        self.cvd_window = config.get('cvd_window', 20)

        # Feature cache (updated per bar)
        self.feature_cache: Dict[str, float] = {}
        self.last_cache_timestamp: Optional[pd.Timestamp] = None

        logger.info(f"MicrostructureEngine initialized - OFI:{self.ofi_window}, "
                   f"VPIN:{self.vpin_num_buckets}x{self.vpin_bucket_size}, CVD:{self.cvd_window}")

    def calculate_features(self, market_data: pd.DataFrame,
                          use_cache: bool = True) -> Dict[str, float]:
        """
        Calculate all microstructure features for current market data.

        Args:
            market_data: DataFrame with OHLCV data
                Required columns: 'timestamp', 'open', 'high', 'low', 'close', 'volume'
            use_cache: If True, return cached features if timestamp unchanged

        Returns:
            Dictionary with microstructure features:
                - 'ofi': Order Flow Imbalance (-1 to 1)
                - 'vpin': Flow toxicity (0 to 1)
                - 'cvd': Cumulative Volume Delta (normalized)
                - 'spread_pct': Spread as % of mid price
                - 'ob_imbalance': Order book imbalance (-1 to 1)
                - 'atr': Average True Range (TYPE B - descriptive metric)

        Example:
            >>> features = engine.calculate_features(data)
            >>> if features['ofi'] > 0 and features['vpin'] < 0.3:
            >>>     # Institutional buying, clean flow
            >>>     pass
        """
        if len(market_data) < max(self.ofi_window, self.cvd_window):
            logger.warning(f"Insufficient data: {len(market_data)} bars, need {max(self.ofi_window, self.cvd_window)}")
            return self._empty_features()

        current_timestamp = market_data.iloc[-1].get('timestamp')

        # Check cache
        if use_cache and current_timestamp == self.last_cache_timestamp:
            logger.debug("Returning cached features")
            return self.feature_cache.copy()

        # Calculate features
        features = {}

        # 1. OFI (Order Flow Imbalance)
        try:
            ofi_series = calculate_ofi(market_data, window_size=self.ofi_window)
            features['ofi'] = float(ofi_series.iloc[-1]) if len(ofi_series) > 0 else 0.0
        except Exception as e:
            logger.error(f"OFI calculation failed: {e}")
            features['ofi'] = 0.0

        # 2. VPIN (Flow Toxicity)
        try:
            vpin = self._calculate_vpin_from_bars(market_data)
            features['vpin'] = float(vpin)
        except Exception as e:
            logger.error(f"VPIN calculation failed: {e}")
            features['vpin'] = 0.0

        # 3. CVD (Cumulative Volume Delta)
        try:
            cvd_value = self._calculate_cvd(market_data)
            features['cvd'] = float(cvd_value)
        except Exception as e:
            logger.error(f"CVD calculation failed: {e}")
            features['cvd'] = 0.0

        # 4. Spread (pct of mid)
        try:
            spread_pct = self._calculate_spread_pct(market_data)
            features['spread_pct'] = float(spread_pct)
        except Exception as e:
            logger.error(f"Spread calculation failed: {e}")
            features['spread_pct'] = 0.0

        # 5. Order Book Imbalance (estimated from price action)
        try:
            ob_imbalance = self._estimate_ob_imbalance(market_data)
            features['ob_imbalance'] = float(ob_imbalance)
        except Exception as e:
            logger.error(f"OB imbalance calculation failed: {e}")
            features['ob_imbalance'] = 0.0

        # 6. ATR (TYPE B - descriptive metric for pattern detection only)
        try:
            atr_series = calculate_atr(
                market_data['high'],
                market_data['low'],
                market_data['close'],
                period=14
            )
            features['atr'] = float(atr_series.iloc[-1]) if len(atr_series) > 0 else 0.0001
        except Exception as e:
            logger.error(f"ATR calculation failed: {e}")
            features['atr'] = 0.0001  # Small default for TYPE B usage

        # Cache features
        self.feature_cache = features
        self.last_cache_timestamp = current_timestamp

        logger.debug(f"Features calculated: OFI={features['ofi']:.3f}, "
                    f"VPIN={features['vpin']:.3f}, CVD={features['cvd']:.3f}")

        return features

    def _calculate_vpin_from_bars(self, market_data: pd.DataFrame) -> float:
        """
        Calculate VPIN from OHLCV bars.

        Uses tick rule to classify trades and accumulate into volume buckets.
        """
        if len(market_data) < 2:
            return 0.0

        # Use Lee-Ready classification
        classified_data = classify_trades_lee_ready(market_data.tail(100))

        # Feed to VPIN calculator
        for _, row in classified_data.iterrows():
            if row.get('buy_volume', 0) > row.get('sell_volume', 0):
                trade_direction = 1
            elif row.get('sell_volume', 0) > row.get('buy_volume', 0):
                trade_direction = -1
            else:
                trade_direction = 0

            vpin = self.vpin_calculator.add_trade(
                volume=row.get('volume', 0),
                trade_direction=trade_direction
            )

        # Get current VPIN
        return self.vpin_calculator.get_current_vpin()

    def _calculate_cvd(self, market_data: pd.DataFrame) -> float:
        """
        Calculate Cumulative Volume Delta (normalized).

        Returns CVD normalized to [-1, 1] range.
        """
        if len(market_data) < self.cvd_window:
            return 0.0

        # Calculate signed volume
        signed_vol = calculate_signed_volume(
            market_data['close'],
            market_data['volume']
        )

        # Calculate CVD over window
        cvd = calculate_cumulative_volume_delta(signed_vol, window=self.cvd_window)

        if len(cvd) == 0:
            return 0.0

        # Normalize by total volume in window
        recent_data = market_data.tail(self.cvd_window)
        total_volume = recent_data['volume'].sum()

        if total_volume == 0:
            return 0.0

        cvd_normalized = cvd.iloc[-1] / total_volume
        # Clip to [-1, 1]
        cvd_normalized = max(-1.0, min(1.0, cvd_normalized))

        return cvd_normalized

    def _calculate_spread_pct(self, market_data: pd.DataFrame) -> float:
        """
        Estimate spread as % of mid price from recent volatility.

        Without true bid/ask, estimate from high-low range.
        """
        if len(market_data) < 5:
            return 0.0

        recent = market_data.tail(5)
        avg_range = (recent['high'] - recent['low']).mean()
        mid_price = recent['close'].mean()

        if mid_price == 0:
            return 0.0

        spread_pct = (avg_range / mid_price) * 100
        return spread_pct

    def _estimate_ob_imbalance(self, market_data: pd.DataFrame) -> float:
        """
        Estimate order book imbalance from price action.

        Positive: More buying pressure (bid side stronger)
        Negative: More selling pressure (ask side stronger)
        """
        if len(market_data) < 3:
            return 0.0

        recent = market_data.tail(3)

        # Analyze close vs range position
        # Close near high = buying pressure (positive imbalance)
        # Close near low = selling pressure (negative imbalance)
        range_position = []
        for _, row in recent.iterrows():
            range_size = row['high'] - row['low']
            if range_size == 0:
                range_position.append(0)
            else:
                # Where close is in range: 1 = at high, -1 = at low
                position = ((row['close'] - row['low']) / range_size) * 2 - 1
                range_position.append(position)

        # Average position over recent bars
        avg_position = np.mean(range_position)
        return avg_position

    def _empty_features(self) -> Dict[str, float]:
        """Return empty features dict with safe default values."""
        return {
            'ofi': 0.0,
            'vpin': 0.0,
            'cvd': 0.0,
            'spread_pct': 0.0,
            'ob_imbalance': 0.0,
            'atr': 0.0001  # TYPE B - small default for pattern detection
        }

    def get_feature_summary(self, features: Dict[str, float]) -> str:
        """
        Get human-readable summary of features.

        Args:
            features: Features dict from calculate_features()

        Returns:
            Summary string
        """
        ofi = features.get('ofi', 0)
        vpin = features.get('vpin', 0)
        cvd = features.get('cvd', 0)

        # Interpret OFI
        if ofi > 0.5:
            ofi_str = "Strong BUY flow"
        elif ofi > 0:
            ofi_str = "Moderate BUY flow"
        elif ofi > -0.5:
            ofi_str = "Moderate SELL flow"
        else:
            ofi_str = "Strong SELL flow"

        # Interpret VPIN
        if vpin > 0.5:
            vpin_str = "TOXIC (uninformed)"
        elif vpin > 0.3:
            vpin_str = "Elevated toxicity"
        else:
            vpin_str = "CLEAN (informed)"

        # Interpret CVD
        if cvd > 0.3:
            cvd_str = "Cumulative BUYING"
        elif cvd < -0.3:
            cvd_str = "Cumulative SELLING"
        else:
            cvd_str = "Balanced"

        return (f"OFI: {ofi_str} ({ofi:+.2f}) | "
                f"VPIN: {vpin_str} ({vpin:.2f}) | "
                f"CVD: {cvd_str} ({cvd:+.2f})")

    def reset(self):
        """Reset engine state (clear cache, reset VPIN)."""
        self.feature_cache.clear()
        self.last_cache_timestamp = None
        self.vpin_calculator.reset()
        logger.info("MicrostructureEngine reset")
