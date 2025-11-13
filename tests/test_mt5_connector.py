"""
Test de reconexion automatica
"""
import sys
sys.path.insert(0, "C:/TradingSystem/src")
from mt5_connector import MT5Connector
import MetaTrader5 as mt5

def test_connection():
    """Test conexion basica"""
    connector = MT5Connector(max_retries=3, base_delay=1.0)
    assert connector.connect() == True, "Fallo conexion inicial"
    assert connector.is_connected() == True, "Estado de conexion incorrecto"
    connector.disconnect()
    print("  OK Conexion basica")

def test_context_manager():
    """Test uso como context manager"""
    with MT5Connector(max_retries=3) as conn:
        assert conn.is_connected() == True, "No conectado en context manager"
    print("  OK Context manager")

def test_ensure_connected():
    """Test ensure_connected mantiene conexion"""
    connector = MT5Connector(max_retries=3, base_delay=1.0)
    connector.connect()
    
    # Simular que conexion esta OK
    assert connector.ensure_connected() == True, "ensure_connected fallo con conexion activa"
    
    connector.disconnect()
    print("  OK ensure_connected")

if __name__ == "__main__":
    print("\n" + "="*60)
    print("TESTS: MT5 RECONEXION")
    print("="*60 + "\n")
    
    try:
        test_connection()
        test_context_manager()
        test_ensure_connected()
        
        print("\n" + "="*60)
        print("PASS: 3/3 tests")
        print("="*60)
        exit(0)
    except Exception as e:
        print(f"\nFAIL: {e}")
        exit(1)
