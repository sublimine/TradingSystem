"""
Analisis preciso del motor de trading - SIN Unicode
"""
import re

with open("C:/TradingSystem/scripts/live_trading_engine.py", "r", encoding="utf-8") as f:
    content = f.read()

print("="*80)
print("ANALISIS DETALLADO: live_trading_engine.py")
print("="*80)

# 1. Estrategias
strategy_imports = re.findall(r'from strategies\.(\w+) import', content)
if strategy_imports:
    print(f"\n[OK] Estrategias importadas: {len(strategy_imports)}")
    for s in strategy_imports[:5]:
        print(f"  - {s}")
    if len(strategy_imports) > 5:
        print(f"  ... y {len(strategy_imports) - 5} mas")
else:
    print("\n[X] CRITICO: Sin imports de estrategias")

# 2. Carga dinamica
if 'importlib' in content:
    print("\n[OK] Sistema de carga dinamica presente")
    
# 3. Fuente de datos
data_methods = re.findall(r'mt5\.(copy_rates_\w+)', content)
if data_methods:
    print(f"\n[OK] Descarga datos MT5: {set(data_methods)}")
else:
    print("\n[X] CRITICO: No se detecta descarga de datos")

# 4. Position sizing
if 'calculate_position_size' in content:
    print("\n[OK] Position sizing dinamico implementado")
    # Ver parametros
    sizing_calls = re.findall(r'calculate_position_size\([^)]+\)', content)
    if sizing_calls:
        print(f"  Ejemplo: {sizing_calls[0][:80]}")
else:
    print("\n[X] Position sizing fijo o ausente")

# 5. Reconexion
mt5_init_count = content.count('mt5.initialize')
if mt5_init_count > 0:
    print(f"\n[INFO] mt5.initialize llamado {mt5_init_count} veces")
    if 'MT5Connector' in content:
        print("  [OK] Usa MT5Connector con reconexion")
    else:
        print("  [WARNING] Reconexion basica, considerar MT5Connector")

# 6. Loop principal
if 'while True:' in content or 'while running:' in content:
    print("\n[OK] Loop principal detectado")
else:
    print("\n[X] CRITICO: Sin loop principal")

# 7. Manejo de señales
if 'signal' in content.lower() and 'evaluate' in content:
    print("\n[OK] Evaluacion y generacion de señales presente")
else:
    print("\n[WARNING] Logica de señales poco clara")

# 8. Ejecucion de trades
if 'order_send' in content:
    print("\n[OK] Ejecucion de trades implementada")
else:
    print("\n[X] Sin ejecucion de trades")

print("\n" + "="*80)
