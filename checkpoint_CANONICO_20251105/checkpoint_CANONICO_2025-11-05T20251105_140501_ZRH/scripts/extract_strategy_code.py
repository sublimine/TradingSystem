"""
Extract complete source code from strategy file
"""

import sys

strategy_file = 'C:/TradingSystem/src/strategies/liquidity_sweep.py'

print("=" * 80)
print("LIQUIDITY_SWEEP.PY - COMPLETE SOURCE CODE")
print("=" * 80)
print()

try:
    with open(strategy_file, 'r', encoding='utf-8') as f:
        content = f.read()
        print(content)
except Exception as e:
    print(f"Error reading file: {e}")
