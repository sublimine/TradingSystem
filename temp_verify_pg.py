
import psycopg2
try:
    conn = psycopg2.connect(
        host='localhost',
        port=5432,
        database='trading_system',
        user='trading_user',
        password='abc'
    )
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM market_data")
    count = cursor.fetchone()[0]
    print(f"Base de datos OK: {count:,} barras disponibles")
    cursor.close()
    conn.close()
except Exception as e:
    print(f"ERROR: {e}")
    exit(1)
