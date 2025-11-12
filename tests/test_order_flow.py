"""
Tests unitarios CORRECTOS para order_flow.py
Basados en API real: add_trade() y get_current_vpin()
"""
import sys
sys.path.insert(0, "C:/TradingSystem/src/features")
import numpy as np
from order_flow import VPINCalculator

def test_vpin_initialization():
    """Inicializacion con parametros correctos"""
    calc = VPINCalculator(bucket_size=1000, num_buckets=10)
    
    assert calc.bucket_size == 1000, f"bucket_size incorrecto: {calc.bucket_size}"
    assert calc.num_buckets == 10, f"num_buckets incorrecto: {calc.num_buckets}"
    assert calc.current_bucket_volume == 0, "current_bucket_volume debe iniciar en 0"
    assert len(calc.buckets) == 0, "buckets debe iniciar vacio"
    
    print(f"  OK Inicializacion: bucket_size={calc.bucket_size}, num_buckets={calc.num_buckets}")

def test_vpin_add_trade():
    """add_trade() debe aceptar volume y trade_direction"""
    calc = VPINCalculator(bucket_size=100, num_buckets=10)
    
    # Agregar trades de compra
    result = calc.add_trade(volume=50, trade_direction=1)
    assert calc.current_bucket_volume == 50, f"Volumen incorrecto: {calc.current_bucket_volume}"
    assert calc.current_bucket_buy_volume == 50, "Buy volume incorrecto"
    
    # Agregar trade de venta
    calc.add_trade(volume=30, trade_direction=-1)
    assert calc.current_bucket_volume == 80, "Volumen acumulado incorrecto"
    assert calc.current_bucket_sell_volume == 30, "Sell volume incorrecto"
    
    print(f"  OK add_trade: volume acumulado correctamente")

def test_vpin_bucket_completion():
    """Bucket debe completarse al alcanzar bucket_size"""
    calc = VPINCalculator(bucket_size=100, num_buckets=5)
    
    # Llenar primer bucket
    calc.add_trade(volume=60, trade_direction=1)
    calc.add_trade(volume=50, trade_direction=-1)  # Total = 110, debe cerrar bucket
    
    assert len(calc.buckets) >= 1, "Bucket no se completo"
    
    print(f"  OK Bucket completion: {len(calc.buckets)} buckets creados")

def test_vpin_calculation():
    """VPIN debe calcularse correctamente despues de llenar buckets"""
    calc = VPINCalculator(bucket_size=100, num_buckets=10)
    
    np.random.seed(42)
    # Agregar suficientes trades para llenar varios buckets
    for i in range(200):
        volume = np.random.randint(10, 50)
        direction = 1 if np.random.random() > 0.5 else -1
        calc.add_trade(volume=volume, trade_direction=direction)
    
    vpin = calc.get_current_vpin()
    
    assert vpin is not None, "VPIN retorno None"
    assert isinstance(vpin, (int, float)), f"VPIN tipo incorrecto: {type(vpin)}"
    assert 0 <= vpin <= 1, f"VPIN fuera de rango [0,1]: {vpin}"
    
    print(f"  OK VPIN calculation: {vpin:.4f} (rango valido)")

def test_vpin_empty():
    """VPIN vacio debe retornar 0"""
    calc = VPINCalculator(bucket_size=100, num_buckets=10)
    vpin = calc.get_current_vpin()
    
    assert vpin == 0.0, f"VPIN vacio debe ser 0.0, obtenido: {vpin}"
    
    print(f"  OK VPIN vacio: retorna 0.0")

def test_vpin_reset():
    """reset() debe limpiar todos los buckets"""
    calc = VPINCalculator(bucket_size=100, num_buckets=10)
    
    # Agregar datos
    for i in range(50):
        calc.add_trade(volume=30, trade_direction=1)
    
    # Reset
    calc.reset()
    
    assert len(calc.buckets) == 0, f"buckets no vacio despues de reset: {len(calc.buckets)}"
    assert calc.current_bucket_volume == 0, "current_bucket_volume no reseteo"
    assert calc.get_current_vpin() == 0.0, "VPIN no es 0 despues de reset"
    
    print(f"  OK reset: estado limpiado correctamente")

if __name__ == "__main__":
    print("\n" + "="*70)
    print("TESTS UNITARIOS: ORDER FLOW (VPIN)")
    print("="*70 + "\n")
    
    tests_run = 0
    tests_passed = 0
    
    for test_func in [test_vpin_initialization, test_vpin_add_trade, 
                     test_vpin_bucket_completion, test_vpin_calculation,
                     test_vpin_empty, test_vpin_reset]:
        tests_run += 1
        try:
            test_func()
            tests_passed += 1
        except AssertionError as e:
            print(f"  FAIL {test_func.__name__}: {e}")
        except Exception as e:
            print(f"  ERROR {test_func.__name__}: {e}")
    
    print("\n" + "="*70)
    print(f"RESULTADO: {tests_passed}/{tests_run} tests pasados")
    print("="*70)
    
    exit(0 if tests_passed == tests_run else 1)
