# OBSERVABILITY RUNBOOK - MANDATO 6

**Proyecto**: SUBLIMINE TradingSystem
**Fecha**: 2025-11-13
**Objetivo**: Observabilidad institucional mínima para cierre de P0

---

## ALCANCE INICIAL

Observabilidad para resolver:
- **P0-002**: Sistema sin logging institucional
- **P0-002**: Sin visibilidad de decisiones críticas

**Componentes**:
1. Logging estructurado centralizado
2. Eventos institucionales key
3. Niveles de severidad

---

## SISTEMA DE LOGGING

### Configuración Central

**Módulo**: `src/core/logging_config.py`

**Inicialización**:
```python
from src.core.logging_config import InstitutionalLogger

# Al inicio del sistema
InstitutionalLogger.setup(log_level="INFO", log_dir="logs")
```

**Uso en módulos**:
```python
from src.core.logging_config import get_logger

logger = get_logger(__name__)
logger.info("Mensaje institucional")
```

### Niveles de Logging

| Nivel | Uso | Ejemplo |
|-------|-----|---------|
| **DEBUG** | Detalles técnicos internos | "Calculando quality score: mtf=0.8, structure=0.7" |
| **INFO** | Eventos normales del sistema | "ARBITER_EXECUTE: signal_id=S001, quality=0.85" |
| **WARNING** | Situaciones anómalas no críticas | "RISK_REJECTED: exposure_limit, current=5.9%, max=6.0%" |
| **ERROR** | Errores operativos | "DATA_FEED_ERROR: EURUSD feed timeout" |
| **CRITICAL** | Fallas sistémicas | "SYSTEM_ERROR: Risk manager crashed" |

---

## EVENTOS INSTITUCIONALES

### DecisionLedger

**LEDGER_WRITE**: Nueva decisión escrita
```
INFO | LEDGER_WRITE: decision_uid=abc123 | batch_id=B001 | signal_id=S001
```

**LEDGER_DUPLICATE**: Intento de escritura duplicada (idempotencia)
```
WARNING | LEDGER_DUPLICATE: decision_uid=abc123 | prevented=True
```

### ConflictArbiter

**ARBITER_EXECUTE**: Decisión de ejecutar señal
```
INFO | ARBITER_EXECUTE: signal_id=S001 | instrument=EURUSD | direction=LONG | quality=0.85
```

**ARBITER_REJECT**: Señal rechazada
```
WARNING | ARBITER_REJECT: signal_id=S001 | reason=QUALITY_LOW | quality=0.45 | threshold=0.60
```

**ARBITER_SILENCE**: Sin señales válidas
```
INFO | ARBITER_SILENCE: instrument=EURUSD | horizon=M15 | reason=NO_SIGNALS
```

**ARBITER_CONFLICT**: Conflicto detectado entre señales
```
INFO | ARBITER_CONFLICT: signals=2 | long=1 | short=1 | resolution=SHORT_WINS
```

### RiskManager

**RISK_APPROVED**: Señal aprobada por risk
```
INFO | RISK_APPROVED: signal_id=S001 | quality=0.85 | position_size=0.75% | lot_size=0.50
```

**RISK_REJECTED**: Señal rechazada por risk
```
WARNING | RISK_REJECTED: signal_id=S001 | reason=exposure_limit | current=5.9% | max=6.0%
```

**RISK_QUALITY_LOW**: Señal rechazada por quality baja
```
WARNING | RISK_QUALITY_LOW: signal_id=S001 | quality=0.45 | min_threshold=0.60
```

**RISK_EXPOSURE_LIMIT**: Límite de exposición alcanzado
```
WARNING | RISK_EXPOSURE_LIMIT: type=total | current=5.9% | proposed=1.0% | max=6.0%
```

**CIRCUIT_BREAKER_OPEN**: Circuit breaker activado
```
ERROR | CIRCUIT_BREAKER_OPEN: reason=Z_SCORE_ANOMALY | z_score=2.8 | threshold=2.5 | consecutive_losses=5
```

**CIRCUIT_BREAKER_CLOSE**: Circuit breaker desactivado
```
INFO | CIRCUIT_BREAKER_CLOSE: cooldown_elapsed=120min | status=TRADING_RESUMED
```

### Trading

**TRADE_OPEN**: Nueva operación abierta
```
INFO | TRADE_OPEN: trade_id=T001 | signal_id=S001 | instrument=EURUSD | direction=LONG | size=0.50 | entry=1.1000
```

**TRADE_CLOSE**: Operación cerrada
```
INFO | TRADE_CLOSE: trade_id=T001 | exit=1.1050 | pnl=+0.45% | r_multiple=1.5R
```

**TRADE_SL_HIT**: Stop loss ejecutado
```
WARNING | TRADE_SL_HIT: trade_id=T001 | exit=1.0950 | pnl=-0.30% | r_multiple=-1.0R
```

**TRADE_TP_HIT**: Take profit ejecutado
```
INFO | TRADE_TP_HIT: trade_id=T001 | exit=1.1100 | pnl=+0.90% | r_multiple=3.0R
```

### System

**SYSTEM_START**: Sistema iniciado
```
INFO | SYSTEM_START: version=0.1.0-alpha | config=production | symbols=5
```

**SYSTEM_STOP**: Sistema detenido
```
INFO | SYSTEM_STOP: reason=MANUAL_SHUTDOWN | uptime=24h | trades=15
```

**SYSTEM_ERROR**: Error sistémico
```
CRITICAL | SYSTEM_ERROR: component=RiskManager | error=NullPointerException | stack_trace=...
```

**DATA_FEED_ERROR**: Error en feed de datos
```
ERROR | DATA_FEED_ERROR: feed=MT5 | symbol=EURUSD | error=CONNECTION_TIMEOUT | retry=True
```

---

## UBICACIÓN DE LOGS

### Estructura de archivos

```
logs/
├── sublimine_20251113.log   # Log diario completo
├── sublimine_20251112.log   # Log día anterior
└── ...
```

### Rotación

- **Frecuencia**: Diaria (nuevo archivo cada día)
- **Retención**: 30 días
- **Compresión**: Pendiente (fase 2)

---

## MONITORIZACIÓN

### Eventos críticos que requieren revisión manual

**Diaria**:
- `CIRCUIT_BREAKER_OPEN`: Revisar por qué se activó
- `SYSTEM_ERROR`: Investigar causa raíz
- `DATA_FEED_ERROR`: Verificar conectividad

**Semanal**:
- Count de `RISK_REJECTED` por reason (entender patrones)
- Win rate de trades (`TRADE_CLOSE` con pnl >0)
- Exposure promedio (`RISK_APPROVED` position_size)

### Alertas (fase 2)

**Pendiente integración**:
- Alertas por email si `CRITICAL` logs
- Slack notification si circuit breaker activo >1h
- Métricas a Prometheus/Grafana

---

## USO EN DEBUGGING

### Filtrar logs por evento

```bash
# Ver solo rechazos de risk
grep "RISK_REJECTED" logs/sublimine_20251113.log

# Ver solo trades cerrados
grep "TRADE_CLOSE" logs/sublimine_20251113.log

# Ver errores
grep "ERROR\|CRITICAL" logs/sublimine_20251113.log
```

### Tracing de decisión

Para rastrear una decisión completa:
```bash
# Buscar por signal_id
grep "S001" logs/sublimine_20251113.log

# Output esperado:
# ARBITER_EXECUTE: signal_id=S001 ...
# RISK_APPROVED: signal_id=S001 ...
# TRADE_OPEN: signal_id=S001 ...
# TRADE_CLOSE: trade_id=T001 (linked to S001) ...
```

---

## EXPANSIÓN FUTURA

### Fase 2 (Post-Mandato 6):
- **Métricas estructuradas**: Prometheus/Grafana
- **Tracing distribuido**: OpenTelemetry
- **Log aggregation**: ELK Stack o Loki

### Fase 3 (Pre-Producción):
- **Alerting avanzado**: PagerDuty integration
- **Dashboards en tiempo real**: Grafana
- **Anomaly detection**: ML-based log analysis

---

**Documento vivo**: Actualizar conforme se expanda observabilidad
