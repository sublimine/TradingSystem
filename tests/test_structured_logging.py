"""
Test de logging estructurado JSON
"""
import sys
sys.path.insert(0, "C:/TradingSystem/src")
from structured_logging import setup_structured_logging, log_signal, log_trade_execution
import json
import os

def test_json_format():
    """Test formato JSON valido"""
    log_path = "C:/TradingSystem/audit_report/evidence/test_structured.log"
    
    # Limpiar archivo previo
    if os.path.exists(log_path):
        os.remove(log_path)
    
    logger = setup_structured_logging(log_path)
    
    # Log de señal
    log_signal(logger, 'liquidity_sweep', 'EURUSD.pro', 'BUY', 1.0850, 0.10, 0.85)
    
    # Log de ejecucion
    log_trade_execution(logger, 12345, 'EURUSD.pro', 'BUY', 1.0850, 0.10)
    
    # Verificar que archivo existe
    assert os.path.exists(log_path), "Archivo de log no creado"
    
    # Leer y parsear JSON
    with open(log_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    assert len(lines) >= 2, f"Debe haber al menos 2 lineas, encontradas: {len(lines)}"
    
    # Verificar que cada linea es JSON valido
    for line in lines:
        try:
            data = json.loads(line.strip())
            assert 'timestamp' in data, "Falta campo timestamp"
            assert 'level' in data, "Falta campo level"
            assert 'message' in data, "Falta campo message"
        except json.JSONDecodeError as e:
            raise AssertionError(f"Linea no es JSON valido: {line[:50]}")
    
    print(f"  OK JSON: {len(lines)} logs parseables")

def test_custom_fields():
    """Test campos personalizados en logs"""
    log_path = "C:/TradingSystem/audit_report/evidence/test_structured.log"
    
    with open(log_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    # Primera linea debe tener campos de signal
    first_log = json.loads(lines[0].strip())
    
    assert 'strategy' in first_log, "Falta campo strategy"
    assert 'symbol' in first_log, "Falta campo symbol"
    assert 'action' in first_log, "Falta campo action"
    assert 'price' in first_log, "Falta campo price"
    
    assert first_log['strategy'] == 'liquidity_sweep'
    assert first_log['symbol'] == 'EURUSD.pro'
    assert first_log['action'] == 'BUY'
    
    print(f"  OK Campos personalizados presentes")

if __name__ == "__main__":
    print("\n" + "="*60)
    print("TESTS: LOGGING ESTRUCTURADO")
    print("="*60 + "\n")
    
    try:
        test_json_format()
        test_custom_fields()
        
        print("\n" + "="*60)
        print("PASS: 2/2 tests")
        print("="*60)
        
        # Mostrar ejemplo de log
        print("\nEjemplo de log JSON:")
        with open("C:/TradingSystem/audit_report/evidence/test_structured.log", 'r') as f:
            print(f.readline().strip())
        
        exit(0)
    except Exception as e:
        print(f"\nFAIL: {e}")
        exit(1)
