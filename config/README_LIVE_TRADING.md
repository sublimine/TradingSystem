# Live Trading Configuration - MANDATO 23

## ⚠️ CRITICAL: LIVE TRADING SETUP ⚠️

Este documento explica cómo configurar y activar **LIVE TRADING** con **DINERO REAL**.

---

## Estado Actual: DISABLED

Por defecto, LIVE trading está **DESACTIVADO** para prevenir ejecución accidental de órdenes reales.

```yaml
# config/live_trading_config.yaml
live_trading:
  enabled: false  # ← DEBE ser cambiado a 'true' explícitamente
```

---

## Habilitación de LIVE Trading

### Paso 1: Verificar Prerequisites

Antes de habilitar LIVE trading, asegúrate de que:

- ✅ Sistema testeado completamente en modo PAPER
- ✅ Smoke tests pasados
- ✅ Estrategias calibradas y validadas
- ✅ MT5 configurado con cuenta REAL
- ✅ Risk limits configurados correctamente
- ✅ Kill Switch entendido y testeado
- ✅ Operador entrenado en procedimientos de emergencia

### Paso 2: Configurar live_trading_config.yaml

Edita `config/live_trading_config.yaml`:

```yaml
live_trading:
  enabled: true  # ← CAMBIAR A true

  # Ajustar parámetros según tu broker
  max_latency_ms: 500
  max_ping_age_seconds: 30
  max_corrupted_ticks: 10

  # Risk limits (CRÍTICOS)
  risk_limits:
    max_daily_loss_pct: 0.02  # 2% daily loss
    max_reject_rate_pct: 0.30
    max_exposure_pct: 0.50
```

### Paso 3: Configurar MT5

Asegúrate de que MT5 esté configurado:

```yaml
mt5:
  max_retries: 5
  base_delay: 2.0
```

Verifica conexión:

```bash
# Test MT5 connection
python -c "import MetaTrader5 as mt5; print('OK' if mt5.initialize() else 'FAIL')"
```

### Paso 4: Test en Modo PAPER Primero

```bash
# SIEMPRE testear en PAPER primero
python main_with_execution.py --mode paper --capital 10000
```

Verifica:
- ✅ Órdenes se ejecutan correctamente (simuladas)
- ✅ P&L tracking funciona
- ✅ Risk limits se respetan
- ✅ Logging completo

### Paso 5: Activar LIVE Trading

```bash
# LIVE MODE (REAL MONEY)
python main_with_execution.py --mode live --capital 10000
```

El sistema pedirá **3 confirmaciones**:

```
Type 'YES' to confirm live trading: YES
Type 'CONFIRM' to proceed with REAL money: CONFIRM
Final confirmation - Type 'LIVE' to start: LIVE
```

---

## Kill Switch - 4 Capas de Protección

El sistema usa un **Kill Switch Multi-Capa** para prevenir pérdidas catastróficas.

### Capa 1: Operador (Config Flag)

```yaml
live_trading:
  enabled: false  # ← Si es false, TODAS las órdenes bloqueadas
```

**Estado**: `DISABLED_BY_OPERATOR`

### Capa 2: Risk / Circuit Breakers

Monitorea:
- Daily loss > 2%
- Reject rate > 30%
- Exposure > 50%

**Estado**: `RISK_BREACH`

### Capa 3: Broker Health

Verifica cada 10s:
- Latencia < 500ms
- Heartbeat < 30s stale
- Conexión activa

**Estado**: `BROKER_UNHEALTHY`

### Capa 4: Data Integrity

Valida cada tick:
- Bid/Ask positivos
- Spread < 1%
- Timestamp reciente
- Corrupted ticks < 10

**Estado**: `DATA_INTEGRITY_FAIL`

---

## Monitoreo LIVE

### Check Kill Switch Status

```bash
# Monitor kill switch en tiempo real
python scripts/monitor_live_trading.py
```

Output:
```
Kill Switch Status: OPERATIONAL
  ✓ Operator: ENABLED
  ✓ Risk: HEALTHY
  ✓ Broker: HEALTHY (latency=45ms)
  ✓ Data: HEALTHY (quality=98%)
```

### Emergency Stop

```bash
# DETENER TODAS LAS ÓRDENES INMEDIATAMENTE
python scripts/emergency_stop_live.py
```

Esto activa el kill switch y **bloquea TODAS las órdenes nuevas** (no cierra posiciones existentes).

---

## Logs & Auditoría

Todos los eventos LIVE se registran en:

```
logs/trading_system.log          # Log general
logs/live_execution.log          # Órdenes LIVE solamente
logs/kill_switch_events.log      # Eventos kill switch
logs/critical_events.log         # Eventos críticos
```

### Formato de Log LIVE

```
2025-11-14 10:15:30 - CRITICAL - 🚨 LIVE ORDER: EURUSD BUY 1.0 lots (type=market, SL=1.0950, TP=1.1050)
2025-11-14 10:15:30 - CRITICAL - ✅ LIVE ORDER FILLED: ticket=12345, price=1.1000, volume=1.0
```

---

## Procedimientos de Emergencia

### Escenario 1: Broker Desconectado

**Síntomas**: `BROKER_UNHEALTHY`, latencia alta, timeout

**Acciones**:
1. Kill switch se activa automáticamente
2. NO se envían órdenes nuevas
3. Posiciones existentes NO se cierran automáticamente
4. Operador debe decidir: cerrar manualmente o esperar reconexión

**Comando Manual**:
```bash
python scripts/emergency_close_all_positions.py  # SI es necesario
```

### Escenario 2: Daily Loss Excedido

**Síntomas**: `RISK_BREACH`, daily loss > 2%

**Acciones**:
1. Kill switch se activa automáticamente
2. NO se envían órdenes nuevas
3. Posiciones existentes quedan abiertas
4. Operador revisa posiciones y decide si cerrar

### Escenario 3: Data Integrity Fail

**Síntomas**: `DATA_INTEGRITY_FAIL`, ticks corruptos

**Acciones**:
1. Kill switch se activa automáticamente
2. NO se envían órdenes nuevas
3. Revisar feed de datos
4. Contactar broker si persiste

### Escenario 4: Emergency Stop Manual

**Comando**:
```bash
python scripts/emergency_stop_live.py --reason "Market volatility extreme"
```

**Resultado**:
- Kill switch → `EMERGENCY_STOP`
- TODAS las órdenes bloqueadas
- Posiciones existentes NO cerradas automáticamente

**Reset**:
```bash
python scripts/reset_kill_switch.py  # Después de resolver issue
```

---

## Checklist Pre-LIVE

Antes de activar LIVE trading, verifica:

- [ ] Sistema testeado en PAPER por al menos 1 semana
- [ ] Smoke tests pasados (todos)
- [ ] Estrategias calibradas con datos REALES
- [ ] Hold-out validation completo
- [ ] Risk limits configurados conservativamente
- [ ] MT5 cuenta REAL configurada correctamente
- [ ] Kill switch testeado (desactivar/activar manualmente)
- [ ] Procedimientos de emergencia entendidos
- [ ] Operador capacitado
- [ ] Notificaciones configuradas (opcional)
- [ ] Capital adecuado (mínimo $10,000 recomendado)
- [ ] Backup plan definido

---

## FAQ

### ¿Puedo testear LIVE mode sin dinero real?

Sí, usa una cuenta **DEMO** de MT5 pero con `--mode live`:

```bash
python main_with_execution.py --mode live --capital 10000
# MT5 conectado a cuenta DEMO
```

Esto te permite testear el flujo completo de LIVE execution (incluyendo kill switch) sin riesgo.

### ¿Qué pasa si se cae la conexión a internet?

El kill switch detectará:
- Broker heartbeat stale (> 30s)
- Estado → `BROKER_UNHEALTHY`
- NO se envían órdenes nuevas

Posiciones existentes quedan abiertas con sus SL/TP en el servidor del broker.

### ¿El kill switch cierra posiciones automáticamente?

**NO**. El kill switch SOLO bloquea **nuevas órdenes**. Las posiciones existentes quedan abiertas.

Razón: Cerrar posiciones automáticamente puede causar slippage severo en momentos de volatilidad.

El operador debe decidir manualmente si cerrar posiciones.

### ¿Cómo sé si el kill switch está funcionando?

Testea manualmente:

```bash
# 1. Activar LIVE mode
python main_with_execution.py --mode live

# 2. En otra terminal, activar emergency stop
python scripts/emergency_stop_live.py

# 3. Intentar colocar orden → Debe ser bloqueada
```

### ¿Puedo cambiar de LIVE a PAPER en caliente?

**NO**. Debes detener el sistema y reiniciar en modo PAPER.

```bash
# Stop LIVE
Ctrl+C

# Start PAPER
python main_with_execution.py --mode paper
```

---

## Soporte

Para problemas o dudas:
- Revisar logs en `logs/`
- Ejecutar `python scripts/diagnose_live_system.py`
- Contactar operador senior

**En emergencia**: Usar `emergency_stop_live.py` inmediatamente.

---

**Última actualización**: 2025-11-14
**Mandato**: MANDATO 23 - Live Execution & Kill Switch
**Versión**: 2.1
