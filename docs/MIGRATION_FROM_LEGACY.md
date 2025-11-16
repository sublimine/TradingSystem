# Migration Guide: Legacy → PLAN OMEGA

**Fecha:** 2025-11-16
**De:** Legacy System (main.py v2.0)
**A:** PLAN OMEGA Institutional System

---

## Executive Summary

**main.py es LEGACY** y será removido en futuras versiones.

**PLAN OMEGA** es la arquitectura moderna (2025) con:
- ✅ MicrostructureEngine centralizadoAdministration
- ✅ ExecutionManager + KillSwitch (4-layer risk)
- ✅ Runtime Profiles (GREEN_ONLY, FULL_24)
- ✅ BacktestEngine moderno
- ✅ Sin dependencias de ML legacy

---

## ¿Por Qué Migrar?

### Problemas del Sistema Legacy (main.py)

1. **MLAdaptiveEngine**: Deprecated, sin mantenimiento
2. **InstitutionalBrain**: Arquitectura monolítica obsoleta
3. **Old Risk/Position Managers**: Reemplazados por ExecutionManager + KillSwitch
4. **Feature Duplication**: Cada estrategia calculaba features independientemente
5. **No Profile System**: Todas las estrategias siempre activas
6. **MetaTrader5 Hardcoded**: Acoplado a MT5, difícil testing

### Beneficios de PLAN OMEGA

1. **MicrostructureEngine**: Features calculados UNA VEZ (24x performance boost)
2. **ExecutionManager**: PAPER/LIVE switching sin cambios de código
3. **KillSwitch**: 4 capas de protección de riesgo automáticas
4. **Runtime Profiles**: GREEN_ONLY (5 estrategias) o FULL_24 (24 estrategias)
5. **Broker Agnostic**: Adapter pattern para cualquier broker
6. **Modern Testing**: BacktestEngine con vectorization

---

## Migration Path

### Opción A: Migration Rápida (Recomendada)

**Tiempo:** 1-2 horas
**Complejidad:** Baja
**Resultado:** Sistema funcional en PAPER mode

#### Paso 1: Entender la Nueva Arquitectura

```
LEGACY (main.py):
┌────────────────────┐
│  EliteTradingSystem │
├────────────────────┤
│ - MLAdaptiveEngine │  ← DEPRECATED
│ - InstitutionalBrain│  ← DEPRECATED
│ - RiskManager      │  ← DEPRECATED
│ - PositionManager  │  ← DEPRECATED
│ - StrategyOrchestrator
└────────────────────┘

PLAN OMEGA:
┌──────────────────────────┐
│  BacktestEngine / Live   │
├──────────────────────────┤
│ - MicrostructureEngine   │  ← NEW: Centralized features
│ - StrategyOrchestrator   │  ← ENHANCED: Profile support
│ - ExecutionManager       │  ← NEW: PAPER/LIVE execution
│   - KillSwitch (4-layer) │  ← NEW: Risk protection
│   - BrokerAdapter        │  ← NEW: Broker abstraction
└──────────────────────────┘
```

#### Paso 2: Identificar Tu Uso Actual

**¿Qué haces con main.py?**

**A) Paper Trading:**
```bash
# LEGACY
python main.py --mode paper
```
→ Migra a **Execution System** (ver Paso 3)

**B) Backtesting:**
```bash
# LEGACY
python main.py --mode backtest --days 90
```
→ Migra a **BacktestEngine** (ver Paso 4)

**C) Live Trading:**
```bash
# LEGACY
python main.py --mode live --capital 10000
```
→ ⚠️ **CRÍTICO:** Valida en PAPER primero (ver Paso 5)

#### Paso 3: Paper Trading Migration

**LEGACY:**
```python
# main.py
from main import EliteTradingSystem

system = EliteTradingSystem()
system.run_paper_trading()
```

**PLAN OMEGA:**
```python
# scripts/run_paper_trading.py
from src.strategy_orchestrator import StrategyOrchestrator
from src.execution.execution_mode import ExecutionMode, ExecutionConfig
import pandas as pd

# 1. Configurar ejecución PAPER
exec_config = ExecutionConfig(
    mode=ExecutionMode.PAPER,
    initial_capital=10000.0,
    max_positions=3,
    max_risk_per_trade=0.015  # 1.5%
)

# 2. Inicializar con profile GREEN_ONLY (5 estrategias core)
orchestrator = StrategyOrchestrator(
    config_path='config/strategies_institutional.yaml',
    profile='green_only',  # O 'full_24' para las 24
    execution_config=exec_config
)

# 3. Loop de trading
while True:
    # Obtener datos de mercado
    market_data = fetch_market_data()  # Tu función

    # Evaluar Y ejecutar automáticamente
    result = orchestrator.evaluate_and_execute(market_data)

    # Monitorear
    print(f"Signals: {result['signals_count']}")
    print(f"Executed: {result['executed']}")

    # Estadísticas
    stats = orchestrator.get_execution_statistics()
    print(f"Balance: ${stats['balance']:.2f}")

    time.sleep(60)  # 1 minuto
```

#### Paso 4: Backtesting Migration

**LEGACY:**
```python
# main.py --mode backtest
python main.py --mode backtest --days 90
```

**PLAN OMEGA:**
```python
# scripts/run_backtest.py
from src.backtesting.backtest_engine import BacktestEngine
import pandas as pd

# 1. Cargar datos históricos
historical_data = pd.read_csv('data/EURUSD_M5_2024.csv')

# 2. Inicializar backtest engine
engine = BacktestEngine(
    initial_capital=10000.0,
    config_path='config/strategies_institutional.yaml',
    profile='green_only'  # GREEN_ONLY para comenzar
)

# 3. Ejecutar backtest
results = engine.run_backtest(
    symbol='EURUSD',
    historical_data=historical_data,
    start_date='2024-01-01',
    end_date='2024-12-31'
)

# 4. Analizar resultados
print(f"Total Trades: {results['total_trades']}")
print(f"Win Rate: {results['win_rate']:.1%}")
print(f"Total Return: {results['total_return']:.2%}")
print(f"Max Drawdown: {results['max_drawdown']:.2%}")
print(f"Sharpe Ratio: {results['sharpe_ratio']:.2f}")

# 5. Generar reporte
engine.generate_report()
```

**Documentación completa:** `docs/BACKTESTING_GUIDE.md`

#### Paso 5: Live Trading Migration (CRÍTICO)

⚠️ **WARNING:** NUNCA migrar directamente a LIVE sin validación PAPER.

**Flujo obligatorio:**
```
1. GREEN_ONLY + PAPER (30 días)
   ↓ (validar métricas positivas)
2. GREEN_ONLY + LIVE (micro capital, 30 días)
   ↓ (validar sin errores)
3. FULL_24 + PAPER (60 días)
   ↓ (validar diversificación)
4. FULL_24 + LIVE (capital completo)
```

**Paso 5.1: GREEN_ONLY PAPER (30 días)**

```python
from src.strategy_orchestrator import StrategyOrchestrator
from src.execution.execution_mode import ExecutionMode, ExecutionConfig

# PAPER mode con GREEN_ONLY
exec_config = ExecutionConfig(
    mode=ExecutionMode.PAPER,
    initial_capital=10000.0,
    max_positions=3,
    max_risk_per_trade=0.015
)

orchestrator = StrategyOrchestrator(
    profile='green_only',
    execution_config=exec_config
)

# Trading loop (30 días)
# ... (ver Paso 3)
```

**Métricas de validación:**
- Win rate > 60%
- Max drawdown < 15%
- Sin KillSwitch emergency stops frecuentes
- Execution rate > 80%

**Paso 5.2: GREEN_ONLY LIVE (micro capital)**

⚠️ **Solo si PAPER exitoso**

```python
# LIVE mode (REAL MONEY)
live_config = ExecutionConfig(
    mode=ExecutionMode.LIVE,
    initial_capital=1000.0,  # Micro capital primero
    max_positions=2,
    max_risk_per_trade=0.01,  # 1% (conservador)
    broker_config={
        'broker_type': 'oanda',  # o tu broker
        'api_key': os.getenv('OANDA_API_KEY'),
        'account_id': os.getenv('OANDA_ACCOUNT_ID'),
        'environment': 'practice'  # 'live' cuando estés listo
    }
)

orchestrator = StrategyOrchestrator(
    profile='green_only',
    execution_config=live_config
)
```

**Checklist pre-LIVE:**
- [ ] Validado 30 días en PAPER
- [ ] Win rate > 60% confirmado
- [ ] Broker credentials correctos
- [ ] KillSwitch activo (emergency_drawdown_pct=0.12)
- [ ] Capital de riesgo ÚNICAMENTE (dinero que puedes perder)
- [ ] Stop manual listo (ability to kill process)

---

### Opción B: Migration Incremental

**Tiempo:** 1-2 semanas
**Complejidad:** Media
**Resultado:** Sistema completamente customizado

#### Semana 1: Familiarización

**Día 1-2: Entender nuevos componentes**
```python
# Explorar MicrostructureEngine
from src.core.microstructure_engine import MicrostructureEngine
engine = MicrostructureEngine()
features = engine.calculate_features(market_data)
print(features)  # OFI, VPIN, CVD, ATR

# Explorar ExecutionManager
from src.execution.execution_manager import ExecutionManager
from src.execution.execution_mode import ExecutionMode, ExecutionConfig

config = ExecutionConfig(mode=ExecutionMode.PAPER, initial_capital=10000.0)
manager = ExecutionManager(config)

# Explorar KillSwitch
ks_status = manager.get_killswitch_status()
print(ks_status)
```

**Día 3-4: Ejecutar backtests**
```bash
# Backtest con GREEN_ONLY
python scripts/run_backtest.py --profile green_only --days 90

# Backtest con FULL_24
python scripts/run_backtest.py --profile full_24 --days 90
```

**Día 5: Crear profile custom**
```yaml
# config/profiles/my_custom.yaml
profile_name: "MY_CUSTOM"
enabled_strategies:
  - mean_reversion_statistical
  - liquidity_sweep
  - vpin_reversal_extreme
```

#### Semana 2: Testing & Migration

**Día 6-9: Paper trading validation**
```bash
# Ejecutar GREEN_ONLY en PAPER
python scripts/run_paper_trading.py --profile green_only
```

**Día 10-12: Custom integration**
- Integrar tus indicadores custom
- Modificar estrategias según necesidad
- Agregar logging custom

**Día 13-14: Pre-production validation**
- Revisar todas las métricas
- Confirmar KillSwitch funcionando
- Preparar runbook de operación

---

## Component Mapping

### Legacy → PLAN OMEGA

| Legacy Component | PLAN OMEGA Equivalent | Notes |
|-----------------|----------------------|-------|
| `MLAdaptiveEngine` | `MicrostructureEngine` | Deprecated ML → Institutional features |
| `InstitutionalBrain` | `StrategyOrchestrator` | Simplified, no "brain" abstraction |
| `RiskManager` | `ExecutionManager.kill_switch` | 4-layer KillSwitch |
| `PositionManager` | `ExecutionManager` | Unified execution |
| `MultiTimeframeManager` | `MicrostructureEngine` | Built-in HTF support |
| `RegimeDetector` | Strategies: `volatility_regime_adaptation` | Strategy-level |
| `InstitutionalReportingSystem` | `BacktestEngine.generate_report()` | Built-in reports |
| MT5 direct calls | `BrokerAdapter` (PAPER/LIVE) | Abstracted |

### Configuration Mapping

| Legacy Config | PLAN OMEGA Config | Location |
|--------------|-------------------|----------|
| `system_config.yaml` | `strategies_institutional.yaml` | `config/` |
| N/A | `profiles/green_only.yaml` | `config/profiles/` |
| N/A | `profiles/full_24.yaml` | `config/profiles/` |
| Hardcoded risk params | `ExecutionConfig` | Code-based |

### API Mapping

#### Legacy Signal Generation
```python
# LEGACY
system = EliteTradingSystem()
signals = system.brain.evaluate_strategies(data)
```

#### PLAN OMEGA Signal Generation
```python
# PLAN OMEGA
orchestrator = StrategyOrchestrator(profile='green_only')
signals = orchestrator.evaluate_strategies(market_data)
```

#### Legacy Execution
```python
# LEGACY
system = EliteTradingSystem()
system.position_manager.execute_signal(signal)
```

#### PLAN OMEGA Execution
```python
# PLAN OMEGA (con auto-execution)
orchestrator = StrategyOrchestrator(
    profile='green_only',
    execution_config=exec_config
)

# Auto-ejecuta señales
result = orchestrator.evaluate_and_execute(market_data)
```

---

## Breaking Changes

### 1. ML Components Removed

**Deprecados:**
- `MLAdaptiveEngine`
- `MLSupervisor`
- `ml_models/` directory

**Razón:** PLAN OMEGA usa institutional microstructure (OFI, VPIN, CVD) sin ML.

**Migración:** No migración directa. Usar MicrostructureEngine.

### 2. Brain Architecture Removed

**Deprecado:**
- `InstitutionalBrain`

**Razón:** Abstracción innecesaria, StrategyOrchestrator maneja directamente.

**Migración:**
```python
# ANTES
brain = InstitutionalBrain()
brain.evaluate()

# DESPUÉS
orchestrator = StrategyOrchestrator()
orchestrator.evaluate_strategies(data)
```

### 3. Risk/Position Managers Replaced

**Deprecados:**
- `RiskManager`
- `PositionManager`

**Reemplazados por:** `ExecutionManager` + `KillSwitch`

**Migración:**
```python
# ANTES
risk_manager = RiskManager(config)
position_manager = PositionManager(config)

# DESPUÉS
exec_config = ExecutionConfig(...)
manager = ExecutionManager(exec_config)  # Incluye KillSwitch
```

### 4. MT5 Direct Calls Removed

**Deprecado:**
```python
import MetaTrader5 as mt5
mt5.initialize()
mt5.symbol_info()
```

**Reemplazado por:** `BrokerAdapter`

**Migración:**
```python
# PAPER mode (no MT5 requerido)
config = ExecutionConfig(mode=ExecutionMode.PAPER)
manager = ExecutionManager(config)

# LIVE mode (adapter maneja MT5)
config = ExecutionConfig(
    mode=ExecutionMode.LIVE,
    broker_config={'broker_type': 'oanda', ...}
)
manager = ExecutionManager(config)
```

---

## Troubleshooting Migration

### Error: "ModuleNotFoundError: No module named 'src.core.brain'"

**Causa:** Código legacy intentando importar Brain.

**Solución:**
```python
# REMOVER
from src.core.brain import InstitutionalBrain

# USAR
from src.strategy_orchestrator import StrategyOrchestrator
```

### Error: "DeprecationWarning: main.py is LEGACY"

**Causa:** Ejecutando main.py (esperado).

**Solución:** Migrar a PLAN OMEGA (ver Paso 3/4/5).

### Pérdida de funcionalidad ML

**Problema:** "¿Dónde está MLAdaptiveEngine?"

**Respuesta:** PLAN OMEGA NO USA ML. Usa microstructure institucional (OFI, VPIN, CVD).

**Si necesitas ML:**
1. Usar MicrostructureEngine features como inputs
2. Entrenar modelo externo
3. Integrar predicciones como señales custom

```python
# Ejemplo integración ML custom
features = microstructure_engine.calculate_features(data)
ml_prediction = your_ml_model.predict(features)

if ml_prediction == 'BUY':
    # Crear señal custom
    signal = Signal(...)
```

### Performance degradado

**Problema:** "Legacy era más rápido"

**Diagnóstico:**
- ¿Usando FULL_24? → Probar GREEN_ONLY
- ¿Calculando features múltiples veces? → Verificar MicrostructureEngine cache
- ¿Demasiadas estrategias activas? → Crear profile custom

**Solución:**
```python
# GREEN_ONLY (5 estrategias, ~4x más rápido)
orchestrator = StrategyOrchestrator(profile='green_only')
```

---

## FAQ

**Q: ¿Puedo seguir usando main.py?**
A: Sí temporalmente, pero será removido. Migra a PLAN OMEGA.

**Q: ¿main.py funciona con PLAN OMEGA simultáneamente?**
A: No recomendado. Son arquitecturas incompatibles. Usa una u otra.

**Q: ¿Cuánto tiempo toma la migración?**
A: 1-2 horas (Opción A rápida) o 1-2 semanas (Opción B incremental).

**Q: ¿Necesito reentrenar modelos ML?**
A: No. PLAN OMEGA no usa ML. Usa institutional microstructure.

**Q: ¿Perderé mi configuración de estrategias?**
A: No. `strategies_institutional.yaml` sigue siendo compatible.

**Q: ¿Qué pasa con mis datos históricos de backtests?**
A: Compatibles. BacktestEngine usa mismo formato CSV.

**Q: ¿GREEN_ONLY es suficiente para live trading?**
A: Sí para comenzar. Escala a FULL_24 después de validación.

---

## Support & Resources

### Documentación PLAN OMEGA

- **Execution System:** `docs/EXECUTION_SYSTEM_GUIDE.md`
- **Backtesting:** `docs/BACKTESTING_GUIDE.md`
- **Runtime Profiles:** `docs/RUNTIME_PROFILES_GUIDE.md`
- **KillSwitch:** `src/risk/kill_switch.py` (docstrings completos)

### Example Scripts

```bash
# Backtesting
scripts/run_backtest.py

# Paper trading
scripts/run_paper_trading.py

# Strategy testing
scripts/test_single_strategy.py
```

### Migration Checklist

**Pre-Migration:**
- [ ] main.py functionality documented
- [ ] Current configuration backed up
- [ ] Understanding PLAN OMEGA architecture

**Migration:**
- [ ] Backtest con GREEN_ONLY (30 días)
- [ ] Backtest con FULL_24 (90 días)
- [ ] Paper trading GREEN_ONLY (30 días)
- [ ] Métricas validadas (WR > 60%, DD < 15%)

**Post-Migration:**
- [ ] main.py deprecated (warnings agregados)
- [ ] PLAN OMEGA en producción
- [ ] Monitoring activo (KillSwitch, execution rate)
- [ ] Runbook operacional creado

---

## Conclusión

**PLAN OMEGA** es el futuro del sistema. **main.py** será removido.

**Próximos pasos:**
1. **HOY:** Ejecutar backtest GREEN_ONLY
2. **Semana 1:** Paper trading GREEN_ONLY
3. **Semana 2-4:** Validar métricas
4. **Mes 2:** Escalar a FULL_24 si exitoso

**Recuerda:** Siempre PAPER antes de LIVE. No hay prisa.

---

**PLAN OMEGA FASE 4.2 - Migration Guide COMPLETE ✅**
