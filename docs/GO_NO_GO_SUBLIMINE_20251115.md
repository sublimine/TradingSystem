# GO / NO-GO Checklist - SUBLIMINE Trading System

**Date**: 2025-11-15
**Mandate**: M26 - Production Hardening
**Classification**: OPERATIONAL - MANDATORY
**Purpose**: Gate progression from RESEARCH → PAPER → LIVE

---

## OVERVIEW

This checklist defines **mandatory requirements** for progressing through trading modes.

**Institutional Standard**: No mode transition without checklist completion + sign-off.

---

## PHILOSOPHY

```
RESEARCH (Development)
    ↓
    GO/NO-GO Checkpoint #1
    ↓
PAPER (Simulation - No Real Money)
    ↓
    GO/NO-GO Checkpoint #2
    ↓
LIVE Small (Real Money - Limited Capital)
    ↓
    GO/NO-GO Checkpoint #3
    ↓
LIVE Full (Real Money - Full Capital)
```

**Each checkpoint requires**:
1. Technical validation (automated)
2. Performance validation (measured)
3. Operational readiness (manual)
4. Sign-off (Risk Manager + CTO)

---

## CHECKPOINT #1: RESEARCH → PAPER

### Technical Validation

**Automated Tests** (MUST PASS):
- [ ] Smoke tests pass (exit code 0)
  ```bash
  python scripts/smoke_test_institutional.py
  ```
- [ ] All P0 health checks pass
- [ ] MicrostructureEngine working (OFI/CVD/VPIN calculated)
- [ ] Backtest parity mode enabled (BACKTEST ↔ PAPER guaranteed)
- [ ] Strategy orchestrator loads ≥3 strategies
- [ ] Config validation passes

**Backtests Completed** (MANDATO 17):
- [ ] Minimum 90 days historical backtest
- [ ] All strategies tested individually
- [ ] Portfolio backtest (multi-strategy)
- [ ] Walk-forward validation completed
- [ ] Out-of-sample results reviewed

**Backtest Performance** (Minimum Acceptable):
- [ ] Sharpe Ratio ≥ 1.0 (preferably ≥1.5)
- [ ] Max Drawdown ≤ 15%
- [ ] Win Rate ≥ 40%
- [ ] Profit Factor ≥ 1.3
- [ ] Tested on different market regimes (trending, ranging, volatile)

---

### Infrastructure Validation

- [ ] Reporting system functional
  - Generates backtest reports
  - Saves to `backtest_reports/`
  - No crashes
- [ ] Database configured (if used)
  - Connection successful
  - Tables created
  - Write/read tested
- [ ] Log aggregation working
  - Logs written to `logs/`
  - Rotation configured
  - No permission errors

---

### Documentation

- [ ] Strategy catalog updated
  - All strategies documented
  - Metadata contracts defined
  - Performance characteristics noted
- [ ] Risk limits documented
  - `risk_limits.yaml` reviewed
  - Max risk per trade: 0-2%
  - Portfolio risk limits: ≤6%
- [ ] Operational runbooks created
  - Smoke test runbook
  - Health checks runbook
  - Monitoring runbook

---

### Sign-Off

**Required Approvals**:
- [ ] **Developer**: Certifies technical readiness
  - Name: ________________
  - Date: ________________
  - Signature: ________________

- [ ] **Risk Manager**: Certifies risk framework
  - Name: ________________
  - Date: ________________
  - Signature: ________________

**Decision**:
- [ ] ✅ **GO** - Proceed to PAPER mode
- [ ] ❌ **NO-GO** - Remain in RESEARCH mode
- [ ] ⚠️ **CONDITIONAL GO** - Proceed with restrictions:
  - Restrictions: ________________

---

## CHECKPOINT #2: PAPER → LIVE (Small)

### PAPER Mode Validation

**Minimum PAPER Duration**: 7 trading days
**Minimum Operations**: 20 trades OR 50 signals generated

**Performance Requirements** (PAPER):
- [ ] No system crashes
- [ ] No P0 smoke test failures
- [ ] MaxDD within limits (≤15% of paper capital)
- [ ] Reject rate reasonable (≤60%)
- [ ] Strategy performance aligned with backtest (within 20% variance)

**PAPER Results** (Measured):
```
┌─────────────────────────┬──────────────┬──────────────┬──────────────┐
│ Metric                  │ Backtest     │ Paper        │ Variance     │
├─────────────────────────┼──────────────┼──────────────┼──────────────┤
│ Total Trades            │ _________    │ _________    │ _________    │
│ Win Rate %              │ _________    │ _________    │ _________    │
│ Avg Win $               │ _________    │ _________    │ _________    │
│ Avg Loss $              │ _________    │ _________    │ _________    │
│ Max Drawdown $          │ _________    │ _________    │ _________    │
│ Sharpe Ratio            │ _________    │ _________    │ _________    │
└─────────────────────────┴──────────────┴──────────────┴──────────────┘

Variance Acceptable: ≤20% deviation from backtest
```

---

### Operational Readiness

**Calibration Complete** (MANDATO 18R-22):
- [ ] Calibration framework operational
- [ ] Real data integration tested
- [ ] Parameter optimization validated
- [ ] Results documented

**Risk Management**:
- [ ] Risk limits enforced in PAPER
  - No violations observed
  - Kill switch functional
  - Position sizing correct
- [ ] Exposure monitoring active
- [ ] Daily P&L tracking working

**Execution Quality**:
- [ ] Order execution tested (simulated)
- [ ] Slippage modeling validated
- [ ] Fill simulation realistic
- [ ] No execution errors

---

### Live Readiness

**MT5 Integration** (LIVE mode requirement):
- [ ] MT5 installed and configured
- [ ] Connection tested (demo account first)
- [ ] Account credentials secured
- [ ] API permissions verified

**Kill Switch** (MANDATORY):
- [ ] Kill switch tested manually
- [ ] Automatic triggers configured:
  - Daily loss limit: -2%
  - Reject rate: >80%
  - Max drawdown breach
- [ ] Recovery procedure documented
- [ ] Contact list for escalation

**Compliance**:
- [ ] Broker account opened (real account)
- [ ] KYC/AML completed
- [ ] Trading permissions granted
- [ ] Capital deposited (small amount for LIVE small)

---

### Sign-Off

**Required Approvals**:
- [ ] **Trader/Operator**: Certifies operational competence
  - Name: ________________
  - Date: ________________
  - Signature: ________________

- [ ] **Risk Manager**: Certifies risk controls
  - Name: ________________
  - Date: ________________
  - Signature: ________________

- [ ] **CTO/Architect**: Certifies technical stability
  - Name: ________________
  - Date: ________________
  - Signature: ________________

**Capital Allocation** (LIVE Small):
- Approved Capital: $________ (Recommended: $1,000 - $5,000)
- Max Loss Tolerance: $________ (Recommended: ≤$200)
- Duration: ________ days (Recommended: 10-15 trading days)

**Decision**:
- [ ] ✅ **GO** - Proceed to LIVE (Small)
- [ ] ❌ **NO-GO** - Remain in PAPER mode
- [ ] ⚠️ **CONDITIONAL GO** - Proceed with restrictions:
  - Restrictions: ________________

---

## CHECKPOINT #3: LIVE (Small) → LIVE (Full)

### LIVE Small Validation

**Minimum Duration**: 10 trading days
**Minimum Operations**: 30 trades OR 100 signals

**Performance Requirements** (LIVE Small):
- [ ] No kill switch activations (or <3 justified activations)
- [ ] No technical failures
- [ ] Real money P&L positive OR within acceptable variance
- [ ] Execution quality acceptable (slippage ≤1 pip avg)

**LIVE Small Results** (Measured):
```
┌─────────────────────────┬──────────────┬──────────────┬──────────────┐
│ Metric                  │ Paper        │ Live Small   │ Variance     │
├─────────────────────────┼──────────────┼──────────────┼──────────────┤
│ Total Trades            │ _________    │ _________    │ _________    │
│ Win Rate %              │ _________    │ _________    │ _________    │
│ Avg Win $               │ _________    │ _________    │ _________    │
│ Avg Loss $              │ _________    │ _________    │ _________    │
│ Max Drawdown $          │ _________    │ _________    │ _________    │
│ Sharpe Ratio            │ _________    │ _________    │ _________    │
│ Execution Slippage (avg)│ _________    │ _________    │ _________    │
└─────────────────────────┴──────────────┴──────────────┴──────────────┘

Variance Acceptable: ≤30% deviation from PAPER
```

---

### Divergence Analysis

**CRITICAL**: Analyze Backtest ↔ Live divergence

**Acceptable Divergences**:
- Slippage/spread costs (expected)
- Minor timing differences (acceptable)
- Market regime changes (documented)

**Unacceptable Divergences** (INVESTIGATION REQUIRED):
- Feature calculation differences (suggests parity bug)
- Strategy logic differences (suggests integration bug)
- Major performance collapse (suggests overfitting)

**Divergence Report**:
```
Analysis Date: ________________
Analyst: ________________

Primary Divergences Identified:
1. ____________________________________________________
2. ____________________________________________________
3. ____________________________________________________

Root Causes:
1. ____________________________________________________
2. ____________________________________________________

Mitigation Plan:
1. ____________________________________________________
2. ____________________________________________________

Risk Assessment: [ ] LOW  [ ] MEDIUM  [ ] HIGH
```

---

### Operational Excellence

**Kill Switch History**:
```
┌────────────┬───────────────┬──────────────────────────────────────────┐
│ Date       │ Reason        │ Resolution                               │
├────────────┼───────────────┼──────────────────────────────────────────┤
│ __________│ _____________ │ ________________________________________ │
│ __________│ _____________ │ ________________________________________ │
└────────────┴───────────────┴──────────────────────────────────────────┘

Total Activations: _________
Justified: _________ (acceptable)
False Positives: _________ (needs tuning)
```

**Incident Log**:
- [ ] No P0 incidents
- [ ] All P1 incidents resolved
- [ ] Post-mortems completed for all incidents

**Monthly Reviews**:
- [ ] Performance review completed
- [ ] Strategy performance attribution
- [ ] Risk metrics reviewed
- [ ] Operational metrics reviewed

---

### Scaling Plan

**Target Capital**: $________
**Scaling Timeline**: ________ weeks/months
**Scaling Increments**: $________ per step

**Example Scaling**:
```
Week 1-2:  $5,000   (LIVE Small - validation)
Week 3-4:  $10,000  (First increment)
Week 5-6:  $20,000  (Second increment)
Week 7-8:  $50,000  (Full deployment - if approved)
```

**Scaling Gates** (Each increment requires):
- [ ] Previous increment profitable OR breakeven
- [ ] No kill switch activations in previous increment
- [ ] Sharpe ratio maintained or improved
- [ ] Risk Manager approval

---

### Sign-Off

**Required Approvals**:
- [ ] **Head of Desk** (if institutional): Certifies business readiness
  - Name: ________________
  - Date: ________________
  - Signature: ________________

- [ ] **Risk Manager**: Certifies risk management
  - Name: ________________
  - Date: ________________
  - Signature: ________________

- [ ] **CTO/Architect**: Certifies production stability
  - Name: ________________
  - Date: ________________
  - Signature: ________________

**Capital Allocation** (LIVE Full):
- Approved Capital: $________
- Max Daily Loss: $________ (-2% of capital)
- Max Drawdown: $________ (-15% of capital)

**Decision**:
- [ ] ✅ **GO** - Proceed to LIVE (Full)
- [ ] ❌ **NO-GO** - Scale back to LIVE (Small)
- [ ] ⚠️ **CONDITIONAL GO** - Proceed with restrictions:
  - Restrictions: ________________

---

## ABORT CONDITIONS (All Modes)

**Immediate Halt Required If**:
- P0 smoke test failure
- Kill switch malfunction
- Execution system failure
- Daily loss > -5% (emergency threshold)
- Uncontrolled drawdown
- Regulatory breach

**Procedure**:
1. STOP all trading immediately
2. Activate kill switch manually
3. Close all positions (if safe to do so)
4. Escalate to Risk Manager + CTO
5. Document incident
6. Perform root cause analysis
7. Implement fix
8. Re-run smoke tests
9. Get approval to restart

---

## REVIEW SCHEDULE

- **Weekly**: Operator review (during PAPER/LIVE Small)
- **Bi-weekly**: Risk Manager review (during LIVE Small)
- **Monthly**: Full team review (during LIVE Full)
- **Quarterly**: Strategic review + checklist update

---

## COMPLIANCE

**Required Documentation**:
- [ ] All checkpoints completed
- [ ] All sign-offs obtained
- [ ] Performance data attached
- [ ] Incident logs attached
- [ ] Risk assessments completed

**Retention**: Keep for 7 years (regulatory requirement)

---

## REFERENCES

- **Smoke Tests**: `scripts/smoke_test_institutional.py`
- **Health Checks**: `docs/MANDATO26_PRODUCTION_HEALTHCHECKS_20251115.md`
- **Monitoring**: `docs/MONITORING_MINIMAL_RUNBOOK_20251115.md`
- **Backtest Guide**: `BACKTESTING_GUIDE.md`

---

**Document Version**: 1.0
**Last Updated**: 2025-11-15
**Next Review**: 2025-12-15
**Owner**: Risk Manager + CTO

---

## SIGN-OFF SUMMARY

```
RESEARCH → PAPER
Date: ________________
Decision: [ ] GO  [ ] NO-GO  [ ] CONDITIONAL GO
Approvals: ________________

PAPER → LIVE (Small)
Date: ________________
Decision: [ ] GO  [ ] NO-GO  [ ] CONDITIONAL GO
Approvals: ________________

LIVE (Small) → LIVE (Full)
Date: ________________
Decision: [ ] GO  [ ] NO-GO  [ ] CONDITIONAL GO
Approvals: ________________
```
