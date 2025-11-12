"""
Technical Indicators Module
Calculates traditional technical analysis indicators
All calculations avoid lookahead bias
"""

import numpy as np
import pandas as pd
from typing import Tuple, Optional, Union


def calculate_rsi(prices: pd.Series, period: int = 14) -> pd.Series:
    """
    Calculate Relative Strength Index.
    
    Args:
        prices: Series of closing prices
        period: Lookback period for RSI calculation
        
    Returns:
        Series of RSI values (0-100)
    """
    if len(prices) < period + 1:
        return pd.Series(index=prices.index, dtype=float)
    
    delta = prices.diff()
    
    gain = delta.where(delta > 0, 0)
    loss = -delta.where(delta < 0, 0)
    
    avg_gain = gain.rolling(window=period, min_periods=period).mean()
    avg_loss = loss.rolling(window=period, min_periods=period).mean()
    
    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    
    return rsi


def calculate_macd(prices: pd.Series, fast: int = 12, slow: int = 26, 
                   signal: int = 9) -> Tuple[pd.Series, pd.Series, pd.Series]:
    """
    Calculate MACD (Moving Average Convergence Divergence).
    
    Args:
        prices: Series of closing prices
        fast: Fast EMA period
        slow: Slow EMA period
        signal: Signal line EMA period
        
    Returns:
        Tuple of (MACD line, Signal line, Histogram)
    """
    ema_fast = prices.ewm(span=fast, adjust=False).mean()
    ema_slow = prices.ewm(span=slow, adjust=False).mean()
    
    macd_line = ema_fast - ema_slow
    signal_line = macd_line.ewm(span=signal, adjust=False).mean()
    histogram = macd_line - signal_line
    
    return macd_line, signal_line, histogram


def calculate_bollinger_bands(prices: pd.Series, period: int = 20, 
                              num_std: float = 2.0) -> Tuple[pd.Series, pd.Series, pd.Series]:
    """
    Calculate Bollinger Bands.
    
    Args:
        prices: Series of closing prices
        period: Moving average period
        num_std: Number of standard deviations for bands
        
    Returns:
        Tuple of (Upper band, Middle band, Lower band)
    """
    middle_band = prices.rolling(window=period, min_periods=period).mean()
    std = prices.rolling(window=period, min_periods=period).std()
    
    upper_band = middle_band + (std * num_std)
    lower_band = middle_band - (std * num_std)
    
    return upper_band, middle_band, lower_band


def calculate_atr(high: pd.Series, low: pd.Series, close: pd.Series, 
                  period: int = 14) -> pd.Series:
    """
    Calculate Average True Range.
    
    Args:
        high: Series of high prices
        low: Series of low prices
        close: Series of closing prices
        period: Lookback period
        
    Returns:
        Series of ATR values
    """
    high_low = high - low
    high_close = (high - close.shift(1)).abs()
    low_close = (low - close.shift(1)).abs()
    
    true_range = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
    atr = true_range.rolling(window=period, min_periods=period).mean()
    
    return atr


def identify_swing_points(prices: pd.Series, order: int = 5) -> Tuple[pd.Series, pd.Series]:
    """
    Identify swing highs and swing lows.
    
    Args:
        prices: Series of prices
        order: Number of bars on each side to compare
        
    Returns:
        Tuple of (swing_highs, swing_lows) as boolean series
    """
    swing_highs = pd.Series(False, index=prices.index)
    swing_lows = pd.Series(False, index=prices.index)
    
    for i in range(order, len(prices) - order):
        window = prices.iloc[i-order:i+order+1]
        current = prices.iloc[i]
        
        if current == window.max():
            swing_highs.iloc[i] = True
        elif current == window.min():
            swing_lows.iloc[i] = True
    
    return swing_highs, swing_lows


def calculate_stochastic(high: pd.Series, low: pd.Series, close: pd.Series,
                         period: int = 14, smooth_k: int = 3, 
                         smooth_d: int = 3) -> Tuple[pd.Series, pd.Series]:
    """
    Calculate Stochastic Oscillator.
    
    Args:
        high: Series of high prices
        low: Series of low prices
        close: Series of closing prices
        period: Lookback period
        smooth_k: K smoothing period
        smooth_d: D smoothing period
        
    Returns:
        Tuple of (%K, %D)
    """
    lowest_low = low.rolling(window=period, min_periods=period).min()
    highest_high = high.rolling(window=period, min_periods=period).max()
    
    stoch = 100 * (close - lowest_low) / (highest_high - lowest_low)
    
    k = stoch.rolling(window=smooth_k, min_periods=smooth_k).mean()
    d = k.rolling(window=smooth_d, min_periods=smooth_d).mean()
    
    return k, d


def calculate_ema(prices: pd.Series, period: int) -> pd.Series:
    """
    Calculate Exponential Moving Average.
    
    Args:
        prices: Series of prices
        period: EMA period
        
    Returns:
        Series of EMA values
    """
    return prices.ewm(span=period, adjust=False).mean()


def calculate_sma(prices: pd.Series, period: int) -> pd.Series:
    """
    Calculate Simple Moving Average.
    
    Args:
        prices: Series of prices
        period: SMA period
        
    Returns:
        Series of SMA values
    """
    return prices.rolling(window=period, min_periods=period).mean()


def calculate_momentum(prices: pd.Series, period: int = 10) -> pd.Series:
    """
    Calculate price momentum.
    
    Args:
        prices: Series of prices
        period: Lookback period
        
    Returns:
        Series of momentum values
    """
    return prices.diff(period)


def calculate_roc(prices: pd.Series, period: int = 10) -> pd.Series:
    """
    Calculate Rate of Change.
    
    Args:
        prices: Series of prices
        period: Lookback period
        
    Returns:
        Series of ROC values (percentage)
    """
    return ((prices - prices.shift(period)) / prices.shift(period)) * 100


def calculate_adx(high: pd.Series, low: pd.Series, close: pd.Series,
                  period: int = 14) -> pd.Series:
    """
    Calculate Average Directional Index.
    
    Args:
        high: Series of high prices
        low: Series of low prices
        close: Series of closing prices
        period: Lookback period
        
    Returns:
        Series of ADX values
    """
    plus_dm = high.diff()
    minus_dm = -low.diff()
    
    plus_dm[plus_dm < 0] = 0
    minus_dm[minus_dm < 0] = 0
    
    atr_series = calculate_atr(high, low, close, period)
    
    plus_di = 100 * (plus_dm.rolling(window=period).mean() / atr_series)
    minus_di = 100 * (minus_dm.rolling(window=period).mean() / atr_series)
    
    dx = 100 * (plus_di - minus_di).abs() / (plus_di + minus_di)
    adx = dx.rolling(window=period).mean()
    
    return adx


def calculate_obv(close: pd.Series, volume: pd.Series) -> pd.Series:
    """
    Calculate On Balance Volume.
    
    Args:
        close: Series of closing prices
        volume: Series of volumes
        
    Returns:
        Series of OBV values
    """
    obv = pd.Series(index=close.index, dtype=float)
    obv.iloc[0] = volume.iloc[0]
    
    for i in range(1, len(close)):
        if close.iloc[i] > close.iloc[i-1]:
            obv.iloc[i] = obv.iloc[i-1] + volume.iloc[i]
        elif close.iloc[i] < close.iloc[i-1]:
            obv.iloc[i] = obv.iloc[i-1] - volume.iloc[i]
        else:
            obv.iloc[i] = obv.iloc[i-1]
    
    return obv


def calculate_williams_r(high: pd.Series, low: pd.Series, close: pd.Series,
                         period: int = 14) -> pd.Series:
    """
    Calculate Williams %R.
    
    Args:
        high: Series of high prices
        low: Series of low prices
        close: Series of closing prices
        period: Lookback period
        
    Returns:
        Series of Williams %R values (-100 to 0)
    """
    highest_high = high.rolling(window=period, min_periods=period).max()
    lowest_low = low.rolling(window=period, min_periods=period).min()
    
    williams_r = -100 * (highest_high - close) / (highest_high - lowest_low)
    
    return williams_r


def calculate_cci(high: pd.Series, low: pd.Series, close: pd.Series,
                  period: int = 20, constant: float = 0.015) -> pd.Series:
    """
    Calculate Commodity Channel Index.
    
    Args:
        high: Series of high prices
        low: Series of low prices
        close: Series of closing prices
        period: Lookback period
        constant: Scaling constant (typically 0.015)
        
    Returns:
        Series of CCI values
    """
    typical_price = (high + low + close) / 3
    sma_tp = typical_price.rolling(window=period, min_periods=period).mean()
    mean_deviation = (typical_price - sma_tp).abs().rolling(window=period, min_periods=period).mean()
    
    cci = (typical_price - sma_tp) / (constant * mean_deviation)
    
    return cci


def detect_divergence(prices: pd.Series, indicator: pd.Series, 
                      lookback: int = 20) -> pd.Series:
    """
    Detect price-indicator divergence.
    
    Args:
        prices: Series of prices
        indicator: Series of indicator values
        lookback: Period for finding local extremes
        
    Returns:
        Series with divergence signals (-1: bearish, 0: none, 1: bullish)
    """
    divergence = pd.Series(0, index=prices.index)
    
    price_highs, price_lows = identify_swing_points(prices, order=lookback//2)
    ind_highs, ind_lows = identify_swing_points(indicator, order=lookback//2)
    
    return divergence