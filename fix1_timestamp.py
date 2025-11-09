import re

file = 'scripts/live_trading_engine.py'
with open(file, 'r', encoding='utf-8') as f:
    content = f.read()

# Buscar get_market_data y agregar timestamp
pattern = r'(df = pd\.DataFrame\(rates\))'
replacement = r'\1\n        df["timestamp"] = pd.to_datetime(df["time"], unit="s")'

content = re.sub(pattern, replacement, content)

with open(file, 'w', encoding='utf-8') as f:
    f.write(content)

print('FIX 1 APLICADO: timestamp agregado al DataFrame')
