"""
Market Microstructure Features Module
Calculates features related to order book dynamics and market microstructure
"""

import numpy as np
import pandas as pd
from typing import Tuple, Optional


def calculate_microprice(bid: float, ask: float, bid_volume: float, ask_volume: float) -> float:
    """
    Calculate volume-weighted microprice.
    
    Microprice provides better estimate of true price than simple mid-price
    by weighting bid and ask by their respective volumes.
    
    Args:
        bid: Best bid price
        ask: Best ask price
        bid_volume: Volume available at best bid
        ask_volume: Volume available at best ask
        
    Returns:
        Volume-weighted microprice
        
    Formula:
        microprice = (ask * bid_volume + bid * ask_volume) / (bid_volume + ask_volume)
    """
    if bid_volume <= 0 or ask_volume <= 0:
        return (bid + ask) / 2
    
    total_volume = bid_volume + ask_volume
    microprice = (ask * bid_volume + bid * ask_volume) / total_volume
    
    return microprice


def calculate_mid_price(bid: float, ask: float) -> float:
    """
    Calculate simple mid price between bid and ask.
    
    Args:
        bid: Best bid price
        ask: Best ask price
        
    Returns:
        Mid price
    """
    return (bid + ask) / 2


def calculate_spread(bid: float, ask: float, in_percentage: bool = False) -> float:
    """
    Calculate bid-ask spread.
    
    Args:
        bid: Best bid price
        ask: Best ask price
        in_percentage: If True, return spread as percentage of mid price
        
    Returns:
        Bid-ask spread (absolute or percentage)
    """
    spread_abs = ask - bid
    
    if in_percentage:
        mid_price = (bid + ask) / 2
        if mid_price > 0:
            return (spread_abs / mid_price) * 100
        return 0
    
    return spread_abs


def calculate_effective_spread(trade_price: float, microprice: float, 
                               trade_direction: int) -> float:
    """
    Calculate effective spread paid by aggressive trader.
    
    Args:
        trade_price: Price at which trade executed
        microprice: Microprice at time of trade
        trade_direction: 1 for buy, -1 for sell
        
    Returns:
        Effective spread in price units
        
    Formula:
        effective_spread = 2 * trade_direction * (trade_price - microprice)
    """
    return 2 * trade_direction * (trade_price - microprice)


def classify_trade_direction(price: float, prev_price: float, 
                             bid: float, ask: float) -> int:
    """
    Classify trade as buyer-initiated or seller-initiated using tick rule.
    
    Args:
        price: Current trade price
        prev_price: Previous trade price
        bid: Current best bid
        ask: Current best ask
        
    Returns:
        1 for buyer-initiated, -1 for seller-initiated, 0 if indeterminate
    """
    mid_price = (bid + ask) / 2
    
    if price > mid_price:
        return 1
    elif price < mid_price:
        return -1
    elif price > prev_price:
        return 1
    elif price < prev_price:
        return -1
    else:
        return 0


def calculate_order_book_imbalance(bid_volume: float, ask_volume: float) -> float:
    """
    Calculate order book imbalance ratio.
    
    Args:
        bid_volume: Total volume on bid side
        ask_volume: Total volume on ask side
        
    Returns:
        Imbalance ratio between -1 and 1
        
    Formula:
        imbalance = (bid_volume - ask_volume) / (bid_volume + ask_volume)
        
    Interpretation:
        > 0: More buying pressure
        < 0: More selling pressure
        Close to 0: Balanced book
    """
    total_volume = bid_volume + ask_volume
    
    if total_volume == 0:
        return 0
    
    imbalance = (bid_volume - ask_volume) / total_volume
    return imbalance


def calculate_depth_weighted_price(prices: np.ndarray, volumes: np.ndarray) -> float:
    """
    Calculate volume-weighted average price across multiple depth levels.
    
    Args:
        prices: Array of prices at different depth levels
        volumes: Array of volumes at corresponding price levels
        
    Returns:
        Volume-weighted average price
    """
    if len(prices) == 0 or len(volumes) == 0 or np.sum(volumes) == 0:
        return 0
    
    return np.average(prices, weights=volumes)


def calculate_roll_measure(prices: pd.Series) -> float:
    """
    Calculate Roll's measure of effective spread from price series.
    
    Roll's measure estimates bid-ask spread from serial covariance of price changes.
    
    Args:
        prices: Series of transaction prices
        
    Returns:
        Estimated effective spread
        
    Formula:
        spread = 2 * sqrt(-cov(delta_p_t, delta_p_t-1))
        where delta_p_t is the price change at time t
    """
    if len(prices) < 3:
        return 0
    
    price_changes = prices.diff().dropna()
    
    if len(price_changes) < 2:
        return 0
    
    covariance = price_changes.autocorr(lag=1) * price_changes.var()
    
    if covariance >= 0:
        return 0
    
    spread_estimate = 2 * np.sqrt(-covariance)
    return spread_estimate


def calculate_price_impact(trade_volume: float, avg_volume: float, 
                          volatility: float, liquidity_factor: float = 0.1) -> float:
    """
    Estimate price impact of a trade based on volume and market conditions.
    
    Args:
        trade_volume: Size of trade in base currency units
        avg_volume: Average trade volume in recent period
        volatility: Recent price volatility (e.g., ATR)
        liquidity_factor: Market-specific liquidity constant
        
    Returns:
        Estimated price impact in price units
        
    Formula:
        impact = liquidity_factor * volatility * (trade_volume / avg_volume)^0.5
    """
    if avg_volume <= 0 or trade_volume <= 0:
        return 0
    
    volume_ratio = trade_volume / avg_volume
    impact = liquidity_factor * volatility * np.sqrt(volume_ratio)
    
    return impact