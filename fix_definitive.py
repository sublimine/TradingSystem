"""
Fix Definitivo: Reemplazar método get_market_data completo
"""

file_path = 'scripts/live_trading_engine.py'

with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# Método get_market_data CORRECTO con indentación apropiada
correct_method = '''    def get_market_data(self, symbol: str, bars: int) -> pd.DataFrame:
        try:
            rates = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_M1, 0, bars)

            if rates is None or len(rates) == 0:
                return pd.DataFrame()

            df = pd.DataFrame(rates)
            df["timestamp"] = pd.to_datetime(df["time"], unit="s")
            df['time'] = pd.to_datetime(df['time'], unit='s')
            df['symbol'] = symbol
            df['volume'] = df['tick_volume']

            return df

        except Exception as e:
            logger.error(f"Error obteniendo datos de {symbol}: {e}")
            return pd.DataFrame()'''

# Encontrar y reemplazar el método completo
import re
pattern = r'    def get_market_data\(self, symbol: str, bars: int\) -> pd\.DataFrame:.*?(?=\n    def |\n\nclass |\Z)'
content = re.sub(pattern, correct_method, content, flags=re.DOTALL)

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(content)

print("Método get_market_data reemplazado completamente")
print("Estructura try/except corregida")
print("Timestamp agregado en posición correcta con indentación apropiada")
