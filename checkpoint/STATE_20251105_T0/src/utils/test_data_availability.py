import MetaTrader5 as mt5
from datetime import datetime, timedelta

mt5.initialize()

symbol = "EURUSD.pro"
print(f"Testing data availability for {symbol}")

# Try different date ranges
test_dates = [
    (datetime.now() - timedelta(days=7), "1 week ago"),
    (datetime.now() - timedelta(days=30), "1 month ago"),
    (datetime.now() - timedelta(days=90), "3 months ago"),
]

for start_date, label in test_dates:
    end_date = datetime.now()
    rates = mt5.copy_rates_range(symbol, mt5.TIMEFRAME_M1, start_date, end_date)
    
    if rates is not None and len(rates) > 0:
        print(f"SUCCESS {label}: Got {len(rates)} bars from {start_date} to {end_date}")
        break
    else:
        print(f"FAILED {label}: No data available")

mt5.shutdown()