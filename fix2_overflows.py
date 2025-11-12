file = 'scripts/live_trading_engine.py'
with open(file, 'r', encoding='utf-8') as f:
    content = f.read()

# Fix overflow 1
old1 = 'imbalance = abs(buy_volume - sell_volume) / total_volume'
new1 = 'imbalance = abs(float(buy_volume) - float(sell_volume)) / float(total_volume) if total_volume > 0 else 0.0'
content = content.replace(old1, new1)

# Fix overflow 2  
old2 = "features['order_book_imbalance'] = float((buy_vol - sell_vol) / total) if total > 0 else 0.0"
new2 = "features['order_book_imbalance'] = (float(buy_vol) - float(sell_vol)) / float(total) if total > 0 else 0.0"
content = content.replace(old2, new2)

with open(file, 'w', encoding='utf-8') as f:
    f.write(content)

print('FIX 2 APLICADO: Overflows corregidos con conversiones explícitas')
