import sys
sys.path.insert(0, 'C:/Users/Administrator/TradingSystem/src')

import os
from pathlib import Path

strategies_dir = Path('C:/Users/Administrator/TradingSystem/src/strategies')

print("=" * 80)
print("ANÁLISIS DE PARÁMETROS DE ESTRATEGIAS")
print("=" * 80)
print()

strategy_files = [
    'liquidity_sweep.py',
    'iceberg_detection.py',
    'ofi_refinement.py',
    'momentum_quality.py',
    'volatility_regime_adaptation.py'
]

for strategy_file in strategy_files:
    file_path = strategies_dir / strategy_file
    if file_path.exists():
        print(f"\n{'='*60}")
        print(f"ESTRATEGIA: {strategy_file}")
        print('='*60)
        
        content = file_path.read_text(encoding='utf-8')
        
        # Buscar thresholds y parámetros críticos
        import re
        
        # Buscar líneas con threshold, minimum, maximum, window, sigma
        keywords = ['threshold', 'minimum', 'maximum', 'window', 'sigma', 'percentile', 'z_score', 'lookback']
        
        for keyword in keywords:
            pattern = rf".*{keyword}.*=.*\d+.*"
            matches = re.findall(pattern, content, re.IGNORECASE)
            
            if matches:
                print(f"\n  Parámetros con '{keyword}':")
                for match in matches[:5]:  # Primeros 5 matches
                    cleaned = match.strip()
                    if len(cleaned) < 100:  # Solo líneas razonables
                        print(f"    {cleaned}")

print("\n" + "=" * 80)
print("FIN DEL ANÁLISIS")
print("=" * 80)
