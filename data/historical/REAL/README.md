# REAL Market Data Directory

**MANDATO 20 - MT5 Data Pipeline Institucional**

This directory contains **REAL historical market data** downloaded from MetaTrader 5 (or other real sources).

---

## ⚠️ CRITICAL DISTINCTION

### REAL vs SYNTHETIC Data

| Type | Location | Naming | Purpose | Use in Trading |
|------|----------|--------|---------|----------------|
| **REAL** | `data/historical/REAL/` | `REAL_{SYMBOL}_{TF}.csv` | Production calibration | ✅ YES - Safe for live trading |
| **SYNTHETIC** | `data/historical/` | `{SYMBOL}*_SYNTHETIC.csv` | Framework testing only | ❌ NO - Testing only |

**NON-NEGOTIABLE**: Only REAL data can be used for production calibration and live trading decisions.

---

## Naming Convention

All files in this directory follow institutional naming:

```
REAL_{SYMBOL}_{TIMEFRAME}.csv
```

**Examples**:
- `REAL_EURUSD_M15.csv` - EUR/USD, 15-minute bars
- `REAL_XAUUSD_H1.csv` - Gold, 1-hour bars
- `REAL_US500_D1.csv` - S&P 500, daily bars

**Timeframe Codes**:
- `M1` = 1 minute
- `M5` = 5 minutes
- `M15` = 15 minutes
- `M30` = 30 minutes
- `H1` = 1 hour
- `H4` = 4 hours
- `D1` = 1 day
- `W1` = 1 week
- `MN1` = 1 month

---

## CSV Format

All CSV files have the following structure:

```csv
timestamp,open,high,low,close,volume
2023-01-02 00:00:00+00:00,1.06720,1.06745,1.06698,1.06715,1234
2023-01-02 00:15:00+00:00,1.06715,1.06738,1.06702,1.06725,987
...
```

**Columns**:
- `timestamp`: UTC datetime (ISO 8601 format with timezone)
- `open`: Opening price
- `high`: Highest price in bar
- `low`: Lowest price in bar
- `close`: Closing price
- `volume`: Tick volume (MT5) or actual volume

**Data Quality Guarantees**:
- ✅ No NaN values
- ✅ High >= Low (validated and corrected)
- ✅ Open/Close within [Low, High] range
- ✅ Volume >= 0
- ✅ Outliers >50% price change flagged (but not removed)
- ✅ Completeness checked (missing bars logged)

---

## Data Sources

### Primary: MetaTrader 5 (MT5)

Downloaded using `scripts/download_mt5_history.py`:

```bash
# Check MT5 connection
python scripts/download_mt5_history.py --check-connection

# Download data
python scripts/download_mt5_history.py \
  --symbols EURUSD,XAUUSD,US500 \
  --timeframe M15 \
  --start 2023-01-01 \
  --end 2024-12-31 \
  --dest data/historical/REAL
```

### Alternative: CSV Import

If you have real data from another source (broker, vendor):

1. **Format Requirements**:
   - Must have columns: `timestamp, open, high, low, close, volume`
   - Timestamp must be UTC timezone-aware
   - NO missing data (gaps are acceptable for weekends/holidays)

2. **Naming Convention**:
   - MUST use `REAL_{SYMBOL}_{TF}.csv` naming
   - Place in `data/historical/REAL/` directory

3. **Validation**:
   - Run validation: `python scripts/validate_market_data.py data/historical/REAL/REAL_EURUSD_M15.csv`
   - Check for quality issues before use

---

## Current Data Status

**Last Updated**: Check file modification dates

To see what data is available:

```bash
ls -lh data/historical/REAL/
```

Expected files for MANDATO 19 minimum scope:
- `REAL_EURUSD_M15.csv`
- `REAL_XAUUSD_M15.csv`
- `REAL_US500_M15.csv`

Expected files for MANDATO 19 full calibration:
- 15 symbols × M15 timeframe = 15 CSV files

---

## Data Periods

### MANDATO 19 Calibration

**Calibration Period**: 2023-01-01 → 2024-06-30 (18 months)
- Used for strategy parameter optimization
- Walk-forward validation with rolling windows

**Hold-Out Period**: 2024-07-01 → 2024-12-31 (6 months)
- **NEVER** used during calibration
- Only used for final validation (MANDATO 18R FASE 4)

### Full Dataset

**Complete Range**: 2023-01-01 → 2024-12-31 (24 months)
- Recommended minimum for institutional calibration

**Extended History** (optional): 2020-01-01 → 2024-12-31 (5 years)
- For regime-aware calibration
- Includes COVID crash, post-COVID recovery, rate hikes

---

## Data Validation

All data downloaded via MT5DataClient undergoes institutional validation:

### Validation Checks

1. **NaN Detection**: Rows with missing values are dropped
2. **OHLC Logic**: High >= Low, Open/Close within [Low, High]
3. **Volume Validation**: No negative volumes
4. **Outlier Detection**: Price changes >50% are flagged
5. **Completeness**: Missing bars (gaps) are estimated and logged

### Validation Logs

Check `logs/data_downloads/` for detailed validation reports:

```
data/historical/REAL/REAL_EURUSD_M15.csv:
  ✅ Data quality OK - no issues found
  Total bars: 35,040
  Date range: 2023-01-02 00:00:00+00:00 to 2024-06-30 23:45:00+00:00
  Price range: 1.04123 to 1.12456
```

---

## Security Notes

### Credentials

**MT5 credentials are NEVER stored in this directory or Git**.

Credentials are managed via:
- Environment variables (`.env` file, gitignored)
- `config/mt5_data_config.yaml` uses `${ENV_VAR}` placeholders

See: `docs/RUNBOOK_MT5_DATA_ACQUISITION_*.md` for credential setup.

### Data Sensitivity

Market data itself is **NOT confidential** (publicly available from brokers).

However:
- ⚠️ Large datasets may be valuable (do not share unnecessarily)
- ⚠️ Proprietary indicators/features ARE confidential
- ⚠️ Trading signals/positions ARE confidential

---

## Troubleshooting

### No Files in This Directory

**Cause**: Data has not been downloaded yet.

**Solution**:

1. Set up MT5 connection (see RUNBOOK)
2. Run download script:
   ```bash
   python scripts/download_mt5_history.py --symbols EURUSD --timeframe M15 --start 2023-01-01 --end 2024-12-31
   ```

### MT5 Not Available

**Error**: `MT5 NOT AVAILABLE: MetaTrader5 module not installed`

**Solution**:

```bash
pip install MetaTrader5
```

**Note**: MT5 module only works on Windows. For Linux/Mac, use:
- CSV import from Windows machine
- Cloud VM with Windows + MT5
- Alternative data vendor

### MT5 Connection Failed

**Error**: `MT5 CONNECTION FAILED`

**Troubleshooting**:
1. Ensure MT5 terminal is **running** and **logged in**
2. Enable **auto-trading** in MT5 terminal (Tools → Options → Expert Advisors)
3. Check **firewall** settings (allow MT5 connections)
4. Verify credentials in `.env` file

See detailed troubleshooting: `docs/RUNBOOK_MT5_DATA_ACQUISITION_*.md`

---

## Integration with Calibration Pipeline

### MANDATO 19 - Calibration Execution

Real data from this directory is used by:

1. **BacktestDataLoader** (`src/backtest/backtest_data_loader.py`)
   - Loads REAL data automatically
   - Validates format and quality

2. **Calibration Sweep** (`scripts/run_calibration_sweep.py`)
   - Uses REAL data for strategy optimization
   - Walk-forward validation across calibration period

3. **Hold-Out Validation** (`scripts/run_calibration_holdout.py`)
   - Tests calibrated strategies on unseen hold-out period

### Usage Example

```bash
# 1. Download data
python scripts/download_mt5_history.py --symbols EURUSD,XAUUSD,US500 --timeframe M15 --start 2023-01-01 --end 2024-12-31

# 2. Verify data
ls -lh data/historical/REAL/

# 3. Run calibration (MANDATO 19)
python scripts/run_calibration_sweep.py --strategy liquidity_sweep

# 4. Hold-out validation
python scripts/run_calibration_holdout.py
```

---

## Maintenance

### Re-downloading Data

If you need to refresh data (e.g., broker changed data, found issues):

1. **Backup** existing data:
   ```bash
   mv data/historical/REAL data/historical/REAL_backup_$(date +%Y%m%d)
   mkdir data/historical/REAL
   ```

2. **Re-download**:
   ```bash
   python scripts/download_mt5_history.py --symbols EURUSD,XAUUSD,US500 --timeframe M15 --start 2023-01-01 --end 2024-12-31
   ```

3. **Compare** old vs new (check for material differences):
   ```bash
   python scripts/compare_market_data.py data/historical/REAL_backup_20251114/REAL_EURUSD_M15.csv data/historical/REAL/REAL_EURUSD_M15.csv
   ```

### Extending History

To download additional historical data:

```bash
# Download extended history (5 years)
python scripts/download_mt5_history.py \
  --symbols EURUSD \
  --timeframe M15 \
  --start 2020-01-01 \
  --end 2024-12-31
```

Note: Older data may have lower quality or be unavailable from broker.

---

## References

- **MANDATO 20**: Data Pipeline Institucional (this implementation)
- **MANDATO 19**: Calibration Execution (consumer of this data)
- **MANDATO 18R**: Calibration Framework (defines data periods)
- **MANDATO 17**: Backtest Engine (data loader integration)

**Docs**:
- `docs/DATA_PIPELINE_MANDATO20_*.md` - Architecture and design
- `docs/RUNBOOK_MT5_DATA_ACQUISITION_*.md` - Step-by-step VPS setup
- `docs/MANDATO20_STATUS_*.md` - Implementation status

---

**Last Updated**: 2025-11-14
**Mandato**: MANDATO 20
**Autor**: SUBLIMINE Institutional Trading System
