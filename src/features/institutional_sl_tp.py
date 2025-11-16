"""
Institutional Stop Loss & Take Profit Calculation - NO ATR VERSION

ZERO TOLERANCE for ATR in operational decisions.

This module replaces ALL ATR-based stop/target logic with:
1. Percentage-based stops (% of price)
2. Structural levels (swing highs/lows, order blocks, liquidity zones)
3. R-multiple targets (based on fixed % risk)

NO ATR. Period.

Research Basis:
- Institutional risk management: Fixed % risk per trade (0-2% of capital)
- Structural analysis: Support/resistance, order blocks, liquidity
- Risk:Reward: Fixed R-multiples independent of volatility

Author: SUBLIMINE Institutional System
Version: 1.0 - ATR-FREE
"""

import numpy as np
import pandas as pd
from typing import Dict, Optional, Tuple
import logging

logger = logging.getLogger(__name__)


def calculate_stop_loss_price(
    direction: str,
    entry_price: float,
    stop_loss_pct: float,
    market_data: Optional[pd.DataFrame] = None,
    features: Optional[Dict] = None
) -> Tuple[float, str]:
    """
    Calculate stop loss price using % of entry price.

    NO ATR. Uses fixed percentage of price.

    Args:
        direction: 'LONG' or 'SHORT'
        entry_price: Entry price
        stop_loss_pct: Stop loss as % of price (e.g., 0.010 = 1.0%)
        market_data: Optional OHLCV data for structural levels
        features: Optional dict with structure (swing points, order blocks, etc.)

    Returns:
        Tuple of (stop_loss_price, stop_type)
        stop_type: 'STRUCTURAL' | 'PERCENTAGE' | 'SWING'
    """
    # Priority 1: Structural level (swing high/low)
    if market_data is not None and len(market_data) >= 20:
        structural_stop = _find_structural_stop(direction, entry_price, market_data, stop_loss_pct)
        if structural_stop is not None:
            return structural_stop, 'STRUCTURAL'

    # Priority 2: Order block / FVG (if available)
    if features is not None:
        ob_stop = _find_order_block_stop(direction, entry_price, features, stop_loss_pct)
        if ob_stop is not None:
            return ob_stop, 'ORDER_BLOCK'

    # Fallback: Percentage-based stop (ALWAYS WORKS)
    if direction == 'LONG':
        stop_price = entry_price * (1.0 - stop_loss_pct)
    else:  # SHORT
        stop_price = entry_price * (1.0 + stop_loss_pct)

    logger.info(f"Stop loss ({stop_loss_pct*100:.2f}%): {stop_price:.5f} (entry: {entry_price:.5f})")
    return stop_price, 'PERCENTAGE'


def calculate_take_profit_price(
    direction: str,
    entry_price: float,
    stop_loss_price: float,
    r_multiple: float,
    take_profit_pct: Optional[float] = None,
    market_data: Optional[pd.DataFrame] = None,
    features: Optional[Dict] = None
) -> Tuple[float, str]:
    """
    Calculate take profit price using R-multiple or fixed %.

    NO ATR. Uses either:
    - R-multiple of risk (distance from entry to stop)
    - Fixed % of price

    Args:
        direction: 'LONG' or 'SHORT'
        entry_price: Entry price
        stop_loss_price: Stop loss price
        r_multiple: R-multiple for target (e.g., 3.0 = 3R)
        take_profit_pct: Optional fixed % target (e.g., 0.020 = 2.0%)
        market_data: Optional OHLCV data for structural targets
        features: Optional dict with structure

    Returns:
        Tuple of (take_profit_price, target_type)
        target_type: 'STRUCTURAL' | 'R_MULTIPLE' | 'PERCENTAGE'
    """
    # Calculate risk amount
    risk = abs(entry_price - stop_loss_price)

    # Priority 1: Structural target (liquidity, swing extreme)
    if market_data is not None and len(market_data) >= 20:
        structural_target = _find_structural_target(direction, entry_price, market_data, risk)
        if structural_target is not None:
            return structural_target, 'STRUCTURAL'

    # Priority 2: R-multiple target
    if r_multiple is not None and r_multiple > 0:
        if direction == 'LONG':
            target_price = entry_price + (risk * r_multiple)
        else:  # SHORT
            target_price = entry_price - (risk * r_multiple)

        logger.info(f"Take profit ({r_multiple}R): {target_price:.5f} (risk: {risk:.5f})")
        return target_price, 'R_MULTIPLE'

    # Priority 3: Fixed percentage target
    if take_profit_pct is not None and take_profit_pct > 0:
        if direction == 'LONG':
            target_price = entry_price * (1.0 + take_profit_pct)
        else:  # SHORT
            target_price = entry_price * (1.0 - take_profit_pct)

        logger.info(f"Take profit ({take_profit_pct*100:.2f}%): {target_price:.5f}")
        return target_price, 'PERCENTAGE'

    # Fallback: 3R default
    if direction == 'LONG':
        target_price = entry_price + (risk * 3.0)
    else:
        target_price = entry_price - (risk * 3.0)

    logger.info(f"Take profit (3R default): {target_price:.5f}")
    return target_price, 'R_MULTIPLE'


def _find_structural_stop(
    direction: str,
    entry_price: float,
    market_data: pd.DataFrame,
    max_stop_pct: float
) -> Optional[float]:
    """
    Find structural stop loss using swing highs/lows.

    Places stop beyond the nearest swing point, but respects max % limit.

    Args:
        direction: 'LONG' or 'SHORT'
        entry_price: Entry price
        market_data: OHLCV data
        max_stop_pct: Maximum stop distance as % of price

    Returns:
        Stop price or None if not found
    """
    lookback = min(50, len(market_data))
    recent_data = market_data.tail(lookback)

    max_stop_distance = entry_price * max_stop_pct
    buffer_pips = 0.0002  # 2 pips buffer

    if direction == 'LONG':
        # Find recent swing low
        swing_low = recent_data['low'].min()

        # Check if swing low is below entry
        if swing_low < entry_price:
            # Place stop below swing low
            stop_price = swing_low - buffer_pips

            # Verify it doesn't exceed max % stop
            stop_distance = entry_price - stop_price
            if stop_distance <= max_stop_distance:
                logger.info(f"Structural stop (swing low): {stop_price:.5f} (swing: {swing_low:.5f})")
                return stop_price

    else:  # SHORT
        # Find recent swing high
        swing_high = recent_data['high'].max()

        # Check if swing high is above entry
        if swing_high > entry_price:
            # Place stop above swing high
            stop_price = swing_high + buffer_pips

            # Verify it doesn't exceed max % stop
            stop_distance = stop_price - entry_price
            if stop_distance <= max_stop_distance:
                logger.info(f"Structural stop (swing high): {stop_price:.5f} (swing: {swing_high:.5f})")
                return stop_price

    return None


def _find_order_block_stop(
    direction: str,
    entry_price: float,
    features: Dict,
    max_stop_pct: float
) -> Optional[float]:
    """
    Find stop loss using order block levels.

    Args:
        direction: 'LONG' or 'SHORT'
        entry_price: Entry price
        features: Dict containing order_blocks
        max_stop_pct: Maximum stop distance as % of price

    Returns:
        Stop price or None
    """
    order_blocks = features.get('order_blocks', [])
    if not order_blocks:
        return None

    max_stop_distance = entry_price * max_stop_pct
    buffer_pips = 0.0002  # 2 pips buffer

    if direction == 'LONG':
        # Find nearest bullish order block below entry
        valid_obs = [
            ob for ob in order_blocks
            if ob.get('type') == 'BULLISH' and ob.get('low', 0) < entry_price
        ]

        if valid_obs:
            closest_ob = max(valid_obs, key=lambda x: x.get('low', 0))
            ob_low = closest_ob.get('low', 0)

            # Place stop below order block
            stop_price = ob_low - buffer_pips

            # Verify max % stop
            stop_distance = entry_price - stop_price
            if stop_distance <= max_stop_distance:
                logger.info(f"Order block stop: {stop_price:.5f} (OB low: {ob_low:.5f})")
                return stop_price

    else:  # SHORT
        # Find nearest bearish order block above entry
        valid_obs = [
            ob for ob in order_blocks
            if ob.get('type') == 'BEARISH' and ob.get('high', 999999) > entry_price
        ]

        if valid_obs:
            closest_ob = min(valid_obs, key=lambda x: x.get('high', 999999))
            ob_high = closest_ob.get('high', 999999)

            # Place stop above order block
            stop_price = ob_high + buffer_pips

            # Verify max % stop
            stop_distance = stop_price - entry_price
            if stop_distance <= max_stop_distance:
                logger.info(f"Order block stop: {stop_price:.5f} (OB high: {ob_high:.5f})")
                return stop_price

    return None


def _find_structural_target(
    direction: str,
    entry_price: float,
    market_data: pd.DataFrame,
    risk: float
) -> Optional[float]:
    """
    Find structural target using swing extremes and liquidity levels.

    Targets nearest swing extreme that offers at least 2R potential.

    Args:
        direction: 'LONG' or 'SHORT'
        entry_price: Entry price
        market_data: OHLCV data
        risk: Risk amount (distance from entry to stop)

    Returns:
        Target price or None
    """
    lookback = min(100, len(market_data))
    recent_data = market_data.tail(lookback)

    min_target_distance = risk * 2.0  # Minimum 2R target

    if direction == 'LONG':
        # Find swing highs above entry
        swing_high = recent_data['high'].max()

        # Check if swing high offers at least 2R
        potential_gain = swing_high - entry_price
        if potential_gain >= min_target_distance:
            # Target just before swing high (don't overshoot)
            target_price = swing_high - (risk * 0.05)  # 5% buffer before swing
            logger.info(f"Structural target (swing high): {target_price:.5f} (swing: {swing_high:.5f})")
            return target_price

    else:  # SHORT
        # Find swing lows below entry
        swing_low = recent_data['low'].min()

        # Check if swing low offers at least 2R
        potential_gain = entry_price - swing_low
        if potential_gain >= min_target_distance:
            # Target just before swing low
            target_price = swing_low + (risk * 0.05)
            logger.info(f"Structural target (swing low): {target_price:.5f} (swing: {swing_low:.5f})")
            return target_price

    return None


def calculate_position_size(
    account_balance: float,
    risk_pct: float,
    entry_price: float,
    stop_loss_price: float,
    contract_size: float = 100000,
    symbol: str = "UNKNOWN"
) -> Tuple[float, float]:
    """
    Calculate position size based on fixed % risk.

    NO ATR. Uses fixed % of account balance.

    Args:
        account_balance: Total account balance
        risk_pct: Risk as % of account (e.g., 0.02 = 2%)
        entry_price: Entry price
        stop_loss_price: Stop loss price
        contract_size: Contract size (100000 for standard lot)
        symbol: Trading symbol (for logging)

    Returns:
        Tuple of (position_size_lots, risk_amount_dollars)
    """
    # Calculate risk amount in dollars
    risk_amount = account_balance * risk_pct

    # Calculate price distance
    price_distance = abs(entry_price - stop_loss_price)

    # Calculate position size in lots
    # risk_amount = lots * contract_size * price_distance
    # lots = risk_amount / (contract_size * price_distance)
    if price_distance > 0:
        position_size_lots = risk_amount / (contract_size * price_distance)
    else:
        position_size_lots = 0.01  # Minimum position

    logger.info(f"{symbol}: Position size {position_size_lots:.2f} lots "
                f"(risk: ${risk_amount:.2f}, {risk_pct*100:.1f}% of account)")

    return position_size_lots, risk_amount


def calculate_partial_exit_levels(
    direction: str,
    entry_price: float,
    stop_loss_price: float,
    final_target: float,
    partial_levels: Optional[list] = None
) -> list:
    """
    Calculate partial exit levels for scaling out of positions.

    Default levels: 50% at 1.5R, 30% at 2.5R, 20% runs to final target.

    Args:
        direction: 'LONG' or 'SHORT'
        entry_price: Entry price
        stop_loss_price: Stop loss price
        final_target: Final take profit target
        partial_levels: Optional custom partial levels [(r_multiple, pct_close), ...]

    Returns:
        List of dicts: [{'price': float, 'pct_close': float, 'r_multiple': float}, ...]
    """
    risk = abs(entry_price - stop_loss_price)

    # Default partial levels
    if partial_levels is None:
        partial_levels = [
            (1.5, 0.50),  # 50% at 1.5R
            (2.5, 0.30),  # 30% at 2.5R
            # Remaining 20% runs to final target
        ]

    exit_levels = []

    for r_multiple, pct_close in partial_levels:
        if direction == 'LONG':
            exit_price = entry_price + (risk * r_multiple)
        else:  # SHORT
            exit_price = entry_price - (risk * r_multiple)

        exit_levels.append({
            'price': exit_price,
            'pct_close': pct_close,
            'r_multiple': r_multiple
        })

    # Add final target
    final_r = abs(final_target - entry_price) / risk
    exit_levels.append({
        'price': final_target,
        'pct_close': 1.0 - sum(pct for _, pct in partial_levels),  # Remaining %
        'r_multiple': final_r
    })

    logger.info(f"Partial exits: {len(exit_levels)} levels")
    for level in exit_levels:
        logger.info(f"  {level['pct_close']*100:.0f}% at {level['price']:.5f} ({level['r_multiple']:.1f}R)")

    return exit_levels
