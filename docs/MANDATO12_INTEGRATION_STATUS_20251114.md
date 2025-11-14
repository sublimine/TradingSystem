# MANDATO 12 - INTEGRATION STATUS

**Proyecto**: SUBLIMINE TradingSystem
**Mandato**: MANDATO 12 - Integración Reporting con Motor de Trading
**Fecha**: 2025-11-14
**Branch**: `claude/mandato9-phase2-broken-rewrite-20251114-011kZAt34EBQTKQG8Zg7avM6`

---

## FASE 1 - COMPLETADO ✅

### 1. Database Layer (Postgres Integration)

**Archivos Creados**:
- `config/reporting_db.yaml` - Configuración de Postgres con soporte de variables de entorno
- `src/reporting/db.py` - ReportingDatabase class con:
  - Connection pooling (`psycopg2.pool.ThreadedConnectionPool`)
  - Batch inserts para performance
  - Fallback a JSONL si DB no disponible
  - Métodos: `insert_trade_events()`, `insert_position_snapshot()`, `insert_risk_snapshot()`

**Status**: ✅ COMPLETO

### 2. ExecutionEventLogger - Postgres Integration

**Archivo Modificado**:
- `src/reporting/event_logger.py`

**Cambios**:
- Import de `ReportingDatabase` con graceful degradation
- Constructor acepta `db: ReportingDatabase` o `config_path` para auto-creación
- Método `flush()` ahora llama a `db.insert_trade_events()` en batch
- Emergency fallback a JSONL local si DB falla completamente
- Métodos de logging sin cambios (API compatible)

**Status**: ✅ COMPLETO

### 3. PositionManager Hooks

**Archivo Modificado**:
- `src/core/position_manager.py`

**Cambios**:
- **PositionTracker**:
  - Constructor acepta `event_logger: Optional[ExecutionEventLogger]`
  - `update_stop()`: Hook a `event_logger.log_sl_adjustment()`
  - `partial_exit()`: Hook a `event_logger.log_partial()`

- **MarketStructurePositionManager**:
  - Constructor acepta `event_logger: Optional[ExecutionEventLogger]`
  - `add_position()`: Pasa `event_logger` a PositionTracker
  - `_handle_stop_hit()`: Hook a `event_logger.log_exit()` con `exit_reason='SL_HIT'`
  - `_handle_target_hit()`: Hook a `event_logger.log_exit()` con `exit_reason='TP_HIT'`

**Datos capturados**:
- SL adjustments (breakeven, trailing structure)
- Partial exits (con % cerrado, precio, PnL parcial)
- Exits completos (SL/TP hits con MFE, MAE, R-multiple, holding time)

**Status**: ✅ COMPLETO

---

## FASE 2 - PENDIENTE ⏳

### 4. Hooks Adicionales en Core Components

**Pendiente: RiskManager**

Ubicación: `src/core/risk_manager.py`

Hooks necesarios:
- `QualityScorer.calculate_quality()`: Log calidad evaluada (opcional, para análisis)
- `RiskManager.evaluate_signal()`: Log rechazos por:
  - Quality score bajo (< threshold)
  - Riesgo insuficiente disponible
  - Max exposure alcanzado
  - Correlación alta con posiciones existentes

Llamar a:
```python
event_logger.log_rejection(
    timestamp=datetime.now(),
    strategy_id=signal['strategy_id'],
    symbol=signal['symbol'],
    reason=rejection_reason,  # "LOW_QUALITY", "MAX_EXPOSURE", "CORRELATION"
    quality_score=quality_score,
    risk_requested_pct=signal['risk_pct']
)
```

**Pendiente: Brain/SignalArbitrator**

Ubicación: `src/core/brain.py`

Hooks necesarios:
- `SignalArbitrator.arbitrate_signals()`: Log si señal rechazada por score bajo
- `InstitutionalBrain.process_signals()`: Log decisiones de no operar

**Pendiente: DecisionLedger**

Ubicación: `src/core/decision_ledger.py`

Hooks necesarios:
- `DecisionLedger.write()`: Si decisión duplicada (idempotencia), podría loggear
- NO es crítico, pero ayuda a entender duplicados rechazados

---

### 5. Entry Logging

**Problema**: Actualmente NO se logea `log_entry()` cuando se abre posición

**Ubicación a Modificar**:
- Buscar donde se ejecuta la orden de apertura (probablemente en `main.py`, `EliteTradingSystem`, o un execution layer)
- Cuando se confirma apertura, crear `TradeRecord` completo y llamar a:

```python
from reporting.event_logger import TradeRecord

trade_record = TradeRecord(
    trade_id=position_id,
    timestamp=datetime.now(),
    symbol=signal['symbol'],
    strategy_id=signal['strategy_id'],
    strategy_name=signal['strategy_name'],
    strategy_category=signal.get('category', 'unknown'),
    setup_type=signal.get('setup_type', ''),
    edge_description=signal.get('edge_description', ''),
    research_basis=signal.get('research_basis', ''),
    direction=signal['direction'],
    quantity=lot_size,
    entry_price=entry_price,
    risk_pct=signal['risk_pct'],
    position_size_usd=position_size,
    stop_loss=signal['stop_loss'],
    take_profit=signal['take_profit'],
    sl_type=signal.get('sl_type', 'STRUCTURAL'),
    tp_type=signal.get('tp_type', 'R_MULTIPLE'),
    # QualityScore breakdown
    quality_score_total=quality_scores['total'],
    quality_pedigree=quality_scores['pedigree'],
    quality_signal=quality_scores['signal'],
    quality_microstructure=quality_scores['microstructure'],
    quality_multiframe=quality_scores['multiframe'],
    quality_data_health=quality_scores['data_health'],
    quality_portfolio=quality_scores['portfolio'],
    # Microstructure context
    vpin=market_context.get('vpin', 0.0),
    ofi=market_context.get('ofi', 0.0),
    cvd=market_context.get('cvd', 0.0),
    depth_imbalance=market_context.get('depth_imbalance', 0.0),
    spoofing_score=market_context.get('spoofing_score', 0.0),
    # Multiframe context
    htf_trend=market_context.get('htf_trend', 'NEUTRAL'),
    mtf_structure=market_context.get('mtf_structure', 'CONSOLIDATION'),
    ltf_entry_quality=market_context.get('ltf_entry_quality', 0.5),
    # Classification
    asset_class=universe_info.get('asset_class', 'FX'),
    region=universe_info.get('region', 'GLOBAL'),
    risk_cluster=universe_info.get('risk_cluster', 'DEFAULT'),
    # Metadata
    regime=regime_detector.current_regime,
    data_health_score=data_health,
    slippage_bps=0.0,  # Actualizar después de ejecución
    notes=f"Entry via {signal['strategy_name']}"
)

event_logger.log_entry(trade_record)
```

**Complejidad**: MEDIA - Requiere encontrar punto exacto de ejecución

---

### 6. Backfill Historical Data

**Objetivo**: Poblar DB con datos históricos de trades ya ejecutados

**Implementación**:

Crear script: `scripts/backfill_reporting_db.py`

Funcionalidad:
- Leer trades históricos desde:
  - Logs antiguos (si existen en `reports/raw/*.jsonl`)
  - MT5 history (si accesible via `mt5.history_deals_get()`)
  - CSV exports (si disponibles)

- Para cada trade histórico:
  - Reconstruir `trade_event` compatible con schema
  - Insertar vía `ReportingDatabase.insert_trade_events()`
  - Manejar duplicados (check por `trade_id` + `timestamp`)

- Progress tracking y logging

**Complejidad**: MEDIA - Depende de disponibilidad de datos históricos

**Comando**:
```bash
python scripts/backfill_reporting_db.py --source jsonl --start-date 2025-01-01 --end-date 2025-11-14
python scripts/backfill_reporting_db.py --source mt5 --days 90
```

---

### 7. Smoke Test Mode

**Objetivo**: Validar pipeline completo de reporting sin romper producción

**Implementación**:

Modificar: `scripts/generate_reports.py`

Añadir opción `--smoke-test`:
- Genera datos sintéticos de prueba (10 trades, 5 estrategias, 7 días)
- Inserta en DB via `ReportingDatabase`
- Genera todos los reportes (diario/semanal/mensual)
- Valida que archivos se generen correctamente
- Comprueba que DB contiene los datos esperados
- Cleanup al final (opcional: `--no-cleanup` para inspección)

**Comando**:
```bash
python scripts/generate_reports.py --smoke-test
python scripts/generate_reports.py --smoke-test --no-cleanup  # Para debugging
```

**Validaciones**:
- ✅ DB connection funciona
- ✅ Inserts batch exitosos
- ✅ Agregadores funcionan (by strategy, by asset class, etc.)
- ✅ Metrics calculan correctamente (Sharpe, Sortino, Calmar, etc.)
- ✅ Generators producen markdown válido
- ✅ JSON summary válido

**Complejidad**: BAJA - Principalmente generación de datos mock

---

### 8. Integration en Main Entry Point

**Objetivo**: EliteTradingSystem inicializa ExecutionEventLogger automáticamente

**Ubicación**: `main.py` - Clase `EliteTradingSystem`

**Modificación**:

```python
class EliteTradingSystem:
    def __init__(self, config_path: str = 'config/system_config.yaml', auto_ml: bool = True):
        # ... existing initialization ...

        # Initialize reporting system (MANDATO 12)
        logger.info("Initializing institutional reporting system...")
        try:
            from src.reporting.event_logger import ExecutionEventLogger
            from src.reporting.db import ReportingDatabase

            self.reporting_db = ReportingDatabase(config_path='config/reporting_db.yaml')
            self.event_logger = ExecutionEventLogger(
                db=self.reporting_db,
                buffer_size=100
            )
            logger.info("✓ Reporting system initialized")
        except Exception as e:
            logger.warning(f"Reporting system initialization failed: {e}. Continuing without reporting.")
            self.event_logger = None

        # Pass event_logger to position manager
        self.position_manager = MarketStructurePositionManager(
            self.config['position_management'],
            self.mtf_manager,
            event_logger=self.event_logger  # NEW
        )
```

**Complejidad**: BAJA - Simple wiring

---

### 9. Snapshots de Posiciones y Riesgo

**Objetivo**: Capturar estado del portfolio periódicamente

**Ubicación**: `main.py` - Main loop

**Implementación**:

Cada N minutos (configurable, default: 60):

```python
# En main trading loop
if datetime.now().minute == 0:  # Cada hora
    # Position snapshot
    positions_snapshot = []
    for pos in position_manager.get_all_positions():
        snapshot = {
            'timestamp': datetime.now(),
            'symbol': pos['symbol'],
            'strategy_id': pos['strategy'],
            'trade_id': pos['position_id'],
            'direction': pos['direction'],
            'quantity': pos['remaining_lots'],
            'entry_price': pos['entry_price'],
            'current_price': current_prices[pos['symbol']],
            'unrealized_pnl': calculate_unrealized_pnl(pos),
            'risk_allocated_pct': pos.get('risk_pct', 0.0),
            'stop_loss': pos['current_stop'],
            'take_profit': pos['current_target'],
            'asset_class': universe[pos['symbol']]['asset_class'],
            'region': universe[pos['symbol']]['region'],
            'risk_cluster': universe[pos['symbol']]['risk_cluster']
        }
        positions_snapshot.append(snapshot)

    # Insertar en batch
    if reporting_db:
        for snap in positions_snapshot:
            reporting_db.insert_position_snapshot(snap)

    # Risk snapshot
    risk_snapshot = {
        'timestamp': datetime.now(),
        'total_risk_used_pct': risk_manager.total_risk_used(),
        'total_risk_available_pct': risk_manager.total_risk_available(),
        'max_risk_allowed_pct': risk_manager.max_risk_allowed,
        'risk_by_asset_class': risk_manager.risk_by_asset_class(),
        'risk_by_region': risk_manager.risk_by_region(),
        'risk_by_strategy': risk_manager.risk_by_strategy(),
        'risk_by_cluster': risk_manager.risk_by_cluster(),
        'symbols_at_limit': risk_manager.symbols_at_limit(),
        'strategies_at_limit': risk_manager.strategies_at_limit(),
        'clusters_at_limit': risk_manager.clusters_at_limit(),
        'portfolio_correlation_avg': correlation_tracker.avg_correlation(),
        'herfindahl_index': calculate_herfindahl(positions),
        'rejections_last_hour': rejection_counter.get_last_hour(),
        'circuit_breaker_active': risk_manager.circuit_breaker_active
    }

    if reporting_db:
        reporting_db.insert_risk_snapshot(risk_snapshot)
```

**Complejidad**: MEDIA - Requiere acceso a métricas de riesgo

---

## TESTING

### Unit Tests Necesarios

1. `tests/test_reporting_db.py`:
   - Test connection pooling
   - Test batch inserts
   - Test fallback a JSONL
   - Test retry logic

2. `tests/test_event_logger_integration.py`:
   - Test flush a DB
   - Test emergency fallback
   - Test event formatting

3. `tests/test_position_manager_hooks.py`:
   - Test log_entry cuando se abre posición
   - Test log_sl_adjustment cuando se mueve stop
   - Test log_partial cuando se cierra parcial
   - Test log_exit cuando se cierra posición

### Integration Tests

1. End-to-end smoke test:
   - Generar trade sintético
   - Abrir posición
   - Ajustar SL
   - Cerrar parcial
   - Cerrar completo
   - Verificar 5 eventos en DB

2. Report generation test:
   - Insertar 30 trades sintéticos
   - Generar daily report
   - Generar weekly report
   - Validar métricas

---

## DEPLOYMENT CHECKLIST

### Pre-Deployment

- [ ] Postgres instalado y corriendo
- [ ] Database `sublimine_reporting` creada
- [ ] Schema aplicado: `psql -d sublimine_reporting -f sql/reporting_schema_20251114.sql`
- [ ] Usuario `sublimine_user` con permisos adecuados
- [ ] Variables de entorno configuradas:
  - `REPORTING_DB_HOST`
  - `REPORTING_DB_PORT`
  - `REPORTING_DB_NAME`
  - `REPORTING_DB_USER`
  - `REPORTING_DB_PASSWORD`
- [ ] Directories creados:
  - `reports/raw/` (fallback)
  - `reports/daily/`
  - `reports/weekly/`
  - `reports/monthly/`
- [ ] Smoke test pasado: `python scripts/generate_reports.py --smoke-test`

### Post-Deployment Monitoring

- Monitor logs para:
  - DB connection errors
  - Fallback activations (warning ⚠️)
  - Batch insert failures
  - Emergency fallback usage
- Verificar disk space en `reports/raw/` no crece descontroladamente
- Validar que reportes se generan diariamente
- Comprobar quality correlation semanal (debe estar > 0.3)

---

## NOTAS DE IMPLEMENTACIÓN

### Design Decisions

1. **Optional event_logger**: Todos los hooks usan `if self.event_logger:` para no romper código existente que no pase el parámetro.

2. **Graceful degradation**: DB → JSONL fallback → Emergency JSONL → Log error pero NO crash trading loop.

3. **Batch inserts**: Buffer de 100 eventos antes de flush para minimizar latencia en trading loop.

4. **TYPE_CHECKING import**: `from typing import TYPE_CHECKING` evita circular imports en `position_manager.py`.

5. **Backward compatibility**: `institutional_reports.py` (viejo sistema) puede coexistir. Query from new DB cuando se migre.

### Performance Considerations

- Connection pooling (5 conexiones default) evita overhead de connect/disconnect
- Batch inserts (100 eventos) reducen I/O
- Async flush NO implementado (mantener simplicidad), pero buffer asegura non-blocking

### Security

- **CRÍTICO**: NO commitear `config/reporting_db.yaml` con credenciales reales
- Usar variables de entorno en producción
- Password en `reporting_db.yaml` debe ser placeholder

---

## TIMELINE ESTIMADO (Fase 2)

| Tarea | Complejidad | Tiempo Estimado |
|-------|-------------|-----------------|
| RiskManager hooks | Media | 2-3 horas |
| Brain/Arbiter hooks | Media | 2-3 horas |
| Entry logging | Media | 3-4 horas |
| Backfill script | Media | 4-6 horas |
| Smoke test mode | Baja | 2-3 horas |
| Main integration | Baja | 1-2 horas |
| Snapshots (pos/risk) | Media | 3-4 horas |
| Testing completo | Alta | 6-8 horas |
| **TOTAL** | | **23-33 horas** |

---

## CONTACTO / SOPORTE

Para preguntas sobre esta integración:
- Ver diseño original: `docs/REPORTING_DESIGN_MANDATO11_20251114.md`
- Ver runbook operativo: `docs/REPORTING_RUNBOOK_MANDATO11_20251114.md`
- Ver schema SQL: `sql/reporting_schema_20251114.sql`

---

**VERSIÓN**: 1.0
**ÚLTIMA ACTUALIZACIÓN**: 2025-11-14
**PRÓXIMA REVISIÓN**: Completar Fase 2

