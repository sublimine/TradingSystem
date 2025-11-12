================================================================================
VOLUME 01 - EXECUTIVE SUMMARY
Sistema de Trading Institucional
Build: 20251105_FINAL
================================================================================

ESTADO DEL SISTEMA
------------------
Estrategias activas: 9/9
Modo operativo: DEMO
Build: 20251105_FINAL
Símbolos monitoreados: 11
Intervalo de escaneo: 60 segundos
Cooldown anti-spam: 300 segundos

LÍMITES DE RIESGO
-----------------
Riesgo máximo por operación: 1%
Lotaje: Dinámico (calculado por motor)
Suspensión automática: 70% fallos en 20 trades
Max posiciones por símbolo: 2

COMPONENTES PRINCIPALES
-----------------------
1. Motor de ejecución (live_trading_engine.py)
2. 9 Estrategias institucionales
3. Sistema de features (indicadores técnicos + microestructura)
4. Pipeline de datos (MT5 M1)
5. Sistema de logs y checkpoints
6. Control de riesgo integrado

ESTRATEGIAS ACTIVAS (9/9)
-------------------------
1. breakout_volume_confirmation
2. correlation_divergence
3. kalman_pairs_trading
4. liquidity_sweep
5. mean_reversion_statistical
6. momentum_quality
7. news_event_positioning
8. order_flow_toxicity
9. volatility_regime_adaptation

DEPENDENCIAS CRÍTICAS
---------------------
- Python 3.x
- MetaTrader5
- pandas
- numpy
- PostgreSQL (opcional para persistencia)

ÁREAS CRÍTICAS
--------------
CRÍTICO:
- Motor de ejecución
- Sistema de carga de estrategias (lista blanca)
- Conexión MT5
- Control de riesgo

NO CRÍTICO (PUEDE FALLAR SIN DETENER SISTEMA):
- Estrategias individuales (motor continúa con las demás)
- Logs históricos
- Checkpoints

ROADMAP DE MANTENIMIENTO
------------------------
1. Monitoreo diario de checkpoints
2. Validación semanal de estrategias
3. Backup mensual de estado completo
4. Auditoría trimestral de performance

ESTADO: OPERATIVO
Fecha: 2025-11-05
Timezone: Europe/Zurich
