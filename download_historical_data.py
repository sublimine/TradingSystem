"""
Script de descarga de datos históricos desde MT5 a PostgreSQL
Descarga 2 años de datos diarios y 3 meses de datos M1 para todos los símbolos
"""

import MetaTrader5 as mt5
import pandas as pd
import psycopg2
from psycopg2.extras import execute_batch
from datetime import datetime, timedelta
import time

# =============================================================================
# CONFIGURACIÓN
# =============================================================================

# Símbolos a descargar
SYMBOLS = ["EURUSD", "GBPUSD", "AUDUSD", "NZDUSD", "USDCAD", "USDJPY"]

# Configuración de PostgreSQL (CAMBIA LA CONTRASEÑA)
DB_CONFIG = {
    'host': 'localhost',
    'database': 'trading_system',
    'user': 'postgres',
    'password': 'Trading2025',  # ← CAMBIA ESTO por la contraseña de PostgreSQL
    'port': 5432
}

# =============================================================================
# FUNCIONES AUXILIARES
# =============================================================================

def initialize_mt5():
    """Inicializa la conexión con MT5"""
    print("Inicializando MetaTrader 5...")
    if not mt5.initialize():
        print(f"❌ Error al inicializar MT5: {mt5.last_error()}")
        return False
    print("✅ MT5 inicializado correctamente")
    return True

def connect_db():
    """Conecta a PostgreSQL"""
    try:
        print("Conectando a PostgreSQL...")
        conn = psycopg2.connect(**DB_CONFIG)
        print("✅ Conexión a PostgreSQL exitosa")
        return conn
    except Exception as e:
        print(f"❌ Error al conectar a PostgreSQL: {e}")
        return None

def download_bars(symbol, timeframe, bars_count, timeframe_name):
    """
    Descarga barras históricas desde MT5
    
    Args:
        symbol: Símbolo a descargar (ej: "EURUSD")
        timeframe: Constante de timeframe de MT5 (ej: mt5.TIMEFRAME_D1)
        bars_count: Número de barras a descargar
        timeframe_name: Nombre legible del timeframe (ej: "D1", "M1")
    
    Returns:
        DataFrame con las barras o None si hay error
    """
    print(f"  Descargando {bars_count} barras de {timeframe_name}...", end=" ")
    
    # Obtener las barras
    rates = mt5.copy_rates_from_pos(symbol, timeframe, 0, bars_count)
    
    if rates is None or len(rates) == 0:
        print(f"❌ Error")
        return None
    
    # Convertir a DataFrame
    df = pd.DataFrame(rates)
    
    # Convertir timestamp de segundos a datetime
    df['time'] = pd.to_datetime(df['time'], unit='s')
    
    # Renombrar columnas para que coincidan con la base de datos
    df = df.rename(columns={'time': 'timestamp'})
    
    # Añadir columnas de metadata
    df['symbol'] = symbol
    df['timeframe'] = timeframe_name
    
    print(f"✅ {len(df)} barras descargadas")
    return df

def insert_bars_to_db(conn, df):
    """
    Inserta barras en la base de datos
    
    Args:
        conn: Conexión a PostgreSQL
        df: DataFrame con las barras
    """
    if df is None or len(df) == 0:
        return 0
    
    cursor = conn.cursor()
    
    # Preparar los datos para inserción
    # Orden de columnas: symbol, timeframe, timestamp, open, high, low, close, tick_volume, spread, real_volume
    insert_query = """
        INSERT INTO bars (symbol, timeframe, timestamp, open, high, low, close, tick_volume, spread, real_volume)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (symbol, timeframe, timestamp) DO NOTHING;
    """
    
    # Convertir DataFrame a lista de tuplas
    data = []
    for _, row in df.iterrows():
        data.append((
            row['symbol'],
            row['timeframe'],
            row['timestamp'],
            float(row['open']),
            float(row['high']),
            float(row['low']),
            float(row['close']),
            int(row['tick_volume']),
            int(row['spread']) if 'spread' in row else 0,
            int(row['real_volume']) if 'real_volume' in row else 0
        ))
    
    # Insertar en lotes de 1000 filas (más eficiente)
    try:
        execute_batch(cursor, insert_query, data, page_size=1000)
        conn.commit()
        inserted = len(data)
        print(f"  💾 {inserted} barras insertadas en DB")
        return inserted
    except Exception as e:
        print(f"  ❌ Error al insertar: {e}")
        conn.rollback()
        return 0
    finally:
        cursor.close()

def check_existing_data(conn, symbol, timeframe):
    """Verifica cuántas barras ya existen en la DB para un símbolo/timeframe"""
    cursor = conn.cursor()
    cursor.execute(
        "SELECT COUNT(*) FROM bars WHERE symbol = %s AND timeframe = %s",
        (symbol, timeframe)
    )
    count = cursor.fetchone()[0]
    cursor.close()
    return count

# =============================================================================
# FUNCIÓN PRINCIPAL
# =============================================================================

def main():
    print("=" * 70)
    print("DESCARGA DE DATOS HISTÓRICOS - SISTEMA DE TRADING INSTITUCIONAL")
    print("=" * 70)
    print()
    
    # Inicializar MT5
    if not initialize_mt5():
        return
    
    # Conectar a base de datos
    conn = connect_db()
    if conn is None:
        mt5.shutdown()
        return
    
    # Estadísticas
    total_downloaded = 0
    total_inserted = 0
    start_time = time.time()
    
    # Descargar datos para cada símbolo
    for symbol in SYMBOLS:
        print()
        print(f"{'='*70}")
        print(f"SÍMBOLO: {symbol}")
        print(f"{'='*70}")
        
        # Verificar que el símbolo existe en MT5
        symbol_info = mt5.symbol_info(symbol)
        if symbol_info is None:
            print(f"⚠️  {symbol} no está disponible en MT5, saltando...")
            continue
        
        # DESCARGAR DATOS DIARIOS (2 años = ~520 barras)
        print(f"\n📊 DATOS DIARIOS (D1)")
        existing_daily = check_existing_data(conn, symbol, 'D1')
        print(f"  Barras existentes en DB: {existing_daily}")
        
        if existing_daily < 500:  # Si hay menos de 500, descargar
            df_daily = download_bars(symbol, mt5.TIMEFRAME_D1, 520, 'D1')
            if df_daily is not None:
                total_downloaded += len(df_daily)
                inserted = insert_bars_to_db(conn, df_daily)
                total_inserted += inserted
        else:
            print(f"  ✓ Ya hay suficientes datos diarios, saltando descarga")
        
        # DESCARGAR DATOS M1 (3 meses = ~90 días * 1440 min/día = ~130,000 barras)
        # Nota: MT5 puede tener límites en el número de barras que devuelve
        # Descargaremos en bloques de 50,000 barras (aproximadamente 35 días)
        print(f"\n📈 DATOS DE 1 MINUTO (M1)")
        existing_m1 = check_existing_data(conn, symbol, 'M1')
        print(f"  Barras existentes en DB: {existing_m1}")
        
        if existing_m1 < 100000:  # Si hay menos de 100k, descargar
            # Bloque 1: últimos ~35 días
            df_m1_recent = download_bars(symbol, mt5.TIMEFRAME_M1, 50000, 'M1')
            if df_m1_recent is not None:
                total_downloaded += len(df_m1_recent)
                inserted = insert_bars_to_db(conn, df_m1_recent)
                total_inserted += inserted
            
            # Bloque 2: ~35 días anteriores (offset de 50000 barras)
            print(f"  Descargando bloque 2 de M1...", end=" ")
            rates2 = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_M1, 50000, 50000)
            if rates2 is not None and len(rates2) > 0:
                df_m1_older = pd.DataFrame(rates2)
                df_m1_older['time'] = pd.to_datetime(df_m1_older['time'], unit='s')
                df_m1_older = df_m1_older.rename(columns={'time': 'timestamp'})
                df_m1_older['symbol'] = symbol
                df_m1_older['timeframe'] = 'M1'
                print(f"✅ {len(df_m1_older)} barras descargadas")
                total_downloaded += len(df_m1_older)
                inserted = insert_bars_to_db(conn, df_m1_older)
                total_inserted += inserted
            else:
                print("❌ Error")
            
            # Bloque 3: ~30 días más antiguos
            print(f"  Descargando bloque 3 de M1...", end=" ")
            rates3 = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_M1, 100000, 43000)
            if rates3 is not None and len(rates3) > 0:
                df_m1_oldest = pd.DataFrame(rates3)
                df_m1_oldest['time'] = pd.to_datetime(df_m1_oldest['time'], unit='s')
                df_m1_oldest = df_m1_oldest.rename(columns={'time': 'timestamp'})
                df_m1_oldest['symbol'] = symbol
                df_m1_oldest['timeframe'] = 'M1'
                print(f"✅ {len(df_m1_oldest)} barras descargadas")
                total_downloaded += len(df_m1_oldest)
                inserted = insert_bars_to_db(conn, df_m1_oldest)
                total_inserted += inserted
            else:
                print("❌ Error")
        else:
            print(f"  ✓ Ya hay suficientes datos M1, saltando descarga")
        
        # Pequeña pausa para no saturar MT5
        time.sleep(0.5)
    
    # Resumen final
    elapsed_time = time.time() - start_time
    print()
    print("=" * 70)
    print("RESUMEN DE DESCARGA")
    print("=" * 70)
    print(f"Total barras descargadas: {total_downloaded:,}")
    print(f"Total barras insertadas en DB: {total_inserted:,}")
    print(f"Tiempo transcurrido: {elapsed_time:.2f} segundos")
    print()
    
    # Verificar contenido final de la base de datos
    cursor = conn.cursor()
    cursor.execute("""
        SELECT timeframe, symbol, COUNT(*) as bars_count
        FROM bars
        GROUP BY timeframe, symbol
        ORDER BY timeframe, symbol
    """)
    results = cursor.fetchall()
    
    print("CONTENIDO ACTUAL DE LA BASE DE DATOS:")
    print("-" * 70)
    for timeframe, symbol, count in results:
        print(f"{symbol:10s} {timeframe:5s}: {count:,} barras")
    cursor.close()
    
    # Cerrar conexiones
    conn.close()
    mt5.shutdown()
    
    print()
    print("✅ Proceso completado exitosamente")
    print()

# =============================================================================
# EJECUTAR
# =============================================================================

if __name__ == "__main__":
    main()