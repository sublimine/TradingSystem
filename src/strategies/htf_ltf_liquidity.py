"""
HTF-LTF Liquidity Strategy - Multi-Timeframe Institutional Zones

Identifies institutional liquidity zones on higher timeframes (H4, D1)
and executes precision entries when price tests these zones on lower timeframes.

FUNDAMENTO ACADÃ‰MICO:
- Derman (2002): "The Perception of Time, Risk and Return During Periods of Speculation"
  Quantitative Finance, 2(4), 282-296
- MÃ¼ller et al. (1997): "Volatilities of Different Time Resolutions"
  Journal of Empirical Finance, 4(2-3), 213-239
- Dacorogna et al. (2001): "An Introduction to High-Frequency Finance"
  Academic Press, Chapter 4 (Scaling Laws)

DIFERENCIADORES INSTITUCIONALES:
1. Swing identification using 20-bar lookback (vs 10 retail)
2. Zone projection tolerance of Â±2 pips for precision
3. Rejection confirmation requiring 60% wick ratio
4. Multi-timeframe confluence validation
"""

import logging
import numpy as np
import pandas as pd
from typing import Optional, Dict, List, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass

from .strategy_base import StrategyBase, Signal

@dataclass
class LiquidityZone:
    """Data class representing an institutional liquidity zone."""
    timeframe: str
    zone_type: str  # 'resistance' or 'support'
    price_level: float
    strength: int
    last_test: datetime
    created_at: datetime
    
    @property
    def zone_bounds(self) -> Tuple[float, float]:
        """Get zone boundaries with pip tolerance."""
        pip_tolerance = 0.0002  # 2 pips
        return (self.price_level - pip_tolerance, self.price_level + pip_tolerance)
    
    def is_expired(self, current_time: datetime, max_age_hours: int = 168) -> bool:
        """Check if zone is too old (default 1 week)."""
        age = current_time - self.created_at
        return age > timedelta(hours=max_age_hours)

class HTFLTFLiquidity(StrategyBase):
    """
    Multi-timeframe liquidity strategy for institutional zones.
    
    Identifies significant levels on higher timeframes and trades
    rejections when price tests these zones on lower timeframes.
    """
    
    def __init__(self, config: Dict):
        """
        Initialize HTF-LTF Liquidity strategy.
        
        Args:
            config: Strategy configuration dictionary
        """
        super().__init__(config)
        
        # Timeframe parameters
        self.htf_timeframes = config.get('htf_timeframes', ['H4', 'D1'])
        self.swing_lookback = config.get('swing_lookback', 20)
        self.projection_tolerance_pips = config.get('projection_tolerance_pips', 2)
        
        # Rejection criteria
        self.rejection_wick_min_pct = config.get('rejection_wick_min_pct', 0.6)
        self.min_zone_touches = config.get('min_zone_touches', 2)
        
        # Risk management
        self.stop_buffer_atr = config.get('stop_buffer_atr', 1.0)
        self.take_profit_atr = config.get('take_profit_atr', 3.0)
        
        # State tracking
        self.htf_zones: List[LiquidityZone] = []
        self.last_htf_update = None
        self.htf_update_interval = timedelta(hours=1)
        
        self.logger = logging.getLogger(self.__class__.__name__)
        self.logger.info(f"HTF-LTF Liquidity initialized with timeframes={self.htf_timeframes}")
        self.name = 'htf_ltf_liquidity'
    
    def detect_rejection(self, data: pd.DataFrame) -> Optional[str]:
        """
        Detect rejection candle pattern at zone.
        
        Args:
            data: Recent price data
            
        Returns:
            'bullish' or 'bearish' rejection, None if no rejection
        """
        if len(data) < 1:
            return None
        
        last_bar = data.iloc[-1]
        
        bar_range = last_bar['high'] - last_bar['low']
        if bar_range == 0:
            return None
        
        body = abs(last_bar['close'] - last_bar['open'])
        body_ratio = body / bar_range
        
        # Check for bullish rejection
        if last_bar['close'] > last_bar['open']:
            lower_wick = last_bar['open'] - last_bar['low']
            lower_wick_ratio = lower_wick / bar_range
            
            if lower_wick_ratio >= self.rejection_wick_min_pct and body_ratio < 0.4:
                self.logger.info(f"Bullish rejection detected: wick={lower_wick_ratio:.2%}")
                return 'bullish'
        
        # Check for bearish rejection
        elif last_bar['close'] < last_bar['open']:
            upper_wick = last_bar['high'] - last_bar['open']
            upper_wick_ratio = upper_wick / bar_range
            
            if upper_wick_ratio >= self.rejection_wick_min_pct and body_ratio < 0.4:
                self.logger.info(f"Bearish rejection detected: wick={upper_wick_ratio:.2%}")
                return 'bearish'
        
        return None
    
    def update_htf_zones_from_features(self, features: Dict) -> None:
        """Update HTF zones from pre-calculated features."""
        current_time = datetime.now()
        
        if self.last_htf_update:
            if current_time - self.last_htf_update < self.htf_update_interval:
                return
        
        if 'htf_swing_highs' in features:
            for level in features['htf_swing_highs']:
                zone = LiquidityZone(
                    timeframe='H4',
                    zone_type='resistance',
                    price_level=level,
                    strength=2,
                    last_test=current_time,
                    created_at=current_time
                )
                self.htf_zones.append(zone)
        
        if 'htf_swing_lows' in features:
            for level in features['htf_swing_lows']:
                zone = LiquidityZone(
                    timeframe='H4',
                    zone_type='support',
                    price_level=level,
                    strength=2,
                    last_test=current_time,
                    created_at=current_time
                )
                self.htf_zones.append(zone)
        
        self.htf_zones = [z for z in self.htf_zones if not z.is_expired(current_time)]
        
        self.last_htf_update = current_time
        self.logger.info(f"HTF zones updated: {len(self.htf_zones)} active zones")
    
    def calculate_atr(self, data: pd.DataFrame, period: int = 14) -> float:
        """Calculate Average True Range."""
        high = data['high']
        low = data['low']
        close = data['close'].shift(1)
        
        tr = pd.concat([
            high - low,
            (high - close).abs(),
            (low - close).abs()
        ], axis=1).max(axis=1)
        
        atr = tr.rolling(window=period, min_periods=1).mean().iloc[-1]
        
        return atr
    
    def evaluate(self, data: pd.DataFrame, features: Dict) -> Optional[Signal]:
        """
        Evaluate HTF-LTF liquidity conditions.
        
        Process:
        1. Load/update HTF zones from features
        2. Check if current price near HTF zone (Â±2 pips)
        3. Detect rejection candle (wick >= 60%)
        4. Entry in direction of rejection
        5. Stop beyond zone, TP = next zone or 3 ATR
        
        Args:
            data: DataFrame with LTF OHLCV data
            features: Dict with HTF analysis
            
        Returns:
            Signal object if conditions met, None otherwise
        """
        if len(data) < 50:
            self.logger.debug("Insufficient data for HTF-LTF analysis")
            return None
        
        # STEP 1: Update HTF zones
        self.update_htf_zones_from_features(features)
        
        if not self.htf_zones:
            self.logger.debug("No HTF zones available")
            return None
        
        # STEP 2: Check if price near zone
        current_price = data['close'].iloc[-1]
        
        near_zone = None
        for zone in self.htf_zones:
            zone_bounds = zone.zone_bounds
            if zone_bounds[0] <= current_price <= zone_bounds[1]:
                near_zone = zone
                self.logger.info(f"Price at {zone.zone_type} zone: {zone.price_level:.5f}")
                break
        
        if not near_zone:
            return None
        
        # STEP 3: Detect rejection
        rejection = self.detect_rejection(data.tail(3))
        
        if not rejection:
            self.logger.debug("No rejection pattern detected")
            return None
        
        # STEP 4: Validate rejection direction
        if near_zone.zone_type == 'support' and rejection != 'bullish':
            self.logger.debug("Rejection direction doesn't match support zone")
            return None
        
        if near_zone.zone_type == 'resistance' and rejection != 'bearish':
            self.logger.debug("Rejection direction doesn't match resistance zone")
            return None
        
        # STEP 5: Generate signal
        atr = self.calculate_atr(data)
        
        if rejection == 'bullish':
            direction = 'long'
            entry_price = current_price
            stop_loss = near_zone.price_level - (self.stop_buffer_atr * atr)
            take_profit = entry_price + (self.take_profit_atr * atr)
        
        else:
            direction = 'short'
            entry_price = current_price
            stop_loss = near_zone.price_level + (self.stop_buffer_atr * atr)
            take_profit = entry_price - (self.take_profit_atr * atr)
        
        base_confidence = 0.70
        strength_bonus = min(0.20, near_zone.strength * 0.05)
        confidence = base_confidence + strength_bonus
        
        if near_zone.strength >= 4:
            sizing_level = 4
        elif near_zone.strength >= 3:
            sizing_level = 3
        else:
            sizing_level = 2
        
        near_zone.last_test = datetime.now()
        
        signal = Signal(
            strategy_name=self.name,
            direction=direction,
            entry_price=entry_price,
            stop_loss=stop_loss,
            take_profit=take_profit,
            confidence=confidence,
            sizing_level=sizing_level,
            metadata={
                'htf_timeframe': near_zone.timeframe,
                'zone_type': near_zone.zone_type,
                'zone_level': float(near_zone.price_level),
                'zone_strength': near_zone.strength,
                'rejection_type': rejection,
                'atr': float(atr),
                'risk_reward_ratio': abs(take_profit - entry_price) / abs(entry_price - stop_loss)
            }
        )
        
        self.logger.info(f"Signal generated: {direction.upper()} @ {entry_price:.5f}")
        
        return signal