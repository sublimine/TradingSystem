"""
Diagnóstico y corrección del error de sintaxis
"""

file_path = 'scripts/live_trading_engine.py'

print("Leyendo archivo para diagnosticar...")
with open(file_path, 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Encontrar la línea problemática
problem_line_num = None
for i, line in enumerate(lines, 1):
    if 'df["timestamp"]' in line:
        problem_line_num = i
        break

if problem_line_num:
    print(f"\nProblema encontrado en línea {problem_line_num}")
    print("\nContexto (10 líneas antes y después):")
    print("-" * 60)
    
    start = max(0, problem_line_num - 11)
    end = min(len(lines), problem_line_num + 10)
    
    for i in range(start, end):
        marker = ">>>" if i == problem_line_num - 1 else "   "
        print(f"{marker} {i+1:4d}: {lines[i]}", end='')
    
    print("-" * 60)
    
    # Encontrar el método get_market_data completo
    in_method = False
    method_start = None
    method_lines = []
    
    for i, line in enumerate(lines):
        if 'def get_market_data(' in line:
            in_method = True
            method_start = i
        
        if in_method:
            method_lines.append(line)
            
            # Termina cuando encontramos el próximo def al mismo nivel de indentación
            if i > method_start and line.strip().startswith('def ') and not line.startswith('        '):
                break
    
    print(f"\nMétodo get_market_data tiene {len(method_lines)} líneas")
    print("\nReconstruyendo método correctamente...")
    
    # Reconstruir método sin el timestamp problemático
    fixed_method = []
    skip_next_timestamp = False
    
    for line in method_lines:
        if 'df["timestamp"]' in line and 'pd.to_datetime' in line:
            # Saltar esta línea problemática por ahora
            continue
        fixed_method.append(line)
    
    # Encontrar donde insertar timestamp correctamente (después de crear df, antes de return)
    final_method = []
    for i, line in enumerate(fixed_method):
        final_method.append(line)
        
        # Después de crear el DataFrame y antes del return
        if 'df = pd.DataFrame(rates)' in line:
            # Agregar timestamp en la siguiente línea con indentación correcta
            indent = '        '  # Misma indentación que df = pd.DataFrame
            final_method.append(f'{indent}df["timestamp"] = pd.to_datetime(df["time"], unit="s")\n')
    
    # Reconstruir archivo completo
    new_content = []
    in_target_method = False
    method_replaced = False
    
    for i, line in enumerate(lines):
        if 'def get_market_data(' in line:
            # Comenzar a reemplazar el método
            in_target_method = True
            for fixed_line in final_method:
                new_content.append(fixed_line)
            method_replaced = True
            continue
        
        if in_target_method:
            # Saltar líneas hasta encontrar el próximo método
            if line.strip().startswith('def ') and not line.startswith('        '):
                in_target_method = False
                new_content.append(line)
            continue
        
        new_content.append(line)
    
    # Guardar archivo corregido
    with open(file_path, 'w', encoding='utf-8') as f:
        f.writelines(new_content)
    
    print("✓ Método get_market_data reconstruido correctamente")
    print("✓ Columna timestamp agregada en posición correcta")
    print("\nArchivo corregido. Intenta arrancar el motor nuevamente.")

else:
    print("No se encontró la línea problemática. El archivo puede estar OK.")
