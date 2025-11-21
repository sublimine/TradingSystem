"""
Strategic Stop Loss Placement - ELITE Institutional Implementation V2.0

⚠️⚠️⚠️ DEPRECATED - PLAN OMEGA ⚠️⚠️⚠️

This module is DEPRECATED as of PLAN OMEGA execution.

**REASON FOR DEPRECATION:**
This entire module uses ATR for risk sizing (buffer calculations), which violates
PLAN OMEGA mandate: "ZERO ATR in risk/SL/TP decisions."

All ATR-based buffer calculations (e.g., `atr * buffer * 0.5`) are TYPE A violations.

**REPLACEMENT:**
Use `src/features/institutional_sl_tp.py` which implements:
- Structural stop placement (swing points, order blocks, FVG)
- Fixed pips buffers (e.g., 15 pips, 20 pips)
- % price based fallback stops (1.5-2.5%)
- NO ATR in risk sizing

**CONCEPTS TO PRESERVE FOR FUTURE ENHANCEMENT:**
This file contains CRITICAL institutional concepts that should be migrated:

1. **WICK LIQUIDITY SWEEP** (lines 92-206):
   - Detects wicks that swept previous highs/lows (institutional stop hunts)
   - "Wicks donde se sacó liquidez, el precio acostumbra a NO volver"
   - Best stop placement = beyond wick sweep levels
   - TODO: Migrate to institutional_sl_tp.py with PIPS buffers (not ATR)

2. **UNTAKEN LIQUIDITY TARGETS** (lines 428-550):
   - Detects equal highs/lows (2+ candles at same level)
   - Liquidity pools never touched = magnets for price
   - Institutions target resting stop losses
   - TODO: Migrate to institutional_sl_tp.py for take profit logic

3. **FRACTAL TARGETS** (lines 553-621):
   - Local highs/lows indicating liquidity zones
   - Liquidity channels = multiple fractals at similar levels
   - TODO: Migrate to institutional_sl_tp.py

**DO NOT USE THIS MODULE FOR NEW STRATEGIES.**
**ALL 24 STRATEGIES NOW USE institutional_sl_tp.py EXCLUSIVELY.**

---

ORIGINAL DOCSTRING:

Stops placed at STRUCTURAL levels, NOT arbitrary ATR multipliers.

**NEW:** Multi-timeframe WICK LIQUIDITY SWEEP detection - wicks that swept liquidity
rarely get revisited. This is where institutions hunted stops.

Stop placement hierarchy (best to worst):
1. **WICK LIQUIDITY SWEEP** - Wicks that swept previous highs/lows (BEST)
2. Order Block boundary + buffer
3. Fair Value Gap (FVG) edge + buffer
4. Swing high/low + buffer
5. ATR-based fallback (only if no structure available)

Trailing stops:
- Move to breakeven after 1R captured
- Trail using structure levels (swing highs/lows)
- Accelerate trail in profit zones

Research Basis:
- Wyckoff Method: Support/Resistance as institutional footprints
- Smart Money Concepts: Order blocks mark institutional zones
- Liquidity Engineering: Price sweeps stops then reverses (stop hunts)
- Risk management: Place stops where institutions would defend

**CRITICAL INSIGHT:** "Wicks donde se sacó liquidez, el precio acostumbra a NO volver
donde ya barrió." - Price rarely returns to liquidity sweep levels.

Author: Elite Trading System
Version: 2.0 - Wick Liquidity Sweep Integration
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
    buffer_multiplier: float = 1.2,
    mtf_data: Optional[Dict[str, pd.DataFrame]] = None
) -> Tuple[float, str]:
    """
    Calculate strategic stop loss using structure and liquidity sweeps.

    Args:
        direction: 'LONG' or 'SHORT'
        entry_price: Entry price level
        market_data: Recent OHLCV data (current timeframe)
        features: Dict containing structure data (order_blocks, fvgs, etc.)
        atr_fallback: ATR value for fallback calculation
        buffer_multiplier: Buffer beyond structure (typically 1.2 = 20%)
        mtf_data: Optional dict of multi-timeframe data {'M5': df, 'M15': df, 'H1': df}

    Returns:
        Tuple of (stop_loss_price, stop_type)
        stop_type: 'WICK_SWEEP' | 'ORDER_BLOCK' | 'FVG' | 'SWING' | 'ATR_FALLBACK'
    """
    # Priority 1: WICK LIQUIDITY SWEEP (BEST - where institutions hunted stops)
    wick_stop = _find_wick_liquidity_sweep(direction, entry_price, market_data, mtf_data, atr_fallback, buffer_multiplier)
    if wick_stop is not None:
        return wick_stop, 'WICK_SWEEP'

    # Priority 2: Order Block
    ob_stop = _find_order_block_stop(direction, entry_price, features, atr_fallback, buffer_multiplier)
    if ob_stop is not None:
        return ob_stop, 'ORDER_BLOCK'

    # Priority 3: Fair Value Gap
    fvg_stop = _find_fvg_stop(direction, entry_price, features, atr_fallback, buffer_multiplier)
    if fvg_stop is not None:
        return fvg_stop, 'FVG'

    # Priority 4: Swing High/Low
    swing_stop = _find_swing_stop(direction, entry_price, market_data, atr_fallback, buffer_multiplier)
    if swing_stop is not None:
        return swing_stop, 'SWING'

    # Fallback: ATR-based
    atr_stop = _calculate_atr_fallback(direction, entry_price, atr_fallback)
    return atr_stop, 'ATR_FALLBACK'


def _find_wick_liquidity_sweep(direction: str, entry_price: float,
                               market_data: pd.DataFrame,
                               mtf_data: Optional[Dict[str, pd.DataFrame]],
                               atr: float, buffer: float) -> Optional[float]:
    """
    Find liquidity sweep wicks for optimal stop placement.

    **CRITICAL CONCEPT:**
    Wicks that swept previous highs/lows are where institutions hunted retail stops.
    Price RARELY returns to these levels once liquidityes swept.

    Detection:
    1. Find wicks that extended beyond previous swing highs/lows
    2. Confirm wick closed back inside range (sweep + reversal)
    3. Check multiple timeframes (M5, M15, H1) for strongest sweeps
    4. Place stop BEYOND the wick (institutions won't let it get hit)

    Args:
        direction: 'LONG' or 'SHORT'
        entry_price: Current entry price
        market_data: Current timeframe OHLCV data
        mtf_data: Multi-timeframe data (optional but recommended)
        atr: ATR for buffer calculation
        buffer: Buffer multiplier

    Returns:
        Stop loss price if wick sweep found, None otherwise
    """
    # Combine current timeframe + MTF data for analysis
    timeframes_to_check = [market_data]  # Always check current TF

    if mtf_data:
        # Check higher timeframes (more significant sweeps)
        for tf_name in ['M5', 'M15', 'H1', 'H4']:
            if tf_name in mtf_data and mtf_data[tf_name] is not None:
                timeframes_to_check.append(mtf_data[tf_name])

    best_wick_level = None
    best_wick_significance = 0.0

    for tf_data in timeframes_to_check:
        if len(tf_data) < 20:
            continue

        # Look back 50 bars for liquidity sweeps
        lookback = min(50, len(tf_data))
        recent_bars = tf_data.tail(lookback).copy()

        # Detect liquidity sweeps
        for i in range(10, len(recent_bars)):
            current_bar = recent_bars.iloc[i]
            previous_bars = recent_bars.iloc[max(0, i-10):i]

            if direction == 'LONG':
                # For LONG: Find DOWNWARD liquidity sweeps (wick below previous lows)
                prev_low = previous_bars['low'].min()

                # Check if wick swept below previous low
                wick_swept_low = current_bar['low'] < prev_low
                closed_above = current_bar['close'] > prev_low  # Reversal confirmation

                if wick_swept_low and closed_above:
                    wick_low = current_bar['low']

                    # Check if this wick is below our entry (valid for stop placement)
                    if wick_low < entry_price:
                        # Calculate significance (how far below prev low)
                        sweep_distance = prev_low - wick_low
                        wick_size = current_bar['high'] - current_bar['low']

                        # Strong sweep = significant distance + large wick
                        significance = sweep_distance / (atr + 1e-10) * (wick_size / atr)

                        if significance > best_wick_significance:
                            best_wick_significance = significance
                            best_wick_level = wick_low

            else:  # SHORT
                # For SHORT: Find UPWARD liquidity sweeps (wick above previous highs)
                prev_high = previous_bars['high'].max()

                # Check if wick swept above previous high
                wick_swept_high = current_bar['high'] > prev_high
                closed_below = current_bar['close'] < prev_high  # Reversal confirmation

                if wick_swept_high and closed_below:
                    wick_high = current_bar['high']

                    # Check if this wick is above our entry (valid for stop placement)
                    if wick_high > entry_price:
                        sweep_distance = wick_high - prev_high
                        wick_size = current_bar['high'] - current_bar['low']

                        significance = sweep_distance / (atr + 1e-10) * (wick_size / atr)

                        if significance > best_wick_significance:
                            best_wick_significance = significance
                            best_wick_level = wick_high

    # If we found a significant wick sweep (significance > 1.5)
    if best_wick_level is not None and best_wick_significance > 1.5:
        if direction == 'LONG':
            # Place stop BELOW the wick that swept liquidity
            stop = best_wick_level - (atr * buffer * 0.3)
            logger.info(f"✓✓ WICK SWEEP stop: {stop:.5f} (wick low: {best_wick_level:.5f}, "
                       f"significance: {best_wick_significance:.1f})")
            return stop
        else:
            # Place stop ABOVE the wick that swept liquidity
            stop = best_wick_level + (atr * buffer * 0.3)
            logger.info(f"✓✓ WICK SWEEP stop: {stop:.5f} (wick high: {best_wick_level:.5f}, "
                       f"significance: {best_wick_significance:.1f})")
            return stop

    return None


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
    default_rr: float = 3.0,
    mtf_data: Optional[Dict[str, pd.DataFrame]] = None
) -> Tuple[float, str]:
    """
    Calculate strategic take profit using structure and liquidity analysis.

    **UPGRADED:** Now detects untaken liquidity pools, fractals, and channels.

    Priority hierarchy (best to worst):
    1. UNTAKEN LIQUIDITY (equal highs/lows, liquidity pools) - BEST
    2. Order Block opposite (just before touching)
    3. Fair Value Gap opposite
    4. Fractals/Liquidity channels
    5. Swing extreme
    6. ATR fallback (only if no structure)

    Args:
        direction: 'LONG' or 'SHORT'
        entry_price: Entry price
        stop_loss: Stop loss price
        market_data: Recent OHLCV data (current timeframe)
        features: Dict containing structure data
        default_rr: Default risk:reward ratio if no structure found
        mtf_data: Optional multi-timeframe data for better liquidity detection

    Returns:
        Tuple of (take_profit_price, target_type)
        target_type: 'UNTAKEN_LIQ' | 'ORDER_BLOCK' | 'FVG' | 'FRACTAL' | 'SWING' | 'RR_DEFAULT'
    """
    risk = abs(entry_price - stop_loss)

    # Priority 1: UNTAKEN LIQUIDITY (equal highs/lows, liquidity pools)
    liq_target = _find_untaken_liquidity_target(direction, entry_price, market_data, mtf_data, risk)
    if liq_target is not None:
        return liq_target, 'UNTAKEN_LIQ'

    # Priority 2: Opposite Order Block (just before touching)
    ob_target = _find_order_block_target(direction, entry_price, features, risk)
    if ob_target is not None:
        return ob_target, 'ORDER_BLOCK'

    # Priority 3: Opposite FVG
    fvg_target = _find_fvg_target(direction, entry_price, features, risk)
    if fvg_target is not None:
        return fvg_target, 'FVG'

    # Priority 4: Fractals and liquidity channels
    fractal_target = _find_fractal_target(direction, entry_price, market_data, risk)
    if fractal_target is not None:
        return fractal_target, 'FRACTAL'

    # Priority 5: Swing extreme
    swing_target = _find_swing_target(direction, entry_price, market_data, risk)
    if swing_target is not None:
        return swing_target, 'SWING'

    # Fallback: R:R ratio (ATR-based)
    if direction == 'LONG':
        target = entry_price + (risk * default_rr)
    else:
        target = entry_price - (risk * default_rr)

    logger.info(f"ℹ️  R:R target (fallback): {target:.5f} ({default_rr}R)")
    return target, 'RR_DEFAULT'


def _find_untaken_liquidity_target(direction: str, entry_price: float,
                                   market_data: pd.DataFrame,
                                   mtf_data: Optional[Dict[str, pd.DataFrame]],
                                   risk: float) -> Optional[float]:
    """
    Find untaken liquidity for target placement.

    **KEY CONCEPT:** Liquidez NO tomada = price levels with:
    - Equal highs/lows (2+ candles at same level)
    - Liquidity pools (clusters of highs/lows never touched)
    - Piscinas/equals (multiple equal price points)

    These are magnets for price - institutions target resting stop losses.

    Args:
        direction: 'LONG' or 'SHORT'
        entry_price: Current entry price
        market_data: Current timeframe data
        mtf_data: Multi-timeframe data (optional but better)
        risk: Risk amount (for minimum distance check)

    Returns:
        Target price if untaken liquidity found, None otherwise
    """
    # Combine current + MTF data for better detection
    timeframes_to_check = [market_data]

    if mtf_data:
        for tf_name in ['M15', 'H1', 'H4']:
            if tf_name in mtf_data and mtf_data[tf_name] is not None:
                timeframes_to_check.append(mtf_data[tf_name])

    best_liquidity_level = None
    best_liquidity_strength = 0.0

    for tf_data in timeframes_to_check:
        if len(tf_data) < 20:
            continue

        lookback = min(100, len(tf_data))
        recent_data = tf_data.tail(lookback)

        if direction == 'LONG':
            # Find UNTAKEN HIGHS above entry (resistance liquidity)
            highs = recent_data['high'].values

            # Detect equal highs (within 5 pips tolerance)
            pip_tolerance = 0.0005  # 5 pips for most pairs

            for i in range(len(highs) - 1):
                current_high = highs[i]

                # Must be above entry price
                if current_high <= entry_price:
                    continue

                # Must be at least 1R above entry (worth targeting)
                if current_high < entry_price + risk:
                    continue

                # Count how many equal highs at this level
                equal_highs = sum(1 for h in highs if abs(h - current_high) < pip_tolerance)

                # Check if liquidity was taken (did price go through this level?)
                was_taken = any(low < current_high - pip_tolerance for low in recent_data['low'].values[i+1:])

                # If liquidity NOT taken AND multiple equal highs = strong target
                if not was_taken and equal_highs >= 2:
                    strength = equal_highs  # More equals = stronger liquidity

                    if strength > best_liquidity_strength:
                        best_liquidity_strength = strength
                        best_liquidity_level = current_high

        else:  # SHORT
            # Find UNTAKEN LOWS below entry (support liquidity)
            lows = recent_data['low'].values

            pip_tolerance = 0.0005

            for i in range(len(lows) - 1):
                current_low = lows[i]

                # Must be below entry price
                if current_low >= entry_price:
                    continue

                # Must be at least 1R below entry
                if current_low > entry_price - risk:
                    continue

                # Count equal lows
                equal_lows = sum(1 for l in lows if abs(l - current_low) < pip_tolerance)

                # Check if taken
                was_taken = any(high > current_low + pip_tolerance for high in recent_data['high'].values[i+1:])

                # If NOT taken AND multiple equals = strong target
                if not was_taken and equal_lows >= 2:
                    strength = equal_lows

                    if strength > best_liquidity_strength:
                        best_liquidity_strength = strength
                        best_liquidity_level = current_low

    # If found strong untaken liquidity (2+ equals)
    if best_liquidity_level is not None and best_liquidity_strength >= 2:
        if direction == 'LONG':
            # Target JUST BEFORE the liquidity (don't overshoot)
            target = best_liquidity_level - (risk * 0.05)  # 5% buffer before liquidity
            logger.info(f"✓✓ UNTAKEN LIQUIDITY target: {target:.5f} "
                       f"(liquidity level: {best_liquidity_level:.5f}, "
                       f"strength: {best_liquidity_strength:.0f} equals)")
            return target
        else:
            # Target JUST BEFORE the liquidity
            target = best_liquidity_level + (risk * 0.05)
            logger.info(f"✓✓ UNTAKEN LIQUIDITY target: {target:.5f} "
                       f"(liquidity level: {best_liquidity_level:.5f}, "
                       f"strength: {best_liquidity_strength:.0f} equals)")
            return target

    return None


def _find_fractal_target(direction: str, entry_price: float,
                        market_data: pd.DataFrame, risk: float) -> Optional[float]:
    """
    Find fractal/liquidity channel for target.

    Fractals = local highs/lows that indicate liquidity zones.

    Detection:
    - Fractal high = high[i] > high[i-1] AND high[i] > high[i+1]
    - Fractal low = low[i] < low[i-1] AND low[i] < low[i+1]

    Liquidity channels = multiple fractals at similar levels.

    Args:
        direction: 'LONG' or 'SHORT'
        entry_price: Current entry price
        market_data: OHLCV data
        risk: Risk amount

    Returns:
        Target price if fractal found, None otherwise
    """
    if len(market_data) < 10:
        return None

    lookback = min(50, len(market_data))
    recent_data = market_data.tail(lookback)

    if direction == 'LONG':
        # Find fractal highs above entry
        highs = recent_data['high'].values
        fractal_highs = []

        # Detect fractals (simplified: local max)
        for i in range(1, len(highs) - 1):
            if highs[i] > highs[i-1] and highs[i] > highs[i+1]:
                # Is fractal
                fractal_high = highs[i]

                # Must be above entry + 1R
                if fractal_high > entry_price + risk:
                    fractal_highs.append(fractal_high)

        if fractal_highs:
            # Target nearest fractal high
            nearest_fractal = min(fractal_highs)
            target = nearest_fractal - (risk * 0.08)  # 8% buffer before fractal
            logger.info(f"✓ FRACTAL target: {target:.5f} (fractal high: {nearest_fractal:.5f})")
            return target

    else:  # SHORT
        # Find fractal lows below entry
        lows = recent_data['low'].values
        fractal_lows = []

        for i in range(1, len(lows) - 1):
            if lows[i] < lows[i-1] and lows[i] < lows[i+1]:
                fractal_low = lows[i]

                if fractal_low < entry_price - risk:
                    fractal_lows.append(fractal_low)

        if fractal_lows:
            nearest_fractal = max(fractal_lows)
            target = nearest_fractal + (risk * 0.08)
            logger.info(f"✓ FRACTAL target: {target:.5f} (fractal low: {nearest_fractal:.5f})")
            return target

    return None


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
