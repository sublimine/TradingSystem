# AUDITORÍA INSTITUCIONAL – MANDATOS 1 A 5

**Proyecto**: SUBLIMINE TradingSystem
**Fecha**: 2025-11-13
**Auditor**: Sistema de Revisión Institucional
**Estándar**: Model Risk + Market Risk + Internal Audit

**Advertencia**: Esta auditoría identifica debilidades críticas que podrían causar pérdidas, degradación operativa o rechazo en revisión institucional. Ninguna concesión. Solo hechos y acciones.

---

## MANDATO 1 – AUDITORÍA INSTITUCIONAL

**Alcance**: Infraestructura, corrección de 97 bugs (P0+P1+P2), scripts de integración, entorno VPS.

**Estado actual**: COMPLETADO (correcciones), pero con **deficiencias institucionales graves** en gobernanza técnica.

---

### RIESGOS / DEBILIDADES DETECTADAS

#### **P0 (CRÍTICO) – Riesgos que pueden romper el sistema o causar pérdidas materiales**

**P0-001: Ausencia de estrategia formal de testing**

**Descripción**:
- 97 bugs corregidos sin evidencia de test suite que valide las correcciones.
- NO hay documentación de:
  - Tests unitarios (unit tests).
  - Tests de integración (integration tests).
  - Tests de regresión (regression tests).
- Riesgo: **Las correcciones de P0/P1/P2 pueden haber introducido nuevos bugs** (regresiones) que no se detectan hasta producción.

**Evidencia**:
- Archivos corregidos: `src/core/brain.py`, `src/core/risk_manager.py`, `src/core/position_manager.py`, `src/strategies/*.py`, `src/features/*.py`.
- NO existe carpeta `tests/` con cobertura sistemática.
- NO hay CI/CD pipeline que ejecute tests automáticamente en cada commit.

**Impacto**:
- **Muy alto**: Bug no detectado en `risk_manager.py` (ej: división por cero en cálculo de posición) puede causar:
  - Órdenes con tamaño incorrecto (sobre-apalancamiento).
  - Crash del sistema en vivo.
  - Pérdida material si se ejecutan trades con riesgo mal calculado.

**Severidad**: **P0 – CRÍTICO**

---

**P0-002: Falta de observabilidad institucional (logs, métricas, alertas)**

**Descripción**:
- NO existe framework estructurado de logging.
- NO hay métricas de salud del sistema (health checks).
- NO hay alertas automáticas ante eventos críticos:
  - Pérdida diaria > X%.
  - Latencia de ejecución > Y ms.
  - Número de rechazos de señal anómalo.
  - Caída de conexión a broker/MT5.

**Evidencia**:
- Archivos actuales usan `logger.warning()`, `logger.info()` de forma inconsistente.
- NO hay documento `OBSERVABILITY_RUNBOOK.md`.
- NO hay dashboard de métricas en tiempo real.
- Scripts PowerShell (`monitor.ps1`, `start_trading.ps1`) NO tienen telemetría estructurada.

**Impacto**:
- **Muy alto**:
  - Sin logs estructurados, **imposible hacer post-mortem** de un fallo en producción.
  - Sin alertas, el sistema puede estar perdiendo dinero durante horas sin que nadie lo sepa.
  - Auditoría interna rechazaría sistema sin observabilidad mínima.

**Severidad**: **P0 – CRÍTICO**

---

**P0-003: Riesgos de concurrency introducidos en correcciones P1**

**Descripción**:
- Correcciones P1-012 y P1-013 añadieron `threading.Lock()` en `decision_ledger.py` y `conflict_arbiter.py`.
- NO hay evidencia de:
  - Análisis de deadlock potential.
  - Tests de carga concurrente (stress tests).
  - Documentación de orden de adquisición de locks.

**Evidencia**:
```python
# decision_ledger.py:12
self.lock = threading.Lock()

# conflict_arbiter.py
# (lock añadido pero sin documentación de threading model)
```

**Impacto**:
- **Muy alto**:
  - Deadlock en producción → sistema congelado.
  - Múltiples estrategias generando señales simultáneas pueden causar contention excesiva.
  - Latencia impredecible en arbitraje de conflictos.

**Escenario concreto**:
```
Thread 1: Adquiere lock en decision_ledger → espera lock en conflict_arbiter
Thread 2: Adquiere lock en conflict_arbiter → espera lock en decision_ledger
→ DEADLOCK
```

**Severidad**: **P0 – CRÍTICO**

---

**P0-004: Validaciones introducidas en P2 pueden bloquear sistema en condiciones edge**

**Descripción**:
- Correcciones P2 añadieron validaciones estrictas:
  - P2-020: `abs(denominator) < 1e-6` en lugar de `== 0`.
  - P2-023: `if sig is None: raise ValueError()`.
  - P2-024: `if total_capital < 0: raise ValueError()`.
- Validaciones correctas **PERO**:
  - NO hay manejo de excepciones en nivel superior.
  - NO hay fallback/degraded mode si validación falla.

**Evidencia**:
```python
# portfolio_manager.py
if sig is None:
    raise ValueError("Invalid signal (None) in executions")
# ¿Qué pasa si esto se lanza en producción? ¿Crash total o log + skip?
```

**Impacto**:
- **Alto**: Una señal `None` por bug upstream causa:
  - Crash de `portfolio_manager`.
  - Stop completo del sistema.
  - NO hay circuit breaker que capture excepción y continúe operando con otras señales.

**Severidad**: **P0 – CRÍTICO**

---

#### **P1 (IMPORTANTE) – Degrada calidad institucional, no mata el sistema inmediatamente**

**P1-001: Ausencia de política de versionado y tagging institucional**

**Descripción**:
- Commits tienen mensajes descriptivos (correcto).
- NO hay:
  - Tags semánticos (v1.0.0, v1.1.0, etc.).
  - Releases formales.
  - CHANGELOG estructurado.
  - Convención de versiones (semantic versioning).

**Evidencia**:
- Historial de commits: `d26bba6`, `6484be8`, `d71f196` (SHAs, no tags).
- NO existe `CHANGELOG.md`.

**Impacto**:
- **Medio**:
  - Imposible rastrear qué versión exacta está en producción.
  - Rollback complicado sin tags claros.
  - Auditoría interna requiere versionado formal.

**Severidad**: **P1 – IMPORTANTE**

---

**P1-002: Scripts PowerShell sin validación ni error handling robusto**

**Descripción**:
- Scripts `INTEGRATE_VPS.ps1`, `monitor.ps1`, `start_trading.ps1`, `sync.ps1`:
  - Normalizados (line endings LF).
  - PERO: NO hay evidencia de:
    - Manejo de errores (try/catch).
    - Validación de precondiciones (ej: VPS alcanzable antes de sync).
    - Logs estructurados de ejecución.

**Evidencia**:
- Archivos `.ps1` presentes en repo.
- Commit `chore: Normalizar line endings en archivos PowerShell`.
- NO hay `docs/SCRIPTS_USAGE.md` con runbook.

**Impacto**:
- **Medio**:
  - Script falla silenciosamente → datos no sincronizados → decisiones con datos stale.
  - Dificulta troubleshooting en entorno VPS.

**Severidad**: **P1 – IMPORTANTE**

---

**P1-003: Falta de runbooks operacionales**

**Descripción**:
- NO existe documentación de:
  - Cómo arrancar el sistema en producción.
  - Cómo hacer rollback ante fallo.
  - Cómo diagnosticar latencia elevada.
  - Cómo responder a pérdida > X% diaria.

**Evidencia**:
- Único documento operacional: `docs/REPO_GOVERNANCE.md` (branching/PR, NO operaciones).
- Falta: `OPERATIONAL_RUNBOOK.md`, `INCIDENT_RESPONSE.md`.

**Impacto**:
- **Medio**:
  - Ante incidente, respuesta lenta por falta de procedimientos documentados.
  - Onboarding de nuevo operador/dev lleva mucho tiempo.

**Severidad**: **P1 – IMPORTANTE**

---

**P1-004: Ausencia de análisis de cobertura de correcciones P0/P1/P2**

**Descripción**:
- 97 bugs corregidos:
  - 12 P0 (críticos).
  - 27 P1 (importantes).
  - 26 P2 (menores).
- NO hay métricas de:
  - Qué % de código fue tocado.
  - Qué áreas tienen mayor densidad de bugs (hotspots).
  - Qué estrategias/módulos son más frágiles.

**Evidencia**:
- Auditorías `AUDIT_P2_BUGS_20251113.md` existen (correcto).
- PERO: NO hay análisis estadístico tipo:
  - "5 bugs en `order_flow.py` → módulo de alto riesgo".
  - "Estrategia `liquidity_sweep` tiene 3 bugs → revisar diseño completo".

**Impacto**:
- **Medio**:
  - NO se priorizan módulos para refactoring profundo.
  - Riesgo de seguir corrigiendo síntomas en lugar de causas raíz.

**Severidad**: **P1 – IMPORTANTE**

---

**P1-005: Falta de integración continua (CI/CD)**

**Descripción**:
- NO hay pipeline CI/CD que:
  - Ejecute tests automáticamente en cada push.
  - Valide linting/formatting.
  - Genere builds de artefactos.
  - Despliegue a entorno staging antes de producción.

**Evidencia**:
- NO existe `.github/workflows/ci.yml` o similar.
- NO hay integración con GitHub Actions, GitLab CI, Jenkins, etc.

**Impacto**:
- **Medio**:
  - Bugs llegan a producción que podrían haberse detectado en CI.
  - Despliegues manuales son lentos y propensos a error humano.

**Severidad**: **P1 – IMPORTANTE**

---

#### **P2 (MENOR) – Calidad de código, naming, documentación**

**P2-001: Inconsistencia en nomenclatura de archivos y funciones**

**Descripción**:
- Mix de estilos:
  - `snake_case` en algunos archivos.
  - `camelCase` en otros.
  - Nombres poco descriptivos (ej: `calculate_score()` sin contexto de qué score).

**Evidencia**:
- `src/features/technical_indicators.py`: función `detect_divergence()` (stub).
- `src/core/brain.py`: función `arbitrate()` sin docstring completo.

**Impacto**:
- **Bajo**: Dificulta lectura de código, pero NO causa fallos.

**Severidad**: **P2 – MENOR**

---

**P2-002: Falta de docstrings completos en funciones críticas**

**Descripción**:
- Muchas funciones carecen de:
  - Descripción completa de parámetros.
  - Tipos de retorno.
  - Excepciones lanzadas.

**Evidencia**:
- Correcciones P2 añadieron comentarios, pero NO docstrings formales tipo:
```python
def calculate_quality_score(signal: Signal) -> float:
    """
    Calcula quality score de señal.

    Args:
        signal: Señal de estrategia con entry, direction, etc.

    Returns:
        Score [0.0, 1.0]

    Raises:
        ValueError: Si signal.entry_price <= 0
    """
```

**Impacto**:
- **Bajo**: Dificulta mantenimiento, NO causa fallos directos.

**Severidad**: **P2 – MENOR**

---

**P2-003: Thresholds hardcodeados sin configuración centralizada**

**Descripción**:
- Thresholds documentados en código (correcto tras P2), pero:
  - NO hay archivo de configuración centralizado tipo `config/thresholds.yaml`.
  - Cambiar threshold requiere editar código Python.

**Evidencia**:
- `src/core/brain.py`: `min_arbitration_score = 0.65` hardcodeado.
- `src/features/order_flow.py`: `vpin_threshold = 0.50` hardcodeado.

**Impacto**:
- **Bajo**: Cambiar thresholds es lento, pero NO rompe sistema.

**Severidad**: **P2 – MENOR**

---

### RESUMEN DE RIESGOS MANDATO 1

| Severidad | Cantidad | Críticos destacados |
|-----------|----------|---------------------|
| **P0 (CRÍTICO)** | 4 | Testing ausente, Observabilidad nula, Deadlocks potenciales, Validaciones sin fallback |
| **P1 (IMPORTANTE)** | 5 | Versionado, Scripts sin error handling, Runbooks ausentes, Sin CI/CD |
| **P2 (MENOR)** | 3 | Naming inconsistente, Docstrings incompletos, Thresholds hardcodeados |
| **TOTAL** | **12** | **4 P0 requieren acción inmediata** |

---

### MEJORAS INSTITUCIONALES RECOMENDADAS

#### **Acción M1-001: Crear estrategia formal de testing**

**Qué hacer**:
1. Crear documento `docs/TESTING_STRATEGY.md` con:
   - Matriz de cobertura mínima:
     - Core: 80% coverage.
     - Strategies: 70% coverage.
     - Features: 60% coverage.
   - Tipos de tests:
     - Unit tests: funciones individuales.
     - Integration tests: flujo completo (señal → QualityScorer → RiskAllocator → orden).
     - Regression tests: validar que bugs corregidos NO reaparecen.
   - Framework: `pytest` + `pytest-cov`.

2. Crear estructura `tests/`:
```
tests/
  unit/
    test_brain.py
    test_risk_manager.py
    test_position_manager.py
  integration/
    test_signal_to_execution_flow.py
  regression/
    test_p0_bugs_fixed.py
    test_p1_bugs_fixed.py
```

3. Implementar tests críticos PRIMERO:
   - Test de división por cero en `risk_manager.py`.
   - Test de concurrency en `decision_ledger.py` (simular 10 threads).
   - Test de validación de señal `None` en `portfolio_manager.py`.

**Impacto**: **Muy alto** – Previene regresiones, detecta bugs antes de producción.

**Prioridad**: **P0 – INMEDIATA**

---

#### **Acción M1-002: Implementar observabilidad institucional**

**Qué hacer**:
1. Crear documento `docs/OBSERVABILITY_RUNBOOK.md` con:
   - Políticas de logging:
     - Niveles: DEBUG, INFO, WARNING, ERROR, CRITICAL.
     - Formato estructurado: JSON logs con campos:
       - `timestamp`, `level`, `module`, `event`, `data`.
   - Métricas a capturar (mínimo):
     - Latencia de ejecución de señal (p50, p95, p99).
     - Número de señales generadas/rechazadas por minuto.
     - Drawdown actual vs límite.
     - Uptime del sistema.
   - Alertas obligatorias:
     - Pérdida diaria > 5%.
     - Latencia > 100ms en decisión crítica.
     - Conexión a broker caída.
     - Sistema sin señales durante > 1 hora (posible freeze).

2. Implementar logging estructurado:
```python
import structlog

logger = structlog.get_logger()

logger.info(
    "signal_generated",
    strategy="momentum_quality",
    symbol="EURUSD",
    direction="LONG",
    quality_score=0.87
)
```

3. Integrar stack de observabilidad:
   - Logs: `structlog` → archivo JSON.
   - Métricas: `prometheus_client` → Prometheus → Grafana.
   - Alertas: Prometheus Alertmanager → Email/Telegram.

4. Dashboard mínimo en Grafana:
   - Panel 1: PnL acumulado.
   - Panel 2: Número de trades ejecutados vs rechazados.
   - Panel 3: Latencia p95 de decisión.
   - Panel 4: Quality score distribution.

**Impacto**: **Muy alto** – Permite detectar problemas en tiempo real, hacer post-mortems, pasar auditorías.

**Prioridad**: **P0 – INMEDIATA**

---

#### **Acción M1-003: Análisis y mitigación de riesgos de concurrency**

**Qué hacer**:
1. Documentar threading model en `docs/CONCURRENCY_MODEL.md`:
   - Qué componentes usan locks.
   - Orden de adquisición de locks (para evitar deadlocks).
   - Timeout en adquisición de locks.

2. Regla estricta de orden de locks:
```python
# SIEMPRE adquirir locks en este orden:
# 1. decision_ledger.lock
# 2. conflict_arbiter.lock
# 3. portfolio_manager.lock
# NUNCA al revés.
```

3. Añadir timeouts:
```python
if not self.lock.acquire(timeout=1.0):
    logger.error("lock_timeout", component="decision_ledger")
    raise TimeoutError("No se pudo adquirir lock en 1s")
```

4. Implementar tests de stress concurrente:
```python
def test_concurrent_signal_processing():
    threads = []
    for i in range(50):
        t = threading.Thread(target=process_signal, args=(signal_i,))
        threads.append(t)
        t.start()

    for t in threads:
        t.join(timeout=5.0)

    assert no_deadlock_occurred()
```

**Impacto**: **Muy alto** – Previene deadlocks en producción.

**Prioridad**: **P0 – INMEDIATA**

---

#### **Acción M1-004: Añadir fallback/degraded mode en validaciones**

**Qué hacer**:
1. Envolver validaciones críticas con manejo de excepciones:
```python
# portfolio_manager.py
try:
    if sig is None:
        raise ValueError("Invalid signal (None)")
except ValueError as e:
    logger.error("validation_failed", error=str(e), signal_id=sig_id)
    # NO crash: registrar error y continuar con siguiente señal
    continue
```

2. Implementar circuit breaker:
```python
if error_count_last_minute > 10:
    logger.critical("circuit_breaker_triggered")
    # Pausa procesamiento de señales durante 1 minuto
    time.sleep(60)
```

3. Definir modos operacionales:
   - **NORMAL**: Todas las validaciones activas.
   - **DEGRADED**: Validaciones relajadas, logs agresivos.
   - **EMERGENCY_STOP**: No se procesan señales nuevas.

**Impacto**: **Alto** – Sistema más robusto ante condiciones edge.

**Prioridad**: **P0 – INMEDIATA**

---

#### **Acción M1-005: Implementar versionado semántico y tagging**

**Qué hacer**:
1. Crear `VERSIONING_POLICY.md`:
   - Usar Semantic Versioning (semver): `MAJOR.MINOR.PATCH`.
   - Ejemplos:
     - `v1.0.0`: Release inicial post-corrección 97 bugs.
     - `v1.1.0`: Añadir Risk Engine implementado.
     - `v1.1.1`: Bugfix menor en VPIN calculation.

2. Crear tags en git:
```bash
git tag -a v1.0.0 -m "Release 1.0.0: 97 bugs corregidos, base institucional"
git push origin v1.0.0
```

3. Mantener `CHANGELOG.md`:
```markdown
# Changelog

## [1.0.0] - 2025-11-13
### Fixed
- P0-001: División por cero en risk_manager.py
- P1-011: Race condition en decision_ledger.py
...

### Added
- Thresholds documentados en brain.py, order_flow.py
```

**Impacto**: **Medio** – Mejora trazabilidad, facilita rollbacks.

**Prioridad**: **P1 – ALTA**

---

#### **Acción M1-006: Crear runbooks operacionales**

**Qué hacer**:
1. Crear `docs/OPERATIONAL_RUNBOOK.md` con secciones:
   - **Startup**: Cómo arrancar sistema en producción.
   - **Shutdown**: Cómo detener sistema sin pérdida de datos.
   - **Rollback**: Cómo volver a versión anterior.
   - **Troubleshooting común**:
     - Latencia alta → revisar logs de microestructura.
     - Señales rechazadas en masa → verificar Quality Score thresholds.
     - Conexión MT5 caída → reiniciar connector.

2. Crear `docs/INCIDENT_RESPONSE.md`:
   - Niveles de severidad de incidentes:
     - **SEV1 (CRÍTICO)**: Pérdida > 10% diaria, sistema caído.
     - **SEV2 (ALTO)**: Pérdida > 5%, latencia > 500ms.
     - **SEV3 (MEDIO)**: Comportamiento anómalo sin pérdida material.
   - Procedimientos:
     - SEV1 → EMERGENCY_STOP inmediato + análisis post-mortem.
     - SEV2 → Investigación en caliente, posible degraded mode.
     - SEV3 → Log + revisión diferida.

**Impacto**: **Medio** – Reduce tiempo de respuesta ante incidentes.

**Prioridad**: **P1 – ALTA**

---

#### **Acción M1-007: Validar y endurecer scripts PowerShell**

**Qué hacer**:
1. Añadir error handling a todos los scripts `.ps1`:
```powershell
# INTEGRATE_VPS.ps1
try {
    # ... lógica de sync ...
} catch {
    Write-Error "Sync failed: $_"
    Exit 1
}
```

2. Validaciones previas:
```powershell
# Verificar que VPS es alcanzable
if (-not (Test-Connection -ComputerName $VPS_IP -Count 1 -Quiet)) {
    Write-Error "VPS not reachable"
    Exit 1
}
```

3. Logging estructurado:
```powershell
function Log-Info($message) {
    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    Write-Output "$timestamp [INFO] $message" | Out-File -Append sync.log
}
```

4. Crear `docs/SCRIPTS_USAGE.md` con documentación de cada script.

**Impacto**: **Medio** – Scripts más robustos, menos fallos silenciosos.

**Prioridad**: **P1 – ALTA**

---

#### **Acción M1-008: Implementar CI/CD pipeline**

**Qué hacer**:
1. Crear `.github/workflows/ci.yml`:
```yaml
name: CI

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Set up Python 3.10
        uses: actions/setup-python@v2
        with:
          python-version: '3.10'
      - name: Install dependencies
        run: pip install -r requirements.txt
      - name: Run tests
        run: pytest tests/ --cov=src --cov-report=xml
      - name: Upload coverage
        uses: codecov/codecov-action@v2
```

2. Gates de calidad:
   - Coverage mínimo: 70%.
   - Todos los tests deben pasar.
   - Linting con `flake8` o `ruff`.

3. Staging deployment automático:
   - En merge a branch `ALGORITMO_INSTITUCIONAL_SUBLIMINE`, deploy automático a VPS staging.
   - Smoke tests en staging antes de producción.

**Impacto**: **Medio-Alto** – Detecta problemas antes de merge, automatiza despliegues.

**Prioridad**: **P1 – ALTA**

---

#### **Acción M1-009: Análisis de hotspots de bugs**

**Qué hacer**:
1. Crear script de análisis:
```python
# tools/bug_hotspot_analysis.py
import pandas as pd

bugs = [
    {'file': 'order_flow.py', 'severity': 'P1', 'count': 5},
    {'file': 'liquidity_sweep.py', 'severity': 'P2', 'count': 3},
    # ... todos los bugs ...
]

df = pd.DataFrame(bugs)
hotspots = df.groupby('file').agg({'count': 'sum', 'severity': 'min'})
print("Top 5 archivos con más bugs:")
print(hotspots.sort_values('count', ascending=False).head(5))
```

2. Generar `docs/BUG_HOTSPOT_REPORT.md` con:
   - Top 10 archivos con más bugs.
   - Estrategias con mayor densidad de bugs.
   - Recomendación: refactoring completo de archivos con >5 bugs.

3. Priorizar refactoring:
   - Archivos con ≥5 bugs → candidatos a reescritura completa.
   - Estrategias "broken" (3 en total) → no refactorizar, eliminar y reescribir desde cero.

**Impacto**: **Medio** – Identifica áreas de alto riesgo para intervención profunda.

**Prioridad**: **P1 – MEDIA**

---

#### **Acción M1-010: Centralizar configuración de thresholds**

**Qué hacer**:
1. Crear `config/thresholds.yaml`:
```yaml
brain:
  min_arbitration_score: 0.65
  vpin_threshold_low: 0.30
  vpin_threshold_high: 0.50

order_flow:
  vpin_bucket_volume:
    EURUSD: 100000
    GBPUSD: 80000
    XAUUSD: 50000
```

2. Cargar config en runtime:
```python
import yaml

with open('config/thresholds.yaml') as f:
    config = yaml.safe_load(f)

min_arbitration_score = config['brain']['min_arbitration_score']
```

3. Validación de config al startup:
```python
def validate_config(config):
    assert 0.0 <= config['brain']['min_arbitration_score'] <= 1.0
    # ... más validaciones ...
```

**Impacto**: **Bajo** – Facilita ajustes de thresholds sin tocar código.

**Prioridad**: **P2 – BAJA**

---

### PLAN DE ACCIÓN PRIORIZADO – MANDATO 1

**Fase inmediata (Semana 1)**:
1. **M1-001**: Crear `TESTING_STRATEGY.md` + estructura `tests/` + tests críticos P0.
2. **M1-002**: Implementar logging estructurado + alertas mínimas.
3. **M1-003**: Documentar threading model + añadir timeouts en locks.
4. **M1-004**: Añadir fallback en validaciones + circuit breaker básico.

**Fase corto plazo (Semana 2-3)**:
5. **M1-005**: Implementar versionado semántico + `CHANGELOG.md`.
6. **M1-006**: Crear runbooks operacionales e incident response.
7. **M1-007**: Endurecer scripts PowerShell con error handling.
8. **M1-008**: Configurar CI/CD básico con GitHub Actions.

**Fase medio plazo (Mes 1)**:
9. **M1-009**: Análisis de hotspots + priorización de refactoring.
10. **M1-010**: Centralizar thresholds en `config/thresholds.yaml`.

---

### VEREDICTO FINAL – MANDATO 1

**Estado**: ⚠️ **COMPLETADO CON DEFICIENCIAS CRÍTICAS**

**Logros**:
- ✅ 97 bugs corregidos (P0+P1+P2).
- ✅ Código base funcional.
- ✅ Documentación de thresholds añadida.

**Fallas institucionales**:
- ❌ **Testing ausente** → riesgo P0 de regresiones.
- ❌ **Observabilidad nula** → imposible operar en producción con seguridad.
- ❌ **Concurrency sin análisis** → riesgo P0 de deadlocks.
- ❌ **Validaciones sin fallback** → riesgo P0 de crash total.

**Recomendación**:
**NO DESPLEGAR A PRODUCCIÓN** hasta completar:
- M1-001 (Testing).
- M1-002 (Observabilidad).
- M1-003 (Concurrency análisis).
- M1-004 (Fallback en validaciones).

**Aprobación condicional**: Sistema puede pasar a Mandato 2 (Estrategias) SOLO si se ejecuta plan de acción inmediato en paralelo.

---

**FIN AUDITORÍA MANDATO 1**

---

## MANDATO 2 – AUDITORÍA INSTITUCIONAL

**Alcance**: Portfolio de 24 estrategias, clasificación broken/hybrid/approved, integración con Risk Engine y Microestructura.

**Estado actual**: PENDIENTE DE CIRUGÍA - **Zoo de estrategias sin gobernanza, solapamientos masivos, falta de catálogo institucional**.

---

### RIESGOS / DEBILIDADES DETECTADAS

#### **P0 (CRÍTICO) – Riesgos que pueden causar pérdidas materiales o degradación severa**

**P0-005: Ausencia total de catálogo institucional de estrategias**

**Descripción**:
- 24 estrategias identificadas en `src/strategies/`:
  - `momentum_quality.py`
  - `liquidity_sweep.py`
  - `order_block_institutional.py`
  - `breakout_volume_confirmation.py`
  - `mean_reversion_statistical.py`
  - `vpin_reversal_extreme.py`
  - `order_flow_toxicity.py`
  - `ofi_refinement.py`
  - `spoofing_detection_l2.py`
  - `iceberg_detection.py`
  - `nfp_news_event_handler.py`
  - `htf_ltf_liquidity.py`
  - `fvg_institutional.py`
  - `idp_inducement_distribution.py`
  - `footprint_orderflow_clusters.py`
  - `kalman_pairs_trading.py`
  - `statistical_arbitrage_johansen.py`
  - `correlation_divergence.py`
  - `correlation_cascade_detection.py`
  - `volatility_regime_adaptation.py`
  - `fractal_market_structure.py`
  - `topological_data_analysis_regime.py`
  - `crisis_mode_volatility_spike.py`
  - `calendar_arbitrage_flows.py`

- **NO existe documento `STRATEGY_CATALOG.md`** con:
  - Nombre formal.
  - Tipo (momentum, mean reversion, liquidity, news, arbitrage, etc.).
  - Universo de símbolos aplicable (FX, commodities, crypto, indices).
  - Horizonte de holding esperado (minutos, horas, días).
  - Métricas objetivo: Sharpe, hit rate, max DD.
  - Estado (experimental, pilot, production, degraded, retired).

**Evidencia**:
- 24 archivos `.py` en `src/strategies/`.
- NO existe `docs/STRATEGY_CATALOG.md`.
- NO hay archivo central que liste qué estrategias están activas vs desactivadas.
- `brain.py` tiene `fit_matrix` hardcodeado con nombres de estrategias sin documentación de estado.

**Impacto**:
- **Muy alto**:
  - **Imposible saber qué estrategias están en producción** vs experimentales.
  - **Riesgo de activar estrategias "broken"** sin querer.
  - **Auditoría interna rechazaría sistema** sin inventario formal de estrategias.
  - **No se puede evaluar exposición por tipo de estrategia** (ej: "¿cuánto riesgo tenemos en momentum vs mean reversion?").

**Severidad**: **P0 – CRÍTICO**

---

**P0-006: Factor crowding interno masivo (múltiples estrategias = misma idea)**

**Descripción**:
- Solapamiento brutal entre estrategias:
  - **Order Flow**: `order_flow_toxicity.py`, `ofi_refinement.py`, `footprint_orderflow_clusters.py` → 3 estrategias mirando OFI/VPIN.
  - **Liquidity**: `liquidity_sweep.py`, `htf_ltf_liquidity.py`, `iceberg_detection.py`, `spoofing_detection_l2.py` → 4 estrategias mirando liquidez/Level 2.
  - **Order Blocks**: `order_block_institutional.py`, `fvg_institutional.py`, `idp_inducement_distribution.py` → 3 estrategias con conceptos ICT/SMC.
  - **Correlación**: `correlation_divergence.py`, `correlation_cascade_detection.py` → 2 estrategias casi idénticas.
  - **Pairs Trading**: `kalman_pairs_trading.py`, `statistical_arbitrage_johansen.py` → 2 estrategias de stat arb.

- **Riesgo**: Si 3-4 estrategias disparan señales al mismo tiempo porque miran el mismo edge:
  - **Sobre-exposición** a un solo factor (ej: "order flow positivo").
  - **Conteo triple del mismo riesgo** → rompe límite de 2% por idea si cada estrategia pide 1.5%.
  - **Correlación entre estrategias = 1.0** → diversificación cero.

**Evidencia**:
- Lectura de código:
  - `order_flow_toxicity.py` usa VPIN + OFI.
  - `ofi_refinement.py` usa OFI + delta.
  - `footprint_orderflow_clusters.py` usa footprint (que también es order flow).
- NO hay matriz de correlación entre estrategias.
- NO hay análisis de overlap de features.

**Impacto**:
- **Muy alto**:
  - **Drawdown amplificado**: Si el factor subyacente falla, todas las estrategias pierden juntas.
  - **ExposureManager puede NO detectar** que 4 estrategias = 1 sola idea.
  - **Sharpe del portfolio se degrada** por falta de diversificación real.

**Severidad**: **P0 – CRÍTICO**

---

**P0-007: Clasificación "broken/hybrid/approved" sin criterios documentados**

**Descripción**:
- Usuario mencionó:
  - 13 "aprobadas".
  - 8 "hybrid".
  - 3 "broken".
- **NO existe documento que defina**:
  - ¿Qué hace que una estrategia sea "aprobada"?
    - ¿Sharpe > X?
    - ¿Win rate > Y%?
    - ¿Backtest en N meses de datos?
  - ¿Qué hace que una estrategia sea "hybrid"?
  - ¿Qué hace que una estrategia sea "broken"?
  - ¿Cuándo una estrategia pasa de "experimental" → "production"?
  - ¿Cuándo una estrategia se degrada y se retira?

**Evidencia**:
- NO existe `docs/STRATEGY_LIFECYCLE_POLICY.md`.
- NO hay métricas de promoción/degradación.
- NO hay proceso formal de aprobación.

**Impacto**:
- **Muy alto**:
  - **Estrategias "aprobadas" pueden estar rotas** sin que nadie lo detecte.
  - **Estrategias "broken" pueden activarse** por error.
  - **Sin criterios objetivos, decisiones son subjetivas** → inaceptable para auditoría.

**Severidad**: **P0 – CRÍTICO**

---

**P0-008: Estrategias usan conceptos SMC/ICT sin formalización cuantitativa rigurosa**

**Descripción**:
- Varias estrategias usan terminología SMC/ICT:
  - `order_block_institutional.py`: "order blocks", "displacement".
  - `fvg_institutional.py`: "Fair Value Gap".
  - `idp_inducement_distribution.py`: "Inducement, Distribution, Price delivery" (conceptos SMC puros).
  - `htf_ltf_liquidity.py`: "liquidity sweeps".

- Aunque el código intenta formalizarlos (ej: `order_block_institutional.py` cita papers de Hasbrouck, Easley):
  - **Riesgo de subjetividad residual**: Términos como "displacement" o "FVG" pueden interpretarse de múltiples formas.
  - **No hay backtests publicados** que validen que estos conceptos funcionan cuantitativamente.
  - **Olor a retail camuflado**: Auditoría institucional cuestionaría si esto es market microstructure real o SMC con paper citations.

**Evidencia**:
```python
# order_block_institutional.py:4
"""
🏆 REAL INSTITUTIONAL IMPLEMENTATION - NO RETAIL DISPLACEMENT GARBAGE
...
```
- Comentarios agresivos contra retail, pero definiciones aún dependen de "displacement", "OFI absorption", conceptos que necesitan validación empírica.

**Impacto**:
- **Alto**:
  - **Model Risk rechazaría** estrategias sin validación empírica robusta.
  - **Riesgo de overfitting** a patrones que no se replican en vivo.
  - **Credibilidad del sistema degradada** si auditor detecta terminología retail.

**Severidad**: **P0 – CRÍTICO**

---

#### **P1 (IMPORTANTE) – Degrada calidad institucional**

**P1-006: Falta de integración explícita de estrategias con MANDATO 4 (QualityScorer) y MANDATO 5 (Microestructura/Multiframe)**

**Descripción**:
- Estrategias implementadas, pero:
  - **NO declaran explícitamente**:
    - Qué features de microestructura usan (VPIN, OFI, depth, spoofing).
    - Qué dependencia tienen del MultiFrameContext (HTF/MTF/LTF).
    - Qué peso estructural esperan en QualityScorer (vía pedigree).

- Ejemplo: `momentum_quality.py`:
  - Usa `vpin_clean_max`, `vpin_toxic_min`.
  - PERO: NO declara formalmente dependency en `MicrostructureEngine`.
  - ¿Qué pasa si microstructure data está degradada?

**Evidencia**:
- Archivos de estrategias NO tienen sección tipo:
```python
DEPENDENCIES = {
    'microstructure': ['vpin', 'ofi'],
    'multiframe': ['htf_trend', 'mtf_zones'],
    'min_data_health_score': 0.70,
}
```

**Impacto**:
- **Medio**:
  - **Debugging complicado**: Si estrategia falla, no está claro qué componente upstream causó el problema.
  - **Integración frágil**: Cambios en MicrostructureEngine pueden romper estrategias sin que nadie lo sepa.

**Severidad**: **P1 – IMPORTANTE**

---

**P1-007: Ausencia de backtests documentados con métricas institucionales**

**Descripción**:
- 24 estrategias, CERO backtests documentados con:
  - Sharpe ratio.
  - Max drawdown.
  - Win rate.
  - Profit factor.
  - Período de backtest (ej: 2020-2024).
  - Out-of-sample validation.

**Evidencia**:
- NO existe `docs/BACKTEST_RESULTS.md`.
- NO hay carpeta `backtests/` con resultados archivados.
- Algunos archivos tienen comentarios tipo:
```python
# order_block_institutional.py:56
Win Rate: 70-77% (institutional grade with order flow confirmation)
```
- PERO: Sin evidencia empírica, esto es marketing, no validación.

**Impacto**:
- **Medio**:
  - **Imposible evaluar qué estrategias funcionan** sin backtests.
  - **Model Risk rechazaría** estrategias sin validación empírica.
  - **Riesgo de desplegar estrategias que pierden dinero** en vivo.

**Severidad**: **P1 – IMPORTANTE**

---

**P1-008: Hardcoded thresholds en estrategias sin proceso de calibración**

**Descripción**:
- Todas las estrategias tienen thresholds hardcodeados:
  - `momentum_quality.py`: `price_threshold=0.30`, `volume_threshold=1.40`, `vpin_clean_max=0.30`.
  - `liquidity_sweep.py`: `penetration_min=3`, `penetration_max=15`, `volume_threshold=1.3`.
  - `order_block_institutional.py`: `volume_sigma_threshold=2.5`, `ofi_absorption_threshold=3.0`.

- **NO hay proceso de calibración**:
  - ¿Cómo se derivaron estos valores?
  - ¿Se optimizaron en backtest?
  - ¿Se recalibran periódicamente?

**Evidencia**:
- Thresholds en código Python, NO en `config/strategy_params.yaml`.
- NO existe `docs/CALIBRATION_METHODOLOGY.md`.

**Impacto**:
- **Medio**:
  - **Thresholds subóptimos** → peor performance.
  - **No adaptación a cambios de régimen** → estrategias se degradan con el tiempo.
  - **Difícil ajustar parámetros** sin tocar código.

**Severidad**: **P1 – IMPORTANTE**

---

**P1-009: Falta de matriz de compatibilidad estrategia-símbolo**

**Descripción**:
- Estrategias NO declaran en qué símbolos funcionan mejor:
  - ¿`kalman_pairs_trading` aplica a FX, commodities, crypto, o todos?
  - ¿`nfp_news_event_handler` solo aplica a USD pairs?
  - ¿`crisis_mode_volatility_spike` solo aplica a XAUUSD?

- Riesgo: Activar estrategia en símbolo incompatible → pérdidas.

**Evidencia**:
- Archivos de estrategias NO tienen:
```python
SUPPORTED_SYMBOLS = ['EURUSD', 'GBPUSD']  # Solo FX majors
```

**Impacto**:
- **Medio**:
  - **Estrategia aplicada a símbolo incorrecto** → performance degradada.
  - **No se puede filtrar automáticamente** qué estrategias aplican a qué símbolos.

**Severidad**: **P1 – IMPORTANTE**

---

**P1-010: Estrategias "news" y "calendar" sin integración con news feed real**

**Descripción**:
- Estrategias identificadas:
  - `nfp_news_event_handler.py`: Maneja eventos NFP (Non-Farm Payrolls).
  - `calendar_arbitrage_flows.py`: Arbitraje basado en calendario económico.

- **NO hay evidencia de integración con news feed**:
  - ¿De dónde vienen los datos de news?
  - ¿Hay API de calendario económico (Bloomberg, Reuters, FXStreet)?
  - ¿Latencia del feed?

**Evidencia**:
- NO existe `src/data_feeds/news_feed.py`.
- NO hay configuración de API en `config/`.

**Impacto**:
- **Medio**:
  - **Estrategias news-based NO pueden operar** sin feed de noticias.
  - **Latencia de news feed crítica**: si llega tarde, estrategia no sirve.

**Severidad**: **P1 – IMPORTANTE**

---

#### **P2 (MENOR) – Calidad de código, organización**

**P2-004: Naming inconsistente en archivos de estrategias**

**Descripción**:
- Mix de estilos:
  - `momentum_quality.py` (snake_case, correcto).
  - `nfp_news_event_handler.py` (muy largo).
  - `idp_inducement_distribution.py` (acrónimo IDP sin expansión).

**Impacto**: **Bajo** - Dificulta navegación, NO causa fallos.

**Severidad**: **P2 – MENOR**

---

**P2-005: Comentarios agresivos y poco profesionales en código**

**Descripción**:
```python
# order_block_institutional.py:4
🏆 REAL INSTITUTIONAL IMPLEMENTATION - NO RETAIL DISPLACEMENT GARBAGE
```

- Aunque expresan frustración legítima con retail logic, **tono poco profesional** para código institucional.

**Impacto**: **Bajo** - Auditoría interna podría cuestionar profesionalismo.

**Severidad**: **P2 – MENOR**

---

**P2-006: Falta de docstrings completos en métodos de estrategias**

**Descripción**:
- Muchas funciones internas sin docstrings:
```python
def _analyze_momentum_quality(self, market_data, features):
    # Sin docstring completo
```

**Impacto**: **Bajo** - Dificulta mantenimiento.

**Severidad**: **P2 – MENOR**

---

### RESUMEN DE RIESGOS MANDATO 2

| Severidad | Cantidad | Críticos destacados |
|-----------|----------|---------------------|
| **P0 (CRÍTICO)** | 4 | Sin catálogo, Factor crowding masivo, Clasificación sin criterios, Conceptos SMC sin validación |
| **P1 (IMPORTANTE)** | 5 | Sin integración M4/M5 explícita, Sin backtests, Thresholds hardcoded, Sin matriz símbolo-estrategia, News sin feed |
| **P2 (MENOR)** | 3 | Naming inconsistente, Comentarios poco profesionales, Docstrings incompletos |
| **TOTAL** | **12** | **4 P0 requieren acción inmediata** |

---

### MEJORAS INSTITUCIONALES RECOMENDADAS

#### **Acción M2-001: Crear catálogo institucional de estrategias**

**Qué hacer**:
1. Crear documento `docs/STRATEGY_CATALOG.md` con tabla completa:

```markdown
# STRATEGY CATALOG – SUBLIMINE TradingSystem

| ID | Nombre | Tipo | Símbolos | Holding | Sharpe Target | Status | Owner |
|----|--------|------|----------|---------|---------------|--------|-------|
| S001 | momentum_quality | Momentum | EURUSD,GBPUSD,XAUUSD | 2-6h | >1.5 | PRODUCTION | Core |
| S002 | liquidity_sweep | Liquidity | ALL | <1h | >1.8 | PRODUCTION | Core |
| S003 | order_block_institutional | Microstructure | FX,Metals | 1-4h | >1.6 | PILOT | Advanced |
| S004 | breakout_volume_confirmation | Momentum | ALL | 1-3h | >1.4 | PRODUCTION | Core |
| S005 | mean_reversion_statistical | Mean Reversion | FX | 30min-2h | >1.3 | DEGRADED | Core |
| ... | ... | ... | ... | ... | ... | ... | ... |
| S024 | calendar_arbitrage_flows | News/Event | USD pairs | Minutes | >2.0 | EXPERIMENTAL | Advanced |
```

2. Campos obligatorios:
   - **ID**: Identificador único (S001-S024).
   - **Nombre**: Nombre de archivo (sin `.py`).
   - **Tipo**: Momentum, Mean Reversion, Liquidity, Microstructure, News, Arbitrage, Volatility.
   - **Símbolos**: Whitelist de símbolos aplicables.
   - **Holding**: Duración típica de trade.
   - **Sharpe Target**: Sharpe ratio objetivo (backtest).
   - **Status**: EXPERIMENTAL, PILOT, PRODUCTION, DEGRADED, RETIRED.
   - **Owner**: Quién mantiene la estrategia (Core, Advanced, Research).

3. Proceso de actualización:
   - Revisión mensual de status.
   - Estrategias DEGRADED → análisis de causas.
   - Estrategias EXPERIMENTAL → backtest antes de PILOT.

**Impacto**: **Muy alto** – Visibilidad completa de portfolio de estrategias.

**Prioridad**: **P0 – INMEDIATA**

---

#### **Acción M2-002: Análisis de factor crowding y matriz de correlación**

**Qué hacer**:
1. Crear script `tools/strategy_correlation_analysis.py`:
```python
import pandas as pd
import numpy as np

# Simular señales de todas las estrategias en históricos
signals = {
    'momentum_quality': [...],
    'order_flow_toxicity': [...],
    # ...
}

# Calcular matriz de correlación
df = pd.DataFrame(signals)
corr_matrix = df.corr()

# Identificar clusters de alta correlación (>0.70)
high_corr_pairs = []
for i in range(len(corr_matrix)):
    for j in range(i+1, len(corr_matrix)):
        if corr_matrix.iloc[i,j] > 0.70:
            high_corr_pairs.append((corr_matrix.index[i], corr_matrix.columns[j], corr_matrix.iloc[i,j]))

print("Pares con correlación > 0.70:")
for pair in high_corr_pairs:
    print(f"{pair[0]} <-> {pair[1]}: {pair[2]:.2f}")
```

2. Generar `docs/STRATEGY_CORRELATION_MATRIX.md`:
   - Matriz visual de correlación.
   - Clusters identificados (ej: "Order Flow Cluster" con 3 estrategias correlación >0.80).
   - Recomendaciones:
     - Si 3+ estrategias tienen correlación >0.80 → considerar como 1 sola para límites de exposición.

3. Implementar en ExposureManager:
```python
# Ajustar exposición por cluster
if strategies_in_cluster(['order_flow_toxicity', 'ofi_refinement', 'footprint_orderflow_clusters']):
    max_cluster_risk = 3.0%  # NO 6% (3 × 2%)
```

**Impacto**: **Muy alto** – Previene sobre-exposición a factores correlacionados.

**Prioridad**: **P0 – INMEDIATA**

---

#### **Acción M2-003: Definir criterios de lifecycle de estrategias**

**Qué hacer**:
1. Crear `docs/STRATEGY_LIFECYCLE_POLICY.md`:

```markdown
# STRATEGY LIFECYCLE POLICY

## Estados

### EXPERIMENTAL
- Criterios de entrada:
  - Idea fundamentada en paper académico o evidencia empírica preliminar.
  - Código implementado con tests básicos.
- Restricciones:
  - NO puede operar en producción.
  - Solo backtesting en historical data.

### PILOT
- Criterios de promoción desde EXPERIMENTAL:
  - Backtest con Sharpe > 1.0 en ≥12 meses de datos.
  - Win rate > 50%.
  - Max DD < 15%.
  - Validación out-of-sample (20% de datos).
- Restricciones:
  - Puede operar en paper trading.
  - Límite de riesgo: 0.5% por idea (vs 2% en PRODUCTION).

### PRODUCTION
- Criterios de promoción desde PILOT:
  - Paper trading exitoso durante ≥3 meses.
  - Sharpe > 1.3.
  - Comportamiento estable (no spikes anómalos).
  - Revisión por Model Risk.
- Restricciones:
  - Límite de riesgo: hasta 2% por idea.

### DEGRADED
- Criterios de degradación desde PRODUCTION:
  - Sharpe cae <0.5 durante 2 meses consecutivos.
  - Drawdown > 20% en 1 mes.
  - Win rate cae <40%.
- Acciones:
  - Reducir riesgo a 0.5% por idea.
  - Análisis de causas (regime change, strategy decay, data quality).
  - Decisión: recalibrar o RETIRED.

### RETIRED
- Criterios de retiro desde DEGRADED:
  - No se identifica causa corregible.
  - Sharpe negativo durante 3 meses.
- Acciones:
  - Desactivar completamente.
  - Archivar código en `src/strategies/retired/`.
```

2. Implementar en código:
```python
# src/governance/strategy_lifecycle.py
class StrategyLifecycleManager:
    def evaluate_promotion(self, strategy_id, metrics):
        if metrics['sharpe'] > 1.0 and metrics['max_dd'] < 0.15:
            return 'PILOT'
        # ...
```

**Impacto**: **Muy alto** – Decisiones objetivas sobre estrategias.

**Prioridad**: **P0 – INMEDIATA**

---

#### **Acción M2-004: Validación empírica de conceptos SMC/ICT**

**Qué hacer**:
1. Para cada estrategia con conceptos SMC (order blocks, FVG, inducement):
   - Backtest riguroso en ≥24 meses de datos.
   - Validación out-of-sample en 20% de datos.
   - Comparación con baseline (buy-and-hold, random entry).

2. Documentar en `docs/STRATEGY_VALIDATION_REPORTS.md`:
```markdown
## order_block_institutional

### Definición cuantitativa
- Order block = última vela antes de displacement >2σ volumen.
- Displacement = movimiento >2×ATR en <3 velas.
- Retest = precio vuelve a zona ±0.5×ATR del OB.

### Backtest
- Período: 2021-01-01 a 2024-12-31 (4 años).
- Sharpe: 1.62.
- Win rate: 68%.
- Max DD: 12%.

### Out-of-sample
- Período: 2023-07-01 a 2024-12-31 (18 meses).
- Sharpe: 1.54 (degradación <5%, aceptable).

### Conclusión
- ✅ APROBADA para PILOT.
- Concepto "order block" validado cuantitativamente.
```

3. Si estrategia NO pasa validación:
   - Status = EXPERIMENTAL o RETIRED.
   - NO promoción a PILOT.

**Impacto**: **Muy alto** – Elimina estrategias no probadas, aumenta credibilidad.

**Prioridad**: **P0 – INMEDIATA**

---

#### **Acción M2-005: Declarar dependencies explícitas en estrategias**

**Qué hacer**:
1. Añadir a cada estrategia:
```python
# momentum_quality.py
class MomentumQuality(StrategyBase):
    METADATA = {
        'id': 'S001',
        'name': 'momentum_quality',
        'type': 'Momentum',
        'supported_symbols': ['EURUSD', 'GBPUSD', 'XAUUSD', 'BTCUSD', 'US50'],
        'holding_period': '2-6h',
        'dependencies': {
            'microstructure': ['vpin', 'ofi'],  # Requiere VPIN y OFI
            'multiframe': ['htf_trend'],        # Requiere HTF trend
            'data_health': 0.70,                 # Mínimo data health score
        },
        'risk_params': {
            'max_risk_per_trade': 2.0,           # % máximo
            'max_open_trades': 3,
        },
    }
```

2. Validar dependencies en runtime:
```python
def evaluate(self, market_data, features):
    # Validar que microstructure está disponible
    if 'vpin' not in features or features['vpin'] is None:
        self.logger.warning("VPIN not available, skipping evaluation")
        return []

    if features['data_health_score'] < self.METADATA['dependencies']['data_health']:
        self.logger.warning(f"Data health too low: {features['data_health_score']}")
        return []
```

**Impacto**: **Medio-Alto** – Debugging más fácil, integración más robusta.

**Prioridad**: **P1 – ALTA**

---

#### **Acción M2-006: Generar backtests documentados para todas las estrategias**

**Qué hacer**:
1. Crear framework de backtesting estandarizado:
```python
# tools/backtest_runner.py
def run_backtest(strategy_class, data, config):
    results = {
        'sharpe': ...,
        'max_dd': ...,
        'win_rate': ...,
        'profit_factor': ...,
        'trades': [...],
    }
    return results
```

2. Ejecutar backtests para todas las estrategias:
```bash
python tools/backtest_runner.py --strategy momentum_quality --start 2021-01-01 --end 2024-12-31
```

3. Archivar resultados en `backtests/YYYY-MM-DD/`:
```
backtests/
  2025-11-13/
    momentum_quality_backtest.json
    liquidity_sweep_backtest.json
    ...
```

4. Generar reporte consolidado en `docs/BACKTEST_RESULTS.md`:
```markdown
| Estrategia | Sharpe | Win Rate | Max DD | Status |
|------------|--------|----------|--------|--------|
| momentum_quality | 1.52 | 64% | 11% | ✅ PASS |
| liquidity_sweep | 1.78 | 71% | 9% | ✅ PASS |
| idp_inducement_distribution | 0.42 | 48% | 22% | ❌ FAIL |
```

**Impacto**: **Medio-Alto** – Evidencia empírica de performance.

**Prioridad**: **P1 – ALTA**

---

#### **Acción M2-007: Externalizar thresholds a config centralizado**

**Qué hacer**:
1. Crear `config/strategy_params.yaml`:
```yaml
momentum_quality:
  price_threshold: 0.30
  volume_threshold: 1.40
  vpin_clean_max: 0.30
  min_quality_score: 0.65

liquidity_sweep:
  penetration_min: 3
  penetration_max: 15
  volume_threshold: 1.3
```

2. Cargar en estrategias:
```python
import yaml

with open('config/strategy_params.yaml') as f:
    params = yaml.safe_load(f)

config = params['momentum_quality']
strategy = MomentumQuality(config)
```

3. Proceso de recalibración:
   - Mensual: revisar performance de estrategias.
   - Si Sharpe cae <1.0 → recalibrar thresholds en grid search.
   - Actualizar `config/strategy_params.yaml`.

**Impacto**: **Medio** – Facilita ajustes sin tocar código.

**Prioridad**: **P1 – MEDIA**

---

#### **Acción M2-008: Crear matriz estrategia-símbolo**

**Qué hacer**:
1. En `METADATA` de cada estrategia, declarar:
```python
'supported_symbols': ['EURUSD', 'GBPUSD', 'XAUUSD'],
```

2. Implementar filtro en arbiter:
```python
def filter_signals_by_symbol_compatibility(signals):
    filtered = []
    for signal in signals:
        strategy = get_strategy(signal.strategy_id)
        if signal.symbol in strategy.METADATA['supported_symbols']:
            filtered.append(signal)
        else:
            logger.warning(f"Signal from {signal.strategy_id} rejected: {signal.symbol} not supported")
    return filtered
```

**Impacto**: **Medio** – Previene aplicación de estrategias a símbolos incompatibles.

**Prioridad**: **P1 – MEDIA**

---

#### **Acción M2-009: Integrar news feed para estrategias event-driven**

**Qué hacer**:
1. Integrar news feed API (ej: FXStreet, Investing.com):
```python
# src/data_feeds/news_feed.py
class NewsFeed:
    def get_upcoming_events(self, currency, hours_ahead=24):
        # Retorna eventos NFP, PMI, CPI, etc.
        return [
            {'timestamp': ..., 'event': 'NFP', 'currency': 'USD', 'impact': 'HIGH'},
        ]
```

2. Conectar a estrategias:
```python
# nfp_news_event_handler.py
def evaluate(self, market_data, features):
    upcoming_events = self.news_feed.get_upcoming_events('USD', hours_ahead=2)

    for event in upcoming_events:
        if event['event'] == 'NFP' and event['impact'] == 'HIGH':
            # Preparar estrategia pre-NFP
```

**Impacto**: **Medio** – Activa estrategias news-based.

**Prioridad**: **P1 – MEDIA**

---

#### **Acción M2-010: Refactoring de naming y limpieza de código**

**Qué hacer**:
1. Renombrar archivos largos:
   - `nfp_news_event_handler.py` → `news_nfp_handler.py`.
   - `idp_inducement_distribution.py` → `smc_idp_pattern.py` (y documentar que IDP = Inducement-Distribution-Price).

2. Eliminar comentarios agresivos:
```python
# ANTES
"""🏆 REAL INSTITUTIONAL - NO RETAIL GARBAGE"""

# DESPUÉS
"""
Institutional order block strategy using order flow microstructure.
Based on: Hasbrouck (2007), Easley et al. (2012).
"""
```

3. Añadir docstrings completos:
```python
def _analyze_momentum_quality(self, market_data: pd.DataFrame, features: Dict) -> Optional[Dict]:
    """
    Analiza calidad de momentum usando confluencia de factores.

    Args:
        market_data: DataFrame con OHLCV de últimos N períodos
        features: Dict con features pre-calculados (VPIN, OFI, etc.)

    Returns:
        Dict con quality_score, direction, strength, o None si no califica
    """
```

**Impacto**: **Bajo** – Mejora profesionalismo del código.

**Prioridad**: **P2 – BAJA**

---

### PLAN DE ACCIÓN PRIORIZADO – MANDATO 2

**Fase inmediata (Semana 1)**:
1. **M2-001**: Crear `STRATEGY_CATALOG.md` con todas las estrategias.
2. **M2-002**: Análisis de correlación entre estrategias.
3. **M2-003**: Definir `STRATEGY_LIFECYCLE_POLICY.md`.
4. **M2-004**: Validación empírica de estrategias SMC (al menos 3 principales).

**Fase corto plazo (Semana 2-3)**:
5. **M2-005**: Declarar dependencies en METADATA de estrategias.
6. **M2-006**: Backtests documentados para top 10 estrategias.
7. **M2-007**: Externalizar thresholds a `config/strategy_params.yaml`.

**Fase medio plazo (Mes 1)**:
8. **M2-008**: Matriz estrategia-símbolo.
9. **M2-009**: Integración news feed para estrategias event-driven.
10. **M2-010**: Refactoring de naming y limpieza de comentarios.

---

### VEREDICTO FINAL – MANDATO 2

**Estado**: ⚠️ **ZOO DE ESTRATEGIAS SIN GOBERNANZA – NO APTO PARA PRODUCCIÓN**

**Logros**:
- ✅ 24 estrategias implementadas.
- ✅ Código mayormente funcional.
- ✅ Intento de formalización cuantitativa.

**Fallas institucionales**:
- ❌ **Sin catálogo formal** → imposible saber qué está activo.
- ❌ **Factor crowding masivo** → sobre-exposición oculta.
- ❌ **Clasificación "broken/hybrid/approved" sin criterios** → decisiones subjetivas.
- ❌ **Conceptos SMC sin validación empírica rigurosa** → riesgo de overfitting.
- ❌ **Sin backtests documentados** → no hay evidencia de que funcionen.

**Recomendación**:
**NO DESPLEGAR MÁS DE 5 ESTRATEGIAS A PRODUCCIÓN** hasta completar:
- M2-001 (Catálogo).
- M2-002 (Análisis de correlación).
- M2-003 (Lifecycle policy).
- M2-004 (Validación empírica de SMC).
- M2-006 (Backtests documentados).

**Estrategias recomendadas para PILOT inicial** (tras validación):
1. `momentum_quality` (si backtest >1.3 Sharpe).
2. `liquidity_sweep` (si backtest >1.5 Sharpe).
3. `breakout_volume_confirmation` (clásica, probablemente robusta).
4. `mean_reversion_statistical` (si no está degradada).
5. `order_flow_toxicity` (representante de cluster order flow).

**Resto de estrategias**: EXPERIMENTAL hasta validación.

---

**FIN AUDITORÍA MANDATO 2**

---

## MANDATO 3 – AUDITORÍA INSTITUCIONAL

**Alcance**: Brain-layer (SignalArbitrator, ML Adaptive Engine), meta-capa de decisión, integración con QualityScorer/MicrostructureEngine/ExposureManager.

**Estado actual**: DISEÑADO PERO SIN GOVERNANCE – **Caja negra potencialmente peligrosa sin límites claros ni model risk management**.

---

### RIESGOS / DEBILIDADES DETECTADAS

#### **P0 (CRÍTICO) – Riesgos que pueden causar pérdidas severas o anular controles de riesgo**

**P0-009: Brain-layer puede modificar decisiones sin límites documentados**

**Descripción**:
- `brain.py` y `ml_adaptive_engine.py` implementan:
  - `SignalArbitrator`: Selecciona entre señales conflictivas.
  - `ML Adaptive Engine`: Aprende de trades pasados y ajusta parámetros.
- **NO existe documento que defina** qué puede y NO puede tocar el brain-layer:
  - ¿Puede modificar risk caps (2% por idea)?
  - ¿Puede anular SL estructurales?
  - ¿Puede cambiar pesos del QualityScorer?
  - ¿Puede desactivar estrategias?
  - ¿Puede ignorar reglas de ExposureManager?

**Evidencia**:
- `brain.py:56-148`: `_score_signal()` usa pesos hardcodeados (40%, 25%, 20%, 10%, 5%).
- `ml_adaptive_engine.py`: Implementa "Parameter Optimizer" y "Risk Parameter Adapter".
- **NO existe `docs/BRAIN_LAYER_GOVERNANCE.md`** con áreas prohibidas.
- **NO existe `docs/MODEL_RISK_POLICY.md`** que defina cómo se valida el brain-layer.

**Impacto**:
- **Muy alto**:
  - **Brain-layer descontrolado puede anular risk caps** → pérdidas catastróficas.
  - **Puede degradar QualityScorer** ajustando pesos incorrectamente.
  - **Sin límites, puede entrar en loop de auto-destrucción** (ej: ajustar parámetros tras pérdidas, causando más pérdidas).
  - **Auditoría rechazaría sistema** sin governance de modelo predictivo.

**Escenario de fallo**:
```
1. Brain-layer detecta que estrategia X pierde dinero.
2. Ajusta pesos del QualityScorer para bajar peso de 'pedigree'.
3. Ahora todas las estrategias pasan threshold, incluyendo malas.
4. Sistema genera más pérdidas.
5. Brain-layer sobre-reacciona, desactiva estrategias buenas.
→ Colapso del sistema.
```

**Severidad**: **P0 – CRÍTICO**

---

**P0-010: ML Adaptive Engine sin challenger model ni validación independiente**

**Descripción**:
- `ml_adaptive_engine.py` implementa:
  - `RandomForestClassifier` para predecir éxito de señales.
  - `GradientBoostingRegressor` para predecir PnL.
  - `Ridge` regression para optimizar parámetros.
- **Problemas**:
  - NO hay **challenger model** (segundo modelo que valida predicciones del primero).
  - NO hay **backtesting del brain-layer** (¿funciona realmente o genera noise?).
  - NO hay **métricas de calidad del modelo** (accuracy, precision, recall, AUC).
  - NO hay **validación out-of-sample** antes de aplicar ajustes.

**Evidencia**:
- `ml_adaptive_engine.py:38-40`: Imports de sklearn (RandomForest, GradientBoosting, Ridge).
- NO existe `docs/ML_MODEL_VALIDATION.md`.
- NO hay carpeta `models/validation/` con métricas.

**Impacto**:
- **Muy alto**:
  - **Modelo puede overfittear** a ruido → decisiones incorrectas.
  - **Sin validación, modelo puede degradarse** sin que nadie lo detecte.
  - **Riesgo de data leakage** (entrenar con datos futuros por error).
  - **Model Risk rechazaría modelo** sin validación rigurosa.

**Severidad**: **P0 – CRÍTICO**

---

**P0-011: Ausencia de rollback mechanism si brain-layer se comporta mal**

**Descripción**:
- Brain-layer ajusta parámetros dinámicamente.
- **NO hay mecanismo de rollback** si:
  - Ajustes causan pérdidas > X%.
  - Modelo ML se degrada (accuracy cae).
  - Brain-layer rechaza señales buenas consistentemente.

**Evidencia**:
- NO existe `docs/BRAIN_LAYER_ROLLBACK_POLICY.md`.
- NO hay código que detecte comportamiento anómalo del brain-layer.
- NO hay snapshot de parámetros antes de ajustes.

**Impacto**:
- **Alto**:
  - **Ajustes malos son irreversibles** → sistema queda degradado.
  - **No se puede volver a última configuración buena** rápidamente.
  - **Pérdidas se acumulan** mientras se diagnostica problema.

**Severidad**: **P0 – CRÍTICO**

---

**P0-012: Data leakage potencial en learning loop**

**Descripción**:
- `TradeMemoryDatabase` almacena trades completos.
- **Riesgo**: Si learning loop usa datos del futuro para calibrar decisiones presentes:
  - Ej: Ajustar pesos del QualityScorer usando PnL de trades que aún no cerraron.
  - Ej: Entrenar modelo ML con datos de régimen futuro.

**Evidencia**:
- `ml_adaptive_engine.py`: Implementa `TradeMemoryDatabase` y `SignalRecord`.
- NO hay validación explícita de time-series split (train/validation temporal).
- NO existe `docs/DATA_GOVERNANCE_ML.md` que prevenga data leakage.

**Impacto**:
- **Muy alto**:
  - **Backtest falso positivo**: Modelo parece funcionar en backtest pero falla en vivo.
  - **Overfitting severo** a datos históricos.
  - **Pérdidas en producción** por decisiones basadas en datos contaminados.

**Severidad**: **P0 – CRÍTICO**

---

#### **P1 (IMPORTANTE) – Degrada calidad institucional**

**P1-011: Pesos del SignalArbitrator hardcodeados sin justificación empírica**

**Descripción**:
- `brain.py:108-141`: Scoring de señales usa pesos:
  - Quality: 40%
  - Performance: 25%
  - Regime: 20%
  - Risk-Reward: 10%
  - Timing: 5%

- **NO hay justificación**:
  - ¿Por qué 40% quality y no 50%?
  - ¿Por qué timing solo 5% cuando microestructura es crítica?
  - ¿Se derivaron de backtest o son arbitrarios?

**Evidencia**:
- Pesos hardcodeados en código.
- NO existe `docs/ARBITRATOR_WEIGHT_CALIBRATION.md`.

**Impacto**:
- **Medio**:
  - **Pesos subóptimos** → selección de señales no maximiza Sharpe.
  - **Sin calibración, pesos se vuelven obsoletos** con cambios de mercado.

**Severidad**: **P1 – IMPORTANTE**

---

**P1-012: Regime-strategy fit matrix hardcodeada sin actualización dinámica**

**Descripción**:
- `brain.py:183-223`: `fit_matrix` hardcodeado con valores tipo:
```python
'TREND_STRONG_UP': {
    'momentum_quality': 1.0,
    'breakout_volume_confirmation': 0.95,
    # ...
}
```

- **Problemas**:
  - Valores fijos sin proceso de calibración.
  - NO se actualiza con performance real de estrategias en cada régimen.
  - Si régimen cambia, matriz puede quedar obsoleta.

**Evidencia**:
- `brain.py:183`: `fit_matrix` dict hardcodeado.
- NO existe `tools/calibrate_regime_fit.py`.

**Impacto**:
- **Medio**:
  - **Estrategias mal asignadas a regímenes** → peor performance.
  - **No adaptación a cambios estructurales de mercado**.

**Severidad**: **P1 – IMPORTANTE**

---

**P1-013: ML Adaptive Engine sin métricas de monitoreo continuo**

**Descripción**:
- Modelos ML entrenados, pero:
  - **NO hay métricas de health**:
    - Accuracy en ventana deslizante.
    - Precision/Recall en últimas N predicciones.
    - AUC degradándose.
  - **NO hay alertas** si modelo se degrada.

**Evidencia**:
- NO existe `src/monitoring/ml_model_monitor.py`.
- NO hay dashboard de métricas ML.

**Impacto**:
- **Medio**:
  - **Modelo degrada silenciosamente** → decisiones incorrectas sin detección.
  - **No se sabe cuándo re-entrenar** modelo.

**Severidad**: **P1 – IMPORTANTE**

---

**P1-014: Falta de separación research vs production en ML pipeline**

**Descripción**:
- Código ML mezclado con lógica de producción.
- **NO hay separación clara**:
  - ¿Dónde se entrenan modelos? (research environment).
  - ¿Dónde se validan? (validation environment).
  - ¿Dónde se despliegan? (production).
  - ¿Cómo se versionan modelos?

**Evidencia**:
- NO existe `models/` con versionado (v1.0, v1.1, etc.).
- NO hay `MLflow` o sistema de tracking de experimentos.

**Impacto**:
- **Medio**:
  - **Modelos experimentales pueden llegar a producción** sin validación.
  - **Dificulta rollback** a versión anterior de modelo.

**Severidad**: **P1 – IMPORTANTE**

---

**P1-015: Brain-layer sin circuit breaker ante comportamiento anómalo**

**Descripción**:
- Brain-layer puede generar decisiones anómalas:
  - Rechazar 100% de señales durante 1 hora.
  - Aprobar señales de muy baja calidad (<0.30).
  - Cambiar pesos del arbitrator abruptamente.

- **NO hay circuit breaker** que detecte y detenga comportamiento anómalo.

**Evidencia**:
- NO existe `src/safety/brain_circuit_breaker.py`.
- NO hay reglas tipo:
```python
if rejection_rate_last_hour > 0.95:
    # ALERT: Brain-layer rechazando TODO
    switch_to_manual_mode()
```

**Impacto**:
- **Medio**:
  - **Comportamiento anómalo no detectado** → pérdida de oportunidades o pérdidas materiales.

**Severidad**: **P1 – IMPORTANTE**

---

#### **P2 (MENOR) – Calidad de código, documentación**

**P2-007: Comentarios "NOT retail" agresivos en brain.py**

**Descripción**:
```python
# brain.py:3
This is NOT a simple signal combiner. This is an advanced orchestration layer
that thinks at the PORTFOLIO level, not individual trade level.
```

- Tono defensivo poco profesional.

**Impacto**: **Bajo** - Auditoría podría cuestionar profesionalismo.

**Severidad**: **P2 – MENOR**

---

**P2-008: Falta de docstrings completos en métodos ML**

**Descripción**:
- Muchas funciones en `ml_adaptive_engine.py` sin docstrings completos:
  - Parámetros de entrada.
  - Outputs esperados.
  - Excepciones.

**Impacto**: **Bajo** - Dificulta mantenimiento.

**Severidad**: **P2 – MENOR**

---

### RESUMEN DE RIESGOS MANDATO 3

| Severidad | Cantidad | Críticos destacados |
|-----------|----------|---------------------|
| **P0 (CRÍTICO)** | 4 | Sin límites claros, Sin challenger model, Sin rollback, Data leakage potencial |
| **P1 (IMPORTANTE)** | 5 | Pesos hardcoded, Fit matrix fija, Sin monitoreo ML, Sin research/production split, Sin circuit breaker |
| **P2 (MENOR)** | 2 | Comentarios agresivos, Docstrings incompletos |
| **TOTAL** | **11** | **4 P0 requieren acción inmediata** |

---

### MEJORAS INSTITUCIONALES RECOMENDADAS

#### **Acción M3-001: Definir governance estricta del brain-layer**

**Qué hacer**:
1. Crear `docs/BRAIN_LAYER_GOVERNANCE.md`:

```markdown
# BRAIN LAYER GOVERNANCE

## Áreas Prohibidas (NO TOCAR JAMÁS)

### 1. Risk Caps
- Brain-layer **NUNCA puede modificar**:
  - Máximo 2.0% riesgo por idea.
  - Caps de exposición total (símbolo, estrategia, dirección).
  - Stop loss estructurales.

### 2. Quality Score Threshold
- Brain-layer **NO puede bajar** threshold de QualityScorer <0.50.
- Puede sugerir ajustes de pesos SOLO dentro de bandas:
  - Pedigree: [0.20, 0.30]
  - Signal: [0.20, 0.30]
  - Microstructure: [0.15, 0.25]
  - Data Health: [0.10, 0.20]
  - Portfolio: [0.10, 0.20]

### 3. Estrategias
- Brain-layer puede:
  - ✅ Ajustar pesos de estrategias en fit_matrix dentro de ±0.10.
  - ✅ Marcar estrategias como "under review".
- Brain-layer NO puede:
  - ❌ Desactivar estrategias PRODUCTION sin aprobación humana.
  - ❌ Activar estrategias EXPERIMENTAL en producción.

### 4. ExposureManager
- Brain-layer NO puede:
  - ❌ Anular límites de correlación.
  - ❌ Ignorar exposición por factor macro.

## Áreas Permitidas (CON RESTRICCIONES)

### 1. Signal Arbitration
- ✅ Seleccionar entre señales conflictivas.
- ✅ Ajustar pesos de arbitrator dentro de bandas predefinidas.

### 2. Regime Fit
- ✅ Ajustar fit_matrix dentro de ±0.10 de valor base.
- ✅ Sugerir recalibración de regímenes.

### 3. Parameter Tuning
- ✅ Ajustar thresholds de estrategias dentro de ±20% del valor base.
- ✅ Solo si backtest valida mejora.

## Proceso de Aprobación de Cambios

1. Brain-layer propone cambio → log detallado.
2. Cambio se valida en **paper trading** durante ≥1 semana.
3. Si Sharpe mejora ≥10% → aprobación automática.
4. Si cambio afecta risk caps → aprobación humana obligatoria.
```

2. Implementar en código:
```python
# src/governance/brain_governor.py
class BrainGovernor:
    FORBIDDEN_ACTIONS = [
        'modify_risk_caps',
        'disable_production_strategy',
        'bypass_exposure_limits',
    ]

    ALLOWED_PARAMETER_RANGES = {
        'quality_score_weights': {
            'pedigree': (0.20, 0.30),
            'signal': (0.20, 0.30),
            # ...
        },
        'fit_matrix_adjustment': (-0.10, +0.10),
    }

    def validate_action(self, action, params):
        if action in self.FORBIDDEN_ACTIONS:
            raise ForbiddenActionError(f"{action} is forbidden")

        if action == 'adjust_quality_weights':
            for key, value in params.items():
                min_val, max_val = self.ALLOWED_PARAMETER_RANGES['quality_score_weights'][key]
                if not (min_val <= value <= max_val):
                    raise ValueError(f"{key}={value} out of range [{min_val}, {max_val}]")

        return True
```

**Impacto**: **Muy alto** – Previene que brain-layer cause daños.

**Prioridad**: **P0 – INMEDIATA**

---

#### **Acción M3-002: Implementar challenger model y validación rigurosa**

**Qué hacer**:
1. Crear `docs/ML_MODEL_VALIDATION.md`:

```markdown
# ML MODEL VALIDATION POLICY

## Requerimientos Mínimos

Cualquier modelo ML debe cumplir:
1. **Backtest out-of-sample** ≥6 meses.
2. **Accuracy ≥65%** en predecir señales ganadoras.
3. **Precision ≥60%** (evitar falsos positivos).
4. **Walk-forward validation** en ≥3 períodos.

## Challenger Model

Todo modelo en producción debe tener challenger:
- Modelo A (producción) vs Modelo B (challenger).
- Comparación mensual de performance.
- Si challenger supera modelo A durante 2 meses → promoción.

## Métricas de Monitoreo

En ventana deslizante de 30 días:
- Accuracy actual vs esperada.
- Drift detection (distribución de features cambia).
- Calibration error (predicciones vs realidad).

Si alguna métrica degrada >20% → ALERT + rollback a modelo anterior.
```

2. Implementar challenger model:
```python
# src/ml/challenger_model.py
class ChallengerModelSystem:
    def __init__(self):
        self.production_model = load_model('models/production/v1.2.pkl')
        self.challenger_model = load_model('models/challenger/v1.3.pkl')

        self.production_metrics = deque(maxlen=100)
        self.challenger_metrics = deque(maxlen=100)

    def predict(self, features):
        # Ambos modelos predicen
        prod_pred = self.production_model.predict(features)
        chall_pred = self.challenger_model.predict(features)

        # Usar producción para decisión
        # Registrar ambos para comparación
        self.production_metrics.append({'prediction': prod_pred, ...})
        self.challenger_metrics.append({'prediction': chall_pred, ...})

        return prod_pred

    def evaluate_challenger(self):
        """Comparar performance mensual."""
        prod_accuracy = calculate_accuracy(self.production_metrics)
        chall_accuracy = calculate_accuracy(self.challenger_metrics)

        if chall_accuracy > prod_accuracy + 0.05:  # +5% mejor
            logger.warning("Challenger model outperforms production")
            # Trigger human review
```

**Impacto**: **Muy alto** – Valida que modelo ML realmente funciona.

**Prioridad**: **P0 – INMEDIATA**

---

#### **Acción M3-003: Implementar rollback mechanism automático**

**Qué hacer**:
1. Snapshot de parámetros antes de cada ajuste:
```python
# src/safety/parameter_snapshot.py
class ParameterSnapshotManager:
    def __init__(self):
        self.snapshots = deque(maxlen=100)

    def take_snapshot(self, component_name):
        """Guarda estado actual de parámetros."""
        snapshot = {
            'timestamp': datetime.now(),
            'component': component_name,
            'parameters': get_current_parameters(component_name),
            'performance_before': get_recent_sharpe(),
        }
        self.snapshots.append(snapshot)
        logger.info(f"Snapshot taken: {component_name}")

    def rollback_to_snapshot(self, snapshot_id):
        """Revierte a snapshot anterior."""
        snapshot = self.snapshots[snapshot_id]
        apply_parameters(snapshot['component'], snapshot['parameters'])
        logger.warning(f"Rolled back to snapshot {snapshot_id}")
```

2. Detector de degradación:
```python
# src/safety/degradation_detector.py
def detect_brain_degradation():
    """Detecta si ajustes del brain-layer causaron degradación."""
    # Métricas últimas 24h vs 7 días previos
    recent_sharpe = calculate_sharpe(hours=24)
    baseline_sharpe = calculate_sharpe(days=7)

    if recent_sharpe < baseline_sharpe * 0.70:  # -30% degradación
        logger.critical("DEGRADATION DETECTED: Sharpe dropped 30%")
        # Rollback automático
        snapshot_manager.rollback_to_last_good_snapshot()
        send_alert("Brain-layer rolled back due to degradation")
```

**Impacto**: **Alto** – Recuperación rápida ante problemas.

**Prioridad**: **P0 – INMEDIATA**

---

#### **Acción M3-004: Prevenir data leakage con time-series split estricto**

**Qué hacer**:
1. Crear `docs/DATA_GOVERNANCE_ML.md`:

```markdown
# DATA GOVERNANCE FOR ML

## Reglas Estrictas

### 1. Time-Series Split
- Training data: hasta timestamp T.
- Validation data: (T, T+30 días].
- Test data: (T+30, T+60 días].
- **NUNCA** usar datos futuros para entrenar.

### 2. Feature Engineering
- Solo usar features disponibles en el momento de decisión.
- Prohibido:
  - ❌ Usar PnL de trade antes de cerrar.
  - ❌ Usar régimen futuro.
  - ❌ Lookahead bias en indicadores.

### 3. Validación
- Walk-forward testing obligatorio.
- Re-entrenar modelo cada 30 días con datos nuevos.
```

2. Implementar en código:
```python
# tools/ml_training.py
def train_model_with_strict_split(data, target_variable):
    """Entrena modelo con split temporal estricto."""
    # Ordenar por timestamp
    data = data.sort_values('timestamp')

    # Split: 70% train, 15% validation, 15% test
    n = len(data)
    train_end = int(n * 0.70)
    val_end = int(n * 0.85)

    train_data = data.iloc[:train_end]
    val_data = data.iloc[train_end:val_end]
    test_data = data.iloc[val_end:]

    # Verificar no overlap
    assert train_data['timestamp'].max() < val_data['timestamp'].min()
    assert val_data['timestamp'].max() < test_data['timestamp'].min()

    # Entrenar
    model = RandomForestClassifier()
    model.fit(train_data.drop(columns=['timestamp', target_variable]),
              train_data[target_variable])

    # Validar
    val_accuracy = model.score(val_data.drop(columns=['timestamp', target_variable]),
                                val_data[target_variable])

    logger.info(f"Validation accuracy: {val_accuracy:.3f}")

    return model
```

**Impacto**: **Muy alto** – Previene overfitting falso.

**Prioridad**: **P0 – INMEDIATA**

---

#### **Acción M3-005: Calibrar pesos del SignalArbitrator empíricamente**

**Qué hacer**:
1. Grid search para encontrar pesos óptimos:
```python
# tools/calibrate_arbitrator_weights.py
def calibrate_arbitrator_weights(historical_signals, outcomes):
    """
    Encuentra pesos óptimos del arbitrator via grid search.

    Args:
        historical_signals: Señales pasadas con scores de cada componente
        outcomes: PnL real de cada señal

    Returns:
        Pesos óptimos que maximizan Sharpe
    """
    best_sharpe = -np.inf
    best_weights = None

    # Grid search
    for w_quality in np.arange(0.30, 0.50, 0.05):
        for w_perf in np.arange(0.15, 0.35, 0.05):
            for w_regime in np.arange(0.10, 0.30, 0.05):
                for w_rr in np.arange(0.05, 0.20, 0.05):
                    w_timing = 1.0 - (w_quality + w_perf + w_regime + w_rr)

                    if w_timing < 0 or w_timing > 0.15:
                        continue

                    weights = {
                        'quality': w_quality,
                        'performance': w_perf,
                        'regime': w_regime,
                        'risk_reward': w_rr,
                        'timing': w_timing,
                    }

                    # Simular selección con estos pesos
                    sharpe = simulate_arbitrator_with_weights(historical_signals, outcomes, weights)

                    if sharpe > best_sharpe:
                        best_sharpe = sharpe
                        best_weights = weights

    logger.info(f"Best weights: {best_weights} (Sharpe: {best_sharpe:.3f})")
    return best_weights
```

2. Documentar en `docs/ARBITRATOR_WEIGHT_CALIBRATION.md`:
```markdown
## Calibración Histórica

Período: 2023-01-01 a 2024-12-31
Pesos óptimos encontrados:
- Quality: 38%
- Performance: 28%
- Regime: 18%
- Risk-Reward: 11%
- Timing: 5%

Sharpe resultante: 1.82 (vs 1.54 con pesos anteriores).

Próxima recalibración: 2025-04-01.
```

**Impacto**: **Medio-Alto** – Pesos derivados empíricamente.

**Prioridad**: **P1 – ALTA**

---

#### **Acción M3-006: Implementar actualización dinámica de fit_matrix**

**Qué hacer**:
1. Recalibrar fit_matrix cada 30 días basado en performance real:
```python
# tools/calibrate_regime_fit.py
def recalibrate_regime_fit_matrix(trade_history):
    """
    Recalibra fit_matrix basado en performance real de estrategias por régimen.

    Args:
        trade_history: Historial de trades con régimen y estrategia

    Returns:
        Matriz actualizada
    """
    # Agrupar por (régimen, estrategia)
    grouped = trade_history.groupby(['regime', 'strategy']).agg({
        'pnl_r': 'mean',
        'win_rate': 'mean',
        'sharpe': 'mean',
    })

    # Normalizar scores por régimen
    fit_matrix = {}

    for regime in grouped.index.get_level_values('regime').unique():
        regime_data = grouped.loc[regime]

        # Normalizar sharpe a [0, 1]
        max_sharpe = regime_data['sharpe'].max()
        min_sharpe = regime_data['sharpe'].min()

        fit_scores = {}
        for strategy in regime_data.index:
            sharpe = regime_data.loc[strategy, 'sharpe']
            normalized = (sharpe - min_sharpe) / (max_sharpe - min_sharpe + 1e-6)
            fit_scores[strategy] = normalized

        fit_matrix[regime] = fit_scores

    return fit_matrix
```

2. Actualizar fit_matrix automáticamente:
```python
# Ejecutar mensualmente
new_fit_matrix = recalibrate_regime_fit_matrix(trade_history_last_12_months)

# Validar cambios no son demasiado abruptos
validate_fit_matrix_changes(old_fit_matrix, new_fit_matrix, max_delta=0.15)

# Aplicar
update_brain_fit_matrix(new_fit_matrix)
```

**Impacto**: **Medio** – Fit matrix se adapta a realidad de mercado.

**Prioridad**: **P1 – MEDIA**

---

#### **Acción M3-007: Monitoreo continuo de modelos ML**

**Qué hacer**:
1. Implementar `src/monitoring/ml_model_monitor.py`:
```python
class MLModelMonitor:
    def __init__(self, model):
        self.model = model
        self.metrics_history = deque(maxlen=1000)

    def track_prediction(self, features, prediction, actual_outcome):
        """Registra predicción y outcome real."""
        self.metrics_history.append({
            'timestamp': datetime.now(),
            'prediction': prediction,
            'actual': actual_outcome,
            'correct': (prediction > 0.5) == (actual_outcome > 0),
        })

    def get_rolling_accuracy(self, window=100):
        """Accuracy en últimas N predicciones."""
        recent = list(self.metrics_history)[-window:]
        correct = sum(1 for m in recent if m['correct'])
        return correct / len(recent) if recent else 0.0

    def detect_degradation(self, baseline_accuracy=0.65, threshold=0.10):
        """Detecta si modelo se ha degradado."""
        current = self.get_rolling_accuracy()

        if current < baseline_accuracy * (1 - threshold):
            logger.critical(f"MODEL DEGRADATION: Accuracy {current:.3f} < {baseline_accuracy * (1 - threshold):.3f}")
            return True

        return False
```

2. Dashboard de métricas:
   - Panel Grafana con:
     - Accuracy rolling 100 predicciones.
     - Precision/Recall.
     - Calibration plot.

**Impacto**: **Medio** – Detección temprana de degradación.

**Prioridad**: **P1 – MEDIA**

---

#### **Acción M3-008: Separar research/production en ML pipeline**

**Qué hacer**:
1. Estructura de directorios:
```
models/
  research/
    experiments/
      exp_001_randomforest/
        config.yaml
        model.pkl
        metrics.json
      exp_002_gradientboosting/
        ...
  validation/
    validated_models/
      v1.0_randomforest/
        model.pkl
        validation_report.md
  production/
    v1.2_randomforest/
      model.pkl
      deployment_date.txt
      performance_live.json
```

2. Proceso de promoción:
```
RESEARCH → VALIDATION → PRODUCTION

1. Research: Experimentar con modelos.
2. Validation: Backtest riguroso + out-of-sample.
3. Production: Deploy solo si pasa validación.
```

3. Implementar versionado:
```python
# src/ml/model_registry.py
class ModelRegistry:
    def register_model(self, model, version, stage):
        """
        Registra modelo en registry.

        Args:
            model: Modelo entrenado
            version: e.g., 'v1.3'
            stage: 'RESEARCH', 'VALIDATION', 'PRODUCTION'
        """
        path = f"models/{stage.lower()}/{version}_model.pkl"
        pickle.dump(model, open(path, 'wb'))

        logger.info(f"Model {version} registered in stage {stage}")

    def promote_model(self, version, from_stage, to_stage):
        """Promociona modelo de stage a stage."""
        # Validar que cumple criterios
        if to_stage == 'PRODUCTION':
            assert self.validate_production_readiness(version)

        # Copiar modelo
        shutil.copy(f"models/{from_stage.lower()}/{version}_model.pkl",
                    f"models/{to_stage.lower()}/{version}_model.pkl")

        logger.info(f"Model {version} promoted: {from_stage} → {to_stage}")
```

**Impacto**: **Medio** – Previene modelos experimentales en producción.

**Prioridad**: **P1 – MEDIA**

---

#### **Acción M3-009: Implementar circuit breaker para brain-layer**

**Qué hacer**:
1. Detectores de comportamiento anómalo:
```python
# src/safety/brain_circuit_breaker.py
class BrainCircuitBreaker:
    def check_rejection_rate(self, window_minutes=60):
        """Detecta si brain-layer rechaza demasiadas señales."""
        recent_signals = get_signals_last_n_minutes(window_minutes)

        if not recent_signals:
            return True

        rejection_rate = sum(1 for s in recent_signals if not s['approved']) / len(recent_signals)

        if rejection_rate > 0.90:
            logger.critical(f"CIRCUIT BREAKER: Rejection rate {rejection_rate:.1%} > 90%")
            self.trigger_circuit_breaker("high_rejection_rate")
            return False

        return True

    def check_low_quality_approvals(self):
        """Detecta si brain-layer aprueba señales de muy baja calidad."""
        recent_approvals = get_approved_signals_last_hour()

        low_quality_count = sum(1 for s in recent_approvals if s['quality_score'] < 0.30)

        if low_quality_count > 5:
            logger.critical(f"CIRCUIT BREAKER: {low_quality_count} low-quality signals approved")
            self.trigger_circuit_breaker("low_quality_approvals")
            return False

        return True

    def trigger_circuit_breaker(self, reason):
        """Activa circuit breaker y pasa a modo manual."""
        logger.critical(f"🚨 CIRCUIT BREAKER TRIGGERED: {reason}")

        # Desactivar brain-layer
        set_brain_mode('MANUAL')

        # Enviar alerta
        send_alert(f"Brain-layer circuit breaker: {reason}")

        # Usar último snapshot bueno
        rollback_to_last_good_snapshot()
```

2. Ejecutar checks cada 5 minutos:
```python
# En main loop
if not brain_circuit_breaker.check_rejection_rate():
    # Brain-layer desactivado, usar configuración manual
```

**Impacto**: **Medio-Alto** – Previene daños por comportamiento anómalo.

**Prioridad**: **P1 – ALTA**

---

#### **Acción M3-010: Limpiar comentarios y añadir docstrings**

**Qué hacer**:
1. Eliminar tono defensivo:
```python
# ANTES
"""
This is NOT a simple signal combiner. This is an advanced orchestration layer
that thinks at the PORTFOLIO level, not individual trade level.
"""

# DESPUÉS
"""
Brain-layer: Orchestrates signal selection and parameter optimization.

Implements institutional decision framework considering:
- Portfolio-level risk management
- Multi-timeframe coherence
- Regime-aware strategy selection
- ML-based continuous learning

Based on: Lo & MacKinlay (1997), López de Prado (2018).
"""
```

2. Añadir docstrings completos:
```python
def _score_signal(self, signal: Dict, market_context: Dict, regime: str) -> float:
    """
    Calcula score de señal usando modelo multi-factor institucional.

    Args:
        signal: Señal candidata con metadata y features
        market_context: Contexto de mercado actual (VPIN, OFI, depth, etc.)
        regime: Régimen de mercado identificado

    Returns:
        Score [0.0, 1.0] donde 1.0 = señal de máxima calidad

    Raises:
        ValueError: Si signal no contiene campos requeridos
    """
```

**Impacto**: **Bajo** – Mejora profesionalismo.

**Prioridad**: **P2 – BAJA**

---

### PLAN DE ACCIÓN PRIORIZADO – MANDATO 3

**Fase inmediata (Semana 1)**:
1. **M3-001**: Crear `BRAIN_LAYER_GOVERNANCE.md` con áreas prohibidas.
2. **M3-002**: Implementar challenger model y validación rigurosa.
3. **M3-003**: Rollback mechanism automático.
4. **M3-004**: Prevenir data leakage con time-series split estricto.

**Fase corto plazo (Semana 2-3)**:
5. **M3-005**: Calibrar pesos del arbitrator empíricamente.
6. **M3-006**: Actualización dinámica de fit_matrix.
7. **M3-009**: Circuit breaker para brain-layer.

**Fase medio plazo (Mes 1)**:
8. **M3-007**: Monitoreo continuo de modelos ML.
9. **M3-008**: Separar research/production en ML pipeline.
10. **M3-010**: Limpiar comentarios y docstrings.

---

### VEREDICTO FINAL – MANDATO 3

**Estado**: ⚠️ **CAJA NEGRA PELIGROSA SIN GOVERNANCE – NO APTO PARA PRODUCCIÓN**

**Logros**:
- ✅ SignalArbitrator implementado con scoring multi-factor.
- ✅ ML Adaptive Engine con learning loop.
- ✅ Intento de formalización institucional.

**Fallas institucionales**:
- ❌ **Sin límites claros** → brain-layer puede anular risk caps.
- ❌ **Sin challenger model** → modelo ML no validado.
- ❌ **Sin rollback mechanism** → ajustes malos son irreversibles.
- ❌ **Riesgo de data leakage** → overfitting falso.
- ❌ **Pesos hardcoded sin justificación** → subóptimos.

**Recomendación**:
**NO ACTIVAR BRAIN-LAYER EN PRODUCCIÓN** hasta completar:
- M3-001 (Governance estricta).
- M3-002 (Challenger model).
- M3-003 (Rollback mechanism).
- M3-004 (Prevenir data leakage).
- M3-009 (Circuit breaker).

**Modo de operación recomendado**:
- **Fase 1**: Brain-layer en **modo de observación** (sugiere pero NO ejecuta).
- **Fase 2**: Brain-layer en **paper trading** (ejecuta en demo, NO en real).
- **Fase 3**: Brain-layer en **producción limitada** (solo arbitration, NO parameter tuning).
- **Fase 4**: Brain-layer en **producción completa** (tras 6 meses de validación).

**Alternativa conservadora**:
- Usar brain-layer SOLO para signal arbitration (seleccionar entre conflictos).
- **Desactivar** ML Adaptive Engine hasta validación completa.
- Ajustes de parámetros 100% manuales con aprobación humana.

---

**FIN AUDITORÍA MANDATO 3**

---

## MANDATO 4 – AUDITORÍA INSTITUCIONAL: RISK ENGINE + QUALITY SCORE

**Alcance**: QualityScorer, StatisticalCircuitBreaker, InstitutionalRiskManager, position sizing, exposure controls, drawdown limits.

**Archivos analizados**:
- `src/core/risk_manager.py` (708 líneas)
- `src/risk_management.py` (164 líneas)
- `src/core/brain.py` (arbitration scoring)

**Fecha**: 2025-11-13
**Auditor**: Senior Quant Auditor (institucional)

---

### RIESGOS / DEBILIDADES DETECTADAS

#### P0 (CRÍTICO)

**P0-013: Quality Score con pesos hardcoded SIN calibración empírica**

**Evidencia**:
```python
# risk_manager.py:38-44
self.weights = {
    'mtf_confluence': 0.40,
    'structure_alignment': 0.25,
    'order_flow': 0.20,
    'regime_fit': 0.10,
    'strategy_performance': 0.05,
}
```

**Problemas**:
- Pesos completamente arbitrarios (¿por qué MTF 40% y no 35%?)
- **NO existe documento** que justifique estos pesos con backtesting
- **NO hay validación out-of-sample** de que estos pesos maximizan Sharpe o minimizan drawdown
- **NO hay mecanismo** de recalibración periódica

**Impacto**:
- Quality Score es la columna vertebral del position sizing (0.33% → 1.0% risk)
- Si los pesos están mal, TODAS las posiciones están mal dimensionadas
- Pérdida potencial: **10-30% de rentabilidad anual** por mal sizing

**Severidad**: **P0 – CRÍTICO**

---

**P0-014: Correlaciones de símbolos hardcoded SIN actualización dinámica**

**Evidencia**:
```python
# risk_manager.py:565-573
correlations = {
    'EURUSD.pro_GBPUSD.pro': 0.85,
    'AUDUSD.pro_NZDUSD.pro': 0.92,
    'EURJPY.pro_GBPJPY.pro': 0.88,
    # ...
}
# Correlaciones estáticas desde... ¿cuándo?
```

**Problemas**:
- Correlaciones fijas, probablemente calculadas hace meses/años
- **NO hay refresh periódico** (diario, semanal, mensual)
- **NO hay detección de cambio de régimen** de correlación
- En crisis (2008, COVID, SVB 2023), correlaciones cambian radicalmente:
  - EURUSD-GBPUSD puede ir de 0.85 → 0.30 en 48 horas
  - Oro-DXY puede invertir correlación de -0.65 → +0.40

**Impacto**:
- Exposure correlated check (línea 520-525) usa correlaciones incorrectas
- Puedes tener 10% exposure real cuando crees que tienes 5%
- En crisis: **riesgo de margin call** por correlaciones no detectadas

**Severidad**: **P0 – CRÍTICO**

---

**P0-015: Exposure limits verifican >= permitiendo exceder límites**

**Evidencia**:
```python
# risk_manager.py:495
if total_exposure + proposed_risk_pct >= self.max_total_exposure_pct:
    return {'approved': False, ...}

# Problema: NO hay buffer de seguridad
# Si total = 5.9%, max = 6.0%, proposed = 0.5% → OK
# Pero llega a 6.4% sin margen para slippage
```

**Problema**:
- Usa `>=` correctamente, pero permite exactamente el límite
- NO hay margen de seguridad para slippage, gap, volatilidad
- Institucional: si límite es 6%, parar en 5.4% (buffer 10%)

**Impacto**:
- Edge case: puede permitir posiciones que llevan exposure al límite exacto
- En volatilidad extrema (gap overnight), puede exceder límites reales

**Severidad**: **P0 – CRÍTICO** (por falta de buffer)

---

**P0-016: División por zero en position sizing (FIX frágil)**

**Evidencia**:
```python
# risk_manager.py:459-463
denominator = (1.0 - self.min_quality_score)
if denominator == 0:
    base_size = self.max_risk_pct
else:
    base_size = self.min_risk_pct + (quality_score - self.min_quality_score) * \
               (self.max_risk_pct - self.min_risk_pct) / denominator
```

**Problema**:
- Si min_quality_score = 1.0 (configuración errónea), denominator = 0
- El código tiene FIX, pero NO hay validación de config al inicio
- ¿Por qué permitir min_quality_score = 1.0 en primer lugar?

**Impacto**:
- Si pasa config inválida, todas las posiciones serán max_risk_pct (1.0%)
- NO detecta error hasta runtime

**Severidad**: **P0 – CRÍTICO** (falta validación de config)

---

#### P1 (IMPORTANTE)

**P1-013: Statistical Circuit Breaker con threshold arbitrario (z=2.5)**

**Evidencia**:
```python
# risk_manager.py:147
self.z_score_threshold = config.get('circuit_breaker_z_score', 2.5)  # 2.5σ = 99.4% confidence
```

**Problema**:
- z = 2.5 es threshold común en ciencia, pero **NO necesariamente óptimo para trading**
- Permite pérdidas hasta 2.5 desviaciones estándar (99.4% confidence)
- En estrategias de alta frecuencia, puede ser demasiado permisivo
- NO hay documento que justifique 2.5 vs 2.0 o 3.0

**Impacto**:
- Circuit breaker puede activarse demasiado tarde (después de -5% drawdown en vez de -3%)

**Severidad**: **P1 – IMPORTANTE**

---

**P1-014: Daily PnL reset con race condition potencial**

**Evidencia**:
```python
# risk_manager.py:675-679
from datetime import datetime
today = datetime.now().date()
if not hasattr(self, '_last_pnl_date') or self._last_pnl_date != today:
    self.daily_pnl = 0.0
    self._last_pnl_date = today
```

**Problema**:
- Si dos threads cierran posiciones exactamente a medianoche
- Thread A: lee _last_pnl_date = ayer, resetea
- Thread B: lee _last_pnl_date = hoy, NO resetea
- Resultado: daily_pnl puede acumular trades incorrectamente

**Impacto**:
- Daily loss limit (3%) puede no detectar pérdida real

**Severidad**: **P1 – IMPORTANTE**

---

**P1-015: Lot size calculation usa aproximación (NO precisa)**

**Evidencia**:
```python
# risk_manager.py:624
lot_size = risk_amount / (stop_distance_pips * 10)  # Approximate
```

**Problema**:
- Comentario dice "Approximate"
- Valor de pip = $10 correcto para EURUSD 1 lote
- Pero **NO correcto** para XAUUSD, BTCUSD, índices

**Impacto**:
- Position sizing incorrecto para instrumentos no-forex
- Puede arriesgar 2% real cuando crees arriesgar 0.5%

**Severidad**: **P1 – IMPORTANTE**

---

**P1-016: NO validación de stop_loss razonable**

**Evidencia**:
```python
# risk_manager.py:428-431
entry_price = signal['entry_price']
stop_loss = signal['stop_loss']
# NO valida si stop_loss es razonable
```

**Problema**:
- Acepta stop_loss sin verificar:
  - ¿Demasiado cerca? (< 5 pips → ruido)
  - ¿Demasiado lejos? (> 500 pips → irracional)
  - ¿Coherente con ATR?

**Impacto**:
- Stop de 0.1 pips → lot size gigante → margin call
- Stop de 5000 pips → lot size minúsculo

**Severidad**: **P1 – IMPORTANTE**

---

**P1-017: Strategy performance lookback fijo (30 trades) sin adaptación temporal**

**Evidencia**:
```python
# risk_manager.py:60
self.strategy_performance: Dict[str, deque] = defaultdict(lambda: deque(maxlen=30))
```

**Problema**:
- Lookback de 30 trades fijo para TODAS las estrategias
- Estrategia A: 10 trades/día → 3 días
- Estrategia B: 1 trade/semana → 30 semanas!
- NO es comparable temporalmente

**Impacto**:
- Performance score sesgado entre estrategias de diferentes frecuencias

**Severidad**: **P1 – IMPORTANTE**

---

#### P2 (MENOR)

**P2-010: Signal history con límite 1000 puede perder datos**

**Problema**: deque(maxlen=1000) pierde historia en alta frecuencia

**Severidad**: **P2**

---

**P2-011: Volatility regime adjustment con multiplicadores fijos**

**Problema**: Reducción 30% en HIGH vol, sin proporcionalidad a qué tan extrema es

**Severidad**: **P2**

---

**P2-012: NO logging de rechazos por quality score**

**Problema**: Señales rechazadas NO se registran en logs

**Severidad**: **P2**

---

### RESUMEN DE RIESGOS

| Severidad | Cantidad | IDs |
|-----------|----------|-----|
| **P0 (Crítico)** | 4 | P0-013, P0-014, P0-015, P0-016 |
| **P1 (Importante)** | 5 | P1-013, P1-014, P1-015, P1-016, P1-017 |
| **P2 (Menor)** | 3 | P2-010, P2-011, P2-012 |
| **TOTAL** | **12** | |

---

### MEJORAS INSTITUCIONALES RECOMENDADAS

#### Acción M4-001: Calibración empírica de Quality Score weights

**Qué hacer**: Optimizar pesos del Quality Score usando backtesting histórico para maximizar Sharpe ratio.

**Código ejemplo**:
```python
# research/quality_score_calibration.py
from scipy.optimize import minimize

def calibrate_quality_weights(historical_signals_df):
    """
    Calibra pesos usando time-series split optimization.

    Input: DataFrame con columnas:
      - mtf_confluence, structure_alignment, order_flow, regime_fit, strategy_performance
      - actual_pnl_R (resultado real del trade)
    """

    def objective(weights):
        # Calcular quality score con pesos propuestos
        quality = (signals['mtf_confluence'] * weights[0] +
                  signals['structure_alignment'] * weights[1] +
                  signals['order_flow'] * weights[2] +
                  signals['regime_fit'] * weights[3] +
                  signals['strategy_performance'] * weights[4])

        # Filtrar señales quality > 0.60
        filtered = signals[quality >= 0.60]

        # Sharpe de señales aceptadas
        sharpe = filtered['actual_pnl_R'].mean() / filtered['actual_pnl_R'].std() * np.sqrt(252)
        return -sharpe  # Minimizar negativo

    # Optimizar
    result = minimize(objective, [0.40, 0.25, 0.20, 0.10, 0.05],
                     method='SLSQP',
                     constraints=[{'type': 'eq', 'fun': lambda w: sum(w) - 1.0}],
                     bounds=[(0, 1)] * 5)

    return result.x
```

**Impacto**: +10-25% Sharpe ratio
**Esfuerzo**: 3-5 días
**Prioridad**: **P0**

---

#### Acción M4-002: Correlaciones dinámicas con rolling windows

**Qué hacer**: Calcular correlaciones diariamente con ventana rolling de 60 días.

**Código**:
```python
# src/core/dynamic_correlations.py
class DynamicCorrelationMonitor:
    def __init__(self, lookback_days=60):
        self.lookback_days = lookback_days
        self.price_history = {}

    def update_prices(self, symbol, price, timestamp):
        """Actualiza histórico de precios."""
        if symbol not in self.price_history:
            self.price_history[symbol] = pd.Series()

        self.price_history[symbol][timestamp] = price

        # Mantener solo lookback_days
        cutoff = timestamp - timedelta(days=self.lookback_days)
        self.price_history[symbol] = self.price_history[symbol][
            self.price_history[symbol].index >= cutoff
        ]

    def calculate_correlations(self):
        """Calcula matriz de correlación rolling."""
        prices_df = pd.DataFrame(self.price_history)
        returns = prices_df.pct_change().dropna()
        return returns.corr()
```

**Impacto**: Reduce riesgo margin call en crisis
**Esfuerzo**: 2-3 días
**Prioridad**: **P0**

---

#### Acción M4-003: Exposure limits con buffer de seguridad

**Qué hacer**: Agregar buffer 10% a límites (si límite 6%, parar en 5.4%).

```python
# src/core/risk_manager.py
self.exposure_buffer_pct = 0.10  # 10% buffer

def _check_exposure_limits(self, signal, proposed_risk_pct):
    effective_limit = self.max_total_exposure_pct * (1.0 - self.exposure_buffer_pct)

    if total_exposure + proposed_risk_pct > effective_limit:
        return {'approved': False, 'reason': 'Exposure limit with buffer'}
```

**Impacto**: Margen de seguridad para slippage
**Esfuerzo**: 1 día
**Prioridad**: **P0**

---

#### Acción M4-004: Config validation al inicio

```python
# src/core/config_validator.py
class RiskConfigValidator:
    @staticmethod
    def validate(config):
        errors = []

        min_q = config.get('min_quality_score', 0.60)
        if min_q >= 1.0 or min_q < 0:
            errors.append(f"min_quality_score inválido: {min_q}")

        if errors:
            raise ValueError(f"Config inválida: {errors}")
```

**Impacto**: Previene crashes por config errónea
**Esfuerzo**: 1 día
**Prioridad**: **P0**

---

#### Acción M4-005: Lot size calculation precisa por instrumento

**Qué hacer**: Usar specs de instrumento para cálculo exacto.

**Impacto**: Sizing preciso
**Esfuerzo**: 2 días
**Prioridad**: **P1**

---

#### Acción M4-006: Validación de stop loss razonable

**Qué hacer**: Validar stop entre 1.0-5.0 ATR.

```python
def _validate_stop_loss(self, signal, market_context):
    atr = market_context['atr'][signal['symbol']]
    stop_distance = abs(signal['entry_price'] - signal['stop_loss'])
    stop_atr = stop_distance / atr

    if stop_atr < 1.0:
        return False, "Stop demasiado cerca (<1 ATR)"
    if stop_atr > 5.0:
        return False, "Stop demasiado lejos (>5 ATR)"

    return True, "OK"
```

**Impacto**: Previene bugs de estrategias
**Esfuerzo**: 1 día
**Prioridad**: **P1**

---

#### Acción M4-007: Strategy performance con lookback temporal

**Qué hacer**: Cambiar de 30 trades a 30 días.

**Impacto**: Performance score coherente
**Esfuerzo**: 1 día
**Prioridad**: **P1**

---

#### Acción M4-008: Logging de rechazos

**Qué hacer**: Log todas las señales rechazadas para análisis.

**Impacto**: Facilita debugging
**Esfuerzo**: 1 día
**Prioridad**: **P2**

---

#### Acción M4-009: Volatility adjustment proporcional

**Qué hacer**: Ajuste proporcional a vol_ratio (no fijo).

**Impacto**: Sizing más fino en volatilidad extrema
**Esfuerzo**: 1 día
**Prioridad**: **P2**

---

#### Acción M4-010: Thread-safe daily PnL reset

**Qué hacer**: Usar threading.Lock para reset de daily_pnl.

**Impacto**: Previene race condition
**Esfuerzo**: 0.5 días
**Prioridad**: **P1**

---

### PLAN DE ACCIÓN PRIORIZADO

#### FASE 1: Riesgos P0 (3-4 semanas)
- M4-001: Calibración Quality Score (5 días)
- M4-002: Correlaciones dinámicas (3 días)
- M4-003: Exposure buffer (1 día)
- M4-004: Config validation (1 día)
- Testing (2 días)

#### FASE 2: Riesgos P1 (2 semanas)
- M4-005 a M4-007, M4-010 (5 días)
- Testing (2 días)

#### FASE 3: Mejoras P2 (1 semana)
- M4-008, M4-009 (2 días)
- Documentación (1 día)

---

### VEREDICTO FINAL

**Estado**: ⚠️ **PARCIALMENTE APTO** para producción

**Logros**:
- ✅ Statistical circuit breaker basado en SPC
- ✅ Multi-factor quality scoring
- ✅ Dynamic position sizing
- ✅ Multi-dimensional exposure control
- ✅ Fix de bugs críticos (division by zero, exposure checks)

**Fallas críticas**:
- ❌ **Quality Score SIN calibración empírica** (P0-013)
- ❌ **Correlaciones hardcoded SIN actualización** (P0-014)
- ❌ **NO buffer de seguridad en exposure limits** (P0-015)
- ❌ **NO validación de configuración** (P0-016)

**Riesgo de producción SIN fixes**:
- Probabilidad **40%** de position sizing subóptimo (pérdida 10-25% Sharpe)
- Probabilidad **15%** de margin call en crisis
- Probabilidad **5%** de crash por config inválida

**Recomendación**:
1. **NO LANZAR** sin M4-001 (calibración Quality Score)
2. **NO LANZAR** sin M4-002 (correlaciones dinámicas)
3. Implementar M4-003, M4-004 antes de producción

**Timeline para producción**: 4-6 semanas (FASES 1+2 completas)

**FIN AUDITORÍA MANDATO 4**
