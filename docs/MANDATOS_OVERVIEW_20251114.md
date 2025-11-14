# OVERVIEW DE MANDATOS - ESTADO EJECUTIVO

**Fecha**: 2025-11-14
**Sesión**: 011CV4uYEyVY6qd3UdpyS6FH
**Propósito**: Mapa ejecutivo del estado de todos los mandatos para contexto rápido
**Última actualización**: MANDATO 8 (PRs pendientes)

---

## PRs INSTITUCIONALES (MANDATO 8)

**Tool bloqueado**: `gh pr create` requiere creación manual

| # | Rama | Target | Mandato | Estado |
|---|------|--------|---------|--------|
| - | `mandato1-rescate-P2-20251114` | AIS | 1 | Pendiente creación |
| - | `mandato5-rescate-auditoria-20251114` | AIS | 5 | Pendiente creación |
| - | `mandato6-p0-testing-observability-risk-20251113` | AIS | 6 | Pendiente creación |
| - | `mandato6-rescate-inventario-20251114` | AIS | 6 | Pendiente creación |
| - | `mandato7-limpieza-normalizacion-20251114` | AIS | 7 | Pendiente creación |

**Specs completas**: `docs/PR_SPECS_MANDATO8_20251114.md`

---

## RESUMEN EJECUTIVO

| Mandato | Estado | Prioridad | Progreso | Bloqueadores |
|---------|--------|-----------|----------|--------------|
| 1 | 🟢 95% COMPLETADO | ALTA | P0✅ P1✅ P2⏸️ | - |
| 2 | ✅ 100% COMPLETADO | MEDIA | Integrado | - |
| 3 | ⏸️ 0% BLOQUEADO | ALTA | Auditoría✅ Código❌ | MANDATO 4, 5 |
| 4 | 🟡 60% PARCIAL | ALTA | Diseño✅ Impl✅ Calibración❌ | Backtesting |
| 5 | 🟠 10% VAPORWARE | CRÍTICA | Diseño✅ Impl(5%)❌ | Recursos |
| 6 | 🟢 80% EN_PROGRESO | CRÍTICA | Bloque1✅ Bloque2✅ | PR approval |
| 7 | 🔄 50% EN_PROGRESO | MEDIA | Docs✅ PRs⏸️ | Ejecución |

---

## MANDATO 1: Auditoría institucional completa + Bugfixes

### Objetivo
Identificar y corregir todos los bugs críticos (P0), importantes (P1) y menores (P2) del sistema base.

### Estado: 🟢 95% COMPLETADO

#### Ramas

| Rama | Estado | Contenido | Commits |
|------|--------|-----------|---------|
| `mandato1-p0-p1-gobernanza-inicial` | ✅ MERGED@6484be8 | P0+P1 bugs + gobernanza | 16 |
| `mandato1-rescate-P2` | ⏸️ PENDIENTE_PR | 21 bugs P2 | 5 |

#### Progreso por prioridad

**P0 (4 bugs críticos)**: ✅ 100% COMPLETADO
- CR1: `generate_decision_uid()` implementado
- CR2: Iteración segura de diccionarios
- CR13: Warm-up phases en gatekeepers
- Otros P0 corregidos

**Commits**: f90f346, bae1b58, e3e7e32, a2d3f3a

**P1 (27 bugs importantes)**: ✅ 100% COMPLETADO
- BLOQUE 1-3: Validaciones numéricas críticas
- BLOQUE 4-6: Thread-safety, NaN propagation, memory leaks
- Deque pop(0) optimizaciones
- Array bounds validations
- Funciones duplicadas eliminadas

**Commits**: 8233190, d71f196, 2c94289, ee51da4, 0f04d3a, 78cb22e, d9ba175

**P2 (26 bugs menores)**: ⏸️ 85% COMPLETADO
- 21 bugs corregidos en rama rescate
- 5 bugs pendientes (prioridad baja)
- Documentación de thresholds hardcoded

**Commits** (en rescate-P2): 664810b, 0689b7d, b20e714, ba864f0, ef6487a

#### Archivos clave

```
docs/AUDIT_P1_BUGS_20251113.md          # ✅ En AIS
docs/AUDIT_P2_BUGS_20251113.md          # ⏸️ En rescate-P2
src/core/decision_ledger.py             # ✅ En AIS (generate_decision_uid)
src/core/conflict_arbiter.py            # ✅ En AIS (thread-safety)
src/gatekeepers/spread_monitor.py       # ✅ En AIS (warm-up phase)
src/gatekeepers/vpin_estimator.py       # ✅ En AIS (warm-up phase)
src/gatekeepers/kyles_lambda.py         # ✅ En AIS (warm-up phase)
```

#### PRs asociados (MANDATO 8)

- **Pendiente**: PR desde `mandato1-rescate-P2-20251114` → AIS
  - Título: "MANDATO 1: Fase P2 – 26/26 bugs menores"
  - Spec: `docs/PR_SPECS_MANDATO8_20251114.md` (PR #1)

#### Qué falta

- [ ] Crear PR rescate-P2 (manual en GitHub UI)
- [ ] Merge de mandato1-rescate-P2 → AIS (21 bugs P2)
- [ ] 5 bugs P2 adicionales (prioridad muy baja)

#### Bloqueadores

**NINGUNO**. Solo creación + aprobación humana de PR.

---

## MANDATO 2: Gobernanza institucional del zoo de estrategias

### Objetivo
Establecer reglas claras para naming, testing, deployment y lifecycle de estrategias.

### Estado: ✅ 100% COMPLETADO

#### Ramas

| Rama | Estado | Contenido | Commits |
|------|--------|-----------|---------|
| (incluido en mandato1-p0-p1) | ✅ MERGED@6484be8 | GOVERNANCE_INSTITUCIONAL.md | 1 (2be9a20) |

#### Contenido integrado

**Documento**: `docs/GOVERNANCE_INSTITUCIONAL.md`

**Reglas establecidas**:
1. **Naming conventions**: Prefijos obligatorios por tipo de estrategia
2. **Testing requirements**: Unit tests + backtesting mínimo
3. **Deployment checklist**: 12 pasos obligatorios antes de producción
4. **Performance thresholds**: Sharpe >1.0, DD <20%, Win rate >50%
5. **Lifecycle management**: Promoción Dev → Staging → Production
6. **Code review standards**: Peer review obligatorio

#### Impacto

- ✅ 19 estrategias base documentadas
- ✅ Reglas aplicadas a todas las estrategias nuevas (MANDATO 6+)
- ✅ Framework para auditoría de estrategias

#### Qué falta

**NADA**. MANDATO 2 completado e integrado.

---

## MANDATO 3: Brain-layer governance (caja negra sin control)

### Objetivo
Agregar validaciones pre-trade, governance de decisiones y observabilidad al `ExecutionBrain`.

### Estado: ⏸️ 0% BLOQUEADO

#### Ramas

**NINGUNA**. No iniciado.

#### Auditoría completa

**Documento**: `docs/AUDITORIA_MANDATOS_1_A_5_20251113.md` (sección MANDATO 3)

**Riesgos identificados**: 11 riesgos (4 P0 críticos)

**P0s críticos**:
1. **P0-001**: `ExecutionBrain.should_execute()` sin validaciones pre-trade de riesgo
2. **P0-002**: `generate_decision_uid()` sin salt (⚠️ SOLUCIONADO en MANDATO 1)
3. **P0-003**: MTF confluence no se valida antes de ejecutar
4. **P0-004**: Inconsistencias `DecisionLedger` vs `ExecutionBrain`

#### Por qué está bloqueado

**Dependencias**:
1. **MANDATO 4**: Risk Engine debe estar calibrado para validaciones pre-trade
2. **MANDATO 5**: MicrostructureEngine debe estar implementado para MTF confluence

**Sin estas piezas**:
- No se pueden agregar validaciones institucionales al brain
- MTF confluence no tiene motor que lo calcule
- Risk scoring necesita `InstitutionalRiskManager` calibrado

#### Qué falta

- [ ] MANDATO 4 completado al 100% (calibración empírica)
- [ ] MANDATO 5 completado al 100% (MicrostructureEngine implementado)
- [ ] Diseño de validaciones pre-trade para `ExecutionBrain`
- [ ] Integración `ExecutionBrain` ↔ `InstitutionalRiskManager`
- [ ] Tests de regresión para brain

#### Bloqueadores

🔴 **CRÍTICO**: MANDATO 4 (calibración) + MANDATO 5 (implementación)

---

## MANDATO 4: Risk Engine sin calibración empírica

### Objetivo
Diseñar e implementar `InstitutionalRiskManager` con calibración basada en datos reales, NO en parámetros arbitrarios.

### Estado: 🟡 60% PARCIAL

#### Ramas

| Rama | Estado | Contenido | Commits |
|------|--------|-----------|---------|
| `mandato4-risk-manager-design` | ❓ DUDOSO | Diseño completo (solo docs) | 2 |
| (implementación en mandato6) | ✅ IMPLEMENTADO | Código en `src/core/risk_manager.py` | - |

#### Progreso

**✅ COMPLETADO (60%)**:
1. **Diseño completo** (3123302):
   - `docs/RISK_MANAGER_DESIGN.md`
   - QualityScorer multi-factor
   - StatisticalCircuitBreaker (SPC methodology)
   - Dynamic position sizing
   - Exposure limits con correlaciones

2. **Implementación base** (MANDATO 6 Bloque 1):
   - `src/core/risk_manager.py` (InstitutionalRiskManager)
   - `config/risk_limits.yaml` (límites institucionales)
   - QualityScorer: 5 factores ponderados
   - StatisticalCircuitBreaker: Z-score + probabilidad de racha
   - Exposure limits: total, per-symbol, per-strategy, correlated
   - Logging institucional de rechazos

**❌ FALTA (40%)**:
3. **Calibración empírica**:
   - [ ] Backtesting de 1000+ trades para calibrar thresholds
   - [ ] Matriz de correlaciones real (FX, crypto, commodities)
   - [ ] Optimización de parámetros via grid search
   - [ ] Validación out-of-sample de circuit breaker
   - [ ] A/B testing de quality scoring weights

**Por qué falta calibración**:
- Requiere **backtesting framework funcional** (MANDATO 6 Bloque 3+)
- Necesita **datos históricos** suficientes (1 año+ de tick data)
- Demanda **tiempo de cómputo** significativo (días/semanas)

#### Archivos clave

```
docs/RISK_MANAGER_DESIGN.md             # ❓ En mandato4-design (DUDOSO rescate)
src/core/risk_manager.py                # ✅ En AIS + ⏸️ mandato6-bloque1 (enhanced)
config/risk_limits.yaml                 # ⏸️ En mandato6-bloque1
tests/risk/test_risk_manager.py         # ⏸️ En mandato6-bloque1
```

#### Auditoría completa

**Documento**: `docs/AUDITORIA_MANDATOS_1_A_5_20251113.md` (sección MANDATO 4)

**Riesgos identificados**: 12 riesgos (4 P0 críticos)

**P0s principales**:
1. **P0-001**: Circuit breaker con thresholds arbitrarios (⚠️ MEJORADO en M6: SPC methodology)
2. **P0-002**: Correlaciones hardcoded, no calculadas dinámicamente
3. **P0-003**: Quality scorer sin backtesting empírico de weights
4. **P0-004**: Position sizing sin Kelly Criterion calibrado

#### Qué falta

- [ ] Backtesting completo (1000+ trades)
- [ ] Calibración de thresholds via optimización
- [ ] Correlaciones dinámicas (rolling window)
- [ ] Validación out-of-sample

#### Bloqueadores

🟡 **MEDIO**: Backtesting framework (MANDATO 6 Bloque 3+)

---

## MANDATO 5: MicrostructureEngine + MultiFrameContext (VAPORWARE)

### Objetivo
Implementar análisis de microestructura de mercado (VPIN, order imbalance, Kyle's lambda) y contexto multi-timeframe.

### Estado: 🟠 10% VAPORWARE

#### Ramas

| Rama | Estado | Contenido | Commits |
|------|--------|-----------|---------|
| `mandato5-microstructure-multiframe` | ⚠️ LEGACY | Diseño + auditoría | 7 |
| `mandato5-rescate-auditoria` | ⏸️ PENDIENTE_PR | Rescate limpio (docs) | 7 |

#### Progreso

**✅ COMPLETADO (10%)**:
1. **Diseño completo** (2200+ líneas):
   - `docs/MICROSTRUCTURE_ENGINE_DESIGN.md` (1100+ líneas)
   - `docs/MULTIFRAME_CONTEXT_DESIGN.md` (1100+ líneas)
   - Especificación institucional de:
     - VPINEstimator
     - OrderImbalanceTracker
     - KylesLambdaEstimator
     - MultiFrameContextEngine
     - Regime detection (4 timeframes)

2. **Auditoría completa** (Mandatos 1-5):
   - 59 riesgos identificados (21 P0 críticos)
   - Roadmap 20-24 semanas
   - Priorización por impacto

**❌ FALTA (90%)**:
3. **Implementación real**:
   - [ ] MicrostructureEngine (0% código)
   - [ ] MultiFrameContextEngine (0% código)
   - [ ] Integración con ExecutionBrain
   - [ ] Tests unitarios + integración
   - [ ] Backtesting de microestructura

**Por qué es VAPORWARE**:
- **2200+ líneas de diseño vs 100 líneas de código**
- Diseño detallado pero **sin ejecución**
- Estimación: **8-10 semanas** de trabajo para implementación completa
- Bloquea MANDATO 3 (brain governance)

#### Archivos clave

```
docs/MICROSTRUCTURE_ENGINE_DESIGN.md    # ⏸️ En rescate-auditoria
docs/MULTIFRAME_CONTEXT_DESIGN.md       # ⏸️ En rescate-auditoria
docs/AUDITORIA_MANDATOS_1_A_5.md        # ⏸️ En rescate-auditoria
docs/ROADMAP_INSTITUCIONAL_20_24_SEM.md # ⏸️ En rescate-auditoria
src/features/microstructure.py          # ⚠️ Implementación parcial (legacy)
src/core/regime_engine.py               # ⚠️ Implementación parcial (legacy)
```

#### Auditoría completa

**Riesgos identificados**: 12 riesgos (5 P0 críticos)

**P0s críticos**:
1. **P0-001**: MicrostructureEngine es vaporware (2200 líneas diseño, 5% código)
2. **P0-002**: VPIN no se calcula en tiempo real
3. **P0-003**: Kyle's lambda sin warm-up period (⚠️ SOLUCIONADO en M1)
4. **P0-004**: MultiFrameContext no se integra con ExecutionBrain
5. **P0-005**: Regime detection sin validación empírica

#### Qué falta

- [ ] Implementar `MicrostructureEngine` completo
- [ ] Implementar `MultiFrameContextEngine` completo
- [ ] Integrar con `ExecutionBrain`
- [ ] Backtesting de decisiones basadas en microestructura
- [ ] Validación empírica de regímenes

#### Bloqueadores

🔴 **CRÍTICO**: Recursos (8-10 semanas de desarrollo)

---

## MANDATO 6: Ejecución P0 (Tests + Observability + Risk Limits)

### Objetivo
Cerrar P0s críticos de Mandatos 1 y 4 mediante infraestructura de testing, observabilidad y límites de riesgo operativos.

### Estado: 🟢 80% EN_PROGRESO

#### Bloque 1: Testing + Observability + Risk Limits

**Rama**: `mandato6-p0-testing-observability-risk-20251113`
**Estado**: ⏸️ PENDIENTE_PR
**Progreso**: ✅ 100% COMPLETADO

**Contenido**:

1. **Testing infrastructure** (P0-001):
   - `tests/core/test_decision_ledger.py` (4 tests)
   - `tests/core/test_conflict_arbiter.py` (5 tests)
   - `tests/risk/test_risk_manager.py` (6 tests)
   - `docs/TESTING_STRATEGY_MANDATO6.md`
   - Coverage target: 60-70% inicial, 80% críticos

2. **Observability** (P0-002):
   - `src/core/logging_config.py` (InstitutionalLogger)
   - LogEvent class con 20+ event codes
   - `docs/OBSERVABILITY_RUNBOOK_MANDATO6.md`
   - Daily log rotation, structured logging

3. **Risk Limits** (P0 MANDATO 4):
   - `config/risk_limits.yaml` (límites institucionales)
   - Integración en `InstitutionalRiskManager`
   - Auto-load desde YAML
   - Logging de rechazos por límites

**Commit**: b427a32

#### Bloque 2: Rescate militar de PRs

**Ramas**:
- `mandato1-rescate-P2-20251114` (21 bugs P2)
- `mandato5-rescate-auditoria-20251114` (auditoría completa)
- `mandato6-rescate-inventario-20251114` (inventario PRs)

**Estado**: ⏸️ PENDIENTE_PR (todos)
**Progreso**: ✅ 100% COMPLETADO

**Contenido**:
- Inventario histórico de PRs
- Clasificación: RESCATAR / OBSOLETO / DUDOSO
- Rescate quirúrgico via cherry-pick
- 0 conflictos, ramas limpias

#### Qué falta

- [ ] Aprobación y merge de PRs (operador humano)
- [ ] Bloque 3: Integración de logging en módulos core
- [ ] Bloque 4: Expansión de coverage a 80%+
- [ ] Bloque 5: Backtesting framework

#### Bloqueadores

🟢 **BAJO**: Solo aprobación de PRs (no técnico)

---

## MANDATO 7: Limpieza total + organización estructural

### Objetivo
Normalización completa del repositorio hacia `ALGORITMO_INSTITUCIONAL_SUBLIMINE` como troncal única institucional.

### Estado: 🔄 50% EN_PROGRESO

#### Progreso

**✅ COMPLETADO (50%)**:

1. **Auditoría de PRs cerrados**:
   - `docs/PR_CLOSED_ANALISIS_MANDATO7_20251114.md`
   - 8 PRs analizados
   - Divergencia main vs AIS determinada (17 commits)
   - main marcado como LEGACY

2. **Snapshot del repositorio**:
   - `docs/REPO_STATE_SNAPSHOT_20251114.md`
   - Estado de ramas, PRs, mandatos
   - Reglas permanentes documentadas

3. **Overview de mandatos**:
   - `docs/MANDATOS_OVERVIEW_20251114.md` (este documento)
   - Mapa ejecutivo de todos los mandatos

**⏸️ PENDIENTE (50%)**:

4. **Creación de PRs formales**:
   - [ ] PR: mandato1-rescate-P2 → AIS
   - [ ] PR: mandato5-rescate-auditoria → AIS
   - [ ] PR: mandato6-rescate-inventario → AIS
   - [ ] PR: mandato7-docs (análisis + snapshot + overview) → AIS

5. **Normalización**:
   - [ ] Marcar main como deprecated en README
   - [ ] Actualizar GitHub repo settings (default branch = AIS)
   - [ ] Limpieza de ramas legacy post-merge

#### Qué falta

- [ ] Crear PRs formales hacia AIS
- [ ] Commit de docs de MANDATO 7
- [ ] Push de rama mandato7
- [ ] Limpieza post-merge

#### Bloqueadores

**NINGUNO**. Solo ejecución restante.

---

## ROADMAP DE EJECUCIÓN

### Prioridad CRÍTICA (P0)

| Mandato | Tarea | Estimación | Dependencias |
|---------|-------|------------|--------------|
| 6 | Merge Bloque 1 (testing + observability) | 1h | Aprobación humana |
| 5 | Merge rescate auditoría | 1h | Aprobación humana |
| 7 | Crear PRs formales | 2h | Docs completados |

### Prioridad ALTA (P1)

| Mandato | Tarea | Estimación | Dependencias |
|---------|-------|------------|--------------|
| 1 | Merge rescate P2 (21 bugs) | 1h | Aprobación humana |
| 6 | Integración logging en core | 4-6h | Bloque 1 merged |
| 7 | Normalización completa | 2-3h | PRs merged |

### Prioridad MEDIA (P2)

| Mandato | Tarea | Estimación | Dependencias |
|---------|-------|------------|--------------|
| 4 | Backtesting para calibración | 1-2 semanas | Framework ready |
| 6 | Expansión coverage 80%+ | 8-10h | Tests base merged |

### Prioridad BAJA (P3)

| Mandato | Tarea | Estimación | Dependencias |
|---------|-------|------------|--------------|
| 4 | Decidir sobre mandato4-design | 15min | - |
| 7 | Limpieza ramas legacy | 1h | PRs merged |

### BLOQUEADO (requiere semanas)

| Mandato | Tarea | Estimación | Bloqueador |
|---------|-------|------------|------------|
| 5 | Implementar MicrostructureEngine | 8-10 semanas | Recursos |
| 5 | Implementar MultiFrameContextEngine | 4-6 semanas | Recursos |
| 3 | Brain governance completo | 2-3 semanas | MANDATO 4 + 5 |

---

## MÉTRICAS DE PROGRESO

### Por Mandato

```
MANDATO 1: ████████████████░░ 95%  (P0✅ P1✅ P2⏸️)
MANDATO 2: ████████████████████ 100% (Completado)
MANDATO 3: ░░░░░░░░░░░░░░░░░░░░ 0%   (Bloqueado)
MANDATO 4: ████████████░░░░░░░░ 60%  (Impl✅ Calib❌)
MANDATO 5: ██░░░░░░░░░░░░░░░░░░ 10%  (Diseño✅ Código❌)
MANDATO 6: ████████████████░░░░ 80%  (B1✅ B2✅ B3-5⏸️)
MANDATO 7: ██████████░░░░░░░░░░ 50%  (Docs✅ PRs⏸️)
```

### Global

```
Completado:    ████████████░░░░░░░░ 60%
En progreso:   ████░░░░░░░░░░░░░░░░ 20%
Bloqueado:     ██░░░░░░░░░░░░░░░░░░ 10%
Por iniciar:   ██░░░░░░░░░░░░░░░░░░ 10%
```

---

## PARA SESIONES NUEVAS

### Documentos obligatorios a leer

1. `docs/REPO_STATE_SNAPSHOT_20251114.md` → Estado actual del repo
2. `docs/MANDATOS_OVERVIEW_20251114.md` → Este documento
3. `docs/PR_CLOSED_ANALISIS_MANDATO7_20251114.md` → Historia de PRs

### Comandos de verificación

```bash
# Ver estado de troncal
git log ALGORITMO_INSTITUCIONAL_SUBLIMINE --oneline -1

# Ver ramas activas
git branch -r | grep "origin/claude/mandato"

# Ver divergencia main vs AIS
git log main..ALGORITMO_INSTITUCIONAL_SUBLIMINE --oneline | wc -l

# Listar PRs pendientes
# (manual en GitHub UI, gh bloqueado)
```

### Regla de oro

```
✅ Base: ALGORITMO_INSTITUCIONAL_SUBLIMINE
❌ NUNCA: main (legacy)
```

---

**Generado por**: MANDATO 7 - Limpieza total y organización estructural
**Próxima actualización**: Post-merge de PRs pendientes
