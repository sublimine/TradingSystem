file = "scripts/live_trading_engine.py"

with open(file, "r", encoding="utf-8") as f:
    content = f.read()

# Buscar la línea donde se agrega la columna symbol
# y agregar inmediatamente después la configuración de attrs
old_line = "            df['symbol'] = symbol"
new_lines = "            df['symbol'] = symbol\n            df.attrs['symbol'] = symbol"

content = content.replace(old_line, new_lines)

with open(file, "w", encoding="utf-8") as f:
    f.write(content)

print("DataFrame.attrs['symbol'] configurado correctamente")
print("Order Block ahora podrá obtener el símbolo desde metadata")
