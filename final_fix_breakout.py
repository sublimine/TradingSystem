"""
Corrección Definitiva: AbsorptionBreakout Constructor
"""

from pathlib import Path

file_path = Path('C:/Users/Administrator/TradingSystem/src/strategies/breakout_volume_confirmation.py')

print("=" * 70)
print("CORRECCIÓN FINAL: AbsorptionBreakout")
print("=" * 70)
print()

if not file_path.exists():
    print("✗ Archivo no encontrado")
    exit(1)

content = file_path.read_text(encoding='utf-8')

# El problema: la firma del __init__ no coincide con lo que el motor espera
# El motor llama: Strategy(config)
# Pero AbsorptionBreakout espera algo diferente

# Buscar el __init__ actual
import re

# Encontrar la línea del __init__
init_pattern = r'def __init__\(self[^)]*\):'
init_match = re.search(init_pattern, content)

if not init_match:
    print("✗ No se encontró el método __init__")
    exit(1)

current_init = init_match.group(0)
print(f"Constructor actual encontrado:")
print(f"  {current_init}")
print()

# Reemplazar con la firma correcta que espera el motor
# Todas las otras estrategias usan: def __init__(self, config: Dict):
correct_init = "def __init__(self, config: Dict):"

content = content.replace(current_init, correct_init)

# Asegurarse de que llama correctamente a super().__init__
# Buscar la línea de super().__init__ si existe
if "super().__init__(" in content:
    # Ya existe, verificar que sea correcta
    # Debe ser: super().__init__("absorption_breakout", config)
    super_pattern = r"super\(\).__init__\([^)]*\)"
    super_match = re.search(super_pattern, content)
    
    if super_match:
        current_super = super_match.group(0)
        correct_super = 'super().__init__("absorption_breakout", config)'
        content = content.replace(current_super, correct_super)
        print("✓ Llamada a super().__init__() corregida")
else:
    # No existe, necesitamos agregarla
    # Buscar dónde termina la firma del __init__ y agregar la llamada
    init_line_pattern = r'(def __init__\(self, config: Dict\):)\s*\n'
    replacement = r'\1\n        super().__init__("absorption_breakout", config)\n'
    content = re.sub(init_line_pattern, replacement, content)
    print("✓ Llamada a super().__init__() agregada")

print()

# Guardar el archivo corregido
file_path.write_text(content, encoding='utf-8')

print("✓ Archivo guardado con correcciones")
print()

# Verificar la corrección intentando importar
print("Verificando corrección...")
print()

import sys
sys.path.insert(0, 'C:/Users/Administrator/TradingSystem/src')

try:
    # Intentar importar
    from strategies.breakout_volume_confirmation import AbsorptionBreakout
    
    # Intentar instanciar con un config vacío
    test_config = {}
    test_strategy = AbsorptionBreakout(test_config)
    
    print("✓✓✓ CORRECCIÓN EXITOSA ✓✓✓")
    print()
    print("AbsorptionBreakout ahora se puede instanciar correctamente.")
    print("El motor podrá cargar esta estrategia en el próximo arranque.")
    
except Exception as e:
    print(f"✗ Error durante verificación: {str(e)}")
    print()
    print("La estrategia aún tiene problemas. Detalles técnicos:")
    import traceback
    traceback.print_exc()

print()
print("=" * 70)
