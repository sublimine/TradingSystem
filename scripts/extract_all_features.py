"""
Complete Feature Modules Code Extraction
"""

import os

feature_files = [
    'C:/TradingSystem/src/features/derived_features.py',
    'C:/TradingSystem/src/features/microstructure.py',
    'C:/TradingSystem/src/features/order_flow.py',
    'C:/TradingSystem/src/features/statistical_models.py',
    'C:/TradingSystem/src/features/technical_indicators.py'
]

print("=" * 80)
print("FEATURE MODULES COMPLETE SOURCE CODE")
print("=" * 80)

for filepath in feature_files:
    filename = os.path.basename(filepath)
    print(f"\n{'=' * 80}")
    print(f"FILE: {filename}")
    print(f"{'=' * 80}\n")
    
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
            print(content)
            print()
    except Exception as e:
        print(f"ERROR: {e}\n")
