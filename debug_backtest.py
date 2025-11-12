"""Debug backtest para identificar bloqueador."""
import pandas as pd
from datetime import datetime
from research import BacktestEngine, BacktestConfig
import logging

# Activar logging
logging.basicConfig(level=logging.DEBUG, format='%(levelname)s: %(message)s')

# Solo EURUSD para aislar problema
df = pd.read_csv('backtest/datasets/EURUSD_pro_synthetic.csv', parse_dates=['timestamp'], index_col='timestamp')
data = {'EURUSD.pro': df}

config = BacktestConfig(
    start_date=datetime(2024, 1, 1, 9, 0),
    end_date=datetime(2024, 1, 1, 16, 0),
    instruments=['EURUSD.pro'],
    initial_capital=10000.0
)

# Estrategia simple
signal_count = 0
def test_strategy(ts, bars):
    global signal_count
    if ts.minute % 10 == 0:
        signal_count += 1
        return [{'instrument': 'EURUSD.pro', 'direction': 1, 'size': 0.1, 'strategy_id': 'test'}]
    return []

print(f"Config: {config.start_date} to {config.end_date}")
print(f"Data bars: {len(df)}")
print(f"Bars in range: {len([d for d in df.index if config.start_date <= d <= config.end_date])}\n")

engine = BacktestEngine(config)
results = engine.run(data, test_strategy)

print(f"\nSignals generated: {signal_count}")
print(f"Trades executed: {results.total_trades}")
print(f"Final capital: ${engine._capital:.2f}")