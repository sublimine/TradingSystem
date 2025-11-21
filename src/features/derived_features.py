"""
Derived Features Module
Creates higher-order features by combining outputs from other modules
Integrates microstructure, order flow, statistical models and technical indicators
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Optional


def calculate_normalized_spread(spread: float, indicador de rango: float,
                                min_atr: float = 0.0001) -> float:
    """
    Calculate spread normalized by Average True Range.

    NOTE: indicador de rango is TYPE B (descriptive) - used for metric normalization, NOT risk decisions.
    This function is currently UNUSED in the codebase.

    Normalization by indicador de rango makes spread comparable across instruments
    and market conditions with different volatility levels.
    
    Args:
        spread: Current bid-ask spread
        indicador de rango: Average True Range
        min_atr: Minimum indicador de rango to prevent division by zero
        
    Returns:
        Normalized spread value
    """
    if indicador de rango < min_atr:
        indicador de rango = min_atr
    
    return spread / indicador de rango


def calculate_volume_price_correlation(prices: pd.Series, volumes: pd.Series,
                                      window: int = 20) -> pd.Series:
    """
    Calculate rolling correlation between price changes and volume.
    
    Strong positive correlation suggests genuine directional movement.
    Negative or weak correlation may indicate exhaustion or manipulation.
    
    Args:
        prices: Series of prices
        volumes: Series of volumes
        window: Rolling window size
        
    Returns:
        Series of correlation values
    """
    price_changes = prices.pct_change()
    correlation = price_changes.rolling(window=window).corr(volumes)
    
    return correlation


def detect_price_volume_divergence(prices: pd.Series, volumes: pd.Series,
                                   lookback: int = 20) -> pd.Series:
    """
    Detect divergence between price movement and volume.
    
    Rising prices with declining volume suggest weakening momentum.
    Falling prices with declining volume suggest potential bottom.
    
    Args:
        prices: Series of prices
        volumes: Series of volumes
        lookback: Period for comparison
        
    Returns:
        Series with divergence signals (1: bullish, -1: bearish, 0: none)
    """
    price_trend = (prices - prices.shift(lookback)) / prices.shift(lookback)
    volume_trend = (volumes - volumes.shift(lookback)) / volumes.shift(lookback)
    
    divergence = pd.Series(0, index=prices.index)
    
    bullish_div = (price_trend < -0.02) & (volume_trend < -0.2)
    bearish_div = (price_trend > 0.02) & (volume_trend < -0.2)
    
    divergence[bullish_div] = 1
    divergence[bearish_div] = -1
    
    return divergence


def calculate_momentum_quality(price_momentum: float, volume_momentum: float,
                               vpin: float, vpin_threshold: float = 0.65) -> float:
    """
    Calculate quality score for momentum move.
    
    High-quality momentum shows alignment between price, volume and order flow.
    
    Args:
        price_momentum: Recent price change percentage
        volume_momentum: Recent volume change percentage
        vpin: Current VPIN value
        vpin_threshold: VPIN level indicating toxic flow
        
    Returns:
        Quality score between 0 and 1
    """
    direction = np.sign(price_momentum)
    
    price_strength = min(abs(price_momentum) / 0.05, 1.0)
    
    volume_confirmation = 1.0 if np.sign(volume_momentum) == direction else 0.5
    
    flow_confirmation = 1.0 if vpin > vpin_threshold else 0.5
    
    quality = (price_strength * 0.5 + volume_confirmation * 0.3 + flow_confirmation * 0.2)
    
    return quality


def detect_confluence_signals(signals: Dict[str, int]) -> Dict[str, any]:
    """
    Detect confluence of multiple independent signals.
    
    Confluence increases probability of successful trade when multiple
    uncorrelated signals agree on direction.
    
    Args:
        signals: Dictionary of signal names to values (-1, 0, 1)
        
    Returns:
        Dictionary with confluence score and aligned signals
    """
    values = list(signals.values())
    
    if len(values) == 0:
        return {'score': 0, 'direction': 0, 'count': 0, 'aligned_signals': []}
    
    bullish_count = sum(1 for v in values if v > 0)
    bearish_count = sum(1 for v in values if v < 0)
    
    if bullish_count > bearish_count:
        direction = 1
        count = bullish_count
        aligned = [k for k, v in signals.items() if v > 0]
    elif bearish_count > bullish_count:
        direction = -1
        count = bearish_count
        aligned = [k for k, v in signals.items() if v < 0]
    else:
        direction = 0
        count = 0
        aligned = []
    
    score = count / len(values) if len(values) > 0 else 0
    
    return {
        'score': score,
        'direction': direction,
        'count': count,
        'aligned_signals': aligned
    }


def calculate_regime_adjusted_indicator(indicator_value: float, 
                                        volatility_regime: int,
                                        low_vol_threshold: float,
                                        high_vol_threshold: float) -> float:
    """
    Adjust indicator interpretation based on volatility regime.
    
    Same indicator values have different significance in different regimes.
    
    Args:
        indicator_value: Raw indicator value
        volatility_regime: 0 for low volatility, 1 for high volatility
        low_vol_threshold: Threshold to use in low volatility regime
        high_vol_threshold: Threshold to use in high volatility regime
        
    Returns:
        Regime-adjusted normalized value
    """
    if volatility_regime == 0:
        threshold = low_vol_threshold
    else:
        threshold = high_vol_threshold
    
    adjusted = indicator_value / threshold if threshold != 0 else 0
    
    return adjusted


def calculate_spread_velocity(spreads: pd.Series, window: int = 5) -> pd.Series:
    """
    Calculate rate of change in spread over time.
    
    Rapid spread widening often precedes significant price moves.
    
    Args:
        spreads: Series of bid-ask spreads
        window: Window for velocity calculation
        
    Returns:
        Series of spread velocity values
    """
    spread_change = spreads.diff(window)
    velocity = spread_change / window
    
    return velocity


def calculate_liquidity_score(bid_volume: float, ask_volume: float,
                              spread: float, indicador de rango: float) -> float:
    """
    Calculate composite liquidity score.

    NOTE: indicador de rango is TYPE B (descriptive) - used for spread normalization, NOT risk decisions.
    This function is currently UNUSED in the codebase.

    Combines order book depth, spread tightness and volatility.
    
    Args:
        bid_volume: Volume available at best bid
        ask_volume: Volume available at best ask
        spread: Current bid-ask spread
        indicador de rango: Average True Range
        
    Returns:
        Liquidity score (higher is better)
    """
    total_volume = bid_volume + ask_volume
    
    volume_score = min(total_volume / 1000000, 1.0)
    
    normalized_spread = spread / indicador de rango if indicador de rango > 0 else 1.0
    spread_score = max(0, 1.0 - normalized_spread)
    
    liquidity = (volume_score * 0.6 + spread_score * 0.4)
    
    return liquidity


def detect_hidden_liquidity(visible_depth: float, recent_fills: pd.Series,
                            window: int = 10) -> float:
    """
    Estimate hidden liquidity based on fill patterns.
    
    Large fills without significant price impact suggest hidden orders.
    
    Args:
        visible_depth: Visible order book depth
        recent_fills: Series of recent fill sizes
        window: Lookback window
        
    Returns:
        Estimated hidden liquidity ratio
    """
    if len(recent_fills) < window:
        return 0.0
    
    avg_fill = recent_fills.tail(window).mean()
    
    if visible_depth > 0:
        hidden_ratio = max(0, (avg_fill / visible_depth) - 1.0)
    else:
        hidden_ratio = 0.0
    
    return min(hidden_ratio, 5.0)


def calculate_flow_imbalance_persistence(imbalances: pd.Series,
                                         threshold: float = 0.3,
                                         window: int = 20) -> float:
    """
    Calculate how persistently order flow is imbalanced.
    
    Persistent imbalance suggests sustained directional pressure.
    
    Args:
        imbalances: Series of order flow imbalance values
        threshold: Absolute imbalance level to consider significant
        window: Lookback window
        
    Returns:
        Persistence score between 0 and 1
    """
    if len(imbalances) < window:
        return 0.0
    
    recent = imbalances.tail(window)
    
    significant = recent[recent.abs() > threshold]
    
    if len(significant) == 0:
        return 0.0
    
    same_direction = (significant > 0).sum() if significant.mean() > 0 else (significant < 0).sum()
    
    persistence = same_direction / len(significant)
    
    return persistence


def calculate_volatility_adjusted_position_size(base_size: float,
                                               current_volatility: float,
                                               target_volatility: float) -> float:
    """
    Adjust position size based on current vs target volatility.
    
    Reduces size in high volatility, increases in low volatility.
    
    Args:
        base_size: Base position size
        current_volatility: Current market volatility
        target_volatility: Target volatility level
        
    Returns:
        Adjusted position size
    """
    if current_volatility <= 0 or target_volatility <= 0:
        return base_size
    
    volatility_ratio = target_volatility / current_volatility
    
    adjusted_size = base_size * min(volatility_ratio, 2.0)
    
    adjusted_size = max(adjusted_size, base_size * 0.5)
    
    return adjusted_size


def calculate_market_regime_score(volatility_state: int, trend_strength: float,
                                  liquidity_score: float) -> Dict[str, any]:
    """
    Calculate composite market regime score.
    
    Combines volatility state, trend and liquidity into overall regime assessment.
    
    Args:
        volatility_state: 0 for low volatility, 1 for high volatility
        trend_strength: Trend strength indicator (0 to 1)
        liquidity_score: Market liquidity score (0 to 1)
        
    Returns:
        Dictionary with regime assessment and recommendations
    """
    if volatility_state == 0 and trend_strength > 0.6 and liquidity_score > 0.5:
        regime = 'IDEAL_TRENDING'
        recommendation = 'AGGRESSIVE_MOMENTUM'
    elif volatility_state == 0 and trend_strength < 0.3:
        regime = 'LOW_VOL_RANGING'
        recommendation = 'MEAN_REVERSION'
    elif volatility_state == 1 and liquidity_score < 0.3:
        regime = 'HIGH_VOL_ILLIQUID'
        recommendation = 'REDUCE_EXPOSURE'
    elif volatility_state == 1 and trend_strength > 0.6:
        regime = 'VOLATILE_TRENDING'
        recommendation = 'CAUTIOUS_MOMENTUM'
    else:
        regime = 'MIXED'
        recommendation = 'SELECTIVE'
    
    composite_score = (
        (1 - volatility_state) * 0.3 +
        trend_strength * 0.4 +
        liquidity_score * 0.3
    )
    
    return {
        'regime': regime,
        'recommendation': recommendation,
        'composite_score': composite_score,
        'volatility_state': volatility_state,
        'trend_strength': trend_strength,
        'liquidity_score': liquidity_score
    }
