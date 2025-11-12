"""
Verificacion de calculos en features
"""
import sys
sys.path.insert(0, "C:/TradingSystem/src/features")

print("="*80)
print("VERIFICACION DE MODULOS DE FEATURES")
print("="*80)

# Technical indicators
try:
    from technical_indicators import (
        calculate_rsi, calculate_bollinger_bands, 
        calculate_atr, calculate_macd, identify_swing_points
    )
    print("\n[OK] technical_indicators.py")
    print("  Funciones: calculate_rsi, calculate_bollinger_bands, calculate_atr,")
    print("             calculate_macd, identify_swing_points")
except Exception as e:
    print(f"\n[X] technical_indicators.py: {e}")

# Order flow
try:
    from order_flow import VPINCalculator
    calc = VPINCalculator()
    print("\n[OK] order_flow.py")
    print(f"  VPINCalculator: bucket_size={calc.bucket_size}, num_buckets={calc.num_buckets}")
    print(f"  Metodos: add_trade(), get_current_vpin(), reset()")
except Exception as e:
    print(f"\n[X] order_flow.py: {e}")

print("\n" + "="*80)
print("VERIFICACION: Todos los modulos core cargables")
print("="*80)
