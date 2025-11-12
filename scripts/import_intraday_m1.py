"""
Intraday Data Import: 1-minute bars from MetaTrader 5
Imports high-resolution data required for sophisticated strategy evaluation
"""

import MetaTrader5 as mt5
import psycopg2
import pandas as pd
from datetime import datetime, timedelta
import time

DB_CONFIG = {
    'host': 'localhost',
    'port': 5432,
    'database': 'trading_system',
    'user': 'trading_user',
    'password': 'abc'
}

SYMBOLS = [
    'EURUSD.pro', 'GBPUSD.pro', 'USDJPY.pro', 'AUDUSD.pro',
    'USDCAD.pro', 'USDCHF.pro', 'NZDUSD.pro', 'EURGBP.pro',
    'XAUUSD.pro', 'BTCUSD', 'ETHUSD'
]

START_DATE = datetime(2025, 9, 1)
END_DATE = datetime.now()

print("=" * 80)
print("IMPORTACIÓN DE DATOS INTRADAY DE 1 MINUTO")
print("=" * 80)
print(f"Período: {START_DATE.date()} a {END_DATE.date()}")
print(f"Símbolos: {len(SYMBOLS)}")
print(f"Timeframe: M1 (1 minuto)")
print("=" * 80)

if not mt5.initialize():
    print("ERROR: No se pudo inicializar MetaTrader 5")
    print("Verifique que MT5 está ejecutándose y conectado al broker")
    exit(1)

account_info = mt5.account_info()
print(f"\nConectado a: {account_info.server}")
print(f"Cuenta: {account_info.login}\n")

conn = psycopg2.connect(**DB_CONFIG)

# Limpiar datos existentes para reimportar correctamente
cursor = conn.cursor()
cursor.execute("DELETE FROM market_data")
conn.commit()
print(f"Base de datos limpiada para reimportación\n")

total_bars_imported = 0

for symbol in SYMBOLS:
    print(f"Importando {symbol}...")
    
    try:
        # Obtener datos de 1 minuto desde MT5
        rates = mt5.copy_rates_range(symbol, mt5.TIMEFRAME_M1, START_DATE, END_DATE)
        
        if rates is None or len(rates) == 0:
            print(f"  ✗ No hay datos disponibles")
            continue
        
        df = pd.DataFrame(rates)
        df['time'] = pd.to_datetime(df['time'], unit='s')
        
        print(f"  Descargadas {len(df):,} barras de M1")
        
        # Importar a base de datos en lotes
        cursor = conn.cursor()
        imported_count = 0
        batch_size = 1000
        
        for i in range(0, len(df), batch_size):
            batch = df.iloc[i:i+batch_size]
            
            for _, row in batch.iterrows():
                try:
                    cursor.execute("""
                        INSERT INTO market_data (
                            symbol, time, open, high, low, close,
                            tick_volume, spread, real_volume
                        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                        ON CONFLICT (symbol, time) DO NOTHING
                    """, (
                        symbol,
                        row['time'],
                        float(row['open']),
                        float(row['high']),
                        float(row['low']),
                        float(row['close']),
                        int(row['tick_volume']),
                        int(row['spread']),
                        int(row['real_volume'])
                    ))
                    imported_count += 1
                except:
                    pass
            
            conn.commit()
            
            progress = min((i + batch_size) / len(df) * 100, 100)
            print(f"  Progreso: {progress:.0f}%", end='\r')
        
        print(f"  ✓ Importadas {imported_count:,} barras de M1")
        total_bars_imported += imported_count
        
        time.sleep(0.5)
        
    except Exception as e:
        print(f"  ✗ Error: {str(e)[:60]}")

cursor.close()
conn.close()
mt5.shutdown()

print("\n" + "=" * 80)
print("IMPORTACIÓN COMPLETADA")
print("=" * 80)
print(f"Total de barras importadas: {total_bars_imported:,}")

# Verificación final
conn = psycopg2.connect(**DB_CONFIG)
cursor = conn.cursor()

cursor.execute("""
    SELECT symbol, COUNT(*), MIN(time), MAX(time)
    FROM market_data
    GROUP BY symbol
    ORDER BY symbol
""")

results = cursor.fetchall()

print("\nDatos disponibles en base de datos:")
for symbol, count, min_time, max_time in results:
    days = (max_time - min_time).days
    print(f"  {symbol:15} {count:7,} barras | {min_time.date()} a {max_time.date()} ({days} días)")

cursor.close()
conn.close()

print("\n" + "=" * 80)
