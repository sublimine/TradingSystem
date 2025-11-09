
FEATURES Y DEPENDENCIAS - order_flow_toxicity
================================================================================

FEATURES CONSUMIDOS
-------------------
Método evaluate() recibe dict 'features' con:

REQUERIDOS:
- atr: float (Average True Range, periodo 14)
- rsi: float (Relative Strength Index, periodo 14)
- swing_high_levels: List[float] (últimos 20 swing highs)
- swing_low_levels: List[float] (últimos 20 swing lows)
- cumulative_volume_delta: float (CVD acumulado)
- vpin: float (Volume-Synchronized Probability, 0-1)
- volatility_regime: int (0=low, 1=high)
- order_book_imbalance: float (-1 a 1, buy/sell pressure)
- momentum_quality: float (0-1, calidad del momentum)
- spread: float (spread promedio del periodo)

CÁLCULO
-------
Ver: src/features/technical_indicators.py
     src/features/order_flow.py
     src/features/statistical_models.py

TOLERANCIA A NULOS
------------------
Si un feature falta o es None:
- Estrategia puede no generar señal
- No lanza excepción
- Log: evaluations++ pero signals=0

DATA MÍNIMA
-----------
500 barras recomendadas
100 barras mínimo absoluto
