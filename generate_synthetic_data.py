"""Generador de datos sintéticos para testing."""
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

def generate_market_data(
    instrument: str,
    start_date: datetime,
    bars: int,
    freq: str = '1min'
) -> pd.DataFrame:
    """Genera datos OHLCV sintéticos realistas."""
    
    # Base price
    if 'EUR' in instrument:
        base_price = 1.1000
        volatility = 0.0001
    elif 'GBP' in instrument:
        base_price = 1.2500
        volatility = 0.00015
    elif 'XAU' in instrument:
        base_price = 1950.0
        volatility = 0.5
    else:
        base_price = 1.0000
        volatility = 0.0001
    
    # Generate timestamps
    timestamps = pd.date_range(start=start_date, periods=bars, freq=freq)
    
    # Generate price path (geometric brownian motion)
    returns = np.random.normal(0, volatility, bars)
    price_multipliers = np.exp(np.cumsum(returns))
    close_prices = base_price * price_multipliers
    
    # Generate OHLC
    data = []
    for i in range(bars):
        close = close_prices[i]
        
        # Open cerca del close anterior
        if i == 0:
            open_price = base_price
        else:
            open_price = close_prices[i-1] * (1 + np.random.normal(0, volatility/2))
        
        # High/Low alrededor de open/close
        high = max(open_price, close) * (1 + abs(np.random.normal(0, volatility)))
        low = min(open_price, close) * (1 - abs(np.random.normal(0, volatility)))
        
        # Volume
        volume = np.random.uniform(50, 200)
        
        # Bid/Ask
        spread = base_price * 0.00015
        bid = close - spread/2
        ask = close + spread/2
        
        data.append({
            'timestamp': timestamps[i],
            'open': open_price,
            'high': high,
            'low': low,
            'close': close,
            'volume': volume,
            'bid': bid,
            'ask': ask
        })
    
    df = pd.DataFrame(data)
    df.set_index('timestamp', inplace=True)
    
    return df

if __name__ == '__main__':
    # Generar datos para 3 instrumentos
    instruments = ['EURUSD.pro', 'GBPUSD.pro', 'XAUUSD.pro']
    start = datetime(2024, 1, 1, 9, 0)
    
    for instrument in instruments:
        print(f"Generating {instrument}...")
        df = generate_market_data(instrument, start, bars=1000)
        
        # Guardar
        filename = f"backtest/datasets/{instrument.replace('.', '_')}_synthetic.csv"
        df.to_csv(filename)
        print(f"  Saved: {filename} ({len(df)} bars)")
    
    print("\nData generation complete")