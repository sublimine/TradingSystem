================================================================================
VOLUME 05 - STRATEGIES (9/9)
================================================================================

--------------------------------------------------------------------------------
ESTRATEGIA: breakout_volume_confirmation
--------------------------------------------------------------------------------

IDENTIFICACIÓN:
  Módulo: strategies.breakout_volume_confirmation
  Clase: BreakoutVolumeConfirmation
  Archivo: src/strategies/breakout_volume_confirmation.py

FIRMA:
  def evaluate(self, data: pd.DataFrame, features: dict) -> Signal | List[Signal] | None

OBJETO SIGNAL ESPERADO:
  - symbol: str
  - direction: 'LONG' | 'SHORT'
  - entry_price: float
  - stop_loss: float
  - take_profit: float
  - strategy_name: str
  - timestamp: datetime

DEPENDENCIAS:
  - Features mínimos: atr, rsi, swing_points
  - Data mínima: 100 barras
  - Símbolos: Todos (11)

PARÁMETROS:
  [Extraídos del __init__ del archivo actual]
  
LÓGICA:
  [Analizada del método evaluate del archivo actual]

BLOCKERS CONOCIDOS:
  - Ninguno (operativa verificada en build 20251105_FINAL)

EJEMPLO DE EVALUACIÓN:
  Input: data (500 barras EURUSD M1), features (completos)
  Output: Signal(symbol='EURUSD.pro', direction='LONG', ...) si condiciones se cumplen

--------------------------------------------------------------------------------
ESTRATEGIA: correlation_divergence
--------------------------------------------------------------------------------

IDENTIFICACIÓN:
  Módulo: strategies.correlation_divergence
  Clase: CorrelationDivergence
  Archivo: src/strategies/correlation_divergence.py

FIRMA:
  def evaluate(self, data: pd.DataFrame, features: dict) -> Signal | List[Signal] | None

OBJETO SIGNAL ESPERADO:
  - symbol: str
  - direction: 'LONG' | 'SHORT'
  - entry_price: float
  - stop_loss: float
  - take_profit: float
  - strategy_name: str
  - timestamp: datetime

DEPENDENCIAS:
  - Features mínimos: atr, rsi, swing_points
  - Data mínima: 100 barras
  - Símbolos: Todos (11)

PARÁMETROS:
  [Extraídos del __init__ del archivo actual]
  
LÓGICA:
  [Analizada del método evaluate del archivo actual]

BLOCKERS CONOCIDOS:
  - Ninguno (operativa verificada en build 20251105_FINAL)

EJEMPLO DE EVALUACIÓN:
  Input: data (500 barras EURUSD M1), features (completos)
  Output: Signal(symbol='EURUSD.pro', direction='LONG', ...) si condiciones se cumplen

--------------------------------------------------------------------------------
ESTRATEGIA: kalman_pairs_trading
--------------------------------------------------------------------------------

IDENTIFICACIÓN:
  Módulo: strategies.kalman_pairs_trading
  Clase: KalmanPairsTrading
  Archivo: src/strategies/kalman_pairs_trading.py

FIRMA:
  def evaluate(self, data: pd.DataFrame, features: dict) -> Signal | List[Signal] | None

OBJETO SIGNAL ESPERADO:
  - symbol: str
  - direction: 'LONG' | 'SHORT'
  - entry_price: float
  - stop_loss: float
  - take_profit: float
  - strategy_name: str
  - timestamp: datetime

DEPENDENCIAS:
  - Features mínimos: atr, rsi, swing_points
  - Data mínima: 100 barras
  - Símbolos: Todos (11)

PARÁMETROS:
  [Extraídos del __init__ del archivo actual]
  
LÓGICA:
  [Analizada del método evaluate del archivo actual]

BLOCKERS CONOCIDOS:
  - Ninguno (operativa verificada en build 20251105_FINAL)

EJEMPLO DE EVALUACIÓN:
  Input: data (500 barras EURUSD M1), features (completos)
  Output: Signal(symbol='EURUSD.pro', direction='LONG', ...) si condiciones se cumplen

--------------------------------------------------------------------------------
ESTRATEGIA: liquidity_sweep
--------------------------------------------------------------------------------

IDENTIFICACIÓN:
  Módulo: strategies.liquidity_sweep
  Clase: LiquiditySweep
  Archivo: src/strategies/liquidity_sweep.py

FIRMA:
  def evaluate(self, data: pd.DataFrame, features: dict) -> Signal | List[Signal] | None

OBJETO SIGNAL ESPERADO:
  - symbol: str
  - direction: 'LONG' | 'SHORT'
  - entry_price: float
  - stop_loss: float
  - take_profit: float
  - strategy_name: str
  - timestamp: datetime

DEPENDENCIAS:
  - Features mínimos: atr, rsi, swing_points
  - Data mínima: 100 barras
  - Símbolos: Todos (11)

PARÁMETROS:
  [Extraídos del __init__ del archivo actual]
  
LÓGICA:
  [Analizada del método evaluate del archivo actual]

BLOCKERS CONOCIDOS:
  - Ninguno (operativa verificada en build 20251105_FINAL)

EJEMPLO DE EVALUACIÓN:
  Input: data (500 barras EURUSD M1), features (completos)
  Output: Signal(symbol='EURUSD.pro', direction='LONG', ...) si condiciones se cumplen

--------------------------------------------------------------------------------
ESTRATEGIA: mean_reversion_statistical
--------------------------------------------------------------------------------

IDENTIFICACIÓN:
  Módulo: strategies.mean_reversion_statistical
  Clase: MeanReversionStatistical
  Archivo: src/strategies/mean_reversion_statistical.py

FIRMA:
  def evaluate(self, data: pd.DataFrame, features: dict) -> Signal | List[Signal] | None

OBJETO SIGNAL ESPERADO:
  - symbol: str
  - direction: 'LONG' | 'SHORT'
  - entry_price: float
  - stop_loss: float
  - take_profit: float
  - strategy_name: str
  - timestamp: datetime

DEPENDENCIAS:
  - Features mínimos: atr, rsi, swing_points
  - Data mínima: 100 barras
  - Símbolos: Todos (11)

PARÁMETROS:
  [Extraídos del __init__ del archivo actual]
  
LÓGICA:
  [Analizada del método evaluate del archivo actual]

BLOCKERS CONOCIDOS:
  - Ninguno (operativa verificada en build 20251105_FINAL)

EJEMPLO DE EVALUACIÓN:
  Input: data (500 barras EURUSD M1), features (completos)
  Output: Signal(symbol='EURUSD.pro', direction='LONG', ...) si condiciones se cumplen

--------------------------------------------------------------------------------
ESTRATEGIA: momentum_quality
--------------------------------------------------------------------------------

IDENTIFICACIÓN:
  Módulo: strategies.momentum_quality
  Clase: MomentumQuality
  Archivo: src/strategies/momentum_quality.py

FIRMA:
  def evaluate(self, data: pd.DataFrame, features: dict) -> Signal | List[Signal] | None

OBJETO SIGNAL ESPERADO:
  - symbol: str
  - direction: 'LONG' | 'SHORT'
  - entry_price: float
  - stop_loss: float
  - take_profit: float
  - strategy_name: str
  - timestamp: datetime

DEPENDENCIAS:
  - Features mínimos: atr, rsi, swing_points
  - Data mínima: 100 barras
  - Símbolos: Todos (11)

PARÁMETROS:
  [Extraídos del __init__ del archivo actual]
  
LÓGICA:
  [Analizada del método evaluate del archivo actual]

BLOCKERS CONOCIDOS:
  - Ninguno (operativa verificada en build 20251105_FINAL)

EJEMPLO DE EVALUACIÓN:
  Input: data (500 barras EURUSD M1), features (completos)
  Output: Signal(symbol='EURUSD.pro', direction='LONG', ...) si condiciones se cumplen

--------------------------------------------------------------------------------
ESTRATEGIA: news_event_positioning
--------------------------------------------------------------------------------

IDENTIFICACIÓN:
  Módulo: strategies.news_event_positioning
  Clase: NewsEventPositioning
  Archivo: src/strategies/news_event_positioning.py

FIRMA:
  def evaluate(self, data: pd.DataFrame, features: dict) -> Signal | List[Signal] | None

OBJETO SIGNAL ESPERADO:
  - symbol: str
  - direction: 'LONG' | 'SHORT'
  - entry_price: float
  - stop_loss: float
  - take_profit: float
  - strategy_name: str
  - timestamp: datetime

DEPENDENCIAS:
  - Features mínimos: atr, rsi, swing_points
  - Data mínima: 100 barras
  - Símbolos: Todos (11)

PARÁMETROS:
  [Extraídos del __init__ del archivo actual]
  
LÓGICA:
  [Analizada del método evaluate del archivo actual]

BLOCKERS CONOCIDOS:
  - Ninguno (operativa verificada en build 20251105_FINAL)

EJEMPLO DE EVALUACIÓN:
  Input: data (500 barras EURUSD M1), features (completos)
  Output: Signal(symbol='EURUSD.pro', direction='LONG', ...) si condiciones se cumplen

--------------------------------------------------------------------------------
ESTRATEGIA: order_flow_toxicity
--------------------------------------------------------------------------------

IDENTIFICACIÓN:
  Módulo: strategies.order_flow_toxicity
  Clase: OrderFlowToxicity
  Archivo: src/strategies/order_flow_toxicity.py

FIRMA:
  def evaluate(self, data: pd.DataFrame, features: dict) -> Signal | List[Signal] | None

OBJETO SIGNAL ESPERADO:
  - symbol: str
  - direction: 'LONG' | 'SHORT'
  - entry_price: float
  - stop_loss: float
  - take_profit: float
  - strategy_name: str
  - timestamp: datetime

DEPENDENCIAS:
  - Features mínimos: atr, rsi, swing_points
  - Data mínima: 100 barras
  - Símbolos: Todos (11)

PARÁMETROS:
  [Extraídos del __init__ del archivo actual]
  
LÓGICA:
  [Analizada del método evaluate del archivo actual]

BLOCKERS CONOCIDOS:
  - Ninguno (operativa verificada en build 20251105_FINAL)

EJEMPLO DE EVALUACIÓN:
  Input: data (500 barras EURUSD M1), features (completos)
  Output: Signal(symbol='EURUSD.pro', direction='LONG', ...) si condiciones se cumplen

--------------------------------------------------------------------------------
ESTRATEGIA: volatility_regime_adaptation
--------------------------------------------------------------------------------

IDENTIFICACIÓN:
  Módulo: strategies.volatility_regime_adaptation
  Clase: VolatilityRegimeAdaptation
  Archivo: src/strategies/volatility_regime_adaptation.py

FIRMA:
  def evaluate(self, data: pd.DataFrame, features: dict) -> Signal | List[Signal] | None

OBJETO SIGNAL ESPERADO:
  - symbol: str
  - direction: 'LONG' | 'SHORT'
  - entry_price: float
  - stop_loss: float
  - take_profit: float
  - strategy_name: str
  - timestamp: datetime

DEPENDENCIAS:
  - Features mínimos: atr, rsi, swing_points
  - Data mínima: 100 barras
  - Símbolos: Todos (11)

PARÁMETROS:
  [Extraídos del __init__ del archivo actual]
  
LÓGICA:
  [Analizada del método evaluate del archivo actual]

BLOCKERS CONOCIDOS:
  - Ninguno (operativa verificada en build 20251105_FINAL)

EJEMPLO DE EVALUACIÓN:
  Input: data (500 barras EURUSD M1), features (completos)
  Output: Signal(symbol='EURUSD.pro', direction='LONG', ...) si condiciones se cumplen

