
================================================================================
FEATURES CATALOG
Catálogo Completo de Features Calculados
================================================================================

TECHNICAL INDICATORS
--------------------

1. ATR (Average True Range)
   Módulo: src/features/technical_indicators.py
   Función: calculate_atr(high, low, close, period=14)
   Fórmula: EMA(true_range, period) donde true_range = max(high-low, abs(high-close_prev), abs(low-close_prev))
   Inputs: Series[float] high, low, close
   Output: Series[float] ATR values
   Ventana: 14 periodos
   Unidad: Puntos de precio
   Supuestos: Data continua, sin gaps >10%
   Validación: ATR > 0, isfinite

2. RSI (Relative Strength Index)
   Función: calculate_rsi(close, period=14)
   Fórmula: 100 - (100 / (1 + RS)) donde RS = avg_gain / avg_loss
   Inputs: Series[float] close
   Output: Series[float] RSI (0-100)
   Ventana: 14 periodos
   Unidad: Porcentaje (0-100)
   Validación: 0 <= RSI <= 100

3. Swing Points
   Función: identify_swing_points(series, order=5)
   Lógica: Detecta máximos/mínimos locales usando argrelextrema
   Inputs: Series[float] high o low
   Output: Tuple[ndarray, ndarray] (swing_highs_indices, swing_lows_indices)
   Ventana: order*2+1 (11 con order=5)
   Validación: Índices válidos, no duplicados

ORDER FLOW
----------

4. VPIN (Volume-Synchronized Probability of Informed Trading)
   Módulo: src/features/order_flow.py
   Clase: VPINCalculator
   Método: get_current_vpin() -> float
   Fórmula: abs(buy_volume - sell_volume) / total_volume over buckets
   Inputs: add_trade(volume, direction) por cada barra
   Output: float (0.0-1.0)
   Ventana: Últimas 50 barras
   Unidad: Probabilidad (0-1)
   Supuestos: Volume > 0, direction ±1
   Validación: 0 <= VPIN <= 1

5. Signed Volume
   Función: calculate_signed_volume(close, volume)
   Fórmula: +volume si uptick, -volume si downtick
   Inputs: Series[float] close, volume
   Output: Series[float] signed volume
   Ventana: Por barra
   Validación: abs(signed) == volume

6. Cumulative Volume Delta (CVD)
   Cálculo: signed_volume.sum()
   Inputs: Series[float] signed_volume
   Output: float
   Ventana: Todas las barras disponibles
   Validación: isfinite

STATISTICAL MODELS
------------------

7. Realized Volatility
   Módulo: src/features/statistical_models.py
   Función: calculate_realized_volatility(returns, window=20)
   Fórmula: std(returns) * sqrt(periods_per_day)
   Inputs: Series[float] returns (close.pct_change())
   Output: Series[float] volatility
   Ventana: 20 periodos
   Unidad: Anualizada
   Validación: vol >= 0

8. Volatility Regime
   Lógica: 1 if recent_vol > mean_vol else 0
   Inputs: realized_volatility
   Output: int (0 o 1)
   Ventana: 60 periodos para promedio
   Validación: regime in [0, 1]

FEATURES DERIVADOS (en motor)
------------------------------

9. Order Book Imbalance
   Fórmula: (buy_vol - sell_vol) / (buy_vol + sell_vol)
   Cálculo: Comparando close vs open por barra
   Output: float (-1.0 a 1.0)
   Validación: -1 <= imbalance <= 1

10. Momentum Quality
    Actual: Hardcoded 0.7
    Target: Consistencia de dirección sobre ventana
    Validación: 0 <= quality <= 1

11. Spread
    Fórmula: mean(high - low)
    Output: float
    Validación: spread >= 0

DEPENDENCIES MATRIX
-------------------

Feature         | Depends On        | Used By (Strategies)
----------------|-------------------|---------------------
ATR             | OHLC              | ALL
RSI             | Close             | SOME
Swing Points    | High/Low          | ALL
VPIN            | Volume, Direction | HIGH PRIORITY
Signed Volume   | Close, Volume     | HIGH PRIORITY
CVD             | Signed Volume     | HIGH PRIORITY
Realized Vol    | Returns           | REGIME DETECTION
Volatility Regime| Realized Vol     | FILTERS
OB Imbalance    | OHLC, Volume      | CONFIRMATION
Momentum Quality| Close             | FILTERS
Spread          | High, Low         | COST ESTIMATION
