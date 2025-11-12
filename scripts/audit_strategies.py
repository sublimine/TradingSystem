"""
Auditoria profunda de estrategias
Identifica umbrales restrictivos y logica institucional
"""
import sys
import os
import re
import ast

sys.path.insert(0, "C:/TradingSystem/src/strategies")

strategies_path = "C:/TradingSystem/src/strategies"
strategies = [f for f in os.listdir(strategies_path) if f.endswith('.py') and f != '__init__.py']

print("="*80)
print("AUDITORIA DE ESTRATEGIAS - ANALISIS DE RESTRICCIONES")
print("="*80)

critical_findings = []
optimization_targets = []

for strategy_file in strategies:
    filepath = os.path.join(strategies_path, strategy_file)
    
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    print(f"\n{strategy_file}")
    print("-"*80)
    
    # Buscar umbrales numericos
    threshold_patterns = [
        (r'>\s*(\d+\.?\d*)', 'Mayor que'),
        (r'<\s*(\d+\.?\d*)', 'Menor que'),
        (r'>=\s*(\d+\.?\d*)', 'Mayor o igual'),
        (r'<=\s*(\d+\.?\d*)', 'Menor o igual'),
        (r'==\s*(\d+\.?\d*)', 'Igual a')
    ]
    
    thresholds_found = []
    
    for pattern, description in threshold_patterns:
        matches = re.findall(pattern, content)
        if matches:
            # Filtrar valores muy comunes (0, 1, 2)
            significant = [m for m in matches if float(m) not in [0.0, 1.0, 2.0]]
            if significant:
                thresholds_found.extend([(description, float(v)) for v in significant])
    
    if thresholds_found:
        print(f"  Umbrales detectados: {len(thresholds_found)}")
        # Mostrar algunos ejemplos
        for desc, val in thresholds_found[:3]:
            print(f"    - {desc}: {val}")
        
        # Identificar umbrales muy restrictivos
        high_thresholds = [v for d, v in thresholds_found if v > 0.7]
        if high_thresholds:
            optimization_targets.append({
                'strategy': strategy_file,
                'high_thresholds': high_thresholds,
                'count': len(high_thresholds)
            })
    else:
        print("  Sin umbrales explicitos detectados")
        critical_findings.append({
            'strategy': strategy_file,
            'issue': 'Sin condiciones de entrada claras'
        })
    
    # Verificar metodo evaluate
    if 'def evaluate' not in content:
        print("  ✗ CRITICO: Sin metodo evaluate()")
        critical_findings.append({
            'strategy': strategy_file,
            'issue': 'Falta metodo evaluate'
        })
    else:
        print("  ✓ Metodo evaluate presente")
    
    # Verificar returns
    if 'return None' in content or 'return' not in content:
        print("  ⚠ WARNING: Podria retornar None frecuentemente")

print("\n" + "="*80)
print("RESULTADOS DE AUDITORIA")
print("="*80)

if critical_findings:
    print("\n✗ HALLAZGOS CRITICOS:")
    for finding in critical_findings:
        print(f"  - {finding['strategy']}: {finding['issue']}")
else:
    print("\n✓ Sin hallazgos criticos")

if optimization_targets:
    print("\n⚡ OBJETIVOS DE OPTIMIZACION:")
    for target in optimization_targets:
        print(f"  - {target['strategy']}: {target['count']} umbrales altos detectados")
        print(f"    Valores: {target['high_thresholds'][:3]}")
else:
    print("\n✓ Sin umbrales excesivamente restrictivos")
