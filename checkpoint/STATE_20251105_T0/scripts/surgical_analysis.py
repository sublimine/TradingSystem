"""
Analisis quirurgico de cada estrategia
Identifica EXACTAMENTE que esta bloqueando operaciones
"""
import os
import re
import ast
import sys

sys.path.insert(0, "C:/TradingSystem/src/strategies")

strategies_path = "C:/TradingSystem/src/strategies"
strategy_files = [
    'liquidity_sweep.py',
    'order_flow_toxicity.py', 
    'breakout_volume_confirmation.py',
    'correlation_divergence.py',
    'kalman_pairs_trading.py',
    'mean_reversion_statistical.py',
    'momentum_quality.py',
    'news_event_positioning.py',
    'volatility_regime_adaptation.py'
]

print("="*80)
print("ANALISIS QUIRURGICO - IDENTIFICACION DE RESTRICCIONES")
print("="*80)

bottlenecks = []

for strategy_file in strategy_files:
    filepath = os.path.join(strategies_path, strategy_file)
    
    if not os.path.exists(filepath):
        print(f"\n[X] {strategy_file}: ARCHIVO NO ENCONTRADO")
        continue
    
    with open(filepath, 'r', encoding='utf-8') as f:
        lines = f.readlines()
        content = ''.join(lines)
    
    print(f"\n{'='*80}")
    print(f"{strategy_file.upper()}")
    print('='*80)
    
    findings = {
        'file': strategy_file,
        'conditions': [],
        'thresholds': [],
        'bottlenecks': []
    }
    
    # 1. Buscar metodo evaluate
    evaluate_start = None
    for i, line in enumerate(lines):
        if 'def evaluate' in line:
            evaluate_start = i
            break
    
    if evaluate_start is None:
        print("[X] CRITICO: Sin metodo evaluate()")
        findings['bottlenecks'].append("Sin metodo evaluate")
        bottlenecks.append(findings)
        continue
    
    print(f"[OK] Metodo evaluate en linea {evaluate_start + 1}")
    
    # 2. Extraer condiciones del evaluate (primeras 100 lineas del metodo)
    evaluate_section = lines[evaluate_start:min(evaluate_start + 100, len(lines))]
    
    # 3. Buscar condiciones if con comparaciones numericas
    conditions_found = []
    
    for i, line in enumerate(evaluate_section):
        # Buscar if statements
        if re.search(r'\bif\b', line):
            # Extraer la condicion
            condition = line.strip()
            
            # Buscar comparaciones numericas
            numeric_comparisons = re.findall(r'([a-zA-Z_]\w*)\s*([><]=?|==)\s*([\d.]+)', condition)
            
            if numeric_comparisons:
                for var, op, value in numeric_comparisons:
                    conditions_found.append({
                        'line': evaluate_start + i + 1,
                        'variable': var,
                        'operator': op,
                        'threshold': float(value),
                        'text': condition[:80]
                    })
    
    if conditions_found:
        print(f"\n[INFO] {len(conditions_found)} condiciones numericas encontradas:")
        
        # Identificar umbrales potencialmente restrictivos
        restrictive = []
        
        for cond in conditions_found:
            threshold = cond['threshold']
            op = cond['operator']
            
            # Umbrales restrictivos segun tipo de operador
            is_restrictive = False
            reason = ""
            
            if op == '>' and threshold > 0.7:
                is_restrictive = True
                reason = f"Requiere {cond['variable']} > {threshold} (MUY ALTO)"
            elif op == '>=' and threshold > 0.8:
                is_restrictive = True
                reason = f"Requiere {cond['variable']} >= {threshold} (MUY ALTO)"
            elif op == '<' and threshold < 0.3:
                is_restrictive = True
                reason = f"Requiere {cond['variable']} < {threshold} (MUY BAJO)"
            elif op == '<=' and threshold < 0.2:
                is_restrictive = True
                reason = f"Requiere {cond['variable']} <= {threshold} (MUY BAJO)"
            
            if is_restrictive:
                restrictive.append({
                    'condition': cond,
                    'reason': reason
                })
                print(f"  [!] RESTRICTIVO (linea {cond['line']}): {reason}")
                findings['bottlenecks'].append(reason)
            else:
                print(f"  [-] Linea {cond['line']}: {cond['variable']} {op} {threshold}")
        
        findings['conditions'] = conditions_found
        findings['restrictive_count'] = len(restrictive)
    else:
        print("\n[WARNING] Sin condiciones numericas explicitas detectadas")
        print("          Posible logica compleja o umbral implicito")
        findings['bottlenecks'].append("Sin condiciones explicitas - logica opaca")
    
    # 4. Buscar return None (rechazos)
    return_none_count = content.count('return None')
    if return_none_count > 0:
        print(f"\n[INFO] {return_none_count} puntos de salida 'return None'")
        if return_none_count > 5:
            print("       [!] EXCESIVO - muchas validaciones que rechazan señales")
            findings['bottlenecks'].append(f"Excesivos return None: {return_none_count}")
    
    # 5. Buscar lookback periods
    lookback_matches = re.findall(r'lookback[_\w]*\s*=\s*(\d+)', content)
    if lookback_matches:
        lookback_values = [int(v) for v in lookback_matches]
        print(f"\n[INFO] Lookback periods: {lookback_values}")
        if any(v > 100 for v in lookback_values):
            print("       [!] Lookback periods muy largos detectados")
            findings['bottlenecks'].append(f"Lookback excesivo: {max(lookback_values)}")
    
    # 6. Verificar requisitos de volumen
    volume_conditions = re.findall(r'volume.*[><]=?\s*([\d.]+)', content, re.IGNORECASE)
    if volume_conditions:
        print(f"\n[INFO] Condiciones de volumen: {len(volume_conditions)}")
        high_volume = [float(v) for v in volume_conditions if float(v) > 1000000]
        if high_volume:
            print(f"       [!] Requisitos de volumen muy altos: {high_volume}")
            findings['bottlenecks'].append(f"Volumen minimo alto: {min(high_volume)}")
    
    bottlenecks.append(findings)

# RESUMEN CONSOLIDADO
print("\n" + "="*80)
print("RESUMEN CONSOLIDADO - CUELLOS DE BOTELLA IDENTIFICADOS")
print("="*80)

total_bottlenecks = sum(len(s['bottlenecks']) for s in bottlenecks)
print(f"\nTotal de restricciones identificadas: {total_bottlenecks}")

# Estrategias mas restrictivas
restrictive_strategies = sorted(
    [(s['file'], len(s['bottlenecks'])) for s in bottlenecks],
    key=lambda x: x[1],
    reverse=True
)

print("\nEstrategias mas restrictivas:")
for strategy, count in restrictive_strategies[:5]:
    if count > 0:
        print(f"  {count} restricciones: {strategy}")

# Guardar resultados detallados
import json
with open('C:/TradingSystem/audit_report/evidence/bottleneck_analysis.json', 'w') as f:
    json.dump(bottlenecks, f, indent=2)

print("\nAnalisis detallado guardado en: bottleneck_analysis.json")
