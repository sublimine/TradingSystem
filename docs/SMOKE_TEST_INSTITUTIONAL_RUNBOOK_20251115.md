# Institutional Smoke Test Runbook

**Date**: 2025-11-15
**Mandate**: M26 - Production Hardening
**Owner**: SRE / Infrastructure Team
**Classification**: OPERATIONAL

---

## PURPOSE

This runbook documents the institutional smoke test suite - a fast, automated health check that answers:

**"Can I start SUBLIMINE today without fear of it exploding?"**

---

## QUICK START

```bash
# Run full test suite
python scripts/smoke_test_institutional.py

# Run production-critical tests only (faster)
python scripts/smoke_test_institutional.py --subset production

# Run with verbose output (debugging)
python scripts/smoke_test_institutional.py --verbose
```

**Expected runtime**: <2 seconds (production subset), <5 seconds (full suite)

---

## EXIT CODES & INTERPRETATION

| Exit Code | Status | Action Required | Meaning |
|-----------|--------|----------------|---------|
| **0** | ✅ ALL PASS | **PROCEED** with launch | All tests passed - system healthy |
| **1** | ❌ P0 FAILURE | **ABORT** launch immediately | Infrastructure broken - DO NOT START |
| **2** | ⚠️ P1 FAILURE | **REVIEW** before launch | Integration issues - needs investigation |
| **3** | ⚠️ P2 WARNING | **PROCEED** with caution | Non-critical issues - document and monitor |

---

## TEST LEVELS EXPLAINED

### P0_HEALTH (BLOCKING)
**Definition**: Infrastructure and core dependencies
**Criticality**: BLOCKING - system cannot start if these fail
**Examples**:
- Python environment (version 3.8+)
- Core library imports (pandas, numpy, yaml)
- Configuration loading (file or defaults)
- KillSwitch initialization
- Database connection (if configured)
- Execution system modules

**If P0 fails**:
1. **DO NOT** start trading
2. **INVESTIGATE** immediately
3. **FIX** before attempting launch
4. **RE-RUN** smoke test to verify fix

### P1_INTEGRATION (HIGH)
**Definition**: Core trading system functionality
**Criticality**: HIGH - system may start but will not function correctly
**Examples**:
- MicrostructureEngine (OFI/CVD/VPIN calculation)
- Strategy orchestrator
- Backtest engine parity mode
- Brain/risk management modules
- Reporting system

**If P1 fails**:
1. **REVIEW** failure details
2. **ASSESS** impact on trading mode (RESEARCH vs PAPER vs LIVE)
3. **CONFIRM** with risk manager before proceeding
4. **DOCUMENT** decision in system log
5. **MONITOR** closely if proceeding

### P2_COSMETIC (LOW)
**Definition**: Nice-to-have features and optional components
**Criticality**: LOW - system functional but some features unavailable
**Examples**:
- MT5 availability (not needed for RESEARCH mode)
- Optional directory structures
- Non-critical integrations

**If P2 fails**:
1. **LOG** warning in operational notes
2. **PROCEED** with launch
3. **SCHEDULE** fix during next maintenance window
4. **VERIFY** affected features are not needed

---

## TEST CATALOG

### P0_HEALTH Tests (7 tests, ~0.7s)

#### 1. Python environment
**What**: Verifies Python version >= 3.8
**Why**: System requires Python 3.8+ features
**Failure**: Upgrade Python installation

#### 2. Core imports
**What**: Tests pandas, numpy, yaml can be imported
**Why**: Core dependencies for all calculations
**Failure**: Run `pip install -r requirements.txt`

#### 3. Config file exists
**What**: Checks for config.yaml OR validates defaults work
**Why**: System configuration required
**Failure**: Create config.yaml from template OR verify defaults acceptable

#### 4. Config loads
**What**: Validates config structure (brain/strategies/risk/execution sections)
**Why**: Required config sections must be present
**Failure**: Check config.yaml syntax, verify required sections

#### 5. KillSwitch config
**What**: Tests KillSwitch initializes in ACTIVE state
**Why**: Safety mechanism must be functional
**Failure**: Check KillSwitch configuration, verify no hard-coded blocks

#### 6. Database connection
**What**: Tests Postgres connection (if configured)
**Why**: Trade history/logging requires DB
**Failure**: Start Postgres, verify credentials in config

#### 7. Execution system imports
**What**: Tests execution modules can be imported
**Why**: Required for PAPER/LIVE modes
**Failure**: Fix import errors, check MT5 installation (LIVE mode only)

---

### P1_INTEGRATION Tests (7 tests, ~1.0s)

#### 8. MicrostructureEngine import
**What**: Tests MicrostructureEngine module imports
**Why**: Core feature calculation engine
**Failure**: Check src/microstructure/ module integrity

#### 9. MicrostructureEngine calculation
**What**: Tests OFI/CVD/VPIN calculation with synthetic data
**Why**: Validates MANDATO 25 fixes (parity mode)
**Failure**: Review MicrostructureEngine implementation, check function signatures

#### 10. Strategy orchestrator
**What**: Tests StrategyOrchestrator loads strategies
**Why**: No strategies = no signals
**Failure**: Check strategy configs, verify at least one strategy enabled

#### 11. Backtest engine parity
**What**: Tests BacktestEngine uses MicrostructureEngine
**Why**: MANDATO 25 parity requirement (BACKTEST ↔ PAPER ↔ LIVE)
**Failure**: Verify BacktestEngine has `use_microstructure_engine=True`

#### 12. Brain import
**What**: Tests InstitutionalBrain module imports
**Why**: Signal filtering and quality control
**Failure**: Check src/core/brain.py or src/brain/ module

#### 13. Reporting system
**What**: Tests reporting modules import
**Why**: Performance tracking and compliance
**Failure**: Check src/reporting/ module integrity

#### 14. Risk allocator
**What**: Tests risk management modules import
**Why**: Position sizing and risk limits
**Failure**: Check src/risk/ or src/core/risk_manager.py

---

### P2_COSMETIC Tests (3 tests, ~0.05s)

#### 15. MT5 availability
**What**: Tests if MetaTrader5 is installed
**Why**: Required for LIVE mode only
**Failure**: Install MT5 if planning LIVE mode, otherwise ignore

#### 16. Reports directory
**What**: Tests reports/ directory exists
**Why**: Output location for performance reports
**Failure**: Create directory: `mkdir -p reports`

#### 17. Data directory
**What**: Tests data/ directory exists
**Why**: Storage for historical data
**Failure**: Create directory: `mkdir -p data`

---

## FAILURE SCENARIOS & RESOLUTIONS

### Scenario 1: P0 Failure - Config not found

**Symptom**:
```
✗ Config file exists: config.yaml not found at /path/to/config.yaml
Exit Code: 1
```

**Root Cause**: No config.yaml file

**Resolution**:
```bash
# Option A: Create from template (if template exists)
cp config.yaml.template config.yaml

# Option B: System will use defaults (verify acceptable)
# Check main_institutional.py _get_default_config()

# Option C: Create minimal config
cat > config.yaml <<EOF
risk:
  max_risk_per_trade: 0.01
  max_portfolio_risk: 0.06
execution:
  slippage_pips: 0.5
features:
  ofi_lookback: 20
strategies:
  vpin_reversal_extreme:
    enabled: true
brain:
  min_quality_score: 3.0
EOF

# Re-run smoke test
python scripts/smoke_test_institutional.py --subset production
```

---

### Scenario 2: P0 Failure - Execution imports fail

**Symptom**:
```
✗ Execution system imports: No module named 'MetaTrader5'
Exit Code: 1
```

**Root Cause**: MT5 not installed (common in dev/CI environments)

**Resolution**:
```bash
# Option A: Install MT5 (Windows/production only)
pip install MetaTrader5

# Option B: Verify environment doesn't need MT5
# - RESEARCH mode: MT5 not required ✓
# - PAPER mode: MT5 not required ✓
# - LIVE mode: MT5 REQUIRED ✗

# If RESEARCH/PAPER only, this is a smoke test false positive
# File issue to make MT5 optional for non-LIVE modes
```

---

### Scenario 3: P1 Failure - MicrostructureEngine calculation fails

**Symptom**:
```
✗ MicrostructureEngine calculation: OFI not calculated
Exit Code: 2
```

**Root Cause**: MANDATO 25 regression - function signature mismatch

**Resolution**:
```bash
# This is a CRITICAL regression - ABORT deployment
# Verify MANDATO 25 fixes are applied:

# Check commit history
git log --oneline --grep="MANDATO25" | head -5

# Expected commits:
# ab1cfc3 - P0 MicrostructureEngine fixes
# 30dc995 - BacktestEngine parity mode

# If missing, checkout correct branch
git checkout claude/mandato24-full-loop-integration-01AqipubodvYuyNtfLsBZpsx
git pull

# Re-run smoke test
python scripts/smoke_test_institutional.py
```

---

### Scenario 4: P1 Failure - Strategy orchestrator fails

**Symptom**:
```
✗ Strategy orchestrator: No strategies loaded
Exit Code: 2
```

**Root Cause**: No strategies enabled in config

**Resolution**:
```yaml
# Edit config.yaml
strategies:
  vpin_reversal_extreme:
    enabled: true
  idp_inducement_distribution:
    enabled: true
  order_flow_toxicity:
    enabled: true

# Or use minimal config with at least 1 strategy
```

---

### Scenario 5: P2 Warning - MT5 not available

**Symptom**:
```
⚠️ MT5 availability: MetaTrader5 not installed (OK for non-MT5 environments)
Exit Code: 3
```

**Root Cause**: MT5 not installed (expected in dev/CI)

**Resolution**:
```
# This is OK for:
# - Development environments
# - CI/CD pipelines
# - RESEARCH mode
# - PAPER mode (if using simulated execution)

# Action: PROCEED with launch if not planning LIVE mode
# Action: DOCUMENT in system notes

# If planning LIVE mode:
pip install MetaTrader5  # Windows only
```

---

## REPORT INTERPRETATION

### Report Location
```
reports/health/SMOKE_TEST_INSTITUTIONAL_<timestamp>.md
```

### Report Structure
```markdown
# Institutional Smoke Test Report

**Date**: 2025-11-15 08:53:04
**Status**: ✅ ALL TESTS PASSED
**Exit Code**: 0
**Duration**: 0.68s

## Summary
- Total Tests: 7
- Passed: 7
- Failed: 0

## Test Results
| Test | Level | Status | Duration | Message |
|------|-------|--------|----------|---------|
| Python environment | P0_HEALTH | ✓ | 0ms | OK |
| Core imports | P0_HEALTH | ✓ | 658ms | OK |
...
```

### Reading the Table

- **✓ (checkmark)**: Test passed
- **✗ (cross)**: Test failed
- **Duration**: Time in milliseconds (ms)
- **Message**: "OK" or error details

---

## INTEGRATION WITH START SCRIPTS

### Automatic Health Check

Start scripts (`start_paper_trading.py`, `start_live_trading.py`) will automatically run smoke tests before launch.

**Workflow**:
```
Operator runs start script
    ↓
Script runs: smoke_test_institutional.py --subset production
    ↓
Exit Code 0 → Continue with launch
Exit Code 1 → ABORT (P0 failure)
Exit Code 2 → WARN and request confirmation
Exit Code 3 → WARN and continue
```

### Manual Override

```bash
# Skip smoke test (NOT RECOMMENDED)
python start_paper_trading.py --skip-health-check

# Force launch despite P1 failures (RISK MANAGER APPROVAL REQUIRED)
python start_paper_trading.py --force-start
```

**Warning**: Manual overrides must be documented in operational log.

---

## CONTINUOUS INTEGRATION

### Pre-Commit Hook

```bash
#!/bin/bash
# .git/hooks/pre-commit
python scripts/smoke_test_institutional.py --subset production
if [ $? -eq 1 ]; then
    echo "P0 smoke test failed - commit aborted"
    exit 1
fi
```

### CI/CD Pipeline

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
      - run: python scripts/smoke_test_institutional.py --subset production
```

---

## OPERATIONAL NOTES

### When to Run

**Mandatory**:
- Before every PAPER/LIVE launch
- After code deployment
- After configuration changes
- After system restarts

**Recommended**:
- Daily at market open (cron job)
- Before important events (NFP, FOMC)
- After dependency upgrades

### Scheduled Execution

```bash
# Crontab entry (daily at 07:00 UTC, before market open)
0 7 * * * cd /path/to/TradingSystem && python scripts/smoke_test_institutional.py --subset production >> /var/log/sublimine/daily_health_check.log 2>&1
```

### Alert Configuration

```bash
# Email on P0 failure
python scripts/smoke_test_institutional.py || mail -s "SUBLIMINE P0 FAILURE" ops@sublimine.com < reports/health/SMOKE_TEST_INSTITUTIONAL_latest.md
```

---

## TROUBLESHOOTING

### Test Hangs/Timeout

**Symptom**: Smoke test doesn't complete

**Common Causes**:
- Database connection timeout
- Network issues
- Deadlock in imports

**Resolution**:
```bash
# Run with timeout
timeout 30s python scripts/smoke_test_institutional.py

# Run subset to isolate issue
python scripts/smoke_test_institutional.py --subset production

# Add verbose output
python scripts/smoke_test_institutional.py --verbose
```

### False Positives

**Symptom**: Test fails but system actually works

**Common Causes**:
- Environment-specific issues (MT5 in CI)
- Test assumptions incorrect
- Stale test code

**Resolution**:
1. Document in runbook as known issue
2. File GitHub issue for test fix
3. Use manual override (with approval)
4. Add environment detection to test

### Performance Degradation

**Symptom**: Smoke test takes >5 seconds

**Investigation**:
```bash
# Run with verbose timing
python scripts/smoke_test_institutional.py --verbose

# Check for slow tests (>500ms)
# Common culprits:
# - Database connection (first time)
# - Large imports (pandas, numpy)
# - Strategy loading

# Profile if needed
python -m cProfile scripts/smoke_test_institutional.py
```

---

## MAINTENANCE

### Adding New Tests

```python
# In scripts/smoke_test_institutional.py

# 1. Add test method
def _test_new_feature(self):
    """Test new feature works."""
    from src.new_module import NewFeature
    feature = NewFeature()
    assert feature.works()

# 2. Register in run_all_tests()
self._run_test("New feature", TestLevel.P1_INTEGRATION, self._test_new_feature)
```

### Updating Test Levels

**Criteria for P0** (BLOCKING):
- System cannot start without it
- Infrastructure dependency
- Core library/module
- Configuration/database

**Criteria for P1** (HIGH):
- Core trading functionality
- Feature calculation
- Strategy/signal generation
- Risk management

**Criteria for P2** (LOW):
- Optional features
- Non-critical integrations
- Convenience utilities

---

## ESCALATION

### P0 Failure - Immediate Escalation
**Contact**: SRE Team + Risk Manager
**SLA**: 15 minutes response
**Action**: ABORT all launches until resolved

### P1 Failure - Same-Day Resolution
**Contact**: Development Team
**SLA**: 4 hours response
**Action**: Review + document decision to proceed/abort

### P2 Warning - Next Sprint
**Contact**: Development Team (ticket)
**SLA**: Next sprint planning
**Action**: Log and continue

---

## REFERENCES

- **Smoke Test Script**: `scripts/smoke_test_institutional.py`
- **MANDATO 26**: Production Hardening mandate
- **MANDATO 25**: Integration audit (context for parity tests)
- **Production Health Checks**: `docs/MANDATO26_PRODUCTION_HEALTHCHECKS_20251115.md`
- **GO/NO-GO Checklist**: `docs/GO_NO_GO_SUBLIMINE_20251115.md`

---

**Document Version**: 1.0
**Last Updated**: 2025-11-15
**Next Review**: 2025-12-15
**Owner**: SRE Team / Infrastructure Lead
