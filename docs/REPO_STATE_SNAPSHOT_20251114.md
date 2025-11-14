# SNAPSHOT DEL REPOSITORIO - MANDATO 7

**Fecha**: 2025-11-14 **Sesión**: 011CV4uYEyVY6qd3UdpyS6FH
**Propósito**: Fotografía estructural completa del sistema SUBLIMINE para contexto en sesiones nuevas

---

## ESTADO ACTUAL

### Troncal institucional

```
Rama: ALGORITMO_INSTITUCIONAL_SUBLIMINE
HEAD: 6484be8 - "Merge: MANDATO 1 P0+P1 bugfixes + gobernanza (simulando merge de PR aprobado)"
Fecha: 2025-11-13
```

**Contenido integrado**:
- ✅ Baseline institucional (109 bugs, 19 estrategias, deployment VPS)
- ✅ MANDATO 1 completo (P0: 4 bugs + P1: 27 bugs)
- ✅ MANDATO 2 completo (gobernanza estratégica)
- ✅ Critical Reviews CR1-CR13 (threading, array bounds, warm-up phases)

**Último commit**:
```
6484be8 Merge: MANDATO 1 P0+P1 bugfixes + gobernanza
├─ d71f196 fix(P1): BLOQUES 4-6 - Thread-safety, NaN propagation y memory leaks (13 bugs)
├─ 8233190 fix(P1): BLOQUES 1-3 - Correcciones de validaciones numéricas críticas
├─ 319be90 chore: Agregar .gitattributes para normalización LF en archivos Python
├─ f335970 docs(audit): Auditoría exhaustiva P1 - 27 bugs importantes identificados
└─ 2be9a20 docs(governance): MANDATO 2.5 - Documento normativo de gobernanza del repositorio
```

---

### Ramas legacy (NO USAR)

#### main (OBSOLETO)

```
Rama: main
HEAD: d11e1cc - "Merge pull request #1 from sublimine/claude/repo-context-summary-..."
Estado: LEGACY - 17 commits detrás de AIS
```

**⚠️ IMPORTANTE**:
- **NO usar main como base para nada**
- **NO crear PRs hacia main**
- main quedó congelado en d11e1cc (baseline institucional)
- Todo el contenido de main está ya en AIS

---

## RAMAS ACTIVAS POR MANDATO

### MANDATO 1: Auditoría + Bugfixes

| Rama | Estado | Commits | Target | Contenido |
|------|--------|---------|--------|-----------|
| `mandato1-p0-p1-gobernanza-inicial` | ✅ MERGED@6484be8 | 16 | AIS | P0+P1 bugs + gobernanza |
| `mandato1-p2-minor-bugs` | ⚠️ LEGACY | 5 | - | Sustituido por rescate |
| `mandato1-rescate-P2` | ⏸️ PENDIENTE_PR | 5 | AIS | 21 bugs P2 (rescate limpio) |

**Resumen MANDATO 1**:
- **P0 (4 bugs críticos)**: ✅ Integrado en AIS
- **P1 (27 bugs importantes)**: ✅ Integrado en AIS
- **P2 (26 bugs menores)**: ⏸️ En rama rescate, pendiente merge

---

### MANDATO 2: Gobernanza estratégica

| Rama | Estado | Commits | Target | Contenido |
|------|--------|---------|--------|-----------|
| (incluido en mandato1-p0-p1) | ✅ MERGED@6484be8 | 1 | AIS | GOVERNANCE_INSTITUCIONAL.md |

**Resumen MANDATO 2**:
- ✅ **Completado e integrado** en AIS@2be9a20
- Documento: `docs/GOVERNANCE_INSTITUCIONAL.md`
- Define reglas para estrategias, naming, testing, PRs

---

### MANDATO 3: Brain-layer governance

| Rama | Estado | Commits | Target | Contenido |
|------|--------|---------|--------|-----------|
| (no iniciado) | ⏸️ BLOQUEADO | 0 | - | Pendiente MANDATO 4 y 5 |

**Resumen MANDATO 3**:
- ⏸️ **NO iniciado** - Bloqueado por MANDATO 4 y 5
- Auditoría completa disponible en: `docs/AUDITORIA_MANDATOS_1_A_5_20251113.md`
- **Riesgos identificados**: 11 riesgos (4 P0 críticos)
- **P0s principales**:
  - P0-001: `ExecutionBrain` sin validaciones pre-trade
  - P0-002: `generate_decision_uid()` sin salt
  - P0-003: No se valida MTF confluence antes de trade
  - P0-004: Inconsistencias entre `DecisionLedger` y `ExecutionBrain`

**Dependencias**:
- MANDATO 4 (Risk Engine calibrado)
- MANDATO 5 (MicrostructureEngine implementado)

---

### MANDATO 4: Risk Engine calibrado

| Rama | Estado | Commits | Target | Contenido |
|------|--------|---------|--------|-----------|
| `mandato4-risk-manager-design` | ⚠️ DUDOSO | 2 | - | Solo docs de diseño |
| (implementación en mandato6) | ✅ IMPLEMENTADO | - | AIS | `src/core/risk_manager.py` |

**Resumen MANDATO 4**:
- ✅ **Diseño completo**: `docs/RISK_MANAGER_DESIGN.md` (rama mandato4)
- ✅ **Implementación**: MANDATO 6 Bloque 1
  - `src/core/risk_manager.py` (InstitutionalRiskManager)
  - `config/risk_limits.yaml` (límites institucionales)
  - QualityScorer, StatisticalCircuitBreaker, exposure limits
- ⏸️ **Calibración empírica**: Pendiente (requiere backtesting)
- **Riesgos identificados**: 12 riesgos (4 P0 críticos)

**Decisión pendiente**: Rescatar rama de diseño (solo histórico) vs marcar como obsoleto

---

### MANDATO 5: MicrostructureEngine + MultiFrameContext

| Rama | Estado | Commits | Target | Contenido |
|------|--------|---------|--------|-----------|
| `mandato5-microstructure-multiframe` | ⚠️ LEGACY | 7 | - | Sustituido por rescate |
| `mandato5-rescate-auditoria` | ⏸️ PENDIENTE_PR | 7 | AIS | Auditoría completa + diseño |

**Resumen MANDATO 5**:
- ✅ **Diseño completo**: 2200+ líneas en docs
  - `MICROSTRUCTURE_ENGINE_DESIGN.md`
  - `MULTIFRAME_CONTEXT_DESIGN.md`
- ❌ **Implementación**: 5% (VAPORWARE)
- ✅ **Auditoría completa**: Mandatos 1-5 (59 riesgos, 21 P0)
- ✅ **Roadmap**: 20-24 semanas de ejecución
- **Riesgos identificados**: 12 riesgos (5 P0 críticos)

**Estado**: Auditoría y diseño rescatados, pendiente merge a AIS

---

### MANDATO 6: Ejecución P0 (Testing + Observability + Risk Limits)

#### Bloque 1: Testing + Observability + Risk Limits

| Rama | Estado | Commits | Target | Contenido |
|------|--------|---------|--------|-----------|
| `mandato6-p0-testing-observability-risk` | ⏸️ PENDIENTE_PR | 1 | AIS | Tests + Logging + Limits |

**Contenido**:
- ✅ **Testing infrastructure**: `tests/core/`, `tests/risk/`, `tests/strategies/`
  - 15 tests P0 (idempotency, thread-safety, exposure limits)
  - `docs/TESTING_STRATEGY_MANDATO6.md`
- ✅ **Observability**: `src/core/logging_config.py`
  - InstitutionalLogger con event codes
  - `docs/OBSERVABILITY_RUNBOOK_MANDATO6.md`
- ✅ **Risk Limits**: `config/risk_limits.yaml`
  - Integración en `src/core/risk_manager.py`
  - Logging de rechazos por límites

**Commit**: b427a32
**Estado**: Pendiente PR manual (gh bloqueado)

#### Bloque 2: Rescate militar de PRs

| Rama | Estado | Commits | Target | Contenido |
|------|--------|---------|--------|-----------|
| `mandato6-rescate-inventario` | ⏸️ PENDIENTE_PR | 1 | AIS | Inventario histórico PRs |

**Contenido**:
- ✅ `docs/PR_HISTORICO_INVENTARIO_MANDATO6.md`
- Rescates ejecutados:
  - mandato1-rescate-P2 (21 bugs)
  - mandato5-rescate-auditoria (auditoría completa)

**Commit**: 4eaf965

---

### MANDATO 7: Limpieza total + organización estructural

| Rama | Estado | Commits | Target | Contenido |
|------|--------|---------|--------|-----------|
| (rama actual) | 🔄 EN_PROGRESO | - | AIS | Análisis + normalización |

**Contenido**:
- ✅ `docs/PR_CLOSED_ANALISIS_MANDATO7_20251114.md`
- 🔄 `docs/REPO_STATE_SNAPSHOT_20251114.md` (este archivo)
- ⏸️ `docs/MANDATOS_OVERVIEW_20251114.md` (pendiente)
- ⏸️ Creación de PRs formales hacia AIS

**Objetivo**: Normalización completa del repositorio hacia AIS como troncal única

---

## RAMAS REMOTAS (RESUMEN)

### Ramas activas (para PRs)

```
✅ MERGED:
  - origin/claude/mandato1-p0-p1-gobernanza-inicial (en AIS@6484be8)

⏸️ PENDIENTES PR hacia AIS:
  - origin/claude/mandato1-rescate-P2-20251114
  - origin/claude/mandato5-rescate-auditoria-20251114
  - origin/claude/mandato6-p0-testing-observability-risk-20251113
  - origin/claude/mandato6-rescate-inventario-20251114

❓ DUDOSO:
  - origin/claude/mandato4-risk-manager-design-20251113 (solo docs, ya implementado)
```

### Ramas legacy (no usar)

```
⚠️ OBSOLETAS (contenido sustituido por rescates):
  - origin/claude/mandato1-p2-minor-bugs-20251113
  - origin/claude/mandato5-microstructure-multiframe-20251113

⚠️ LEGACY GENERAL:
  - origin/claude/ALGORITMO-INSTITUCIONAL-SUBLIMINE-011CV4uXVN8w... (rama vieja)
  - origin/claude/audit-trading-system-repo-011CV4uYEyVY6qd3UdpyS6FH
  - origin/claude/conversation-capacity-limit-011CV4qmyvHoMEDK2xjiMMey
  - origin/claude/repo-context-summary-011CUyJb8kfhzpna9sWGrd5d (merged en main)
```

---

## PRs ABIERTOS

### Listos para merge hacia AIS

| PR | Rama | Mandato | Contenido | Prioridad |
|----|------|---------|-----------|-----------|
| (manual) | mandato6-p0-testing-observability | 6 | Tests + Logging + Limits | 🔴 ALTA |
| (pendiente) | mandato1-rescate-P2 | 1 | 21 bugs P2 | 🟡 MEDIA |
| (pendiente) | mandato5-rescate-auditoria | 1-5 | Auditoría completa | 🔴 ALTA |
| (pendiente) | mandato6-rescate-inventario | 6 | Inventario PRs | 🟢 BAJA |

**Nota**: PRs "pendientes" serán creados por Claude en MANDATO 7 (gh ahora permitido según reglas).

---

## ESTRUCTURA DE ARCHIVOS CLAVE

### Documentación institucional

```
docs/
├── GOVERNANCE_INSTITUCIONAL.md                    # ✅ En AIS (MANDATO 2)
├── AUDIT_P1_BUGS_20251113.md                      # ✅ En AIS (MANDATO 1)
├── AUDIT_P2_BUGS_20251113.md                      # ⏸️ En rescate-P2
├── AUDITORIA_MANDATOS_1_A_5_20251113.md           # ⏸️ En rescate-auditoria
├── ROADMAP_INSTITUCIONAL_20_24_SEMANAS.md         # ⏸️ En rescate-auditoria
├── MICROSTRUCTURE_ENGINE_DESIGN.md                # ⏸️ En rescate-auditoria
├── MULTIFRAME_CONTEXT_DESIGN.md                   # ⏸️ En rescate-auditoria
├── RISK_MANAGER_DESIGN.md                         # ❓ En mandato4-design (DUDOSO)
├── TESTING_STRATEGY_MANDATO6.md                   # ⏸️ En mandato6-bloque1
├── OBSERVABILITY_RUNBOOK_MANDATO6.md              # ⏸️ En mandato6-bloque1
├── PR_HISTORICO_INVENTARIO_MANDATO6.md            # ⏸️ En mandato6-inventario
├── PR_CLOSED_ANALISIS_MANDATO7_20251114.md        # 🔄 MANDATO 7 (este doc)
├── REPO_STATE_SNAPSHOT_20251114.md                # 🔄 MANDATO 7 (actual)
└── MANDATOS_OVERVIEW_20251114.md                  # ⏸️ MANDATO 7 (pendiente)
```

### Código institucional

```
src/
├── core/
│   ├── decision_ledger.py                         # ✅ En AIS
│   ├── conflict_arbiter.py                        # ✅ En AIS
│   ├── risk_manager.py                            # ✅ En AIS + ⏸️ mandato6-bloque1 (enhanced)
│   └── logging_config.py                          # ⏸️ En mandato6-bloque1 (NEW)
├── risk/
│   └── (varios módulos)                           # ✅ En AIS
└── strategies/
    └── (19 estrategias)                           # ✅ En AIS

config/
├── system_config.yaml                             # ✅ En AIS
├── strategies_institutional.yaml                  # ✅ En AIS
└── risk_limits.yaml                               # ⏸️ En mandato6-bloque1 (NEW)

tests/
├── core/
│   ├── test_decision_ledger.py                    # ⏸️ En mandato6-bloque1 (NEW)
│   ├── test_conflict_arbiter.py                   # ⏸️ En mandato6-bloque1 (NEW)
│   └── __init__.py
├── risk/
│   ├── test_risk_manager.py                       # ⏸️ En mandato6-bloque1 (NEW)
│   └── __init__.py
└── strategies/
    └── __init__.py
```

---

## REGLAS PERMANENTES (PARA TODAS LAS SESIONES)

### 1. Troncal única

```
✅ Base para TODO: ALGORITMO_INSTITUCIONAL_SUBLIMINE
❌ NUNCA usar: main (legacy)
```

### 2. Creación de PRs

```
✅ Target: SIEMPRE ALGORITMO_INSTITUCIONAL_SUBLIMINE
❌ NUNCA hacia: main, ramas aleatorias
✅ Formato rama: claude/mandatoX-<descripción>-YYYYMMDD-<session_id>
```

### 3. Documentación de PRs

Todo PR debe incluir en descripción:
- Mandato(s) que afecta
- Ramas/PRs que sustituye (si aplica)
- Confirmación de obsolescencia de PRs viejos

### 4. Mantenimiento de contexto

Actualizar en cada cambio significativo:
- `docs/REPO_STATE_SNAPSHOT_YYYYMMDD.md` (este archivo)
- `docs/MANDATOS_OVERVIEW_YYYYMMDD.md`
- `docs/PR_HISTORICO_INVENTARIO_MANDATOX.md` (si afecta PRs)

---

## PRÓXIMOS PASOS INMEDIATOS

| # | Acción | Responsable | Prioridad |
|---|--------|-------------|-----------|
| 1 | Crear `docs/MANDATOS_OVERVIEW_20251114.md` | Claude | 🔴 ALTA |
| 2 | Crear PRs formales para rescates → AIS | Claude | 🔴 ALTA |
| 3 | Revisar y aprobar mandato6-bloque1 PR | Humano | 🔴 ALTA |
| 4 | Revisar y aprobar mandato5-rescate PR | Humano | 🔴 ALTA |
| 5 | Revisar y aprobar mandato1-rescate-P2 PR | Humano | 🟡 MEDIA |
| 6 | Decidir sobre mandato4-design | Humano | 🟢 BAJA |
| 7 | Marcar main como deprecated en README | Claude | 🟡 MEDIA |
| 8 | Limpiar ramas legacy post-merge | Claude | 🟢 BAJA |

---

## INFORMACIÓN DE SESIÓN

```
Session ID: 011CV4uYEyVY6qd3UdpyS6FH
Fecha inicio: 2025-11-13
Mandatos ejecutados en sesión: 6 (Bloque 1-2), 7 (en progreso)
Commits creados: 20+
Ramas creadas: 4 (rescate-P2, rescate-auditoria, mandato6-bloque1, rescate-inventario)
PRs pendientes: 4
```

**Continuidad**: Este documento + `MANDATOS_OVERVIEW` + `PR_CLOSED_ANALISIS` son suficientes para reconstruir contexto completo en sesión nueva.

---

**Generado por**: MANDATO 7 - Limpieza total y organización estructural
**Próxima actualización**: Post-merge de PRs pendientes
