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
