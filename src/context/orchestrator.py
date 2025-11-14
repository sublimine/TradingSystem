"""
MultiFrame Orchestrator - Main Coordinator

MANDATO 15: Orquestador de análisis multi-timeframe.

Combina HTF/MTF/LTF en multiframe_score [0-1].
"""

import pandas as pd
from typing import Dict, Optional
import logging
from .htf_structure import HTFStructureAnalyzer, Trend
from .mtf_context import MTFContextValidator
from .ltf_timing import LTFTimingExecutor

logger = logging.getLogger(__name__)


class MultiFrameOrchestrator:
    """Orquesta análisis HTF/MTF/LTF."""

    def __init__(self, config: Dict):
        self.htf = HTFStructureAnalyzer(config.get('htf', {}))
        self.mtf = MTFContextValidator(config.get('mtf', {}))
        self.ltf = LTFTimingExecutor(config.get('ltf', {}))

        # Pesos agregación
        weights = config.get('aggregation_weights', {})
        self.weight_htf = weights.get('htf', 0.50)
        self.weight_mtf = weights.get('mtf', 0.30)
        self.weight_ltf = weights.get('ltf', 0.20)

        logger.info(f"MultiFrameOrchestrator init: weights HTF={self.weight_htf}, "
                   f"MTF={self.weight_mtf}, LTF={self.weight_ltf}")

    def analyze(self, symbol: str, data_by_tf: Dict[str, pd.DataFrame]) -> Dict:
        """
        Analizar multi-timeframe.

        Args:
            symbol: Símbolo
            data_by_tf: {
                'H4': DataFrame,
                'M15': DataFrame,
                'M1': DataFrame
            }

        Returns:
            {
                'multiframe_score': float [0-1],
                'htf_analysis': Dict,
                'mtf_analysis': Dict,
                'ltf_analysis': Dict,
                'pois': List[float]  # Points of Interest
            }
        """
        # Analizar HTF
        htf_data = data_by_tf.get('H4')
        if htf_data is None:
            htf_data = data_by_tf.get('D1')
        if htf_data is None or len(htf_data) < 20:
            return self._empty_result()

        htf_result = self.htf.analyze(symbol, htf_data)

        # Analizar MTF
        mtf_data = data_by_tf.get('M15')
        if mtf_data is None:
            mtf_data = data_by_tf.get('M5')
        if mtf_data is not None and len(mtf_data) >= 20:
            mtf_result = self.mtf.analyze(symbol, mtf_data, htf_result['trend'].value)
        else:
            mtf_result = {'supply_zones': [], 'demand_zones': [], 'confluence': 0.5}

        # Analizar LTF
        ltf_data = data_by_tf.get('M1')
        if ltf_data is not None and len(ltf_data) >= 3:
            ltf_result = self.ltf.analyze(symbol, ltf_data)
        else:
            ltf_result = {'fvgs': [], 'entry_triggers': [], 'timing_score': 0.5}

        # Calcular multiframe_score
        mf_score = self._calculate_multiframe_score(htf_result, mtf_result, ltf_result)

        # Extraer POIs
        pois = self._extract_pois(htf_result, mtf_result, ltf_result)

        return {
            'multiframe_score': mf_score,
            'htf_analysis': htf_result,
            'mtf_analysis': mtf_result,
            'ltf_analysis': ltf_result,
            'pois': pois
        }

    def _calculate_multiframe_score(self, htf: Dict, mtf: Dict, ltf: Dict) -> float:
        """
        Calcular score agregado.

        HTF: trend_strength
        MTF: confluence
        LTF: timing_score
        """
        htf_score = htf['trend_strength']
        mtf_score = mtf['confluence']
        ltf_score = ltf['timing_score']

        mf_score = (
            self.weight_htf * htf_score +
            self.weight_mtf * mtf_score +
            self.weight_ltf * ltf_score
        )

        return max(0.0, min(1.0, mf_score))

    def _extract_pois(self, htf: Dict, mtf: Dict, ltf: Dict) -> list:
        """Extract Points of Interest."""
        pois = []

        # HTF key levels
        pois.extend(htf['key_levels'])

        # MTF zones
        for zone in mtf['supply_zones']:
            pois.append((zone['high'] + zone['low']) / 2)
        for zone in mtf['demand_zones']:
            pois.append((zone['high'] + zone['low']) / 2)

        # Dedup y sort
        if pois:
            pois = sorted(list(set(pois)))

        return pois[:10]  # Top 10 POIs

    def _empty_result(self) -> Dict:
        return {
            'multiframe_score': 0.5,
            'htf_analysis': {},
            'mtf_analysis': {},
            'ltf_analysis': {},
            'pois': []
        }

    def get_multiframe_score(self, symbol: str) -> float:
        """
        Get multiframe_score de cache o recalcular.

        Returns:
            Score [0-1]
        """
        # Intentar obtener de cache de HTF
        htf_cached = self.htf.get_cached(symbol)
        mtf_cached = self.mtf.get_cached(symbol)
        ltf_cached = self.ltf.get_cached(symbol)

        if htf_cached and mtf_cached and ltf_cached:
            return self._calculate_multiframe_score(htf_cached, mtf_cached, ltf_cached)

        return 0.5  # Default sin datos
