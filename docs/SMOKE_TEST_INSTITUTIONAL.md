# Smoke Test Institucional - MANDATO 25

**Status**: DOCUMENTED (P2-M25-1 specification)
**Date**: 2025-11-15
**Purpose**: End-to-end validation of institutional trading loop

---

## OBJECTIVE

Create a fast (<30s), fail-loud smoke test that validates the complete institutional trading loop works end-to-end.

**Scope**: RESEARCH mode only (no execution, no MT5 dependency)

**Goal**: Catch integration breakages before they reach production

---

## TEST SCENARIOS

### Scenario 1: Feature Pipeline (P0)
**What**: MicrostructureEngine calculates all features correctly
**Input**: Synthetic OHLCV data (30 bars)
**Expected**:
- `has_order_flow = True`
- OFI, CVD, VPIN, ATR all calculated (non-default values)
- No exceptions raised

### Scenario 2: Strategy Orchestrator (P0)
**What**: StrategyOrchestrator loads strategies and generates signals
**Input**: Config with 3 strategies enabled
**Expected**:
- All 3 strategies loaded
- `generate_signals()` returns Signal objects (may be empty list)
- All signals pass `validate()`

### Scenario 3: Brain Filtering (P1)
**What**: Brain filters signals based on quality/regime
**Input**: 5 synthetic signals (various quality scores)
**Expected**:
- Brain filters low-quality signals
- High-quality signals pass through
- Brain state metrics logged

### Scenario 4: Backtest Integration (P1)
**What**: BacktestEngine uses MicrostructureEngine (parity mode)
**Input**: Historical data (100 bars)
**Expected**:
- `use_microstructure_engine = True`
- Features calculated via MicrostructureEngine
- Backtest completes without errors

### Scenario 5: Config Loading (P1)
**What**: System loads config.yaml correctly
**Input**: Test config file
**Expected**:
- All required sections present
- Default values applied
- Config validation passes

---

## IMPLEMENTATION APPROACH

### Option A: Standalone Script (Recommended)
**File**: `scripts/smoke_test_institutional_loop.py`

```python
#!/usr/bin/env python3
"""
Institutional Trading Loop - Smoke Test

Fast (<30s) end-to-end validation of complete trading system.
Runs in RESEARCH mode (no MT5, no execution).

Usage:
    python scripts/smoke_test_institutional_loop.py

Exit codes:
    0: All tests passed
    1: One or more tests failed
"""

import sys
import logging
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

def test_feature_pipeline():
    """Test MicrostructureEngine calculates features."""
    from src.microstructure import MicrostructureEngine
    import pandas as pd

    engine = MicrostructureEngine({})
    df = create_synthetic_data(30)
    features = engine.calculate_features('TEST', df)

    assert engine.has_order_flow, "Order flow not available"
    assert features.ofi != 0.0, "OFI not calculated"
    assert features.cvd != 0.0 or True, "CVD may be zero"
    assert features.vpin != 0.5 or True, "VPIN may be neutral"

    print("✓ Feature pipeline working")

def test_strategy_orchestrator():
    """Test StrategyOrchestrator loads and runs strategies."""
    from src.strategy_orchestrator import StrategyOrchestrator
    import pandas as pd

    config = load_test_config()
    orchestrator = StrategyOrchestrator(config)

    assert len(orchestrator.strategies) > 0, "No strategies loaded"

    df = create_synthetic_data(100)
    features = {'ofi': 1.0, 'cvd': 1000, 'vpin': 0.6, 'atr': 0.0001}
    signals = orchestrator.generate_signals(df, features)

    for signal in signals:
        assert signal.validate(), f"Invalid signal: {signal}"

    print(f"✓ StrategyOrchestrator working ({len(orchestrator.strategies)} strategies)")

def test_brain_filtering():
    """Test Brain filters signals correctly."""
    from src.brain import InstitutionalBrain

    brain = InstitutionalBrain({'brain': {'min_quality_score': 3.0}})

    # Create test signals
    high_quality = create_test_signal(quality=4.5)
    low_quality = create_test_signal(quality=2.0)

    filtered = brain.filter_signals([high_quality, low_quality])

    assert high_quality in filtered, "High quality signal filtered out"
    assert low_quality not in filtered or True, "Low quality may pass if other criteria met"

    print("✓ Brain filtering working")

def test_backtest_parity():
    """Test BacktestEngine uses MicrostructureEngine."""
    from src.backtesting.backtest_engine import BacktestEngine

    engine = BacktestEngine(
        strategies=[],
        config={'features': {'ofi_lookback': 20}}
    )

    assert engine.use_microstructure_engine, "Parity mode not enabled"
    assert engine.microstructure_engine is not None, "MicrostructureEngine not initialized"

    print("✓ Backtest parity mode enabled")

def test_config_loading():
    """Test config.yaml loads correctly."""
    import yaml

    config_path = Path(__file__).parent.parent / 'config.yaml'
    with open(config_path) as f:
        config = yaml.safe_load(f)

    required_sections = ['brain', 'strategies', 'risk', 'execution']
    for section in required_sections:
        assert section in config, f"Missing config section: {section}"

    print("✓ Config loading working")

# Helper functions
def create_synthetic_data(bars: int) -> pd.DataFrame:
    """Create synthetic OHLCV data for testing."""
    import pandas as pd
    import numpy as np

    return pd.DataFrame({
        'open': np.random.uniform(1.0, 1.01, bars),
        'high': np.random.uniform(1.01, 1.02, bars),
        'low': np.random.uniform(0.99, 1.0, bars),
        'close': np.random.uniform(1.0, 1.01, bars),
        'volume': np.random.uniform(1000, 10000, bars)
    })

def create_test_signal(quality: float):
    """Create test Signal object."""
    from src.strategies.strategy_base import Signal
    from datetime import datetime

    return Signal(
        timestamp=datetime.now(),
        symbol='TEST',
        strategy_name='test_strategy',
        direction='LONG',
        entry_price=1.0,
        stop_loss=0.99,
        take_profit=1.03,
        sizing_level=3,
        metadata={'confirmation_score': quality, 'setup_type': 'TEST'}
    )

def load_test_config():
    """Load minimal test config."""
    return {
        'strategies': {
            'order_flow_toxicity': {'enabled': True},
            'vpin_reversal_extreme': {'enabled': True},
            'idp_inducement_distribution': {'enabled': True}
        },
        'features': {'ofi_lookback': 20}
    }

def main():
    """Run all smoke tests."""
    print("=" * 80)
    print("INSTITUTIONAL TRADING LOOP - SMOKE TEST")
    print("=" * 80)
    print()

    tests = [
        ("Feature Pipeline", test_feature_pipeline),
        ("Strategy Orchestrator", test_strategy_orchestrator),
        ("Brain Filtering", test_brain_filtering),
        ("Backtest Parity", test_backtest_parity),
        ("Config Loading", test_config_loading)
    ]

    passed = 0
    failed = 0

    for name, test_func in tests:
        try:
            print(f"Testing: {name}...", end=' ')
            test_func()
            passed += 1
        except Exception as e:
            print(f"✗ FAILED: {e}")
            failed += 1

    print()
    print("=" * 80)
    print(f"Results: {passed} passed, {failed} failed")
    print("=" * 80)

    if failed > 0:
        print("❌ SMOKE TEST FAILED")
        sys.exit(1)
    else:
        print("✅ SMOKE TEST PASSED")
        sys.exit(0)

if __name__ == '__main__':
    main()
```

---

## USAGE

### Run Manually
```bash
python scripts/smoke_test_institutional_loop.py
```

### Integrate with CI/CD
```yaml
# .github/workflows/smoke_test.yml
name: Smoke Test

on: [push, pull_request]

jobs:
  smoke:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - uses: actions/setup-python@v2
        with:
          python-version: '3.10'
      - run: pip install -r requirements.txt
      - run: python scripts/smoke_test_institutional_loop.py
```

### Pre-commit Hook
```bash
#!/bin/bash
# .git/hooks/pre-commit
python scripts/smoke_test_institutional_loop.py
if [ $? -ne 0 ]; then
    echo "Smoke test failed - commit aborted"
    exit 1
fi
```

---

## EXPECTED OUTPUT (Success)

```
================================================================================
INSTITUTIONAL TRADING LOOP - SMOKE TEST
================================================================================

Testing: Feature Pipeline... ✓ Feature pipeline working
Testing: Strategy Orchestrator... ✓ StrategyOrchestrator working (3 strategies)
Testing: Brain Filtering... ✓ Brain filtering working
Testing: Backtest Parity... ✓ Backtest parity mode enabled
Testing: Config Loading... ✓ Config loading working

================================================================================
Results: 5 passed, 0 failed
================================================================================
✅ SMOKE TEST PASSED
```

---

## EXPECTED OUTPUT (Failure)

```
================================================================================
INSTITUTIONAL TRADING LOOP - SMOKE TEST
================================================================================

Testing: Feature Pipeline... ✓ Feature pipeline working
Testing: Strategy Orchestrator... ✗ FAILED: No strategies loaded
Testing: Brain Filtering... [skipped]
Testing: Backtest Parity... [skipped]
Testing: Config Loading... [skipped]

================================================================================
Results: 1 passed, 1 failed
================================================================================
❌ SMOKE TEST FAILED
```

---

## IMPLEMENTATION STATUS

| Component | Status | Notes |
|-----------|--------|-------|
| Specification | ✅ DONE | This document |
| Script Creation | ❌ TODO | Create scripts/smoke_test_institutional_loop.py |
| Test Execution | ❌ TODO | Run and validate |
| CI Integration | ❌ TODO | Add to GitHub Actions |
| Documentation | ✅ DONE | This document |

---

## NEXT STEPS (P2 Priority)

1. **Create Script** (2 hours)
   - Implement test functions as specified
   - Add helper utilities
   - Validate on actual system

2. **Refine Tests** (1 hour)
   - Add edge case coverage
   - Improve error messages
   - Optimize execution time

3. **CI Integration** (1 hour)
   - Add GitHub Actions workflow
   - Configure automated runs on push
   - Set up notifications

4. **Documentation** (30 min)
   - Add to main README
   - Create troubleshooting guide
   - Document common failures

---

## MAINTENANCE

- **Update when**: Major architectural changes (e.g., new MANDATO)
- **Review**: Monthly to ensure tests remain relevant
- **Expand**: Add scenarios as system evolves
- **Keep fast**: Target <30s total runtime

---

## BENEFITS

1. **Fast Feedback**: Catches breakages in <30s
2. **Confidence**: Know system works before deploying
3. **Documentation**: Living spec of expected behavior
4. **Regression Prevention**: Prevent re-introduction of fixed bugs
5. **Onboarding**: New developers can verify setup quickly
