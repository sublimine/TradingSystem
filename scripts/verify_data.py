import psycopg2

DB_CONFIG = {
    'host': 'localhost',
    'port': 5432,
    'database': 'trading_system',
    'user': 'trading_user',
    'password': 'abc'
}

conn = psycopg2.connect(**DB_CONFIG)
cursor = conn.cursor()

cursor.execute("""
    SELECT 
        symbol,
        COUNT(*) as bars,
        MIN(time)::date as first_date,
        MAX(time)::date as last_date,
        MAX(time)::date - MIN(time)::date as days_coverage
    FROM market_data
    GROUP BY symbol
    ORDER BY symbol
""")

results = cursor.fetchall()

print("\n" + "=" * 80)
print("DATOS DISPONIBLES PARA BACKTESTING")
print("=" * 80)

for symbol, bars, first, last, days in results:
    print(f"{symbol:15} | {bars:4} barras | {first} a {last} ({days} días)")

total = sum(r[1] for r in results)
print(f"\nTotal: {total:,} barras en {len(results)} símbolos")

cursor.close()
conn.close()
