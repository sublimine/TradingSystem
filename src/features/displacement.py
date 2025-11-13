"""
Displacement and Order Block detection module.

Based on:
- Bouchaud, J.P., et al. (2009). "How Markets Slowly Digest Changes in Supply and Demand."
- Lillo, F., et al. (2003). "Master curve for price-impact function."
"""

import pandas as pd
import numpy as np
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

@dataclass
class OrderBlock:
    """Represents an institutional order block zone."""
    timestamp: datetime
    block_type: str
    zone_high: float
    zone_low: float
    displacement_magnitude: float
    volume_sigma: float
    creation_price: float
    tested_count: int = 0
    last_test_timestamp: Optional[datetime] = None
    is_active: bool = True
    is_breached: bool = False
    
    @property
    def zone_middle(self) -> float:
        return (self.zone_high + self.zone_low) / 2
    
    @property 
    def zone_width(self) -> float:
        return self.zone_high - self.zone_low

def detect_displacement(data: pd.DataFrame, atr: float, displacement_threshold: float = 2.0,
                       volume_sigma_threshold: float = 2.5, lookback_periods: int = 50) -> List[OrderBlock]:
    """
    Detect institutional displacement creating order blocks.

    P2-017: Complete algorithm documentation for displacement detection

    ALGORITHM:
    Institutional order blocks form when large orders "displace" price rapidly with
    anomalous volume, creating imbalance zones that act as future support/resistance.

    Detection Process:
    1. Calculate displacement ratio = body_size / ATR for each candle
       - Body size measures directional price movement
       - ATR normalization makes threshold instrument-agnostic

    2. Calculate volume z-score over rolling window
       - z = (volume - mean) / std over lookback_periods
       - Identifies volume spikes above statistical norm

    3. Order block detected when BOTH conditions met:
       a) Displacement ratio >= displacement_threshold (default: 2.0)
          - 2.0 = candle body is 2x normal ATR movement
          - Indicates strong institutional push, not drift

       b) Volume z-score >= volume_sigma_threshold (default: 2.5)
          - 2.5σ = 98.8% confidence level
          - Confirms institutional size, not retail accumulation

    4. Order block zone = [candle_low, candle_high]
       - Block type: BULLISH if close > open, BEARISH if close < open
       - Zone represents price region where institution absorbed liquidity

    Args:
        data: OHLCV DataFrame with 'timestamp', 'open', 'high', 'low', 'close', 'tick_volume'
        atr: Average True Range value for normalization
        displacement_threshold: Minimum body/ATR ratio (default: 2.0)
        volume_sigma_threshold: Minimum volume z-score (default: 2.5σ)
        lookback_periods: Rolling window for volume statistics (default: 50)

    Returns:
        List[OrderBlock]: Detected order blocks with displacement magnitude and volume sigma

    Research basis:
    - Bouchaud et al. (2009): "How Markets Slowly Digest Changes in Supply and Demand"
    - Lillo et al. (2003): "Master curve for price-impact function"
    - ICT (Inner Circle Trader) order block concepts adapted to statistical rigor
    """
    try:
        if len(data) < lookback_periods:
            return []
        if atr is None or np.isnan(atr) or atr <= 0:
            return []
        
        volume_mean = data['tick_volume'].rolling(window=lookback_periods).mean()
        volume_std = data['tick_volume'].rolling(window=lookback_periods).std()
        body_sizes = abs(data['close'] - data['open'])
        displacement_ratios = body_sizes / atr
        
        order_blocks = []
        
        for i in range(lookback_periods, len(data)):
            candle = data.iloc[i]
            
            if displacement_ratios.iloc[i] >= displacement_threshold:
                vol_mean = volume_mean.iloc[i]
                vol_std = volume_std.iloc[i]
                
                if vol_std > 0:
                    volume_z = (candle['tick_volume'] - vol_mean) / vol_std
                    
                    if volume_z >= volume_sigma_threshold:
                        block_type = 'BULLISH' if candle['close'] > candle['open'] else 'BEARISH'
                        
                        block = OrderBlock(
                            timestamp=candle['timestamp'],
                            block_type=block_type,
                            zone_high=candle['high'],
                            zone_low=candle['low'],
                            displacement_magnitude=displacement_ratios.iloc[i],
                            volume_sigma=volume_z,
                            creation_price=candle['close'],
                            tested_count=0,
                            is_active=True,
                            is_breached=False
                        )
                        
                        order_blocks.append(block)
        
        return order_blocks
        
    except Exception as e:
        logger.error(f"Displacement detection failed: {str(e)}", exc_info=True)
        return []

def validate_order_block_retest(block: OrderBlock, price_data: pd.DataFrame,
                               buffer_atr: float, atr_value: float) -> Tuple[bool, bool]:
    """Check if order block is being retested with rejection."""
    try:
        if len(price_data) < 3:
            return False, False
        
        current_candle = price_data.iloc[-1]
        buffer = buffer_atr * atr_value
        zone_high_buffered = block.zone_high + buffer
        zone_low_buffered = block.zone_low - buffer
        
        is_retesting = False
        shows_rejection = False
        
        if block.block_type == 'BULLISH':
            if (current_candle['low'] <= zone_high_buffered and 
                current_candle['low'] >= zone_low_buffered):
                is_retesting = True
                
                if (current_candle['close'] > block.zone_middle and
                    current_candle['low'] < current_candle['close'] - 0.5 * (current_candle['high'] - current_candle['low'])):
                    shows_rejection = True
        else:
            if (current_candle['high'] >= zone_low_buffered and
                current_candle['high'] <= zone_high_buffered):
                is_retesting = True
                
                if (current_candle['close'] < block.zone_middle and
                    current_candle['high'] > current_candle['close'] + 0.5 * (current_candle['high'] - current_candle['low'])):
                    shows_rejection = True
        
        if block.block_type == 'BULLISH':
            if current_candle['close'] < zone_low_buffered:
                block.is_breached = True
                block.is_active = False
        else:
            if current_candle['close'] > zone_high_buffered:
                block.is_breached = True
                block.is_active = False
        
        return is_retesting, shows_rejection
        
    except Exception as e:
        logger.error(f"Order block validation failed: {str(e)}")
        return False, False

def calculate_footprint_direction(data: pd.DataFrame, lookback: int = 10) -> float:
    """Calculate directional footprint from recent order flow."""
    try:
        if len(data) < lookback:
            return 0.0
        
        recent_data = data.tail(lookback)
        deltas = []
        
        for _, bar in recent_data.iterrows():
            mid = (bar['high'] + bar['low']) / 2
            if bar['close'] > mid:
                delta = (bar['close'] - mid) / (bar['high'] - mid) if bar['high'] > mid else 1.0
            else:
                delta = (bar['close'] - mid) / (mid - bar['low']) if mid > bar['low'] else -1.0
            
            weighted_delta = delta * (bar['tick_volume'] / recent_data['tick_volume'].mean())
            deltas.append(weighted_delta)
        
        cumulative_delta = np.sum(deltas)
        normalized_delta = np.tanh(cumulative_delta / lookback)
        
        return normalized_delta
        
    except Exception as e:
        logger.error(f"Footprint calculation failed: {str(e)}")
        return 0.0