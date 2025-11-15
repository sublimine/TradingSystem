# MANDATO 24 - ARCHITECTURE ANALYSIS: Entry Points & Duplications

**Date**: 2025-11-15
**Branch**: claude/mandato24-full-loop-integration-01AqipubodvYuyNtfLsBZpsx
**Status**: CRITICAL - Multiple redundant entry points detected
**Classification**: ARCHITECTURAL DEBT

---

## EXECUTIVE SUMMARY

**Problema crítico**: El sistema tiene **CUATRO (4) entry points diferentes** para trading live/paper, cada uno con lógica parcialmente implementada y SIN unificación.

**Consecuencia**:
- Código duplicado
- Lógica inconsistente entre modos
- Features NO integradas en ningún loop live/paper
- Confusión sobre cuál usar

**Veredicto**: **ARQUITECTURA FRAGMENTADA** - Requiere unificación inmediata.

---

## BLOQUE 1: INVENTARIO DE ENTRY POINTS

### 1.1 Entry Points PRINCIPALES (Trading Loop)

| Entry Point | Líneas | Clase Principal | Estado | Propósito Original |
|------------|--------|-----------------|--------|-------------------|
| `main.py` | 370 | `EliteTradingSystem` | ⚠️ INCOMPLETO | Sistema principal PAPER (v1) |
| `main_with_execution.py` | 543 | `EliteTradingSystemV2` | ⚠️ INCOMPLETO | Sistema PAPER/LIVE con ExecutionAdapter (v2 - MANDATO 23) |
| `scripts/live_trading_engine.py` | 643 | `LiveTradingEngine` | ⚠️ LEGACY | Engine legacy con GatekeeperAdapter |
| `scripts/live_trading_engine_institutional.py` | 920 | `InstitutionalTradingEngine` | ⚠️ LEGACY | Engine institucional alternativo |

**Total**: 4 implementaciones diferentes del mismo concepto (trading loop).

### 1.2 Entry Points AUXILIARES (Utilidades)

| Entry Point | Propósito | ¿Duplica funcionalidad? |
|------------|-----------|------------------------|
| `scripts/start_live_trading.py` | Launcher con validaciones pre-LIVE | ✅ Wrapper sobre main_with_execution.py |
| `scripts/monitor_live_trading.py` | Monitor de trading LIVE | ✅ Utilidad única (NO duplica) |
| `scripts/emergency_stop_live.py` | Kill switch manual | ✅ Utilidad única (NO duplica) |
| `scripts/smoke_test_execution_system.py` | Tests de sistema de ejecución | ✅ Utilidad única (NO duplica) |
| `scripts/pre_flight_check.py` | Pre-flight validations | ⚠️ Posible overlap con start_live_trading.py |

### 1.3 Entry Points BACKTEST

| Entry Point | Propósito | Estado |
|------------|-----------|--------|
| `scripts/institutional_backtest.py` | Backtest institucional | ✅ FUNCIONA (usa BacktestEngine) |
| `scripts/consolidated_backtest.py` | Backtest consolidado | ⚠️ Posible duplicación |
| `scripts/complete_backtest.py` | Backtest completo | ⚠️ Posible duplicación |
| `scripts/adaptive_backtest.py` | Backtest adaptativo | ⚠️ Posible duplicación |
| `scripts/real_backtest.py` | Backtest "real" | ⚠️ Posible duplicación |

**Total**: 5 scripts de backtest (posible duplicación).

---

## BLOQUE 2: ANÁLISIS COMPARATIVO - Main Entry Points

### 2.1 main.py vs main_with_execution.py

#### Características Comunes

| Componente | main.py | main_with_execution.py |
|-----------|---------|----------------------|
| **Clase principal** | `EliteTradingSystem` | `EliteTradingSystemV2` |
| **Config loading** | ✅ system_config.yaml | ✅ system_config.yaml + live_trading_config.yaml |
| **RiskManager** | ✅ Inicializado | ✅ Inicializado |
| **PositionManager** | ✅ Inicializado | ✅ Inicializado |
| **RegimeDetector** | ✅ Inicializado | ✅ Inicializado |
| **MultiTimeframeManager** | ✅ Inicializado | ✅ Inicializado |
| **InstitutionalBrain** | ✅ Inicializado | ✅ Inicializado |
| **StrategyOrchestrator** | ✅ Inicializado | ✅ Inicializado |
| **MLAdaptiveEngine** | ✅ Inicializado | ✅ Inicializado (auto_ml flag) |
| **MLSupervisor** | ✅ Inicializado | ✅ Inicializado |
| **InstitutionalReportingSystem** | ✅ Inicializado | ✅ Inicializado |

**Duplicación**: ~90% del código de inicialización es IDÉNTICO.

#### Diferencias Críticas

| Aspecto | main.py | main_with_execution.py |
|---------|---------|----------------------|
| **ExecutionMode enum** | ❌ NO tiene | ✅ Sí (RESEARCH/PAPER/LIVE) |
| **ExecutionAdapter** | ❌ NO tiene | ✅ Sí (PaperExecutionAdapter / LiveExecutionAdapter) |
| **KillSwitch** | ❌ NO tiene | ✅ Sí (integrado con LiveExecutionAdapter) |
| **Trading loop PAPER** | ✅ Implementado (L241-299) | ⚠️ TODO placeholder (L368-396) |
| **Trading loop LIVE** | ❌ NO tiene | ⚠️ TODO placeholder (L397-456) |
| **Feature calculation** | ❌ NO tiene | ❌ NO tiene |
| **generate_signals() call** | ❌ Llama método NO existente (L263) | ❌ NO implementado |
| **Triple confirmation LIVE** | ❌ N/A | ✅ Sí (L415-428) |

### 2.2 Código Duplicado - Ejemplo Concreto

#### Inicialización de componentes (IDÉNTICA)

**main.py (L85-170)**:
```python
# 1. Risk Manager
self.risk_manager = RiskManager(self.config)
logger.info("✓ Risk Manager initialized")

# 2. Position Manager
self.position_manager = PositionManager(self.config)
logger.info("✓ Position Manager initialized")

# 3. Regime Detector
self.regime_detector = RegimeDetector(self.config)
logger.info("✓ Regime Detector initialized")

# 4. Multi-Timeframe Manager
self.mtf_manager = MultiTimeframeManager(self.config)
logger.info("✓ Multi-Timeframe Manager initialized")

# 5. ML Adaptive Engine
self.ml_engine = None
if auto_ml:
    try:
        self.ml_engine = MLAdaptiveEngine(self.config)
        logger.info("✓✓ ML Adaptive Engine ENABLED")
    except Exception as e:
        logger.warning(f"⚠️  ML Engine failed: {e}")

# 6. Institutional Brain
self.brain = InstitutionalBrain(
    config=self.config,
    risk_manager=self.risk_manager,
    position_manager=self.position_manager,
    regime_detector=self.regime_detector,
    mtf_manager=self.mtf_manager,
    ml_engine=self.ml_engine
)
logger.info("✓ Institutional Brain initialized")

# 7. Strategy Orchestrator
self.strategy_orchestrator = StrategyOrchestrator(
    config_path='config/strategies_institutional.yaml',
    brain=self.brain
)
logger.info("✓ Strategy Orchestrator initialized")

# 8. Reporting System
self.reporting = InstitutionalReportingSystem(output_dir='reports/')
logger.info("✓ Institutional Reporting System initialized")

# 9. ML Supervisor
self.ml_supervisor = MLSupervisor(
    config=self.config,
    ml_engine=self.ml_engine,
    strategy_orchestrator=self.strategy_orchestrator,
    reporting_system=self.reporting
)
logger.info("✓✓ ML Supervisor ENABLED")
```

**main_with_execution.py (L128-186)**: **IDÉNTICO** (salvo logs ligeramente diferentes).

**Duplicación**: ~85 líneas duplicadas EXACTAMENTE.

### 2.3 Trading Loop - Comparación

#### main.py - run_paper_trading() (L241-299)

**Estado**: ⚠️ PARCIALMENTE implementado, pero con BUG crítico

```python
def run_paper_trading(self):
    """Run paper trading loop."""
    logger.info("Starting paper trading mode...")

    self.is_running = True
    iteration = 0

    while self.is_running:
        try:
            iteration += 1

            # 1. Update all timeframes
            self.mtf_manager.update()

            # 2. Get current market data
            current_data = self.mtf_manager.get_current_data()

            if not current_data:
                logger.warning("No market data available")
                time.sleep(self.config['trading']['update_interval'])
                continue

            # 3. Detect market regime
            current_regime = self.regime_detector.detect_regime(current_data)
            logger.debug(f"Current regime: {current_regime}")

            # 4. Generate signals from all strategies
            signals = self.strategy_orchestrator.generate_signals(  # ← LÍNEA 263
                current_data,
                current_regime
            )
            # ^^^ BUG: generate_signals() NO EXISTE en StrategyOrchestrator
            # ^^^ NO HAY CÁLCULO DE FEATURES

            logger.info(f"Generated {len(signals)} signals")

            # 5. Process signals (paper trading - no real execution)
            for signal in signals:
                logger.info(f"Paper Signal: {signal.symbol} {signal.direction} "
                          f"@ {signal.entry_price:.5f}")

            # 6. Sleep until next update
            time.sleep(self.config['trading']['update_interval'])

        except KeyboardInterrupt:
            logger.info("Stopping paper trading...")
            self.is_running = False
            break
        except Exception as e:
            logger.error(f"Error in paper trading loop: {e}")
            time.sleep(5)
```

**Problemas**:
1. ❌ Llama `strategy_orchestrator.generate_signals()` que NO EXISTE
2. ❌ NO calcula features (OFI, CVD, VPIN, L2)
3. ❌ NO pasa features a estrategias
4. ⚠️ Pero la ESTRUCTURA del loop es correcta (update → regime → signals → process)

#### main_with_execution.py - run_paper_trading() (L368-396)

**Estado**: ❌ PLACEHOLDER - NO implementado

```python
def run_paper_trading(self):
    """
    Run system in paper trading mode (demo account).

    Uses PaperExecutionAdapter for simulated fills.
    """
    logger.info("=" * 80)
    logger.info("STARTING PAPER TRADING MODE")
    logger.info("=" * 80)

    if self.execution_mode != ExecutionMode.PAPER:
        logger.error(f"Cannot run paper trading in {self.execution_mode.value} mode")
        return

    self.is_running = True

    # Main trading loop
    try:
        while self.is_running:
            # Trading logic aquí (simplified for now)
            # TODO: Implement full trading loop

            import time
            time.sleep(60)  # 1 minute between updates

    except KeyboardInterrupt:
        logger.info("\n⚠️  Shutdown requested by user")
        self.shutdown()
```

**Problemas**:
1. ❌ TODO placeholder - NO implementado
2. ❌ Solo duerme 60s en loop
3. ✅ Pero TIENE PaperExecutionAdapter inicializado
4. ✅ Tiene ExecutionMode enum correcto

#### main_with_execution.py - run_live_trading() (L397-456)

**Estado**: ⚠️ PARCIALMENTE implementado - Tiene confirmaciones pero NO loop completo

```python
def run_live_trading(self):
    """
    Run system in live trading mode (real account).

    Uses LiveExecutionAdapter + KillSwitch for REAL execution.
    """
    logger.critical("=" * 80)
    logger.critical("STARTING LIVE TRADING MODE")
    logger.critical("=" * 80)

    if self.execution_mode != ExecutionMode.LIVE:
        logger.error(f"Cannot run live trading in {self.execution_mode.value} mode")
        return

    # Triple confirmation
    logger.critical("⚠️⚠️⚠️  LIVE TRADING MODE - REAL MONEY AT RISK  ⚠️⚠️⚠️")
    logger.critical(f"Kill Switch State: {self.kill_switch.get_state().value}")

    confirm1 = input("Type 'YES' to confirm live trading: ")
    if confirm1 != 'YES':
        logger.info("Live trading cancelled")
        return

    confirm2 = input("Type 'CONFIRM' to proceed with REAL money: ")
    if confirm2 != 'CONFIRM':
        logger.info("Live trading cancelled")
        return

    confirm3 = input("Final confirmation - Type 'LIVE' to start: ")
    if confirm3 != 'LIVE':
        logger.info("Live trading cancelled")
        return

    logger.critical("✅ Live trading confirmed - Starting...")

    self.is_running = True

    # Main trading loop (same as paper but with LiveExecutionAdapter)
    try:
        while self.is_running:
            # Check kill switch periodically
            if not self.kill_switch.can_send_orders():
                logger.critical(
                    f"⚠️  KILL SWITCH ACTIVE: {self.kill_switch.get_state().value}"
                )
                # Pause trading but don't exit
                import time
                time.sleep(60)
                continue

            # Trading logic aquí
            # TODO: Implement full trading loop

            import time
            time.sleep(60)  # 1 minute between updates

    except KeyboardInterrupt:
        logger.critical("\n⚠️  EMERGENCY SHUTDOWN REQUESTED BY USER")
        self.shutdown()
```

**Fortalezas**:
1. ✅ Triple confirmación (YES → CONFIRM → LIVE)
2. ✅ Kill Switch check en loop
3. ✅ LiveExecutionAdapter inicializado

**Problemas**:
1. ❌ TODO placeholder - loop NO implementado
2. ❌ NO calcula features
3. ❌ NO llama estrategias

### 2.4 Conclusión: Complementariedad Invertida

| Componente | main.py | main_with_execution.py |
|-----------|---------|----------------------|
| **Loop structure** | ✅ Tiene | ❌ Falta |
| **ExecutionAdapter** | ❌ Falta | ✅ Tiene |
| **KillSwitch** | ❌ Falta | ✅ Tiene |
| **Feature calculation** | ❌ Falta | ❌ Falta |
| **generate_signals()** | ❌ Bug (método no existe) | ❌ No llamado |

**Diagnóstico**: Ninguno de los dos es completo. Necesitan FUSIONARSE.

---

## BLOQUE 3: scripts/live_trading_engine*.py - Engines Legacy

### 3.1 scripts/live_trading_engine.py

**Clase**: `LiveTradingEngine`
**Líneas**: 643
**Estado**: ⚠️ LEGACY - No usa componentes institucionales

**Arquitectura**:
```python
class LiveTradingEngine:
    def __init__(self):
        self.strategies = []  # Carga estrategias manualmente
        self.gatekeeper_adapter = GatekeeperAdapter()  # Legacy gatekeeper
        self.vpin_calculators = {symbol: VPINCalculator() for symbol in SYMBOLS}
        self.open_positions = {}
```

**Diferencias con main.py**:
- ❌ NO usa InstitutionalBrain
- ❌ NO usa StrategyOrchestrator
- ❌ NO usa RiskManager institucional
- ✅ Tiene GatekeeperAdapter (sistema alternativo de validación)
- ✅ Tiene STRATEGY_WHITELIST hardcoded
- ✅ Carga estrategias vía `importlib` dinámicamente

**Propósito original**: Engine legacy pre-MANDATO 23, antes de arquitectura institucional.

**¿Deprecar?**: SÍ - Reemplazar por main_with_execution.py unificado.

### 3.2 scripts/live_trading_engine_institutional.py

**Clase**: `InstitutionalTradingEngine`
**Líneas**: 920
**Estado**: ⚠️ LEGACY - Duplica main.py pero con variaciones

**¿Usa componentes institucionales?**: Posiblemente (necesita inspección detallada).

**¿Deprecar?**: Probablemente SÍ - Si no aporta funcionalidad única, consolidar.

---

## BLOQUE 4: DUPLICACIONES CRÍTICAS

### 4.1 Inicialización de Componentes

**Duplicado en**:
- `main.py` (L85-170)
- `main_with_execution.py` (L128-186)
- Posiblemente en `scripts/live_trading_engine_institutional.py`

**Solución**: Crear método `_initialize_core_components()` compartido.

### 4.2 Config Loading

**Duplicado en**:
- `main.py` (L55-87)
- `main_with_execution.py` (L204-278)

**Variaciones**:
- main_with_execution.py también carga `live_trading_config.yaml`

**Solución**: Método unificado `_load_configs(execution_mode)`.

### 4.3 Directory Creation

**Duplicado en**:
- `main.py` (no explícito, asume existen)
- `main_with_execution.py` (L280-293)

**Solución**: Método unificado `_create_directories()`.

### 4.4 Trading Loop Structure

**Variaciones**:
- `main.py`: Loop con estructura pero sin features
- `main_with_execution.py`: Loop placeholder sin estructura
- `scripts/live_trading_engine.py`: Loop legacy con lógica diferente

**Solución**: Loop UNIFICADO con:
1. MTF update
2. Feature calculation (OFI, CVD, VPIN, L2)
3. Regime detection
4. Signal generation (via StrategyOrchestrator)
5. Brain filtering
6. Execution (via ExecutionAdapter)
7. Reporting

---

## BLOQUE 5: DIAGRAMA ACTUAL (Estado AS-IS)

```
┌─────────────────────────────────────────────────────────────────────┐
│                        USER ENTRY POINTS                            │
└─────────────────────────────────────────────────────────────────────┘
                                  │
        ┌─────────────────────────┼─────────────────────────┐
        │                         │                         │
        ▼                         ▼                         ▼
┌───────────────┐    ┌──────────────────────┐    ┌────────────────────┐
│   main.py     │    │ main_with_           │    │ scripts/live_      │
│               │    │   execution.py       │    │   trading_engine.py│
│ EliteTrading  │    │ EliteTradingSystemV2 │    │ LiveTradingEngine  │
│   System      │    │                      │    │                    │
│               │    │                      │    │                    │
│ ✓ Loop lógica │    │ ✓ ExecutionAdapter   │    │ ✓ Gatekeeper       │
│ ✗ Features    │    │ ✓ KillSwitch         │    │ ✗ Brain            │
│ ✗ Execution   │    │ ✗ Loop TODO          │    │ ✗ Orchestrator     │
│ ✗ KillSwitch  │    │ ✗ Features           │    │                    │
└───────────────┘    └──────────────────────┘    └────────────────────┘
        │                         │                         │
        │                         │                         │
        ▼                         ▼                         ▼
┌─────────────────────────────────────────────────────────────────────┐
│                     SHARED COMPONENTS                               │
│                                                                     │
│  • InstitutionalBrain        • RiskManager                         │
│  • StrategyOrchestrator      • PositionManager                     │
│  • MultiTimeframeManager     • RegimeDetector                      │
│  • MLAdaptiveEngine          • MLSupervisor                        │
│  • InstitutionalReportingSystem                                    │
│                                                                     │
│  ⚠️ PROBLEMA: Inicializados 3+ veces (código duplicado)            │
└─────────────────────────────────────────────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────────┐
│                       MISSING COMPONENTS                            │
│                                                                     │
│  ❌ Feature Pipeline (OFI, CVD, VPIN, L2) en loops live/paper      │
│  ❌ generate_signals() implementado en StrategyOrchestrator         │
│  ❌ MicrostructureEngine unificado                                  │
│  ❌ Level2DepthMonitor                                              │
│  ❌ SpoofingDetector                                                │
└─────────────────────────────────────────────────────────────────────┘
```

**Leyenda**:
- ✓ = Componente implementado
- ✗ = Componente faltante
- ⚠️ = Problema arquitectural

---

## BLOQUE 6: DIAGRAMA PROPUESTO (Estado TO-BE)

```
┌─────────────────────────────────────────────────────────────────────┐
│                    SINGLE UNIFIED ENTRY POINT                       │
│                                                                     │
│                  main_institutional.py                              │
│                                                                     │
│              InstitutionalTradingSystem                             │
│                                                                     │
│  ┌──────────────────────────────────────────────────────────┐     │
│  │ __init__(execution_mode: ExecutionMode)                  │     │
│  │   • RESEARCH (backtest only)                             │     │
│  │   • PAPER (PaperExecutionAdapter)                        │     │
│  │   • LIVE (LiveExecutionAdapter + KillSwitch)             │     │
│  └──────────────────────────────────────────────────────────┘     │
└─────────────────────────────────────────────────────────────────────┘
                                  │
                                  │
        ┌─────────────────────────┼─────────────────────────┐
        │                         │                         │
        ▼                         ▼                         ▼
┌───────────────┐    ┌──────────────────────┐    ┌────────────────────┐
│  BACKTEST     │    │   PAPER TRADING      │    │   LIVE TRADING     │
│   MODE        │    │                      │    │                    │
│               │    │ PaperExecution       │    │ LiveExecution      │
│ BacktestEngine│    │   Adapter            │    │   Adapter          │
│ (existing)    │    │                      │    │ + KillSwitch       │
│               │    │ VenueSimulator       │    │ + MT5Connector     │
└───────────────┘    └──────────────────────┘    └────────────────────┘
                                  │
                                  │
                     ┌────────────┴────────────┐
                     │                         │
                     ▼                         ▼
        ┌─────────────────────┐   ┌──────────────────────┐
        │  UNIFIED LOOP       │   │  FEATURE PIPELINE    │
        │                     │   │                      │
        │ 1. MTF Update       │   │ MicrostructureEngine │
        │ 2. Feature Calc ────┼──▶│   • OFI              │
        │ 3. Regime Detect    │   │   • CVD              │
        │ 4. Generate Signals │   │   • VPIN             │
        │ 5. Brain Filter     │   │   • L2 parsing       │
        │ 6. Execute          │   │   • Imbalance        │
        │ 7. Report           │   └──────────────────────┘
        └─────────────────────┘
                     │
                     ▼
        ┌─────────────────────┐
        │ StrategyOrchestrator│
        │                     │
        │ generate_signals()  │◀── IMPLEMENTAR
        │   (features: Dict)  │
        └─────────────────────┘
                     │
                     ▼
        ┌─────────────────────┐
        │ InstitutionalBrain  │
        │                     │
        │ filter_signals()    │
        │ adjust_sizing()     │
        └─────────────────────┘
                     │
                     ▼
        ┌─────────────────────┐
        │ ExecutionAdapter    │
        │                     │
        │ execute_signal()    │
        │   • PAPER → Sim     │
        │   • LIVE → MT5      │
        └─────────────────────┘
```

**Ventajas**:
1. ✅ UN SOLO entry point
2. ✅ Lógica unificada para RESEARCH/PAPER/LIVE
3. ✅ Feature pipeline integrado
4. ✅ KillSwitch respetado en LIVE
5. ✅ Brain filtering en todos los modos
6. ✅ Zero código duplicado

---

## BLOQUE 7: PLAN DE UNIFICACIÓN

### Fase 1: Crear main_institutional.py (Unificado)

**Acción**:
- Fusionar main.py + main_with_execution.py
- Tomar ExecutionMode, ExecutionAdapter, KillSwitch de main_with_execution.py
- Tomar loop structure de main.py
- Añadir feature pipeline (de BacktestEngine)

**Resultado**: UN entry point único.

### Fase 2: Implementar Feature Pipeline

**Acción**:
- Crear `src/microstructure/engine.py` con `MicrostructureEngine`
- Implementar `calculate_features()` method (OFI, CVD, VPIN, L2)
- Integrar en loop ANTES de generate_signals()

**Resultado**: Features disponibles para estrategias.

### Fase 3: Implementar generate_signals()

**Acción**:
- Añadir método en `StrategyOrchestrator`
- Filtrar estrategias por régimen
- Pasar features a cada estrategia
- Retornar lista de señales

**Resultado**: Estrategias reciben features correctas.

### Fase 4: Deprecar Entry Points Legacy

**Acción**:
- Renombrar `main.py` → `main_DEPRECATED_v1.py`
- Renombrar `main_with_execution.py` → `main_DEPRECATED_v2.py`
- Renombrar `scripts/live_trading_engine.py` → `scripts/live_trading_engine_LEGACY.py`
- Actualizar README con instrucciones: "Use main_institutional.py"

**Resultado**: Usuarios migran al entry point unificado.

### Fase 5: Testing

**Acción**:
- Smoke test con main_institutional.py --mode paper
- Smoke test con main_institutional.py --mode live (demo account)
- Verificar features calculadas correctamente
- Verificar estrategias reciben features
- Verificar Kill Switch funciona en LIVE

**Resultado**: Sistema unificado validado.

---

## BLOQUE 8: ARCHIVOS A MODIFICAR/CREAR

### Crear (Nuevos)

| Archivo | Propósito |
|---------|-----------|
| `main_institutional.py` | Entry point unificado (fusión de main.py + main_with_execution.py) |
| `src/microstructure/__init__.py` | Módulo microstructure |
| `src/microstructure/engine.py` | MicrostructureEngine (feature calculation) |
| `src/microstructure/level2_monitor.py` | Level2DepthMonitor |
| `src/microstructure/spoofing_detector.py` | SpoofingDetector |

### Modificar (Existentes)

| Archivo | Cambios |
|---------|---------|
| `src/strategy_orchestrator.py` | Añadir `generate_signals(market_data, regime, features)` method |
| `config/README_LIVE_TRADING.md` | Actualizar instrucciones: usar main_institutional.py |
| `.gitignore` | Ignorar archivos _DEPRECATED |

### Deprecar (Renombrar)

| Archivo | Nuevo Nombre |
|---------|--------------|
| `main.py` | `main_DEPRECATED_v1.py` |
| `main_with_execution.py` | `main_DEPRECATED_v2.py` |
| `scripts/live_trading_engine.py` | `scripts/live_trading_engine_LEGACY.py` |

---

## BLOQUE 9: MÉTRICAS DE DUPLICACIÓN

### Líneas de Código Duplicadas

| Componente | Duplicado en | Líneas Aprox |
|-----------|--------------|--------------|
| Component initialization | 3 archivos | ~85 líneas × 3 = 255 |
| Config loading | 2 archivos | ~30 líneas × 2 = 60 |
| Directory creation | 2 archivos | ~15 líneas × 2 = 30 |
| Logging setup | 4 archivos | ~20 líneas × 4 = 80 |

**Total duplicación estimada**: ~425 líneas de código duplicadas.

**Reducción esperada post-unificación**: -70% (retener solo 1 copia).

---

## BLOQUE 10: NON-NEGOTIABLES AFECTADOS

| Non-Negotiable | Estado Actual | Impacto |
|----------------|---------------|---------|
| **Risk 0-2%** | ⚠️ Parcial | RiskManager existe pero NO llamado en loops |
| **NO ATR** | ✅ OK | Strategies no usan ATR para sizing |
| **Brain sin violar caps** | ⚠️ Parcial | Brain existe pero NO llamado en loops |
| **Kill Switch LIVE** | ⚠️ Parcial | Existe en main_with_execution.py pero loop es placeholder |

**Conclusión**: NON-NEGOTIABLES están implementados en componentes, pero NO integrados en loops.

---

**FIN DEL ANÁLISIS**

**Próximo paso**: FASE 3 - Diseño e implementación del loop unificado.
