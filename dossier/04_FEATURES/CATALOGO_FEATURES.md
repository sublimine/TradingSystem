
================================================================================
FEATURES - CATÁLOGO COMPLETO
================================================================================

TECHNICAL INDICATORS (src/features/technical_indicators.py)
-----------------------------------------------------------

1. ATR (Average True Range)
   Función: calculate_atr(high, low, close, period=14)
   Fórmula: Promedio móvil de true range
   Ventana: 14 periodos
   Dependencia: high, low, close
   Rango esperado: > 0, proporcional a volatilidad
   Fallo típico: NaN si <14 barras
   Criticidad: ALTA (usado por múltiples estrategias)

2. RSI (Relative Strength Index)
   Función: calculate_rsi(close, period=14)
   Fórmula: 100 - (100 / (1 + RS))
   Ventana: 14 periodos
   Dependencia: close
   Rango esperado: 0-100
   Fallo típico: NaN si <14 barras
   Criticidad: MEDIA (informativo, no decisión primaria)

3. Swing Points
   Función: identify_swing_points(series, order=5)
   Lógica: Detecta máximos/mínimos locales
   Ventana: order * 2 + 1 (11 barras con order=5)
   Dependencia: high o low
   Rango esperado: índices de barras
   Fallo típico: Pocos puntos si mercado lateral
   Criticidad: ALTA (zonas de liquidez)

ORDER FLOW (src/features/order_flow.py)
----------------------------------------

4. VPIN (Volume-Synchronized Probability of Informed Trading)
   Clase: VPINCalculator
   Método: get_current_vpin()
   Lógica: Desbalance de volumen en buckets
   Ventana: últimas 50 barras
   Dependencia: volume, direction (buy/sell)
   Rango esperado: 0.0-1.0
   Fallo típico: 0 si no hay datos suficientes
   Criticidad: ALTA (toxicidad de flujo)

5. Signed Volume
   Función: calculate_signed_volume(close, volume)
   Fórmula: +volume si up-tick, -volume si down-tick
   Ventana: barra individual
   Dependencia: close, volume
   Rango esperado: ±volume
   Fallo típico: None
   Criticidad: ALTA (dirección del flujo)

6. Cumulative Volume Delta (CVD)
   Cálculo: sum(signed_volume)
   Ventana: acumulativa
   Dependencia: signed_volume
   Rango esperado: ±∞ (acumulativo)
   Fallo típico: None
   Criticidad: ALTA (presión neta)

STATISTICAL MODELS (src/features/statistical_models.py)
-------------------------------------------------------

7. Realized Volatility
   Función: calculate_realized_volatility(returns, window=20)
   Fórmula: std(returns) * sqrt(window)
   Ventana: 20 periodos
   Dependencia: returns (close.pct_change())
   Rango esperado: > 0
   Fallo típico: NaN si <20 barras
   Criticidad: ALTA (regímenes)

8. Volatility Regime
   Lógica: 1 si vol > avg, 0 si vol <= avg
   Ventana: 60 barras para promedio
   Dependencia: realized_volatility
   Rango esperado: 0 o 1
   Fallo típico: 0 por defecto
   Criticidad: MEDIA (filtro)

FEATURES DERIVADOS (calculados en motor)
-----------------------------------------

9. Order Book Imbalance
   Fórmula: (buy_vol - sell_vol) / (buy_vol + sell_vol)
   Ventana: últimas barras (variable)
   Rango esperado: -1.0 a 1.0
   Criticidad: ALTA

10. Momentum Quality
    Hardcoded: 0.7 (placeholder)
    Futuro: Cálculo real basado en consistencia
    Criticidad: MEDIA

11. Spread
    Fórmula: mean(high - low)
    Ventana: todas las barras disponibles
    Rango esperado: > 0
    Criticidad: BAJA (informativo)

MATRIZ DE DEPENDENCIAS (Estrategia → Features)
-----------------------------------------------
Todas las estrategias reciben el dict completo de features.
Cada una decide qué features usar internamente.

Críticos para mayoría:
- atr
- swing_high_levels / swing_low_levels
- cumulative_volume_delta
- vpin

Auxiliares:
- rsi
- volatility_regime
- order_book_imbalance
