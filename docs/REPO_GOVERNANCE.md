# GOBERNANZA DEL REPOSITORIO - ALGORITMO INSTITUCIONAL SUBLIMINE

**Documento Normativo** | **Versión 1.0** | **Fecha: 2025-11-13**

---

## 1. PROPÓSITO Y ALCANCE

Este documento establece las reglas no negociables de gobernanza para el desarrollo del **ALGORITMO_INSTITUCIONAL_SUBLIMINE**. Todo contribuyente, humano o IA, debe cumplir estrictamente estas normas.

**Alcance**: Aplica a todo código institucional en fase de reconstrucción hasta alcanzar estado INSTITUTIONAL GRADE estable.

**Autoridad**: Establecido por mandato ejecutivo del operador humano (jefe de mesa cuantitativa).

---

## 2. RAMA TRONCAL INSTITUCIONAL ÚNICA

### 2.1 Definición

La **única rama troncal institucional** es:

```
ALGORITMO_INSTITUCIONAL_SUBLIMINE
```

### 2.2 Rol y Responsabilidades

- **Espacio de verdad único**: Todo código institucional evoluciona exclusivamente a través de esta rama
- **Destino obligatorio**: Toda integración de trabajo completado se hace hacia esta rama
- **Protegida**: NO se permiten commits directos (ver sección 4)
- **Baseline institucional**: Representa el estado actual del algoritmo institucional

### 2.3 Rama `main` - Estado Legacy

La rama `main` queda designada como **legacy/histórico**:

- ❌ **NO es destino** de integraciones durante la reconstrucción institucional
- ❌ **NO mezclar** código institucional nuevo con `main` sin pasar primero por `ALGORITMO_INSTITUCIONAL_SUBLIMINE`
- ℹ️ **Conservada** solo como referencia histórica hasta completar mandatos

---

## 3. POLÍTICA DE RAMAS DE TRABAJO

### 3.1 Prohibición de Trabajo Directo

**PROHIBIDO TERMINANTEMENTE**:
- Commits directos sobre `ALGORITMO_INSTITUCIONAL_SUBLIMINE`
- Cualquier operación que simule "merge directo" sin trazabilidad de PR

### 3.2 Creación de Ramas de Trabajo

**Requisitos obligatorios**:

1. **Siempre crear rama nueva** con prefijo claro
2. **Siempre basada** en `ALGORITMO_INSTITUCIONAL_SUBLIMINE` actualizado
3. **Nunca basada** en `main` o ramas obsoletas

### 3.3 Convención de Nombres

**Formato obligatorio para ramas de Claude**:
```
claude/<descripción-corta>
```

**Ejemplos correctos**:
- `claude/p0-bugfixes-core` - Correcciones P0 en componentes core
- `claude/p1-bugfixes-important` - Correcciones P1 importantes
- `claude/rewrite-correlation-divergence` - Reescritura estrategia correlation_divergence
- `claude/rewrite-johansen-real` - Implementación Johansen real
- `claude/repo-governance-doc` - Documentación de gobernanza
- `claude/improve-strategies-batch1` - Mejoras estrategias institucionales lote 1

**Otros prefijos permitidos** (para operador humano):
- `feature/<nombre>` - Nueva funcionalidad completa
- `hotfix/<descripción>` - Corrección urgente de producción
- `docs/<tema>` - Documentación pura

---

## 4. INTEGRACIÓN OBLIGATORIA VÍA PULL REQUEST

### 4.1 Flujo de Integración

**Proceso obligatorio para TODO código institucional**:

1. ✅ Completar bloque de trabajo coherente en rama dedicada
2. ✅ Abrir Pull Request con destino **EXCLUSIVO**: `ALGORITMO_INSTITUCIONAL_SUBLIMINE`
3. ✅ PR debe incluir descripción estructurada (ver 4.2)
4. ✅ Revisión y aprobación manual antes de merge
5. ✅ Merge con estrategia apropiada (squash para fixes pequeños, merge para features grandes)

### 4.2 Estructura Obligatoria de PR

Todo PR debe incluir como mínimo:

```markdown
## Rama Origen
`claude/nombre-de-rama`

## Resumen Estructurado

### Bugs Corregidos
- **CR1**: generate_decision_uid() no exist\u00eda → Implementado en DecisionLedger
- **CR2**: Iteración dict incorrecta → Corregida en decision_ledger.py
- **CR8**: Race conditions → Threading locks agregados en conflict_arbiter
...

### Ficheros Clave Modificados
**Core**:
- `src/core/decision_ledger.py` - Nuevo método generate_decision_uid()
- `src/core/conflict_arbiter.py` - Threading locks en intention_locks dict

**Strategies**:
- `src/strategies/liquidity_sweep.py` - Array bounds validation
- `src/strategies/momentum_quality.py` - Array bounds explícitos

**Gatekeepers**:
- `src/gatekeepers/spread_monitor.py` - Warm-up phase añadida
- `src/gatekeepers/kyles_lambda.py` - Warm-up phase añadida
- `src/gatekeepers/epin_estimator.py` - Warm-up phase añadida

### Riesgos Potenciales
- Cambios en API interna de DecisionLedger (backward compatible)
- Nuevos parámetros en gatekeepers (defaults configurados, no breaking)
- Warm-up phase puede reducir trades en primeros 50-100 ticks (ESPERADO e INSTITUCIONAL)

### Estado de Tests/Validaciones
- ✅ Módulos compilan sin errores
- ✅ Threading locks verificados con análisis de concurrencia
- ⏳ Tests unitarios pendientes (próximo PR)
- ⏳ Backtesting con warm-up phases pendiente

### Referencias a Auditorías
- INFORME_EJECUTIVO_MANDATO_1.md - Sección "Bugs Críticos P0"
- AUDIT_CORE_20251113.md - Race conditions en conflict_arbiter
- AUDIT_ESTRATEGIAS_20251113.md - Array bounds en strategies
```

### 4.3 Aprobación de PRs

**Proceso de aprobación**:
1. PR queda en estado "Ready for Review"
2. Revisión manual por operador humano o modelo asistente
3. Aprobación explícita requerida antes de merge
4. **NO autorizable automáticamente** - garantía de trazabilidad

---

## 5. PROHIBICIÓN DE MEZCLA SUCIA

### 5.1 Operaciones Prohibidas

❌ **PROHIBIDO TERMINANTEMENTE**:
- Duplicar repositorio sin plan de gobernanza explícito
- Crear forks operativos descontrolados
- Copias manuales de código entre ramas sin usar git
- Merge de ramas obsoletas o no basadas en troncal institucional

### 5.2 Espacio de Verdad Único

**Mantener UN SOLO espacio de verdad**:
```
ALGORITMO_INSTITUCIONAL_SUBLIMINE + árbol de ramas + PRs trazables
```

Cualquier copia, fork o duplicación debe tener:
- Justificación técnica explícita
- Plan de sincronización documentado
- Aprobación del operador humano

---

## 6. OPERACIONES FUTURAS (POST-MANDATOS)

Las siguientes operaciones solo se contemplan **después de completar mandatos intermedios** y alcanzar estado INSTITUTIONAL GRADE estable:

### 6.1 Promoción a Main (Futuro)

Opciones formales disponibles una vez completados mandatos:

1. **Tagging del estado final**:
   ```bash
   git tag -a v1.0.0-institucional -m "Estado INSTITUTIONAL GRADE alcanzado"
   ```

2. **Creación de repositorio limpio**:
   - Nuevo repo sin historial legacy
   - Solo código institucional certificado
   - Documentación completa de gobernanza

3. **Renombrado de ramas**:
   ```bash
   # main → legacy_main
   # ALGORITMO_INSTITUCIONAL_SUBLIMINE → main
   ```

### 6.2 Condiciones para Promoción

Solo se autoriza cuando:
- ✅ 97 bugs críticos corregidos (100%)
- ✅ 13+8+3 estrategias elevadas a INSTITUTIONAL GRADE
- ✅ 3 estrategias críticas reescritas (Johansen, correlation, IDP)
- ✅ Arbiter y decision_ledger endurecidos completamente
- ✅ Tests de regresión completos ejecutados
- ✅ Backtesting institucional validado
- ✅ Documentación técnica completa y auditada

---

## 7. COORDINACIÓN CON MANDATOS TÉCNICOS

### 7.1 Principio de Coherencia

Todos los mandatos técnicos deben ejecutarse bajo estas reglas de gobernanza:

| Mandato Técnico | Gobernanza Aplicable |
|----------------|---------------------|
| Corrección de 97 bugs | 1 rama dedicada por bloque coherente (P0, P1, P2) |
| Reescritura de estrategias | 1 rama por estrategia reescrita |
| Elevación a INSTITUTIONAL GRADE | 1 rama por lote de estrategias |
| Endurecimiento core | 1 rama para arbiter/decision_ledger |
| Tests y validación | 1 rama para test suite |

### 7.2 Prohibición de Mezclas sin Justificación

**NO mezclar en el mismo PR**:
- Reescrituras profundas + correcciones menores
- Múltiples estrategias no relacionadas
- Cambios arquitecturales + bug fixes superficiales

**Excepción**: Puede mezclarse si existe dependencia técnica explicada en descripción del PR.

---

## 8. MÉTRICAS DE CUMPLIMIENTO

### 8.1 Indicadores de Salud del Repositorio

**Métricas obligatorias a reportar**:
- ✅ % de PRs con descripción estructurada completa
- ✅ % de commits directos sobre troncal (debe ser 0%)
- ✅ % de ramas basadas correctamente en `ALGORITMO_INSTITUCIONAL_SUBLIMINE`
- ✅ Tiempo promedio de review de PRs
- ✅ Número de conflictos de merge por semana (objetivo: < 2)

### 8.2 Auditoría Semanal

**Cada semana se verifica**:
1. Ningún commit directo a `ALGORITMO_INSTITUCIONAL_SUBLIMINE` sin PR
2. Todas las ramas activas están basadas en troncal actualizada
3. PRs abiertos > 7 días tienen justificación o se cierran
4. Documentación de gobernanza está actualizada

---

## 9. VIOLACIONES Y CORRECCIONES

### 9.1 Violaciones Detectadas

Si se detecta violación de estas normas:

**Nivel 1 - Corrección Inmediata**:
- Commit directo a troncal sin PR → revert + crear PR correctamente
- Rama basada en `main` → rebase desde `ALGORITMO_INSTITUCIONAL_SUBLIMINE`
- PR sin descripción → agregar descripción estructurada antes de merge

**Nivel 2 - Revisión Arquitectural**:
- Múltiples violaciones recurrentes → auditoría de proceso
- Conflictos de merge frecuentes → revisar estrategia de branching
- PRs de > 1000 líneas sin justificación → refactorizar en PRs más pequeños

### 9.2 Proceso de Corrección

```bash
# Ejemplo: Corregir commit directo a troncal
git log ALGORITMO_INSTITUCIONAL_SUBLIMINE -5  # Identificar commit incorrecto
git revert <commit-hash>  # Revertir cambio
git checkout -b claude/fix-<descripción>  # Crear rama correcta
git cherry-pick <commit-hash>  # Aplicar cambio original
# Crear PR con descripción estructurada
```

---

## 10. CONTACTO Y ESCALACIÓN

### 10.1 Responsables

**Operador Humano**: Jefe de mesa cuantitativa
- Aprobación final de PRs críticos
- Decisiones arquitecturales mayores
- Excepciones a normas de gobernanza (debe documentarse)

**Modelo Asistente**: Claude (Sonnet 4.5)
- Cumplimiento estricto de normas
- Creación de PRs estructurados
- Reporte de métricas de salud
- Detección de violaciones

### 10.2 Escalación

**Situaciones que requieren escalación**:
- Conflicto de merge no trivial
- Decisión de arquitectura que afecta múltiples componentes
- Necesidad de operación prohibida con justificación excepcional
- Detección de bugs críticos en troncal institucional

**Proceso**: Crear issue en GitHub con label `escalation` y notificar operador humano.

---

## 11. APÉNDICE: COMANDOS ÚTILES

### 11.1 Crear Rama de Trabajo Correcta

```bash
# Actualizar troncal institucional
git fetch origin
git checkout ALGORITMO_INSTITUCIONAL_SUBLIMINE
git pull origin ALGORITMO_INSTITUCIONAL_SUBLIMINE

# Crear rama nueva desde troncal
git checkout -b claude/mi-trabajo-descriptivo

# Verificar base correcta
git log --oneline -1  # Debe mostrar último commit de troncal
```

### 11.2 Crear Pull Request (GitHub CLI)

```bash
# Desde tu rama de trabajo
gh pr create \
  --base ALGORITMO_INSTITUCIONAL_SUBLIMINE \
  --title "fix(core): CR1-CR10 - Correcciones P0 críticas" \
  --body-file PR_TEMPLATE.md
```

### 11.3 Verificar Salud del Repositorio

```bash
# Listar commits directos a troncal (debe ser vacío)
git log ALGORITMO_INSTITUCIONAL_SUBLIMINE --all --no-merges --since="1 week ago"

# Verificar ramas activas y sus bases
git branch -vv | grep claude/

# Identificar ramas obsoletas (sin commits en 30 días)
git for-each-ref --sort=-committerdate --format='%(refname:short) %(committerdate:relative)' refs/heads/
```

---

## 12. HISTORIAL DE CAMBIOS

| Versión | Fecha | Cambios | Autor |
|---------|-------|---------|-------|
| 1.0 | 2025-11-13 | Creación inicial - MANDATO 2.5 | Claude (Sonnet 4.5) |

---

## 13. FIRMA Y ACATAMIENTO

**Este documento es NORMATIVO, no opcional.**

Todo trabajo en `ALGORITMO_INSTITUCIONAL_SUBLIMINE` implica aceptación explícita de estas reglas.

**Vigencia**: Desde 2025-11-13 hasta completar mandatos intermedios y alcanzar estado INSTITUTIONAL GRADE.

---

**FIN DEL DOCUMENTO DE GOBERNANZA**
