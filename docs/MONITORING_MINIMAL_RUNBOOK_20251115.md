# Monitoring Minimal Runbook - MANDATO 26

**Date**: 2025-11-15
**Mandate**: M26 - Production Hardening
**Classification**: OPERATIONAL

---

## PURPOSE

Lightweight monitoring framework for SUBLIMINE trading system without full observability stack (Grafana, Prometheus, etc.).

**Philosophy**: JSON snapshots + manual review for institutional desk monitoring.

---

## COMPONENTS

### 1. Metrics Exporter
**Module**: `src/monitoring/metrics_exporter.py`
**Purpose**: Generate JSON snapshots of system metrics
**Output**: `reports/health/metrics_snapshot_<timestamp>.json`

### 2. Export Script
**Script**: `scripts/export_metrics_snapshot.py`
**Purpose**: CLI tool to generate snapshots
**Usage**: One-command snapshot export

### 3. Snapshot Reports
**Location**: `reports/health/`
**Format**: JSON (machine-readable)
**Retention**: Last 30 days

---

## USAGE

### Generate Snapshot (Demo Mode)
```bash
# Quick test without live data
python scripts/export_metrics_snapshot.py --demo --mode PAPER
```

**Output**:
```json
{
  "timestamp": "2025-11-15T09:04:58.137579",
  "mode": "PAPER",
  "uptime_seconds": 0.0,
  "kill_switch": {
    "state": "ACTIVE",
    "reason": null,
    "blocked_since": null,
    "total_blocks": 0
  },
  "positions": {
    "open_positions": 0,
    "total_exposure_pct": 0.0,
    "max_exposure_pct": 0.0,
    "positions_by_symbol": {}
  },
  "pnl": {
    "daily_pnl": 0.0,
    "daily_pnl_pct": 0.0,
    "current_drawdown": 0.0,
    "max_drawdown": 0.0,
    "total_trades_today": 0,
    "winning_trades": 0,
    "losing_trades": 0
  },
  "signals": {
    "signals_generated": 0,
    "signals_rejected": 0,
    "reject_rate_pct": 0.0,
    "avg_signal_quality": 0.0,
    "signals_by_strategy": {}
  },
  "microstructure": {
    "symbols": [],
    "avg_vpin": 0.0,
    "avg_ofi": 0.0,
    "avg_cvd": 0.0,
    "extreme_vpin_count": 0
  },
  "alerts": [],
  "demo_mode": true,
  "note": "Demo snapshot - system not running"
}
```

---

### Generate Snapshot (Live Mode)
```bash
# From live system (future implementation)
python scripts/export_metrics_snapshot.py --mode LIVE --capital 50000
```

**Note**: Live mode integration pending - requires system to expose metrics API.

---

### Custom Output Path
```bash
python scripts/export_metrics_snapshot.py --demo --output /tmp/snapshot.json
```

---

## METRICS CATALOG

### Kill Switch Metrics
```json
"kill_switch": {
  "state": "ACTIVE|BLOCKED",
  "reason": "string|null",
  "blocked_since": "ISO timestamp|null",
  "total_blocks": 0
}
```

**Key Values**:
- `state`: "ACTIVE" = trading allowed, "BLOCKED" = trading stopped
- `reason`: Why kill switch triggered (if BLOCKED)
- `blocked_since`: When kill switch activated
- `total_blocks`: Lifetime block count

**Alerts**:
- `state == "BLOCKED"` → 🚨 CRITICAL
- `total_blocks > 0` → ⚠️ Review history

---

### Position Metrics
```json
"positions": {
  "open_positions": 3,
  "total_exposure_pct": 45.5,
  "max_exposure_pct": 20.2,
  "positions_by_symbol": {
    "EURUSD": 20.2,
    "GBPUSD": 15.3,
    "USDJPY": 10.0
  }
}
```

**Key Values**:
- `open_positions`: Number of active positions
- `total_exposure_pct`: Sum of all position exposures (% of capital)
- `max_exposure_pct`: Largest single position exposure
- `positions_by_symbol`: Breakdown by symbol

**Alerts**:
- `total_exposure_pct > 200%` → ⚠️ HIGH EXPOSURE
- `max_exposure_pct > 50%` → ⚠️ CONCENTRATED RISK
- `open_positions > 10` → ⚠️ OVER-DIVERSIFIED

---

### P&L Metrics
```json
"pnl": {
  "daily_pnl": -250.50,
  "daily_pnl_pct": -2.51,
  "current_drawdown": 320.00,
  "max_drawdown": 450.00,
  "total_trades_today": 15,
  "winning_trades": 8,
  "losing_trades": 7
}
```

**Key Values**:
- `daily_pnl`: Today's realized P&L ($)
- `daily_pnl_pct`: Today's P&L as % of capital
- `current_drawdown`: Current drawdown from peak ($)
- `max_drawdown`: Maximum historical drawdown ($)
- `total_trades_today`: Trades executed today
- `winning_trades`: Profitable trades today
- `losing_trades`: Unprofitable trades today

**Alerts**:
- `daily_pnl_pct < -2%` → ⚠️ DAILY LOSS LIMIT
- `current_drawdown > max_drawdown * 0.9` → ⚠️ APPROACHING MAX DD
- `losing_trades > winning_trades * 2` → ⚠️ WIN RATE DETERIORATION

---

### Signal Metrics
```json
"signals": {
  "signals_generated": 45,
  "signals_rejected": 28,
  "reject_rate_pct": 62.2,
  "avg_signal_quality": 3.2,
  "signals_by_strategy": {
    "vpin_reversal_extreme": 12,
    "order_flow_toxicity": 8,
    "idp_inducement_distribution": 6
  }
}
```

**Key Values**:
- `signals_generated`: Total signals in recent window (last 100)
- `signals_rejected`: Signals filtered by Brain
- `reject_rate_pct`: % of signals rejected
- `avg_signal_quality`: Average confirmation score
- `signals_by_strategy`: Breakdown by strategy

**Alerts**:
- `reject_rate_pct > 50%` → ⚠️ HIGH REJECT RATE (market conditions poor)
- `reject_rate_pct < 10%` → ⚠️ LOW REJECT RATE (Brain may be too permissive)
- `avg_signal_quality < 2.5` → ⚠️ LOW QUALITY SIGNALS
- `signals_generated == 0` → ⚠️ NO SIGNALS (strategies inactive)

---

### Microstructure Metrics
```json
"microstructure": {
  "symbols": ["EURUSD", "GBPUSD", "USDJPY"],
  "avg_vpin": 0.45,
  "avg_ofi": 0.02,
  "avg_cvd": 1200.5,
  "extreme_vpin_count": 1
}
```

**Key Values**:
- `symbols`: Active symbols being monitored
- `avg_vpin`: Average VPIN across all symbols
- `avg_ofi`: Average OFI (order flow imbalance)
- `avg_cvd`: Average CVD (cumulative volume delta)
- `extreme_vpin_count`: Number of symbols with VPIN > 0.7

**Alerts**:
- `avg_vpin > 0.7` → ⚠️ TOXIC FLOW (reduce exposure)
- `extreme_vpin_count > len(symbols) * 0.5` → ⚠️ WIDESPREAD TOXICITY
- `avg_ofi > 0.8` or `< -0.8` → ⚠️ EXTREME ORDER FLOW

---

### Alerts Array
```json
"alerts": [
  "🚨 KILL SWITCH BLOCKED: Daily loss limit exceeded",
  "⚠️ HIGH EXPOSURE: 215.3% (threshold: 200%)",
  "⚠️ DAILY LOSS: -2.5% (threshold: -2%)"
]
```

**Format**: Pre-generated alert strings based on thresholds

**Alert Types**:
- 🚨 CRITICAL (kill switch, system failures)
- ⚠️ WARNING (thresholds exceeded, degraded performance)

---

## MONITORING WORKFLOW

### Hourly Check (Automated via Cron)
```bash
# Add to crontab
0 * * * * cd /path/to/TradingSystem && python scripts/export_metrics_snapshot.py --mode LIVE --capital 50000 >> /var/log/sublimine/hourly_metrics.log 2>&1
```

**Purpose**: Continuous metrics collection for post-mortem analysis

---

### Manual Check (Risk Manager)
```bash
# Generate snapshot
python scripts/export_metrics_snapshot.py --demo --mode LIVE

# Review latest snapshot
cat reports/health/metrics_snapshot_<latest>.json | jq .

# Check for alerts
cat reports/health/metrics_snapshot_<latest>.json | jq '.alerts[]'
```

**Frequency**:
- Pre-market: Once before session start
- Intraday: Every 2 hours during session
- Post-market: Once after session close

---

### Emergency Check (Incident Response)
```bash
# Quick snapshot
python scripts/export_metrics_snapshot.py --demo --mode LIVE

# Check kill switch status
cat reports/health/metrics_snapshot_<latest>.json | jq '.kill_switch'

# Check alerts
cat reports/health/metrics_snapshot_<latest>.json | jq '.alerts[]'

# Check positions
cat reports/health/metrics_snapshot_<latest>.json | jq '.positions'
```

**Purpose**: Rapid assessment during incidents

---

## THRESHOLDS & INTERPRETATION

### Kill Switch
| Metric | Threshold | Severity | Action |
|--------|-----------|----------|--------|
| state == "BLOCKED" | N/A | 🚨 CRITICAL | Investigate immediately |
| total_blocks > 5 | Daily | ⚠️ WARNING | Review kill switch logic |

### Positions
| Metric | Threshold | Severity | Action |
|--------|-----------|----------|--------|
| total_exposure_pct | > 200% | ⚠️ WARNING | Reduce exposure |
| total_exposure_pct | > 300% | 🚨 CRITICAL | Force liquidation |
| max_exposure_pct | > 50% | ⚠️ WARNING | Diversify |

### P&L
| Metric | Threshold | Severity | Action |
|--------|-----------|----------|--------|
| daily_pnl_pct | < -2% | ⚠️ WARNING | Review strategy performance |
| daily_pnl_pct | < -5% | 🚨 CRITICAL | Trigger kill switch |
| current_drawdown | > max_drawdown * 0.9 | ⚠️ WARNING | Approaching max DD |

### Signals
| Metric | Threshold | Severity | Action |
|--------|-----------|----------|--------|
| reject_rate_pct | > 50% | ⚠️ WARNING | Market conditions poor |
| reject_rate_pct | > 80% | 🚨 CRITICAL | Consider session pause |
| avg_signal_quality | < 2.5 | ⚠️ WARNING | Strategy recalibration needed |

### Microstructure
| Metric | Threshold | Severity | Action |
|--------|-----------|----------|--------|
| avg_vpin | > 0.7 | ⚠️ WARNING | Toxic flow - reduce size |
| avg_vpin | > 0.85 | 🚨 CRITICAL | Toxic flow - halt trading |
| extreme_vpin_count | > 50% of symbols | ⚠️ WARNING | Widespread toxicity |

---

## INTEGRATION (Future)

### Grafana Dashboard (Optional)
```bash
# Parse JSON snapshots into Prometheus format
# Feed to Grafana for visualization
# Not implemented yet - manual review sufficient
```

### Alerting (Optional)
```bash
# Check alerts array and send notifications
cat reports/health/metrics_snapshot_<latest>.json | jq '.alerts[]' | mail -s "SUBLIMINE Alerts" ops@sublimine.com
```

### API Endpoint (Future)
```python
# Expose metrics via HTTP endpoint
# GET /api/metrics → latest snapshot
# Not implemented yet
```

---

## TROUBLESHOOTING

### Snapshot Generation Fails
**Symptom**: Script exits with error
**Cause**: System component not accessible
**Resolution**: Check logs, verify system running, use `--demo` mode for testing

### Missing Metrics
**Symptom**: Some metrics show 0.0 or empty
**Cause**: Component not initialized or no activity
**Resolution**: Verify component is running and has data

### High Memory Usage
**Symptom**: Snapshot generation slow
**Cause**: Large trade/signal history
**Resolution**: Limit history to recent window (last 100)

---

## REFERENCES

- **Metrics Exporter**: `src/monitoring/metrics_exporter.py`
- **Export Script**: `scripts/export_metrics_snapshot.py`
- **Health Checks**: `docs/MANDATO26_PRODUCTION_HEALTHCHECKS_20251115.md`

---

**Document Version**: 1.0
**Last Updated**: 2025-11-15
**Owner**: SRE Team
