# ISSUES CRÍTICOS - ACCIÓN INMEDIATA REQUERIDA

**Fecha**: 2025-11-13  
**Estado**: 12 Issues bloqueantes para producción  
**Autor**: Auditoría automatizada de src/core/

---

## TABLA RESUMEN DE CRÍTICOS

| ID | Archivo | Línea | Problema | Impacto | Esfuerzo |
|----|---------|-------|----------|---------|----------|
| H1.2 | conflict_arbiter.py | 474 | Llamada a método inexistente: `DECISION_LEDGER.generate_decision_uid()` | RuntimeError en ejecución | 1h |
| H1.3 | decision_ledger.py | 92 | Iteración sobre dict keys como if fueran objects | TypeError garantizado | 30m |
| H1.5 | conflict_arbiter.py | 257-289 | Race condition en `intention_locks` sin mutex | Condición carrera en threads | 2h |
| H1.8 | conflict_arbiter.py | 709 | División por cero: `qty_lots / top_of_book_estimate` | Crash si ADV = 0 | 1h |
| H1.6 | conflict_arbiter.py | 782 | Budget check hardcoded al 1% por señal | Sobre-alocación de capital | 2h |
| H2.1 | decision_ledger.py | 92-104 | Iteración sobre OrderedDict claves, no values | TypeError: string indices | 30m |
| H2.2 | decision_ledger.py | 112 | Instancia global sin Lock | Race condition en .write() | 1h |
| H3.1 | portfolio_manager.py | 129 | Llamada a `write()` con payload incorrecto | TypeError en ledger | 1h |
| H4.1 | regime_engine.py | 289-295 | Covariance puede ser NaN | NaN propagation a spreads | 1.5h |
| H1.4 | conflict_arbiter.py | 599 | `max()` sin validar regime_probs vacío | ValueError si empty dict | 30m |
| H1.1 | conflict_arbiter.py | 33-41 | Dependencias circulares | ImportError potencial | 4h (refactor) |
| H1.7 | decision_ledger.py | 92 | Mismo problema que H2.1 | TypeError: string indices | 30m |

---

## DETALLES DE SOLUCIÓN

### H1.2: DECISION_LEDGER.generate_decision_uid() no existe

**Archivo**: `/home/user/TradingSystem/src/core/conflict_arbiter.py:474`

```python
# ACTUAL (FALLA)
uuid5, ulid_id = DECISION_LEDGER.generate_decision_uid(
    batch_id, signal_id, instrument, horizon
)
```

**Solución Option A** - Implementar método en DecisionLedger:
```python
import uuid
import ulid

def generate_decision_uid(self, batch_id: str, signal_id: str, 
                         instrument: str, horizon: str) -> Tuple[str, str]:
    """Genera UUID5 y ULID para decisión idempotente."""
    decision_key = f"{batch_id}:{signal_id}:{instrument}:{horizon}"
    uuid5 = str(uuid.uuid5(uuid.NAMESPACE_DNS, decision_key))
    ulid_id = str(ulid.new())
    return uuid5, ulid_id
```

**Solución Option B** - Cambiar call en conflict_arbiter:
```python
import uuid
import ulid

signal_id = winning_signal.metadata.get('signal_id', winning_signal.strategy_id)
decision_key = f"{batch_id}:{signal_id}:{instrument}:{horizon}"
uuid5 = str(uuid.uuid5(uuid.NAMESPACE_DNS, decision_key))
ulid_id = str(ulid.new())
```

**Recomendación**: Option A (implementar en DecisionLedger)

**Esfuerzo**: 1 hora

---

### H1.3 & H2.1 & H1.7: Iteración incorrecta sobre diccionario

**Archivo**: `/home/user/TradingSystem/src/core/decision_ledger.py:92-104`

```python
# ACTUAL (FALLA)
for decision in self.decisions:  # Itera sobre CLAVES (strings)
    if decision['decision_id'] == decision_id:  # ERROR: decision es string, no dict
        execution_meta = {...}
        decision['execution_metadata'] = execution_meta  # TypeError
        break
```

**Solución**:
```python
# CORRECTO
for decision_uid, decision_record in self.decisions.items():
    # decision_record es el dict guardado
    if decision_uid == decision_id or decision_record.get('decision_id') == decision_id:
        execution_meta = {
            'mid_at_send': mid_at_send,
            'mid_at_fill': mid_at_fill,
            'hold_ms': hold_ms,
            'fill_prob_model_version': fill_prob_model_version,
            'lp_name': lp_name,
            'reject_reason': reject_reason,
            'timestamp_added': datetime.now().isoformat()
        }
        decision_record['execution_metadata'] = execution_meta
        break
```

**Esfuerzo**: 30 minutos

---

### H1.5: Race condition en intention_locks

**Archivo**: `/home/user/TradingSystem/src/core/conflict_arbiter.py:257-289`

```python
# ACTUAL (RACE CONDITION)
if lock_key in self.intention_locks:  # Check sin lock
    existing_lock = self.intention_locks[lock_key]  # Lectura sin sincronización
    age = (now - existing_lock.timestamp).total_seconds()
    if age > self.lock_timeout_seconds:
        del self.intention_locks[lock_key]  # Modificación sin lock
```

**Solución**:
```python
import threading

def __init__(self, ...):
    # ... resto del código ...
    self.intention_locks: Dict[str, IntentionLock] = {}
    self.intention_locks_lock = threading.Lock()  # NUEVO

def acquire_intention_lock(self, instrument: str, horizon: str, batch_id: str) -> bool:
    """Adquiere lock de intención con protección mutex."""
    lock_key = f"{instrument}_{horizon}"
    now = datetime.now()
    
    with self.intention_locks_lock:  # PROTEGIDO
        if lock_key in self.intention_locks:
            existing_lock = self.intention_locks[lock_key]
            age = (now - existing_lock.timestamp).total_seconds()
            
            if age > self.lock_timeout_seconds:
                logger.warning(f"LOCK_TIMEOUT: Liberando {lock_key}")
                del self.intention_locks[lock_key]
            else:
                logger.debug(f"LOCK_CONTENTION: {lock_key}")
                self.stats['race_conditions_prevented'] += 1
                return False
        
        self.intention_locks[lock_key] = IntentionLock(
            instrument=instrument,
            horizon=horizon,
            batch_id=batch_id,
            timestamp=now,
            thread_id=threading.get_ident()
        )
        logger.debug(f"LOCK_ACQUIRED: {lock_key}")
        return True

def release_intention_lock(self, instrument: str, horizon: str, batch_id: str):
    """Libera lock con protección."""
    lock_key = f"{instrument}_{horizon}"
    with self.intention_locks_lock:  # PROTEGIDO
        if lock_key in self.intention_locks:
            lock = self.intention_locks[lock_key]
            if lock.batch_id == batch_id:
                del self.intention_locks[lock_key]
                logger.debug(f"LOCK_RELEASED: {lock_key}")
```

**Esfuerzo**: 2 horas (incluyendo tests)

---

### H1.8: División por cero en slippage

**Archivo**: `/home/user/TradingSystem/src/core/conflict_arbiter.py:709`

```python
# ACTUAL (PUEDE FALLAR)
adv_daily = spec.get('adv_daily_lots', 1000)
top_of_book_estimate = adv_daily * 0.01  # Puede ser 0
size_impact = self.ev_params['slippage_size_factor'] * (qty_lots / top_of_book_estimate)
# Si top_of_book_estimate = 0, ZeroDivisionError
```

**Solución**:
```python
# CORREGIDO
adv_daily = spec.get('adv_daily_lots', 1000)
if adv_daily <= 0:
    adv_daily = 1000  # Default fallback
    
top_of_book_estimate = max(adv_daily * 0.01, 0.1)  # Mínimo 0.1

size_impact = self.ev_params['slippage_size_factor'] * (qty_lots / top_of_book_estimate) if top_of_book_estimate > 0 else 0
```

**Esfuerzo**: 1 hora

---

### H1.6: Budget check hardcoded

**Archivo**: `/home/user/TradingSystem/src/core/conflict_arbiter.py:782`

```python
# ACTUAL (HARDCODED)
def _check_family_budgets(self, signals, instrument):
    for signal in signals:
        family = self._get_strategy_family(signal.strategy_id)
        budget = self.family_budgets.get(family, 0.1)
        current_exposure = self.family_exposure[family]
        
        # PROBLEMA: Asume cada señal = 1%
        new_exposure = current_exposure + 0.01  # HARDCODED 0.01
        
        if new_exposure > budget:
            return False, f"{family} budget exceeded"
    return True, ""
```

**Solución**:
Necesita integración con PositionSizer para obtener tamaño real:

```python
def _check_family_budgets(self, signals, instrument, position_sizer=None):
    """Verifica budgets basado en tamaño real de posición."""
    for signal in signals:
        family = self._get_strategy_family(signal.strategy_id)
        budget = self.family_budgets.get(family, 0.1)
        current_exposure = self.family_exposure[family]
        
        # Obtener tamaño real si position_sizer disponible
        if position_sizer:
            try:
                pos_size = position_sizer.calculate_size(signal, {})
                signal_exposure = pos_size.capital_fraction
            except:
                signal_exposure = 0.01  # Default fallback
        else:
            signal_exposure = 0.01  # Default fallback
        
        new_exposure = current_exposure + signal_exposure
        
        if new_exposure > budget:
            reason = f"{family} budget exceeded: {new_exposure:.2%} > {budget:.2%}"
            logger.warning(f"BUDGET_VIOLATION: {reason}")
            return False, reason
    
    return True, ""
```

**Esfuerzo**: 2 horas (requiere refactorización)

---

### H2.2: DecisionLedger sin sincronización

**Archivo**: `/home/user/TradingSystem/src/core/decision_ledger.py:1-112`

```python
# ACTUAL (SIN LOCK)
from collections import OrderedDict

class DecisionLedger:
    def __init__(self, max_size: int = 10000):
        self.decisions: OrderedDict[str, Dict] = OrderedDict()
        # NO HAY LOCK
```

**Solución**:
```python
# CORREGIDO
import threading
from collections import OrderedDict

class DecisionLedger:
    def __init__(self, max_size: int = 10000):
        self.decisions: OrderedDict[str, Dict] = OrderedDict()
        self.max_size = max_size
        self.lock = threading.Lock()  # NUEVO
        self.stats = {"total_decisions": 0, "duplicates_prevented": 0}
    
    def write(self, decision_uid: str, *args) -> bool:
        """Thread-safe write."""
        if len(args) == 1:
            payload = args[0]
            ulid_temporal = None
        elif len(args) == 2:
            ulid_temporal, payload = args
        else:
            raise TypeError("DecisionLedger.write espera (uid, payload) o (uid, ulid_temporal, payload)")
        
        if not isinstance(payload, dict):
            raise TypeError("payload debe ser dict serializable")
        
        with self.lock:  # PROTEGIDO
            if self.exists(decision_uid):
                logger.warning(f"DUPLICATE_DECISION: {decision_uid}")
                self.stats["duplicates_prevented"] += 1
                return False
            
            record = {
                "timestamp": datetime.now().isoformat(),
                "ulid_temporal": ulid_temporal,
                "payload": payload
            }
            self.decisions[decision_uid] = record
            
            if len(self.decisions) > self.max_size:
                evicted_key = next(iter(self.decisions))
                self.decisions.popitem(last=False)
                logger.info(f"LEDGER_EVICTION: {evicted_key} (size limit reached)")
            
            self.stats["total_decisions"] += 1
            logger.debug(f"LEDGER_WRITE: {decision_uid}")
            return True
```

**Esfuerzo**: 1 hora

---

### H3.1: Llamada a write() con firma incorrecta

**Archivo**: `/home/user/TradingSystem/src/core/portfolio_manager.py:129`

```python
# ACTUAL (PUEDE FALLAR)
self.decision_ledger.write(decision_uuid5, payload)
```

DecisionLedger.write() espera:
- `write(uid, payload)` O
- `write(uid, ulid_temporal, payload)`

Pero aquí se pasa:
- `write(decision_uuid5, payload)` donde payload es dict

**Solución**:
```python
# CORRECTO
ulid_temporal = f"ULID_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}"
self.decision_ledger.write(decision_uuid5, ulid_temporal, payload)
```

**Ubicación a cambiar**: portfolio_manager.py línea 129

**Esfuerzo**: 30 minutos

---

### H4.1: Covariance potencialmente NaN

**Archivo**: `/home/user/TradingSystem/src/core/regime_engine.py:289-295`

```python
# ACTUAL (PUEDE RETORNAR NaN)
log_returns = np.log(close / close.shift(1)).dropna()

if len(log_returns) < 2:
    return 0.0

cov = np.cov(log_returns.iloc[:-1], log_returns.iloc[1:])[0, 1]

if cov < 0:  # NaN < 0 = False, así que entra en else
    spread_pct = 2 * np.sqrt(-cov)
else:
    spread_bp = 2 * log_returns.std() * 10000
```

**Solución**:
```python
# CORREGIDO
def _estimate_effective_spread_roll_log(self, close: pd.Series) -> float:
    """Roll estimator usando Δlog precio (escala-invariante)."""
    try:
        if len(close) < 10:
            return 0.0
        
        # Log-returns en lugar de pct_change
        log_returns = np.log(close / close.shift(1)).dropna()
        
        if len(log_returns) < 2:
            return 0.0
        
        # Covariance de log-returns consecutivos
        cov = np.cov(log_returns.iloc[:-1], log_returns.iloc[1:])[0, 1]
        
        # GUARD contra NaN
        if np.isnan(cov) or np.isinf(cov):
            logger.debug("Roll estimator: NaN/Inf covariance, using std fallback")
            spread_bp = 2 * log_returns.std() * 10000
            return max(0.0, spread_bp)
        
        if cov < 0:
            spread_pct = 2 * np.sqrt(-cov)
            spread_bp = spread_pct * 10000
            return max(0.0, spread_bp)
        else:
            spread_bp = 2 * log_returns.std() * 10000
            return max(0.0, spread_bp)
    
    except Exception as e:
        logger.debug(f"Roll estimator (log) failed: {e}")
        return 0.0
```

**Esfuerzo**: 1.5 horas

---

### H1.4: max() sin validar regime_probs vacío

**Archivo**: `/home/user/TradingSystem/src/core/conflict_arbiter.py:599`

```python
# ACTUAL (PUEDE FALLAR)
regime = max(regime_probs, key=regime_probs.get)
# Si regime_probs = {}, ValueError: max() arg is an empty sequence
```

**Solución**:
```python
# CORREGIDO
if not regime_probs:
    logger.warning("regime_probs vacío, usando default")
    regime_probs = {'trend': 0.33, 'range': 0.33, 'shock': 0.33}

regime = max(regime_probs, key=regime_probs.get)
```

**Esfuerzo**: 30 minutos

---

### H1.1: Dependencias circulares

**Archivo**: `/home/user/TradingSystem/src/core/` (múltiples)

Este es el más difícil de resolver. Requiere refactorización arquitectónica.

**Análisis de ciclos**:
```
conflict_arbiter.py
  ├─ importa signal_schema
  ├─ importa regime_engine
  ├─ importa position_sizer
  │   └─ importa signal_schema (OK, ya importada)
  ├─ importa correlation_tracker
  └─ importa decision_ledger

portfolio_manager.py
  ├─ importa conflict_arbiter (AQUÍ)
  ├─ importa signal_bus
  │   ├─ importa signal_schema
  │   └─ importa conflict_arbiter (CICLO)
  └─ ...
```

**Solución** (Option A): Mover InstitutionalSignal a módulo separado
```
core/
  ├─ signal_schema.py (SOLO dataclass)
  ├─ signal_base.py (Nuevo - interfaces)
  ├─ conflict_arbiter.py
  └─ ...
```

**Solución** (Option B): Usar TYPE_CHECKING
```python
from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from core.position_sizer import PositionSize
```

**Recomendación**: Option B + refactor gradual

**Esfuerzo**: 4 horas

---

## TABLA DE PRIORIZACIÓN

| Prioridad | ID | Problema | Riesgo | Esfuerzo | Combinado |
|-----------|-----|----------|--------|----------|-----------|
| 🔴 BLOCKER | H1.2 | generate_decision_uid() no existe | CRASH | 1h | 1h |
| 🔴 BLOCKER | H1.3/H2.1 | Iteración dict incorrecto | CRASH | 1h | 1h |
| 🔴 BLOCKER | H1.5 | Race condition locks | FINANCIAL | 2h | 2h |
| 🔴 BLOCKER | H1.8 | División por cero | CRASH | 1h | 1h |
| 🔴 BLOCKER | H3.1 | write() firma incorrecta | CRASH | 0.5h | 0.5h |
| 🟠 HIGH | H1.6 | Budget hardcoded | FINANCIAL | 2h | 2h |
| 🟠 HIGH | H2.2 | DecisionLedger sin sync | RACE | 1h | 1h |
| 🟠 HIGH | H4.1 | Covariance NaN | LOGIC | 1.5h | 1.5h |
| 🟡 MEDIUM | H1.4 | max() sin guard | CRASH | 0.5h | 0.5h |
| 🟡 MEDIUM | H1.1 | Circular imports | ARCH | 4h | 4h |
| 🟢 LOW | Otros | Config/Docs | QUALITY | 1h cada | - |

**Total de esfuerzo para BLOCKER + HIGH**: ~16.5 horas

---

## NEXT STEPS

1. **Hoy**: Fijar H1.2, H1.3/H2.1, H3.1 (3 horas)
2. **Mañana**: H1.5, H1.8, H1.6 (5 horas) 
3. **Esta semana**: H2.2, H4.1, H1.4 (4.5 horas)
4. **Próxima semana**: H1.1 (refactor) (4 horas)

---

**Documento generado**: 2025-11-13  
**Auditor**: Sistema automático  
**Status**: REQUIERE ACCIÓN INMEDIATA
