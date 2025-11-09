import sys
sys.path.insert(0, 'C:/TradingSystem/src')
import json
import importlib
import inspect
from pathlib import Path

WHITELIST = [
    'breakout_volume_confirmation',
    'correlation_divergence',
    'kalman_pairs_trading',
    'liquidity_sweep',
    'mean_reversion_statistical',
    'momentum_quality',
    'news_event_positioning',
    'order_flow_toxicity',
    'volatility_regime_adaptation'
]

integrity_results = []
import_matrix = {}
signature_check = {}

for module_name in WHITELIST:
    module_file = Path(f'C:/TradingSystem/src/strategies/{module_name}.py')
    
    result = {
        'module': module_name,
        'present': module_file.exists(),
        'class_detected': False,
        'signature_ok': False
    }
    
    if module_file.exists():
        try:
            module = importlib.import_module(f'strategies.{module_name}')
            classes = [(n, o) for n, o in inspect.getmembers(module, inspect.isclass)
                      if o.__module__ == f'strategies.{module_name}']
            
            if classes:
                result['class_detected'] = True
                class_name, strategy_class = classes[0]
                
                if hasattr(strategy_class, 'evaluate'):
                    result['signature_ok'] = True
                    signature_check[module_name] = 'OK'
                else:
                    signature_check[module_name] = 'INVALID_SIGNATURE: Sin método evaluate'
            
            import_matrix[module_name] = 'OK'
        
        except Exception as e:
            import_matrix[module_name] = f'ERROR: {str(e)[:50]}'
            signature_check[module_name] = 'ERROR_IMPORT'
    
    else:
        import_matrix[module_name] = 'MISSING'
        signature_check[module_name] = 'MISSING'
    
    integrity_results.append(result)

with open('C:/TradingSystem/report/whitelist_integrity.json', 'w') as f:
    json.dump(integrity_results, f, indent=2)

with open('C:/TradingSystem/report/import_matrix.json', 'w') as f:
    json.dump(import_matrix, f, indent=2)

with open('C:/TradingSystem/report/signature_check.json', 'w') as f:
    json.dump(signature_check, f, indent=2)

ok_count = sum(1 for r in integrity_results if r['present'] and r['class_detected'] and r['signature_ok'])
print(f"Validación completada: {ok_count}/9 OK")
