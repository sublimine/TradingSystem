"""
Strategy Inspector - Identify actual class names and structure
"""

import sys
sys.path.insert(0, 'C:/TradingSystem')
sys.path.insert(0, 'C:/TradingSystem/src')

import os
import importlib
import inspect

STRATEGY_MODULES = [
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

print("=" * 80)
print("STRATEGY CLASS INSPECTION")
print("=" * 80)

strategy_classes = {}

for module_name in STRATEGY_MODULES:
    try:
        module = importlib.import_module(f'strategies.{module_name}')
        
        classes = [name for name, obj in inspect.getmembers(module, inspect.isclass) 
                  if obj.__module__ == f'strategies.{module_name}']
        
        print(f"\n{module_name}.py:")
        if classes:
            for cls_name in classes:
                cls = getattr(module, cls_name)
                
                is_abstract = inspect.isabstract(cls)
                
                methods = [method for method in dir(cls) if not method.startswith('_')]
                
                print(f"  Class: {cls_name}")
                print(f"    Abstract: {is_abstract}")
                print(f"    Methods: {len(methods)}")
                
                if hasattr(cls, 'analyze_market'):
                    print(f"    ✓ Has analyze_market")
                else:
                    print(f"    ✗ Missing analyze_market")
                
                if hasattr(cls, 'get_required_lookback_bars'):
                    print(f"    ✓ Has get_required_lookback_bars")
                else:
                    print(f"    ✗ Missing get_required_lookback_bars")
                
                if not is_abstract:
                    strategy_classes[module_name] = cls_name
        else:
            print(f"  No classes found")
            
    except Exception as e:
        print(f"\n{module_name}.py:")
        print(f"  Error: {e}")

print("\n" + "=" * 80)
print(f"Concrete strategy classes found: {len(strategy_classes)}")
print("=" * 80)

if strategy_classes:
    print("\nStrategy class mapping:")
    for module, class_name in strategy_classes.items():
        print(f"  {module} -> {class_name}")
