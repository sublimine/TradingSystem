"""
FVG Institutional Strategy - Fair Value Gap Detection

Identifies and trades inefficient pricing gaps where rapid price movement
creates zones without transaction history, expecting mean reversion.

FUNDAMENTO ACADÃ‰MICO:
- Grossman & Stiglitz (1980): "On the Impossibility of Informationally Efficient Markets"
  American Economic Review, 70(3), 393-408
- Hasbrouck (2007): "Empirical Market Microstructure"
  Oxford University Press, Chapter 5 (Price Discovery)
- O'Hara (1995): "Market Microstructure Theory"
  Blackwell Publishers, Chapter 3 (Information-Based Models)

DIFERENCIADORES INSTITUCIONALES:
1. Gap minimum of 0.75 ATR (vs 0.5 retail) for statistical significance
2. Volume anomaly requirement using 70th percentile threshold
3. Entry at 50% gap fill zone for optimal risk-reward
4. Stop placement beyond gap extremes with ATR buffer
"""

import logging
import numpy as np
import pandas as pd
from typing import Optional, Dict, Tuple, List
from datetime import datetime
from dataclasses import dataclass

from .strategy_base import StrategyBase, Signal

@dataclass
class FVGZone:
    """Data class representing a Fair Value Gap zone."""
    gap_type: str  # 'bullish' or 'bearish'
    gap_start: float
    gap_end: float
    gap_size: float
    timestamp: datetime
    volume_spike: float
    entry_triggered: bool = False
    
    @property
    def gap_midpoint(self) -> float:
        """Calculate midpoint of gap zone."""
        return (self.gap_start + self.gap_end) / 2
    
    @property
    def fill_zone_50(self) -> Tuple[float, float]:
        """Calculate 50% fill zone for entry."""
        if self.gap_type == 'bullish':
            return (self.gap_start, self.gap_start + self.gap_size * 0.5)
        else:
            return (self.gap_end - self.gap_size * 0.5, self.gap_end)

class FVGInstitutional(StrategyBase):
    """
    Fair Value Gap strategy detecting inefficient pricing zones.
    
    Trades mean reversion when price returns to fill gaps created
    by rapid institutional movements.
    """
    
    def __init__(self, config: Dict):
        """
        Initialize FVG Institutional strategy.
        
        Args:
            config: Strategy configuration dictionary
        """
        super().__init__(config)
        
        # Gap detection parameters
        self.gap_atr_minimum = config.get('gap_atr_minimum', 0.75)
        self.volume_anomaly_required = config.get('volume_anomaly_required', True)
        self.volume_percentile = config.get('volume_percentile', 70)
        self.gap_fill_percentage = config.get('gap_fill_percentage', 0.5)
        
        # Risk management
        self.stop_buffer_atr = config.get('stop_buffer_atr', 0.5)
        self.target_gap_multiples = config.get('target_gap_multiples', 2.0)
        self.max_gap_age_bars = config.get('max_gap_age_bars', 100)
        
        # State tracking
        self.active_gaps: List[FVGZone] = []
        self.filled_gaps: List[FVGZone] = []
        
        self.logger = logging.getLogger(self.__class__.__name__)
        self.logger.info(f"FVG Institutional initialized with gap_min={self.gap_atr_minimum} ATR, "
                        f"volume_percentile={self.volume_percentile}")
        self.name = 'fvg_institutional'
    
    def detect_fvg_bullish(self, data: pd.DataFrame) -> Optional[Tuple[float, float]]:
        """
        Detect bullish Fair Value Gap (gap up).
        
        Bullish FVG occurs when: Bar[i-2].high < Bar[i].low
        Creating a gap zone between Bar[i-2].high and Bar[i].low
        
        Args:
            data: DataFrame with OHLCV data (need at least 3 bars)
            
        Returns:
            Tuple of (gap_start, gap_end) if FVG detected, None otherwise
        """
        if len(data) < 3:
            return None
        
        bar_minus_2 = data.iloc[-3]
        bar_current = data.iloc[-1]
        
        if bar_minus_2['high'] < bar_current['low']:
            gap_start = bar_minus_2['high']
            gap_end = bar_current['low']
            
            self.logger.info(f"Bullish FVG detected: gap from {gap_start:.5f} to {gap_end:.5f}")
            return (gap_start, gap_end)
        
        return None
    
    def detect_fvg_bearish(self, data: pd.DataFrame) -> Optional[Tuple[float, float]]:
        """
        Detect bearish Fair Value Gap (gap down).
        
        Bearish FVG occurs when: Bar[i-2].low > Bar[i].high
        Creating a gap zone between Bar[i].high and Bar[i-2].low
        
        Args:
            data: DataFrame with OHLCV data (need at least 3 bars)
            
        Returns:
            Tuple of (gap_start, gap_end) if FVG detected, None otherwise
        """
        if len(data) < 3:
            return None
        
        bar_minus_2 = data.iloc[-3]
        bar_current = data.iloc[-1]
        
        if bar_minus_2['low'] > bar_current['high']:
            gap_start = bar_current['high']
            gap_end = bar_minus_2['low']
            
            self.logger.info(f"Bearish FVG detected: gap from {gap_start:.5f} to {gap_end:.5f}")
            return (gap_start, gap_end)
        
        return None
    
    def is_volume_anomalous(self, data: pd.DataFrame, bar_index: int) -> bool:
        """
        Check if volume at gap bar is anomalous (above percentile threshold).
        
        Args:
            data: DataFrame with volume data
            bar_index: Index of bar to check
            
        Returns:
            True if volume exceeds percentile threshold
        """
        if bar_index < 0 or bar_index >= len(data):
            return False
        
        lookback = min(100, len(data))
        volume_series = data['volume'].iloc[-lookback:]
        
        threshold = np.percentile(volume_series, self.volume_percentile)
        bar_volume = data['volume'].iloc[bar_index]
        
        is_anomalous = bar_volume > threshold
        
        if is_anomalous:
            self.logger.debug(f"Volume anomaly detected: {bar_volume:.0f} > "
                            f"{threshold:.0f} ({self.volume_percentile}th percentile)")
        
        return is_anomalous
    
    def calculate_atr(self, data: pd.DataFrame, period: int = 14) -> float:
        """
        Calculate Average True Range for gap validation and stops.
        
        Args:
            data: DataFrame with OHLC data
            period: ATR period
            
        Returns:
            Current ATR value
        """
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
    
    def manage_active_gaps(self, data: pd.DataFrame) -> None:
        """Update and clean active gap zones."""
        current_price = data['close'].iloc[-1]
        
        updated_gaps = []
        
        for gap in self.active_gaps:
            if gap.gap_type == 'bullish':
                if current_price <= gap.gap_start:
                    self.logger.info(f"Bullish gap fully filled at {current_price:.5f}")
                    self.filled_gaps.append(gap)
                    continue
            else:
                if current_price >= gap.gap_end:
                    self.logger.info(f"Bearish gap fully filled at {current_price:.5f}")
                    self.filled_gaps.append(gap)
                    continue
            
            updated_gaps.append(gap)
        
        self.active_gaps = updated_gaps
    
    def evaluate(self, data: pd.DataFrame, features: Dict) -> Optional[Signal]:
        """
        Evaluate FVG conditions and generate trading signal.
        
        Process:
        1. Detect FVG (bullish or bearish)
        2. Verify gap size â‰¥ 0.75 ATR
        3. Check volume anomaly in gap bar
        4. Wait for price retracement to 50% fill zone
        5. Entry with stop beyond gap, target = 2x gap size
        
        Args:
            data: DataFrame with OHLCV data
            features: Dict with pre-calculated features
            
        Returns:
            Signal object if conditions met, None otherwise
        """
        if len(data) < 20:
            self.logger.debug("Insufficient data for FVG analysis")
            return None
        
        atr = self.calculate_atr(data)
        
        self.manage_active_gaps(data)
        
        # STEP 1: Detect new FVGs
        bullish_gap = self.detect_fvg_bullish(data)
        bearish_gap = self.detect_fvg_bearish(data)
        
        # Process new bullish gap
        if bullish_gap:
            gap_size = bullish_gap[1] - bullish_gap[0]
            
            if gap_size >= self.gap_atr_minimum * atr:
                self.logger.info(f"Bullish gap validated: {gap_size:.5f} = {gap_size/atr:.2f} ATR")
                
                if not self.volume_anomaly_required or self.is_volume_anomalous(data, -1):
                    new_gap = FVGZone(
                        gap_type='bullish',
                        gap_start=bullish_gap[0],
                        gap_end=bullish_gap[1],
                        gap_size=gap_size,
                        timestamp=datetime.now(),
                        volume_spike=data['volume'].iloc[-1] / data['volume'].mean()
                    )
                    self.active_gaps.append(new_gap)
                    self.logger.info(f"New bullish FVG zone added")
        
        # Process new bearish gap
        if bearish_gap:
            gap_size = bearish_gap[1] - bearish_gap[0]
            
            if gap_size >= self.gap_atr_minimum * atr:
                self.logger.info(f"Bearish gap validated: {gap_size:.5f} = {gap_size/atr:.2f} ATR")
                
                if not self.volume_anomaly_required or self.is_volume_anomalous(data, -1):
                    new_gap = FVGZone(
                        gap_type='bearish',
                        gap_start=bearish_gap[0],
                        gap_end=bearish_gap[1],
                        gap_size=gap_size,
                        timestamp=datetime.now(),
                        volume_spike=data['volume'].iloc[-1] / data['volume'].mean()
                    )
                    self.active_gaps.append(new_gap)
                    self.logger.info(f"New bearish FVG zone added")
        
        # STEP 4: Check for entry conditions
        current_price = data['close'].iloc[-1]
        
        for gap in self.active_gaps:
            if gap.entry_triggered:
                continue
            
            fill_zone = gap.fill_zone_50
            
            if gap.gap_type == 'bullish':
                if fill_zone[0] <= current_price <= fill_zone[1]:
                    self.logger.info(f"Bullish gap fill zone reached")
                    
                    direction = 'long'
                    entry_price = current_price
                    stop_loss = gap.gap_start - (self.stop_buffer_atr * atr)
                    take_profit = entry_price + (gap.gap_size * self.target_gap_multiples)
                    
                    confidence = min(0.90, 0.70 + gap.volume_spike * 0.05)
                    
                    if gap.gap_size > 1.5 * atr and gap.volume_spike > 2.0:
                        sizing_level = 4
                    elif gap.gap_size > 1.0 * atr:
                        sizing_level = 3
                    else:
                        sizing_level = 2
                    
                    gap.entry_triggered = True
                    
                    return Signal(
                        strategy_name=self.name,
                        direction=direction,
                        entry_price=entry_price,
                        stop_loss=stop_loss,
                        take_profit=take_profit,
                        confidence=confidence,
                        sizing_level=sizing_level,
                        metadata={
                            'gap_type': gap.gap_type,
                            'gap_size': float(gap.gap_size),
                            'gap_size_atr': float(gap.gap_size / atr),
                            'volume_spike': float(gap.volume_spike),
                            'risk_reward_ratio': abs(take_profit - entry_price) / abs(entry_price - stop_loss)
                        }
                    )
            
            else:  # bearish gap
                if fill_zone[0] <= current_price <= fill_zone[1]:
                    self.logger.info(f"Bearish gap fill zone reached")
                    
                    direction = 'short'
                    entry_price = current_price
                    stop_loss = gap.gap_end + (self.stop_buffer_atr * atr)
                    take_profit = entry_price - (gap.gap_size * self.target_gap_multiples)
                    
                    confidence = min(0.90, 0.70 + gap.volume_spike * 0.05)
                    
                    if gap.gap_size > 1.5 * atr and gap.volume_spike > 2.0:
                        sizing_level = 4
                    elif gap.gap_size > 1.0 * atr:
                        sizing_level = 3
                    else:
                        sizing_level = 2
                    
                    gap.entry_triggered = True
                    
                    return Signal(
                        strategy_name=self.name,
                        direction=direction,
                        entry_price=entry_price,
                        stop_loss=stop_loss,
                        take_profit=take_profit,
                        confidence=confidence,
                        sizing_level=sizing_level,
                        metadata={
                            'gap_type': gap.gap_type,
                            'gap_size': float(gap.gap_size),
                            'gap_size_atr': float(gap.gap_size / atr),
                            'volume_spike': float(gap.volume_spike),
                            'risk_reward_ratio': abs(entry_price - take_profit) / abs(entry_price - stop_loss)
                        }
                    )
        
        return None