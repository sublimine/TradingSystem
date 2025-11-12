"""Test de validación de datos."""
import pandas as pd
from execution import DataValidator

print("=== DATA VALIDATION TEST ===\n")

# Cargar datos
instruments = ['EURUSD_pro', 'GBPUSD_pro', 'XAUUSD_pro']

validator = DataValidator(
    outlier_std_threshold=5.0,
    volume_std_threshold=3.0
)

total_bars = 0
total_valid = 0
total_warnings = 0

for instrument in instruments:
    filename = f"backtest/datasets/{instrument}_synthetic.csv"
    df = pd.read_csv(filename, parse_dates=['timestamp'], index_col='timestamp')
    
    print(f"Validating {instrument}...")
    print(f"  Bars: {len(df)}")
    
    valid_count = 0
    warning_count = 0
    
    for idx, row in df.iterrows():
        is_valid, results = validator.validate_bar(
            instrument=instrument,
            timestamp=idx,
            open_price=row['open'],
            high=row['high'],
            low=row['low'],
            close=row['close'],
            volume=row['volume'],
            bid=row['bid'],
            ask=row['ask']
        )
        
        if is_valid:
            valid_count += 1
        
        # Contar warnings
        warning_count += sum(1 for r in results if r.severity.value == 'warning')
    
    total_bars += len(df)
    total_valid += valid_count
    total_warnings += warning_count
    
    print(f"  Valid: {valid_count}/{len(df)} ({valid_count/len(df)*100:.1f}%)")
    print(f"  Warnings: {warning_count}")
    print()

print("=== SUMMARY ===")
print(f"Total bars: {total_bars}")
print(f"Valid bars: {total_valid} ({total_valid/total_bars*100:.1f}%)")
print(f"Total warnings: {total_warnings}")
print("\n✓ Data validation complete\n")