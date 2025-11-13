"""
Análisis Completo de las 9 Estrategias Restantes
"""

import sys
sys.path.insert(0, 'C:/Users/Administrator/TradingSystem/src')

from pathlib import Path
import re

strategies_dir = Path('C:/Users/Administrator/TradingSystem/src/strategies')

print("=" * 80)
print("ANÁLISIS COMPLETO: 9 ESTRATEGIAS RESTANTES")
print("=" * 80)
print()

remaining_strategies = [
    'breakout_volume_confirmation.py',
    'correlation_divergence.py',
    'kalman_pairs_trading.py',
    'mean_reversion_statistical.py',
    'order_flow_toxicity.py',
    'fvg_institutional.py',
    'order_block_institutional.py',
    'htf_ltf_liquidity.py',
    'idp_inducement_distribution.py'
]

for strategy_file in remaining_strategies:
    file_path = strategies_dir / strategy_file
    
    print(f"\n{'='*70}")
    print(f"ESTRATEGIA: {strategy_file}")
    print('='*70)
    
    if not file_path.exists():
        print("  ✗ ARCHIVO NO ENCONTRADO")
        continue
    
    try:
        content = file_path.read_text(encoding='utf-8')
        
        # Buscar todos los parámetros configurables
        # Patrón: self.algo = config.get('algo', valor_default)
        pattern = r"self\.(\w+)\s*=\s*config\.get\(['\"](\w+)['\"]\s*,\s*([^)]+)\)"
        matches = re.findall(pattern, content)
        
        if matches:
            print("\n  Parámetros configurables encontrados:")
            for var_name, config_key, default_value in matches[:15]:
                # Limpiar el valor default
                default_clean = default_value.strip()
                if len(default_clean) < 50:
                    print(f"    {var_name}: {default_clean}")
        else:
            print("\n  ⚠ No se encontraron parámetros configurables con patrón estándar")
        
        # Buscar valores hardcoded que podrían ser restrictivos
        print("\n  Valores numéricos significativos en el código:")
        
        # Buscar números con punto decimal (thresholds típicos)
        float_pattern = r'\b\d+\.\d+\b'
        float_matches = re.findall(float_pattern, content)
        
        # Contar frecuencia de valores comunes
        from collections import Counter
        float_counter = Counter(float_matches)
        
        # Mostrar los 10 valores más comunes
        for value, count in float_counter.most_common(10):
            if float(value) > 0.1 and float(value) < 100:  # Filtrar valores muy pequeños o muy grandes
                print(f"    {value} (aparece {count} veces)")
        
        # Buscar patrones problemáticos específicos
        print("\n  Análisis de patrones problemáticos:")
        
        issues_found = False
        
        # Buscar VPIN alto como requisito
        if re.search(r'vpin.*>\s*0\.[5-9]', content, re.IGNORECASE):
            print("    ⚠ VPIN alto como requisito detectado (posible error conceptual)")
            issues_found = True
        
        # Buscar z-scores muy altos
        if re.search(r'(threshold|z_score).*[>=]\s*[3-9]\.', content):
            print("    ⚠ Z-score muy alto detectado (> 3.0 sigma)")
            issues_found = True
        
        # Buscar ventanas muy largas (> 500)
        if re.search(r'(window|lookback|period).*[>=]\s*[5-9]\d{2,}', content):
            print("    ⚠ Ventana temporal muy larga detectada (> 500)")
            issues_found = True
        
        if not issues_found:
            print("    ✓ No se detectaron patrones obviamente problemáticos")
    
    except Exception as e:
        print(f"  ✗ ERROR al analizar: {str(e)}")

print("\n" + "=" * 80)
print("FIN DEL ANÁLISIS COMPLETO")
print("=" * 80)
print()
print("RECOMENDACIÓN:")
print()
print("Ejecuta el motor con las 5 estrategias ya corregidas y observa")
print("si generan señales en las próximas 2-4 horas. Si esas 5 estrategias")
print("comienzan a operar correctamente, entonces sabemos que el problema")
print("era la calibración de parámetros y podemos evaluar las otras 9")
print("estrategias una por una según su tipo (microestructura vs price action).")
print()
