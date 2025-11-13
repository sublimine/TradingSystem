"""
Order Flow Analytics Module
Calculates VPIN and other order flow toxicity metrics
"""

import numpy as np
import pandas as pd
from typing import List, Tuple, Optional
from collections import deque


class VPINCalculator:
    """
    Calculator for Volume-Synchronized Probability of Informed Trading (VPIN).
    
    VPIN measures order flow toxicity by analyzing imbalance between
    buyer-initiated and seller-initiated volume over volume buckets.
    """
    
    def __init__(self, bucket_size: int = 50000, num_buckets: int = 50):
        """
        Initialize VPIN calculator.

        Args:
            bucket_size: Volume threshold for each bucket
            num_buckets: Number of buckets to maintain for rolling calculation
        """
        # P2-008: VPIN bucket parameters (Easley et al. 2012)
        # bucket_size=50000: Volume por bucket calibrado para FX majors con ADV ~$1B
        #   - 50K captura ~5 min de flow en horario activo, suficiente para detectar toxicity
        #   - Muy pequeño (<10K) = ruido, muy grande (>100K) = lag excesivo
        # num_buckets=50: Rolling window de ~50 buckets = 4 horas flow aprox
        #   - Balance entre sensibilidad (detectar toxicity rápido) y estabilidad (evitar false positives)
        # Para instrumentos menos líquidos considerar bucket_size proporcional a ADV
        self.bucket_size = bucket_size
        self.num_buckets = num_buckets
        self.buckets = deque(maxlen=num_buckets)
        self.current_bucket_volume = 0
        self.current_bucket_buy_volume = 0
        self.current_bucket_sell_volume = 0
        
    def add_trade(self, volume: float, trade_direction: int) -> Optional[float]:
        """
        Add trade to VPIN calculator and return current VPIN if bucket completed.

        Args:
            volume: Trade volume
            trade_direction: 1 for buy, -1 for sell, 0 for unclassified

        Returns:
            Current VPIN value if bucket completed, None otherwise

        P2-023: trade_direction==0 handling documented
        IMPORTANT: When trade_direction is 0 (unclassified/neutral), this method returns None.
        Callers MUST validate return value before using:
            vpin = calculator.add_trade(volume, direction)
            if vpin is not None:
                # Safe to use vpin
        Failing to check for None can cause AttributeError or incorrect calculations.
        """
        if trade_direction == 0:
            return None
        
        self.current_bucket_volume += volume
        
        if trade_direction > 0:
            self.current_bucket_buy_volume += volume
        else:
            self.current_bucket_sell_volume += volume
        
        if self.current_bucket_volume >= self.bucket_size:
            bucket_imbalance = abs(
                self.current_bucket_buy_volume - self.current_bucket_sell_volume
            )
            
            self.buckets.append({
                'total_volume': self.current_bucket_volume,
                'buy_volume': self.current_bucket_buy_volume,
                'sell_volume': self.current_bucket_sell_volume,
                'imbalance': bucket_imbalance
            })
            
            self.current_bucket_volume = 0
            self.current_bucket_buy_volume = 0
            self.current_bucket_sell_volume = 0
            
            if len(self.buckets) >= self.num_buckets:
                return self._calculate_vpin()
        
        return None
    
    def _calculate_vpin(self) -> float:
        """
        Calculate VPIN from accumulated buckets.
        
        Returns:
            VPIN value between 0 and 1
        """
        if len(self.buckets) == 0:
            return 0
        
        total_imbalance = sum(bucket['imbalance'] for bucket in self.buckets)
        total_volume = sum(bucket['total_volume'] for bucket in self.buckets)
        
        if total_volume == 0:
            return 0
        
        vpin = total_imbalance / total_volume
        return vpin
    
    def get_current_vpin(self) -> float:
        """
        Get current VPIN value without waiting for bucket completion.
        
        Returns:
            Current VPIN value
        """
        if len(self.buckets) == 0:
            return 0
        
        return self._calculate_vpin()
    
    def reset(self):
        """Reset calculator state."""
        self.buckets.clear()
        self.current_bucket_volume = 0
        self.current_bucket_buy_volume = 0
        self.current_bucket_sell_volume = 0


def calculate_signed_volume(prices: pd.Series, volumes: pd.Series) -> pd.Series:
    """
    Calculate signed volume based on price changes.
    
    Positive volume indicates buying pressure, negative indicates selling pressure.
    
    Args:
        prices: Series of prices
        volumes: Series of volumes
        
    Returns:
        Series of signed volumes
    """
    price_changes = prices.diff()
    
    signed_vol = volumes.copy()
    signed_vol[price_changes < 0] = -signed_vol[price_changes < 0]
    signed_vol[price_changes == 0] = 0
    
    return signed_vol


def calculate_cumulative_volume_delta(signed_volumes: pd.Series, 
                                     window: int = 20) -> pd.Series:
    """
    Calculate cumulative volume delta over rolling window.
    
    Args:
        signed_volumes: Series of signed volumes
        window: Rolling window size
        
    Returns:
        Series of cumulative volume deltas
    """
    cvd = signed_volumes.rolling(window=window).sum()
    return cvd


def calculate_volume_weighted_average_price(prices: pd.Series, 
                                           volumes: pd.Series,
                                           window: int = 20) -> pd.Series:
    """
    Calculate Volume Weighted Average Price (VWAP) over rolling window.
    
    Args:
        prices: Series of prices
        volumes: Series of volumes
        window: Rolling window size
        
    Returns:
        Series of VWAP values
    """
    typical_price = prices
    vwap = (typical_price * volumes).rolling(window=window).sum() / \
           volumes.rolling(window=window).sum()
    
    return vwap


def calculate_order_flow_imbalance_ratio(buy_volume: float, 
                                         sell_volume: float) -> float:
    """
    Calculate Order Flow Imbalance Ratio.
    
    Args:
        buy_volume: Total buy volume
        sell_volume: Total sell volume
        
    Returns:
        Imbalance ratio between -1 and 1
    """
    total_volume = buy_volume + sell_volume
    
    if total_volume == 0:
        return 0
    
    return (buy_volume - sell_volume) / total_volume


def detect_volume_clusters(volumes: pd.Series, 
                          threshold_multiplier: float = 2.0,
                          window: int = 20) -> pd.Series:
    """
    Detect volume clusters where volume exceeds threshold.
    
    Args:
        volumes: Series of volumes
        threshold_multiplier: Multiple of average volume to consider cluster
        window: Window for calculating average volume
        
    Returns:
        Boolean series indicating volume clusters
    """
    avg_volume = volumes.rolling(window=window).mean()
    threshold = avg_volume * threshold_multiplier
    
    clusters = volumes > threshold
    return clusters


def calculate_volume_profile(prices: pd.Series, 
                             volumes: pd.Series,
                             num_bins: int = 50) -> pd.DataFrame:
    """
    Calculate volume profile showing volume distribution across price levels.
    
    Args:
        prices: Series of prices
        volumes: Series of volumes
        num_bins: Number of price bins
        
    Returns:
        DataFrame with price levels and corresponding volumes
    """
    min_price = prices.min()
    max_price = prices.max()
    
    bins = np.linspace(min_price, max_price, num_bins + 1)
    
    price_bins = pd.cut(prices, bins=bins, include_lowest=True)
    
    volume_profile = pd.DataFrame({
        'price_level': price_bins,
        'volume': volumes
    }).groupby('price_level').sum()
    
    volume_profile['price_midpoint'] = volume_profile.index.map(lambda x: x.mid)
    
    return volume_profile.reset_index(drop=True)


def calculate_trade_intensity(volumes: pd.Series, 
                              time_deltas: pd.Series) -> pd.Series:
    """
    Calculate trade intensity as volume per unit time.
    
    Args:
        volumes: Series of trade volumes
        time_deltas: Series of time differences between trades in seconds
        
    Returns:
        Series of trade intensity values
    """
    time_deltas_safe = time_deltas.replace(0, np.nan)
    intensity = volumes / time_deltas_safe
    intensity = intensity.fillna(0)
    
    return intensity


def calculate_kyle_lambda(price_changes: pd.Series, 
                         signed_volumes: pd.Series,
                         window: int = 50) -> pd.Series:
    """
    Calculate Kyle's lambda (price impact coefficient).
    
    Kyle's lambda measures price impact per unit of order flow.
    
    Args:
        price_changes: Series of price changes
        signed_volumes: Series of signed volumes
        window: Rolling window for calculation
        
    Returns:
        Series of Kyle's lambda estimates
    """
    if len(price_changes) != len(signed_volumes):
        raise ValueError("Price changes and signed volumes must have same length")
    
    lambda_values = []
    
    for i in range(len(price_changes)):
        if i < window:
            lambda_values.append(np.nan)
            continue
        
        window_price_changes = price_changes.iloc[i-window:i]
        window_signed_volumes = signed_volumes.iloc[i-window:i]
        
        if window_signed_volumes.std() == 0:
            lambda_values.append(0)
            continue
        
        covariance = np.cov(window_price_changes, window_signed_volumes)[0, 1]
        variance = window_signed_volumes.var()
        
        if variance > 0:
            lambda_estimate = covariance / variance
            lambda_values.append(lambda_estimate)
        else:
            lambda_values.append(0)
    
    return pd.Series(lambda_values, index=price_changes.index)


def calculate_amihud_illiquidity(returns: pd.Series, 
                                 volumes: pd.Series,
                                 window: int = 20) -> pd.Series:
    """
    Calculate Amihud illiquidity measure.
    
    Measures price impact per unit of volume, higher values indicate less liquidity.
    
    Args:
        returns: Series of returns
        volumes: Series of volumes
        window: Rolling window size
        
    Returns:
        Series of illiquidity measures
    """
    abs_returns = returns.abs()
    
    illiquidity = (abs_returns / volumes).rolling(window=window).mean()
    
    return illiquidity

"""
Order Flow Imbalance (OFI) Calculator
Implementation based on Cont, Stoikov, Talreja (2014)
"""

import numpy as np
from collections import deque
from typing import Dict, Optional


class OFICalculator:
    """
    Calculates Order Flow Imbalance to predict short-term price direction.
    
    OFI(t) = ΔBid_volume(t) - ΔAsk_volume(t)
    
    Positive OFI: Buying pressure (bullish)
    Negative OFI: Selling pressure (bearish)
    """
    
    def __init__(self, window: int = 20):
        """
        Initialize OFI calculator.
        
        Args:
            window: Rolling window for OFI calculation
        """
        self.window = window
        self.bid_volumes = deque(maxlen=window)
        self.ask_volumes = deque(maxlen=window)
        self.ofi_history = deque(maxlen=window)
    
    def update(self, bid_volume: float, ask_volume: float) -> float:
        """
        Update OFI with new bid/ask volume data.
        
        Args:
            bid_volume: Current cumulative bid volume
            ask_volume: Current cumulative ask volume
            
        Returns:
            Current OFI value
        """
        # Calculate delta from previous observation
        if len(self.bid_volumes) > 0:
            delta_bid = bid_volume - self.bid_volumes[-1]
            delta_ask = ask_volume - self.ask_volumes[-1]
        else:
            delta_bid = 0
            delta_ask = 0
        
        # OFI = ΔBid - ΔAsk
        ofi = delta_bid - delta_ask
        
        # Store for history
        self.bid_volumes.append(bid_volume)
        self.ask_volumes.append(ask_volume)
        self.ofi_history.append(ofi)
        
        return ofi
    
    def get_cumulative_ofi(self) -> float:
        """Get cumulative OFI over window."""
        if not self.ofi_history:
            return 0.0
        return float(sum(self.ofi_history))
    
    def get_ofi_direction(self) -> int:
        """
        Get OFI direction signal.
        
        Returns:
            1: Bullish (buying pressure)
            -1: Bearish (selling pressure)
            0: Neutral
        """
        cum_ofi = self.get_cumulative_ofi()
        
        if cum_ofi > 0:
            return 1
        elif cum_ofi < 0:
            return -1
        else:
            return 0
    
    def get_ofi_strength(self) -> float:
        """
        Get OFI strength (normalized).
        
        Returns:
            Float between 0 and 1 indicating strength of imbalance
        """
        if not self.ofi_history:
            return 0.0
        
        cum_ofi = abs(self.get_cumulative_ofi())
        total_volume = sum(self.bid_volumes) + sum(self.ask_volumes)
        
        if total_volume == 0:
            return 0.0
        
        # Normalize by total volume
        strength = cum_ofi / total_volume
        
        # Cap at 1.0
        return min(strength, 1.0)
    
    def get_metrics(self) -> Dict[str, float]:
        """
        Get all OFI metrics.
        
        Returns:
            Dictionary with ofi, direction, and strength
        """
        return {
            'ofi': self.get_cumulative_ofi(),
            'ofi_direction': float(self.get_ofi_direction()),
            'ofi_strength': self.get_ofi_strength()
        }
