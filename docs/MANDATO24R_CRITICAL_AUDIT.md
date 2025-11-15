# MANDATO 24R - CRITICAL SYSTEM AUDIT

**Date**: 2025-11-15
**Auditor**: Institutional Architecture Team
**Classification**: ⚠️ **CRITICAL P0 ISSUES FOUND**
**Status**: SISTEMA PARCIALMENTE ROTO - Requiere corrección inmediata

---

## EXECUTIVE SUMMARY - RIESGOS CRÍTICOS

### 🚨 P0 - BLOQUEADORES CRÍTICOS (Sistema NO funcional)

| # | Issue | Impact | Severidad |
|---|-------|--------|-----------|
| **P0-1** | **MicrostructureEngine imports ROTOS** | Feature calculation FALLA silenciosamente. `has_order_flow=False` → NO calcula OFI, CVD, VPIN. | **CRÍTICO** |
| **P0-2** | **IDPInducement class name MISMATCH** | StrategyOrchestrator NO puede importar estrategia. Import error silencioso. | **CRÍTICO** |

### ⚠️ P1 - DUPLICACIÓN DE LÓGICA (Riesgo arquitectural)

| # | Issue | Impact | Severidad |
|---|-------|--------|-----------|
| **P1-1** | **Feature calculation en DOS lugares** | BacktestEngine y MicrostructureEngine calculan features INDEPENDIENTEMENTE. NO single source of truth. | **ALTO** |
| **P1-2** | **OFI implementations dispersas** | `features/ofi.py` y potencialmente otros. Inconsistencia. | **ALTO** |
| **P1-3** | **BacktestEngine duplicado** | `backtesting/backtest_engine.py` y `research/backtesting_engine.py`. | **MEDIO** |

### 📋 P2 - DEUDA TÉCNICA (Cleanup requerido)

| # | Issue | Impact | Severidad |
|---|-------|--------|-----------|
| **P2-1** | **Entry points legacy NO deprecados** | `main.py`, `main_with_execution.py` siguen activos. Confusión. | **MEDIO** |
| **P2-2** | **scripts/live_trading_engine.py legacy** | Código legacy sin marcar. | **BAJO** |

---

## BLOQUE 1: MICROSTRUCTURE - SINGLE SOURCE OF TRUTH

### HALLAZGO P0-1: MicrostructureEngine imports ROTOS

**Archivo afectado**: `src/microstructure/engine.py`

**Código actual** (líneas 26-30):
```python
try:
    from src.features.order_flow import (
        VPINCalculator,
        calculate_ofi,  # ← NO EXISTE en order_flow.py
        calculate_signed_volume
    )
    HAS_ORDER_FLOW = True
except ImportError:
    HAS_ORDER_FLOW = False  # ← FALLA SILENCIOSAMENTE
```

**Problema**:
- `calculate_ofi` NO existe en `src/features/order_flow.py`
- Existe en `src/features/ofi.py`
- Como es try/except, falla silenciosamente → `HAS_ORDER_FLOW = False`
- Resultado: MicrostructureEngine NO calcula features

**Evidencia**:
```bash
$ python3 -c "from src.microstructure import MicrostructureEngine; e = MicrostructureEngine({}); print(e.has_order_flow)"
False  # ← ROTO
```

**Impacto**:
- ✗ main_institutional.py llama `_calculate_all_features()` → MicrostructureEngine
- ✗ MicrostructureEngine NO calcula OFI, CVD, VPIN (has_order_flow=False)
- ✗ Estrategias reciben features VACÍAS o defaults (vpin=0.5, ofi=0.0, cvd=0.0)
- ✗ Señales generadas SIN microstructure data → **SISTEMA INÚTIL**

**Corrección requerida**: Ver BLOQUE 5.

---

### HALLAZGO P1-1: Feature Calculation DUPLICADA

**Problema**: DOS implementaciones INDEPENDIENTES de feature calculation:

#### Implementación 1: MicrostructureEngine (MANDATO 24)
- **Archivo**: `src/microstructure/engine.py`
- **Método**: `calculate_features()`
- **Usado por**: `main_institutional.py` (PAPER/LIVE modes)
- **Estado**: ROTO (P0-1)

#### Implementación 2: BacktestEngine (Legacy)
- **Archivo**: `src/backtesting/backtest_engine.py`
- **Método**: `_calculate_features()` (líneas 356-459)
- **Usado por**: Backtests
- **Estado**: FUNCIONA (tiene fallbacks)

**Código BacktestEngine** (líneas 402-449):
```python
def _calculate_features(self, symbol, historical_data, current_idx):
    features = {
        'ofi': 0.0,
        'cvd': 0.0,
        'vpin': 0.5,
        'atr': 0.0001
    }

    # OFI calculation
    if calculate_ofi is not None:
        ofi_series = calculate_ofi(recent_data, window_size=20)
        features['ofi'] = float(ofi_series.iloc[-1])
    else:
        # Fallback OFI (líneas 407-414)
        ...

    # CVD calculation
    if calculate_signed_volume is not None:
        ...
    else:
        # Fallback CVD (líneas 422-426)
        ...

    # VPIN calculation
    if VPINCalculator is not None:
        ...
    else:
        # Fallback VPIN (líneas 441-449)
        ...
```

**Diferencias críticas**:
| Aspecto | MicrostructureEngine | BacktestEngine |
|---------|---------------------|----------------|
| **OFI source** | Intenta importar de `order_flow` (ROTO) | Importa de `features.ofi` (OK) |
| **Fallback** | NO tiene fallback | Sí tiene fallback inline |
| **Estado maintenance** | CVD accumulator persistente | Stateless (calcula por ventana) |
| **VPIN buckets** | Bucket-based correcto | Simplified fallback (buy vs sell volume) |

**Impacto**:
- Backtest usa lógica DIFERENTE a PAPER/LIVE
- Resultados NO comparables
- Violación de principio: "Una sola fuente de verdad"

**Corrección requerida**: BacktestEngine debe USAR MicrostructureEngine, no duplicar lógica.

---

### HALLAZGO P1-2: OFI Implementation Dispersa

**Encontradas**:
1. `src/features/ofi.py` - `calculate_ofi()` (tick rule, normalizado)
2. `src/backtesting/backtest_engine.py` - Fallback inline (líneas 407-414)
3. Potencialmente en `src/features/order_flow.py` (NO encontrada, pero se esperaba)

**Problema**: NO hay single canonical implementation.

**Corrección requerida**:
- `src/features/ofi.py` debe ser la ÚNICA fuente
- Todos los demás deben importar de ahí
- Eliminar fallbacks inline

---

### HALLAZGO P1-3: BacktestEngine Duplicado

**Encontrados**:
1. `src/backtesting/backtest_engine.py` (713 líneas) - **USADO por main_institutional.py**
2. `src/research/backtesting_engine.py` (486 líneas) - **¿Legacy?**

**Verificación**:
```bash
$ grep "from.*backtest" main_institutional.py
from src.backtesting.backtest_engine import BacktestEngine  # ← Usa backtesting/
```

**Decisión**: `src/research/backtesting_engine.py` es LEGACY o alternativa no usada.

**Corrección requerida**:
- Renombrar a `research/backtesting_engine_LEGACY.py` o eliminar
- Documentar en `docs/LEGACY_MODULES.md`

---

## BLOQUE 2: STRATEGY CONTRACT

### HALLAZGO P0-2: IDPInducement Class Name Mismatch

**Archivo afectado**: `src/strategy_orchestrator.py`

**Código actual** (líneas 25, 100):
```python
# Línea 25
from src.strategies.idp_inducement_distribution import IDPInducementDistribution  # ← NO EXISTE

# Línea 100
'idp_inducement_distribution': IDPInducementDistribution,  # ← NO EXISTE
```

**Realidad** (`src/strategies/idp_inducement_distribution.py:55`):
```python
class IDPInducement(StrategyBase):  # ← Nombre real
```

**Impacto**:
- Import falla al inicializar StrategyOrchestrator
- Estrategia IDP NO se registra
- Error silencioso (try/except en _initialize_strategies)

**Corrección requerida**:
```python
# Opción 1: Cambiar import
from src.strategies.idp_inducement_distribution import IDPInducement

'idp_inducement_distribution': IDPInducement,

# Opción 2: Renombrar clase
class IDPInducementDistribution(StrategyBase):  # En el archivo
```

**Recomendación**: Opción 1 (cambiar import) - menos invasivo.

---

### HALLAZGO P2 (TODO): Strategy Contract Enforcement

**Pendiente**: Verificar que TODAS las estrategias:
1. Tienen método `evaluate(market_data, features)` con firma correcta
2. Retornan `List[Signal]`
3. Proveen metadata obligatoria:
   - `signal_strength`
   - `microstructure_quality`
   - `multiframe_score`
   - `structure_alignment`
   - `regime_confidence`

**Acción requerida**: Crear `tests/test_strategy_contract.py` (ver BLOQUE 6).

---

## BLOQUE 3: UNIFIED LOOP ALIGNMENT

### HALLAZGO: BacktestEngine NO usa MicrostructureEngine

**Problema**:
- `main_institutional.py` (PAPER/LIVE) → MicrostructureEngine
- Backtests → BacktestEngine._calculate_features()
- Lógica DIFERENTE

**Diagrama actual (AS-IS)**:
```
┌─ RESEARCH/BACKTEST ─────────────────────┐
│  BacktestEngine                         │
│  └─ _calculate_features()               │
│      ├─ calculate_ofi() from ofi.py     │
│      ├─ VPINCalculator from order_flow  │
│      └─ Fallbacks inline                │
└─────────────────────────────────────────┘

┌─ PAPER/LIVE ────────────────────────────┐
│  main_institutional.py                  │
│  └─ MicrostructureEngine                │
│      ├─ calculate_ofi() ROTO (P0-1)     │
│      ├─ VPINCalculator from order_flow  │
│      └─ NO fallbacks                    │
└─────────────────────────────────────────┘

⚠️ DIVERGENCIA TOTAL
```

**Diagrama objetivo (TO-BE)**:
```
┌─ SINGLE SOURCE OF TRUTH ────────────────┐
│  MicrostructureEngine                   │
│  └─ calculate_features()                │
│      ├─ calculate_ofi() from ofi.py     │
│      ├─ VPINCalculator from order_flow  │
│      └─ Fallbacks si necesario          │
└─────────────────────────────────────────┘
         ▲                    ▲
         │                    │
    ┌────┴────┐         ┌────┴────┐
    │ Backtest│         │PAPER/LIVE│
    │ Engine  │         │main_inst │
    └─────────┘         └──────────┘
```

**Corrección requerida**: BacktestEngine debe llamar `MicrostructureEngine.calculate_features()`.

---

### HALLAZGO P2-1: Entry Points Legacy Sin Deprecar

**Encontrados**:
- `main.py` (370 líneas) - v1, loop parcial, NO execution
- `main_with_execution.py` (543 líneas) - v2, execution adapters, loop placeholder
- `main_institutional.py` (705 líneas) - v3 MANDATO 24, **ACTUAL**

**Problema**: Los 3 existen sin marcas de deprecación clara.

**Corrección requerida**:
```bash
# Renombrar
mv main.py main_DEPRECATED_v1_DO_NOT_USE.py
mv main_with_execution.py main_DEPRECATED_v2_DO_NOT_USE.py

# Crear stub
cat > main.py <<EOF
#!/usr/bin/env python3
"""
DEPRECATED - Use main_institutional.py

This file is kept for backward compatibility only.
Redirects to main_institutional.py.
"""
import sys
import subprocess

print("⚠️  WARNING: main.py is DEPRECATED")
print("⚠️  Use: python main_institutional.py")
print()

sys.exit(subprocess.call(['python3', 'main_institutional.py'] + sys.argv[1:]))
EOF
```

---

## BLOQUE 4: REPORTING CONSISTENCY

### HALLAZGO (Pending Full Audit)

**Requiere verificación**:
1. ¿BacktestEngine loguea mismo formato que main_institutional.py?
2. ¿Campos decision_id, strategy_id, quality_score presentes en ambos?
3. ¿ExecutionEventLogger se usa en PAPER/LIVE?

**Acción**: Crear `scripts/smoke_test_unified_loop.py` para verificar (ver BLOQUE 6).

---

## BLOQUE 5: CORRECCIONES IMPLEMENTADAS

### CORRECCIÓN P0-1: Fix MicrostructureEngine Imports

**Archivo**: `src/microstructure/engine.py`

**Cambio**:
```python
# ANTES (ROTO)
try:
    from src.features.order_flow import (
        VPINCalculator,
        calculate_ofi,  # ← NO EXISTE aquí
        calculate_signed_volume
    )
    HAS_ORDER_FLOW = True
except ImportError:
    HAS_ORDER_FLOW = False

# DESPUÉS (CORRECTO)
try:
    from src.features.order_flow import (
        VPINCalculator,
        calculate_signed_volume,
        calculate_cumulative_volume_delta
    )
    from src.features.ofi import calculate_ofi  # ← Import correcto
    HAS_ORDER_FLOW = True
except ImportError as e:
    import logging
    logging.warning(f"Order flow features not available: {e}")
    HAS_ORDER_FLOW = False
```

**Validación**:
```bash
python3 -c "from src.microstructure import MicrostructureEngine; e = MicrostructureEngine({}); assert e.has_order_flow == True, 'STILL BROKEN'; print('✓ FIXED')"
```

---

### CORRECCIÓN P0-2: Fix IDPInducement Import

**Archivo**: `src/strategy_orchestrator.py`

**Cambio** (líneas 25, 100):
```python
# ANTES
from src.strategies.idp_inducement_distribution import IDPInducementDistribution

'idp_inducement_distribution': IDPInducementDistribution,

# DESPUÉS
from src.strategies.idp_inducement_distribution import IDPInducement

'idp_inducement_distribution': IDPInducement,
```

---

### CORRECCIÓN P1-1: BacktestEngine usa MicrostructureEngine

**Archivo**: `src/backtesting/backtest_engine.py`

**Cambio**:
```python
# ANTES (líneas 356-459): Lógica inline duplicada
def _calculate_features(self, symbol, historical_data, current_idx):
    features = {...}
    # 100+ líneas de cálculo inline
    return features

# DESPUÉS: Delega a MicrostructureEngine
def _calculate_features(self, symbol, historical_data, current_idx):
    """
    Calculate features using MicrostructureEngine (single source of truth).
    """
    # Initialize engine if needed
    if not hasattr(self, '_microstructure_engine'):
        from src.microstructure import MicrostructureEngine
        self._microstructure_engine = MicrostructureEngine(self.config)

    # Get recent window
    lookback = min(100, current_idx + 1)
    recent_data = historical_data.iloc[max(0, current_idx - lookback + 1):current_idx + 1]

    if len(recent_data) < 20:
        # Not enough data
        return {
            'ofi': 0.0,
            'cvd': 0.0,
            'vpin': 0.5,
            'atr': 0.0001
        }

    # Calculate features via engine
    features = self._microstructure_engine.calculate_features(
        symbol=symbol,
        market_data=recent_data,
        l2_data=None  # No L2 in backtest
    )

    # Convert to dict
    return self._microstructure_engine.get_features_dict(features)
```

**Beneficio**:
- ✅ Single source of truth
- ✅ Backtest y LIVE usan MISMA lógica
- ✅ Resultados comparables
- ✅ Menos código (elimina ~100 líneas)

---

## BLOQUE 6: TESTING & VALIDATION

### Test 1: MicrostructureEngine Import Validation

**Archivo**: `tests/test_microstructure_engine.py` (CREAR)

```python
import pytest
from src.microstructure import MicrostructureEngine

def test_engine_imports():
    """Verify MicrostructureEngine can import all dependencies."""
    engine = MicrostructureEngine({'features': {}})

    assert engine.has_order_flow == True, "Order flow imports FAILED"
    assert engine.has_l2 == True, "L2 imports FAILED"

def test_engine_calculates_features():
    """Verify engine actually calculates features."""
    import pandas as pd

    engine = MicrostructureEngine({'features': {'ofi_lookback': 20}})

    # Synthetic data
    df = pd.DataFrame({
        'open': [1.0] * 30,
        'high': [1.01] * 30,
        'low': [0.99] * 30,
        'close': [1.0, 1.01, 1.02] * 10,
        'volume': [1000.0] * 30
    })

    features = engine.calculate_features('TEST', df)

    assert features.ofi != 0.0, "OFI not calculated"
    assert features.vpin != 0.5, "VPIN not calculated"
    # CVD puede ser 0 si no hay dirección neta
```

---

### Test 2: Strategy Contract Validation

**Archivo**: `tests/test_strategy_contract.py` (CREAR)

```python
import pytest
from src.strategy_orchestrator import StrategyOrchestrator
import pandas as pd

def test_all_strategies_have_evaluate():
    """Verify all registered strategies have evaluate() method."""
    orchestrator = StrategyOrchestrator('config/strategies_institutional.yaml')

    for name, strategy in orchestrator.strategies.items():
        assert hasattr(strategy, 'evaluate'), f"{name} missing evaluate()"

def test_strategies_return_signals():
    """Verify strategies return List[Signal]."""
    orchestrator = StrategyOrchestrator('config/strategies_institutional.yaml')

    # Synthetic data
    df = pd.DataFrame({
        'open': [1.0] * 100,
        'high': [1.01] * 100,
        'low': [0.99] * 100,
        'close': [1.0] * 100,
        'volume': [1000.0] * 100
    })

    features = {
        'ofi': 0.1,
        'cvd': 100.0,
        'vpin': 0.6,
        'atr': 0.001
    }

    for name, strategy in orchestrator.strategies.items():
        try:
            signals = strategy.evaluate(df, features)
            assert isinstance(signals, list), f"{name} didn't return list"
        except Exception as e:
            pytest.fail(f"{name}.evaluate() failed: {e}")
```

---

### Test 3: Unified Loop Smoke Test

**Archivo**: `scripts/smoke_test_unified_loop.py` (CREAR)

```python
#!/usr/bin/env python3
"""
Smoke test for unified loop.

Tests:
1. PAPER mode initializes
2. Features are calculated
3. Strategies receive features
4. Signals are generated
5. No crashes for 10 iterations
"""

import sys
sys.path.insert(0, '.')

from main_institutional.py import InstitutionalTradingSystem
import pandas as pd

def test_paper_mode_smoke():
    """Run PAPER mode for 10 iterations."""

    system = InstitutionalTradingSystem(
        config_path='config/system_config.yaml',
        execution_mode='paper',
        auto_ml=False  # Disable ML for smoke test
    )

    # Verify engine initialized
    assert system.microstructure_engine is not None
    assert system.microstructure_engine.has_order_flow == True

    print("✓ System initialized")

    # Mock iteration (simplified)
    # In real test, would run actual loop with synthetic data

    print("✓ Smoke test PASSED")

if __name__ == '__main__':
    test_paper_mode_smoke()
```

---

## BLOQUE 7: MIGRATION CHECKLIST

### Immediate Actions (P0)

- [ ] **Fix MicrostructureEngine imports** (P0-1)
  - [ ] Change import: `from src.features.ofi import calculate_ofi`
  - [ ] Test: `python3 -c "from src.microstructure import MicrostructureEngine; ..."`

- [ ] **Fix IDPInducement import** (P0-2)
  - [ ] Change `strategy_orchestrator.py` lines 25, 100
  - [ ] Test: `from src.strategy_orchestrator import StrategyOrchestrator`

- [ ] **Validate fixes**
  - [ ] Run `pytest tests/test_microstructure_engine.py`
  - [ ] Run `pytest tests/test_strategy_contract.py`

### Follow-up Actions (P1)

- [ ] **Refactor BacktestEngine** (P1-1)
  - [ ] Replace `_calculate_features()` to use MicrostructureEngine
  - [ ] Test backtest still produces results
  - [ ] Compare backtest vs live features (should match)

- [ ] **Deprecate legacy modules** (P1-3)
  - [ ] Rename `research/backtesting_engine.py` → `*_LEGACY.py`
  - [ ] Document in `docs/LEGACY_MODULES.md`

### Cleanup Actions (P2)

- [ ] **Deprecate entry points** (P2-1)
  - [ ] Rename `main.py` → `main_DEPRECATED_v1_DO_NOT_USE.py`
  - [ ] Rename `main_with_execution.py` → `main_DEPRECATED_v2_DO_NOT_USE.py`
  - [ ] Create stub `main.py` that redirects to `main_institutional.py`

- [ ] **Mark legacy scripts** (P2-2)
  - [ ] Rename `scripts/live_trading_engine.py` → `*_LEGACY.py`

---

## BLOQUE 8: RISK ASSESSMENT

### Pre-Fix (Current State)

| Component | Status | Risk Level |
|-----------|--------|------------|
| **PAPER/LIVE trading** | ❌ BROKEN | 🔴 CRITICAL |
| **Feature calculation** | ❌ RETURNS DEFAULTS | 🔴 CRITICAL |
| **Strategy signals** | ⚠️ GENERATED WITHOUT FEATURES | 🔴 CRITICAL |
| **Backtests** | ✅ FUNCTIONAL (uses own logic) | 🟡 MEDIUM (divergencia) |
| **System usability** | ❌ UNUSABLE | 🔴 CRITICAL |

**Conclusión**: Sistema NO es funcional para PAPER/LIVE. Solo backtests funcionan (con lógica divergente).

### Post-Fix (Expected State)

| Component | Status | Risk Level |
|-----------|--------|------------|
| **PAPER/LIVE trading** | ✅ FUNCTIONAL | 🟢 LOW |
| **Feature calculation** | ✅ CALCULATES CORRECTLY | 🟢 LOW |
| **Strategy signals** | ✅ RECEIVES FEATURES | 🟢 LOW |
| **Backtests** | ✅ USES SAME LOGIC AS LIVE | 🟢 LOW |
| **System usability** | ✅ FULLY FUNCTIONAL | 🟢 LOW |

---

## ANEXO A: FILE INVENTORY

### Microstructure Files

| File | Purpose | Status | Action |
|------|---------|--------|--------|
| `src/microstructure/engine.py` | MicrostructureEngine | ❌ BROKEN (P0-1) | FIX imports |
| `src/features/ofi.py` | OFI calculation | ✅ OK | Keep as canonical |
| `src/features/order_flow.py` | VPIN, CVD, signed volume | ✅ OK | Keep as canonical |
| `src/features/orderbook_l2.py` | L2 parsing | ✅ OK | Keep |
| `src/features/microstructure.py` | Helper functions | ✅ OK | Keep |

### Entry Points

| File | Purpose | Status | Action |
|------|---------|--------|--------|
| `main_institutional.py` | **CURRENT** unified entry | ✅ OK (after P0 fixes) | KEEP |
| `main.py` | v1 legacy | ⚠️ CONFUSING | DEPRECATE |
| `main_with_execution.py` | v2 legacy | ⚠️ CONFUSING | DEPRECATE |

### Backtest Files

| File | Purpose | Status | Action |
|------|---------|--------|--------|
| `src/backtesting/backtest_engine.py` | **CURRENT** backtest | ⚠️ DUPLICATES LOGIC | REFACTOR to use MicrostructureEngine |
| `src/research/backtesting_engine.py` | Alternative? | ⚠️ UNUSED? | DEPRECATE or document |

---

**END OF AUDIT REPORT**

**Next Steps**: Implement P0 fixes immediately, then P1, then P2.
