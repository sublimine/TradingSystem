"""
MultiFrame Orchestrator - Multi-Timeframe Synthesis

Orquesta análisis HTF + MTF para producir:
- multiframe_score [0-1]: Alineación temporal completa
- mtf_confluence: Confluencia específica de timeframes
- structure_alignment: Alineación estructural

Score alto → HTF y MTF alineados, contexto favorable
Score bajo → Conflicto temporal, evitar operación
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Optional
import logging

from .htf_analyzer import HTFStructureAnalyzer
from .mtf_validator import MTFContextValidator

logger = logging.getLogger(__name__)


class MultiFrameOrchestrator:
    """
    Orquestador de análisis multi-temporal.

    Combina:
    - HTF trend direction y strength
    - MTF context validation
    - Structure alignment

    Output: multiframe_score [0-1] para QualityScorer
    """

    def __init__(self, config: Dict):
        """
        Inicializar orchestrator.

        Args:
            config: {
                'htf': {...},  # Config para HTFStructureAnalyzer
                'mtf': {...},  # Config para MTFContextValidator
                'weights': {
                    'htf_trend': float,  # default: 0.50
                    'mtf_alignment': float,  # default: 0.30
                    'structure_alignment': float  # default: 0.20
                }
            }
        """
        htf_config = config.get('htf', {
            'lookback_swings': 10,
            'range_threshold': 0.3
        })
        mtf_config = config.get('mtf', {
            'poi_lookback': 20,
            'min_poi_size': 5
        })

        self.htf_analyzer = HTFStructureAnalyzer(htf_config)
        self.mtf_validator = MTFContextValidator(mtf_config)

        # Pesos institucionales
        weights = config.get('weights', {})
        self.weight_htf = weights.get('htf_trend', 0.50)
        self.weight_mtf = weights.get('mtf_alignment', 0.30)
        self.weight_structure = weights.get('structure_alignment', 0.20)

        logger.info(f"MultiFrameOrchestrator initialized: "
                   f"htf={self.weight_htf}, mtf={self.weight_mtf}, struct={self.weight_structure}")

    def analyze_multiframe(self, symbol: str, htf_ohlcv: pd.DataFrame,
                          mtf_ohlcv: pd.DataFrame, current_price: float,
                          signal_direction: Optional[int] = None) -> Dict:
        """
        Analiza estructura multi-temporal completa.

        Args:
            symbol: Símbolo
            htf_ohlcv: OHLCV de HTF (H4 o D1)
            mtf_ohlcv: OHLCV de MTF (M15 o M5)
            current_price: Precio actual
            signal_direction: Dirección de señal propuesta (1=long, -1=short, None=neutral)

        Returns:
            {
                'multiframe_score': float [0-1],
                'mtf_confluence': float [0-1],
                'structure_alignment': float [0-1],
                'htf_structure': Dict,
                'mtf_context': Dict,
                'conflicts': List[str],  # Conflictos detectados
                'recommendation': str  # 'APPROVE', 'REJECT', 'CAUTION'
            }
        """
        # 1. Analizar HTF structure
        htf_structure = self.htf_analyzer.analyze_structure(symbol, htf_ohlcv)
        htf_bias = self.htf_analyzer.get_trend_bias(symbol)

        # 2. Validar MTF context
        mtf_context = self.mtf_validator.validate_context(
            symbol, mtf_ohlcv, htf_bias, current_price
        )

        # 3. Calcular scores componentes
        htf_score = self._calculate_htf_score(htf_structure, signal_direction)
        mtf_alignment = mtf_context['mtf_alignment']
        structure_alignment = self._calculate_structure_alignment(
            htf_structure, mtf_context, current_price
        )

        # 4. Score composite
        multiframe_score = (
            self.weight_htf * htf_score +
            self.weight_mtf * mtf_alignment +
            self.weight_structure * structure_alignment
        )

        # 5. Detectar conflictos
        conflicts = self._detect_conflicts(htf_structure, mtf_context, signal_direction)

        # 6. Recomendación
        recommendation = self._make_recommendation(multiframe_score, conflicts)

        return {
            'multiframe_score': round(multiframe_score, 4),
            'mtf_confluence': round(mtf_alignment, 4),
            'structure_alignment': round(structure_alignment, 4),
            'htf_structure': htf_structure,
            'mtf_context': mtf_context,
            'conflicts': conflicts,
            'recommendation': recommendation
        }

    def _calculate_htf_score(self, htf_structure: Dict,
                            signal_direction: Optional[int]) -> float:
        """
        Calcula score de HTF.

        Score alto si:
        - HTF trend strength alto
        - Signal direction alineado con HTF (si se proporciona)
        """
        trend_strength = htf_structure['trend_strength']

        # Si hay dirección de señal, verificar alineación
        if signal_direction is not None:
            trend_direction = htf_structure['trend_direction']
            if trend_direction == 'BULLISH' and signal_direction == 1:
                alignment_bonus = 0.3
            elif trend_direction == 'BEARISH' and signal_direction == -1:
                alignment_bonus = 0.3
            elif trend_direction == 'RANGE':
                alignment_bonus = 0.0
            else:
                # Conflicto: señal contra HTF
                alignment_bonus = -0.5

            htf_score = trend_strength + alignment_bonus
        else:
            htf_score = trend_strength

        return np.clip(htf_score, 0.0, 1.0)

    def _calculate_structure_alignment(self, htf_structure: Dict,
                                       mtf_context: Dict, current_price: float) -> float:
        """
        Calcula alineación estructural (proximidad a niveles clave).

        Score alto si:
        - Cerca de POI MTF
        - Cerca de swing level HTF
        """
        # Componente 1: Distancia a POI (MTF)
        poi_distance = mtf_context.get('poi_distance_normalized', 0.5)
        poi_score = 1.0 - poi_distance  # Invertir: cerca = score alto

        # Componente 2: Distancia a swing level (HTF)
        swing_score = 0.5  # Default neutral
        swing_high = htf_structure.get('current_swing_high')
        swing_low = htf_structure.get('current_swing_low')

        if swing_high and swing_low:
            swing_range = swing_high - swing_low
            if swing_range > 0:
                # Distancia al nivel más cercano
                dist_to_high = abs(current_price - swing_high)
                dist_to_low = abs(current_price - swing_low)
                min_dist = min(dist_to_high, dist_to_low)

                # Normalizar
                dist_normalized = min_dist / swing_range
                swing_score = 1.0 - min(dist_normalized, 1.0)

        # Promediar componentes
        structure_alignment = (poi_score * 0.6 + swing_score * 0.4)
        return structure_alignment

    def _detect_conflicts(self, htf_structure: Dict, mtf_context: Dict,
                         signal_direction: Optional[int]) -> List[str]:
        """
        Detecta conflictos entre timeframes.

        Returns:
            Lista de conflictos detectados
        """
        conflicts = []

        # Conflicto 1: MTF alignment bajo con HTF
        if mtf_context['mtf_alignment'] < 0.3:
            conflicts.append("MTF_HTF_MISALIGNMENT")

        # Conflicto 2: Señal contra HTF trend
        if signal_direction is not None:
            trend = htf_structure['trend_direction']
            if (trend == 'BULLISH' and signal_direction == -1) or \
               (trend == 'BEARISH' and signal_direction == 1):
                conflicts.append("SIGNAL_AGAINST_HTF_TREND")

        # Conflicto 3: No hay POIs válidos en MTF
        if not mtf_context.get('context_valid', False):
            conflicts.append("MTF_CONTEXT_INVALID")

        return conflicts

    def _make_recommendation(self, multiframe_score: float,
                            conflicts: List[str]) -> str:
        """
        Genera recomendación basada en score y conflictos.

        Returns:
            'APPROVE', 'CAUTION', 'REJECT'
        """
        # Rechazo automático si hay conflicto crítico
        if "SIGNAL_AGAINST_HTF_TREND" in conflicts:
            return 'REJECT'

        # Por score
        if multiframe_score >= 0.7:
            return 'APPROVE'
        elif multiframe_score >= 0.4:
            return 'CAUTION'
        else:
            return 'REJECT'

    def get_multiframe_score(self, symbol: str, htf_ohlcv: pd.DataFrame,
                            mtf_ohlcv: pd.DataFrame, current_price: float) -> float:
        """
        Obtiene solo el score composite [0-1].

        Returns:
            multiframe_score [0-1]
        """
        result = self.analyze_multiframe(symbol, htf_ohlcv, mtf_ohlcv, current_price)
        return result['multiframe_score']

    def validate_signal_direction(self, symbol: str, signal_direction: int,
                                  htf_ohlcv: pd.DataFrame) -> bool:
        """
        Valida rápidamente si dirección de señal es compatible con HTF.

        Returns:
            True si compatible, False si conflicto
        """
        htf_structure = self.htf_analyzer.analyze_structure(symbol, htf_ohlcv)
        trend = htf_structure['trend_direction']

        if trend == 'RANGE':
            return True  # En rango, cualquier dirección es válida

        if (trend == 'BULLISH' and signal_direction == 1) or \
           (trend == 'BEARISH' and signal_direction == -1):
            return True

        return False
