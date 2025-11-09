
import MetaTrader5 as mt5
if not mt5.initialize():
    print("ERROR: MT5 no inicializado - Abra MetaTrader 5 manualmente")
    exit(1)
account = mt5.account_info()
print(f"Broker: {account.server}")
print(f"Cuenta: {account.login}")
print(f"Balance: ${account.balance:,.2f}")
mt5.shutdown()
