"""
Strategic Stop Loss Placement - ELITE Institutional Implementation

Stops placed at STRUCTURAL levels, NOT arbitrary ATR multipliers.

Stop placement hierarchy (best to worst):
1. Order Block boundary + buffer
2. Fair Value Gap (FVG) edge + buffer
3. Swing high/low + buffer
4. ATR-based fallback (only if no structure available)

Trailing stops:
- Move to breakeven after 1R captured
- Trail using structure levels (swing highs/lows)
- Accelerate trail in profit zones

Research Basis:
- Wyckoff Method: Support/Resistance as institutional footprints
- Smart Money Concepts: Order blocks mark institutional zones
- Risk management: Place stops where institutions would defend

Author: Elite Trading System
Version: 1.0
"""

import numpy as np
import pandas as pd
from typing import Dict, Optional, Tuple
import logging

logger = logging.getLogger(__name__)


def calculate_strategic_stop(
    direction: str,
    entry_price: float,
    market_data: pd.DataFrame,
    features: Dict,
    atr_fallback: float,
    buffer_multiplier: float = 1.2
) -> Tuple[float, str]:
    """
    Calculate strategic stop loss using structure.

    Args:
        direction: 'LONG' or 'SHORT'
        entry_price: Entry price level
        market_data: Recent OHLCV data
        features: Dict containing structure data (order_blocks, fvgs, etc.)
        atr_fallback: ATR value for fallback calculation
        buffer_multiplier: Buffer beyond structure (typically 1.2 = 20%)

    Returns:
        Tuple of (stop_loss_price, stop_type)
        stop_type: 'ORDER_BLOCK' | 'FVG' | 'SWING' | 'ATR_FALLBACK'
    """
    # Priority 1: Order Block
    ob_stop = _find_order_block_stop(direction, entry_price, features, atr_fallback, buffer_multiplier)
    if ob_stop is not None:
        return ob_stop, 'ORDER_BLOCK'

    # Priority 2: Fair Value Gap
    fvg_stop = _find_fvg_stop(direction, entry_price, features, atr_fallback, buffer_multiplier)
    if fvg_stop is not None:
        return fvg_stop, 'FVG'

    # Priority 3: Swing High/Low
    swing_stop = _find_swing_stop(direction, entry_price, market_data, atr_fallback, buffer_multiplier)
    if swing_stop is not None:
        return swing_stop, 'SWING'

    # Fallback: ATR-based
    atr_stop = _calculate_atr_fallback(direction, entry_price, atr_fallback)
    return atr_stop, 'ATR_FALLBACK'


def _find_order_block_stop(direction: str, entry_price: float, features: Dict,
                           atr: float, buffer: float) -> Optional[float]:
    """
    Find nearest order block for stop placement.

    Order blocks = zones where large institutional orders were filled.
    Institutions will defend these zones.
    """
    order_blocks = features.get('order_blocks', [])

    if not order_blocks:
        return None

    if direction == 'LONG':
        # Find highest bullish order block BELOW entry
        valid_obs = [
            ob for ob in order_blocks
            if ob.get('type') == 'BULLISH' and ob.get('low', 0) < entry_price
        ]

        if valid_obs:
            # Take closest OB below entry
            closest_ob = max(valid_obs, key=lambda x: x.get('low', 0))
            ob_low = closest_ob.get('low', 0)

            # Place stop below OB with buffer
            stop = ob_low - (atr * buffer * 0.5)  # 50% of buffer below OB
            logger.info(f"✓ Order Block stop: {stop:.5f} (OB low: {ob_low:.5f})")
            return stop

    else:  # SHORT
        # Find lowest bearish order block ABOVE entry
        valid_obs = [
            ob for ob in order_blocks
            if ob.get('type') == 'BEARISH' and ob.get('high', 999999) > entry_price
        ]

        if valid_obs:
            # Take closest OB above entry
            closest_ob = min(valid_obs, key=lambda x: x.get('high', 999999))
            ob_high = closest_ob.get('high', 999999)

            # Place stop above OB with buffer
            stop = ob_high + (atr * buffer * 0.5)
            logger.info(f"✓ Order Block stop: {stop:.5f} (OB high: {ob_high:.5f})")
            return stop

    return None


def _find_fvg_stop(direction: str, entry_price: float, features: Dict,
                  atr: float, buffer: float) -> Optional[float]:
    """
    Find nearest Fair Value Gap for stop placement.

    FVGs = price gaps without transactions, institutional inefficiencies.
    """
    fvgs = features.get('fvgs', [])

    if not fvgs:
        return None

    if direction == 'LONG':
        # Find FVG below entry
        valid_fvgs = [
            fvg for fvg in fvgs
            if fvg.get('low', 0) < entry_price
        ]

        if valid_fvgs:
            closest_fvg = max(valid_fvgs, key=lambda x: x.get('low', 0))
            fvg_low = closest_fvg.get('low', 0)

            stop = fvg_low - (atr * buffer * 0.3)  # 30% of buffer below FVG
            logger.info(f"✓ FVG stop: {stop:.5f} (FVG low: {fvg_low:.5f})")
            return stop

    else:  # SHORT
        # Find FVG above entry
        valid_fvgs = [
            fvg for fvg in fvgs
            if fvg.get('high', 999999) > entry_price
        ]

        if valid_fvgs:
            closest_fvg = min(valid_fvgs, key=lambda x: x.get('high', 999999))
            fvg_high = closest_fvg.get('high', 999999)

            stop = fvg_high + (atr * buffer * 0.3)
            logger.info(f"✓ FVG stop: {stop:.5f} (FVG high: {fvg_high:.5f})")
            return stop

    return None


def _find_swing_stop(direction: str, entry_price: float, market_data: pd.DataFrame,
                    atr: float, buffer: float) -> Optional[float]:
    """
    Find swing high/low for stop placement.

    Swing points = local extremes where price reversed.
    """
    lookback = min(50, len(market_data))
    recent_data = market_data.tail(lookback)

    if direction == 'LONG':
        # Find recent swing low
        lows = recent_data['low'].values

        # Simple swing low: lowest point in window
        swing_low = np.min(lows)

        if swing_low < entry_price:
            stop = swing_low - (atr * buffer * 0.4)  # 40% of buffer below swing
            logger.info(f"✓ Swing stop: {stop:.5f} (Swing low: {swing_low:.5f})")
            return stop

    else:  # SHORT
        # Find recent swing high
        highs = recent_data['high'].values

        # Simple swing high: highest point in window
        swing_high = np.max(highs)

        if swing_high > entry_price:
            stop = swing_high + (atr * buffer * 0.4)
            logger.info(f"✓ Swing stop: {stop:.5f} (Swing high: {swing_high:.5f})")
            return stop

    return None


def _calculate_atr_fallback(direction: str, entry_price: float, atr: float) -> float:
    """
    Fallback ATR-based stop (only when no structure available).

    Uses 2.0 ATR as conservative default.
    """
    if direction == 'LONG':
        stop = entry_price - (atr * 2.0)
    else:
        stop = entry_price + (atr * 2.0)

    logger.warning(f"⚠️  ATR fallback stop used: {stop:.5f} (no structure available)")
    return stop


def calculate_strategic_target(
    direction: str,
    entry_price: float,
    stop_loss: float,
    market_data: pd.DataFrame,
    features: Dict,
    default_rr: float = 3.0
) -> Tuple[float, str]:
    """
    Calculate strategic take profit using structure or R:R.

    Args:
        direction: 'LONG' or 'SHORT'
        entry_price: Entry price
        stop_loss: Stop loss price
        market_data: Recent OHLCV data
        features: Dict containing structure data
        default_rr: Default risk:reward ratio if no structure found

    Returns:
        Tuple of (take_profit_price, target_type)
        target_type: 'ORDER_BLOCK' | 'FVG' | 'SWING' | 'RR_DEFAULT'
    """
    risk = abs(entry_price - stop_loss)

    # Priority 1: Opposite Order Block
    ob_target = _find_order_block_target(direction, entry_price, features, risk)
    if ob_target is not None:
        return ob_target, 'ORDER_BLOCK'

    # Priority 2: Opposite FVG
    fvg_target = _find_fvg_target(direction, entry_price, features, risk)
    if fvg_target is not None:
        return fvg_target, 'FVG'

    # Priority 3: Swing extreme
    swing_target = _find_swing_target(direction, entry_price, market_data, risk)
    if swing_target is not None:
        return swing_target, 'SWING'

    # Fallback: R:R ratio
    if direction == 'LONG':
        target = entry_price + (risk * default_rr)
    else:
        target = entry_price - (risk * default_rr)

    logger.info(f"ℹ️  R:R target: {target:.5f} ({default_rr}R)")
    return target, 'RR_DEFAULT'


def _find_order_block_target(direction: str, entry_price: float, features: Dict,
                             risk: float) -> Optional[float]:
    """Find opposite-side order block for target."""
    order_blocks = features.get('order_blocks', [])

    if direction == 'LONG':
        # Find bearish OB above entry (resistance)
        valid_obs = [
            ob for ob in order_blocks
            if ob.get('type') == 'BEARISH' and ob.get('low', 999999) > entry_price
        ]

        if valid_obs:
            closest_ob = min(valid_obs, key=lambda x: x.get('low', 999999))
            ob_low = closest_ob.get('low', 999999)

            # Target just before OB (don't overshoot)
            target = ob_low - (risk * 0.1)  # 10% buffer before OB
            logger.info(f"✓ Order Block target: {target:.5f} (OB low: {ob_low:.5f})")
            return target

    else:  # SHORT
        # Find bullish OB below entry (support)
        valid_obs = [
            ob for ob in order_blocks
            if ob.get('type') == 'BULLISH' and ob.get('high', 0) < entry_price
        ]

        if valid_obs:
            closest_ob = max(valid_obs, key=lambda x: x.get('high', 0))
            ob_high = closest_ob.get('high', 0)

            target = ob_high + (risk * 0.1)
            logger.info(f"✓ Order Block target: {target:.5f} (OB high: {ob_high:.5f})")
            return target

    return None


def _find_fvg_target(direction: str, entry_price: float, features: Dict,
                    risk: float) -> Optional[float]:
    """Find FVG for target."""
    fvgs = features.get('fvgs', [])

    if direction == 'LONG':
        valid_fvgs = [
            fvg for fvg in fvgs
            if fvg.get('low', 999999) > entry_price
        ]

        if valid_fvgs:
            closest_fvg = min(valid_fvgs, key=lambda x: x.get('low', 999999))
            fvg_low = closest_fvg.get('low', 999999)

            target = fvg_low - (risk * 0.05)
            logger.info(f"✓ FVG target: {target:.5f}")
            return target

    else:  # SHORT
        valid_fvgs = [
            fvg for fvg in fvgs
            if fvg.get('high', 0) < entry_price
        ]

        if valid_fvgs:
            closest_fvg = max(valid_fvgs, key=lambda x: x.get('high', 0))
            fvg_high = closest_fvg.get('high', 0)

            target = fvg_high + (risk * 0.05)
            logger.info(f"✓ FVG target: {target:.5f}")
            return target

    return None


def _find_swing_target(direction: str, entry_price: float, market_data: pd.DataFrame,
                      risk: float) -> Optional[float]:
    """Find swing extreme for target."""
    lookback = min(100, len(market_data))
    recent_data = market_data.tail(lookback)

    if direction == 'LONG':
        highs = recent_data['high'].values
        swing_high = np.max(highs)

        if swing_high > entry_price + risk:  # At least 1R potential
            target = swing_high - (risk * 0.1)  # 10% buffer
            logger.info(f"✓ Swing target: {target:.5f} (Swing high: {swing_high:.5f})")
            return target

    else:  # SHORT
        lows = recent_data['low'].values
        swing_low = np.min(lows)

        if swing_low < entry_price - risk:
            target = swing_low + (risk * 0.1)
            logger.info(f"✓ Swing target: {target:.5f} (Swing low: {swing_low:.5f})")
            return target

    return None


def calculate_trailing_stop(
    direction: str,
    entry_price: float,
    current_price: float,
    current_stop: float,
    market_data: pd.DataFrame,
    profit_captured_r: float
) -> float:
    """
    Calculate trailing stop based on profit captured.

    Trailing logic:
    - At 1R profit: Move to breakeven
    - At 2R profit: Trail at 50% retracement (lock 1R)
    - At 3R+ profit: Trail using swing points

    Args:
        direction: 'LONG' or 'SHORT'
        entry_price: Original entry price
        current_price: Current market price
        current_stop: Current stop loss
        market_data: Recent OHLCV data
        profit_captured_r: How many R captured (e.g., 2.5 = 2.5R profit)

    Returns:
        Updated stop loss price
    """
    risk = abs(entry_price - current_stop)

    # Stage 1: Move to breakeven at 1R
    if profit_captured_r >= 1.0:
        if direction == 'LONG':
            new_stop = max(current_stop, entry_price + (risk * 0.05))  # BE + 5% buffer
        else:
            new_stop = min(current_stop, entry_price - (risk * 0.05))

        if new_stop != current_stop:
            logger.info(f"🔒 Trailing to breakeven: {new_stop:.5f} (profit={profit_captured_r:.1f}R)")
            return new_stop

    # Stage 2: 50% retracement at 2R
    if profit_captured_r >= 2.0:
        if direction == 'LONG':
            fifty_pct = entry_price + ((current_price - entry_price) * 0.5)
            new_stop = max(current_stop, fifty_pct)
        else:
            fifty_pct = entry_price - ((entry_price - current_price) * 0.5)
            new_stop = min(current_stop, fifty_pct)

        if new_stop != current_stop:
            logger.info(f"🔒 Trailing 50% retracement: {new_stop:.5f} (profit={profit_captured_r:.1f}R)")
            return new_stop

    # Stage 3: Swing-based trailing at 3R+
    if profit_captured_r >= 3.0:
        recent_data = market_data.tail(10)

        if direction == 'LONG':
            recent_low = recent_data['low'].min()
            swing_trail = recent_low - (risk * 0.3)  # 30% buffer below recent low
            new_stop = max(current_stop, swing_trail)
        else:
            recent_high = recent_data['high'].max()
            swing_trail = recent_high + (risk * 0.3)
            new_stop = min(current_stop, swing_trail)

        if new_stop != current_stop:
            logger.info(f"🔒 Trailing swing: {new_stop:.5f} (profit={profit_captured_r:.1f}R)")
            return new_stop

    return current_stop
