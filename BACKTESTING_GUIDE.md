# Elite Backtesting Framework - Complete Guide

## Overview

Professional-grade backtesting framework with:
- ✅ Historical simulation with tick-level accuracy
- ✅ Transaction cost modeling (spread, slippage, commission)
- ✅ Walk-forward optimization
- ✅ Monte Carlo simulation
- ✅ Advanced risk metrics (Sharpe, Sortino, Calmar, Omega, Kappa)
- ✅ Strategy attribution and correlation analysis
- ✅ Comprehensive reporting system

---

## Why Backtest?

**WITHOUT BACKTESTING = FLYING BLIND**

You need to answer:
1. Do these strategies actually work on historical data?
2. Which strategies are profitable vs losers?
3. What are realistic Sharpe/Sortino/Win Rate expectations?
4. What's the max drawdown you should expect?
5. Are parameters overfitted or robust?

**Renaissance, Citadel, DE Shaw:** 10-20 years of backtesting before deployment.

**You:** MUST backtest 1-2 years minimum before risking real capital.

---

## Quick Start

### 1. Install Requirements

```bash
pip install pandas numpy scipy scikit-learn MetaTrader5
```

### 2. Load Historical Data

```python
import MetaTrader5 as mt5
from datetime import datetime, timedelta
import pandas as pd

# Initialize MT5
mt5.initialize()

# Load 3 months of M5 data
end_date = datetime.now()
start_date = end_date - timedelta(days=90)

rates = mt5.copy_rates_range('EURUSD', mt5.TIMEFRAME_M5, start_date, end_date)
df = pd.DataFrame(rates)
df['time'] = pd.to_datetime(df['time'], unit='s')
df.set_index('time', inplace=True)
```

### 3. Run Backtest

```python
from src.backtesting import BacktestEngine, PerformanceAnalyzer
from src.strategies import OrderBlockStrategy, StopHuntReversal

# Initialize strategies
strategies = [
    OrderBlockStrategy(config={'enabled': True}),
    StopHuntReversal(config={'enabled': True}),
]

# Create backtest engine
engine = BacktestEngine(
    strategies=strategies,
    initial_capital=10000.0,
    risk_per_trade=0.01,              # 1% risk per trade
    commission_per_lot=7.0,           # $7 round-trip
    slippage_pips=0.5,                # 0.5 pip slippage
    spread_pips={'EURUSD': 1.2}       # 1.2 pip spread
)

# Run backtest
results = engine.run_backtest(
    historical_data={'EURUSD': df},
    start_date=start_date,
    end_date=end_date
)

# Analyze performance
analyzer = PerformanceAnalyzer()
analysis = analyzer.analyze_backtest(results, save_report=True)

# Print results
print(f"Total Return: {results['total_return_r']:.2f}R")
print(f"Win Rate: {results['win_rate']:.2%}")
print(f"Sharpe: {analysis['risk_metrics']['sharpe_ratio']:.2f}")
print(f"Max DD: {abs(analysis['drawdown_analysis']['max_drawdown_r']):.2f}R")
```

---

## Advanced Features

### Walk-Forward Optimization

Prevents overfitting by dividing data into in-sample (training) and out-of-sample (testing) periods.

```python
wf_results = engine.run_walk_forward(
    historical_data={'EURUSD': df},
    in_sample_months=3,    # 3 months training
    out_sample_months=1,   # 1 month testing
    total_periods=4         # 4 iterations
)

print(f"WF Efficiency: {wf_results['wf_efficiency']:.2%}")

# Interpretation:
# > 70% = Excellent (parameters robust)
# > 50% = Good (acceptable degradation)
# > 30% = Marginal (possible overfitting)
# < 30% = Poor (severe overfitting)
```

### Monte Carlo Simulation

Assesses probability of achieving results by randomly reordering trades.

```python
# Extract trade returns
trades_df = pd.DataFrame(results['trades'])
trade_returns = trades_df['pnl_r'].values

# Run 1000 simulations
mc_results = engine.run_monte_carlo(
    trade_results=trade_returns,
    num_simulations=1000,
    confidence_level=0.95
)

print(f"P(Profit): {mc_results['probability_positive']:.2%}")
print(f"VaR 95%: {mc_results['var_95']:.2f}R")
print(f"Worst DD: {mc_results['worst_case_dd']:.2f}R")
```

---

## Performance Metrics Explained

### Sharpe Ratio
**Formula:** `(Mean Return - Risk Free Rate) / Std Dev * sqrt(252)`

- **Interpretation:**
  - < 1.0: Poor risk-adjusted returns
  - 1.0-2.0: Good
  - 2.0-3.0: Very Good
  - > 3.0: Excellent (institutional grade)

### Sortino Ratio
Like Sharpe, but only penalizes downside volatility.

- **Interpretation:**
  - > Sharpe: Good (upside volatility dominates)
  - ≈ Sharpe: Balanced
  - < Sharpe: Bad (excessive downside)

### Calmar Ratio
**Formula:** `Total Return / Max Drawdown`

- **Interpretation:**
  - < 1.0: Return doesn't justify drawdown
  - 1.0-3.0: Acceptable
  - > 3.0: Excellent

### Profit Factor
**Formula:** `Gross Profit / Gross Loss`

- **Interpretation:**
  - < 1.0: Losing system
  - 1.0-1.5: Marginal
  - 1.5-2.0: Good
  - > 2.0: Excellent

### Omega Ratio
Probability-weighted gains vs losses.

- **Interpretation:**
  - < 1.0: Losing
  - > 1.5: Good
  - > 2.0: Excellent

---

## Strategy Attribution

Analyze which strategies contribute most to P&L:

```python
attribution = analysis['strategy_attribution']

for strategy_name, metrics in attribution.items():
    print(f"\n{strategy_name}:")
    print(f"  Trades: {metrics['total_trades']}")
    print(f"  Win Rate: {metrics['win_rate']:.2%}")
    print(f"  Total P&L: {metrics['total_pnl_r']:.2f}R")
    print(f"  Sharpe: {metrics['sharpe']:.2f}")
```

**Actions:**
- **Negative P&L strategies:** Disable or optimize
- **Low Sharpe (<1.0):** Review parameters
- **High Sharpe (>2.0):** Increase allocation

---

## Drawdown Analysis

Understand worst losing periods:

```python
dd_analysis = analysis['drawdown_analysis']

print(f"Max DD: {abs(dd_analysis['max_drawdown_r']):.2f}R")
print(f"Avg DD: {abs(dd_analysis['avg_drawdown_depth_r']):.2f}R")
print(f"Avg Recovery: {dd_analysis['avg_recovery_trades']:.0f} trades")

# Top 5 drawdowns
for i, dd in enumerate(dd_analysis['top_5_drawdowns'], 1):
    print(f"{i}. Depth: {dd['depth_r']:.2f}R, Length: {dd['length_trades']} trades")
```

**Key Questions:**
1. Can you psychologically handle max DD?
2. How long does recovery take?
3. Are drawdowns concentrated in specific regimes?

---

## Recommendations System

Automatically generates actionable recommendations:

```python
recommendations = analyzer.generate_recommendations(analysis)

for rec in recommendations:
    print(rec)
```

**Example Output:**
```
⚠️  Sharpe ratio 0.85 below 1.0. Actions: 1) Review entry filters, 2) Optimize position sizing
⚠️  Win rate 48% below 50%. Actions: 1) Tighten entry criteria, 2) Trail profits sooner
🔴 Strategy 'spoofing_detection_l2' lost -8.2R. Consider: 1) Disable, 2) Optimize parameters
✅ Profit factor 2.35. System is robust.
```

---

## Multi-Symbol Backtesting

Test across multiple symbols to assess diversification:

```python
# Load multiple symbols
eurusd_data = load_data('EURUSD', start, end)
gbpusd_data = load_data('GBPUSD', start, end)
usdjpy_data = load_data('USDJPY', start, end)

results = engine.run_backtest(
    historical_data={
        'EURUSD': eurusd_data,
        'GBPUSD': gbpusd_data,
        'USDJPY': usdjpy_data
    },
    start_date=start,
    end_date=end
)

# Check symbol performance
symbol_perf = analysis['symbol_performance']
for symbol, metrics in symbol_perf.items():
    print(f"{symbol}: {metrics['total_r']:.2f}R, WR={metrics['win_rate']:.2%}")
```

---

## Transaction Cost Modeling

**CRITICAL:** Retail traders lose 30-40% of theoretical profits to costs.

### Costs Modeled:

1. **Spread:** Bid-ask spread (1-2 pips typical)
2. **Slippage:** Execution delay (0.5-1 pip)
3. **Commission:** Broker fees ($6-10 per lot round-trip)

```python
engine = BacktestEngine(
    strategies=strategies,
    commission_per_lot=7.0,        # $7 RT commission
    slippage_pips=0.5,             # 0.5 pip slippage
    spread_pips={
        'EURUSD': 1.2,             # 1.2 pip spread
        'GBPUSD': 1.8,
        'USDJPY': 1.5
    }
)
```

**Impact Example:**
- Theoretical: +50R over 3 months
- After spread: +38R (-12R = -24%)
- After slippage: +33R (-5R = -10%)
- After commission: +28R (-5R = -10%)
- **Net:** +28R (44% reduction from theoretical)

---

## Interpreting Results

### Minimum Acceptable Metrics (Retail+)
- **Total Trades:** > 30 (statistical significance)
- **Win Rate:** > 55%
- **Sharpe:** > 1.0
- **Profit Factor:** > 1.5
- **Max DD:** < 20R
- **Expectancy:** > 0.3R

### Institutional Grade Metrics
- **Total Trades:** > 100
- **Win Rate:** > 60%
- **Sharpe:** > 2.0
- **Profit Factor:** > 2.0
- **Max DD:** < 15R
- **Expectancy:** > 0.5R

### RED FLAGS (Do NOT Deploy)
- ❌ Sharpe < 0.5
- ❌ Win Rate < 50%
- ❌ Profit Factor < 1.2
- ❌ Max DD > 25R
- ❌ WF Efficiency < 30%
- ❌ P(Profit) < 60% (Monte Carlo)

---

## Example Workflow

### Phase 1: Initial Validation (1-2 weeks)

```python
# 1. Backtest 3 months
results_3m = run_backtest(days=90)

# 2. Check metrics
if results_3m['sharpe'] < 1.0:
    print("❌ Failed initial validation")
    exit()

print("✅ Passed initial validation")
```

### Phase 2: Extended Backtest (2-3 weeks)

```python
# 3. Backtest 1 year
results_1y = run_backtest(days=365)

# 4. Check consistency
if abs(results_1y['sharpe'] - results_3m['sharpe']) > 0.5:
    print("⚠️  Performance inconsistent across timeframes")

# 5. Strategy attribution
analyze_strategies(results_1y)
# Disable losing strategies
```

### Phase 3: Robustness Testing (1-2 weeks)

```python
# 6. Walk-forward optimization
wf = run_walk_forward(in_sample=3, out_sample=1, periods=4)

if wf['wf_efficiency'] < 0.5:
    print("❌ Overfitting detected")
    exit()

# 7. Monte Carlo
mc = run_monte_carlo(simulations=1000)

if mc['probability_positive'] < 0.65:
    print("❌ High probability of loss")
    exit()

print("✅ System passed robustness testing")
```

### Phase 4: Paper Trading (3-6 months)

```python
# 8. Deploy to demo account
# 9. Monitor daily/weekly reports
# 10. Compare live vs backtest metrics
# 11. Adjust if necessary

# IF live metrics match backtest (within 20%):
#    ✅ Ready for micro live deployment
# ELSE:
#    ❌ More optimization needed
```

---

## Common Mistakes

### 1. Insufficient Data
❌ **Bad:** 30 days backtest (10-20 trades)
✅ **Good:** 1+ year backtest (100+ trades)

### 2. Ignoring Transaction Costs
❌ **Bad:** No spread/commission modeling
✅ **Good:** Conservative cost estimates (1.5 pip spread + commission)

### 3. No Out-of-Sample Testing
❌ **Bad:** Optimize on full dataset
✅ **Good:** Walk-forward with 70/30 in-sample/out-sample split

### 4. Cherry-Picking Periods
❌ **Bad:** Only test bull markets
✅ **Good:** Test across regimes (trending, ranging, crisis)

### 5. No Monte Carlo
❌ **Bad:** Assume backtest results are deterministic
✅ **Good:** Run MC to understand probability distribution

---

## Next Steps

1. **Run `examples/backtest_example.py`** - See complete workflow
2. **Backtest 1 year of data** - Validate all 23 strategies
3. **Disable losing strategies** - Eliminate negative P&L strategies
4. **Optimize parameters** - Use walk-forward optimization
5. **Paper trade 3-6 months** - Validate live performance
6. **Micro deployment** - Start with $500-$1000 real capital
7. **Scale gradually** - Increase capital ONLY if metrics hold

---

## Support

For questions:
- Review examples in `examples/backtest_example.py`
- Check `src/backtesting/` source code
- Analyze saved reports in `backtest_reports/`

---

**Remember:** Backtesting is NOT optional. It's the difference between professional trading and gambling.

**Quote:** "In God we trust. All others must bring data." - W. Edwards Deming

---

Author: Elite Trading System
Version: 1.0
Last Updated: 2025-11-11
