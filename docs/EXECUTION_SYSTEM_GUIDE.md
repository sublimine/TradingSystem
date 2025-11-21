# Execution System Guide - FASE 3.2

**PLAN OMEGA - Sistema de Ejecución PAPER/LIVE**

## Overview

Sistema completo de ejecución de órdenes con soporte para modo **PAPER** (simulado) y **LIVE** (dinero real).

### Componentes

```
ExecutionMode (enum)
      ↓
ExecutionConfig
      ↓
ExecutionManager
      ↓
BrokerAdapter (abstract)
   ├── PaperBrokerAdapter ✅ PRODUCTION READY
   └── LiveBrokerAdapter  ⚠️  SKELETON (TODO: implementar)
```

---

## ExecutionMode

Enum que define el modo de operación del sistema.

### Modos Disponibles

| Modo | Descripción | Uso |
|------|-------------|-----|
| `PAPER` | Simulación completa sin dinero real | Testing, validación, desarrollo |
| `LIVE` | Ejecución real en broker conectado | Trading en vivo con dinero real |

### Ejemplo

```python
from src.execution import ExecutionMode

# Modo PAPER
paper_mode = ExecutionMode.PAPER
assert paper_mode.is_paper()  # True
assert not paper_mode.is_live()  # False

# Modo LIVE
live_mode = ExecutionMode.LIVE
assert live_mode.is_live()  # True

# Desde string
mode = ExecutionMode.from_string("paper")  # Acepta "paper" o "PAPER"
```

---

## ExecutionConfig

Configuración del sistema de ejecución con límites de riesgo.

### Parámetros

```python
ExecutionConfig(
    mode: ExecutionMode,            # PAPER o LIVE
    initial_capital: float,         # Capital inicial (solo PAPER)
    max_positions: int,             # Máximo posiciones simultáneas
    max_risk_per_trade: float,      # Riesgo máximo por trade (0.02 = 2%)
    max_daily_loss: float,          # Pérdida máxima diaria (0.05 = 5%)
    broker_config: Optional[Dict]   # Config del broker (para LIVE)
)
```

### Límites de Riesgo (PLAN OMEGA)

⚠️ **LÍMITES ESTRICTOS**:
- `max_risk_per_trade` **≤ 2.5%** (0.025)
- `max_daily_loss` **≤ 10%** (0.10)

Exceder estos límites lanza `ValueError`.

### Ejemplo

```python
from src.execution import ExecutionMode, ExecutionConfig

# Configuración PAPER
paper_config = ExecutionConfig(
    mode=ExecutionMode.PAPER,
    initial_capital=10000.0,
    max_positions=5,
    max_risk_per_trade=0.02,  # 2% por trade
    max_daily_loss=0.05       # 5% pérdida diaria máxima
)

# Configuración LIVE
live_config = ExecutionConfig(
    mode=ExecutionMode.LIVE,
    max_positions=3,
    max_risk_per_trade=0.015,  # 1.5% por trade (conservador)
    broker_config={
        'broker_type': 'oanda',
        'api_key': 'your_api_key',
        'account_id': 'your_account',
        'environment': 'practice'
    }
)
```

---

## PaperBrokerAdapter

Broker simulado para modo PAPER. **PRODUCTION READY** ✅

### Features

- ✅ Simulación completa de órdenes
- ✅ Tracking de posiciones
- ✅ Simulación de slippage y spread
- ✅ Validación de stop loss y take profit
- ✅ Cálculo de P&L realizado y no realizado
- ✅ Estadísticas de trading (WR, profit factor, etc.)
- ✅ Balance y equity tracking

### Ejemplo Básico

```python
from src.execution import PaperBrokerAdapter, Order
from datetime import datetime

# Configurar broker
config = {
    'initial_capital': 10000.0,
    'slippage_pips': 0.5,
    'spread_pips': {'EURUSD': 1.0, 'GBPUSD': 1.5},
    'commission_per_lot': 7.0
}

broker = PaperBrokerAdapter(config)
broker.connect()

# Crear orden
order = Order(
    order_id="ORD_001",
    symbol="EURUSD",
    direction="LONG",
    entry_price=1.1000,
    stop_loss=1.0950,  # 50 pips SL
    take_profit=1.1100,  # 100 pips TP
    position_size=0.1,  # 0.1 lotes
    strategy_name="fvg_institutional",
    timestamp=datetime.now()
)

# Ejecutar orden
success = broker.submit_order(order)
if success:
    print(f"✅ Order filled @ {order.fill_price}")

# Verificar posiciones
positions = broker.get_positions()
print(f"Open positions: {len(positions)}")

# Actualizar con datos de mercado
market_data = {
    'EURUSD': {
        'bid': 1.1050,
        'ask': 1.1051,
        'high': 1.1060,
        'low': 1.1040,
        'close': 1.1050
    }
}
broker.update_positions(market_data)

# Obtener estadísticas
stats = broker.get_statistics()
print(f"Balance: ${stats['current_balance']:.2f}")
print(f"Equity: ${stats['current_equity']:.2f}")
print(f"Win Rate: {stats['win_rate']:.1%}")
```

### Simulación de Slippage y Spread

El broker aplica automáticamente:

- **Spread**: Diferencia bid/ask (configurable por símbolo)
- **Slippage**: Deslizamiento en ejecución (configurable)

```python
# LONG: precio final = entry + spread + slippage
# SHORT: precio final = entry - spread - slippage

# Ejemplo con spread=1.0 pips, slippage=0.5 pips:
# Entry: 1.1000
# LONG fill: 1.10015 (1.1000 + 0.0001 + 0.00005)
# SHORT fill: 1.09985 (1.1000 - 0.0001 - 0.00005)
```

---

## LiveBrokerAdapter

Adaptador para broker real. **SKELETON - NO IMPLEMENTADO** ⚠️

### Advertencias

⚠️ **WARNING: DINERO REAL**

Este adaptador ejecuta órdenes con **dinero real** cuando esté implementado.

**Requisitos antes de usar**:
1. ✅ Testing exhaustivo en modo PAPER
2. ✅ Validación de todas las estrategias
3. ✅ Configuración correcta de API keys
4. ✅ Límites de riesgo configurados
5. ✅ KillSwitch funcionando (FASE 3.3)

### Configuración

```python
# ⚠️ SOLO USAR DESPUÉS DE TESTING EXHAUSTIVO
live_config = {
    'broker_type': 'oanda',  # o 'ib', 'alpaca', etc.
    'api_key': 'your_api_key_here',
    'account_id': 'your_account_id',
    'environment': 'practice',  # o 'live'
    'live_trading_confirmed': True  # DEBE ser True para LIVE
}

broker = LiveBrokerAdapter(live_config)
# TODO: Implementar conexión a broker específico
```

### Estado Actual

El LiveBrokerAdapter es un **skeleton** con estructura completa pero sin implementación:

```python
def connect(self) -> bool:
    logger.error("❌ LiveBroker.connect() NOT IMPLEMENTED")
    return False

def submit_order(self, order) -> bool:
    logger.error("❌ LiveBroker.submit_order() NOT IMPLEMENTED")
    return False

# ... todos los métodos retornan error
```

**TODO FASE 4+**: Implementar conexión a brokers específicos:
- OANDA (oandapyV20)
- Interactive Brokers (ib_insync)
- Alpaca
- Otros

---

## ExecutionManager

Gestor centralizado de ejecución que coordina brokers según ExecutionMode.

### Responsibilities

1. **Gestión de Brokers**: Inicializa broker correcto (PAPER o LIVE)
2. **Conversión de Señales**: Convierte Signal → Order
3. **Cálculo de Position Sizing**: Según riesgo configurado
4. **Validación Pre-Ejecución**: Valida señales antes de ejecutar
5. **Tracking**: Estadísticas de ejecución

### Ejemplo Completo

```python
from src.execution import ExecutionManager, ExecutionMode, ExecutionConfig
from src.strategies.strategy_base import Signal
from datetime import datetime

# 1. Configurar ejecución
config = ExecutionConfig(
    mode=ExecutionMode.PAPER,
    initial_capital=10000.0,
    max_positions=5,
    max_risk_per_trade=0.02
)

# 2. Inicializar manager
manager = ExecutionManager(config)

# 3. Crear señal (viene de estrategia)
signal = Signal(
    timestamp=datetime.now(),
    symbol="EURUSD",
    strategy_name="fvg_institutional",
    direction="LONG",
    entry_price=1.1000,
    stop_loss=1.0950,
    take_profit=1.1100,
    sizing_level=3,  # 1-5, afecta position size
    metadata={'setup_type': 'FVG_RETEST'}
)

# 4. Ejecutar señal
current_price = 1.1000
success = manager.execute_signal(signal, current_price)

if success:
    print("✅ Signal executed")

    # Verificar posiciones
    positions = manager.get_positions()
    for pos in positions:
        print(f"  {pos.symbol} {pos.direction} @ {pos.entry_price}")
        print(f"  SL: {pos.stop_loss}, TP: {pos.take_profit}")
        print(f"  Size: {pos.position_size} lots")

# 5. Actualizar posiciones con mercado
market_data = {
    'EURUSD': {
        'bid': 1.1050,
        'ask': 1.1051,
        'high': 1.1060,
        'low': 1.1040,
        'close': 1.1050
    }
}
manager.update_positions(market_data)

# 6. Obtener estadísticas
stats = manager.get_statistics()
print(f"Signals received: {stats['signals_received']}")
print(f"Orders submitted: {stats['orders_submitted']}")
print(f"Execution rate: {stats['execution_rate']:.1%}")
print(f"Balance: ${stats['balance']:.2f}")
print(f"Equity: ${stats['equity']:.2f}")

# 7. Cerrar todas las posiciones (opcional)
manager.close_all_positions()

# 8. Shutdown
manager.shutdown()
```

### Position Sizing

El ExecutionManager calcula automáticamente el tamaño de posición basado en:

1. **Riesgo configurado** (`max_risk_per_trade`)
2. **Balance disponible**
3. **Distancia al stop loss**
4. **Sizing level** de la señal (1-5)

```python
# Fórmula:
risk_amount = balance * max_risk_per_trade
stop_distance_pips = abs(entry - stop_loss) * 10000
value_per_pip = 10.0  # Para lote estándar

position_size = risk_amount / (stop_distance_pips * value_per_pip)
position_size *= sizing_level / 3.0  # Ajuste por sizing_level

# Límites: 0.01 - 10.0 lotes
position_size = max(0.01, min(position_size, 10.0))
```

---

## Integración con StrategyOrchestrator

El StrategyOrchestrator ahora soporta ejecución automática.

### Modo 1: Solo Generación de Señales

```python
from src.strategy_orchestrator import StrategyOrchestrator

# Sin ExecutionConfig = solo genera señales
orchestrator = StrategyOrchestrator(
    config_path='config/strategies_institutional.yaml'
)

# Generar señales
signals = orchestrator.evaluate_strategies(market_data)

# Procesar señales manualmente
for signal in signals:
    print(f"Signal: {signal.direction} {signal.symbol}")
```

### Modo 2: Ejecución Automática (PAPER)

```python
from src.strategy_orchestrator import StrategyOrchestrator
from src.execution import ExecutionMode, ExecutionConfig

# Con ExecutionConfig = ejecución automática
config = ExecutionConfig(
    mode=ExecutionMode.PAPER,
    initial_capital=10000.0,
    max_positions=5,
    max_risk_per_trade=0.02
)

orchestrator = StrategyOrchestrator(
    config_path='config/strategies_institutional.yaml',
    execution_config=config
)

# Evaluar Y ejecutar automáticamente
result = orchestrator.evaluate_and_execute(market_data)

print(f"Signals generated: {len(result['signals'])}")
print(f"Signals executed: {result['executed']}")
print(f"Open positions: {len(result['positions'])}")
print(f"Balance: ${result['balance']:.2f}")
print(f"Equity: ${result['equity']:.2f}")

# Obtener estadísticas
stats = orchestrator.get_execution_statistics()
print(stats)
```

### Modo 3: Ejecución Automática (LIVE)

⚠️ **SOLO DESPUÉS DE TESTING EXHAUSTIVO**

```python
# ⚠️ WARNING: DINERO REAL
live_config = ExecutionConfig(
    mode=ExecutionMode.LIVE,
    max_positions=3,
    max_risk_per_trade=0.015,  # 1.5% conservador
    broker_config={
        'broker_type': 'oanda',
        'api_key': 'YOUR_API_KEY',
        'account_id': 'YOUR_ACCOUNT',
        'environment': 'live',  # ⚠️  LIVE!
        'live_trading_confirmed': True  # Confirmación explícita
    }
)

orchestrator = StrategyOrchestrator(
    config_path='config/strategies_institutional.yaml',
    execution_config=live_config
)

# Ejecutar en loop
while trading_session_active:
    market_data = get_latest_data()
    result = orchestrator.evaluate_and_execute(market_data)
    time.sleep(60)  # 1 minuto entre evaluaciones
```

---

## Workflow Completo

```
1. Market Data
        ↓
2. MicrostructureEngine
   (calcula OFI, VPIN, CVD, ATR)
        ↓
3. 24 Estrategias
   (evalúan features → generan señales)
        ↓
4. ExecutionManager
   (valida señales → calcula position size)
        ↓
5. BrokerAdapter (PAPER o LIVE)
   (ejecuta órdenes → gestiona posiciones)
        ↓
6. Posiciones Abiertas
   (tracking P&L, stops, targets)
```

---

## Validaciones de Seguridad

### 1. Validación de Señales

Antes de ejecutar, se valida:

- ✅ Campos obligatorios presentes
- ✅ Dirección válida (LONG/SHORT)
- ✅ Stop loss del lado correcto
- ✅ Take profit del lado correcto
- ✅ Riesgo ≤ 2.5% (PLAN OMEGA límite estricto)

### 2. Validación de Órdenes

Al crear Order:

- ✅ Position size > 0
- ✅ SL/TP consistentes con dirección
- ✅ Todos los campos requeridos

### 3. Validación de Capital

Antes de ejecutar:

- ✅ Capital suficiente para riesgo
- ✅ No usar > 50% del balance en una orden
- ✅ Máximo posiciones no excedido

---

## Testing

Script de tests disponible:

```bash
python3 /tmp/test_execution_system.py
```

Tests incluidos:
1. ✅ ExecutionMode enum
2. ✅ ExecutionConfig con validación de límites
3. ✅ Order y Position objects
4. ✅ PaperBrokerAdapter ejecución completa
5. ✅ ExecutionManager gestión
6. ✅ StrategyOrchestrator integración

---

## Checklist Pre-LIVE

Antes de usar modo LIVE, **OBLIGATORIO** completar:

- [ ] ✅ 100+ trades ejecutados en modo PAPER
- [ ] ✅ Win rate ≥ 65% en PAPER
- [ ] ✅ Profit factor ≥ 2.0 en PAPER
- [ ] ✅ Drawdown máximo < 10% en PAPER
- [ ] ✅ Todas las 24 estrategias validadas
- [ ] ✅ KillSwitch implementado y probado (FASE 3.3)
- [ ] ✅ Límites de riesgo configurados
- [ ] ✅ Broker API keys configurados correctamente
- [ ] ✅ Cuenta de práctica probada primero
- [ ] ✅ Emergency stop procedures documentados
- [ ] ✅ Monitoring activo configurado

---

## Troubleshooting

### Error: "max_risk_per_trade exceeds limit"

**Causa**: Riesgo configurado > 2.5%

**Solución**:
```python
config = ExecutionConfig(
    max_risk_per_trade=0.02  # ✅ 2% OK
    # max_risk_per_trade=0.05  # ❌ 5% RECHAZADO
)
```

### Error: "LiveBroker.connect() NOT IMPLEMENTED"

**Causa**: LiveBrokerAdapter es skeleton

**Solución**: Usar modo PAPER hasta que se implemente conexión a broker real (FASE 4+)

### Error: "Signal validation failed"

**Causa**: Señal inválida (SL/TP mal configurados, riesgo excesivo, etc.)

**Solución**: Revisar logs para detalles específicos de validación

---

## Próximos Pasos

**FASE 3.3**: KillSwitch 4-Layer System
- Layer 1: Per-trade risk limits
- Layer 2: Daily drawdown cutoff
- Layer 3: Strategy circuit breaker
- Layer 4: Portfolio emergency stop

**FASE 4+**: LiveBroker Implementation
- Implementar conexión OANDA
- Implementar conexión Interactive Brokers
- Testing extensivo en cuentas de práctica
- Deployment gradual a LIVE

---

**Author**: Elite Institutional Trading System
**Version**: 1.0 - PRODUCTION READY (PAPER mode)
**Date**: 2025-11-16
