"""
ETL Incremental: MT5 -> PostgreSQL
Sincroniza datos M1 desde ultima actualizacion
"""

import MetaTrader5 as mt5
import psycopg2
from datetime import datetime, timedelta
import sys
import json
from typing import Dict, Optional

DB_CONFIG = {
    'host': 'localhost',
    'port': 5432,
    'database': 'trading_system',
    'user': 'postgres',
    'password': 'abc'
}

SYMBOLS = [
    'EURUSD.pro', 'GBPUSD.pro', 'USDJPY.pro', 'AUDUSD.pro',
    'USDCAD.pro', 'USDCHF.pro', 'NZDUSD.pro', 'EURGBP.pro',
    'EURJPY.pro', 'GBPJPY.pro', 'XAUUSD.pro',
    'BTCUSD', 'ETHUSD'
]

def get_last_timestamp(cursor, symbol: str) -> Optional[datetime]:
    """Obtiene timestamp de ultima barra en BD para un simbolo"""
    cursor.execute(
        "SELECT MAX(time) FROM market_data WHERE symbol = %s",
        (symbol,)
    )
    result = cursor.fetchone()
    return result[0] if result[0] else None

def fetch_new_bars(symbol: str, from_date: datetime) -> list:
    """Descarga barras nuevas desde MT5"""
    # Agregar 1 minuto para no duplicar ultima barra
    from_date = from_date + timedelta(minutes=1)
    to_date = datetime.now()
    
    # Verificar que simbolo existe
    info = mt5.symbol_info(symbol)
    if info is None:
        print(f"    X {symbol}: no existe en broker")
        return []
    
    # Habilitar simbolo si necesario
    if not info.visible:
        mt5.symbol_select(symbol, True)
    
    # Descargar barras
    rates = mt5.copy_rates_range(symbol, mt5.TIMEFRAME_M1, from_date, to_date)
    
    if rates is None or len(rates) == 0:
        return []
    
    return rates

def insert_bars(cursor, symbol: str, bars) -> int:
    """Inserta barras en PostgreSQL, omitiendo duplicados"""
    inserted = 0
    
    for bar in bars:
        try:
            cursor.execute("""
                INSERT INTO market_data (symbol, time, open, high, low, close, 
                                       tick_volume, spread, real_volume)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (symbol, time) DO NOTHING
            """, (
                symbol,
                datetime.fromtimestamp(bar['time']),
                float(bar['open']),
                float(bar['high']),
                float(bar['low']),
                float(bar['close']),
                int(bar['tick_volume']),
                int(bar['spread']),
                int(bar['real_volume'])
            ))
            if cursor.rowcount > 0:
                inserted += 1
        except Exception as e:
            print(f"    Error insertando barra: {e}")
    
    return inserted

def run_incremental_sync():
    """Ejecuta sincronizacion incremental completa"""
    print("=" * 70)
    print(f"ETL INCREMENTAL - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)
    
    # Conectar MT5
    if not mt5.initialize():
        print("ERROR: No se pudo conectar a MT5")
        return False
    
    print(f"OK MT5 conectado: {mt5.account_info().server}")
    
    # Conectar PostgreSQL
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor()
        print("OK PostgreSQL conectado")
    except Exception as e:
        print(f"ERROR PostgreSQL: {e}")
        mt5.shutdown()
        return False
    
    # Sincronizar cada simbolo
    stats = {
        'timestamp': datetime.now().isoformat(),
        'symbols_synced': 0,
        'total_bars_inserted': 0,
        'details': {}
    }
    
    print(f"\nSincronizando {len(SYMBOLS)} simbolos...")
    
    for symbol in SYMBOLS:
        try:
            # Obtener ultima fecha en BD
            last_ts = get_last_timestamp(cursor, symbol)
            
            if last_ts is None:
                print(f"  {symbol}: Sin datos previos (saltar)")
                continue
            
            # Descargar barras nuevas
            new_bars = fetch_new_bars(symbol, last_ts)
            
            if len(new_bars) == 0:
                print(f"  {symbol}: Sin barras nuevas")
                stats['details'][symbol] = {'new_bars': 0, 'inserted': 0}
                continue
            
            # Insertar barras
            inserted = insert_bars(cursor, symbol, new_bars)
            conn.commit()
            
            print(f"  {symbol}: {inserted}/{len(new_bars)} barras insertadas")
            
            stats['symbols_synced'] += 1
            stats['total_bars_inserted'] += inserted
            stats['details'][symbol] = {
                'new_bars': len(new_bars),
                'inserted': inserted,
                'last_update': datetime.now().isoformat()
            }
            
        except Exception as e:
            print(f"  {symbol}: ERROR - {e}")
            stats['details'][symbol] = {'error': str(e)}
    
    # Cerrar conexiones
    cursor.close()
    conn.close()
    mt5.shutdown()
    
    # Guardar estadisticas
    log_path = 'C:/TradingSystem/audit_report/logs/etl_sync.log'
    with open(log_path, 'a') as f:
        f.write(json.dumps(stats) + '\n')
    
    print("\n" + "=" * 70)
    print(f"COMPLETADO: {stats['total_bars_inserted']} barras nuevas")
    print(f"Simbolos sincronizados: {stats['symbols_synced']}/{len(SYMBOLS)}")
    print("=" * 70)
    
    return True

if __name__ == "__main__":
    success = run_incremental_sync()
    sys.exit(0 if success else 1)
