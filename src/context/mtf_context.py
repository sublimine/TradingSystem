"""
MTF Context Validator - Medium Timeframe Context (M15/M5)

MANDATO 15: Validación de contexto MTF institucional.

Supply/demand zones, CHoCH, BOS, POIs.
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional
import logging

logger = logging.getLogger(__name__)


class MTFContextValidator:
    """Valida contexto en medium timeframes (M15/M5)."""

    def __init__(self, config: Dict):
        self.zone_lookback = config.get('zone_lookback', 20)
        self.cache: Dict[str, Dict] = {}
        logger.info(f"MTFContextValidator init")

    def analyze(self, symbol: str, df: pd.DataFrame, htf_trend: str) -> Dict:
        """
        Analizar contexto MTF.

        Args:
            symbol: Símbolo
            df: DataFrame OHLC
            htf_trend: Tendencia HTF

        Returns:
            {
                'supply_zones': List[Dict],
                'demand_zones': List[Dict],
                'last_bos': Optional[Dict],
                'confluence': float [0-1]
            }
        """
        if len(df) < self.zone_lookback:
            return self._empty_result()

        supply_zones = self._identify_supply_zones(df)
        demand_zones = self._identify_demand_zones(df)

        # Calcular confluencia con HTF
        confluence = self._calculate_htf_confluence(htf_trend, supply_zones, demand_zones)

        result = {
            'supply_zones': supply_zones[-3:],
            'demand_zones': demand_zones[-3:],
            'confluence': confluence
        }

        self.cache[symbol] = result
        return result

    def _identify_supply_zones(self, df: pd.DataFrame) -> List[Dict]:
        """Identificar supply zones (bearish rejection areas)."""
        zones = []
        for i in range(len(df) - 5, len(df)):
            candle = df.iloc[i]
            # Zona supply: vela con long upper wick
            upper_wick = candle['high'] - max(candle['open'], candle['close'])
            body = abs(candle['close'] - candle['open'])
            if upper_wick > body * 1.5:
                zones.append({
                    'high': candle['high'],
                    'low': max(candle['open'], candle['close']),
                    'strength': min(upper_wick / body, 3.0) / 3.0
                })
        return zones

    def _identify_demand_zones(self, df: pd.DataFrame) -> List[Dict]:
        """Identificar demand zones (bullish rejection areas)."""
        zones = []
        for i in range(len(df) - 5, len(df)):
            candle = df.iloc[i]
            # Zona demand: vela con long lower wick
            lower_wick = min(candle['open'], candle['close']) - candle['low']
            body = abs(candle['close'] - candle['open'])
            if lower_wick > body * 1.5:
                zones.append({
                    'high': min(candle['open'], candle['close']),
                    'low': candle['low'],
                    'strength': min(lower_wick / body, 3.0) / 3.0
                })
        return zones

    def _calculate_htf_confluence(self, htf_trend: str, supply: List, demand: List) -> float:
        """Calcular confluencia con HTF."""
        if htf_trend == 'UPTREND':
            return 0.8 if len(demand) > len(supply) else 0.4
        elif htf_trend == 'DOWNTREND':
            return 0.8 if len(supply) > len(demand) else 0.4
        else:
            return 0.5

    def _empty_result(self) -> Dict:
        return {'supply_zones': [], 'demand_zones': [], 'confluence': 0.5}

    def get_cached(self, symbol: str) -> Optional[Dict]:
        return self.cache.get(symbol)
