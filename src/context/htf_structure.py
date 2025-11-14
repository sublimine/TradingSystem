"""
HTF Structure Analyzer - High Timeframe Structure (H4/D1)

MANDATO 15: Análisis de estructura HTF institucional.

Identifica tendencia, swing highs/lows, order blocks, key levels.
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class Trend(Enum):
    UPTREND = 'UPTREND'        # HH + HL
    DOWNTREND = 'DOWNTREND'    # LH + LL
    RANGING = 'RANGING'         # Sin tendencia clara


class HTFStructureAnalyzer:
    """
    Analiza estructura de higher timeframes (H4/D1).
    """

    def __init__(self, config: Dict):
        """
        Args:
            config: {
                'swing_lookback': Ventana para detectar swings (típico 10-20),
                'ob_lookback': Ventana para order blocks (típico 5)
            }
        """
        self.swing_lookback = config.get('swing_lookback', 15)
        self.ob_lookback = config.get('ob_lookback', 5)

        # Cache por símbolo
        self.cache: Dict[str, Dict] = {}

        logger.info(f"HTFStructureAnalyzer init: swing_lb={self.swing_lookback}")

    def analyze(self, symbol: str, df: pd.DataFrame) -> Dict:
        """
        Analizar estructura HTF.

        Args:
            symbol: Símbolo
            df: DataFrame con OHLC

        Returns:
            {
                'trend': Trend enum,
                'trend_strength': float [0-1],
                'swing_highs': List[float],
                'swing_lows': List[float],
                'order_blocks': List[Dict],
                'key_levels': List[float]
            }
        """
        if len(df) < self.swing_lookback * 2:
            return self._empty_result()

        # Detectar swings
        swing_highs, swing_lows = self._detect_swings(df)

        # Determinar tendencia
        trend, strength = self._determine_trend(swing_highs, swing_lows)

        # Identificar order blocks
        order_blocks = self._identify_order_blocks(df, trend)

        # Key levels (swings recientes)
        key_levels = self._extract_key_levels(swing_highs, swing_lows)

        result = {
            'trend': trend,
            'trend_strength': strength,
            'swing_highs': swing_highs[-5:],  # Últimos 5
            'swing_lows': swing_lows[-5:],
            'order_blocks': order_blocks[-3:],  # Últimos 3
            'key_levels': key_levels
        }

        self.cache[symbol] = result
        return result

    def _detect_swings(self, df: pd.DataFrame) -> Tuple[List[float], List[float]]:
        """
        Detectar swing highs y lows.

        Returns:
            (swing_highs, swing_lows)
        """
        highs = []
        lows = []

        for i in range(self.swing_lookback, len(df) - self.swing_lookback):
            # Swing high: high[i] > all highs en ventana
            if df['high'].iloc[i] == df['high'].iloc[i-self.swing_lookback:i+self.swing_lookback+1].max():
                highs.append(df['high'].iloc[i])

            # Swing low: low[i] < all lows en ventana
            if df['low'].iloc[i] == df['low'].iloc[i-self.swing_lookback:i+self.swing_lookback+1].min():
                lows.append(df['low'].iloc[i])

        return highs, lows

    def _determine_trend(self, swing_highs: List[float],
                        swing_lows: List[float]) -> Tuple[Trend, float]:
        """
        Determinar tendencia basado en swings.

        Returns:
            (trend, strength [0-1])
        """
        if len(swing_highs) < 2 or len(swing_lows) < 2:
            return Trend.RANGING, 0.5

        # Analizar últimos 3 swings
        recent_highs = swing_highs[-3:]
        recent_lows = swing_lows[-3:]

        # UPTREND: HH + HL
        hh = all(recent_highs[i] > recent_highs[i-1] for i in range(1, len(recent_highs)))
        hl = all(recent_lows[i] > recent_lows[i-1] for i in range(1, len(recent_lows)))

        # DOWNTREND: LH + LL
        lh = all(recent_highs[i] < recent_highs[i-1] for i in range(1, len(recent_highs)))
        ll = all(recent_lows[i] < recent_lows[i-1] for i in range(1, len(recent_lows)))

        if hh and hl:
            strength = 0.9
            return Trend.UPTREND, strength
        elif lh and ll:
            strength = 0.9
            return Trend.DOWNTREND, strength
        else:
            return Trend.RANGING, 0.5

    def _identify_order_blocks(self, df: pd.DataFrame, trend: Trend) -> List[Dict]:
        """
        Identificar order blocks (simplificado institucional).

        Order block = vela con fuerte movimiento seguido de reversal.
        """
        obs = []

        for i in range(len(df) - self.ob_lookback, len(df)):
            candle = df.iloc[i]
            body_size = abs(candle['close'] - candle['open'])
            candle_range = candle['high'] - candle['low']

            if candle_range == 0:
                continue

            # Fuerte body (>60% de la vela)
            if body_size / candle_range > 0.6:
                obs.append({
                    'price': candle['open'] if candle['close'] > candle['open'] else candle['close'],
                    'high': candle['high'],
                    'low': candle['low'],
                    'type': 'BULLISH_OB' if candle['close'] > candle['open'] else 'BEARISH_OB'
                })

        return obs

    def _extract_key_levels(self, swing_highs: List[float],
                           swing_lows: List[float]) -> List[float]:
        """Extract key levels from recent swings."""
        levels = []
        if swing_highs:
            levels.extend(swing_highs[-3:])
        if swing_lows:
            levels.extend(swing_lows[-3:])
        return sorted(levels)

    def _empty_result(self) -> Dict:
        return {
            'trend': Trend.RANGING,
            'trend_strength': 0.5,
            'swing_highs': [],
            'swing_lows': [],
            'order_blocks': [],
            'key_levels': []
        }

    def get_cached(self, symbol: str) -> Optional[Dict]:
        """Get cached analysis."""
        return self.cache.get(symbol)
