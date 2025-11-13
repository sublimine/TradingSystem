# AUDITORÍA P1 - BUGS IMPORTANTES
## ALGORITMO_INSTITUCIONAL_SUBLIMINE

**Fecha**: 2025-11-13
**Auditor**: Claude (Agente Institucional)
**Alcance**: Sistema completo (core, strategies, gatekeepers, features)
**Total identificado**: 27 bugs P1

---

## DISTRIBUCIÓN POR CATEGORÍA

### CATEGORÍA 1: DIVISIÓN POR CERO / VALIDACIONES NUMÉRICAS (10 bugs)

#### BUG-P1-001: División por cero en cálculo de spread quoted
- **Archivo**: `src/gatekeepers/spread_monitor.py`
- **Línea**: 91
- **Severidad**: P1-logic
- **Descripción**: En `calculate_quoted_spread()`, la división por `mid` no valida `mid > 0`. Si `bid=ask=0`, resulta en división por cero.
- **Impacto**: Crash del gatekeeper durante condiciones de mercado degeneradas o datos corruptos. Podría permitir trades con spread incorrecto.
- **Fix sugerido**: Agregar validación: `if mid <= 0: return float('inf')`

#### BUG-P1-002: División por cero en cálculo de effective spread
- **Archivo**: `src/gatekeepers/spread_monitor.py`
- **Línea**: 120
- **Severidad**: P1-logic
- **Descripción**: En `calculate_effective_spread()`, división por `mid_price` sin validación de `mid_price > 0`.
- **Impacto**: Crash del monitor durante datos de mercado anómalos. Sistema puede aprobar trades sin conocer el costo real de transacción.
- **Fix sugerido**: Validar `mid_price > 0` antes de división, retornar spread máximo si inválido.

#### BUG-P1-003: División por total_volume sin validación robusta
- **Archivo**: `src/features/ofi.py`
- **Línea**: 46
- **Severidad**: P1-performance
- **Descripción**: División por `(total_volume + 1e-10)` usa epsilon muy pequeño. Si `total_volume` es exactamente `-1e-10`, aún produce división por cero.
- **Impacto**: NaN en cálculo de OFI que se propaga a estrategias dependientes. Decisiones de trading basadas en señales corruptas.
- **Fix sugerido**: Usar `max(total_volume, 1e-6)` o validación explícita con early return.

#### BUG-P1-004: División por median sin validación
- **Archivo**: `src/gatekeepers/spread_monitor.py`
- **Línea**: 233
- **Severidad**: P1-logic
- **Descripción**: En `get_spread_ratio()`, división por `median` sin validar `median != 0`. El check `"or median == 0"` está después del return.
- **Impacto**: División por cero si spread histórico es exactamente 0 (posible en datos sintéticos o mercados ilíquidos extremos).
- **Fix sugerido**: Invertir el orden del check: `if median is None or median <= 0: return None`

#### BUG-P1-005: RSI con división por avg_loss sin protección
- **Archivo**: `src/features/technical_indicators.py`
- **Línea**: 34
- **Severidad**: P1-logic
- **Descripción**: Cálculo `rs = avg_gain / avg_loss` sin validar `avg_loss > 0`. En mercados trending fuerte alcista, `avg_loss` puede ser 0.
- **Impacto**: RSI = inf o NaN, que contamina señales de estrategias basadas en RSI. Puede causar false positives en condiciones de sobrecompra extrema.
- **Fix sugerido**: `rs = avg_gain / avg_loss.replace(0, 1e-10)` o validación explícita con valor de saturación.

#### BUG-P1-006: Stochastic con división por rango sin validación
- **Archivo**: `src/features/technical_indicators.py`
- **Línea**: 156
- **Severidad**: P1-logic
- **Descripción**: `stoch = 100 * (close - lowest_low) / (highest_high - lowest_low)` sin validar que `highest_high != lowest_low`. Ocurre en mercados planos o low liquidity.
- **Impacto**: Stochastic = inf/NaN durante consolidaciones extremas. Estrategias mean-reversion reciben señales inválidas.
- **Fix sugerido**: Validar rango: `range = highest_high - lowest_low; if range < 1e-10: return pd.Series(50.0, ...)` (neutral)

#### BUG-P1-007: Williams %R con mismo problema que Stochastic
- **Archivo**: `src/features/technical_indicators.py`
- **Línea**: 293
- **Severidad**: P1-logic
- **Descripción**: `williams_r = -100 * (highest_high - close) / (highest_high - lowest_low)` sin validar denominador != 0.
- **Impacto**: Indicador inválido en flat markets, afecta estrategias que usan Williams %R para timing de entradas.
- **Fix sugerido**: Validar `range > epsilon` antes de división.

#### BUG-P1-008: ADX con división por suma sin protección
- **Archivo**: `src/features/technical_indicators.py`
- **Línea**: 245
- **Severidad**: P1-logic
- **Descripción**: `dx = 100 * (plus_di - minus_di).abs() / (plus_di + minus_di)` sin validar denominador > 0. Falla cuando `plus_di = minus_di = 0`.
- **Impacto**: ADX corrupto durante periodos de ATR extremadamente bajo. RegimeEngine clasifica mal el régimen, causando activación incorrecta de estrategias.
- **Fix sugerido**: `sum_di = plus_di + minus_di; dx = 100 * diff.abs() / sum_di.replace(0, 1)`

#### BUG-P1-009: CCI con división por mean_deviation
- **Archivo**: `src/features/technical_indicators.py`
- **Línea**: 317
- **Severidad**: P1-logic
- **Descripción**: `cci = (typical_price - sma_tp) / (constant * mean_deviation)` sin validar `mean_deviation > 0`.
- **Impacto**: CCI = inf durante periodos de precio completamente estable. False signals en estrategias de channel breakout.
- **Fix sugerido**: Validar `mean_deviation > epsilon`, retornar 0 si desviación es negligible.

#### BUG-P1-010: Kelly criterion con división por avg_loss
- **Archivo**: `src/core/position_sizer.py`
- **Líneas**: 111, 120
- **Severidad**: P1-logic
- **Descripción**: División `b = avg_win / avg_loss` y `kelly = (p * b - q) / b` sin validar `avg_loss != 0` y `b != 0`. El check en línea 108 setea `avg_loss = 1.0` solo si `== 0` exactamente, pero no considera valores muy pequeños.
- **Impacto**: Kelly fraction incorrecta con `avg_loss` cercano a 0 (estrategias con stop muy tight). Over-sizing catastrófico en edge cases.
- **Fix sugerido**: `avg_loss = max(abs(avg_loss), 0.1)` (mínimo razonable)

---

### CATEGORÍA 2: ITERACIÓN SOBRE ESTRUCTURAS MUTABLES (3 bugs)

#### BUG-P1-011: Iteración sobre dict mientras se modifica
- **Archivo**: `src/core/decision_ledger.py`
- **Líneas**: 92-104
- **Severidad**: P1-concurrency
- **Descripción**: El método `add_execution_metadata()` itera sobre `self.decisions` (dict) con `"for decision in self.decisions"` pero decisions es un OrderedDict de uuids como keys. Busca `decision['decision_id']` asumiendo que decision es un dict, pero es solo un string (el key).
- **Impacto**: `add_execution_metadata()` nunca actualiza nada. Metadata de ejecución (mid_at_fill, hold_ms, etc.) se pierde, impidiendo TCA post-trade. Loop inútil que consume CPU sin resultado.
- **Fix sugerido**: `for uid, decision_data in self.decisions.items(): if decision_data['payload'].get('decision_id') == decision_id: ...`

#### BUG-P1-012: Falta thread-safety en add_execution_metadata
- **Archivo**: `src/core/decision_ledger.py`
- **Líneas**: 67-104
- **Severidad**: P1-concurrency
- **Descripción**: `add_execution_metadata()` no usa locks pero modifica `self.decisions` que es accedido concurrentemente por `write()` (que usa lock implícito en LRU). Race condition posible.
- **Impacto**: Metadata puede escribirse a decision incorrecta o perderse durante escritura concurrente. Corrupción de ledger en producción multi-thread.
- **Fix sugerido**: Agregar `with self.lock: ...` o mejor, hacer decisions thread-safe con RLock.

#### BUG-P1-013: Iteración sobre correlation_tracker sin lock
- **Archivo**: `src/core/correlation_tracker.py`
- **Líneas**: 68-79
- **Severidad**: P1-concurrency
- **Descripción**: `update_correlation_matrix()` itera sobre `self.strategy_returns.keys()` sin lock, pero `record_signal_outcome()` modifica `strategy_returns` concurrentemente.
- **Impacto**: RuntimeError: dictionary changed size during iteration en entorno multi-thread. Sistema de correlation tracking se cae durante alta frecuencia de señales.
- **Fix sugerido**: Agregar `threading.Lock` y proteger tanto record como update. O usar `strategies_snapshot = list(self.strategy_returns.keys())`.

---

### CATEGORÍA 3: MANEJO DE EXCEPCIONES INSUFICIENTE (2 bugs)

#### BUG-P1-014: Bare except sin tipo específico
- **Archivo**: `src/mt5_connector.py`
- **Línea**: 56
- **Severidad**: P1-validation
- **Descripción**: `is_connected()` usa bare `"except:"` que captura SystemExit, KeyboardInterrupt, etc. Puede enmascarar errores críticos.
- **Impacto**: Sistema puede interpretar un crash de MT5 como "desconectado normal". Intenta continuar trading sin conexión válida, causando pérdida de órdenes.
- **Fix sugerido**: `except Exception: return False` (excluir BaseException subclasses)

#### BUG-P1-015: Excepción genérica en régimen crítico
- **Archivo**: `src/core/signal_bus.py`
- **Líneas**: 98-100
- **Severidad**: P1-validation
- **Descripción**: En `process_decision_tick()`, captura Exception pero convierte a REJECT sin logging detallado del traceback. El `exc_info=True` registra, pero no hay alerting.
- **Impacto**: Errores en arbiter se silencian. Decisiones críticas se rechazan sin alarma visible en dashboard. Pérdida de oportunidades sin visibilidad de root cause.
- **Fix sugerido**: Agregar severity CRITICAL al log y optional raise después de log para fail-fast mode.

---

### CATEGORÍA 4: CÁLCULOS CON NaN/Inf PROPAGATION (5 bugs)

#### BUG-P1-016: Std() sin validación de datos suficientes
- **Archivo**: `src/core/conflict_arbiter.py`
- **Línea**: 688
- **Severidad**: P1-logic
- **Descripción**: `vol_realized = returns.tail(20).std()` sin validar que `tail(20)` tenga datos. Si `returns.tail(20)` está vacío o tiene <2 elementos, `std()` retorna NaN.
- **Impacto**: `vol_component = NaN` propaga a `slippage_bp = NaN`, luego `ev_net_bp = NaN`. Señales rechazadas incorrectamente por EV insuficiente.
- **Fix sugerido**: `vol_realized = returns.tail(20).std() if len(returns.tail(20)) >= 2 else 0.0`

#### BUG-P1-017: Hurst exponent con log de valores negativos
- **Archivo**: `src/core/regime_engine.py`
- **Línea**: 623
- **Severidad**: P1-logic
- **Descripción**: `hurst = np.polyfit(np.log(tau), np.log(rs_values), 1)[0]` sin validar que `rs_values > 0`. Si R/S <= 0 (posible con chunk variance = 0), `np.log` produce -inf.
- **Impacto**: Hurst = NaN o -inf contamina regime classification. Sistema puede entrar en shock regime incorrectamente, deteniendo todas las estrategias.
- **Fix sugerido**: `rs_values = [max(rs, 1e-10) for rs in rs_chunk]` antes de append

#### BUG-P1-018: Covariance de serie muy corta
- **Archivo**: `src/core/regime_engine.py`
- **Línea**: 289
- **Severidad**: P1-logic
- **Descripción**: `cov = np.cov(log_returns.iloc[:-1], log_returns.iloc[1:])[0, 1]` sin validar `len >= 2`. Si log_returns tiene 1 elemento, slicing produce arrays vacíos y cov falla.
- **Impacto**: Exception en `_estimate_effective_spread_roll_log()` interrumpe clasificación de régimen. Fallback a spread = 0 causa underestimación de costos.
- **Fix sugerido**: Mover check `if len(log_returns) < 2` antes de slicing, no después.

#### BUG-P1-019: Variance_sv con threshold muy bajo
- **Archivo**: `src/gatekeepers/kyles_lambda.py`
- **Línea**: 170
- **Severidad**: P1-performance
- **Descripción**: Validación `variance_sv > 1e-10` es muy permisiva. Con `variance_sv = 1.1e-10`, `lambda_estimate = cov / 1.1e-10` puede ser gigantesco.
- **Impacto**: Lambda spike artificial indica illiquidity falsa. Sistema halt innecesario durante mercados normales con bajo volume variance.
- **Fix sugerido**: Aumentar threshold a `1e-6` o usar `np.clip(variance_sv, 1e-6, inf)`

#### BUG-P1-020: Sqrt de covariance negativa sin abs()
- **Archivo**: `src/features/microstructure.py`
- **Línea**: 197
- **Severidad**: P1-logic
- **Descripción**: `spread_estimate = 2 * np.sqrt(-covariance)` asume `cov < 0`, pero check `if covariance >= 0` hace fallback. Sin embargo, si `cov = -1e-100` (muy cercano a 0), sqrt puede producir warning.
- **Impacto**: Warnings de NumPy en logs contaminan observability. Edge case: sqrt de valor negativo muy pequeño puede producir NaN en algunas plataformas.
- **Fix sugerido**: Usar `np.sqrt(abs(covariance))` o aumentar threshold de detección.

---

### CATEGORÍA 5: EDGE CASES Y VALIDACIONES FALTANTES (4 bugs)

#### BUG-P1-021: Penetration depth sin validación de valores extremos
- **Archivo**: `src/strategies/liquidity_sweep.py`
- **Líneas**: 184-186
- **Severidad**: P1-logic
- **Descripción**: `penetration_depth = (level_price - recent_bars['low'].min()) * 10000` sin validar que `level_price` y `min()` sean válidos. Si `min()` es NaN, `penetration_depth = NaN`.
- **Impacto**: `criteria_scores['penetration_depth']` nunca es 1. Liquidity sweep nunca detecta sweeps válidos, pérdida total de alpha de esta estrategia.
- **Fix sugerido**: Validar `recent_bars['low'].notna().all()` antes de calcular `min()`.

#### BUG-P1-022: Reversal velocity con división por bars_since_sweep
- **Archivo**: `src/strategies/liquidity_sweep.py`
- **Líneas**: 199-204
- **Severidad**: P1-logic
- **Descripción**: `reversal_velocity = price_reversal / bars_since_sweep` sin validar `bars_since_sweep > 0` (solo valida `!= 0`). Si `bars_since_sweep < 0` (bug en lógica de index), velocity es negativa incorrectamente.
- **Impacto**: Scoring incorrecto de reversals. False positives en detección de sweeps, trades en setups falsos.
- **Fix sugerido**: Validar `bars_since_sweep > 0` explícitamente, no solo `!= 0`.

#### BUG-P1-023: Portfolio manager asume signal.instrument existe
- **Archivo**: `src/core/portfolio_manager.py`
- **Línea**: 192
- **Severidad**: P1-validation
- **Descripción**: `_assert_no_duplicate_directions()` accede `sig.instrument` sin verificar que `sig` sea InstitutionalSignal válido. Si executions contiene None por bug upstream, AttributeError.
- **Impacto**: Crash del portfolio manager durante assertion de invariante. Toda decisión del tick actual se pierde.
- **Fix sugerido**: Validar `for sig in executions: if sig is None: raise ValueError("Invalid signal in executions")`

#### BUG-P1-024: Budget manager división por total sin validación
- **Archivo**: `src/core/budget_manager.py`
- **Líneas**: 210, 219
- **Severidad**: P1-logic
- **Descripción**: `utilization_pct = (committed / total * 100) if total > 0 else 0.0` protege división por 0, pero si total es negativo (por bug en config), el porcentaje es negativo.
- **Impacto**: Utilization reporting incorrecto. Dashboard muestra métricas inconsistentes. No afecta trading directamente pero degrada observability.
- **Fix sugerido**: Validar `total >= 0` en `__init__`, raise ValueError si negativo.

---

### CATEGORÍA 6: PERFORMANCE Y MEMORY LEAKS (3 bugs)

#### BUG-P1-025: Deque pop en loop ineficiente
- **Archivo**: `src/core/decision_ledger.py`
- **Línea**: 57
- **Severidad**: P1-performance
- **Descripción**: `self.decisions.popitem(last=False)` para implementar LRU, pero `OrderedDict.popitem(last=False)` es O(1). No es bug pero usage pattern sugiere code review: se llama en cada write cuando `len > max_size`.
- **Impacto**: Bajo: popitem es eficiente. Sin embargo, `max_size=10000` puede ser insuficiente en producción high-frequency. Memory leak lento si decisiones se toman > 10k/día.
- **Fix sugerido**: Aumentar `max_size` a 100k o implementar periodic persistence + purge.

#### BUG-P1-026: Cache de Hurst sin límite de tamaño
- **Archivo**: `src/core/regime_engine.py`
- **Línea**: 44
- **Severidad**: P1-performance
- **Descripción**: `self.hurst_cache: Dict` sin límite de tamaño. Si se tradean 1000+ símbolos, cache crece indefinidamente.
- **Impacto**: Memory leak lento en sistema multi-instrument. Eventual OOM después de semanas de uptime.
- **Fix sugerido**: Usar LRU cache con maxsize o periodic cleanup de entries con TTL expirado.

#### BUG-P1-027: Decision history sin límite
- **Archivo**: `src/core/conflict_arbiter.py`
- **Línea**: 205
- **Severidad**: P1-performance
- **Descripción**: `self.decision_history: List[ConflictResolution] = []` sin maxlen. Crece sin bound en sistemas long-running.
- **Impacto**: Memory leak proporcional a número de decisiones (miles por día). Eventual slowdown por GC pressure.
- **Fix sugerido**: Cambiar a `deque(maxlen=10000)` o implementar periodic export + clear.

---

## RESUMEN EJECUTIVO

### Total: 27 bugs P1

#### Distribución por impacto:
- **P1-logic** (errores lógicos con impacto económico): 16 bugs
- **P1-performance** (memory leaks, complejidad): 5 bugs
- **P1-concurrency** (race conditions): 3 bugs
- **P1-validation** (validaciones faltantes): 3 bugs

#### Bugs de máxima prioridad (impacto económico directo):
1. **P1-001 a P1-010**: Divisiones por cero en gatekeepers y features (pueden causar decisiones incorrectas)
2. **P1-011**: `add_execution_metadata` inútil (impide TCA y mejora continua)
3. **P1-016**: `vol_realized` NaN propaga a EV calculation (rechazo incorrecto de trades)
4. **P1-021**: Liquidity sweep nunca detecta sweeps (pérdida de alpha)

---

## PLAN DE CORRECCIÓN PROPUESTO

### Bloque 1 (INMEDIATO): Validaciones numéricas en gatekeepers
- **Bugs**: P1-001, P1-002, P1-004
- **Archivos**: `src/gatekeepers/spread_monitor.py`
- **Impacto**: ALTO - Protege contra crashes en gatekeepers críticos

### Bloque 2 (ESTA SEMANA): Validaciones numéricas en features
- **Bugs**: P1-003, P1-005, P1-006, P1-007, P1-008, P1-009
- **Archivos**: `src/features/ofi.py`, `src/features/technical_indicators.py`
- **Impacto**: ALTO - Evita propagación de NaN/Inf a estrategias

### Bloque 3 (ESTA SEMANA): Bugs críticos en decisiones
- **Bugs**: P1-010, P1-011, P1-016, P1-021
- **Archivos**: `src/core/position_sizer.py`, `src/core/decision_ledger.py`, `src/core/conflict_arbiter.py`, `src/strategies/liquidity_sweep.py`
- **Impacto**: MUY ALTO - Impacto directo en sizing, TCA, EV calculation y alpha generation

### Bloque 4 (PRÓXIMA SEMANA): Concurrency y excepciones
- **Bugs**: P1-012, P1-013, P1-014, P1-015
- **Archivos**: `src/core/decision_ledger.py`, `src/core/correlation_tracker.py`, `src/mt5_connector.py`, `src/core/signal_bus.py`
- **Impacto**: MEDIO-ALTO - Estabilidad en producción multi-thread

### Bloque 5 (PRÓXIMA SEMANA): NaN propagation y edge cases
- **Bugs**: P1-017, P1-018, P1-019, P1-020, P1-022, P1-023, P1-024
- **Archivos**: `src/core/regime_engine.py`, `src/gatekeepers/kyles_lambda.py`, `src/features/microstructure.py`, `src/strategies/liquidity_sweep.py`, `src/core/portfolio_manager.py`, `src/core/budget_manager.py`
- **Impacto**: MEDIO - Robustez en edge cases

### Bloque 6 (ESTE MES): Memory leaks y performance
- **Bugs**: P1-025, P1-026, P1-027
- **Archivos**: `src/core/decision_ledger.py`, `src/core/regime_engine.py`, `src/core/conflict_arbiter.py`
- **Impacto**: BAJO-MEDIO - Uptime largo sin degradación

---

## PROCEDIMIENTO DE VALIDACIÓN

Para cada bug corregido:
1. ✅ **Unit test** específico que reproduce el bug
2. ✅ **Regression test** que verifica el fix no rompe funcionalidad existente
3. ✅ **Integration test** en sistema completo con datos históricos
4. ✅ **Code review** peer review del fix
5. ✅ **Documentación** actualizada si afecta API pública

---

## FIRMA Y ACATAMIENTO

Este documento es **VINCULANTE** para el proceso de corrección del ALGORITMO_INSTITUCIONAL_SUBLIMINE.

No se integrará código nuevo (features, estrategias adicionales, refactors) hasta completar la corrección de estos 27 bugs P1.

**Responsable**: Claude (Agente Institucional)
**Fecha límite objetivo**: 2025-11-20 (7 días)
**Tracking**: Via GitHub Issues + PR estructurado por bloque
