# ANÁLISIS DE PRs CERRADOS - MANDATO 7

**Fecha**: 2025-11-14
**Objetivo**: Auditoría completa de PRs cerrados/mergeados para normalización hacia `ALGORITMO_INSTITUCIONAL_SUBLIMINE`

---

## RESUMEN EJECUTIVO

| Categoría | Cantidad |
|-----------|----------|
| PRs analizados | 8 |
| Mergeados en main | 1 |
| Mergeados en AIS | 0 (1 merge interno simulado) |
| Cerrados sin merge | 5 |
| Rescatados en Bloque 2 | 2 |
| Pendientes PR hacia AIS | 3 |
| Obsoletos confirmados | 0 |

**Conclusión crítica**:
- **main (d11e1cc) es LEGACY**. No tiene commits que AIS no tenga.
- **AIS (6484be8) tiene 17 commits que main NO tiene** (MANDATO 1, MANDATO 2, bugfixes).
- Todo contenido institucional está en AIS o en ramas rescatadas.

---

## ANÁLISIS DETALLADO POR PR

### PR #1: Normalize line endings across repository

| Campo | Valor |
|-------|-------|
| **Rama origen** | `claude/repo-context-summary-011CUyJb8kfhzpna9sWGrd5d` |
| **Base original** | `main` |
| **Estado** | MERGED (d11e1cc) |
| **Merge commit** | d11e1cc |
| **Contenido** | 109 bugs, overhaul institucional, deployment VPS, 19 estrategias |
| **En AIS** | ✅ SÍ (heredado, AIS parte desde d11e1cc) |
| **Decisión** | **YA_INTEGRADO** - Base común de main y AIS |

**Contenido del PR**:
- 7c95cd0: Scripts VPS (Linux + Windows)
- c382f1d: 109 bugs + PowerShell deployment
- ed70012: Sistema deployment automático
- da65200: Bugs críticos + memory leaks
- 4806d93: 65+ bugs arreglados
- 5f414df: MASSIVE 50+ bugs críticos
- 85275f2: CRITICAL feature integration bugs
- 0c0ff5e: Institutional overhaul batch 6-7 (estrategias 10-19)
- e8a764f-36992a8: Batches 1-5 (estrategias 1-9)

**Observación**: Este PR creó el baseline institucional. AIS divergió desde aquí.

---

### PR #2: fix(gatekeepers): CR13 - Agregar warm-up phase a ePINEstimator

| Campo | Valor |
|-------|-------|
| **Rama origen** | Desconocida (commit directo o rama eliminada) |
| **Base original** | Probablemente main o pre-AIS |
| **Estado** | Código presente en AIS@bae1b58 |
| **En AIS** | ✅ SÍ (commit bae1b58 en AIS) |
| **Decisión** | **YA_INTEGRADO** |

**Contenido**:
- bae1b58: CR13 - Warm-up phase ePINEstimator
- e3e7e32: CR12 - Warm-up phase KylesLambdaEstimator
- a2d3f3a: CR11 - Warm-up phase SpreadMonitor

**Observación**: Estos commits están en AIS como parte del MANDATO 1.

---

### PR #3: Claude/mandato1 p0 p1 gobernanza inicial

| Campo | Valor |
|-------|-------|
| **Rama origen** | `claude/mandato1-p0-p1-gobernanza-inicial-011CV4uYEyVY6qd3UdpyS6FH` |
| **Base original** | `ALGORITMO_INSTITUCIONAL_SUBLIMINE` (o pre-AIS) |
| **Estado** | MERGED (simulado) en AIS@6484be8 |
| **En AIS** | ✅ SÍ (merge commit 6484be8) |
| **Decisión** | **YA_INTEGRADO** |

**Contenido**:
- d71f196: BLOQUES 4-6 (thread-safety, NaN, memory leaks)
- 8233190: BLOQUES 1-3 (validaciones numéricas)
- 319be90: .gitattributes LF
- f335970: Auditoría P1 (27 bugs)
- 2be9a20: Gobernanza (MANDATO 2.5)
- Commits CR1-CR13: Bugfixes críticos

**Observación**: Este es el merge HEAD de AIS actualmente.

---

### PR #4: Claude/mandato4 risk manager design

| Campo | Valor |
|-------|-------|
| **Rama origen** | `claude/mandato4-risk-manager-design-20251113-011CV4uYEyVY6qd3UdpyS6FH` |
| **Base original** | `ALGORITMO_INSTITUCIONAL_SUBLIMINE` |
| **Estado** | CERRADO sin merge |
| **En AIS** | ❌ NO (solo docs de diseño) |
| **Código implementado** | ✅ SÍ en `src/core/risk_manager.py` (MANDATO 6) |
| **Decisión** | **DUDOSO** → Recomendación: **OBSOLETO** |

**Contenido**:
- 3123302: Diseño completo Risk Manager (solo docs)
- d02807a: Normalización line endings PowerShell

**Razón para OBSOLETO**:
- El diseño ya fue **implementado** en MANDATO 6 Bloque 1
- `config/risk_limits.yaml` contiene los límites institucionales
- `src/core/risk_manager.py` tiene la implementación completa
- Documentos de diseño pueden ser redundantes con código auto-documentado

**Si se rescata**: Solo por valor histórico, NO por contenido operativo.

---

### PR #5: Claude/mandato5 microstructure multiframe

| Campo | Valor |
|-------|-------|
| **Rama origen** | `claude/mandato5-microstructure-multiframe-20251113-011CV4uYEyVY6qd3UdpyS6FH` |
| **Base original** | `ALGORITMO_INSTITUCIONAL_SUBLIMINE` |
| **Estado** | CERRADO sin merge |
| **En AIS** | ❌ NO |
| **Rescatado** | ✅ SÍ en `claude/mandato5-rescate-auditoria-20251114-...` |
| **Decisión** | **RESCATADO** (Bloque 2) |

**Contenido**:
- 889cb62: Roadmap completo 20-24 semanas (59 riesgos, 21 P0)
- c81a07e: MANDATO 5 VAPORWARE (2200+ líneas diseño)
- a84b089: MANDATO 4 audit (12 riesgos, 4 P0)
- ce2fe3b: MANDATO 3 audit (11 riesgos, 4 P0)
- 8ea0c72: MANDATO 2 audit (12 riesgos, 4 P0)
- fb0cabf: MANDATO 1 audit (12 riesgos, 4 P0)
- d26bba6: Diseño MicrostructureEngine + MultiFrameContextEngine

**Estado del rescate**:
- ✅ Cherry-picked a `claude/mandato5-rescate-auditoria-20251114-011CV4uYEyVY6qd3UdpyS6FH`
- ✅ Pusheado a remote
- ⏸️ Pendiente PR hacia AIS

---

### PR #6: (No existe - salto en numeración)

**Observación**: GitHub saltó del #5 al #7 en la numeración.

---

### PR #7: "m"

| Campo | Valor |
|-------|-------|
| **Rama origen** | Desconocida |
| **Base original** | Desconocido |
| **Estado** | CERRADO sin merge (título basura) |
| **En AIS** | ❓ Desconocido (sin info) |
| **Decisión** | **IGNORAR** - PR basura |

**Observación**: PR con título "m" es claramente un error humano. Sin información útil. Ignorar completamente.

---

### PR #8: Claude/mandato1 p2 minor bugs

| Campo | Valor |
|-------|-------|
| **Rama origen** | `claude/mandato1-p2-minor-bugs-20251113-011CV4uYEyVY6qd3UdpyS6FH` |
| **Base original** | `ALGORITMO_INSTITUCIONAL_SUBLIMINE` |
| **Estado** | CERRADO sin merge |
| **En AIS** | ❌ NO |
| **Rescatado** | ✅ SÍ en `claude/mandato1-rescate-P2-20251114-...` |
| **Decisión** | **RESCATADO** (Bloque 2) |

**Contenido**:
- 79dd07e: P2-005 a P2-026 (21 bugs)
- afaf975: P2-003 (documentar min_quality_score)
- e6a0659: P2-001, P2-002, P2-004 (thresholds brain.py)
- 7b24a95: ALTA PRIORIDAD (P2-024, P2-019, P2-022)
- 5deda72: Auditoría P2 (26 bugs menores)

**Estado del rescate**:
- ✅ Cherry-picked a `claude/mandato1-rescate-P2-20251114-011CV4uYEyVY6qd3UdpyS6FH`
- ✅ Pusheado a remote
- ⏸️ Pendiente PR hacia AIS

---

## RAMAS ADICIONALES (NO PRs CERRADOS, PERO RELEVANTES)

### Mandato 6 Bloque 1: Testing + Observability

| Campo | Valor |
|-------|-------|
| **Rama** | `claude/mandato6-p0-testing-observability-risk-20251113-011CV4uYEyVY6qd3UdpyS6FH` |
| **Base** | `ALGORITMO_INSTITUCIONAL_SUBLIMINE` |
| **Estado** | PENDIENTE PR (creado manualmente por operador) |
| **En AIS** | ❌ NO |
| **Decisión** | **PENDIENTE_APROBACION** |

**Contenido**:
- b427a32: Tests críticos + logging + risk limits
- 15 tests P0 (idempotency, thread-safety, exposure limits)
- `config/risk_limits.yaml`
- `src/core/logging_config.py`
- Docs: TESTING_STRATEGY, OBSERVABILITY_RUNBOOK

---

### Mandato 6 Bloque 2: Inventario

| Campo | Valor |
|-------|-------|
| **Rama** | `claude/mandato6-rescate-inventario-20251114-011CV4uYEyVY6qd3UdpyS6FH` |
| **Base** | `ALGORITMO_INSTITUCIONAL_SUBLIMINE` |
| **Estado** | PENDIENTE PR |
| **En AIS** | ❌ NO |
| **Decisión** | **PENDIENTE_APROBACION** |

**Contenido**:
- 4eaf965: Inventario histórico PRs (docs/PR_HISTORICO_INVENTARIO_MANDATO6.md)

---

## CONCLUSIONES Y RECOMENDACIONES

### Estado actual del repositorio

1. **Troncal institucional**: `ALGORITMO_INSTITUCIONAL_SUBLIMINE@6484be8`
   - Contiene: baseline institucional + MANDATO 1 (P0+P1) + MANDATO 2
   - **17 commits adelante de main**

2. **main@d11e1cc**: **LEGACY OBSOLETO**
   - No aporta contenido que AIS no tenga
   - No debe usarse como base para nada nuevo

3. **PRs rescatados** (Bloque 2):
   - mandato1-rescate-P2 (21 bugs P2)
   - mandato5-rescate-auditoria (auditoría completa Mandatos 1-5)

4. **PRs pendientes**:
   - mandato6-p0-testing-observability (Bloque 1)
   - mandato6-rescate-inventario (docs)

### Acciones requeridas

| Acción | Prioridad | Responsable |
|--------|-----------|-------------|
| Aprobar/mergear mandato1-rescate-P2 → AIS | MEDIA | Operador humano |
| Aprobar/mergear mandato5-rescate-auditoria → AIS | ALTA | Operador humano |
| Aprobar/mergear mandato6-p0-testing-observability → AIS | ALTA | Operador humano |
| Aprobar/mergear mandato6-rescate-inventario → AIS | BAJA | Operador humano |
| Decidir sobre mandato4-risk-manager-design | BAJA | Operador humano |
| Marcar main como deprecated/legacy | ALTA | Claude (docs) |
| Crear PRs formales para rescates | INMEDIATA | Claude (MANDATO 7) |

### Ramas a eliminar (post-merge)

Después de mergear los rescates a AIS:
- `claude/mandato1-p2-minor-bugs-20251113-...` (contenido en rescate-P2)
- `claude/mandato5-microstructure-multiframe-20251113-...` (contenido en rescate-auditoria)
- `claude/mandato4-risk-manager-design-20251113-...` (obsoleto por implementación)
- `origin/claude/repo-context-summary-...` (mergeado en main legacy)
- Otras ramas claude/conversation-*, claude/audit-* (legacy)

---

## VERIFICACIÓN TÉCNICA

### Divergencia main vs AIS

```bash
# Commits en AIS que NO están en main
$ git log main..ALGORITMO_INSTITUCIONAL_SUBLIMINE --oneline | wc -l
17

# Commits en main que NO están en AIS
$ git log ALGORITMO_INSTITUCIONAL_SUBLIMINE..main --oneline | wc -l
0
```

**Conclusión**: AIS es un superconjunto estricto de main. main no aporta nada nuevo.

### Merge base común

```bash
$ git merge-base main ALGORITMO_INSTITUCIONAL_SUBLIMINE
d11e1ccba60229fd5dfdd1a71ea46f42ac49a017
```

**Interpretación**: Ambas ramas divergen desde d11e1cc (merge de PR #1). AIS continuó evolucionando, main se detuvo.

---

**Documento generado**: MANDATO 7 - Análisis institucional de PRs
**Próximo paso**: Crear PRs formales hacia AIS para todos los rescates
