# MANDATO 22 - ORQUESTACIÓN CALIBRACIÓN REAL + PROMOCIÓN CONFIGS

**Autor**: Claude (Arquitecto Cuant Institucional Jefe - SUBLIMINE)
**Fecha**: 2025-11-14
**Branch**: `claude/mandato22-calibracion-real-01AqipubodvYuyNtfLsBZpsx`
**Status**: ✅ **COMPLETADO**

---

## OBJETIVO

Bot\u00f3n nuclear de calibraci\u00f3n institucional.

**Requisitos**:
- Pipeline automático completo (sweep + brain + holdout + promotion)
- Validación estricta datos REALES vs SYNTHETIC
- Promoci\u00f3n configs calibradas → config/calibrated/active/
- Reporte institucional final
- ZERO riesgo inventar resultados

**Problema resuelto**: Mandatos 17-18-19-20 listos pero sin orquestaci\u00f3n unificada.

**Solución**: Un comando ejecuta todo el pipeline end-to-end.

---

## NON-NEGOTIABLES COMPLIANCE

✅ **NO inventar resultados**
- Validador rechaza SYNTHETIC data para calibración oficial
- Si solo hay sintéticos → status BLOQUEADO - NO_REAL_DATA
- Documento de status generado automáticamente
- Pipeline aborta limpiamente

✅ **Risk 0-2% intacto**
- `config/risk_limits.yaml` SIN modificar
- `RiskAllocator` intacto
- Caps de exposición sin tocar
- Calibración SOLO ajusta parámetros de estrategias

✅ **NO ATR, NO retail**
- Cero ATR nuevos
- Cero indicadores retail
- Calibración institucional pura

✅ **Backward compatible**
- Sistema funciona sin ejecutar pipeline
- Pipeline opcional, NO obligatorio
- Configs calibradas requieren activación manual

---

## ARQUITECTURA IMPLEMENTADA

### Pipeline Maestro

**scripts/run_full_calibration_pipeline.py** (450 líneas):

**7 STAGES**:

```
STAGE 1: Sanity Checks
  → smoke_test_backtest.py
  → smoke_test_calibration.py
  ✅ PASS → Continue
  ❌ FAIL → ABORT

STAGE 2: Data Validation
  → CalibrationDataValidator
  → Check REAL vs SYNTHETIC
  ✅ READY → Continue
  ❌ BLOCKED → Generate status doc, ABORT

STAGE 3: Calibration Sweep
  → run_calibration_sweep.py
  → Grid search, walk-forward validation
  ✅ SUCCESS → Continue
  ❌ FAIL → ABORT

STAGE 4: Brain Training
  → train_brain_policies_calibrated.py
  → Update brain weights/thresholds
  ✅ SUCCESS → Continue
  ❌ FAIL → ABORT

STAGE 5: Hold-out Validation
  → run_calibration_holdout.py
  → Test on unseen data
  ✅ SUCCESS → Continue
  ❌ FAIL → ABORT

STAGE 6: Config Promotion
  → Copy calibrated configs to active/
  → Generate ACTIVE_STRATEGIES_INDEX.yaml
  ✅ SUCCESS → Continue

STAGE 7: Final Report
  → Generate docs/MANDATO22_CALIBRACION_REAL_*.md
  ✅ COMPLETE
```

**Exit Codes**:
- `0` - SUCCESS or DRY_RUN_SUCCESS
- `1` - FAILED (error in any stage)
- `2` - BLOCKED (no REAL data)

### Data Validator

**src/calibration/data_validator.py** (200+ líneas):

**Clase**: `CalibrationDataValidator`

**M\u00e9todos**:
- `validate(required_symbols, timeframe)` - Main validation
- `_find_real_data_files()` - Find REAL_*.csv
- `_find_synthetic_data_files()` - Find *_SYNTHETIC.csv
- `get_available_symbols_from_real_data()` - Extract symbols

**L\u00f3gica de validación**:

```python
if len(real_files) == 0:
    if len(synthetic_files) > 0:
        return BLOCKED_ONLY_SYNTHETIC  # ❌ Solo sintéticos
    else:
        return BLOCKED_NO_DATA  # ❌ Sin datos

elif len(missing_symbols) > 0:
    return BLOCKED_NO_DATA  # ❌ Faltan símbolos

else:
    return READY  # ✅ Todos los símbolos tienen datos REALES
```

**Output**:

```
DataValidationResult:
  status: READY | BLOCKED_NO_DATA | BLOCKED_ONLY_SYNTHETIC
  real_files: List[Path]
  synthetic_files: List[Path]
  missing_symbols: List[str]
  ready_symbols: List[str]
  message: str
```

### Promotion Logic

**Config Promotion** (en pipeline maestro):

```python
def _promote_calibrated_configs(self) -> List[str]:
    # 1. Find calibrated configs in config/calibrated/
    calibrated_files = list(self.calibrated_dir.glob("*.yaml"))

    # 2. Copy to config/calibrated/active/
    for file in calibrated_files:
        dest = self.active_dir / f"{file.stem}_active.yaml"
        shutil.copy2(file, dest)
        promoted.append(dest.name)

    # 3. Generate ACTIVE_STRATEGIES_INDEX.yaml
    self._generate_active_index(promoted)

    return promoted
```

**Índice Activo** (`ACTIVE_STRATEGIES_INDEX.yaml`):

```yaml
last_calibration_date: '2025-11-14T23:00:00'
pipeline_version: '1.0-MANDATO22'
data_period:
  start: '2023-01-01'
  end: '2024-06-30'
active_configs:
  - strategy_liquidity_sweep_active.yaml
  - strategy_vpin_reversal_extreme_active.yaml
  - brain_policies_active.yaml
num_active_strategies: 2
```

**Naming Convention**:
- Pre-promotion: `strategy_{name}_calibrated.yaml`
- Post-promotion: `strategy_{name}_active.yaml`

### Directory Structure

```
config/calibrated/
├── README.md                          # Usage guide
├── active/                            # ← PROMOTED configs
│   ├── ACTIVE_STRATEGIES_INDEX.yaml
│   ├── strategy_*_active.yaml
│   └── brain_policies_active.yaml
│
└── *.yaml                            # Calibrated (pre-promotion)
```

---

## COMANDOS OPERADOR

### Caso 1: Sin Datos (BLOQUEADO)

```bash
# Ejecutar pipeline
python scripts/run_full_calibration_pipeline.py

# Output esperado:
# ❌ BLOCKED: Only SYNTHETIC data available
# MANDATO22_STATUS_20251114.md generated
# Exit code: 2
```

**Documento generado**: `docs/MANDATO22_STATUS_20251114.md`

**Contenido**:
- Razón del bloqueo
- Símbolos faltantes
- Comando para descargar datos REALES

**Acción requerida**:

```bash
# Descargar datos REALES
python scripts/download_mt5_history.py \
  --symbols EURUSD,XAUUSD,US500 \
  --timeframe M15 \
  --start 2023-01-01 \
  --end 2024-12-31

# Re-ejecutar pipeline
python scripts/run_full_calibration_pipeline.py
```

### Caso 2: Con Datos REALES (EJECUTADO)

```bash
# Dry-run (validar sin ejecutar)
python scripts/run_full_calibration_pipeline.py --dry-run

# Output esperado:
# ✅ Data validation: PASSED
# Would proceed with calibration if not dry-run
# Exit code: 0

# Ejecución completa
python scripts/run_full_calibration_pipeline.py

# Output esperado:
# STAGE 1: ✅ Sanity checks PASSED
# STAGE 2: ✅ Data validation READY
# STAGE 3: ✅ Calibration sweep COMPLETED
# STAGE 4: ✅ Brain training COMPLETED
# STAGE 5: ✅ Hold-out validation COMPLETED
# STAGE 6: ✅ Configs promoted (3 configs)
# STAGE 7: ✅ Final report generated
# Exit code: 0
```

**Documento generado**: `docs/MANDATO22_CALIBRACION_REAL_20251114.md`

**Contenido**:
- Resumen ejecutivo
- Pipeline execution (todas las stages)
- Promoted configs
- Link a log file

### Caso 3: Skip Smoke Tests (Desarrollo)

```bash
# Skip smoke tests (use with caution)
python scripts/run_full_calibration_pipeline.py --skip-smoke-tests
```

---

## REVISIÓN POST-CALIBRACIÓN

### Verificar Ejecución

```bash
# 1. Check exit code
echo $?
# 0 = SUCCESS
# 1 = FAILED
# 2 = BLOCKED

# 2. Ver log
tail -f logs/calibration/mandato22_pipeline_*.log

# 3. Ver reporte
cat docs/MANDATO22_CALIBRACION_REAL_*.md

# 4. Ver configs promovidas
ls -la config/calibrated/active/
cat config/calibrated/active/ACTIVE_STRATEGIES_INDEX.yaml
```

### Activar Configs Calibradas (MANUAL)

**IMPORTANTE**: Configs NO se activan automáticamente.

**Opción A**: Usar index

```yaml
# config/runtime_profile_paper.yaml
use_calibrated_configs: true
calibrated_config_dir: "config/calibrated/active"
```

**Opción B**: Especificar configs individuales

```yaml
# config/runtime_profile_paper.yaml
strategies:
  liquidity_sweep:
    config_file: "config/calibrated/active/strategy_liquidity_sweep_active.yaml"
```

**Opción C**: Copiar manualmente

```bash
# Backup configs actuales
cp config/strategies_institutional.yaml config/strategies_institutional_backup.yaml

# Merge calibrated params
# (manual editing required)
```

---

## ARCHIVOS CREADOS

### Código (3 archivos, ~700 líneas)

**Nuevos**:
1. `src/calibration/__init__.py` (10 líneas) - Module init
2. `src/calibration/data_validator.py` (240 líneas) - Data validator
3. `scripts/run_full_calibration_pipeline.py` (450 líneas) - Pipeline maestro

### Config (1 directorio + README)

4. `config/calibrated/` - Directory for calibrated configs
5. `config/calibrated/active/` - Directory for promoted configs
6. `config/calibrated/README.md` (180 líneas) - Usage guide

### Documentación (1 archivo)

7. `docs/MANDATO22_ORQUESTACION_CALIBRACION_20251114.md` (este archivo)

**Total**: 7 items, ~900 líneas

---

## MODIFICACIONES A EXISTENTES

**NINGUNA**.

Pipeline es 100% aditivo:
- ✅ NO modifica `risk_limits.yaml`
- ✅ NO modifica `RiskAllocator`
- ✅ NO modifica scripts de calibración existentes
- ✅ Solo orquesta scripts existentes

---

## CONFIRMACIÓN EXPLÍCITA

### risk_limits.yaml INTACTO

```bash
git diff config/risk_limits.yaml
# (no output - unchanged)
```

### NO ATR nuevos

```bash
git diff | grep -i "def.*atr"
# (no matches)
```

### NO modificación RiskAllocator

```bash
git diff src/core/risk_manager.py
# (no output - unchanged)

git diff src/core/*allocator*
# (no output - no allocator files modified)
```

### Política NO inventar resultados

```bash
# Validador rechaza SYNTHETIC
grep -A5 "BLOCKED_ONLY_SYNTHETIC" src/calibration/data_validator.py

# Output:
#   status = DataStatus.BLOCKED_ONLY_SYNTHETIC
#   message = (
#       "BLOCKED: Only SYNTHETIC data available. "
#       "Official calibration requires REAL data from MT5 or broker."
#   )
```

---

## VALIDACIÓN

### Imports Check

```bash
python -c "from src.calibration import CalibrationDataValidator; print('✅ OK')"
```

### Pipeline Help

```bash
python scripts/run_full_calibration_pipeline.py --help
```

**Output**:

```
usage: run_full_calibration_pipeline.py [-h] [--config CONFIG] [--dry-run] [--skip-smoke-tests]

MANDATO 22 - Full Calibration Pipeline

optional arguments:
  --config CONFIG        Calibration config file
  --dry-run              Validate only, do not run calibration
  --skip-smoke-tests     Skip smoke tests (use with caution)
```

### Dry-Run Test

```bash
python scripts/run_full_calibration_pipeline.py --dry-run
```

**Expected**: Either BLOCKED (no data) or DRY_RUN_SUCCESS (data available).

---

## INTEGRATION POINTS

### MANDATO 17 - Backtest Engine

**Status**: ✅ Used
- Pipeline llama `run_calibration_sweep.py`
- Sweep usa `BacktestEngine` de MANDATO 17
- NO modificaciones

### MANDATO 18R - Calibration Framework

**Status**: ✅ Orchestrated
- Pipeline ejecuta 3 scripts de MANDATO 18R:
  - `run_calibration_sweep.py`
  - `train_brain_policies_calibrated.py`
  - `run_calibration_holdout.py`
- NO modificaciones a scripts

### MANDATO 19 - Calibration Execution

**Status**: ✅ Unblocked
- MANDATO 19 estaba bloqueado (sin datos)
- MANDATO 22 valida datos antes de ejecutar
- Pipeline integra framework de MANDATO 19

### MANDATO 20 - Data Pipeline

**Status**: ✅ Validated
- `CalibrationDataValidator` valida output de MANDATO 20
- Espera datos en `data/historical/REAL/`
- Naming: `REAL_{SYMBOL}_{TF}.csv`

### MANDATO 21 - Paper Trading

**Status**: ✅ Ready
- Configs calibradas pueden usarse en paper mode
- `runtime_profile_paper.yaml` puede referenciar configs calibradas
- Manual activation (no auto)

---

## LIMITACIONES CONOCIDAS

### 1. Promotion Logic Simplificada

**Current**: Promueve TODOS los configs calibrados a active/.

**Future** (MANDATO 23):
- Parsear holdout reports
- Promover SOLO ADOPT/PILOT
- Rechazar configs con REJECT decision

### 2. Activación Manual

**Current**: Configs calibradas requieren activación manual.

**Future**:
- Flag `use_calibrated_configs` en runtime profile
- Auto-load de configs desde active/

### 3. Rollback Manual

**Current**: Rollback via git checkout manual.

**Future**:
- Comando rollback automático
- Versioning de calibrations

---

## NEXT STEPS (FUTURO)

### Enhancement 1: Smart Promotion

**Pending**:
- Parsear `HOLDOUT_REPORT.md` o JSON
- Extraer decisiones (ADOPT/PILOT/REJECT)
- Promover SOLO si ADOPT o PILOT
- Documentar razón de rechazo

### Enhancement 2: Auto-Activation

**Pending**:
- `use_calibrated_configs: true` en runtime profile
- Auto-load configs desde active/
- Merge con configs base

### Enhancement 3: Versioning

**Pending**:
- Tag calibrations con version number
- Track historical calibrations
- Easy rollback command

---

## RESUMEN EJECUTIVO

**MANDATO 22 - ORQUESTACIÓN CALIBRACIÓN REAL: ✅ COMPLETADO**

**Implementado**:
- ✅ CalibrationDataValidator (REAL vs SYNTHETIC)
- ✅ Pipeline maestro (7 stages, orchestration completa)
- ✅ Promotion logic (configs → active/)
- ✅ Directory structure (config/calibrated/active/)
- ✅ ACTIVE_STRATEGIES_INDEX.yaml
- ✅ Documentación completa

**NON-NEGOTIABLES cumplidos**:
- ✅ NO inventar resultados (SYNTHETIC = BLOCKED)
- ✅ Risk 0-2% intacto
- ✅ NO ATR
- ✅ Backward compatible

**Comandos**:

```bash
# Dry-run
python scripts/run_full_calibration_pipeline.py --dry-run

# Full execution
python scripts/run_full_calibration_pipeline.py

# Ver status
ls -la docs/MANDATO22_*
cat logs/calibration/mandato22_pipeline_*.log
```

**Confirmación**:
- ✅ risk_limits.yaml unchanged
- ✅ NO ATR added
- ✅ RiskAllocator untouched
- ✅ SYNTHETIC data blocked

**Bot\u00f3n nuclear de calibraci\u00f3n institucional operacional.**

---

**Branch**: `claude/mandato22-calibracion-real-01AqipubodvYuyNtfLsBZpsx`
**Commit**: Pending
**Fecha**: 2025-11-14
**Autor**: SUBLIMINE Institutional Trading System
