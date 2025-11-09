
================================================================================
ARQUITECTURA DEL SISTEMA
================================================================================

DIAGRAMA DE FLUJO COMPLETO
---------------------------

[MT5] --> [Data Pipeline] --> [Feature Engineering] --> [Strategies (9)] --> 
[Motor] --> [Risk Management] --> [Execution] --> [Logs]

COMPONENTES DETALLADOS
----------------------

1. MT5 (MetaTrader 5)
   - Fuente de datos en tiempo real
   - Timeframe: M1 (1 minuto)
   - 11 símbolos monitoreados
   - API: mt5.copy_rates_from_pos()

2. Data Pipeline
   - Extracción: motor llama get_market_data()
   - Transformación: pd.DataFrame con OHLCV
   - Validación: mínimo 100 barras
   - Lookback: 500 barras

3. Feature Engineering
   Location: src/features/
   
   technical_indicators.py:
     - calculate_atr(high, low, close, period=14)
     - calculate_rsi(close, period=14)
     - identify_swing_points(high/low, order=5)
   
   order_flow.py:
     - VPINCalculator (Volume-Synchronized Probability)
     - calculate_signed_volume()
     - cumulative_volume_delta
   
   statistical_models.py:
     - calculate_realized_volatility()
     - volatility_regime detection

4. Strategies (src/strategies/)
   9 módulos independientes
   
   Contrato:
     Input: evaluate(data: pd.DataFrame, features: dict)
     Output: Signal | List[Signal] | None
   
   Cada estrategia:
     - Autónoma (no depende de otras estrategias)
     - Fallo aislado (no detiene motor)
     - Stats individuales

5. Motor (scripts/live_trading_engine.py)
   Responsabilidades:
     - Inicialización MT5
     - Carga de estrategias (lista blanca)
     - Ciclo de escaneo (60s)
     - Gestión de cooldowns
     - Ejecución de órdenes
     - Logging
   
   Políticas:
     - No abortar en fallo de estrategia
     - Anti-spam por símbolo/dirección
     - Max 2 posiciones por símbolo

6. Risk Management
   Integrado en motor:
     - 1% riesgo por operación
     - Lotaje: symbol_info.volume_min (dinámico)
     - SL/TP: definidos por estrategia
     - Validación pre-ejecución

7. Execution
   MT5 order_send():
     - type: BUY/SELL
     - volume: calculado
     - price: tick actual
     - sl/tp: de la señal
     - magic: 234000
     - filling: FOK

8. Logs
   Destino: logs/live_trading.log
   Formato: texto con timestamps
   Eventos: cargas, scans, señales, órdenes, errores

CONTRATOS DE INTERFACES
------------------------

Strategy.evaluate() -> Signal:
  Input:
    - data: pd.DataFrame con columnas [time, open, high, low, close, volume]
    - features: dict con keys [atr, rsi, swing_high_levels, swing_low_levels,
                cumulative_volume_delta, vpin, volatility_regime, 
                order_book_imbalance, momentum_quality, spread]
  
  Output:
    - Signal object con atributos:
        symbol: str
        direction: 'LONG' | 'SHORT'
        entry_price: float
        stop_loss: float
        take_profit: float
        strategy_name: str
        timestamp: datetime
        validate() -> bool
    - O None si no hay señal

Engine -> MT5:
  request = {
    "action": TRADE_ACTION_DEAL,
    "symbol": str,
    "volume": float,
    "type": ORDER_TYPE_BUY/SELL,
    "price": float,
    "sl": float,
    "tp": float,
    "deviation": 20,
    "magic": 234000,
    "comment": str,
    "type_time": ORDER_TIME_GTC,
    "type_filling": ORDER_FILLING_FOK
  }
  
  result = mt5.order_send(request)
  -> result.retcode == TRADE_RETCODE_DONE

POLÍTICAS DE ERRORES
--------------------

1. Error en carga de estrategia:
   - Log: ERROR_IMPORT <strategy>
   - Acción: Continuar con las demás
   - No detener motor

2. Error en evaluate():
   - Log: ERROR evaluando <strategy>: <mensaje>
   - Stats: errors++
   - Acción: Continuar con siguiente

3. Error en MT5:
   - Log: ERROR con detalle
   - Acción: No ejecutar esa orden, continuar

4. Pérdida de conexión MT5:
   - Detener motor
   - Logs de error
   - Reinicio manual requerido

RECONEXIÓN
----------
Actualmente: Manual
Futuro: Auto-reconnect con backoff exponencial
