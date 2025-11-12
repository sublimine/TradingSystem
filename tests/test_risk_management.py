"""
Tests unitarios para modulo de gestion de riesgo
"""
import sys
sys.path.insert(0, "C:/TradingSystem/src")
from risk_management import calculate_position_size, validate_position_size, calculate_stop_loss_atr

def test_position_size_basic():
    """Test calculo basico de tamano de posicion"""
    capital = 10000
    risk_pct = 1.0
    entry = 1.1000
    stop = 1.0950  # 50 pips de riesgo
    
    lots = calculate_position_size(capital, risk_pct, entry, stop)
    
    # Con 10000 capital, 1% riesgo = 100 USD
    # 50 pips de riesgo, 10 USD por pip = 0.20 lotes esperados
    assert 0.15 <= lots <= 0.25, f"Lotes fuera de rango: {lots}"
    print(f"  OK Test 1: {lots} lotes (esperado ~0.20)")

def test_minimum_lot_size():
    """Test que se respeta minimo de 0.01 lotes"""
    capital = 100  # Capital muy pequeno
    risk_pct = 0.5
    entry = 1.1000
    stop = 1.0900  # 100 pips
    
    lots = calculate_position_size(capital, risk_pct, entry, stop)
    
    assert lots >= 0.01, f"Lote menor al minimo: {lots}"
    print(f"  OK Test 2: Minimo respetado ({lots} lotes)")

def test_maximum_lot_size():
    """Test que se respeta maximo de 100 lotes"""
    capital = 1000000  # Capital grande
    risk_pct = 2.0
    entry = 1.1000
    stop = 1.0990  # Solo 10 pips de riesgo
    
    lots = calculate_position_size(capital, risk_pct, entry, stop)
    
    assert lots <= 100.0, f"Lote mayor al maximo: {lots}"
    print(f"  OK Test 3: Maximo respetado ({lots} lotes)")

def test_position_validation():
    """Test validacion de posiciones"""
    assert validate_position_size(0.01, "EURUSD.pro") == True
    assert validate_position_size(0.00, "EURUSD.pro") == False
    assert validate_position_size(150.0, "EURUSD.pro") == False
    assert validate_position_size(15.0, "BTCUSD") == False  # Cripto mas restrictivo
    print("  OK Test 4: Validaciones correctas")

def test_stop_loss_atr():
    """Test calculo de stop loss con ATR"""
    price = 1.1000
    atr = 0.0020  # 20 pips
    
    stop_long = calculate_stop_loss_atr(price, atr, 'LONG', multiplier=2.0)
    stop_short = calculate_stop_loss_atr(price, atr, 'SHORT', multiplier=2.0)
    
    assert stop_long < price, "Stop loss LONG debe estar debajo del precio"
    assert stop_short > price, "Stop loss SHORT debe estar arriba del precio"
    assert abs(price - stop_long - (atr * 2.0)) < 0.0001, "Calculo ATR incorrecto"
    print(f"  OK Test 5: Stop loss ATR (LONG: {stop_long}, SHORT: {stop_short})")

def test_zero_distance():
    """Test comportamiento con distancia cero"""
    lots = calculate_position_size(10000, 1.0, 1.1000, 1.1000)
    assert lots == 0.01, "Debe retornar minimo cuando distancia es 0"
    print(f"  OK Test 6: Distancia cero manejada ({lots} lotes)")

if __name__ == "__main__":
    print("\n" + "="*60)
    print("TESTS DE GESTION DE RIESGO")
    print("="*60 + "\n")
    
    try:
        test_position_size_basic()
        test_minimum_lot_size()
        test_maximum_lot_size()
        test_position_validation()
        test_stop_loss_atr()
        test_zero_distance()
        
        print("\n" + "="*60)
        print("RESULTADO: TODOS LOS TESTS PASARON (6/6)")
        print("="*60)
        exit(0)
        
    except AssertionError as e:
        print(f"\nERROR: {e}")
        print("="*60)
        print("RESULTADO: TESTS FALLARON")
        print("="*60)
        exit(1)
    except Exception as e:
        print(f"\nERROR INESPERADO: {e}")
        exit(1)
