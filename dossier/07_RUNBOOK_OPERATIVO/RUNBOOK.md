
================================================================================
RUNBOOK OPERATIVO
================================================================================

ARRANQUE
--------

1. Verificar MT5 activo y conectado a Axi-US50-Demo
2. Abrir PowerShell como administrador
3. cd C:\TradingSystem
4. python scripts\live_trading_engine.py

Verificación post-arranque:
- Ver "Estrategias activas: 9"
- Sin ERROR_IMPORT
- Primer SCAN completa sin excepciones

PARADA
------

1. Ctrl+C en la ventana del motor
2. Esperar mensaje "Sistema detenido"
3. Verificar que no quedan posiciones abiertas no deseadas

Parada de emergencia:
- Cerrar ventana PowerShell
- Cerrar todas las posiciones en MT5 manualmente si necesario

VERIFICACIÓN
------------

Durante operación:
1. Logs en tiempo real en consola
2. Revisar logs/live_trading.log para errores
3. Monitorear MT5 para posiciones abiertas
4. Checkpoints cada 15-30 min (manual actualmente)

Health checks:
- Estrategias activas == 9
- Errores == 0 o muy bajos
- Latencia < 1s por scan
- Señales coherentes (no spam)

RECUPERACIÓN ANTE FALLO
-----------------------

Fallo de conexión MT5:
1. Verificar conexión internet
2. Reiniciar MT5
3. Reiniciar motor

Fallo de una estrategia:
- Motor continúa con las demás
- Identificar estrategia con errors++ en stats
- Revisar logs para causa
- Fix y redeploy solo esa estrategia

Fallo crítico del motor:
1. Parar motor
2. Revisar última excepción en logs
3. Restaurar desde checkpoint si necesario
4. Reiniciar

CAMBIO DE PARÁMETROS
---------------------

Actualmente: Requiere editar código y reiniciar

Procedimiento:
1. Parar motor
2. Editar archivo de estrategia o motor
3. Verificar sintaxis: python -m py_compile <archivo>
4. Backup del archivo anterior
5. Reiniciar motor
6. Verificar carga correcta

Futuro: config.yaml para parámetros sin redeploy

PAPER TRADING (DEMO)
--------------------

Estado actual: Sistema opera en DEMO
- Cuenta: Axi-US50-Demo
- Capital virtual
- Sin riesgo real

Duración recomendada: 30+ días

Métricas a monitorear:
- Win rate por estrategia
- Drawdown máximo
- Frecuencia de operaciones
- Calidad de ejecución (slippage)

GO-LIVE (Futuro)
----------------

Pre-requisitos:
1. 30+ días en DEMO sin errores críticos
2. Win rate > 55%
3. Drawdown < 15%
4. Todas las estrategias estables

Procedimiento:
1. Cambiar conexión MT5 a cuenta LIVE
2. Reducir lotajes (conservative sizing)
3. Monitoreo intensivo primeras 48h
4. Escalar gradualmente

SEÑALES DE ALERTA
-----------------

CRÍTICAS (detener inmediatamente):
- Pérdida > 5% en 24h
- Errores > 50/hora
- Pérdida de conexión MT5
- Señales spam (>10/min)

ADVERTENCIA (revisar y ajustar):
- Win rate < 45% en 100 trades
- Drawdown > 10%
- Estrategia con 70% errors en 20 evals

REMEDIACIÓN
-----------

Error crítico:
1. PARAR motor
2. Cerrar posiciones manualmente si necesario
3. Analizar logs
4. Restaurar desde checkpoint
5. Contactar soporte si necesario

Estrategia problemática:
1. Identificar en stats
2. Deshabilitar temporalmente (quitar de lista blanca)
3. Analizar condiciones que causan errors
4. Fix y test unitario
5. Reactivar cuando fixed

Performance baja:
1. Analizar métricas por estrategia
2. Revisar umbrales y filtros
3. Backtest con datos recientes
4. Ajustar parámetros
5. Redeploy y monitor
