"""
Test del Gatekeeper Adapter
"""

import sys
sys.path.insert(0, 'C:/Users/Administrator/TradingSystem/src')

import numpy as np
from datetime import datetime, timedelta
from gatekeepers.gatekeeper_adapter import GatekeeperAdapter

print("=" * 80)
print("TEST: Gatekeeper Adapter")
print("=" * 80)
print()

# Crear instancia
try:
    adapter = GatekeeperAdapter()
    print("✓ Adaptador instanciado")
except Exception as e:
    print(f"✗ Error: {str(e)}")
    sys.exit(1)

# Simular flujo de ticks
print()
print("Simulando flujo de 100 ticks...")

base_time = datetime.now()
base_price = 1.1000

for i in range(100):
    tick = {
        'symbol': 'EURUSD',
        'bid': base_price + np.random.normal(0, 0.0001),
        'ask': base_price + np.random.normal(0, 0.0001) + 0.00015,
        'last': base_price + np.random.normal(0, 0.0001),
        'volume': np.random.uniform(1000, 3000),
        'time': base_time + timedelta(seconds=i)
    }
    
    adapter.process_tick(tick)

print("✓ Ticks procesados")

# Simular solicitudes de trade
print()
print("Simulando solicitudes de trade...")

permissions = []
for i in range(10):
    permission = adapter.check_trade_permission(
        strategy_name='test_strategy',
        direction='long' if i % 2 == 0 else 'short',
        symbol='EURUSD',
        proposed_size=10000.0
    )
    permissions.append(permission)

print(f"✓ {len(permissions)} solicitudes procesadas")

# Verificar que todas tienen las keys requeridas
print()
print("Verificando estructura de respuestas...")

required_keys = ['permitted', 'adjusted_size', 'reason', 'regime', 'details']
for i, perm in enumerate(permissions):
    for key in required_keys:
        if key not in perm:
            print(f"✗ Falta key '{key}' en respuesta {i}")
            sys.exit(1)

print("✓ Todas las respuestas tienen estructura correcta")

# Verificar estadísticas
print()
print("Verificando estadísticas...")

stats = adapter.get_statistics_summary()
print(f"  Ticks procesados: {stats['ticks_processed']}")
print(f"  Trades aprobados: {stats['trades_approved']}")
print(f"  Trades rechazados: {stats['trades_rejected']}")
print(f"  Approval rate: {stats['approval_rate']:.1%}")

if stats['ticks_processed'] != 100:
    print(f"✗ Ticks procesados incorrectos: {stats['ticks_processed']} != 100")
    sys.exit(1)

print("✓ Estadísticas correctas")

# Verificar status comprehensivo
print()
print("Verificando comprehensive status...")

status = adapter.get_comprehensive_status()
if 'gatekeepers' not in status or 'adapter_stats' not in status:
    print("✗ Comprehensive status incompleto")
    sys.exit(1)

print("✓ Comprehensive status completo")

print()
print("=" * 80)
print("✓ GATEKEEPER ADAPTER: TODOS LOS TESTS PASADOS")
print("=" * 80)
print()
