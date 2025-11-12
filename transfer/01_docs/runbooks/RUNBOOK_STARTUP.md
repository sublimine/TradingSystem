
================================================================================
RUNBOOK - STARTUP
Procedimiento de Arranque DEMO
================================================================================

PRE-REQUISITOS
--------------
1. MT5 instalado y configurado
2. Cuenta DEMO Axi-US50 activa
3. Python 3.x con dependencias instaladas
4. C:\TradingSystem con código actualizado

PROCEDIMIENTO
-------------

1. Verificar MT5
   - Abrir MT5
   - Login a Axi-US50-Demo
   - Verificar conexión (luz verde)
   - Confirmar símbolos disponibles

2. Abrir PowerShell
   cd C:\TradingSystem

3. Verificar estado previo (opcional)
   python -c "import MetaTrader5 as mt5; print(mt5.initialize())"

4. Iniciar motor
   python scripts\live_trading_engine.py

5. Verificación post-startup (primeros 60 segundos)
   Buscar en logs:
   ✓ "Conectado a Axi-US50-Demo"
   ✓ "Estrategias activas: 9"
   ✓ "CARGADA" x9 (sin ERROR_IMPORT)
   ✓ "SCAN #1" completa sin excepciones

TROUBLESHOOTING
---------------

Error "No se pudo inicializar MT5":
  - Verificar MT5 running
  - Verificar login activo
  - Reiniciar MT5
  - Retry

Error "ERROR_IMPORT <strategy>":
  - Verificar sintaxis: python -m py_compile src/strategies/<strategy>.py
  - Revisar imports del módulo
  - Verificar PYTHONPATH
  - Si persiste: comentar de STRATEGY_WHITELIST

Error "No tick para <symbol>":
  - Verificar que símbolo está en Market Watch
  - Click derecho → Show All en MT5
  - Retry

CONFIRMACIÓN DE ÉXITO
---------------------
✓ Logs muestran 9/9 estrategias cargadas
✓ Primer scan completa sin excepciones
✓ No ERROR en logs (avisos OK)
✓ Motor continúa scans cada 60s
