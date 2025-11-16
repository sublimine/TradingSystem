# Operational Runbook - PLAN OMEGA

**Version:** 1.0
**Last Updated:** 2025-11-16
**Status:** PRODUCTION READY

---

## Quick Reference

| Task | Command | Time |
|------|---------|------|
| Run Smoke Tests | `cd tests/smoke && ./run_all_smoke_tests.sh` | <20s |
| Backtest GREEN_ONLY | `python scripts/run_backtest.py --profile green_only --days 90` | ~2min |
| Backtest FULL_24 | `python scripts/run_backtest.py --profile full_24 --days 90` | ~5min |
| Start PAPER GREEN | `python scripts/run_paper_trading.py --profile green_only` | Continuous |
| Check KillSwitch | `python scripts/check_killswitch_status.py` | <1s |

---

## Table of Contents

1. [Daily Operations](#daily-operations)
2. [Weekly Operations](#weekly-operations)
3. [Monthly Operations](#monthly-operations)
4. [Pre-LIVE Checklist](#pre-live-checklist)
5. [Monitoring & Alerts](#monitoring--alerts)
6. [Troubleshooting](#troubleshooting)
7. [Emergency Procedures](#emergency-procedures)
8. [Performance Benchmarks](#performance-benchmarks)

---

## Daily Operations

### Morning Routine (Before Market Open)

#### 1. System Health Check (5 minutes)

```bash
# Step 1: Run smoke tests
cd /home/user/TradingSystem/tests/smoke
./run_all_smoke_tests.sh

# Expected output: ALL PASSED
# If any test fails → Do NOT start trading, investigate first
```

#### 2. Check KillSwitch Status (1 minute)

```python
# scripts/check_killswitch_status.py
from src.execution.execution_manager import ExecutionManager
from src.execution.execution_mode import ExecutionMode, ExecutionConfig

config = ExecutionConfig(mode=ExecutionMode.PAPER, initial_capital=10000.0)
manager = ExecutionManager(config)

status = manager.get_killswitch_status()
print(f"Emergency Stop: {status['emergency_stop_active']}")  # Should be False
print(f"Current Balance: ${status['current_balance']:.2f}")
print(f"Daily P&L: ${status['daily_pnl']:.2f}")

# Layer status
for layer, info in status['layers'].items():
    print(f"{layer}: {info['status']}")
```

**Expected:**
- Emergency stop: `False`
- All 4 layers: `ACTIVE`
- Balance > 0

**If emergency stop active:**
1. Review why (exceeded 15% drawdown?)
2. Analyze trades from yesterday
3. Reset manually if appropriate: `manager.kill_switch.reset_emergency_stop()`

#### 3. Review Yesterday's Performance (3 minutes)

```python
# scripts/daily_performance_report.py
stats = manager.get_statistics()

print(f"Yesterday's trades: {stats['total_trades']}")
print(f"Win rate: {stats['win_rate']:.1%}")
print(f"Total P&L: ${stats['total_pnl']:.2f}")
print(f"Max drawdown: {stats['max_drawdown']:.1%}")
```

**Red flags:**
- Win rate < 50% → Review strategy performance
- Max drawdown > 10% → Check risk management
- Too many trades (>20/day PAPER) → Overtrading?

#### 4. Start PAPER Trading (if applicable)

```bash
# For GREEN_ONLY
python scripts/run_paper_trading.py --profile green_only --log-level INFO

# For FULL_24
python scripts/run_paper_trading.py --profile full_24 --log-level INFO
```

**Monitoring during session:**
- Check logs every hour: `tail -f logs/trading_system.log`
- Watch for KillSwitch warnings
- Monitor position count (should not exceed max_positions)

---

### Evening Routine (After Market Close)

#### 1. Stop Trading System

```bash
# Gracefully stop (Ctrl+C)
# Wait for "System shutdown complete" message
```

#### 2. Daily Report Generation (5 minutes)

```bash
python scripts/generate_daily_report.py --date today --output reports/daily_$(date +%Y%m%d).md
```

**Review report for:**
- Total trades executed
- Win rate (target >60% for GREEN_ONLY)
- P&L breakdown by strategy
- KillSwitch activations (if any)
- Average R:R ratio

#### 3. Backup Critical Data

```bash
# Backup trades database
cp data/trades.db backups/trades_$(date +%Y%m%d).db

# Backup logs
gzip logs/trading_system_$(date +%Y%m%d).log

# Commit to git (optional)
git add reports/daily_*.md
git commit -m "Daily report $(date +%Y-%m-%d)"
```

#### 4. Strategy Performance Review

```python
# scripts/strategy_performance_review.py
from src.strategy_orchestrator import StrategyOrchestrator

orchestrator = StrategyOrchestrator(profile='green_only')
perf = orchestrator.performance_tracker

for strategy, stats in perf.items():
    win_rate = stats['winning_trades'] / stats['total_trades'] if stats['total_trades'] > 0 else 0
    print(f"{strategy}: {stats['total_trades']} trades, {win_rate:.1%} WR, ${stats['total_pnl']:.2f} P&L")
```

**Actions:**
- If strategy WR < 40% for 5+ trades → Disable temporarily
- If strategy has 5 consecutive losses → Circuit breaker should trigger (check KillSwitch)

---

## Weekly Operations

### Monday Morning (Week Start)

#### 1. Review Weekly Targets

```python
# scripts/weekly_targets.py
weekly_target_pnl = initial_capital * 0.02  # 2% weekly target
weekly_max_loss = initial_capital * 0.05    # 5% weekly stop

print(f"Weekly P&L target: ${weekly_target_pnl:.2f}")
print(f"Weekly max loss: ${weekly_max_loss:.2f}")
print(f"Current balance: ${current_balance:.2f}")
```

#### 2. Run Extended Backtest (Optional)

```bash
# Test with latest week's data
python scripts/run_backtest.py --profile green_only --days 7 --output reports/weekly_backtest.json
```

**Validate:**
- Backtest results align with PAPER results
- No significant degradation vs historical

### Friday Evening (Week End)

#### 1. Weekly Performance Report

```bash
python scripts/generate_weekly_report.py --week $(date +%W) --year $(date +%Y)
```

**Metrics to review:**
- Total weekly P&L
- Weekly win rate
- Max drawdown during week
- Strategy attribution
- KillSwitch activation count

#### 2. Strategic Review Meeting (15 minutes)

**Questions:**
1. Did we hit weekly target? Why/why not?
2. Which strategies performed best/worst?
3. Any KillSwitch emergency stops? Root cause?
4. Any market regime changes to note?
5. Action items for next week?

**Document in:** `reports/weekly_review_$(date +%Y%W).md`

---

## Monthly Operations

### First Day of Month

#### 1. Monthly Performance Report

```bash
python scripts/generate_monthly_report.py --month $(date +%m) --year $(date +%Y)
```

**Include:**
- Total monthly P&L
- Monthly win rate by strategy
- Sharpe ratio
- Max drawdown
- Strategy performance ranking
- Comparison to previous months

#### 2. Backtest Full Month

```bash
python scripts/run_backtest.py --profile full_24 --days 30 --output reports/monthly_backtest_$(date +%Y%m).json
```

**Validate:**
- PAPER results vs backtest results
- Strategy parameters still optimal?
- Market regime shifts?

#### 3. Strategy Calibration (if needed)

**If strategy underperforming for 30+ days:**

1. Review parameters in `config/strategies_institutional.yaml`
2. Run parameter optimization:
   ```bash
   python scripts/optimize_strategy.py --strategy mean_reversion_statistical --days 90
   ```
3. Backtest optimized parameters
4. Update config if improvement >5%

#### 4. Capital Allocation Review

**For PAPER:**
- If consistently profitable (>60% WR, <15% DD) → Consider scaling
- If WIN RATE declining → Reduce exposure or pause

**For LIVE:**
- Review position sizing
- Adjust max_positions if needed
- Update max_risk_per_trade based on volatility

---

## Pre-LIVE Checklist

### Before Going LIVE (First Time)

⚠️ **CRITICAL:** Complete ALL items before enabling LIVE mode.

#### Phase 1: PAPER Validation (30-90 days)

- [ ] GREEN_ONLY PAPER running 30+ days
- [ ] Win rate > 60% confirmed
- [ ] Max drawdown < 15%
- [ ] No KillSwitch emergency stops
- [ ] Execution rate > 80%
- [ ] No critical errors in logs

#### Phase 2: Technical Validation

- [ ] Smoke tests PASSING (100%)
- [ ] Broker connection tested
- [ ] API keys secured (environment variables)
- [ ] Broker account verified (correct type: demo/live)
- [ ] Commission/slippage settings accurate
- [ ] Position limits configured correctly

#### Phase 3: Risk Management Validation

- [ ] KillSwitch enabled: `enable_kill_switch=True`
- [ ] Layer 1 (per-trade): max_risk_per_trade ≤ 0.025
- [ ] Layer 2 (daily): max_daily_loss ≤ 0.05
- [ ] Layer 3 (circuit breaker): max_consecutive_losses = 5
- [ ] Layer 4 (emergency): emergency_drawdown_pct = 0.15
- [ ] Emergency contact/notification setup

#### Phase 4: Capital & Sizing

- [ ] Initial capital decided (start small: $1k-$5k)
- [ ] Position sizing validated in PAPER
- [ ] Correlation limits configured
- [ ] Max total exposure calculated
- [ ] Capital is RISK CAPITAL ONLY (can afford to lose)

#### Phase 5: Monitoring Setup

- [ ] Logging enabled (INFO level minimum)
- [ ] Daily report automation working
- [ ] Alert system configured (email/SMS)
- [ ] Monitoring dashboard accessible
- [ ] Backup systems in place

#### Phase 6: Emergency Procedures

- [ ] Manual stop procedure documented
- [ ] Emergency contact list updated
- [ ] Broker support number saved
- [ ] Rollback plan documented
- [ ] Team trained on emergency procedures

#### Phase 7: Final Checks

- [ ] Configuration YAML reviewed
- [ ] Profile correct (GREEN_ONLY for first LIVE)
- [ ] Execution mode: `ExecutionMode.LIVE`
- [ ] All team members notified
- [ ] Start time scheduled (low volatility period)
- [ ] Monitoring plan for first 24 hours

**Sign-off required:**
- Lead Developer: _______________
- Risk Manager: _______________
- Operations Manager: _______________
- Date: _______________

---

## Monitoring & Alerts

### Real-Time Monitoring (LIVE mode)

#### 1. Dashboard Metrics (Check Every Hour)

```python
# scripts/live_dashboard.py (conceptual)
import time

while True:
    stats = manager.get_statistics()
    ks_status = manager.get_killswitch_status()

    print(f"\n{'='*60}")
    print(f"LIVE DASHBOARD - {datetime.now()}")
    print(f"{'='*60}")
    print(f"Balance: ${stats['balance']:,.2f}")
    print(f"Daily P&L: ${stats['daily_pnl']:,.2f} ({stats['daily_pnl']/stats['balance']*100:.2f}%)")
    print(f"Open Positions: {len(manager.get_open_positions())}/{config.max_positions}")
    print(f"Total Trades Today: {stats['daily_trades']}")
    print(f"Win Rate: {stats['daily_win_rate']:.1%}")
    print(f"\nKillSwitch Status:")
    print(f"  Emergency Stop: {ks_status['emergency_stop_active']}")
    print(f"  Layer 1: {ks_status['layers']['layer1']['status']}")
    print(f"  Layer 2: {ks_status['layers']['layer2']['status']}")
    print(f"  Layer 3: {ks_status['layers']['layer3']['status']}")
    print(f"  Layer 4: {ks_status['layers']['layer4']['status']}")

    time.sleep(3600)  # Check every hour
```

#### 2. Alert Conditions

**CRITICAL (Immediate Action Required):**
- KillSwitch Layer 4 (Emergency) activated
- Daily loss > 4%
- System crash/restart
- Broker connection lost

**WARNING (Review within 1 hour):**
- Daily loss > 2%
- Win rate < 50% (10+ trades)
- KillSwitch Layer 3 (Circuit Breaker) activated
- Position count at max for >4 hours

**INFO (Review end of day):**
- Daily profit > 2%
- New strategy enabled
- Configuration changed

#### 3. Alert Delivery

**Email alerts:**
```python
# config/alerts.yaml
email:
  smtp_server: smtp.gmail.com
  from: trading-alerts@yourdomain.com
  to:
    - trader@yourdomain.com
    - risk-manager@yourdomain.com
  critical_only: false
```

**SMS alerts (CRITICAL only):**
```python
sms:
  service: twilio
  to: ["+1234567890"]
  critical_only: true
```

---

## Troubleshooting

### Common Issues

#### Issue 1: "KillSwitch Layer 2 activated - Daily loss limit"

**Symptoms:**
- Trading stopped mid-day
- Log message: "LAYER 2: Daily loss limit reached"

**Diagnosis:**
```python
status = manager.get_killswitch_status()
print(f"Daily P&L: ${status['daily_pnl']:.2f}")
print(f"Daily loss limit: ${status['max_daily_loss']:.2f}")
```

**Solution:**
1. **DO NOT** manually override
2. Review trades that led to loss
3. Wait until next day (auto-reset at midnight)
4. Consider reducing position sizing tomorrow

#### Issue 2: "Execution rate low (<50%)"

**Symptoms:**
- Many signals generated
- Few positions opened
- Log: "Signal rejected by KillSwitch"

**Diagnosis:**
```bash
grep "KILLSWITCH BLOCKED" logs/trading_system.log | wc -l
grep "KILLSWITCH BLOCKED" logs/trading_system.log | tail -20
```

**Possible causes:**
- Layer 1: Risk per trade too high (SL too wide)
- Layer 2: Daily loss limit already hit
- Layer 3: Strategy disabled (consecutive losses)
- Position limit reached

**Solution:**
- Review position sizing algorithm
- Check stop loss distances
- Verify strategy circuit breakers not triggered

#### Issue 3: "Performance degradation (WR dropped 20%)"

**Symptoms:**
- Win rate historically 65%, now 45%
- Last week profitable, this week not

**Diagnosis:**
```bash
# Compare last 2 weeks
python scripts/performance_comparison.py --week1 -2 --week2 -1
```

**Possible causes:**
- Market regime change
- Strategy parameters no longer optimal
- Increased volatility (wider stops being hit)

**Solution:**
1. Check market news (new regulations, economic events?)
2. Run backtest on recent 30 days
3. Consider parameter re-optimization
4. Temporarily reduce exposure or pause

#### Issue 4: "Smoke test failing"

**Symptoms:**
- `./run_all_smoke_tests.sh` shows FAILED

**Diagnosis:**
```bash
# Run individual test to see failure
python tests/smoke/test_microstructure_engine.py
```

**Possible causes:**
- Code change broke component
- Configuration YAML invalid
- Missing dependency

**Solution:**
1. Review error traceback
2. Check recent commits: `git log --oneline -10`
3. Revert if necessary: `git revert <commit>`
4. Fix issue and re-run smoke tests

---

## Emergency Procedures

### Emergency Stop (IMMEDIATE)

#### Scenario: Need to stop ALL trading NOW

**Steps:**
1. **Kill trading process:**
   ```bash
   # Find process
   ps aux | grep python | grep trading

   # Kill it
   kill -9 <PID>
   ```

2. **Activate emergency stop:**
   ```python
   # scripts/emergency_stop.py
   from src.risk.kill_switch import KillSwitch

   # Load KillSwitch from running system
   manager = load_execution_manager()  # Your loading logic
   manager.kill_switch.activate_emergency_stop("Manual emergency stop - [YOUR REASON]")

   print("✅ Emergency stop activated")
   print("All trading halted until manual reset")
   ```

3. **Close all open positions (if in LIVE):**
   ```python
   positions = manager.get_open_positions()
   for pos in positions:
       manager.broker.close_position(pos['position_id'])

   print(f"✅ Closed {len(positions)} positions")
   ```

4. **Notify team:**
   ```bash
   python scripts/send_alert.py --level CRITICAL --message "EMERGENCY STOP ACTIVATED"
   ```

5. **Document incident:**
   ```bash
   # Create incident report
   cat > incidents/incident_$(date +%Y%m%d_%H%M%S).md << EOF
   # Emergency Stop Incident

   **Time:** $(date)
   **Triggered by:** [NAME]
   **Reason:** [DETAILED REASON]

   ## Actions Taken:
   1. Process killed
   2. Emergency stop activated
   3. [X] positions closed

   ## Impact:
   - P&L at time of stop: \$[AMOUNT]
   - Open positions: [COUNT]

   ## Root Cause:
   [TO BE DETERMINED]

   ## Prevention:
   [TO BE ADDED]
   EOF
   ```

### Emergency Reset (After Issue Resolved)

#### Scenario: Emergency stop was activated, issue fixed, want to resume

**Steps:**
1. **Verify issue resolved:**
   - [ ] Root cause identified
   - [ ] Fix implemented
   - [ ] Smoke tests passing
   - [ ] Backtest shows expected behavior

2. **Reset KillSwitch:**
   ```python
   # scripts/reset_killswitch.py
   manager.kill_switch.reset_emergency_stop()
   print("✅ Emergency stop deactivated")

   # Verify
   status = manager.get_killswitch_status()
   assert not status['emergency_stop_active'], "Emergency stop still active!"
   ```

3. **Gradual restart:**
   - Start with PAPER mode first (even if was LIVE before)
   - Monitor for 1-2 hours
   - If stable, return to previous mode

4. **Document resolution:**
   ```bash
   # Append to incident report
   echo "## Resolution:" >> incidents/incident_[TIMESTAMP].md
   echo "- Issue: [DESCRIPTION]" >> incidents/incident_[TIMESTAMP].md
   echo "- Fix: [DESCRIPTION]" >> incidents/incident_[TIMESTAMP].md
   echo "- Tested: $(date)" >> incidents/incident_[TIMESTAMP].md
   echo "- Resumed: $(date)" >> incidents/incident_[TIMESTAMP].md
   ```

---

## Performance Benchmarks

### Expected Performance (GREEN_ONLY PAPER)

| Metric | Target | Acceptable | Poor |
|--------|--------|------------|------|
| Win Rate | >65% | 60-65% | <60% |
| R:R Avg | >2.5 | 2.0-2.5 | <2.0 |
| Max DD | <12% | 12-15% | >15% |
| Daily Trades | 3-8 | 2-10 | >10 |
| Execution Rate | >80% | 70-80% | <70% |
| Daily P&L Volatility | <2% | 2-3% | >3% |

### Expected Performance (FULL_24 PAPER)

| Metric | Target | Acceptable | Poor |
|--------|--------|------------|------|
| Win Rate | >62% | 58-62% | <58% |
| R:R Avg | >2.8 | 2.3-2.8 | <2.3 |
| Max DD | <15% | 15-18% | >18% |
| Daily Trades | 15-40 | 10-50 | >50 |
| Execution Rate | >75% | 65-75% | <65% |
| Daily P&L Volatility | <3% | 3-4% | >4% |

### System Performance

| Metric | Target | Measured |
|--------|--------|----------|
| Smoke Tests | <20s | ~15s ✅ |
| Feature Calculation | <100ms | ~40ms ✅ |
| Signal Processing | >100/s | ~150/s ✅ |
| Backtest (90 days) | <3min | ~2min ✅ |

---

## Maintenance Schedule

### Daily
- [ ] Morning health check (smoke tests)
- [ ] KillSwitch status check
- [ ] Evening performance review
- [ ] Daily report generation

### Weekly
- [ ] Review weekly targets
- [ ] Strategy performance ranking
- [ ] Extended backtest (7 days)
- [ ] Weekly review meeting

### Monthly
- [ ] Monthly performance report
- [ ] Full month backtest
- [ ] Strategy calibration review
- [ ] Capital allocation review

### Quarterly
- [ ] Comprehensive system audit
- [ ] Parameter optimization across all strategies
- [ ] Documentation updates
- [ ] Disaster recovery drill

---

## Contact Information

### Escalation Path

**Level 1 - Operational Issues:**
- Trading Team Lead
- Response time: <1 hour
- Examples: Daily performance questions, configuration changes

**Level 2 - Technical Issues:**
- System Administrator
- Response time: <30 minutes
- Examples: System crashes, broker connection issues

**Level 3 - Critical Issues:**
- CTO / Risk Manager
- Response time: <15 minutes
- Examples: Emergency stop needed, security breach

### External Contacts

**Broker Support:**
- Name: [BROKER NAME]
- Phone: [PHONE]
- Email: [EMAIL]
- Hours: 24/7

**System Vendor:**
- Name: PLAN OMEGA Development
- Support: See `docs/` folder
- Emergency: N/A (self-hosted)

---

## Revision History

| Version | Date | Changes | Author |
|---------|------|---------|--------|
| 1.0 | 2025-11-16 | Initial release | PLAN OMEGA |

---

**This runbook should be reviewed and updated quarterly.**
**Last review:** 2025-11-16
**Next review due:** 2026-02-16
