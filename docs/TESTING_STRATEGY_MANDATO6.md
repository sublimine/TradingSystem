# ESTRATEGIA DE TESTING - MANDATO 6

**Proyecto**: SUBLIMINE TradingSystem
**Fecha**: 2025-11-13
**Objetivo**: Testing institucional mínimo para cierre de P0

---

## ALCANCE INICIAL

Testing strategy para resolver:
- **P0-001**: Sistema sin tests institucionales
- **P0-002**: Infraestructura sin cobertura mínima

**Cobertura objetivo inicial**: 60-70% en módulos críticos

---

## TIPOS DE TESTS

### 1. Unit Tests

**Objetivo**: Validar componentes individuales en aislamiento

**Módulos críticos con tests**:
- `tests/core/test_decision_ledger.py`: Idempotencia, LRU eviction, thread-safety
- `tests/core/test_conflict_arbiter.py`: Resolución de conflictos, quality thresholds
- `tests/risk/test_risk_manager.py`: Quality scoring, exposure limits, circuit breakers

**Criterios de aceptación**:
- Todos los tests unitarios deben pasar antes de merge
- Coverage mínimo 60% en `src/core/` y `src/risk/`
- Tests deben ejecutarse en <5 segundos

### 2. Integration Tests

**Objetivo**: Validar flujo completo end-to-end

**Pipeline crítico**:
```
Señal → QualityScorer → ConflictArbiter → RiskManager → DecisionLedger
```

**Tests de integración**:
- Pipeline completo con señal válida (debe ejecutarse)
- Pipeline con señal de baja calidad (debe rechazarse)
- Pipeline con exposure limit excedido (debe rechazarse)
- Pipeline con circuit breaker activo (debe bloquearse)

**Ubicación**: `tests/integration/` (pendiente implementación)

### 3. Regression Tests

**Objetivo**: Prevenir reintroducción de bugs corregidos

**Cobertura**:
- Bugs P0 de Mandato 1-4 corregidos
- Cada fix debe venir con regression test que falla sin el fix

**Ejecución**: En CI/CD antes de merge a troncal

---

## ESTRUCTURA DE TESTS

```
tests/
├── __init__.py
├── conftest.py              # Fixtures compartidos
├── core/
│   ├── __init__.py
│   ├── test_decision_ledger.py
│   ├── test_conflict_arbiter.py
│   └── test_brain.py        # Pendiente
├── risk/
│   ├── __init__.py
│   ├── test_risk_manager.py
│   └── test_exposure.py     # Pendiente
├── strategies/
│   ├── __init__.py
│   └── test_strategy_*.py   # Pendiente
└── integration/
    ├── __init__.py
    └── test_pipeline.py     # Pendiente
```

---

## EJECUCIÓN DE TESTS

### Comando único

```bash
# Ejecutar todos los tests
pytest tests/ -v

# Ejecutar solo tests críticos (core + risk)
pytest tests/core/ tests/risk/ -v

# Ejecutar con coverage
pytest tests/ --cov=src/core --cov=src/risk --cov-report=term-missing
```

### CI/CD Integration

**Pre-merge checks** (obligatorio):
1. Todos los tests unitarios verdes
2. Coverage >= 60% en módulos críticos
3. Sin warnings críticos de pytest

**Post-merge monitoring**:
- Regression tests nightly
- Performance tests semanales

---

## FIXTURES Y MOCKS

### Fixtures compartidos (`conftest.py`)

```python
@pytest.fixture
def mock_signal_high_quality():
    """Señal de alta calidad para tests."""
    return {
        'symbol': 'EURUSD.pro',
        'direction': 'LONG',
        'quality_score': 0.85,
        'metadata': {
            'mtf_confluence': 0.90,
            'structure_alignment': 0.80,
            'regime_confidence': 0.85
        }
    }

@pytest.fixture
def mock_market_context():
    """Contexto de mercado típico."""
    return {
        'vpin': 0.30,
        'volatility_regime': 'NORMAL',
        'strategy_performance': {}
    }
```

### Mocking de componentes externos

- `RegimeEngine`: Mock para control de régimen
- `CorrelationTracker`: Mock para correlaciones fijas
- `MT5Connector`: Mock para no conectar a broker en tests

---

## COVERAGE TARGETS

| Módulo | Coverage Target | Prioridad |
|--------|-----------------|-----------|
| `src/core/decision_ledger.py` | 80% | Alta |
| `src/core/conflict_arbiter.py` | 70% | Alta |
| `src/core/risk_manager.py` | 75% | Alta |
| `src/core/brain.py` | 60% | Media |
| `src/strategies/*.py` | 50% | Media |

**Coverage global inicial**: 60-70% (target Mandato 6)

---

## EXPANSIÓN FUTURA

### Fase 2 (Post-Mandato 6):
- Integration tests completos
- Performance tests (latencia, throughput)
- Load tests (1000+ señales/segundo)
- Chaos engineering (fallas simuladas)

### Fase 3 (Pre-Producción):
- End-to-end tests con datos históricos reales
- Backtesting automático en CI/CD
- Shadow mode testing (producción simulada)

---

## REGLAS DE MERGE

**Bloqueantes**:
- Tests unitarios fallando → **NO MERGE**
- Coverage < 60% en módulos tocados → **NO MERGE**
- Tests skipped sin justificación → **NO MERGE**

**Warnings**:
- Coverage 60-70% → Warning, merge permitido
- Tests lentos (>10s) → Optimizar en próximo PR

---

**Documento vivo**: Actualizar conforme se expanda cobertura
