================================================================================
VOLUME 02 - ARCHITECTURE
================================================================================

DIAGRAMA DE ALTO NIVEL
-----------------------
MT5 (M1 Data) → Data Pipeline → Feature Engineering → Strategies → Engine → Execution → Logs

COMPONENTES
-----------

1. DATA INGESTION
   - Fuente: MetaTrader5
   - Timeframe: M1
   - Símbolos: 11 (EURUSD, GBPUSD, USDJPY, AUDUSD, USDCAD, USDCHF, NZDUSD, EURGBP, XAUUSD, BTCUSD, ETHUSD)
   - Lookback: 500 barras

2. FEATURE ENGINEERING (src/features/)
   - technical_indicators.py: ATR, RSI, swing points
   - order_flow.py: VPIN, signed volume, CVD
   - statistical_models.py: Volatility regimes

3. STRATEGIES (src/strategies/)
   - 9 módulos independientes
   - Cada uno implementa evaluate(data, features)
   - Retornan Signal objects

4. ENGINE (scripts/live_trading_engine.py)
   - Ciclo de escaneo (60s)
   - Lista blanca de estrategias
   - Anti-spam / cooldown
   - Ejecución de órdenes
   - Logging

5. EXECUTION
   - MT5 order_send()
   - Validación pre-ejecución
   - Control de riesgo

6. PERSISTENCE
   - Logs: logs/live_trading.log
   - Checkpoints: checkpoints/*.json
   - Backups: backups/

MAPA DE DIRECTORIOS
-------------------
C:\TradingSystem\
├── src\
│   ├── features\
│   │   ├── technical_indicators.py
│   │   ├── order_flow.py
│   │   └── statistical_models.py
│   └── strategies\
│       ├── breakout_volume_confirmation.py
│       ├── correlation_divergence.py
│       ├── kalman_pairs_trading.py
│       ├── liquidity_sweep.py
│       ├── mean_reversion_statistical.py
│       ├── momentum_quality.py
│       ├── news_event_positioning.py
│       ├── order_flow_toxicity.py
│       └── volatility_regime_adaptation.py
├── scripts\
│   └── live_trading_engine.py
├── logs\
├── checkpoints\
└── backups\

CONTRATOS ENTRE MÓDULOS
------------------------

Engine → Strategy:
  Input: evaluate(data: pd.DataFrame, features: dict)
  Output: Signal | List[Signal] | None

Strategy → Signal:
  Attributes:
    - symbol: str
    - direction: 'LONG' | 'SHORT'
    - entry_price: float
    - stop_loss: float
    - take_profit: float
    - strategy_name: str
    - timestamp: datetime
  Method: validate() -> bool

Engine → MT5:
  order_send(request: dict) -> result

Features → Engine:
  calculate_features(data, symbol) -> dict
