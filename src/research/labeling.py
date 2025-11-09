"""
Triple Barrier Labeling - Labeling sin data leakage para ML
Implementa método de triple barrier con meta-labeling opcional.
"""

import logging
import numpy as np
import pandas as pd
from typing import Optional, Tuple

logger = logging.getLogger(__name__)


def triple_barrier_label(
    prices: pd.Series,
    upper_threshold: float,
    lower_threshold: float,
    max_holding_bars: int,
    side: Optional[pd.Series] = None
) -> pd.DataFrame:
    """
    Aplica triple barrier method para labeling.
    
    Para cada observación, proyecta hacia adelante y determina
    qué barrera se toca primero:
    - Upper barrier: ganancia objetivo
    - Lower barrier: pérdida máxima
    - Time barrier: máximo holding period
    
    Args:
        prices: Serie de precios (close)
        upper_threshold: Ganancia objetivo (ej: 0.002 = 0.2%)
        lower_threshold: Pérdida máxima (ej: -0.001 = -0.1%)
        max_holding_bars: Máximo de barras hacia adelante
        side: Lado de la operación (1=long, -1=short, None=ambos)
        
    Returns:
        DataFrame con labels y metadata
    """
    logger.info(
        f"Triple barrier labeling: "
        f"upper={upper_threshold:.4f}, lower={lower_threshold:.4f}, "
        f"max_bars={max_holding_bars}"
    )
    
    labels = []
    
    for i in range(len(prices) - max_holding_bars):
        entry_price = prices.iloc[i]
        
        # Determinar lado
        if side is not None:
            position_side = side.iloc[i]
        else:
            position_side = 1  # Default long
        
        # Proyectar hacia adelante
        forward_prices = prices.iloc[i+1:i+1+max_holding_bars]
        
        if position_side == 1:  # Long
            # Upper barrier = ganancia
            upper_barrier = entry_price * (1 + upper_threshold)
            # Lower barrier = pérdida
            lower_barrier = entry_price * (1 + lower_threshold)
        else:  # Short
            # Invertir barreras para short
            upper_barrier = entry_price * (1 - lower_threshold)
            lower_barrier = entry_price * (1 - upper_threshold)
        
        # Encontrar primera barrera tocada
        hit_upper = forward_prices >= upper_barrier
        hit_lower = forward_prices <= lower_barrier
        
        first_upper = hit_upper.idxmax() if hit_upper.any() else None
        first_lower = hit_lower.idxmax() if hit_lower.any() else None
        
        # Determinar qué pasó primero
        if first_upper is not None and first_lower is not None:
            if forward_prices.index.get_loc(first_upper) < forward_prices.index.get_loc(first_lower):
                label = 1  # Ganador
                exit_idx = forward_prices.index.get_loc(first_upper)
                barrier_hit = 'upper'
            else:
                label = -1  # Perdedor
                exit_idx = forward_prices.index.get_loc(first_lower)
                barrier_hit = 'lower'
        elif first_upper is not None:
            label = 1
            exit_idx = forward_prices.index.get_loc(first_upper)
            barrier_hit = 'upper'
        elif first_lower is not None:
            label = -1
            exit_idx = forward_prices.index.get_loc(first_lower)
            barrier_hit = 'lower'
        else:
            # Time barrier alcanzada
            label = 0
            exit_idx = len(forward_prices) - 1
            barrier_hit = 'time'
        
        exit_price = forward_prices.iloc[exit_idx]
        holding_bars = exit_idx + 1
        
        # Calcular return realizado
        if position_side == 1:
            realized_return = (exit_price / entry_price - 1)
        else:
            realized_return = (entry_price / exit_price - 1)
        
        labels.append({
            'timestamp': prices.index[i],
            'entry_price': entry_price,
            'exit_price': exit_price,
            'label': label,
            'barrier_hit': barrier_hit,
            'holding_bars': holding_bars,
            'realized_return': realized_return,
            'side': position_side
        })
    
    df = pd.DataFrame(labels)
    df.set_index('timestamp', inplace=True)
    
    # Estadísticas
    label_counts = df['label'].value_counts()
    logger.info(
        f"Labels generated: "
        f"winners={label_counts.get(1, 0)}, "
        f"losers={label_counts.get(-1, 0)}, "
        f"neutral={label_counts.get(0, 0)}"
    )
    
    return df


def meta_labeling(
    primary_signals: pd.Series,
    prices: pd.Series,
    upper_threshold: float,
    lower_threshold: float,
    max_holding_bars: int
) -> pd.DataFrame:
    """
    Meta-labeling: entrena modelo para filtrar señales.
    
    En lugar de predecir dirección, predice si vale la pena
    ejecutar una señal generada por estrategia primaria.
    
    Args:
        primary_signals: Señales de estrategia base (1=long, -1=short, 0=neutral)
        prices: Serie de precios
        upper_threshold: Ganancia objetivo
        lower_threshold: Pérdida máxima
        max_holding_bars: Máximo holding period
        
    Returns:
        DataFrame con meta-labels
    """
    # Filtrar solo donde hay señal primaria
    signal_mask = primary_signals != 0
    filtered_signals = primary_signals[signal_mask]
    filtered_prices = prices[signal_mask]
    
    if len(filtered_signals) == 0:
        logger.warning("No primary signals found for meta-labeling")
        return pd.DataFrame()
    
    # Aplicar triple barrier solo a señales primarias
    labels = triple_barrier_label(
        filtered_prices,
        upper_threshold,
        lower_threshold,
        max_holding_bars,
        side=filtered_signals
    )
    
    # Convertir a meta-label binario: ¿ejecutar o no?
    # 1 = ejecutar (ganador), 0 = silenciar (perdedor o neutral)
    labels['meta_label'] = (labels['label'] == 1).astype(int)
    
    meta_counts = labels['meta_label'].value_counts()
    logger.info(
        f"Meta-labels: "
        f"execute={meta_counts.get(1, 0)}, "
        f"silence={meta_counts.get(0, 0)}"
    )
    
    return labels


def calculate_label_statistics(labels: pd.DataFrame) -> dict:
    """Calcula estadísticas de labels."""
    stats = {
        'total_labels': len(labels),
        'label_distribution': labels['label'].value_counts().to_dict(),
        'avg_holding_bars': labels['holding_bars'].mean(),
        'barrier_distribution': labels['barrier_hit'].value_counts().to_dict(),
        'avg_return_winners': labels[labels['label'] == 1]['realized_return'].mean(),
        'avg_return_losers': labels[labels['label'] == -1]['realized_return'].mean(),
    }
    
    return stats