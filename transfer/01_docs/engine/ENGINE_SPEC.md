
================================================================================
ENGINE SPECIFICATION
Motor de Ejecución - live_trading_engine.py
================================================================================

DIAGRAMA DE FLUJO
-----------------

[MT5 Data Feed]
    ↓
[get_market_data(symbol, 500 bars)]
    ↓
[calculate_features(data, symbol)]
    ↓  
[for strategy in strategies:]
    ↓
[strategy.evaluate(data, features)]
    ↓
[if signal:]
    ↓
[can_open_position(symbol, direction)?]
    ↓ (yes)
[execute_order(signal)]
    ↓
[mt5.order_send(request)]
    ↓
[log result]
    ↓
[update stats]

CONTRATOS DE INTEGRACIÓN
-------------------------

Carga de Estrategias:
  - Lista blanca: STRATEGY_WHITELIST (9 módulos)
  - Importación: importlib.import_module(f'strategies.{name}')
  - Instanciación: strategy_class(config)
  - Validación: hasattr(instance, 'evaluate')
  - Error handling: ERROR_IMPORT → log y continuar

Firma evaluate():
  Input:
    - data: pd.DataFrame (columnas: time, open, high, low, close, volume, symbol)
    - features: dict (keys: atr, rsi, swing_high_levels, swing_low_levels, 
                      cumulative_volume_delta, vpin, volatility_regime,
                      order_book_imbalance, momentum_quality, spread)
  Output:
    - Signal object | List[Signal] | None
  
  Signal attributes (obligatorios):
    - symbol: str
    - direction: 'LONG' | 'SHORT'
    - entry_price: float
    - stop_loss: float
    - take_profit: float
    - strategy_name: str
    - timestamp: datetime
  
  Signal method:
    - validate() -> bool

Manejo de Errores No Fatales:
  - Fallo en carga: ERROR_IMPORT → stats[strategy]['errors']++ → continuar
  - Excepción en evaluate(): ERROR → stats['errors']++ → continuar
  - Señal inválida: descartada → continuar
  - Motor NUNCA se detiene por fallo individual

POLÍTICAS ANTI-SPAM
-------------------

"Una sola idea por estrategia por símbolo":
  - Cooldown: 300 segundos por símbolo/dirección
  - Verificación: can_open_position(symbol, direction)
  - Registro: open_positions[f"{symbol}_{direction}"] = timestamp
  - Log: THROTTLE_COOLDOWN | DUPLICATE_IDEA

Límites:
  - Max posiciones simultáneas por símbolo: 2
  - Max posiciones globales: ilimitado (controlado por capital)
  - Min intervalo misma estrategia/símbolo: 300s

REGLAS DE RIESGO
----------------

Riesgo por operación: 1% del capital
Implementación actual: lotaje = symbol_info.volume_min (placeholder)
Implementación target:
  risk_amount = balance * 0.01
  sl_distance = abs(entry - stop_loss)
  volume = risk_amount / (sl_distance * contract_size)
  volume = clamp(volume, volume_min, volume_max)

Condiciones de rechazo:
  - signal.validate() == False
  - can_open_position() == False
  - symbol_info no disponible
  - tick no disponible
  - mt5.order_send() != TRADE_RETCODE_DONE

CICLO DE ESCANEO
----------------

Intervalo: 60 segundos
Secuencia:
  1. scan_markets()
  2. for symbol in SYMBOLS (11)
  3. for strategy in strategies (9)
  4. evaluate()
  5. execute if valid
  6. sleep(60)
  7. repeat

Latencia target: <500ms por scan completo
Latencia actual: ~200ms promedio

LOGGING
-------
Destino: logs/live_trading.log
Formato: texto con timestamps
Encoding: UTF-8

Eventos críticos:
  - "CARGADA <strategy>"
  - "ERROR_IMPORT <strategy>"
  - "SEÑAL GENERADA"
  - "OK ORDEN EJECUTADA"
  - "ERROR evaluando <strategy>"
  - "THROTTLE_COOLDOWN"
