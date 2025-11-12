
================================================================================
RIESGO Y EJECUCIÓN
================================================================================

SIZING (1% POR OPERACIÓN)
--------------------------

Regla: Riesgo máximo 1% del capital por operación

Fórmula actual:
  volume = symbol_info.volume_min

Implementación futura (TODO):
  account_balance = mt5.account_info().balance
  risk_amount = account_balance * 0.01
  sl_distance = abs(entry_price - stop_loss)
  volume = risk_amount / (sl_distance * contract_size)
  volume = max(volume, symbol_info.volume_min)
  volume = min(volume, symbol_info.volume_max)

Inputs:
- account_balance: float
- entry_price: float (de la señal)
- stop_loss: float (de la señal)
- contract_size: float (por símbolo)

Validaciones:
- volume >= volume_min
- volume <= volume_max
- volume múltiplo de volume_step

Límites:
- Max open positions global: ilimitado actualmente
- Max open per symbol: 2
- Max risk simultáneo: Sin límite hard (depende de # operaciones activas)

POLÍTICAS SL/TP
---------------

Definición: Por estrategia en Signal
Estructura típica:
- SL: entry ± (ATR * multiplicador)
- TP: entry ± (ATR * multiplicador_tp)

Trailing:
- No implementado actualmente
- Futuro: Trailing stop basado en ATR

Límites diarios:
- No implementados
- Futuro: Max drawdown diario → auto-stop

Correlación de posiciones:
- No gestionada actualmente
- Futuro: Evitar posiciones correlacionadas simultáneas

FILL POLICIES
-------------

MT5 order_send():
  filling: ORDER_FILLING_FOK (Fill or Kill)
  deviation: 20 pips
  
Reintentos:
- No automáticos actualmente
- Si falla: log y continuar

Slippage:
- Aceptado hasta deviation (20)
- Mayor slippage → orden rechazada

Comentarios:
- strategy_name (primeros 15 caracteres)
- magic: 234000

VALIDACIÓN PRE-EJECUCIÓN
-------------------------

Checklist:
1. signal.validate() == True
2. can_open_position() == True (anti-spam)
3. symbol_info disponible
4. tick disponible
5. volume válido

Si alguno falla:
- Log error
- No ejecutar
- Continuar con siguiente
