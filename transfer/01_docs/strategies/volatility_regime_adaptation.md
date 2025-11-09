
================================================================================
ESTRATEGIA: volatility_regime_adaptation
================================================================================

IDENTIFICACIÓN
--------------
Módulo: strategies.volatility_regime_adaptation
Clase: VolatilityRegimeAdaptation
Archivo: src/strategies/volatility_regime_adaptation.py

ROL E HIPÓTESIS DE MERCADO
---------------------------
Estrategia institucional basada en microestructura de mercado.
Busca ineficiencias mediante análisis cuantitativo de flujo de órdenes,
zonas de liquidez y confirmación volumétrica institucional.

DEPENDENCIAS
------------
Features:
  - atr (crítico)
  - swing_high_levels, swing_low_levels (crítico)
  - cumulative_volume_delta
  - vpin
  - volatility_regime
  - order_book_imbalance

Estado compartido:
  - Ninguno (estrategia stateless por scan)

Objetos compartidos:
  - Ninguno (evaluación independiente)

CONTRATO
--------

Firma exacta:
  def evaluate(self, data: pd.DataFrame, features: dict) -> Signal | List[Signal] | None

Estructura de señal (keys obligatorias):
  - symbol: str
  - direction: 'LONG' | 'SHORT'
  - entry_price: float
  - stop_loss: float
  - take_profit: float
  - strategy_name: str
  - timestamp: datetime

Pre-condiciones:
  - len(data) >= 100
  - features dict contiene keys mínimos
  - data columnas válidas: open, high, low, close, volume

Post-condiciones:
  - Signal válido (validate() == True) o None
  - No modifica data ni features
  - No side effects

Invariantes:
  - stop_loss != entry_price
  - take_profit != entry_price
  - direction in ['LONG', 'SHORT']

PARÁMETROS
----------
(Extraídos de __init__)

Valor actual, rango válido, sensibilidad:
  [Parámetros específicos de la estrategia]
  Nota: Revisar código fuente para detalles exactos

LÓGICA PASO A PASO
------------------

1. Validar data disponible (len >= 100)
2. Extraer precio actual (data['close'].iloc[-1])
3. Evaluar condiciones de entrada:
   - [Condición 1 con umbral específico]
   - [Condición 2 con umbral específico]
   - [Condición N...]
4. Si todas las condiciones cumplen:
   - Calcular entry_price
   - Calcular stop_loss (basado en ATR)
   - Calcular take_profit (basado en ATR)
   - Crear Signal object
5. Validar señal (signal.validate())
6. Retornar Signal o None

MOTIVOS DE RECHAZO
------------------

Filtros que bloquean señal:
  1. Data insuficiente (<100 barras)
  2. Features incompletos (keys faltantes)
  3. Condiciones de mercado no cumplen umbrales
  4. ATR inválido o NaN
  5. Swing points insuficientes
  6. VPIN fuera de rango operativo

INTERACCIONES CON OTRAS ESTRATEGIAS
------------------------------------

Conflictos potenciales:
  - Ninguno (evaluación independiente)

Sinergias:
  - Confirmación implícita si múltiples estrategias
    coinciden en dirección del mismo símbolo

REGISTROS ESPERADOS
-------------------

Normal (sin señal):
  [No aparece en logs]
  stats['evaluations']++

Con señal:
  "SEÑAL GENERADA:"
  "  Estrategia: volatility_regime_adaptation"
  "  Simbolo: <symbol>"
  "  Direccion: <direction>"
  stats['signals']++

Con error:
  "ERROR evaluando volatility_regime_adaptation: <mensaje>"
  stats['errors']++

PRUEBAS MÍNIMAS
---------------

Casos que DEBEN disparar señal:
  1. Breakout confirmado con volumen 5x normal
  2. [Caso específico 2]
  3. [Caso específico N]

Casos que DEBEN bloquear señal:
  1. Data <100 barras
  2. ATR NaN
  3. [Condición umbral no cumplida]
