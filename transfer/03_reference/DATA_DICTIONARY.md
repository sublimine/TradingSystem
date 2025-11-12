
================================================================================
DATA DICTIONARY
Diccionario de Datos
================================================================================

MARKET DATA (pd.DataFrame)
--------------------------

time: datetime
  - Timestamp de la barra
  - Timezone: Broker (UTC típicamente)
  - Rango: Histórico disponible

open: float
  - Precio de apertura de la barra
  - Unidad: Puntos de precio del símbolo
  - Rango: >0

high: float
  - Precio máximo de la barra
  - Constraint: >= max(open, close)
  - Unidad: Puntos de precio

low: float
  - Precio mínimo de la barra
  - Constraint: <= min(open, close)
  - Unidad: Puntos de precio

close: float
  - Precio de cierre de la barra
  - Unidad: Puntos de precio

volume: float
  - Volumen de la barra (tick_volume)
  - Unidad: Ticks
  - Rango: >=0

symbol: str
  - Identificador del símbolo
  - Formato: "<pair>.pro" o "<symbol>"
  - Ejemplos: "EURUSD.pro", "XAUUSD.pro"

FEATURES (dict)
---------------

atr: float
  - Average True Range
  - Unidad: Puntos de precio
  - Rango: >0
  - Semántica: Volatilidad promedio

rsi: float
  - Relative Strength Index
  - Unidad: Porcentaje
  - Rango: [0, 100]
  - Semántica: Momentum relativo

swing_high_levels: List[float]
  - Niveles de swing highs recientes
  - Unidad: Puntos de precio
  - Semántica: Resistencias potenciales

swing_low_levels: List[float]
  - Niveles de swing lows recientes
  - Unidad: Puntos de precio
  - Semántica: Soportes potenciales

cumulative_volume_delta: float
  - CVD acumulado
  - Unidad: Volumen neto
  - Rango: (-∞, +∞)
  - Semántica: Presión neta compradora/vendedora

vpin: float
  - Volume-Synchronized Probability of Informed Trading
  - Unidad: Probabilidad
  - Rango: [0.0, 1.0]
  - Semántica: Toxicidad del flujo

volatility_regime: int
  - Régimen de volatilidad
  - Valores: 0 (low) | 1 (high)
  - Semántica: Estado de volatilidad actual

order_book_imbalance: float
  - OBI
  - Rango: [-1.0, 1.0]
  - Semántica: Desbalance compra/venta

momentum_quality: float
  - Calidad del momentum
  - Rango: [0.0, 1.0]
  - Semántica: Consistencia direccional

spread: float
  - Spread promedio
  - Unidad: Puntos de precio
  - Semántica: Costo de transacción

SIGNAL (object)
---------------

symbol: str
  - Símbolo para operar
  - Formato: Mismo que market data

direction: str
  - Dirección de la operación
  - Valores: 'LONG' | 'SHORT'

entry_price: float
  - Precio de entrada objetivo
  - Unidad: Puntos de precio

stop_loss: float
  - Precio de stop loss
  - Constraint: != entry_price

take_profit: float
  - Precio de take profit
  - Constraint: != entry_price

strategy_name: str
  - Nombre de la estrategia que generó la señal

timestamp: datetime
  - Momento de generación de la señal
