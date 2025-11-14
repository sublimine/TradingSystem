# INVENTARIO HISTÓRICO DE PRs - MANDATO 6 BLOQUE 2

**Fecha**: 2025-11-14
**Objetivo**: Rescate militar de PRs para normalización hacia `ALGORITMO_INSTITUCIONAL_SUBLIMINE`

---

## RESUMEN EJECUTIVO

| Categoría | Cantidad | Acción |
|-----------|----------|--------|
| RESCATAR | 2 | Crear ramas limpias desde ALGORITMO_INSTITUCIONAL_SUBLIMINE |
| DUDOSO | 1 | Evaluar con operador humano |
| OBSOLETO | 0 | - |
| YA INTEGRADO | 1 | Ya mergeado en 6484be8 |
| PENDIENTE PR | 1 | PR abierto, esperando aprobación |

---

## INVENTARIO DETALLADO

### ✅ YA INTEGRADO EN ALGORITMO_INSTITUCIONAL_SUBLIMINE

| ID | Rama | Estado | Mandato | Commits | Clasificación |
|----|------|--------|---------|---------|---------------|
| - | `claude/mandato1-p0-p1-gobernanza-inicial-011CV4uYEyVY6qd3UdpyS6FH` | MERGED | 1 | 6484be8 | YA_INTEGRADO |

**Contenido**:
- MANDATO 1 P0+P1 bugfixes (27 bugs críticos)
- Gobernanza institucional
- Thread-safety, NaN propagation, memory leaks
- Auditoría P1 completa

**Acción**: NINGUNA (ya está en troncal institucional)

---

### 🔥 RESCATAR - PRIORIDAD ALTA

#### RESCATE 1: Mandato 1 P2 Bugfixes

| Campo | Valor |
|-------|-------|
| **Rama original** | `claude/mandato1-p2-minor-bugs-20251113-011CV4uYEyVY6qd3UdpyS6FH` |
| **Mandatos** | 1 |
| **Commits** | 5 (79dd07e, afaf975, e6a0659, 7b24a95, 5deda72) |
| **Estado** | OPEN/NO_PR |
| **Clasificación** | **RESCATAR** |

**Contenido institucional**:
- 21 bugs P2 corregidos (P2-001 a P2-026)
- Documentación de thresholds hardcoded
- Alta prioridad: P2-024, P2-019, P2-022
- Auditoría P2 completa

**Razón para rescate**: Bugfixes institucionales válidos, menor prioridad que P0/P1 pero necesarios para estabilidad.

**Plan de rescate**:
```bash
git checkout ALGORITMO_INSTITUCIONAL_SUBLIMINE
git checkout -b claude/mandato1-rescate-P2-20251114-011CV4uYEyVY6qd3UdpyS6FH
git cherry-pick 5deda72^..79dd07e
```

---

#### RESCATE 2: Auditoría Completa Mandatos 1-5

| Campo | Valor |
|-------|-------|
| **Rama original** | `claude/mandato5-microstructure-multiframe-20251113-011CV4uYEyVY6qd3UdpyS6FH` |
| **Mandatos** | 1, 2, 3, 4, 5 |
| **Commits** | 7 (889cb62, c81a07e, a84b089, ce2fe3b, 8ea0c72, fb0cabf, d26bba6) |
| **Estado** | OPEN/NO_PR |
| **Clasificación** | **RESCATAR** |

**Contenido institucional**:
- Auditoría institucional completa Mandatos 1-5
- Roadmap 20-24 semanas (59 riesgos, 21 P0)
- Diseño completo MicrostructureEngine + MultiFrameContextEngine
- Documentación de arquitectura crítica

**Razón para rescate**: Documentación institucional crítica. Base para Mandatos futuros. 0 riesgo operativo (solo docs).

**Plan de rescate**:
```bash
git checkout ALGORITMO_INSTITUCIONAL_SUBLIMINE
git checkout -b claude/mandato5-rescate-auditoria-20251114-011CV4uYEyVY6qd3UdpyS6FH
git cherry-pick d26bba6^..889cb62
```

---

### ❓ DUDOSO - REQUIERE EVALUACIÓN HUMANA

#### DUDOSO 1: Diseño Risk Manager (Mandato 4)

| Campo | Valor |
|-------|-------|
| **Rama original** | `claude/mandato4-risk-manager-design-20251113-011CV4uYEyVY6qd3UdpyS6FH` |
| **Mandatos** | 4 |
| **Commits** | 2 (d02807a, 3123302) |
| **Estado** | OPEN/NO_PR |
| **Clasificación** | **DUDOSO** |

**Contenido**:
- Diseño completo Risk Manager institucional (solo docs)
- Normalización line endings PowerShell

**Razón para duda**:
- El diseño ya fue **implementado** en `src/core/risk_manager.py` (Mandato 6 Bloque 1)
- La documentación puede ser útil como referencia histórica
- Puede ser redundante con código ya implementado

**Recomendación**:
- **RESCATAR solo si** el operador humano quiere mantener docs de diseño separados del código
- **OBSOLETO si** el código auto-documentado es suficiente

**Plan condicional**:
```bash
# SI se decide rescatar:
git checkout ALGORITMO_INSTITUCIONAL_SUBLIMINE
git checkout -b claude/mandato4-rescate-design-20251114-011CV4uYEyVY6qd3UdpyS6FH
git cherry-pick 3123302
```

---

### ✅ PENDIENTE PR - NO RESCATAR

#### Mandato 6 Bloque 1 (Testing + Observability)

| Campo | Valor |
|-------|-------|
| **Rama** | `claude/mandato6-p0-testing-observability-risk-20251113-011CV4uYEyVY6qd3UdpyS6FH` |
| **Mandatos** | 6 |
| **Commits** | 1 (b427a32) |
| **Estado** | PENDING_PR |
| **Clasificación** | NO_RESCATAR |

**Razón**: PR pendiente de aprobación humana. No requiere rescate.

---

## PLAN DE EJECUCIÓN

### Fase 1: Rescates automáticos
1. ✅ Crear `claude/mandato1-rescate-P2-20251114-...` (21 bugfixes P2)
2. ✅ Crear `claude/mandato5-rescate-auditoria-20251114-...` (Auditoría completa)

### Fase 2: Evaluación humana
3. ⏸️ Esperar decisión sobre `mandato4-risk-manager-design` (DUDOSO)

### Fase 3: Limpieza
4. ⏸️ Marcar ramas antiguas como obsoletas (post-merge)

---

## NOTAS OPERATIVAS

- **Base común**: Todas las ramas rescatadas parten de `ALGORITMO_INSTITUCIONAL_SUBLIMINE@6484be8`
- **Conflictos esperados**: NINGUNO (solo documentación y bugfixes aislados)
- **Riesgo operativo**: CERO (0 cambios en código productivo sin review)
- **Merge strategy**: Cherry-pick individual para trazabilidad quirúrgica
