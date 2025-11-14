# BRAIN-LAYER INSTITUCIONAL - DISEÑO FORMAL
**MANDATO 14 - SUBLIMINE TradingSystem**

**Fecha:** 2025-11-14
**Versión:** 1.0
**Estado:** IMPLEMENTACIÓN

---

## 1. ROL Y ALCANCE DEL BRAIN-LAYER

### 1.1 Responsabilidades

El Brain-layer actúa como **supervisor estratégico** del sistema de trading, con las siguientes capacidades:

1. **Gestión de estados de estrategia**
   - Recomendar estado operativo: `PRODUCTION`, `PILOT`, `DEGRADED`, `RETIRED`
   - Basado en performance histórica, estabilidad y edge detection

2. **Asignación de pesos relativos**
   - Calcular peso recomendado (0.0–1.0) por estrategia dentro de su cluster
   - Maximizar Sharpe/Calmar del cluster minimizando crowding

3. **Ajuste de umbrales de calidad**
   - Modificar threshold mínimo de QualityScore por estrategia
   - Calibrado por régimen de mercado y performance observada

4. **Gestión por régimen**
   - Habilitar/deshabilitar estrategias según régimen (HIGH_VOL, LOW_VOL, TRENDING, RANGING)
   - Ajustar pesos por régimen basado en performance histórica

5. **Detección de decay**
   - Identificar estrategias con edge degradado
   - Proponer degradación o retiro automático

### 1.2 Límites NO Negociables

**El Brain-layer NO puede:**

❌ Modificar RiskAllocator (0–2% por idea permanece fijo)
❌ Alterar `risk_limits.yaml` (caps institucionales inmutables)
❌ Cambiar SL/TP estructurales (decisión de estrategias/TradeManager)
❌ Bypass del Arbiter de conflictos
❌ Enviar órdenes directamente al mercado

**El Brain-layer SOLO puede:**

✅ Bloquear estrategias (estado RETIRED/DEGRADED)
✅ Ajustar threshold de QualityScore (+/- 0.15 máximo)
✅ Recomendar pesos (el Arbiter decide uso final)
✅ Sugerir activación/desactivación por régimen

---

## 2. ARQUITECTURA DE DATOS

### 2.1 Inputs (Reporting Database)

**Tablas consumidas:**

| Tabla | Datos Extraídos | Ventana Temporal |
|-------|----------------|------------------|
| `trade_events` | PnL, R-multiples, símbolos, regímenes | 30/90/180 días |
| `strategy_performance` | Sharpe, Sortino, Calmar, MaxDD | Rolling 30/90 días |
| `risk_snapshots` | Exposición por cluster, correlaciones | Daily |
| `position_snapshots` | Duración promedio, win rate | 30/90 días |
| `rejection_events` | Rechazos por tipo (quality, CB, exposure) | 30 días |

**Métricas calculadas por estrategia:**

```python
{
    'sharpe_ratio': float,           # 30d, 90d
    'sortino_ratio': float,
    'calmar_ratio': float,
    'max_drawdown_pct': float,
    'hit_rate': float,               # % trades ganadores
    'avg_winner': float,             # R promedio ganador
    'avg_loser': float,              # R promedio perdedor
    'expectancy': float,             # E = (win_rate * avg_win) - (loss_rate * avg_loss)
    'pnl_by_regime': {               # PnL por régimen
        'HIGH_VOL': float,
        'LOW_VOL': float,
        'TRENDING': float,
        'RANGING': float
    },
    'quality_correlation': float,    # Corr(QualityScore, R-multiple)
    'rejection_rate': float,         # % señales rechazadas
    'rejection_breakdown': {         # Por tipo de rechazo
        'QUALITY': int,
        'CIRCUIT_BREAKER': int,
        'EXPOSURE': int,
        'DRAWDOWN': int
    },
    'cluster_contribution': float,   # % PnL del cluster
    'crowding_score': float          # Correlación con otras estrategias del cluster
}
```

### 2.2 Output: BrainPolicy

**Estructura de política por estrategia:**

```python
@dataclass
class BrainPolicy:
    strategy_id: str

    # Estado operativo recomendado
    state_suggested: Literal['PRODUCTION', 'PILOT', 'DEGRADED', 'RETIRED']

    # Peso relativo en cluster (0.0–1.0)
    weight_recommendation: float

    # Ajuste de threshold de QualityScore (-0.15 a +0.15)
    quality_threshold_adjustment: float

    # Configuración por régimen
    regime_overrides: Dict[str, RegimeConfig]  # {regime: {enabled, weight_factor}}

    # Metadata de decisión
    metadata: PolicyMetadata

    # Timestamp de generación
    created_at: datetime
    valid_until: datetime  # Expiración de la policy
```

**RegimeConfig:**

```python
@dataclass
class RegimeConfig:
    enabled: bool                    # Activar/desactivar en este régimen
    weight_factor: float             # Multiplicador de peso (0.5–1.5)
    quality_adjustment: float        # Ajuste adicional de threshold
```

**PolicyMetadata:**

```python
@dataclass
class PolicyMetadata:
    reason_summary: str              # Motivo resumido de la decisión
    confidence_score: float          # 0–1, confianza en la recomendación
    triggering_metrics: Dict[str, float]  # Métricas que justifican cambios
    previous_state: str              # Estado anterior
    lookback_days: int               # Ventana de análisis usada
```

---

## 3. CICLO DE VIDA Y PIPELINE

### 3.1 Frecuencias de Recalibración

| Tipo | Frecuencia | Scope | Duración Estimada |
|------|-----------|-------|-------------------|
| **FAST** | Diaria (fin de día) | Métricas 30d, ajustes menores | 5–10 min |
| **DEEP** | Semanal (domingo) | Métricas 90d, cambios de estado | 30–60 min |
| **STRATEGIC** | Mensual | Métricas 180d, retiros, governance | 2–4 horas |

### 3.2 Pipeline de Entrenamiento OFFLINE

```
┌─────────────────────────────────────────────────────┐
│  1. DATA EXTRACTION (Postgres)                      │
│     - Load trade_events, snapshots, rejections      │
│     - Window: 30/90/180 days                        │
└────────────────┬────────────────────────────────────┘
                 │
┌────────────────▼────────────────────────────────────┐
│  2. METRICS CALCULATION                             │
│     - Sharpe, Sortino, Calmar per strategy          │
│     - Regime performance breakdown                  │
│     - Quality correlation analysis                  │
└────────────────┬────────────────────────────────────┘
                 │
┌────────────────▼────────────────────────────────────┐
│  3. POLICY GENERATION (EXPLICABLE MODELS)           │
│     - State decision (rules-based)                  │
│     - Weight optimization (mean-variance)           │
│     - Quality threshold calibration (logistic reg)  │
└────────────────┬────────────────────────────────────┘
                 │
┌────────────────▼────────────────────────────────────┐
│  4. PERSISTENCE                                     │
│     - PostgreSQL: brain_policies table              │
│     - YAML: config/brain_policies.yaml              │
│     - Report: reports/brain/BRAIN_REPORT_*.md       │
└────────────────┬────────────────────────────────────┘
                 │
┌────────────────▼────────────────────────────────────┐
│  5. VALIDATION & APPROVAL                           │
│     - Smoke test policies on synthetic signals      │
│     - Generate diff report vs previous policies     │
│     - Operator approval (manual gate)               │
└─────────────────────────────────────────────────────┘
```

---

## 4. MODELOS EXPLICABLES (NO CAJA NEGRA)

### 4.1 State Decision (Rules-Based)

**Algoritmo de decisión de estado:**

```python
def decide_state(metrics: StrategyMetrics) -> str:
    """
    Decisión basada en umbrales documentados, NO machine learning.
    """
    # RETIRED: edge muerto
    if (metrics.sharpe_30d < 0.5 and
        metrics.sharpe_90d < 0.5 and
        metrics.expectancy < 0):
        return 'RETIRED'

    # DEGRADED: performance cayendo
    if (metrics.sharpe_30d < metrics.sharpe_90d * 0.7 or
        metrics.max_drawdown_pct > 15.0 or
        metrics.rejection_rate > 0.6):
        return 'DEGRADED'

    # PILOT: muestra corta o transición
    if metrics.total_trades < 30:
        return 'PILOT'

    # PRODUCTION: métricas sólidas
    if (metrics.sharpe_90d > 1.0 and
        metrics.hit_rate > 0.45 and
        metrics.expectancy > 0.3):
        return 'PRODUCTION'

    # Default: mantener estado actual
    return metrics.current_state
```

### 4.2 Weight Optimization (Mean-Variance)

**Objetivo:** Maximizar Sharpe del cluster minimizando crowding.

```python
def optimize_cluster_weights(strategies: List[Strategy]) -> Dict[str, float]:
    """
    Optimización de pesos usando mean-variance framework.
    NO deep learning, solo Markowitz adaptado.
    """
    # 1. Matriz de covarianza de PnL entre estrategias
    returns_matrix = get_returns_matrix(strategies, window=90)
    cov_matrix = np.cov(returns_matrix.T)

    # 2. Retornos esperados (Sharpe como proxy)
    expected_returns = [s.sharpe_90d for s in strategies]

    # 3. Constraint: suma de pesos = 1.0 (dentro del cluster)
    # 4. Constraint: peso individual >= 0.1 (mínimo exposure)
    # 5. Constraint: peso individual <= 0.5 (máximo concentration)

    # Solver: quadratic programming (scipy.optimize)
    weights = solve_qp(cov_matrix, expected_returns, constraints)

    return dict(zip([s.id for s in strategies], weights))
```

### 4.3 Quality Threshold Calibration (Logistic Regression)

**Objetivo:** Ajustar threshold para maximizar precision de QualityScore.

```python
def calibrate_quality_threshold(strategy_id: str) -> float:
    """
    Regresión logística simple: QS → P(R > 0)
    Ajustar threshold para maximizar F1-score.
    """
    # 1. Obtener histórico: (quality_score, actual_return)
    data = get_historical_signals(strategy_id, window=90)

    # 2. Modelo: P(win) = sigmoid(β₀ + β₁*QS)
    from sklearn.linear_model import LogisticRegression
    model = LogisticRegression(penalty=None)  # Sin regularización
    model.fit(data[['quality_score']], data['is_winner'])

    # 3. Encontrar threshold óptimo (maximizar F1)
    thresholds = np.linspace(0.5, 0.85, 50)
    f1_scores = [f1_score(data['is_winner'], data['quality_score'] > t)
                 for t in thresholds]
    optimal_threshold = thresholds[np.argmax(f1_scores)]

    # 4. Calcular ajuste vs base (0.60)
    base_threshold = 0.60
    adjustment = optimal_threshold - base_threshold

    # 5. Limitar ajuste a [-0.15, +0.15]
    return np.clip(adjustment, -0.15, +0.15)
```

---

## 5. INTEGRACIÓN CON SISTEMA EXISTENTE

### 5.1 BrainPolicyStore (Runtime)

**Responsabilidades:**

- Cargar policies desde DB/YAML al inicio
- Exponer API thread-safe para consultas en tiempo real
- Cache en memoria con TTL

**API pública:**

```python
class BrainPolicyStore:
    def get_policy(self, strategy_id: str) -> Optional[BrainPolicy]

    def get_effective_quality_threshold(self, strategy_id: str,
                                       regime: str) -> float

    def get_weight(self, strategy_id: str) -> float

    def get_state(self, strategy_id: str) -> str

    def is_enabled_in_regime(self, strategy_id: str, regime: str) -> bool

    def reload_policies(self) -> int  # Recarga desde DB, retorna count
```

### 5.2 Modificaciones en InstitutionalBrain

**Ubicación:** `src/core/brain.py`

**Cambios:**

```python
class InstitutionalBrain:
    def __init__(self, ..., brain_policy_store: Optional[BrainPolicyStore] = None):
        # ...
        self.brain_policy_store = brain_policy_store

    def process_signals(self, signals: List[Signal],
                       market_context: Dict) -> List[Signal]:
        """
        MODIFICACIÓN: Aplicar políticas del Brain antes de arbitraje.
        """
        if not self.brain_policy_store:
            return self._process_signals_original(signals, market_context)

        filtered = []
        regime = market_context.get('regime', 'NORMAL')

        for signal in signals:
            policy = self.brain_policy_store.get_policy(signal.strategy_id)

            if not policy:
                # Sin policy, procesar normalmente
                filtered.append(signal)
                continue

            # 1. Aplicar estado
            if policy.state_suggested == 'RETIRED':
                self._log_brain_block(signal, 'STRATEGY_RETIRED')
                continue

            # 2. Aplicar régimen
            if not self.brain_policy_store.is_enabled_in_regime(
                signal.strategy_id, regime):
                self._log_brain_block(signal, 'REGIME_DISABLED')
                continue

            # 3. Aplicar threshold de calidad ajustado
            adjusted_threshold = self.brain_policy_store.get_effective_quality_threshold(
                signal.strategy_id, regime)

            if signal.quality_score < adjusted_threshold:
                self._log_brain_block(signal, 'QUALITY_BELOW_ADJUSTED_THRESHOLD')
                continue

            # 4. Añadir metadata de Brain a señal (para Arbiter)
            signal.brain_weight = self.brain_policy_store.get_weight(signal.strategy_id)
            signal.brain_state = policy.state_suggested

            filtered.append(signal)

        return self.arbiter.arbitrate_signals(filtered, market_context)
```

### 5.3 Modificaciones en SignalArbitrator

**Integración de pesos del Brain:**

```python
class SignalArbitrator:
    def _calculate_signal_score(self, signal: Signal, context: Dict) -> float:
        """
        MODIFICACIÓN: Incorporar brain_weight como factor adicional.
        """
        base_score = signal.quality_score * signal.ev_calculation.expected_value

        # Factor de peso del Brain (si disponible)
        brain_factor = 1.0
        if hasattr(signal, 'brain_weight'):
            # Estrategias con mayor peso del Brain tienen ventaja en conflictos
            brain_factor = 0.8 + (0.4 * signal.brain_weight)  # [0.8, 1.2]

        # Factor de estado del Brain
        state_factor = {
            'PRODUCTION': 1.0,
            'PILOT': 0.9,
            'DEGRADED': 0.7,
            'RETIRED': 0.0  # No debería llegar aquí
        }.get(getattr(signal, 'brain_state', 'PRODUCTION'), 1.0)

        return base_score * brain_factor * state_factor
```

---

## 6. REPORTING Y AUDITORÍA

### 6.1 Nuevos Tipos de Evento

**BRAIN_POLICY_UPDATE:**

```python
{
    'event_type': 'BRAIN_POLICY_UPDATE',
    'timestamp': datetime,
    'strategy_id': str,
    'old_state': str,
    'new_state': str,
    'old_weight': float,
    'new_weight': float,
    'old_threshold': float,
    'new_threshold': float,
    'reason_summary': str,
    'confidence': float,
    'lookback_days': int
}
```

**BRAIN_DECISION_APPLIED:**

```python
{
    'event_type': 'BRAIN_DECISION_APPLIED',
    'timestamp': datetime,
    'strategy_id': str,
    'symbol': str,
    'action': Literal['BLOCKED', 'THRESHOLD_RAISED', 'DOWNWEIGHTED', 'REGIME_DISABLED'],
    'quality_score_actual': float,
    'quality_threshold_required': float,
    'regime': str,
    'brain_weight': float,
    'brain_state': str
}
```

### 6.2 Informes Mensuales

**Ubicación:** `reports/brain/BRAIN_MONTHLY_YYYYMM.md`

**Contenido:**

1. **Resumen Ejecutivo**
   - Estrategias promocionadas: PILOT → PRODUCTION
   - Estrategias degradadas: PRODUCTION → DEGRADED/RETIRED
   - Impacto estimado en PnL vs baseline sin Brain

2. **Análisis por Cluster**
   - Rebalanceo de pesos
   - Cambios en crowding score
   - Performance del cluster pre/post ajuste

3. **Watchlist**
   - Estrategias en observación (Sharpe cayendo, DD creciente)
   - Candidatas a retiro en próximo ciclo

4. **Calibración de Thresholds**
   - Estrategias con threshold ajustado
   - Impacto en tasa de rechazo y win rate

---

## 7. PERSISTENCIA

### 7.1 Schema SQL

**Tabla:** `brain_policies`

```sql
CREATE TABLE IF NOT EXISTS brain_policies (
    id SERIAL PRIMARY KEY,
    strategy_id VARCHAR(100) NOT NULL,
    state_suggested VARCHAR(20) NOT NULL,
    weight_recommendation NUMERIC(5, 4) NOT NULL,
    quality_threshold_adjustment NUMERIC(4, 3) NOT NULL,
    regime_overrides JSONB,
    metadata JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    valid_until TIMESTAMPTZ NOT NULL,
    is_active BOOLEAN DEFAULT TRUE
);

CREATE INDEX idx_brain_policies_strategy ON brain_policies(strategy_id);
CREATE INDEX idx_brain_policies_active ON brain_policies(is_active, valid_until);
```

**Tabla:** `brain_events`

```sql
CREATE TABLE IF NOT EXISTS brain_events (
    id BIGSERIAL PRIMARY KEY,
    event_type VARCHAR(50) NOT NULL,
    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    strategy_id VARCHAR(100),
    payload JSONB NOT NULL
);

CREATE INDEX idx_brain_events_type ON brain_events(event_type, timestamp);
CREATE INDEX idx_brain_events_strategy ON brain_events(strategy_id, timestamp);
```

### 7.2 Archivo YAML

**Ubicación:** `config/brain_policies.yaml`

**Formato:**

```yaml
# Generado automáticamente por offline_trainer.py
# NO editar manualmente
generated_at: "2025-11-14T10:30:00Z"
valid_until: "2025-11-21T10:30:00Z"
lookback_days: 90

policies:
  breakout_volume_confirmation:
    state: PRODUCTION
    weight: 0.35
    quality_threshold_adjustment: 0.00
    regime_overrides:
      HIGH_VOL:
        enabled: true
        weight_factor: 1.2
      LOW_VOL:
        enabled: true
        weight_factor: 0.8
    metadata:
      reason: "Sharpe 1.8, consistent across regimes"
      confidence: 0.92

  statistical_arbitrage_johansen:
    state: PRODUCTION
    weight: 0.28
    quality_threshold_adjustment: +0.05
    regime_overrides:
      TRENDING:
        enabled: false
        weight_factor: 0.0
    metadata:
      reason: "Strong in ranging, disabled in trends"
      confidence: 0.85
```

---

## 8. TESTING Y VALIDACIÓN

### 8.1 Unit Tests

**Ubicación:** `tests/brain_layer/`

- `test_offline_trainer.py`: Validar extracción de métricas y generación de policies
- `test_runtime.py`: Validar BrainPolicyStore (load, cache, TTL)
- `test_integration.py`: Validar integración con Brain y Arbiter

### 8.2 Smoke Test

**Extensión de:** `scripts/smoke_test_reporting.py`

```python
def test_brain_layer():
    """
    Test 7: Validar Brain-layer end-to-end.
    """
    # 1. Crear policy sintética
    policy = BrainPolicy(
        strategy_id='test_strategy',
        state_suggested='PRODUCTION',
        weight_recommendation=0.5,
        quality_threshold_adjustment=0.05,
        ...
    )

    # 2. Guardar en DB/YAML
    store = BrainPolicyStore()
    store.save_policy(policy)

    # 3. Simular señal y aplicar policy
    signal = create_test_signal(quality_score=0.62)
    brain = InstitutionalBrain(brain_policy_store=store)
    result = brain.process_signals([signal], context)

    # 4. Verificar evento BRAIN_DECISION_APPLIED
    events = get_brain_events_from_db()
    assert any(e['event_type'] == 'BRAIN_DECISION_APPLIED' for e in events)
```

---

## 9. RESTRICCIONES Y COMPLIANCE

### 9.1 Validaciones Obligatorias

Antes de aplicar cualquier BrainPolicy:

✅ `quality_threshold_adjustment` ∈ [-0.15, +0.15]
✅ `weight_recommendation` ∈ [0.0, 1.0]
✅ Suma de pesos por cluster ≤ 1.0
✅ `state_suggested` ∈ {PRODUCTION, PILOT, DEGRADED, RETIRED}
✅ Policy tiene `valid_until` > NOW
✅ Metadata incluye `reason_summary` no vacío

### 9.2 Inmutabilidad Garantizada

**Archivos que el Brain NO puede modificar:**

- `config/risk_limits.yaml`
- `src/core/risk_manager.py::RiskAllocator._calculate_position_size()`
- Cualquier lógica de SL/TP en `TradeManager`

**Validación en CI/CD:**

```bash
# Pre-commit hook
git diff --name-only | grep -E "risk_limits.yaml|risk_allocator" && exit 1
```

---

## 10. ROADMAP Y MEJORAS FUTURAS

### Fase 1 (MANDATO 14) - ACTUAL
- ✅ Diseño formal
- ✅ Offline trainer básico
- ✅ Runtime con BrainPolicyStore
- ✅ Integración con Brain/Arbiter
- ✅ Reporting básico

### Fase 2 (Futuro)
- 🔲 Crowding detection avanzado (network analysis)
- 🔲 Régimen prediction (lead indicators)
- 🔲 Multi-horizon optimization (intraday vs swing)
- 🔲 Adaptive threshold per symbol (no solo por estrategia)

### Fase 3 (Futuro)
- 🔲 Meta-learning sobre políticas (qué ajustes funcionaron mejor)
- 🔲 Simulación de políticas antes de deploy (backtesting de policies)
- 🔲 A/B testing framework para políticas

---

## 11. REFERENCIAS

- Markowitz (1952): Portfolio Selection
- Kelly Criterion (1956): Optimal Position Sizing
- López de Prado (2018): Advances in Financial Machine Learning (Meta-labeling)
- Tharp (1998): Trade Your Way to Financial Freedom (Expectancy)

---

**FIN DEL DISEÑO FORMAL**

**Versión:** 1.0
**Aprobado para implementación:** MANDATO 14
**Siguiente paso:** Codificación de `offline_trainer.py` y `runtime.py`
