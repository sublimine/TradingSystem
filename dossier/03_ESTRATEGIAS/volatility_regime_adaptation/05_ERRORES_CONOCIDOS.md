
ERRORES CONOCIDOS - volatility_regime_adaptation
================================================================================

CONDICIONES QUE BLOQUEAN SEÑALES
---------------------------------
1. Data insuficiente (<100 barras)
   Log: No aparece en signals, evaluations++ normal
   
2. Features incompletos
   Log: evaluations++ pero signals=0
   
3. Condiciones de mercado no cumplen umbrales
   Log: Normal, evaluations++ pero signals=0
   
4. Excepción en evaluate()
   Log: ERROR evaluando volatility_regime_adaptation: <mensaje>
   Stats: errors++
   Motor: Continúa con siguiente

CÓMO SE REGISTRAN
-----------------
Logs en: logs/live_trading.log
Formato: "ERROR evaluando <strategy>: <exception>"
Stats en memoria: self.stats[strategy_name]['errors']++

NINGÚN ERROR CRÍTICO CONOCIDO
------------------------------
Estrategia validada en build 20251105_FINAL
