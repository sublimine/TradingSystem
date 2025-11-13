"""
INSTALADOR MAESTRO - EJECUCIÓN AUTOMATIZADA COMPLETA
Configura el sistema completo de trading en vivo sin intervención manual
"""

import subprocess
import sys
import os
import time
from pathlib import Path

print("=" * 80)
print("INSTALADOR MAESTRO DEL SISTEMA DE TRADING")
print("=" * 80)
print("Este script ejecutará TODOS los pasos automáticamente")
print("Tiempo estimado: 5-10 minutos")
print("=" * 80)

def run_command(cmd, description):
    """Ejecuta comando y maneja errores."""
    print(f"\n[{time.strftime('%H:%M:%S')}] {description}...")
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=300)
        if result.returncode == 0:
            print(f"✓ {description} - COMPLETADO")
            if result.stdout.strip():
                print(result.stdout[:500])
            return True
        else:
            print(f"✗ {description} - ERROR")
            print(result.stderr[:500])
            return False
    except Exception as e:
        print(f"✗ {description} - EXCEPCIÓN: {str(e)[:200]}")
        return False

# PASO 1: Instalar dependencias de Python
print("\n" + "=" * 80)
print("PASO 1/5: INSTALANDO DEPENDENCIAS DE PYTHON")
print("=" * 80)

dependencies = [
    ('pip install --upgrade pip --break-system-packages', 'Actualizar pip'),
    ('pip install MetaTrader5 --break-system-packages', 'MetaTrader5'),
    ('pip install psycopg2-binary --break-system-packages', 'PostgreSQL driver'),
    ('pip install pandas --break-system-packages', 'Pandas'),
    ('pip install numpy --break-system-packages', 'NumPy')
]

for cmd, name in dependencies:
    run_command(cmd, f'Instalar {name}')

# PASO 2: Verificar MetaTrader 5
print("\n" + "=" * 80)
print("PASO 2/5: VERIFICANDO METATRADER 5")
print("=" * 80)

verify_mt5 = '''
import MetaTrader5 as mt5
if not mt5.initialize():
    print("ERROR: MT5 no inicializado - Abra MetaTrader 5 manualmente")
    exit(1)
account = mt5.account_info()
print(f"Broker: {account.server}")
print(f"Cuenta: {account.login}")
print(f"Balance: ${account.balance:,.2f}")
mt5.shutdown()
'''

with open('C:/TradingSystem/temp_verify_mt5.py', 'w') as f:
    f.write(verify_mt5)

if not run_command('python C:/TradingSystem/temp_verify_mt5.py', 'Verificar MT5'):
    print("\n⚠️  ACCIÓN REQUERIDA:")
    print("1. Abra MetaTrader 5")
    print("2. Conéctese a su cuenta de AxiCorp")
    print("3. Presione Enter para continuar...")
    input()

# PASO 3: Verificar PostgreSQL
print("\n" + "=" * 80)
print("PASO 3/5: VERIFICANDO POSTGRESQL")
print("=" * 80)

verify_pg = '''
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
'''

with open('C:/TradingSystem/temp_verify_pg.py', 'w') as f:
    f.write(verify_pg)

run_command('python C:/TradingSystem/temp_verify_pg.py', 'Verificar PostgreSQL')

# PASO 4: Actualizar lista de símbolos en live_trading_engine.py
print("\n" + "=" * 80)
print("PASO 4/5: ACTUALIZANDO CONFIGURACIÓN DE SÍMBOLOS")
print("=" * 80)

live_engine_path = 'C:/TradingSystem/scripts/live_trading_engine.py'

with open(live_engine_path, 'r', encoding='utf-8') as f:
    content = f.read()

# Reemplazar lista de símbolos
old_symbols = "SYMBOLS = [\n    'EURUSD.pro', 'GBPUSD.pro', 'USDJPY.pro', 'AUDUSD.pro',\n    'USDCAD.pro', 'USDCHF.pro', 'NZDUSD.pro', 'EURGBP.pro'\n]"
new_symbols = "SYMBOLS = [\n    'EURUSD.pro', 'GBPUSD.pro', 'USDJPY.pro', 'AUDUSD.pro',\n    'USDCAD.pro', 'USDCHF.pro', 'NZDUSD.pro', 'EURGBP.pro',\n    'XAUUSD.pro', 'BTCUSD', 'ETHUSD'\n]"

content = content.replace(old_symbols, new_symbols)

with open(live_engine_path, 'w', encoding='utf-8') as f:
    f.write(content)

print("✓ Símbolos actualizados: 11 instrumentos configurados")

# PASO 5: Iniciar sistema de trading en vivo
print("\n" + "=" * 80)
print("PASO 5/5: INICIANDO SISTEMA DE TRADING EN VIVO")
print("=" * 80)
print("\n⚠️  El sistema comenzará a operar en 3 segundos...")
print("   Presione Ctrl+C en cualquier momento para detener\n")

time.sleep(3)

# Ejecutar sistema
os.system('python C:/TradingSystem/scripts/live_trading_engine.py')
