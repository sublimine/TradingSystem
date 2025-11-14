"""
LTF Timing Executor - Low Timeframe Timing (M1)

MANDATO 15: Timing de entrada en LTF institucional.

Entry triggers: BOS, FVG fill, mitigation zones.
"""

import pandas as pd
from typing import Dict, Optional, List
import logging

logger = logging.getLogger(__name__)


class LTFTimingExecutor:
    """Detecta timing de entrada en low timeframes (M1)."""

    def __init__(self, config: Dict):
        self.fvg_lookback = config.get('fvg_lookback', 10)
        self.cache: Dict[str, Dict] = {}
        logger.info(f"LTFTimingExecutor init")

    def analyze(self, symbol: str, df: pd.DataFrame) -> Dict:
        """
        Analizar timing LTF.

        Returns:
            {
                'fvgs': List[Dict],  # Fair Value Gaps
                'entry_triggers': List[str],
                'timing_score': float [0-1]
            }
        """
        if len(df) < 3:
            return self._empty_result()

        fvgs = self._identify_fvgs(df)
        triggers = self._detect_triggers(df, fvgs)

        timing_score = 0.7 if triggers else 0.3

        result = {
            'fvgs': fvgs[-3:],
            'entry_triggers': triggers,
            'timing_score': timing_score
        }

        self.cache[symbol] = result
        return result

    def _identify_fvgs(self, df: pd.DataFrame) -> List[Dict]:
        """
        Identificar Fair Value Gaps (FVG).

        FVG = gap entre velas consecutivas sin solapamiento.
        """
        fvgs = []
        for i in range(1, len(df) - 1):
            prev = df.iloc[i-1]
            curr = df.iloc[i]
            next_c = df.iloc[i+1]

            # Bullish FVG: gap entre prev.high y next.low
            if prev['high'] < next_c['low']:
                fvgs.append({
                    'type': 'BULLISH_FVG',
                    'high': next_c['low'],
                    'low': prev['high'],
                    'index': i
                })

            # Bearish FVG: gap entre prev.low y next.high
            if prev['low'] > next_c['high']:
                fvgs.append({
                    'type': 'BEARISH_FVG',
                    'high': prev['low'],
                    'low': next_c['high'],
                    'index': i
                })

        return fvgs

    def _detect_triggers(self, df: pd.DataFrame, fvgs: List[Dict]) -> List[str]:
        """Detectar entry triggers."""
        triggers = []

        if not fvgs:
            return triggers

        # Check si precio actual está en FVG (mitigation)
        current_price = df['close'].iloc[-1]
        for fvg in fvgs[-3:]:
            if fvg['low'] <= current_price <= fvg['high']:
                triggers.append(f"{fvg['type']}_MITIGATION")

        return triggers

    def _empty_result(self) -> Dict:
        return {'fvgs': [], 'entry_triggers': [], 'timing_score': 0.5}

    def get_cached(self, symbol: str) -> Optional[Dict]:
        return self.cache.get(symbol)
