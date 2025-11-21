"""
Multi-Timeframe Data Manager - Institutional Implementation

Manages synchronized data across multiple timeframes with efficient caching.
Provides HTF context for LTF execution decisions.
"""

import MetaTrader5 as mt5
import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple
import logging
from datetime import datetime, timedelta
from collections import defaultdict

logger = logging.getLogger(__name__)


class MultiTimeframeDataManager:
    """
    Institutional multi-timeframe data management.

    Maintains synchronized OHLCV data across timeframes with:
    - Efficient caching and incremental updates
    - Timeframe alignment for cross-TF analysis
    - Structure detection across timeframes
    - Liquidity level mapping
    """

    def __init__(self, symbols: List[str]):
        """
        Initialize MTF data manager.

        Args:
            symbols: List of symbols to manage
        """
        self.symbols = symbols

        # Timeframe hierarchy (highest to lowest)
        self.timeframes = {
            'D1': mt5.TIMEFRAME_D1,
            'H4': mt5.TIMEFRAME_H4,
            'H1': mt5.TIMEFRAME_H1,
            'M30': mt5.TIMEFRAME_M30,
            'M15': mt5.TIMEFRAME_M15,
            'M5': mt5.TIMEFRAME_M5,
            'M1': mt5.TIMEFRAME_M1,
        }

        # Cache: {symbol: {timeframe: DataFrame}}
        self.data_cache: Dict[str, Dict[str, pd.DataFrame]] = defaultdict(dict)

        # Structure cache: {symbol: {timeframe: structure_info}}
        self.structure_cache: Dict[str, Dict[str, Dict]] = defaultdict(dict)

        # Last update timestamps
        self.last_update: Dict[str, Dict[str, datetime]] = defaultdict(dict)

        logger.info(f"MTF Manager initialized: {len(symbols)} symbols, {len(self.timeframes)} timeframes")

    def update_all_timeframes(self, symbol: str, bars_config: Optional[Dict[str, int]] = None):
        """
        Update all timeframes for a symbol.

        Args:
            symbol: Symbol to update
            bars_config: Optional dict of bars to load per TF
        """
        if bars_config is None:
            bars_config = {
                'D1': 100,
                'H4': 150,
                'H1': 200,
                'M30': 200,
                'M15': 300,
                'M5': 400,
                'M1': 500,
            }

        for tf_name, tf_const in self.timeframes.items():
            bars = bars_config.get(tf_name, 100)

            try:
                rates = mt5.copy_rates_from_pos(symbol, tf_const, 0, bars)

                if rates is not None and len(rates) > 0:
                    df = self._process_ohlcv(rates, symbol, tf_name)
                    self.data_cache[symbol][tf_name] = df
                    self.last_update[symbol][tf_name] = datetime.now()

                    # Update structure cache for this TF
                    self._update_structure_cache(symbol, tf_name, df)

                    logger.debug(f"Updated {symbol} {tf_name}: {len(df)} bars")
                else:
                    logger.warning(f"No data for {symbol} {tf_name}")

            except Exception as e:
                logger.error(f"Error updating {symbol} {tf_name}: {e}")

    def _process_ohlcv(self, rates, symbol: str, timeframe: str) -> pd.DataFrame:
        """
        Process raw OHLCV data into DataFrame with indicators.

        âš ï¸ indicador de rango USAGE: TYPE B - DESCRIPTIVE METRIC ONLY âš ï¸
        indicador de rango is calculated here for PATTERN DETECTION (order blocks, FVGs, liquidity zones).
        NOT used for risk sizing, stop loss, or take profit calculations.
        """
        df = pd.DataFrame(rates)
        df['time'] = pd.to_datetime(df['time'], unit='s')
        df['timestamp'] = df['time']
        df['symbol'] = symbol
        df['volume'] = df['tick_volume']
        df.attrs['symbol'] = symbol
        df.attrs['timeframe'] = timeframe

        # Add basic indicators
        df['ema_20'] = df['close'].ewm(span=20, adjust=False).mean()
        df['ema_50'] = df['close'].ewm(span=50, adjust=False).mean()
        df['ema_200'] = df['close'].ewm(span=200, adjust=False).mean()

        # indicador de rango (TYPE B - descriptive metric for pattern detection)
        high_low = df['high'] - df['low']
        high_close = (df['high'] - df['close'].shift()).abs()
        low_close = (df['low'] - df['close'].shift()).abs()
        true_range = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
        df['indicador de rango'] = true_range.rolling(14).mean()  # TYPE B - descriptive metric only

        # Volume profile
        df['volume_ma'] = df['volume'].rolling(20).mean()
        df['volume_spike'] = df['volume'] / df['volume_ma']

        return df

    def _update_structure_cache(self, symbol: str, timeframe: str, df: pd.DataFrame):
        """
        Update market structure information for timeframe.

        âš ï¸ indicador de rango USAGE: TYPE B - DESCRIPTIVE METRIC ONLY âš ï¸
        indicador de rango is used for PATTERN DETECTION (order blocks, FVGs, liquidity zones).
        NOT used for risk sizing, stop loss, or take profit calculations.

        Identifies:
        - Swing highs/lows (institutional levels)
        - Order blocks (displacement candles - >1.5 indicador de rango range)
        - Fair value gaps (minimum gap size >0.3 indicador de rango)
        - Liquidity zones (indicador de rango compression <0.6 mean indicador de rango)
        """
        if len(df) < 50:
            return

        structure = {
            'swing_highs': [],
            'swing_lows': [],
            'order_blocks': [],
            'fvgs': [],
            'liquidity_zones': [],
        }

        # Detect swing points (institutional pivot points)
        highs = df['high'].values
        lows = df['low'].values
        times = df['time'].values

        # Swing highs: local maximum with 5 bars on each side
        for i in range(5, len(df) - 5):
            if highs[i] == max(highs[i-5:i+6]):
                structure['swing_highs'].append({
                    'price': float(highs[i]),
                    'time': times[i],
                    'index': i
                })

        # Swing lows: local minimum with 5 bars on each side
        for i in range(5, len(df) - 5):
            if lows[i] == min(lows[i-5:i+6]):
                structure['swing_lows'].append({
                    'price': float(lows[i]),
                    'time': times[i],
                    'index': i
                })

        # Order blocks: Strong displacement candles (>1.5 indicador de rango range)
        if 'indicador de rango' in df.columns:
            df_tail = df.tail(100)
            for idx, row in df_tail.iterrows():
                candle_range = row['high'] - row['low']
                if candle_range > row['indicador de rango'] * 1.5:
                    ob_type = 'BULLISH' if row['close'] > row['open'] else 'BEARISH'
                    structure['order_blocks'].append({
                        'type': ob_type,
                        'high': float(row['high']),
                        'low': float(row['low']),
                        'time': row['time'],
                    })

        # Fair Value Gaps: Gap in price action (3-candle pattern)
        for i in range(2, len(df)):
            # Bullish FVG: candle[i-2].high < candle[i].low
            if df.iloc[i-2]['high'] < df.iloc[i]['low']:
                gap_size = df.iloc[i]['low'] - df.iloc[i-2]['high']
                if gap_size > df.iloc[i]['indicador de rango'] * 0.3:  # Minimum gap size
                    structure['fvgs'].append({
                        'type': 'BULLISH',
                        'high': float(df.iloc[i]['low']),
                        'low': float(df.iloc[i-2]['high']),
                        'time': df.iloc[i]['time'],
                    })

            # Bearish FVG: candle[i-2].low > candle[i].high
            elif df.iloc[i-2]['low'] > df.iloc[i]['high']:
                gap_size = df.iloc[i-2]['low'] - df.iloc[i]['high']
                if gap_size > df.iloc[i]['indicador de rango'] * 0.3:
                    structure['fvgs'].append({
                        'type': 'BEARISH',
                        'high': float(df.iloc[i-2]['low']),
                        'low': float(df.iloc[i]['high']),
                        'time': df.iloc[i]['time'],
                    })

        # Liquidity zones: Consolidation areas (low volatility clusters)
        # Identify using indicador de rango compression
        if 'indicador de rango' in df.columns:
            df_tail = df.tail(50)
            atr_values = df_tail['indicador de rango'].values
            atr_mean = np.mean(atr_values)

            for i in range(5, len(df_tail)):
                window_atr = df_tail.iloc[i-5:i]['indicador de rango'].mean()
                if window_atr < atr_mean * 0.6:  # Low volatility
                    zone_high = df_tail.iloc[i-5:i]['high'].max()
                    zone_low = df_tail.iloc[i-5:i]['low'].min()
                    structure['liquidity_zones'].append({
                        'high': float(zone_high),
                        'low': float(zone_low),
                        'time': df_tail.iloc[i]['time'],
                    })

        self.structure_cache[symbol][timeframe] = structure

    def get_data(self, symbol: str, timeframe: str) -> pd.DataFrame:
        """Get cached data for symbol/timeframe."""
        return self.data_cache.get(symbol, {}).get(timeframe, pd.DataFrame())

    def get_structure(self, symbol: str, timeframe: str) -> Dict:
        """Get market structure for symbol/timeframe."""
        return self.structure_cache.get(symbol, {}).get(timeframe, {})

    def calculate_mtf_trend(self, symbol: str) -> Dict[str, str]:
        """
        Calculate trend direction across timeframes.

        Uses EMA structure:
        - UP: EMA20 > EMA50 > EMA200, price > EMA20
        - DOWN: EMA20 < EMA50 < EMA200, price < EMA20
        - NEUTRAL: Mixed or ranging

        Returns:
            Dict mapping timeframe to trend: {'D1': 'UP', 'H4': 'DOWN', ...}
        """
        trends = {}

        for tf in ['D1', 'H4', 'H1', 'M30', 'M15']:
            df = self.get_data(symbol, tf)

            if len(df) < 200 or 'ema_200' not in df.columns:
                trends[tf] = 'NEUTRAL'
                continue

            current = df.iloc[-1]
            price = current['close']
            ema20 = current['ema_20']
            ema50 = current['ema_50']
            ema200 = current['ema_200']

            # Strong uptrend: all EMAs aligned + price above
            if ema20 > ema50 > ema200 and price > ema20:
                trends[tf] = 'UP'
            # Weak uptrend: EMAs aligned but price below EMA20 (pullback)
            elif ema20 > ema50 > ema200 and price < ema20:
                trends[tf] = 'UP_WEAK'
            # Strong downtrend
            elif ema20 < ema50 < ema200 and price < ema20:
                trends[tf] = 'DOWN'
            # Weak downtrend
            elif ema20 < ema50 < ema200 and price > ema20:
                trends[tf] = 'DOWN_WEAK'
            else:
                trends[tf] = 'NEUTRAL'

        return trends

    def calculate_mtf_confluence(self, symbol: str, direction: str) -> float:
        """
        Calculate multi-timeframe confluence score.

        Institutional weighting:
        - D1: 40% (primary trend)
        - H4: 30% (intermediate trend)
        - H1: 20% (short-term trend)
        - M30: 7% (entry refinement)
        - M15: 3% (execution)

        Args:
            symbol: Symbol
            direction: 'LONG' or 'SHORT'

        Returns:
            Confluence score 0.0-1.0
        """
        trends = self.calculate_mtf_trend(symbol)

        weights = {
            'D1': 0.40,
            'H4': 0.30,
            'H1': 0.20,
            'M30': 0.07,
            'M15': 0.03,
        }

        score = 0.0

        for tf, weight in weights.items():
            trend = trends.get(tf, 'NEUTRAL')

            if direction == 'LONG':
                if trend == 'UP':
                    score += weight * 1.0
                elif trend == 'UP_WEAK':
                    score += weight * 0.75
                elif trend == 'NEUTRAL':
                    score += weight * 0.40
                # DOWN contributes 0

            elif direction == 'SHORT':
                if trend == 'DOWN':
                    score += weight * 1.0
                elif trend == 'DOWN_WEAK':
                    score += weight * 0.75
                elif trend == 'NEUTRAL':
                    score += weight * 0.40

        return score

    def find_nearest_structure(self, symbol: str, timeframe: str,
                              price: float, structure_type: str) -> Optional[Dict]:
        """
        Find nearest market structure level to current price.

        Args:
            symbol: Symbol
            timeframe: Timeframe
            price: Current price
            structure_type: 'swing_high', 'swing_low', 'order_block', 'fvg', 'liquidity_zone'

        Returns:
            Nearest structure dict or None
        """
        structure = self.get_structure(symbol, timeframe)

        if structure_type not in structure or not structure[structure_type]:
            return None

        levels = structure[structure_type]

        # Find closest by price
        closest = None
        min_distance = float('inf')

        for level in levels:
            if 'price' in level:
                distance = abs(level['price'] - price)
            elif 'high' in level and 'low' in level:
                # For zones, use midpoint
                midpoint = (level['high'] + level['low']) / 2
                distance = abs(midpoint - price)
            else:
                continue

            if distance < min_distance:
                min_distance = distance
                closest = level

        return closest

    def get_htf_bias(self, symbol: str) -> str:
        """
        Get higher timeframe directional bias.

        Returns:
            'BULLISH', 'BEARISH', or 'NEUTRAL'
        """
        d1_df = self.get_data(symbol, 'D1')
        h4_df = self.get_data(symbol, 'H4')

        if d1_df.empty or h4_df.empty:
            return 'NEUTRAL'

        # D1 bias (primary)
        d1_current = d1_df.iloc[-1]
        d1_bias = 'BULLISH' if d1_current['ema_20'] > d1_current['ema_50'] else 'BEARISH'

        # H4 confirmation
        h4_current = h4_df.iloc[-1]
        h4_bias = 'BULLISH' if h4_current['ema_20'] > h4_current['ema_50'] else 'BEARISH'

        # Both must agree for clear bias
        if d1_bias == h4_bias:
            return d1_bias
        else:
            return 'NEUTRAL'
