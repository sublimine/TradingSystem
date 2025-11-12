import psycopg2
from datetime import datetime

DB_CONFIG = {
    'host': 'localhost',
    'port': 5432,
    'database': 'trading_system',
    'user': 'trading_user',
    'password': 'abc'
}

conn = psycopg2.connect(**DB_CONFIG)
cursor = conn.cursor()

print("=" * 80)
print("LIMPIEZA DE BASE DE DATOS")
print("=" * 80)

# Verificar estado actual
cursor.execute("SELECT symbol, MIN(time), MAX(time), COUNT(*) FROM market_data GROUP BY symbol ORDER BY symbol")
current_state = cursor.fetchall()

print("\nEstado actual de market_data:")
for symbol, min_time, max_time, count in current_state:
    print(f"{symbol:15} | {min_time.date()} a {max_time.date()} | {count:,} barras")

# Los datos de Yahoo Finance tienen características identificables:
# - Volumen tick_volume = 1000 (valor constante que usamos durante importación)
# - Fechas anteriores a los últimos 129 días desde hoy

print("\n" + "=" * 80)
print("Eliminando datos de Yahoo Finance...")
print("=" * 80)

# Mantener solo los últimos 150 días de datos (margen de seguridad para los 129 días originales de MT5)
cursor.execute("""
    DELETE FROM market_data 
    WHERE time < NOW() - INTERVAL '150 days'
""")
deleted_old = cursor.rowcount
print(f"Eliminadas {deleted_old:,} barras con fechas antiguas (>150 días)")

# Eliminar datos con características de Yahoo Finance
cursor.execute("""
    DELETE FROM market_data 
    WHERE tick_volume = 1000 AND spread = 0 AND real_volume = 0
""")
deleted_yahoo = cursor.rowcount
print(f"Eliminadas {deleted_yahoo:,} barras con características de Yahoo Finance")

conn.commit()

# Verificar estado después de limpieza
cursor.execute("SELECT symbol, MIN(time), MAX(time), COUNT(*) FROM market_data GROUP BY symbol ORDER BY symbol")
clean_state = cursor.fetchall()

print("\n" + "=" * 80)
print("Estado después de limpieza:")
print("=" * 80)

total_bars = 0
for symbol, min_time, max_time, count in clean_state:
    print(f"{symbol:15} | {min_time.date()} a {max_time.date()} | {count:,} barras")
    total_bars += count

print(f"\nTotal de barras limpias: {total_bars:,}")
print(f"Total de símbolos: {len(clean_state)}")

cursor.close()
conn.close()

print("\n" + "=" * 80)
print("LIMPIEZA COMPLETADA")
print("=" * 80)
