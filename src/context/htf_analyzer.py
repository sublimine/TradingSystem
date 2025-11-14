"""
HTF Structure Analyzer - High Timeframe Structure Analysis

Analiza estructura macro en H4/D1 para identificar:
- Trend direction (alcista, bajista, rango)
- Key swing levels (highs/lows)
- Market structure (HH/HL o LH/LL)

HTF = Ley. NO se opera contra HTF bias.
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Tuple
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class HTFStructureAnalyzer:
    """
    Analiza estructura en timeframes altos (H4, D1).

    Output:
    - trend_direction: 'BULLISH', 'BEARISH', 'RANGE'
    - trend_strength: [0-1]
    - key_levels: {swing_highs: [...], swing_lows: [...]}
    """

    def __init__(self, config: Dict):
        """
        Inicializar analizador HTF.

        Args:
            config: {
                'lookback_swings': int - Número de swings a analizar (default: 10),
                'range_threshold': float - Threshold para rango vs tendencia (default: 0.3),
                'swing_detection_window': int - Ventana para detección de swing (default: 5)
            }
        """
        self.lookback_swings = config.get('lookback_swings', 10)
        self.range_threshold = config.get('range_threshold', 0.3)
        self.swing_window = config.get('swing_detection_window', 5)

        # Cache de estructura por símbolo
        self.structure_cache = {}

        logger.info(f"HTFStructureAnalyzer initialized: lookback={self.lookback_swings}, "
                   f"range_threshold={self.range_threshold}")

    def analyze_structure(self, symbol: str, ohlcv: pd.DataFrame) -> Dict:
        """
        Analiza estructura HTF completa.

        Args:
            symbol: Símbolo
            ohlcv: DataFrame con columnas [open, high, low, close, volume]
                  Debe contener al menos 50+ velas para análisis robusto

        Returns:
            {
                'trend_direction': str,
                'trend_strength': float [0-1],
                'swing_highs': List[float],
                'swing_lows': List[float],
                'current_swing_high': float,
                'current_swing_low': float,
                'market_structure': str  # 'HH_HL', 'LH_LL', 'RANGE'
            }
        """
        if len(ohlcv) < 50:
            logger.warning(f"{symbol}: Insufficient HTF data ({len(ohlcv)} bars)")
            return self._default_structure()

        # 1. Detectar swing highs/lows
        swing_highs, swing_lows = self._detect_swings(ohlcv)

        # 2. Analizar market structure (HH/HL vs LH/LL)
        market_structure = self._analyze_market_structure(swing_highs, swing_lows)

        # 3. Determinar trend direction y strength
        trend_direction, trend_strength = self._determine_trend(
            ohlcv, swing_highs, swing_lows, market_structure
        )

        structure = {
            'trend_direction': trend_direction,
            'trend_strength': round(trend_strength, 4),
            'swing_highs': swing_highs[-self.lookback_swings:],
            'swing_lows': swing_lows[-self.lookback_swings:],
            'current_swing_high': swing_highs[-1] if swing_highs else None,
            'current_swing_low': swing_lows[-1] if swing_lows else None,
            'market_structure': market_structure
        }

        self.structure_cache[symbol] = structure
        return structure

    def _detect_swings(self, ohlcv: pd.DataFrame) -> Tuple[List[float], List[float]]:
        """
        Detecta swing highs y swing lows usando ventana móvil.

        Swing High: high[i] > high[i±window] para todos los vecinos
        Swing Low: low[i] < low[i±window] para todos los vecinos
        """
        highs = ohlcv['high'].values
        lows = ohlcv['low'].values
        n = len(ohlcv)
        w = self.swing_window

        swing_highs = []
        swing_lows = []

        for i in range(w, n - w):
            # Swing high
            if all(highs[i] > highs[j] for j in range(i - w, i + w + 1) if j != i):
                swing_highs.append(highs[i])

            # Swing low
            if all(lows[i] < lows[j] for j in range(i - w, i + w + 1) if j != i):
                swing_lows.append(lows[i])

        return swing_highs, swing_lows

    def _analyze_market_structure(self, swing_highs: List[float],
                                  swing_lows: List[float]) -> str:
        """
        Analiza secuencia de swings para determinar estructura.

        HH/HL (Higher Highs, Higher Lows) → BULLISH structure
        LH/LL (Lower Highs, Lower Lows) → BEARISH structure
        Mixto → RANGE
        """
        if len(swing_highs) < 3 or len(swing_lows) < 3:
            return 'RANGE'

        recent_highs = swing_highs[-3:]
        recent_lows = swing_lows[-3:]

        # Verificar HH (highs crecientes)
        hh = all(recent_highs[i] < recent_highs[i + 1] for i in range(len(recent_highs) - 1))
        # Verificar HL (lows crecientes)
        hl = all(recent_lows[i] < recent_lows[i + 1] for i in range(len(recent_lows) - 1))

        # Verificar LH (highs decrecientes)
        lh = all(recent_highs[i] > recent_highs[i + 1] for i in range(len(recent_highs) - 1))
        # Verificar LL (lows decrecientes)
        ll = all(recent_lows[i] > recent_lows[i + 1] for i in range(len(recent_lows) - 1))

        if hh and hl:
            return 'HH_HL'  # Bullish structure
        elif lh and ll:
            return 'LH_LL'  # Bearish structure
        else:
            return 'RANGE'

    def _determine_trend(self, ohlcv: pd.DataFrame, swing_highs: List[float],
                        swing_lows: List[float], market_structure: str) -> Tuple[str, float]:
        """
        Determina trend direction y strength.

        Combina:
        - Market structure (HH/HL vs LH/LL)
        - Precio actual vs swings recientes
        - Volatilidad y rango

        Returns:
            (trend_direction, trend_strength)
        """
        current_price = ohlcv['close'].iloc[-1]

        # Usar market structure como base
        if market_structure == 'HH_HL':
            base_direction = 'BULLISH'
            base_strength = 0.7
        elif market_structure == 'LH_LL':
            base_direction = 'BEARISH'
            base_strength = 0.7
        else:
            base_direction = 'RANGE'
            base_strength = 0.3

        # Ajustar por posición de precio actual vs swings
        if swing_highs and swing_lows:
            recent_high = max(swing_highs[-3:]) if len(swing_highs) >= 3 else swing_highs[-1]
            recent_low = min(swing_lows[-3:]) if len(swing_lows) >= 3 else swing_lows[-1]

            price_position = (current_price - recent_low) / (recent_high - recent_low + 1e-8)

            if price_position > 0.7 and base_direction != 'BEARISH':
                base_strength = min(base_strength + 0.2, 1.0)
            elif price_position < 0.3 and base_direction != 'BULLISH':
                base_strength = min(base_strength + 0.2, 1.0)

        return base_direction, base_strength

    def get_trend_bias(self, symbol: str) -> int:
        """
        Obtiene bias de tendencia simplificado.

        Returns:
            1 (bullish), -1 (bearish), 0 (range)
        """
        if symbol not in self.structure_cache:
            return 0

        direction = self.structure_cache[symbol]['trend_direction']
        if direction == 'BULLISH':
            return 1
        elif direction == 'BEARISH':
            return -1
        else:
            return 0

    def _default_structure(self) -> Dict:
        """Estructura por defecto cuando no hay datos suficientes."""
        return {
            'trend_direction': 'RANGE',
            'trend_strength': 0.3,
            'swing_highs': [],
            'swing_lows': [],
            'current_swing_high': None,
            'current_swing_low': None,
            'market_structure': 'RANGE'
        }
