
================================================================================
DATA AND ETL
Fuentes de Datos y Pipeline
================================================================================

FUENTES
-------

Primaria: MetaTrader5
  - Tipo: Broker feed en tiempo real
  - Timeframe: M1 (1 minuto)
  - Método: mt5.copy_rates_from_pos(symbol, TIMEFRAME_M1, start, count)
  - Latencia: <100ms típica
  - Disponibilidad: Durante horas de mercado

Símbolos:
  - Forex: EURUSD, GBPUSD, USDJPY, AUDUSD, USDCAD, USDCHF, NZDUSD, EURGBP
  - Metales: XAUUSD
  - Cripto: BTCUSD, ETHUSD

PERÍODOS
--------

Lookback: 500 barras (8.3 horas de datos M1)
Mínimo operativo: 100 barras
Retención: No hay persistencia local (solo logs)

FORMATOS
--------

Raw MT5:
  numpy structured array con campos:
  - time: int (epoch seconds)
  - open, high, low, close: float
  - tick_volume, spread, real_volume: int/float

Transformado (pd.DataFrame):
  - time: datetime
  - open, high, low, close: float
  - volume: float (= tick_volume)
  - symbol: str

POLÍTICAS DE CALIDAD
--------------------

Validaciones pre-feature:
  1. len(data) >= 100
  2. No NaN en OHLC
  3. Volume >= 0
  4. High >= Low
  5. High >= Open, Close
  6. Low <= Open, Close

Si falla validación:
  - Log warning
  - Skip features para ese símbolo
  - Continuar con siguiente

Handling de gaps:
  - No hay lógica de gap filling
  - Data "as-is" del broker

REHIDRATACIÓN HISTÓRICA
------------------------

No implementada actualmente.

Target:
  - PostgreSQL para histórico M1
  - Backfill on-demand
  - Schema: (symbol, time, OHLCV)
  - Índices: (symbol, time) compound

Procedimiento:
  1. mt5.copy_rates_range(symbol, timeframe, date_from, date_to)
  2. Validar data
  3. INSERT INTO historical_data
  4. Verificar integridad
