"""
Auditoria arquitectonica - Analisis de flujo de datos
"""
import sys
import re

# Analizar live_trading_engine.py
with open("C:/TradingSystem/scripts/live_trading_engine.py", "r", encoding="utf-8") as f:
    engine_content = f.read()

findings = {
    "data_source": None,
    "strategy_loading": None,
    "position_sizing": None,
    "error_handling": None,
    "reconnection": None
}

# 1. Verificar fuente de datos
if "copy_rates_from_pos" in engine_content or "copy_rates_range" in engine_content:
    findings["data_source"] = "MT5_DIRECT"
    print("✓ CORRECTO: Datos desde MT5 en tiempo real")
else:
    findings["data_source"] = "UNKNOWN"
    print("✗ CRITICO: No se detecta descarga directa desde MT5")

# 2. Verificar carga de estrategias
strategy_pattern = r"from.*strategies.*import"
if re.search(strategy_pattern, engine_content):
    findings["strategy_loading"] = "DYNAMIC"
    print("✓ CORRECTO: Carga dinamica de estrategias")
else:
    findings["strategy_loading"] = "MISSING"
    print("✗ CRITICO: No se detecta carga de estrategias")

# 3. Verificar position sizing
if "calculate_position_size" in engine_content:
    findings["position_sizing"] = "DYNAMIC"
    print("✓ CORRECTO: Position sizing dinamico implementado")
else:
    findings["position_sizing"] = "FIXED"
    print("⚠ WARNING: Position sizing podria ser fijo")

# 4. Verificar manejo de errores
if "try:" in engine_content and "except" in engine_content:
    findings["error_handling"] = "PRESENT"
    print("✓ CORRECTO: Manejo de errores presente")
else:
    findings["error_handling"] = "MISSING"
    print("✗ CRITICO: Sin manejo de errores")

# 5. Verificar reconexion
if "mt5.initialize" in engine_content:
    # Contar intentos de reconexion
    init_count = engine_content.count("mt5.initialize")
    if init_count > 1:
        findings["reconnection"] = "IMPLEMENTED"
        print("✓ CORRECTO: Reconexion implementada")
    else:
        findings["reconnection"] = "SINGLE_ATTEMPT"
        print("⚠ WARNING: Solo un intento de conexion")
else:
    findings["reconnection"] = "MISSING"
    print("✗ CRITICO: Sin inicializacion MT5")

print("\n" + "="*60)
print("RESUMEN ARQUITECTONICO")
print("="*60)
for key, value in findings.items():
    status = "✓" if value not in ["MISSING", "UNKNOWN", "FIXED"] else "✗"
    print(f"{status} {key}: {value}")
