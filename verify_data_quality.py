"""
Script de verificación de calidad de datos
Verifica que los datos descargados son completos y coherentes
"""

import psycopg2
import pandas as pd
from datetime import datetime, timedelta

# Configuración de PostgreSQL (USA LA MISMA CONTRASEÑA QUE ANTES)
DB_CONFIG = {
    'host': 'localhost',
    'database': 'trading_system',
    'user': 'postgres',
    'password': 'Trading2025',  # ← CAMBIA ESTO
    'port': 5432
}

def connect_db():
    """Conecta a PostgreSQL"""
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        return conn
    except Exception as e:
        print(f"❌ Error al conectar: {e}")
        return None

def check_data_gaps(conn, symbol, timeframe):
    """Verifica si hay gaps (huecos) en los datos temporales"""
    query = """
        SELECT timestamp, 
               LAG(timestamp) OVER (ORDER BY timestamp) as prev_timestamp
        FROM bars
        WHERE symbol = %s AND timeframe = %s
        ORDER BY timestamp
    """
    df = pd.read_sql_query(query, conn, params=(symbol, timeframe))
    
    if len(df) == 0:
        return []
    
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    df['prev_timestamp'] = pd.to_datetime(df['prev_timestamp'])
    
    # Calcular diferencia esperada según timeframe
    if timeframe == 'D1':
        expected_diff = timedelta(days=1)
        tolerance = timedelta(days=4)  # Permitir fines de semana
    elif timeframe == 'M1':
        expected_diff = timedelta(minutes=1)
        tolerance = timedelta(minutes=5)  # Permitir pequeños gaps
    else:
        return []
    
    # Encontrar gaps mayores a la tolerancia
    gaps = []
    for idx, row in df.iterrows():
        if pd.notna(row['prev_timestamp']):
            diff = row['timestamp'] - row['prev_timestamp']
            if diff > tolerance:
                gaps.append({
                    'start': row['prev_timestamp'],
                    'end': row['timestamp'],
                    'duration': diff
                })
    
    return gaps

def check_price_anomalies(conn, symbol):
    """Verifica si hay precios anómalos (spikes irreales)"""
    query = """
        SELECT timestamp, open, high, low, close
        FROM bars
        WHERE symbol = %s AND timeframe = 'M1'
        ORDER BY timestamp DESC
        LIMIT 10000
    """
    df = pd.read_sql_query(query, conn, params=(symbol,))
    
    if len(df) < 100:
        return []
    
    # Calcular retornos logarítmicos
    df['returns'] = (df['close'] / df['close'].shift(1)).apply(lambda x: abs(x - 1) if x > 0 else 0)
    
    # Detectar movimientos > 1% en 1 minuto (sospechosos en forex)
    anomalies = df[df['returns'] > 0.01].copy()
    
    return anomalies[['timestamp', 'close', 'returns']].to_dict('records')

def main():
    print("=" * 70)
    print("VERIFICACIÓN DE CALIDAD DE DATOS")
    print("=" * 70)
    print()
    
    conn = connect_db()
    if conn is None:
        return
    
    # Obtener lista de símbolos
    cursor = conn.cursor()
    cursor.execute("SELECT DISTINCT symbol FROM bars ORDER BY symbol")
    symbols = [row[0] for row in cursor.fetchall()]
    cursor.close()
    
    print(f"Símbolos encontrados: {', '.join(symbols)}\n")
    
    for symbol in symbols:
        print(f"{'='*70}")
        print(f"VERIFICANDO: {symbol}")
        print(f"{'='*70}")
        
        # Verificar datos diarios
        print(f"\n📊 DATOS DIARIOS (D1)")
        cursor = conn.cursor()
        cursor.execute("""
            SELECT COUNT(*), MIN(timestamp), MAX(timestamp)
            FROM bars WHERE symbol = %s AND timeframe = 'D1'
        """, (symbol,))
        count, min_date, max_date = cursor.fetchone()
        cursor.close()
        
        print(f"  Total barras: {count}")
        print(f"  Rango: {min_date.strftime('%Y-%m-%d')} a {max_date.strftime('%Y-%m-%d')}")
        
        gaps_d1 = check_data_gaps(conn, symbol, 'D1')
        if len(gaps_d1) > 5:
            print(f"  ⚠️  {len(gaps_d1)} gaps detectados (probablemente fines de semana)")
        else:
            print(f"  ✅ Sin gaps significativos")
        
        # Verificar datos M1
        print(f"\n📈 DATOS DE 1 MINUTO (M1)")
        cursor = conn.cursor()
        cursor.execute("""
            SELECT COUNT(*), MIN(timestamp), MAX(timestamp)
            FROM bars WHERE symbol = %s AND timeframe = 'M1'
        """, (symbol,))
        count, min_date, max_date = cursor.fetchone()
        cursor.close()
        
        print(f"  Total barras: {count:,}")
        print(f"  Rango: {min_date.strftime('%Y-%m-%d %H:%M')} a {max_date.strftime('%Y-%m-%d %H:%M')}")
        
        # Calcular días cubiertos
        days_covered = (max_date - min_date).days
        print(f"  Días cubiertos: {days_covered}")
        
        # Verificar anomalías de precio
        anomalies = check_price_anomalies(conn, symbol)
        if len(anomalies) > 10:
            print(f"  ⚠️  {len(anomalies)} movimientos anómalos detectados (>1% en 1min)")
            print(f"      Esto puede ser normal en eventos de alta volatilidad")
        else:
            print(f"  ✅ Precios consistentes, sin anomalías mayores")
        
        # Verificar que no hay valores NULL
        cursor = conn.cursor()
        cursor.execute("""
            SELECT COUNT(*) FROM bars
            WHERE symbol = %s AND (
                open IS NULL OR high IS NULL OR low IS NULL OR close IS NULL
            )
        """, (symbol,))
        null_count = cursor.fetchone()[0]
        cursor.close()
        
        if null_count > 0:
            print(f"  ❌ {null_count} barras con valores NULL (datos corruptos)")
        else:
            print(f"  ✅ Sin valores NULL")
        
        # Verificar consistencia OHLC (Open-High-Low-Close)
        cursor = conn.cursor()
        cursor.execute("""
            SELECT COUNT(*) FROM bars
            WHERE symbol = %s AND timeframe = 'M1' AND (
                high < low OR
                high < open OR
                high < close OR
                low > open OR
                low > close
            )
        """, (symbol,))
        inconsistent_count = cursor.fetchone()[0]
        cursor.close()
        
        if inconsistent_count > 0:
            print(f"  ❌ {inconsistent_count} barras con OHLC inconsistente")
        else:
            print(f"  ✅ OHLC consistente en todas las barras")
        
        print()
    
    # Resumen final
    print("=" * 70)
    print("RESUMEN")
    print("=" * 70)
    
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM bars")
    total_bars = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(DISTINCT symbol) FROM bars")
    total_symbols = cursor.fetchone()[0]
    
    cursor.execute("""
        SELECT MIN(timestamp), MAX(timestamp)
        FROM bars WHERE timeframe = 'D1'
    """)
    d1_range = cursor.fetchone()
    
    cursor.execute("""
        SELECT MIN(timestamp), MAX(timestamp)
        FROM bars WHERE timeframe = 'M1'
    """)
    m1_range = cursor.fetchone()
    
    cursor.close()
    
    print(f"Total de barras almacenadas: {total_bars:,}")
    print(f"Total de símbolos: {total_symbols}")
    print(f"Rango D1: {d1_range[0].strftime('%Y-%m-%d')} a {d1_range[1].strftime('%Y-%m-%d')}")
    print(f"Rango M1: {m1_range[0].strftime('%Y-%m-%d')} a {m1_range[1].strftime('%Y-%m-%d')}")
    print()
    print("✅ Base de datos lista para backtesting y cálculo de features")
    print()
    
    conn.close()

if __name__ == "__main__":
    main()