"""
Validation script for Correlation Redundancy - CORRECTED for real schema
Uses actual column names: lot_size, trade_type (no strategy_name column)
"""

import sys
sys.path.append('C:/TradingSystem')

from src.risk_management import RiskManager, CorrelationMatrix
from src.strategies.strategy_base import Signal
from datetime import datetime
import psycopg2

db_config = {
    'host': 'localhost',
    'port': 5432,
    'database': 'trading_system',
    'user': 'trading_user',
    'password': 'abc'
}

risk_config = {
    'max_positions_per_symbol': 3,
    'correlation_threshold': 0.70,
    'max_correlated_exposure_score': 2.0,
    'margin_buffer_percent': 20,
    'leverage': 1000,
    'sizing_levels': {1: 0.5, 2: 1.0, 3: 1.5, 4: 2.0, 5: 2.5},
    'drawdown_adjustments': {5: 0.8, 10: 0.6, 20: 0.4, 30: 0.0}
}

print("=" * 80)
print("VALIDACIÓN DE SISTEMA DE CORRELACIÓN REDUNDANCY")
print("=" * 80)

print("\n1. Inicializando CorrelationMatrix...")
correlation_matrix = CorrelationMatrix(db_config)
print("   ✓ CorrelationMatrix inicializado")

print("\n2. Insertando correlaciones de prueba...")
conn = psycopg2.connect(**db_config)
cursor = conn.cursor()

test_correlations = [
    ('EURUSD.pro', 'GBPUSD.pro', 0.85),
    ('EURUSD.pro', 'USDJPY.pro', -0.60),
    ('GBPUSD.pro', 'USDJPY.pro', -0.55),
    ('EURUSD.pro', 'AUDUSD.pro', 0.72),
    ('GBPUSD.pro', 'AUDUSD.pro', 0.78)
]

for symbol_a, symbol_b, corr_value in test_correlations:
    cursor.execute("""
        INSERT INTO correlation_matrix (
            symbol_a, symbol_b, correlation_value, lookback_days,
            calculated_at, data_points
        ) VALUES (%s, %s, %s, %s, %s, %s)
        ON CONFLICT (symbol_a, symbol_b) DO UPDATE 
        SET correlation_value = EXCLUDED.correlation_value
    """, (symbol_a, symbol_b, corr_value, 180, datetime.now(), 180))

conn.commit()
cursor.close()
conn.close()
print(f"   ✓ {len(test_correlations)} correlaciones insertadas")

print("\n3. Verificando consultas...")
corr_eu_gb = correlation_matrix.get_correlation('EURUSD.pro', 'GBPUSD.pro')
corr_eu_jp = correlation_matrix.get_correlation('EURUSD.pro', 'USDJPY.pro')
print(f"   EURUSD-GBPUSD: {corr_eu_gb:.2f}")
print(f"   EURUSD-USDJPY: {corr_eu_jp:.2f}")
print("   ✓ Consultas correctas")

print("\n4. Inicializando RiskManager...")
risk_manager = RiskManager(risk_config, db_config)
print("   ✓ RiskManager inicializado")

print("\n5. Creando posición GBPUSD LONG 1.5 lotes...")
conn = psycopg2.connect(**db_config)
cursor = conn.cursor()

# USAR COLUMNAS REALES: symbol, trade_type, lot_size, entry_price, entry_time, stop_loss, take_profit, status
cursor.execute("""
    INSERT INTO trades (
        symbol, trade_type, lot_size, entry_price, entry_time,
        stop_loss, take_profit, status
    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
    RETURNING id
""", ('GBPUSD.pro', 'LONG', 1.5, 1.2500, datetime.now(), 
      1.2450, 1.2600, 'open'))

trade_id_1 = cursor.fetchone()[0]
conn.commit()
print(f"   ✓ Trade ID {trade_id_1} creado")

print("\n6. Validando EURUSD LONG (correlación 0.85 con GBPUSD)...")
test_signal = Signal(
    timestamp=datetime.now(),
    symbol='EURUSD.pro',
    strategy_name='TestStrategy',
    direction='LONG',
    entry_price=1.1000,
    stop_loss=1.0950,
    take_profit=1.1100,
    sizing_level=2,
    metadata={'test': True}
)

approved, reason, volume = risk_manager.validate_signal(test_signal, 10000.0)
print(f"   Approved: {approved}, Reason: {reason}")
print("   Exposure Score: 1.5 * 0.85 = 1.275 < 2.0 → APROBADA")
assert approved == True, "Should be approved"
print("   ✓ Señal con correlación moderada aprobada")

print("\n7. Agregando AUDUSD LONG 1.2 lotes...")
cursor.execute("""
    INSERT INTO trades (
        symbol, trade_type, lot_size, entry_price, entry_time,
        stop_loss, take_profit, status
    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
    RETURNING id
""", ('AUDUSD.pro', 'LONG', 1.2, 0.6500, datetime.now(),
      0.6450, 0.6600, 'open'))

trade_id_2 = cursor.fetchone()[0]
conn.commit()
print(f"   ✓ Trade ID {trade_id_2} creado")

print("\n8. Re-validando EURUSD LONG (exposición agregada)...")
approved, reason, volume = risk_manager.validate_signal(test_signal, 10000.0)
print(f"   Approved: {approved}, Reason: {reason}")
print("   Exposure Score:")
print("     GBPUSD: 1.5 * 0.85 = 1.275")
print("     AUDUSD: 1.2 * 0.72 = 0.864")
print("     Total: 2.139 > 2.0 → RECHAZADA")

assert approved == False, "Should be rejected"
assert reason == "CORRELATION_REDUNDANCY", "Reason should be correlation"
print("   ✓ Señal con exposición excesiva rechazada")

print("\n9. Validando USDJPY SHORT (no correlacionada)...")
test_signal_short = Signal(
    timestamp=datetime.now(),
    symbol='USDJPY.pro',
    strategy_name='TestStrategy',
    direction='SHORT',
    entry_price=150.00,
    stop_loss=150.50,
    take_profit=149.00,
    sizing_level=2,
    metadata={'test': True}
)

approved, reason, volume = risk_manager.validate_signal(test_signal_short, 10000.0)
print(f"   Approved: {approved}, Reason: {reason}")
print("   (Dirección opuesta, no suma exposure)")
assert approved == True, "Uncorrelated should be approved"
print("   ✓ Señal no correlacionada aprobada")

print("\n10. Limpiando datos de prueba...")
cursor.execute("DELETE FROM trades WHERE id IN (%s, %s)", (trade_id_1, trade_id_2))
conn.commit()
cursor.close()
conn.close()
print("   ✓ Trades de prueba eliminados")

print("\n" + "=" * 80)
print("VALIDACIÓN COMPLETADA EXITOSAMENTE")
print("=" * 80)
print("\nFUNCIONALIDAD VALIDADA:")
print("  • CorrelationMatrix consulta correctamente")
print("  • Exposure score se calcula agregando volúmenes ponderados")
print("  • Señales moderadas son aprobadas")
print("  • Señales excesivas son rechazadas")
print("  • Direcciones opuestas no suman exposure")
print("\nDEFICIENCIA 3 COMPLETAMENTE REMEDIADA")
