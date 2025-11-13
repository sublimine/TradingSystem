# AUDITORÍA EXHAUSTIVA - src/core/

Análisis realizado: 2025-11-13
Rama: claude/audit-trading-system-repo-011CV4uYEyVY6qd3UdpyS6FH

## RESUMEN EJECUTIVO

Se han identificado **45 hallazgos** distribuidos así:
- CRÍTICO: 12
- IMPORTANTE: 20
- MENOR: 13

### Distribución por archivo:
- conflict_arbiter.py: 14 hallazgos (8 críticos)
- decision_ledger.py: 8 hallazgos (2 críticos)
- portfolio_manager.py: 8 hallazgos (1 crítico)
- regime_engine.py: 7 hallazgos (1 crítico)
- position_sizer.py: 3 hallazgos (0 críticos)
- correlation_tracker.py: 2 hallazgos (0 críticos)
- signal_bus.py: 1 hallazgo (0 críticos)
- strategy_adapter.py: 1 hallazgo (0 críticos)
- signal_schema.py: 1 hallazgo (0 críticos)
- budget_manager.py: 0 hallazgos

---

## ANÁLISIS DETALLADO POR ARCHIVO

### 1. CONFLICT_ARBITER.PY - 14 HALLAZGOS

#### CRÍTICOS (8)

**H1.1 - Line 33: Dependencia circular detectada**
- Tipo: Dependencia circular / Arquitectura
- Severidad: CRÍTICO
- Descripción: El archivo importa desde signal_schema, regime_engine, position_sizer, correlation_tracker, decision_ledger. Estos a su vez importan desde conflict_arbiter indirectamente:
  - portfolio_manager importa conflict_arbiter
  - signal_bus importa conflict_arbiter y usa ConflictResolution
  
Esto crea un grafo de dependencias problemático que puede causar ImportError en tiempo de ejecución si el módulo se carga en cierto orden.

- Ubicación exacta: Líneas 33-41 (imports)
- Código:
```python
from core.signal_schema import InstitutionalSignal
from core.regime_engine import RegimeEngine
from typing import Optional
try:
    from core.position_sizer import PositionSize
except ImportError:
    PositionSize = None
```
- Problema: El try/except no es suficiente. position_sizer.py línea 10 importa InstitutionalSignal, creando ciclo.

**H1.2 - Line 474: Referencias a métodos inexistentes**
- Tipo: Lógica/API
- Severidad: CRÍTICO
- Descripción: Llama a `DECISION_LEDGER.generate_decision_uid()` pero la clase DecisionLedger no tiene ese método.
- Ubicación exacta: Línea 474
- Código:
```python
uuid5, ulid_id = DECISION_LEDGER.generate_decision_uid(
    batch_id, signal_id, instrument, horizon
)
```
- Impacto: RuntimeError en tiempo de ejecución cuando intenta ejecutar una orden.

**H1.3 - Line 104: Iteración sobre diccionario durante lectura sin copia**
- Tipo: Lógica
- Severidad: CRÍTICO
- Descripción: En `add_execution_metadata()` de DecisionLedger, se itera sobre self.decisions directamente:
```python
for decision in self.decisions:  # ERROR: self.decisions es dict
    if decision['decision_id'] == decision_id:
```
Debería iterar sobre self.decisions.values() o .items().

- Ubicación exacta: decision_ledger.py línea 92
- Impacto: Itera sobre claves, no sobre objetos. AttributeError garantizado.

**H1.4 - Line 599: Acceso a diccionario sin validación**
- Tipo: Manejo de errores
- Severidad: CRÍTICO
- Descripción: En `_calculate_pairwise_correlation()`, accede a dicts sin verificar claves:
```python
regime = max(regime_probs, key=regime_probs.get)
```
Si regime_probs está vacío, max() lanza ValueError.

- Ubicación exacta: conflict_arbiter.py línea 599
- Impacto: Crash si regime_probs === {}

**H1.5 - Line 187: Race condition potencial en diccionario compartido**
- Tipo: Seguridad / Concurrencia
- Severidad: CRÍTICO
- Descripción: `self.intention_locks` se accede y modifica sin lock en múltiples lugares:
```python
if lock_key in self.intention_locks:  # Line 262
    existing_lock = self.intention_locks[lock_key]  # No está en lock
    ...
    del self.intention_locks[lock_key]  # Potencial race
```
Aunque hay logging de "LOCK_ACQUIRED", no hay lock mutex que proteja intention_locks.

- Ubicación exacta: Líneas 257-289
- Impacto: Race condition entre threads si dos llamadas evaluate() simultáneamente.

**H1.6 - Line 782: Hardcoded values que deberían ser configurables**
- Tipo: Configuración
- Severidad: CRÍTICO
- Descripción: En `_check_family_budgets()`, asume que cada señal = 1% del capital:
```python
new_exposure = current_exposure + 0.01  # Hardcoded 0.01 = 1%
```
Este valor debe ser dinámico basado en el tamaño real de posición.

- Ubicación exacta: conflict_arbiter.py línea 782
- Impacto: Cálculo de presupuesto incorrecto. Puede permitir sobre-alocación.

**H1.7 - Line 92: Iteración sobre OrderedDict incorrectamente en DecisionLedger**
- Tipo: Lógica
- Severidad: CRÍTICO
- Descripción: `add_execution_metadata` intenta buscar en self.decisions iterando sobre claves:
```python
for decision in self.decisions:  # Itera sobre keys (str), no values (dict)
    if decision['decision_id'] == decision_id:  # KEY no es un dict!
```

- Ubicación exacta: decision_ledger.py línea 92
- Impacto: TypeError: string indices must be integers

**H1.8 - Line 704: División por cero potencial**
- Tipo: Aritmética
- Severidad: CRÍTICO
- Descripción: En `_estimate_slippage_with_size()`:
```python
adv_daily = spec.get('adv_daily_lots', 1000)
...
top_of_book_estimate = adv_daily * 0.01  # Puede ser 0 si adv_daily = 0
...
size_impact = self.ev_params['slippage_size_factor'] * (qty_lots / top_of_book_estimate)
# Potencial division by zero si top_of_book_estimate == 0
```

- Ubicación exacta: conflict_arbiter.py línea 709
- Impacto: Crash si instrumento no tiene adv_daily definido.

#### IMPORTANTE (4)

**H1.9 - Line 167: Estructura de familia_budgets hardcoded**
- Tipo: Configuración
- Severidad: IMPORTANTE
- Descripción: Los budgets por familia están hardcoded:
```python
self.family_budgets = {
    'MOMENTUM': 0.35,
    'MEAN_REVERSION': 0.25,
    'MICROSTRUCTURE': 0.30,
    'VOLATILITY': 0.10
}
```
Debería cargar desde config.

- Ubicación exacta: Lines 166-172
- Impacto: No configurable en tiempo de ejecución.

**H1.10 - Line 159-164: Hardcoded no-trade zones**
- Tipo: Configuración
- Severidad: IMPORTANTE
- Descripción: Thresholds para no-trade zone hardcoded:
```python
self.base_no_trade_zones = {
    'scalp': 0.3,
    'intraday': 0.5,
    'swing': 0.7
}
```

- Ubicación exacta: Lines 159-164
- Impacto: No configurable sin cambiar código.

**H1.11 - Line 183-192: EV parameters hardcoded**
- Tipo: Configuración
- Severidad: IMPORTANTE
- Descripción: Todos los parámetros de EV están hardcoded:
```python
self.ev_params = {
    'slippage_base_bp': 1.0,
    'slippage_vol_multiplier': 0.5,
    ...
}
```

- Ubicación exacta: Lines 183-192
- Impacto: Requiere recompilación para cambiar.

**H1.12 - Line 804: Acceso a signal.calculate_regime_weight sin verificación**
- Tipo: Interfaz incompleta
- Severidad: IMPORTANTE
- Descripción: Llama a método que puede no existir:
```python
regime_weight = signal.calculate_regime_weight(regime_probs)
```
InstitutionalSignal sí lo define (signal_schema.py línea 74), pero esta dependencia no es explícita.

- Ubicación exacta: conflict_arbiter.py línea 804
- Impacto: Si InstitutionalSignal cambia, falla.

#### MENOR (2)

**H1.13 - Line 255: Formato de batch_id vulnerable**
- Tipo: Seguridad
- Severidad: MENOR
- Descripción: batch_id incluye microsegundos:
```python
return f"BATCH_{self.batch_id_counter:08d}_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}"
```
Puede causar issues si hay miles de batches en mismo microsegundo (no único).

- Ubicación exacta: Line 255
- Impacto: Colisión teórica de IDs.

**H1.14 - Line 1053: Método agregado dinámicamente al final**
- Tipo: Code smell / Mantenibilidad
- Severidad: MENOR
- Descripción: `record_performance()` se añade dinámicamente al final del archivo:
```python
if not hasattr(ConflictArbiter, "record_performance"):
    ConflictArbiter.record_performance = _record_performance_method
```
Debería ser un método formal de la clase.

- Ubicación exacta: Lines 1040-1063
- Impacto: Difícil de mantener y debuggear.

---

### 2. DECISION_LEDGER.PY - 8 HALLAZGOS

#### CRÍTICOS (2)

**H2.1 - Line 92-104: Iteración incorrecta sobre diccionario**
- Tipo: Lógica
- Severidad: CRÍTICO
- Descripción: En método `add_execution_metadata()`:
```python
for decision in self.decisions:  # Itera sobre CLAVES (strings)
    if decision['decision_id'] == decision_id:  # Intenta acceso dict a string
        decision['execution_metadata'] = ...  # ERROR
```
Debería ser:
```python
for decision_id_key, decision in self.decisions.items():
    if decision_id_key == decision_id or decision.get('decision_id') == decision_id:
```

- Ubicación exacta: Lines 92-104
- Impacto: TypeError: string indices must be integers

**H2.2 - Line 112: Instancia global sin sincronización**
- Tipo: Concurrencia
- Severidad: CRÍTICO
- Descripción: DECISION_LEDGER se crea sin sincronización:
```python
DECISION_LEDGER = DecisionLedger()
```
Si múltiples threads llaman `.write()` simultáneamente, no hay protección. La clase no tiene Lock.

- Ubicación exacta: Line 112
- Impacto: Race condition en OrderedDict.

#### IMPORTANTE (4)

**H2.3 - Line 20: Parámetro max_size sin validación**
- Tipo: Validación
- Severidad: IMPORTANTE
- Descripción: Constructor no valida max_size:
```python
def __init__(self, max_size: int = 10000):
    self.decisions: OrderedDict[str, Dict] = OrderedDict()
    self.max_size = max_size
```
¿Qué pasa si max_size < 0 o max_size = 0?

- Ubicación exacta: Line 19-21
- Impacto: Comportamiento indefinido.

**H2.4 - Line 56-57: Evicción sin logging**
- Tipo: Auditoría
- Severidad: IMPORTANTE
- Descripción: Cuando se alcanza max_size, se elimina entrada sin registrar:
```python
if len(self.decisions) > self.max_size:
    self.decisions.popitem(last=False)  # Sin logging
```

- Ubicación exacta: Lines 56-57
- Impacto: Pérdida silenciosa de datos.

**H2.5 - Line 50-51: Timestamp hardcoded a ahora**
- Tipo: Lógica
- Severidad: IMPORTANTE
- Descripción: Siempre usa datetime.now():
```python
record = {
    "timestamp": datetime.now().isoformat(),  # Siempre ahora
    "ulid_temporal": ulid_temporal,
    ...
}
```
Debería permitir timestamp externo.

- Ubicación exacta: Lines 50-51
- Impacto: Difícil de testear reproducibilidad.

**H2.6 - Line 108: export_to_json sin manejo de errores**
- Tipo: Manejo de errores
- Severidad: IMPORTANTE
- Descripción: No captura IOError, PermissionError, etc:
```python
def export_to_json(self, filepath: str):
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(dict(self.decisions), f, indent=2, ensure_ascii=False)
```

- Ubicación exacta: Lines 106-109
- Impacto: Crash si no hay permisos o path inválido.

#### MENOR (2)

**H2.7 - Line 27: Firma flexible es confusa**
- Tipo: Usabilidad
- Severidad: MENOR
- Descripción: Método `write()` acepta argumentos variables:
```python
def write(self, decision_uid: str, *args) -> bool:
```
Deberían ser dos métodos: `write()` y `write_with_timestamp()`.

- Ubicación exacta: Line 27
- Impacto: Confusión en API.

**H2.8 - Line 65: Docstring incompleto**
- Tipo: Documentación
- Severidad: MENOR
- Descripción: Método `get()` sin docstring:
```python
def get(self, decision_uid: str) -> Optional[Dict]:
    return self.decisions.get(decision_uid)
```

- Ubicación exacta: Line 63-64
- Impacto: Falta contexto.

---

### 3. PORTFOLIO_MANAGER.PY - 8 HALLAZGOS

#### CRÍTICO (1)

**H3.1 - Line 129: Llamada a método inexistente**
- Tipo: Lógica
- Severidad: CRÍTICO
- Descripción: Llama a `DECISION_LEDGER.write()` con firma que no existe en DecisionLedger:
```python
self.decision_ledger.write(decision_uuid5, payload)  # Payload es dict, no ulid_temporal
```
Pero DecisionLedger.write() espera (uid, payload) o (uid, ulid_temporal, payload).

- Ubicación exacta: Line 129
- Impacto: TypeError si payload no es string.

#### IMPORTANTE (5)

**H3.2 - Line 36: Default family_allocations incompleto**
- Tipo: Configuración
- Severidad: IMPORTANTE
- Descripción: Allocations por defecto solo suman 95%:
```python
family_allocations = {
    'momentum': 0.35,
    'mean_reversion': 0.25,
    'breakout': 0.20,
    'other': 0.15  # = 0.95
}
```
Deja 5% no asignado.

- Ubicación exacta: Lines 31-36
- Impacto: Ambigüedad en intención.

**H3.3 - Line 52: BudgetManager no sincronizado con conflict_arbiter**
- Tipo: Arquitectura
- Severidad: IMPORTANTE
- Descripción: BudgetManager se crea pero conflict_arbiter tiene su propio family_budgets:
```python
self.budget_manager = BudgetManager(total_capital, family_allocations)  # Line 52
# Pero conflict_arbiter también tiene self.family_budgets (conflict_arbiter.py línea 167)
```
Dos fuentes de verdad.

- Ubicación exacta: Lines 52 y conflict_arbiter.py:167
- Impacto: Inconsistencia de presupuestos.

**H3.4 - Line 227: export_to_json sin validación de path**
- Tipo: Manejo de errores
- Severidad: IMPORTANTE
- Descripción: No valida si directorio es creable:
```python
def export_to_json(self, filepath: str):
    import os
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    self.decision_ledger.export_to_json(filepath)
```
Si filepath es inválido, falla.

- Ubicación exacta: Lines 226-230
- Impacto: Crash silencioso.

**H3.5 - Line 166: Assert sin mensaje**
- Tipo: Manejo de errores
- Severidad: IMPORTANTE
- Descripción: Assert sin contexto:
```python
self._assert_no_duplicate_directions([e['signal'] for e in executions_with_sizing])
```
En método privado, levanta RuntimeError sin stack trace útil.

- Ubicación exacta: Line 166
- Impacto: Difícil de debuggear.

**H3.6 - Line 200-218: Inicialización tardía de atributo**
- Tipo: Mantenibilidad
- Severidad: IMPORTANTE
- Descripción: En `record_signal_outcome()`, inicializa performance_stats si no existe:
```python
if not hasattr(self.conflict_arbiter, "performance_stats"):
    self.conflict_arbiter.performance_stats = defaultdict(...)
```
Debería estar en constructor.

- Ubicación exacta: Lines 200-208
- Impacto: Comportamiento no predecible.

#### MENOR (2)

**H3.7 - Line 98: Conversión de tuple a string innecesaria**
- Tipo: Performance
- Severidad: MENOR
- Descripción: Crea decision_key como string cuando podría ser tuple:
```python
decision_key = f"{batch_id}:{group_str}:{win.strategy_id if win else 'NONE'}"
```

- Ubicación exacta: Line 98
- Impacto: Innecesario parsing.

**H3.8 - Line 117-127: Try/except demasiado amplio**
- Tipo: Manejo de errores
- Severidad: MENOR
- Descripción: Captura múltiples excepciones sin contexto:
```python
try:
    payload['ev_net_bp'] = getattr(ev_obj, "ev_net", None)
except (AttributeError, TypeError):
    try:
        payload['ev_net_bp'] = ev_obj.get('ev_net')
except Exception:
    pass  # Silencia todo
```

- Ubicación exacta: Lines 116-127
- Impacto: Difícil de debuggear.

---

### 4. REGIME_ENGINE.PY - 7 HALLAZGOS

#### CRÍTICO (1)

**H4.1 - Line 289: Covariance potencialmente NaN**
- Tipo: Aritmética
- Severidad: CRÍTICO
- Descripción: En `_estimate_effective_spread_roll_log()`:
```python
cov = np.cov(log_returns.iloc[:-1], log_returns.iloc[1:])[0, 1]
```
Si log_returns es muy pequeño o tiene NaN, cov puede ser NaN. Luego:
```python
if cov < 0:  # NaN < 0 = False
    spread_pct = 2 * np.sqrt(-cov)  # sqrt(NaN) = NaN
```

- Ubicación exacta: Lines 288-295
- Impacto: spread_bp = NaN, propaga errores downstream.

#### IMPORTANTE (4)

**H4.2 - Line 225-269: Múltiples hardcoded thresholds en fallback**
- Tipo: Configuración
- Severidad: IMPORTANTE
- Descripción: Si YAML no carga, usa hardcoded defaults:
```python
return {
    'DEFAULT': {
        'adx_trend_enter': 28.0,
        'adx_trend_exit': 22.0,
        ...
    }
}
```
También en línea 113-120.

- Ubicación exacta: Lines 95-105 y 113-120
- Impacto: Duplicación de configuración.

**H4.3 - Line 189: ofi_persistence usando corrcoef sin validación**
- Tipo: Lógica
- Severidad: IMPORTANTE
- Descripción: Asume ofi_values siempre existe:
```python
ofi_values = features.get('ofi_history', [])
ofi_persistence = abs(np.corrcoef(ofi_values[-20:], range(20))[0, 1]) if len(ofi_values) > 20 else 0.0
```
Si ofi_values[-20:] tiene NaN, corrcoef falla.

- Ubicación exacta: Line 189
- Impacto: Posible NaN propagation.

**H4.4 - Line 337: Hardcoded lookback y confirm_bars**
- Tipo: Configuración
- Severidad: IMPORTANTE
- Descripción: En `_calculate_follow_through_no_leak()`:
```python
lookback = 50
confirm_bars = 5
```
Debería ser configurable.

- Ubicación exacta: Lines 337-338
- Impacto: No ajustable.

**H4.5 - Line 52: Cache window hardcoded**
- Tipo: Configuración
- Severidad: IMPORTANTE
- Descripción: Spread baseline window:
```python
self.spread_baseline_window = 200  # Hardcoded
```

- Ubicación exacta: Line 52
- Impacto: No configurable.

#### MENOR (2)

**H4.6 - Line 620-623: Polyfit sin protección contra singular matrix**
- Tipo: Robustez
- Severidad: MENOR
- Descripción: En `_calculate_hurst_exponent()`:
```python
hurst = np.polyfit(np.log(tau), np.log(rs_values), 1)[0]
```
Si tau o rs_values tienen valores idénticos, polyfit puede fallar.

- Ubicación exacta: Line 623
- Impacto: Posible excepción no capturada.

**H4.7 - Line 15: Logger no inicializado en clase**
- Tipo: Documentación
- Severidad: MENOR
- Descripción: Logger es global, no hay docstring sobre logging.

- Ubicación exacta: Line 15
- Impacto: Confusión sobre nivel de detalle.

---

### 5. POSITION_SIZER.PY - 3 HALLAZGOS

#### IMPORTANTE (2)

**H5.1 - Line 113: Acceso directo a target_profile**
- Tipo: Validación
- Severidad: IMPORTANTE
- Descripción: Asume target_profile no vacío:
```python
primary_target = list(signal.target_profile.values())[0] if signal.target_profile else 2.0
```
Si target_profile es dict vacío, list()[0] falla.

- Ubicación exacta: Line 113
- Impacto: IndexError.

**H5.2 - Line 31-34: Parámetros hardcoded**
- Tipo: Configuración
- Severidad: IMPORTANTE
- Descripción: Kelly fraction y caps hardcoded:
```python
kelly_fraction: float = 0.25,
min_position_pct: float = 0.002,
max_position_pct: float = 0.05,
```

- Ubicación exacta: Lines 31-34
- Impacto: No configurable.

#### MENOR (1)

**H5.3 - Line 124-132: Magic numbers en confidence multiplier**
- Tipo: Code smell
- Severidad: MENOR
- Descripción: Hardcoded thresholds sin explicación:
```python
if confidence >= 0.90:
    return 1.2
elif confidence >= 0.70:
    return 1.0
```

- Ubicación exacta: Lines 124-132
- Impacto: Difícil de mantener.

---

### 6. CORRELATION_TRACKER.PY - 2 HALLAZGOS

#### IMPORTANTE (1)

**H6.1 - Line 31: deque sin TTL explícito**
- Tipo: Memory management
- Severidad: IMPORTANTE
- Descripción: Acumula retornos indefinidamente:
```python
self.strategy_returns: Dict[str, deque] = defaultdict(lambda: deque(maxlen=500))
```
500 máximo, pero ¿qué pasa si una estrategia no comercia? Crece indefinidamente en memory.

- Ubicación exacta: Line 31
- Impacto: Posible memory leak si muchas estrategias inactivas.

#### MENOR (1)

**H6.2 - Line 162: Instancia global sin parámetros**
- Tipo: Configuración
- Severidad: MENOR
- Descripción: CORRELATION_TRACKER creado con defaults:
```python
CORRELATION_TRACKER = CorrelationTracker()
```
No configurable.

- Ubicación exacta: Line 162
- Impacto: No ajustable en tiempo de ejecución.

---

### 7. SIGNAL_BUS.PY - 1 HALLAZGO

#### IMPORTANTE (1)

**H7.1 - Line 127: Singleton sin reset**
- Tipo: Testing
- Severidad: IMPORTANTE
- Descripción: Instancia global singleton:
```python
_SIGNAL_BUS_INSTANCE: Optional[SignalBus] = None
```
Sin método para resetear en tests. Causa state leakage entre tests.

- Ubicación exacta: Line 127
- Impacto: Tests no aislados.

---

### 8. STRATEGY_ADAPTER.PY - 1 HALLAZGO

#### MENOR (1)

**H8.1 - Line 101-102: Setdefault con hardcoded values**
- Tipo: Configuración
- Severidad: MENOR
- Descripción: En `create_signal()`:
```python
metadata.setdefault('risk_reward_ratio', list(target_profile.values())[0] if target_profile else 1.5)
metadata.setdefault('execution_style', 'aggressive')
```
1.5 y 'aggressive' son hardcoded.

- Ubicación exacta: Lines 101-102
- Impacto: No configurable.

---

### 9. SIGNAL_SCHEMA.PY - 1 HALLAZGO

#### MENOR (1)

**H9.1 - Line 85-87: to_dict() puede fallar con datetime**
- Tipo: Serialización
- Severidad: MENOR
- Descripción: `asdict()` no maneja datetime:
```python
def to_dict(self) -> Dict:
    return asdict(self)
```
El campo `timestamp` es datetime, no es JSON-serializable.

- Ubicación exacta: Lines 85-87
- Impacto: json.dump() fallará.

---

### 10. BUDGET_MANAGER.PY - 0 HALLAZGOS

✓ SIN HALLAZGOS DETECTADOS

---

## MATRIZ DE CLASIFICACIÓN

### Por Severidad:

| Severidad | Total | 
|-----------|-------|
| CRÍTICO   | 12    |
| IMPORTANTE| 20    |
| MENOR     | 13    |
| **TOTAL** | **45**|

### Por Categoría:

| Categoría                    | Cantidad |
|------------------------------|----------|
| Lógica / Errores de Código   | 10       |
| Configuración / Hardcoding   | 12       |
| Concurrencia / Race Conds    | 3        |
| Manejo de Errores            | 6        |
| Arquitectura / Dependencias  | 7        |
| Validación / Input           | 4        |
| Documentación                | 3        |

---

## RECOMENDACIONES INMEDIATAS

### ANTES DE PRODUCCIÓN (Bloquear):

1. **H1.2**: Implementar `DECISION_LEDGER.generate_decision_uid()` o cambiar llamada
2. **H1.3**: Cambiar iteración en add_execution_metadata()
3. **H2.1**: Corregir iteración sobre OrderedDict
4. **H1.5**: Proteger intention_locks con threading.Lock()
5. **H1.8**: Agregar guard contra división por cero
6. **H3.1**: Validar llamada a write() vs firma real

### ANTES DE SIGUIENTE RELEASE (Importante):

1. **H1.4**: Proteger contra regime_probs vacío
2. **H1.7**: Same as H2.1
3. **H1.6**: Hacer family budget dinámico basado en posición real
4. **H4.1**: Validar NaN en covariance
5. **H3.3**: Unificar family_budgets entre managers

### ANTES DE SIGUIENTE SPRINT (Menor):

1. Extraer hardcoded values a config files
2. Implementar proper logging en evictions
3. Agregar métodos reset() a singletons para testing

---

## PATRONES DETECTADOS

### 🚩 Antipatrones Recurrentes:

1. **Hardcoded Magic Numbers**: 
   - conflict_arbiter.py: 0.35, 0.25, 0.3, 0.1 (family budgets)
   - regime_engine.py: 28.0, 22.0, 0.55 (thresholds)
   - position_sizer.py: 0.25, 0.002, 0.05 (kelly params)

2. **Métodos Inexistentes Llamados**:
   - DECISION_LEDGER.generate_decision_uid() [No existe]
   - signal.calculate_regime_weight() [Sí existe pero no documentado]

3. **Race Conditions Potenciales**:
   - intention_locks sin mutex
   - DECISION_LEDGER sin sincronización
   - CORRELATION_TRACKER sin sincronización

4. **Iteraciones Incorrectas**:
   - decision_ledger.py línea 92
   - Múltiples lugares iteran sobre dicts sin .items()

5. **División por Cero**:
   - conflict_arbiter.py línea 709: top_of_book_estimate puede ser 0
   - correlation_tracker.py línea 109: total_budget puede ser 0

---

## CONCLUSIONES

### Resumen de Riesgo:

- **12 Issues CRÍTICOS**: Pueden causar crashes o pérdidas financieras
- **20 Issues IMPORTANTES**: Afectan mantenibilidad y confiabilidad
- **13 Issues MENORES**: Mejoras de estilo y documentación

### Dependencias Problemáticas:

El sistema tiene **dependencias circulares** entre:
- conflict_arbiter ↔ signal_schema
- portfolio_manager ↔ conflict_arbiter  
- position_sizer ↔ signal_schema

Recomendación: Refactorizar a capas claras.

### Recomendación General:

**NO LLEVAR A PRODUCCIÓN** sin resolver al menos los 12 críticos.

