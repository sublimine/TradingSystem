"""Test de backtesting engine."""
import pandas as pd
from datetime import datetime
from research import BacktestEngine, BacktestConfig

print("=== BACKTEST ENGINE TEST ===\n")

# Cargar datos
instruments = ['EURUSD.pro', 'GBPUSD.pro']
data = {}

for instrument in instruments:
    filename = f"backtest/datasets/{instrument.replace('.', '_')}_synthetic.csv"
    df = pd.read_csv(filename, parse_dates=['timestamp'], index_col='timestamp')
    data[instrument] = df

print(f"Loaded {len(data)} instruments")
for inst, df in data.items():
    print(f"  {inst}: {len(df)} bars")

# Configurar backtest
config = BacktestConfig(
    start_date=datetime(2024, 1, 1, 9, 0),
    end_date=datetime(2024, 1, 1, 16, 0),
    instruments=list(data.keys()),
    initial_capital=10000.0,
    commission_per_lot=7.0,
    slippage_pct=0.0001
)

print(f"\nConfig: ${config.initial_capital:,.0f} capital, {len(config.instruments)} instruments")

# Estrategia simple: compra cuando RSI < 30
def simple_strategy(timestamp, current_bars):
    """Estrategia de ejemplo simple."""
    signals = []
    
    # Generar señal simple cada 50 barras
    if timestamp.minute % 50 == 0:
        for instrument, bar in current_bars.items():
            signals.append({
                'instrument': instrument,
                'direction': 1,  # Long
                'size': 0.5,
                'strategy_id': 'simple_rsi'
            })
    
    return signals

# Ejecutar backtest
print("\nRunning backtest...")
engine = BacktestEngine(config)
results = engine.run(data, simple_strategy)

print("\n=== RESULTS ===")
print(f"Total Return: {results.total_return_pct:.2f}%")
print(f"Annualized Return: {results.annualized_return_pct:.2f}%")
print(f"Sharpe Ratio: {results.sharpe_ratio:.2f}")
print(f"Max Drawdown: {results.max_drawdown_pct:.2f}%")
print(f"Calmar Ratio: {results.calmar_ratio:.2f}")
print()
print(f"Total Trades: {results.total_trades}")
print(f"Win Rate: {results.win_rate_pct:.1f}%")
print(f"Profit Factor: {results.profit_factor:.2f}")
print(f"Avg Win: ${results.avg_win:.2f}")
print(f"Avg Loss: ${results.avg_loss:.2f}")

# Guardar resultados
results.equity_curve.to_csv("backtest/results/equity_curve.csv")
print(f"\n✓ Results saved to backtest/results/")

print("\n✓ Backtest engine test complete\n")