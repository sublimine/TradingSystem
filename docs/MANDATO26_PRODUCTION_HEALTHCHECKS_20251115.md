# Production Health Checks - MANDATO 26

**Date**: 2025-11-15
**Mandate**: M26 - Production Hardening
**Classification**: OPERATIONAL

---

## OVERVIEW

Production health checks are **automatic pre-flight validations** executed before launching PAPER or LIVE trading modes. They ensure system integrity and prevent launch with broken infrastructure.

**Key Principle**: **"If it doesn't pass smoke tests, it doesn't trade."**

---

## ARCHITECTURE

```
┌─────────────────────────────────────────────────────────────┐
│                      OPERATOR                               │
│                                                             │
│  python scripts/start_paper_trading.py --capital 10000     │
│         OR                                                  │
│  python scripts/start_live_trading.py --capital 10000      │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│               START SCRIPT (Launcher)                       │
│  ┌─────────────────────────────────────────────────────┐  │
│  │ Step 0: HEALTH CHECKS (smoke_test_institutional.py)│  │
│  │   - P0: Infrastructure (BLOCKING)                   │  │
│  │   - P1: Integration (HIGH)                          │  │
│  │   - P2: Cosmetic (LOW)                              │  │
│  └────────┬────────────────────────────────────────────┘  │
│           │                                                 │
│           ├─► Exit 0: ✅ PASS → Continue                  │
│           ├─► Exit 1: ❌ P0 FAIL → ABORT                  │
│           ├─► Exit 2: ⚠️  P1 FAIL → WARN (force if approved)│
│           └─► Exit 3: ⚠️  P2 WARN → LOG + Continue         │
│                                                             │
│  Step 1-N: Additional Validations                          │
│   - Config loading                                          │
│   - MT5 connection (LIVE only)                              │
│   - Risk limits                                             │
│   - Operator confirmation                                   │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│           main_institutional.py --mode {paper|live}         │
│                   TRADING LOOP                              │
└─────────────────────────────────────────────────────────────┘
```

---

## MODES

### PAPER Mode (Simulated)
**Health Check**: Production subset (`--subset production`)
**Runtime**: ~0.7s
**Tests**: 7 P0 tests
**Philosophy**: Fast checks, zero real money risk

**Rationale**: PAPER mode has lower risk tolerance for delays. Quick P0 validation ensures infrastructure works without comprehensive integration checks.

### LIVE Mode (Real Money)
**Health Check**: FULL suite (all tests)
**Runtime**: ~1.8s
**Tests**: 17 tests (P0 + P1 + P2)
**Philosophy**: Comprehensive checks, real money protection

**Rationale**: LIVE mode requires exhaustive validation. Extra 1 second is acceptable to prevent real money loss from broken integration.

---

## EXIT CODE HANDLING

### Exit Code 0: All Tests Passed ✅
**Action**: PROCEED with launch
**Logging**: Info level
**User message**: "✅ Health checks passed"

**Example**:
```
Step 0/3: Running health checks...
================================================================================
INSTITUTIONAL SMOKE TEST SUITE - MANDATO 26
================================================================================
...
✅ ALL TESTS PASSED
================================================================================
✅ Health checks passed

Step 1/3: Operator confirmation...
```

---

### Exit Code 1: P0 Failure ❌
**Action**: **ABORT** launch immediately (no override)
**Logging**: Critical level
**User message**: Detailed abort message with report path

**Example (PAPER)**:
```
Step 0/3: Running health checks...
...
❌ P0 HEALTH CHECK FAILURE - ABORTING LAUNCH
================================================================================
Infrastructure is broken. DO NOT START trading.
Fix P0 issues and re-run smoke test.

To view detailed report:
  ls -lt reports/health/SMOKE_TEST_INSTITUTIONAL_*.md | head -1
================================================================================

Launch aborted
```

**Example (LIVE)**:
```
Step 0/6: Running MANDATORY health checks...
...
❌ P0 HEALTH CHECK FAILURE - LAUNCH ABORTED
================================================================================
Infrastructure is broken. DO NOT START LIVE TRADING.
Fix P0 issues and re-run smoke test before attempting LIVE.

To view detailed report:
  ls -lt reports/health/SMOKE_TEST_INSTITUTIONAL_*.md | head -1
================================================================================
```

**Common P0 Failures**:
- Python version < 3.8
- Core libraries not installed (pandas, numpy)
- Execution system imports broken
- Config validation failed
- Database connection failed (if required)

**Resolution**: Fix infrastructure issue, re-run smoke test, retry launch

---

### Exit Code 2: P1 Failure ⚠️
**Action (PAPER)**: WARN + request manual override
**Action (LIVE)**: **ABORT** unless `--force-start` (requires approval)
**Logging**: Warning level
**User message**: Detailed warning with override instructions

**Example (PAPER without --force-start)**:
```
Step 0/3: Running health checks...
...
⚠️  P1 HEALTH CHECK FAILURES DETECTED
================================================================================
Core functionality may be impaired.

Options:
  1. ABORT and fix P1 issues (RECOMMENDED)
  2. Force start with --force-start (REQUIRES APPROVAL)

Aborting launch for safety.
================================================================================
```

**Example (LIVE with --force-start)**:
```
Step 0/6: Running MANDATORY health checks...
...
🚨 P1 HEALTH CHECK FAILURES DETECTED 🚨
================================================================================
Core trading functionality may be impaired.
LAUNCHING LIVE WITH P1 FAILURES IS EXTREMELY RISKY.
...
🚨 FORCE START ENABLED - PROCEEDING WITH P1 FAILURES 🚨
⚠️  This decision MUST be approved by:
    - Risk Manager
    - CTO / Technical Lead
⚠️  Document this in compliance/operational log
================================================================================
Press ENTER to acknowledge and continue...
```

**Common P1 Failures**:
- MicrostructureEngine calculation broken
- Strategy orchestrator not loading strategies
- Backtest parity mode disabled
- Brain/risk modules import failed

**Resolution**:
1. **RECOMMENDED**: Fix P1 issue, re-run smoke test
2. **Override** (PAPER only, or LIVE with approval):
   - Risk Manager review
   - CTO approval
   - Document decision in compliance log
   - Use `--force-start` flag

---

### Exit Code 3: P2 Warnings ⚠️
**Action**: LOG warning + PROCEED
**Logging**: Warning level
**User message**: Brief warning

**Example**:
```
Step 0/3: Running health checks...
...
⚠️  P2 warnings detected (non-critical) - proceeding
```

**Common P2 Warnings**:
- MT5 not installed (OK for RESEARCH/PAPER without MT5)
- Reports/data directories missing (created on demand)
- Optional integrations unavailable

**Resolution**: Document in operational notes, schedule fix during maintenance

---

## OVERRIDE FLAGS

### --skip-health-check
**Purpose**: Bypass health checks entirely
**Risk Level**: 🔴 EXTREME (for LIVE), 🟡 HIGH (for PAPER)
**Authorization Required**: CTO (LIVE), Team Lead (PAPER)

**PAPER Mode**:
```bash
python scripts/start_paper_trading.py --capital 10000 --skip-health-check

# Output:
⚠️  HEALTH CHECKS SKIPPED (--skip-health-check)
⚠️  This is NOT RECOMMENDED for production use
```

**LIVE Mode**:
```bash
python scripts/start_live_trading.py --capital 10000 --skip-health-check

# Output:
🚨 HEALTH CHECKS SKIPPED (--skip-health-check) 🚨
================================================================================
⚠️  THIS IS EXTREMELY DANGEROUS FOR LIVE TRADING
⚠️  Skipping health checks can result in REAL MONEY LOSS
⚠️  This override MUST be approved by CTO
================================================================================
Type 'I UNDERSTAND THE RISKS' to continue: _
```

**When to Use**:
- Emergency hotfix deployment (CTO approved)
- Known smoke test false positive (documented)
- Development/testing environment (never production)

**Mandatory Actions**:
1. Get written approval (email/ticket)
2. Document reason in operational log
3. Create ticket to fix underlying issue
4. Re-enable health checks after emergency

---

### --force-start
**Purpose**: Proceed despite P1 failures
**Risk Level**: 🔴 HIGH (for LIVE), 🟡 MEDIUM (for PAPER)
**Authorization Required**: Risk Manager + CTO (LIVE), Team Lead (PAPER)

**Usage**:
```bash
python scripts/start_live_trading.py --capital 10000 --force-start
```

**Output**:
```
🚨 FORCE START ENABLED - PROCEEDING WITH P1 FAILURES 🚨
⚠️  This decision MUST be approved by:
    - Risk Manager
    - CTO / Technical Lead
⚠️  Document this in compliance/operational log
================================================================================
Press ENTER to acknowledge and continue...
```

**When to Use**:
- P1 failure is a false positive (test bug)
- P1 failure is known and acceptable (time-critical deployment)
- Functionality impacted by P1 is not needed for this session

**Mandatory Actions**:
1. Risk Manager approval (documented)
2. CTO approval (documented)
3. Operational log entry with:
   - Timestamp
   - Who approved
   - Reason for override
   - Expected impact
   - Mitigation plan
4. Monitor session closely
5. Create P0 ticket to fix P1 issue

---

## ABORT CONDITIONS

### Hard Abort (No Override)
- P0 failure (infrastructure broken)
- Smoke test script not found (LIVE mode)
- Smoke test timeout (>30s PAPER, >60s LIVE)
- Smoke test crash (exception)

### Soft Abort (Override Available)
- P1 failure without `--force-start`
- Operator cancellation (confirmation step)
- Config validation failed
- MT5 connection failed (LIVE mode)

---

## OPERATIONAL PROCEDURES

### Daily Launch Checklist

**PAPER Mode**:
```bash
# 1. Run health check manually (optional but recommended)
python scripts/smoke_test_institutional.py --subset production

# 2. If passed, launch PAPER
python scripts/start_paper_trading.py --capital 10000

# 3. Confirm when prompted
Type 'YES' to confirm: YES
```

**LIVE Mode**:
```bash
# 1. Run FULL health check manually (MANDATORY)
python scripts/smoke_test_institutional.py

# 2. Review report
cat reports/health/SMOKE_TEST_INSTITUTIONAL_<latest>.md

# 3. If all passed, launch LIVE
python scripts/start_live_trading.py --capital 10000

# 4. Monitor health check output carefully
# 5. Confirm when prompted
Type 'YES' to confirm: YES
```

---

### Emergency Procedures

**P0 Failure During Trading**:
1. System auto-stops (KillSwitch activation)
2. Investigate immediately
3. DO NOT restart until P0 fixed
4. Run smoke test to verify fix
5. Document in incident log

**P1 Failure Discovered Post-Launch**:
1. Assess impact on live positions
2. If critical, trigger controlled shutdown
3. Fix P1 issue
4. Run smoke test
5. Restart with --force-start if urgent (get approval)

---

## REPORTING

### Health Check Reports
**Location**: `reports/health/SMOKE_TEST_INSTITUTIONAL_<timestamp>.md`

**Format**:
```markdown
# Institutional Smoke Test Report

**Date**: 2025-11-15 08:53:04
**Status**: ✅ ALL TESTS PASSED
**Exit Code**: 0
**Duration**: 0.68s

## Test Results
| Test | Level | Status | Duration | Message |
|------|-------|--------|----------|---------|
| Python environment | P0_HEALTH | ✓ | 0ms | OK |
...
```

**Retention**: Keep last 30 days, archive older

---

### Operational Log

**Required Entries**:
- Every health check failure (exit ≠ 0)
- Every override use (--skip-health-check, --force-start)
- Every abort decision

**Format**:
```
[2025-11-15 08:53:04] HEALTH_CHECK_FAILED
  Mode: LIVE
  Exit Code: 2 (P1 failure)
  Failures: Strategy orchestrator (MT5 import)
  Decision: ABORT
  Operator: John Doe

[2025-11-15 09:15:22] OVERRIDE_FORCE_START
  Mode: LIVE
  Reason: Known MT5 import issue, not needed for active strategies
  Approved By: Risk Manager (Jane Smith), CTO (Bob Jones)
  Documentation: Ticket #1234
  Operator: John Doe
```

---

## MAINTENANCE

### Monthly Review
- Review all override usage
- Identify recurring failures
- Update smoke tests if needed
- Update abort/proceed criteria

### Quarterly Audit
- Test all exit code paths
- Verify approval workflows
- Update documentation
- Train new operators

---

## REFERENCES

- **Smoke Test Runner**: `scripts/smoke_test_institutional.py`
- **Smoke Test Runbook**: `docs/SMOKE_TEST_INSTITUTIONAL_RUNBOOK_20251115.md`
- **Start Scripts**: `scripts/start_{paper,live}_trading.py`
- **GO/NO-GO Checklist**: `docs/GO_NO_GO_SUBLIMINE_20251115.md`

---

**Document Version**: 1.0
**Last Updated**: 2025-11-15
**Owner**: SRE Team
