"""
Order Flow Imbalance - Institutional Implementation
Implementación práctica para datos de barras OHLCV sin L2 completo.
"""
import pandas as pd
import numpy as np
from typing import Optional


def calculate_ofi(bars_df: pd.DataFrame, window_size: int = 20) -> pd.Series:
    """
    Calcula Order Flow Imbalance usando clasificación tick desde barras OHLCV.
    
    Sin datos de order book completo, aproximamos OFI usando:
    - Tick rule: comparar close vs midpoint para clasificar dirección
    - Volumen direccional: volumen * dirección
    - OFI acumulado: suma rolling de volumen direccional
    
    Args:
        bars_df: DataFrame con columnas 'high', 'low', 'close', 'volume'
        window_size: Ventana para calcular OFI rolling
    
    Returns:
        pd.Series: Valores de OFI donde positivo indica presión compradora,
                   negativo indica presión vendedora
    """
    if len(bars_df) < window_size:
        # Retornar Series vacío con índice del DataFrame original
        return pd.Series(0.0, index=bars_df.index, dtype=float)
    
    # Calcular punto medio de cada barra
    midpoint = (bars_df['high'] + bars_df['low']) / 2.0
    
    # Clasificación tick: +1 si close > midpoint (compra), -1 si close < midpoint (venta)
    tick_direction = np.sign(bars_df['close'] - midpoint)
    
    # Volumen direccional: volumen multiplicado por dirección
    signed_volume = bars_df['volume'] * tick_direction
    
    # OFI es la suma rolling del volumen direccional
    # Normalizar por la suma total de volumen en la ventana para hacer comparable
    ofi = signed_volume.rolling(window=window_size, min_periods=1).sum()
    total_volume = bars_df['volume'].rolling(window=window_size, min_periods=1).sum()

    # P1-003: Usar max() para validación robusta en lugar de epsilon pequeño
    # Normalizar OFI para que esté en rango [-1, 1]
    total_volume_safe = total_volume.where(total_volume > 1e-6, 1e-6)
    ofi_normalized = ofi / total_volume_safe

    # Reemplazar NaN con 0
    ofi_normalized = ofi_normalized.fillna(0.0)

    return ofi_normalized


def classify_trades_lee_ready(bars_df: pd.DataFrame) -> pd.DataFrame:
    """
    Clasificación Lee-Ready adaptada para barras OHLCV.
    
    Agrega columnas de volumen direccional al DataFrame:
    - buy_volume: volumen estimado de compras agresivas
    - sell_volume: volumen estimado de ventas agresivas
    """
    df = bars_df.copy()
    
    # Calcular punto medio
    midpoint = (df['high'] + df['low']) / 2.0
    
    # Clasificar cada barra
    is_buy = df['close'] > midpoint
    is_sell = df['close'] < midpoint
    
    # Asignar volumen
    df['buy_volume'] = np.where(is_buy, df['volume'], 0.0)
    df['sell_volume'] = np.where(is_sell, df['volume'], 0.0)
    
    # Barras donde close == midpoint: distribuir 50/50
    neutral = ~(is_buy | is_sell)
    df.loc[neutral, 'buy_volume'] = df.loc[neutral, 'volume'] / 2.0
    df.loc[neutral, 'sell_volume'] = df.loc[neutral, 'volume'] / 2.0
    
    return df
