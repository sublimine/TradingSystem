
================================================================================
CONFIG MODEL
Modelo de Configuración del Sistema
================================================================================

CAPAS DE CONFIGURACIÓN
----------------------

1. Hardcoded (en código)
   - Lista blanca de estrategias: STRATEGY_WHITELIST
   - Símbolos: SYMBOLS array
   - Scan interval: SCAN_INTERVAL_SECONDS = 60
   - Lookback: LOOKBACK_BARS = 500

2. Runtime (en constructor)
   - Cooldown: self.position_cooldown = 300
   - Max open per symbol: ilimitado (lógica can_open_position)
   - VPIN calculators: inicializados por símbolo

3. Estrategia (en __init__)
   - Parámetros específicos por estrategia
   - Umbrales, multiplicadores, filtros

PRECEDENCIA
-----------
Hardcoded > Runtime > Default

VALIDACIÓN
----------
Pre-startup:
  - STRATEGY_WHITELIST no vacío
  - SYMBOLS no vacío
  - SCAN_INTERVAL_SECONDS > 0
  - Cooldown >= 0

Runtime:
  - Estrategias en whitelist existen como módulos
  - MT5 symbols disponibles
  - Conexión MT5 activa

DEMO/LIVE SWITCH
----------------

Actual: Hardcoded DEMO (cuenta Axi-US50-Demo)

Target:
  MODE = os.getenv('TRADING_MODE', 'DEMO')
  if MODE == 'LIVE':
      validate_live_safeguards()
      confirm_with_user()

LIVE safeguards:
  - Doble confirmación
  - Límite de capital en riesgo
  - Circuit breaker por drawdown
  - Notificaciones activas

PARÁMETROS DE SEGURIDAD
------------------------

Anti-spam:
  - COOLDOWN_SECONDS: 300
  - MAX_OPEN_PER_SYMBOL: 2

Riesgo:
  - RISK_PER_TRADE_PCT: 1.0
  - LOTAJE: 'dynamic' (target) | 'min' (actual)

Execution:
  - DEVIATION: 20 pips
  - MAGIC: 234000
  - FILLING: FOK
  - TYPE_TIME: GTC

Monitoring:
  - LOG_LEVEL: INFO
  - STATS_INTERVAL: 10 scans
  - CHECKPOINT_INTERVAL: manual
