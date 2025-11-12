
================================================================================
NAMING CONVENTIONS
Convenciones de Nombrado
================================================================================

MÓDULOS
-------
Formato: lowercase_with_underscores
Ejemplos: 
  - liquidity_sweep
  - mean_reversion_statistical
  - order_flow_toxicity

CLASES
------
Formato: PascalCase
Ejemplos:
  - LiquiditySweep
  - MeanReversionStatistical
  - OrderFlowToxicity

FUNCIONES
---------
Formato: lowercase_with_underscores
Ejemplos:
  - calculate_atr
  - identify_swing_points
  - get_current_vpin

CONSTANTES
----------
Formato: UPPER_CASE_WITH_UNDERSCORES
Ejemplos:
  - STRATEGY_WHITELIST
  - SCAN_INTERVAL_SECONDS
  - LOOKBACK_BARS

VARIABLES
---------
Formato: lowercase_with_underscores
Descriptivas, no abreviaturas crípticas
Ejemplos:
  - entry_price (no ep)
  - stop_loss (no sl en código, OK en logs)
  - cumulative_volume_delta (no cvd en variables)

LOGS
----
Formato: UPPER_CASE para eventos clave
Ejemplos:
  - "CARGADA"
  - "ERROR_IMPORT"
  - "SEÑAL GENERADA"
  - "OK ORDEN EJECUTADA"
  - "THROTTLE_COOLDOWN"

ARCHIVOS
--------
Python: lowercase_with_underscores.py
JSON: lowercase_with_underscores.json
Logs: lowercase_with_underscores.log
Docs: UPPER_CASE_DESCRIPTIVE.md (para manifiestos)
