"""
Metadata Builder - MANDATO 16 Integration Helper

Construye metadata enriquecida para QualityScorer a partir de:
- MicrostructureEngine
- MultiFrameOrchestrator
- Datos de estrategia

Elimina duplicaciÃ³n de cÃ³digo entre estrategias.
"""

import numpy as np
import pandas as pd
from typing import Dict, Optional


def build_enriched_metadata(
    base_metadata: Dict,
    symbol: str,
    current_price: float,
    signal_direction: int,  # 1=LONG, -1=SHORT
    market_data: pd.DataFrame,
    microstructure_engine: Optional[object] = None,
    multiframe_orchestrator: Optional[object] = None,
    signal_strength_value: Optional[float] = None,
    structure_reference_price: Optional[float] = None,
    structure_reference_size: Optional[float] = None
) -> Dict:
    """
    Construye metadata completa para QualityScorer.

    MANDATO 16: Integra microstructure + multiframe scores.

    Args:
        base_metadata: Metadata base de estrategia (legacy)
        symbol: SÃ­mbolo
        current_price: Precio actual
        signal_direction: 1 (LONG) o -1 (SHORT)
        market_data: DataFrame OHLCV
        microstructure_engine: MicrostructureEngine instance (optional)
        multiframe_orchestrator: MultiFrameOrchestrator instance (optional)
        signal_strength_value: Signal strength pre-calculado [0-1] (optional)
        structure_reference_price: Precio de referencia estructural (order block, nivel clave)
        structure_reference_size: TamaÃ±o de referencia (rango del nivel, sin indicadores de rango en fÃ³rmula)

    Returns:
        metadata enriquecida con:
        - signal_strength: [0-1]
        - mtf_confluence: [0-1]
        - structure_alignment: [0-1] (distancia normalizada, sin indicadores de rango)
        - microstructure_quality: [0-1]
        - regime_confidence: [0-1]
    """
    metadata = base_metadata.copy()

    # 1. Signal Strength
    if signal_strength_value is not None:
        metadata['signal_strength'] = round(signal_strength_value, 4)
    else:
        # Default: moderado
        metadata['signal_strength'] = 0.6

    # 2. Structure Alignment (distancia a nivel estructural, normalizada)
    if structure_reference_price is not None and structure_reference_size is not None:
        distance = abs(current_price - structure_reference_price)
        order_block_distance_normalized = min(distance / (structure_reference_size + 1e-8), 1.0)
        structure_alignment = 1.0 - order_block_distance_normalized
        metadata['structure_alignment'] = round(structure_alignment, 4)
        metadata['order_block_distance_normalized'] = round(order_block_distance_normalized, 4)
    else:
        # Sin referencia estructural clara
        metadata['structure_alignment'] = 0.5
        metadata['order_block_distance_normalized'] = 0.5

    # 3. Microstructure Quality (from MicrostructureEngine)
    if microstructure_engine:
        micro_state = microstructure_engine.get_detailed_state(symbol)
        metadata['microstructure_quality'] = micro_state['microstructure_score']
        metadata['vpin'] = micro_state['vpin']
        metadata['ofi'] = micro_state['ofi']
    else:
        # Fallback
        metadata['microstructure_quality'] = 0.5
        metadata['vpin'] = None
        metadata['ofi'] = None

    # 4. MTF Confluence + Regime Confidence (from MultiFrameOrchestrator)
    if multiframe_orchestrator and len(market_data) >= 50:
        htf_data = market_data.tail(200) if len(market_data) >= 200 else market_data
        mtf_data = market_data.tail(50)

        mf_result = multiframe_orchestrator.analyze_multiframe(
            symbol, htf_data, mtf_data, current_price, signal_direction
        )

        metadata['mtf_confluence'] = mf_result['mtf_confluence']
        metadata['multiframe_score'] = mf_result['multiframe_score']
        metadata['mf_conflicts'] = mf_result['conflicts']
        metadata['mf_recommendation'] = mf_result['recommendation']
        metadata['regime_confidence'] = mf_result['htf_structure']['trend_strength']
    else:
        # Fallback: derivar de tendencia simple
        if len(market_data) >= 20:
            closes = market_data['close'].tail(20).values
            slope = np.polyfit(range(len(closes)), closes, 1)[0]
            trend_strength = min(abs(slope) * 1000, 1.0)
            metadata['regime_confidence'] = round(trend_strength, 4)
        else:
            metadata['regime_confidence'] = 0.5

        metadata['mtf_confluence'] = 0.5

    return metadata
