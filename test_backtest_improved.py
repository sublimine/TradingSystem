"""Test de backtesting engine con estrategia mejorada."""
import pandas as pd
from datetime import datetime
from research import BacktestEngine, BacktestConfig

print("=== IMPROVED BACKTEST TEST ===\n")

# Cargar datos
instruments = ['EURUSD.pro', 'GBPUSD.pro']
data = {}

for instrument in instruments:
    filename = f"backtest/datasets/{instrument.replace('.', '_')}_synthetic.csv"
    df = pd.read_csv(filename, parse_dates=['timestamp'], index_col='timestamp')
    data[instrument] = df

print(f"Loaded {len(data)} instruments")

# Configurar backtest
config = BacktestConfig(
    start_date=datetime(2024, 1, 1, 9, 0),
    end_date=datetime(2024, 1, 1, 16, 0),
    instruments=list(data.keys()),
    initial_capital=10000.0,
    commission_per_lot=7.0,
    slippage_pct=0.0001
)

# Estrategia mejorada: genera trades cada 10 barras
def improved_strategy(timestamp, current_bars):
    """Estrategia que genera más trades para testing."""
    signals = []
    
    # Generar señal cada 10 barras (cada 10 minutos)
    if timestamp.minute % 10 == 0:
        for instrument, bar in current_bars.items():
            # Alternar long/short basado en minuto
            direction = 1 if timestamp.minute % 20 == 0 else -1
            
            signals.append({
                'instrument': instrument,
                'direction': direction,
                'size': 0.1,  # Tamaño pequeño para evitar rechazos
                'strategy_id': 'test_strategy'
            })
    
    return signals

# Ejecutar backtest
print("\nRunning backtest with improved strategy...")
engine = BacktestEngine(config)
results = engine.run(data, improved_strategy)

print("\n=== RESULTS ===")
print(f"Total Return: {results.total_return_pct:.2f}%")
print(f"Annualized Return: {results.annualized_return_pct:.2f}%")
print(f"Sharpe Ratio: {results.sharpe_ratio:.2f}")
print(f"Sortino Ratio: {results.sortino_ratio:.2f}")
print(f"Max Drawdown: {results.max_drawdown_pct:.2f}%")
print(f"Calmar Ratio: {results.calmar_ratio:.2f}")
print()
print(f"Total Trades: {results.total_trades}")
print(f"Winning Trades: {results.winning_trades}")
print(f"Losing Trades: {results.losing_trades}")
print(f"Win Rate: {results.win_rate_pct:.1f}%")
print(f"Profit Factor: {results.profit_factor:.2f}")
print(f"Avg Win: ${results.avg_win:.2f}")
print(f"Avg Loss: ${results.avg_loss:.2f}")

# Guardar
results.equity_curve.to_csv("backtest/results/equity_curve_improved.csv")
print(f"\n✓ Results saved")

if results.total_trades > 0:
    print(f"\n✓✓ BACKTEST SUCCESSFUL - {results.total_trades} trades executed")
else:
    print(f"\n✗✗ BACKTEST FAILED - No trades executed")

print()