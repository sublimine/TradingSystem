import MetaTrader5 as mt5

if not mt5.initialize():
    print("ERROR: No se pudo inicializar MT5")
    exit(1)

print("Obteniendo simbolos disponibles en AxiCorp...")
symbols = mt5.symbols_get()

if symbols is None or len(symbols) == 0:
    print("No se encontraron simbolos")
    mt5.shutdown()
    exit(1)

print(f"\nTotal de simbolos disponibles: {len(symbols)}")
print("\nSimbolos principales (Forex y Metales):\n")

forex_symbols = []
for s in symbols:
    name = s.name
    # Filtrar forex y metales principales
    if any(pair in name for pair in ['EUR', 'GBP', 'USD', 'JPY', 'AUD', 'CAD', 'CHF', 'NZD', 'XAU', 'XAG']):
        print(f"  {name:20} | {s.description}")
        forex_symbols.append(name)

print(f"\nTotal forex/metales encontrados: {len(forex_symbols)}")
print("\nSimbolos a usar en el script:")
print(forex_symbols[:15])  # Primeros 15

mt5.shutdown()
