# PLAN OMEGA - ROADMAP COMPLETO
## SUBLIMINE Sistema Institucional 24/5

**Fecha inicio:** 2025-11-16
**Objetivo:** Sistema institucional completo, 24 estrategias operativas, CERO ATR en decisiones críticas
**Estado actual:** FASE 1.2 en progreso (30% completado)

---

## ESTADO ACTUAL (2025-11-16 12:00 UTC)

### ✅ COMPLETADO

**FASE 0 - Reconocimiento Total:**
- ✅ Auditoría completa del repositorio
- ✅ 24 estrategias identificadas y clasificadas
- ✅ 341 violaciones ATR TYPE A detectadas
- ✅ Componentes core mapeados (Brain, Risk, Execution, Features)

**FASE 1.1 - Config YAML Purgado:**
- ✅ 18 parámetros ATR reemplazados en `config/strategies_institutional.yaml`
- ✅ `stop_loss_atr_*` → `stop_loss_pct` (% precio: 0.8-2.0%)
- ✅ `displacement_atr_*` → `displacement_pips` (pips estructurales: 30-40)
- ✅ `buffer_atr` → `buffer_pips` (8 pips fijos)
- ✅ `gap_atr_minimum` → `gap_pips_minimum` (15 pips)
- ✅ `structure_break_atr_min` → `structure_break_pips` (30 pips)

**FASE 1.2 - Estrategias GREEN (parcial):**
- ✅ Guard ATR creado (`scripts/check_no_atr_in_risk.py`) - detecta 341 violaciones
- ✅ Módulo institucional sin ATR (`src/features/institutional_sl_tp.py`)
- ✅ `ofi_refinement.py` purgada de ATR (1/5 GREEN completadas)

### ⏳ EN PROGRESO

**FASE 1.2 - Purga ATR de src/strategies/ (17 archivos activos):**
- ✅ 1/5 GREEN completadas: `ofi_refinement.py`
- ⏳ 4/5 GREEN pendientes (10 violaciones ATR):
  - `vpin_reversal_extreme.py` (3 violaciones)
  - `order_flow_toxicity.py` (2 violaciones)
  - `footprint_orderflow_clusters.py` (3 violaciones)
  - `spoofing_detection_l2.py` (2 violaciones)
- ⏳ 19 estrategias HYBRID/BROKEN pendientes (~140 violaciones ATR)

### ❌ PENDIENTE

**FASE 1.3 - Purga ATR de src/features/, src/core/, src/risk_management.py:**
- ❌ ~50 violaciones ATR en componentes core
- ❌ Archivos críticos: `strategic_stops.py`, `derived_features.py`, `displacement.py`, `technical_indicators.py`, `mtf_data_manager.py`, `position_manager.py`, `regime_detector.py`, `risk_management.py`

**FASE 1.4 - Verificación Guard ATR:**
- ❌ Ejecutar `scripts/check_no_atr_in_risk.py`
- ❌ Objetivo: 0 violaciones TYPE A
- ❌ Validar que YAML + strategies + features estén limpias

**FASE 2 - Institucionalización de 24 Estrategias:**
- ❌ Naming retail/SMC/ICT persistente en:
  - `fvg_institutional.py` → renombrar a `imbalance_zones.py`
  - `order_block_institutional.py` → `absorption_zones.py`
  - `idp_inducement_distribution.py` → `liquidity_engineering.py`
  - `liquidity_sweep.py` → `stop_hunt_detection.py`
- ❌ Metadata institucional completa (strategy_id, family, required_features, risk_profile, quality_dimensions)
- ❌ Docstrings con research basis académica (no SMC/ICT)

**FASE 3 - Integración Ecosistema:**
- ❌ **MicrostructureEngine NO EXISTE** - solo diseño en `docs/MICROSTRUCTURE_ENGINE_DESIGN.md`
  - Debe implementarse como fuente ÚNICA de OFI/VPIN/CVD/L2
  - Reemplaza funciones dispersas en `src/features/`
- ❌ **ExecutionMode/Adapters NO EXISTEN** - solo concepto
  - `ExecutionMode` enum (RESEARCH/PAPER/LIVE)
  - `PaperExecutionAdapter` (simulación sin órdenes reales)
  - `LiveExecutionAdapter` (MT5 con KillSwitch)
- ❌ **KillSwitch NO IMPLEMENTADO** - solo diseño
  - 4 capas: Health, Risk, Market, Emergency
  - Bloquea órdenes LIVE si no está OK
- ❌ **Runtime Profiles NO EXISTEN:**
  - `config/runtime_profile_GREEN_ONLY.yaml` (5 estrategias core)
  - `config/runtime_profile_FULL_24.yaml` (todas las institucionales)
- ❌ **risk_limits.yaml NO EXISTE** - CRÍTICO para risk management
  - Debe crearse con límites 0-2% por idea
  - Caps por símbolo, estrategia, día, drawdown

**FASE 4 - Higiene y Organización:**
- ❌ Limpieza de `/backups/` (94 violaciones ATR en archivos obsoletos)
- ❌ Deprecación formal de:
  - `main.py` → `main_LEGACY.py` + docs
  - `main_with_execution.py` → deprecado
  - Scripts temporales en `/scripts/` sin runbooks
- ❌ Estructura de `src/` reorganizada por dominios
- ❌ Documentación en `docs/` indexada y coherente

**FASE 5 - Testing Institucional:**
- ❌ Smoke tests end-to-end:
  - `scripts/smoke_test_institutional.py`
  - `scripts/smoke_test_backtest.py`
  - `scripts/smoke_test_execution_system.py`
  - `scripts/validate_runtime_profiles.py`
- ❌ Arranque PAPER simulado con GREEN_ONLY profile
- ❌ Arranque PAPER simulado con FULL_24 profile
- ❌ Validación de KillSwitch en diferentes estados

**FASE 6 - Informe Final + Runbook:**
- ❌ Documento OMEGA_FINAL_REPORT.md con:
  - Estado de 24 estrategias (GREEN/REWORKED/DEPRECATED)
  - Edge institucional explicado por estrategia
  - Confirmaciones: ATR eliminado, risk_limits intacto, KillSwitch activo
- ❌ Runbook para Elias:
  - Comandos exactos para 30 días PAPER (GREEN_ONLY)
  - Comandos para 30 días PAPER (FULL_24)
  - Checklist GO/NO-GO antes de LIVE
  - Logs y metrics a revisar
- ❌ Mapa de archivos clave del sistema

---

## DESGLOSE DE TRABAJO RESTANTE

### FASE 1 - ATR Hard Purge (70% pendiente)

**Violaciones ATR detectadas: 341 TYPE A**

Distribución:
- ✅ Config YAML: 18 (100% completado)
- ⏳ Estrategias activas: 150 (7% completado: 10/150)
  - ✅ 1 GREEN completada
  - ⏳ 4 GREEN pendientes (10 violaciones)
  - ⏳ 19 HYBRID/BROKEN pendientes (~140 violaciones)
- ❌ Features/Core/Risk: 50 (0% completado)
- ❌ Backups (IGNORAR): 94 (archivos obsoletos)
- ❌ Docs/Tests: ~29 (baja prioridad)

**Estimación de esfuerzo:**
- FASE 1.2 (estrategias restantes): **8-12 horas**
  - 4 GREEN: 1 hora
  - 19 HYBRID/BROKEN: 7-11 horas (requiere re-diseño de lógica)
- FASE 1.3 (features/core/risk): **4-6 horas**
  - Archivos complejos con dependencias cruzadas
- FASE 1.4 (verificación guard): **1 hora**

**Total FASE 1:** **13-19 horas**

### FASE 2 - Institucionalización (0% completado)

**Tareas:**
1. Renaming de 4 estrategias retail → institucional (2 horas)
2. Metadata completa para 24 estrategias (4 horas)
3. Docstrings con research basis (6 horas)
4. Deprecación formal de conceptos SMC/ICT (3 horas)

**Total FASE 2:** **15 horas**

### FASE 3 - Integración Ecosistema (0% completado)

**Componentes a implementar desde cero:**
1. **MicrostructureEngine** (8-12 horas)
   - Centralizar OFI/VPIN/CVD/L2 calculation
   - Integrar con BacktestEngine, Paper, Live
   - Tests unitarios
2. **ExecutionMode + Adapters** (6-8 horas)
   - ExecutionMode enum
   - PaperExecutionAdapter (simulación)
   - LiveExecutionAdapter (MT5)
3. **KillSwitch 4 capas** (4-6 horas)
   - Health, Risk, Market, Emergency checks
   - Integración con LiveExecutionAdapter
4. **Runtime Profiles** (2 hours)
   - GREEN_ONLY.yaml
   - FULL_24.yaml
5. **risk_limits.yaml** (1 hora)
   - Estructura institucional 0-2%

**Total FASE 3:** **21-29 horas**

### FASE 4 - Higiene (0% completado)

**Tareas:**
1. Limpieza `/backups/` y archivos obsoletos (1 hora)
2. Deprecación formal de mains antiguos (1 hora)
3. Reorganización `src/` por dominios (2 horas)
4. Indexación y coherencia `docs/` (2 horas)

**Total FASE 4:** **6 horas**

### FASE 5 - Testing (0% completado)

**Tareas:**
1. Crear smoke tests (4 archivos, 4 horas)
2. Arranque PAPER simulado GREEN_ONLY (1 hora)
3. Arranque PAPER simulado FULL_24 (1 hora)
4. Validación KillSwitch (2 horas)

**Total FASE 5:** **8 horas**

### FASE 6 - Informe Final (0% completado)

**Tareas:**
1. OMEGA_FINAL_REPORT.md (3 horas)
2. Runbook completo para Elias (2 horas)
3. Mapa de archivos clave (1 hora)

**Total FASE 6:** **6 horas**

---

## ESTIMACIÓN TOTAL

**Trabajo completado:** ~10 horas (FASE 0 + FASE 1.1 + FASE 1.2 parcial)
**Trabajo restante:** **69-85 horas**

**Total Plan OMEGA:** **79-95 horas** (2-2.5 semanas a tiempo completo)

---

## ESTRATEGIA DE ENTREGA INCREMENTAL

Dado que el Plan OMEGA completo requiere 80-95 horas, se propone estrategia incremental:

### CHECKPOINT 1 - MVP GREEN (ACTUAL)
**Objetivo:** Core GREEN strategies operativas en PAPER
**Tiempo:** 8-10 horas adicionales
**Entregables:**
- ✅ 5 estrategias GREEN 100% libres de ATR
- ✅ `config/risk_limits.yaml` creado
- ✅ Smoke test básico (`scripts/smoke_test_green_core.py`)
- ✅ Documentación del estado + roadmap (este documento)

**Valor:** Sistema core funcional para paper trading con estrategias de máxima convicción.

### CHECKPOINT 2 - Ecosistema Integrado
**Objetivo:** MicrostructureEngine + Execution + KillSwitch
**Tiempo:** 21-29 horas
**Entregables:**
- MicrostructureEngine implementado
- ExecutionMode + PaperExecutionAdapter + LiveExecutionAdapter
- KillSwitch 4 capas operativo
- Runtime profiles (GREEN_ONLY, FULL_24)

**Valor:** Infraestructura institucional completa, lista para LIVE con cualquier estrategia.

### CHECKPOINT 3 - Sistema Completo
**Objetivo:** 24 estrategias institucionalizadas + testing + docs
**Tiempo:** 40-46 horas
**Entregables:**
- FASE 1 completa (CERO ATR en todo el sistema)
- FASE 2 completa (24 estrategias institucionalizadas)
- FASE 4 completa (repo limpio y organizado)
- FASE 5 completa (smoke tests end-to-end)
- FASE 6 completa (informe final + runbook)

**Valor:** Sistema producción-ready 24/5 con todas las estrategias operativas.

---

## PRIORIDADES CRÍTICAS

### 🔴 CRÍTICO (Bloqueante para PAPER/LIVE):
1. **risk_limits.yaml** - NO EXISTE, sistema sin caps de riesgo
2. **KillSwitch** - NO EXISTE, LIVE sin protección
3. **Purga ATR de 5 GREEN** - Estrategias core con decisiones retail
4. **ExecutionMode + Adapters** - NO HAY separación PAPER/LIVE

### 🟠 ALTA (Mejora significativa):
1. **MicrostructureEngine** - Centralizar features, evitar duplicación
2. **Runtime Profiles** - Facilitar switching GREEN_ONLY ↔ FULL_24
3. **Purga ATR completa (24 strategies)** - Eliminar último vestigio retail
4. **Institucionalización naming** - Claridad conceptual

### 🟡 MEDIA (Nice to have):
1. **Smoke tests end-to-end** - Validación automatizada
2. **Higiene repo** - Limpieza backups/obsoletos
3. **Docs indexadas** - Navegación mejorada

---

## ARCHIVOS CLAVE DEL SISTEMA

### Configuración:
- ✅ `config/strategies_institutional.yaml` - Parámetros de 24 estrategias (ATR purgado)
- ❌ `config/risk_limits.yaml` - **NO EXISTE** (CRÍTICO)
- ❌ `config/runtime_profile_GREEN_ONLY.yaml` - **NO EXISTE**
- ❌ `config/runtime_profile_FULL_24.yaml` - **NO EXISTE**
- ✅ `config/system_config.yaml` - Configuración global

### Estrategias (24 archivos):
**GREEN (5 - microestructura pura):**
- ⏳ `src/strategies/ofi_refinement.py` - Order Flow Imbalance (ATR purgado ✅)
- ⏳ `src/strategies/vpin_reversal_extreme.py` - VPIN reversals (3 ATR)
- ⏳ `src/strategies/order_flow_toxicity.py` - Toxic flow detection (2 ATR)
- ⏳ `src/strategies/footprint_orderflow_clusters.py` - Volume profile (3 ATR)
- ⏳ `src/strategies/spoofing_detection_l2.py` - L2 spoofing (2 ATR)

**HYBRID (14 - requieren institucionalización):**
- ⏳ `src/strategies/mean_reversion_statistical.py` (3 ATR)
- ⏳ `src/strategies/liquidity_sweep.py` (2 ATR) - **RENOMBRAR** → `stop_hunt_detection.py`
- ⏳ `src/strategies/momentum_quality.py` (4 ATR)
- ⏳ `src/strategies/order_block_institutional.py` (6 ATR) - **RENOMBRAR** → `absorption_zones.py`
- ⏳ `src/strategies/kalman_pairs_trading.py` (3 ATR)
- ⏳ `src/strategies/correlation_divergence.py` (3 ATR)
- ⏳ `src/strategies/volatility_regime_adaptation.py` (6 ATR)
- ⏳ `src/strategies/breakout_volume_confirmation.py` (9 ATR)
- ⏳ `src/strategies/fvg_institutional.py` (4 ATR) - **RENOMBRAR** → `imbalance_zones.py`
- ⏳ `src/strategies/htf_ltf_liquidity.py` (3 ATR)
- ⏳ `src/strategies/iceberg_detection.py` (3 ATR)
- ⏳ `src/strategies/idp_inducement_distribution.py` (5 ATR) - **RENOMBRAR** → `liquidity_engineering.py`
- ⏳ `src/strategies/nfp_news_event_handler.py` (11 ATR)
- ⏳ `src/strategies/statistical_arbitrage_johansen.py` (0 ATR ✅)

**ADVANCED (5 - stat arb / regime):**
- ⏳ `src/strategies/fractal_market_structure.py` (3 ATR)
- ⏳ `src/strategies/correlation_cascade_detection.py` (3 ATR)
- ⏳ `src/strategies/crisis_mode_volatility_spike.py` (3 ATR)
- ⏳ `src/strategies/calendar_arbitrage_flows.py` (7 ATR)
- ⏳ `src/strategies/topological_data_analysis_regime.py` (2 ATR)

### Core Components:
- ✅ `src/core/brain.py` - Signal arbitration & orchestration
- ⏳ `src/core/risk_manager.py` - Risk allocation (usa ATR)
- ⏳ `src/core/position_manager.py` - Position lifecycle (usa ATR)
- ⏳ `src/core/regime_detector.py` - Market regime detection (usa ATR)
- ⏳ `src/core/mtf_data_manager.py` - Multi-timeframe data (usa ATR)
- ✅ `src/core/conflict_arbiter.py` - Signal conflict resolution
- ✅ `src/core/ml_adaptive_engine.py` - ML integration

### Features:
- ❌ **`src/features/microstructure.py`** - Funciones básicas, NO es MicrostructureEngine
- ⏳ `src/features/strategic_stops.py` - Stop placement (COMPLETAMENTE basado en ATR - reemplazar con institutional_sl_tp.py)
- ✅ `src/features/institutional_sl_tp.py` - Nuevo módulo sin ATR ✅
- ⏳ `src/features/derived_features.py` - Features derivadas (usa ATR)
- ⏳ `src/features/displacement.py` - Displacement calculation (usa ATR)
- ⏳ `src/features/technical_indicators.py` - Indicators (usa ATR)
- ✅ `src/features/ofi.py` - Order Flow Imbalance
- ✅ `src/features/order_flow.py` - Order flow metrics
- ✅ `src/features/orderbook_l2.py` - Level 2 orderbook

### Execution:
- ❌ **ExecutionMode / PaperExecutionAdapter / LiveExecutionAdapter - NO IMPLEMENTADOS**
- ❌ **KillSwitch - NO IMPLEMENTADO**
- ✅ `src/execution/broker_client.py` - MT5 broker integration
- ✅ `src/execution/circuit_breakers.py` - Circuit breakers
- ✅ `src/execution/data_validator.py` - Data validation

### Risk:
- ⏳ `src/risk_management.py` - Risk management (usa ATR)
- ✅ `src/risk/factor_limits.py` - Factor exposure limits

### Scripts:
- ✅ `scripts/check_no_atr_in_risk.py` - Guard ATR (detecta 341 violaciones)
- ❌ `scripts/smoke_test_institutional.py` - NO EXISTE
- ❌ `scripts/smoke_test_green_core.py` - NO EXISTE
- ❌ `scripts/validate_runtime_profiles.py` - NO EXISTE
- ✅ `scripts/live_trading_engine_institutional.py` - Main institutional
- ✅ `scripts/institutional_backtest.py` - Backtest engine

### Documentación:
- ✅ `docs/MICROSTRUCTURE_ENGINE_DESIGN.md` - Diseño MicrostructureEngine (NO implementado)
- ✅ `docs/RISK_ENGINE_DESIGN.md` - Diseño Risk Engine
- ✅ `docs/RISK_EXECUTION_PROFILES.md` - Perfiles de ejecución
- ✅ `docs/OMEGA_ROADMAP.md` - Este documento
- ❌ `docs/OMEGA_FINAL_REPORT.md` - NO EXISTE

---

## SIGUIENTES PASOS INMEDIATOS

### Para Claude (próxima sesión):
1. Completar purga ATR de 4 estrategias GREEN restantes (~1 hora)
2. Crear `config/risk_limits.yaml` institucional
3. Crear smoke test GREEN core básico
4. Commit + push

### Para Elias (decisión estratégica):
1. **Revisar este roadmap** - ¿Prioridades correctas?
2. **Decidir estrategia de entrega:**
   - Opción A: Continuar CHECKPOINT 1 (MVP GREEN en 8-10 horas)
   - Opción B: Saltar a CHECKPOINT 2 (Ecosistema completo en 21-29 horas)
   - Opción C: Plan completo secuencial (80-95 horas)
3. **Validar arquitectura propuesta:**
   - MicrostructureEngine como fuente única de features
   - ExecutionMode + Adapters para separación PAPER/LIVE
   - KillSwitch 4 capas
   - Runtime Profiles para switching fácil

### Para el sistema (checklist de arranque):
- [ ] BLOQUEANTE: Crear `config/risk_limits.yaml`
- [ ] BLOQUEANTE: Implementar KillSwitch básico
- [ ] BLOQUEANTE: Purgar ATR de 5 estrategias GREEN
- [ ] NICE-TO-HAVE: Implementar MicrostructureEngine
- [ ] NICE-TO-HAVE: Crear runtime profiles

---

## CONTACTO / REFERENCIAS

**Repositorio:** `sublimine/TradingSystem`
**Rama de trabajo:** `claude/sublimine-institutional-omega-01PcHwxQAbXk1E9cBxpCn9jS`
**Última actualización:** 2025-11-16 12:00 UTC
**Progreso:** 30% del Plan OMEGA completado

**Documentos relacionados:**
- `ANALISIS_INSTITUCIONAL_COMPLETO.md` - Análisis institucional previo
- `MICROSTRUCTURE_ENGINE_DESIGN.md` - Diseño de MicrostructureEngine
- `RISK_EXECUTION_PROFILES.md` - Perfiles de riesgo y ejecución
- `AUDITORIA_ESTRATEGIAS_CONSOLIDADA.md` - Auditoría previa de estrategias

---

**Nota final:** Este roadmap es un documento vivo. Se actualizará conforme avance el trabajo. La estimación de 80-95 horas totales es conservadora y asume trabajo concentrado sin interrupciones. En un entorno real con context switching y revisiones, podría extenderse a 3-4 semanas.

**Filosofía OMEGA:** "No pares hasta que el algoritmo sea institucional al 100%. Sin azúcar, sin atajos, sin opciones."
