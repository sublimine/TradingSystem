# MicrostructureEngine - Guía de Uso

**FASE 3.1: Ecosystem Integration - MicrostructureEngine MVP**

## Objetivo

Centralizar el cálculo de features institucionales de microestructura (OFI, VPIN, CVD) en un motor unificado que todas las 24 estrategias usan de forma consistente.

## Features Provistas

El `MicrostructureEngine` calcula:

| Feature | Rango | Descripción |
|---------|-------|-------------|
| **OFI** | -1 to +1 | Order Flow Imbalance - dirección del flujo institucional |
| **VPIN** | 0 to 1 | Flow toxicity - flujo informado (0) vs desinformado (1) |
| **CVD** | -1 to +1 | Cumulative Volume Delta - presión direccional acumulada |
| **spread_pct** | 0+ | Spread estimado como % del mid price |
| **ob_imbalance** | -1 to +1 | Order book imbalance estimado |

## Uso Básico

```python
from src.core.microstructure_engine import MicrostructureEngine

# 1. Inicializar engine (una vez por sistema)
engine = MicrostructureEngine()

# 2. Calcular features por cada tick/bar
features = engine.calculate_features(market_data)

# 3. Acceder features
ofi = features['ofi']        # Order Flow Imbalance
vpin = features['vpin']      # Flow toxicity
cvd = features['cvd']        # Cumulative Volume Delta

# 4. Interpretación
if ofi > 0 and vpin < 0.3:
    # Institutional BUYING + CLEAN flow = Strong buy signal
    pass
elif ofi < 0 and vpin > 0.5:
    # Institutional SELLING + TOXIC flow = Avoid (panic selling)
    pass
```

## Integración en Estrategias

### Antes (sin MicrostructureEngine)

Cada estrategia calculaba sus propias features:

```python
# strategy_a.py
from src.features.ofi import calculate_ofi
from src.features.order_flow import VPINCalculator

class StrategyA:
    def __init__(self):
        self.ofi_window = 20
        self.vpin_calc = VPINCalculator()

    def evaluate(self, data):
        ofi = calculate_ofi(data, self.ofi_window)  # Calculado aquí
        vpin = self.vpin_calc.get_current_vpin()    # Calculado aquí
        # ...

# strategy_b.py - DUPLICANDO lógica
class StrategyB:
    def __init__(self):
        self.ofi_window = 25  # ⚠️ Diferente window!
        # ...mismo cálculo duplicado
```

**Problemas**:
- Código duplicado
- Inconsistencias en parámetros (OFI window 20 vs 25)
- Múltiples cálculos del mismo feature
- Difícil mantener consistencia

### Después (con MicrostructureEngine)

```python
# Todas las estrategias comparten el mismo engine

class StrategyA(StrategyBase):
    def evaluate(self, market_data: pd.DataFrame, features: Dict):
        ofi = features['ofi']    # Ya calculado por engine
        vpin = features['vpin']  # Ya calculado por engine
        cvd = features['cvd']    # Ya calculado por engine

        if ofi > 0.5 and vpin < 0.3:
            # Strong institutional buying, clean flow
            return self._generate_signal(...)

class StrategyB(StrategyBase):
    def evaluate(self, market_data: pd.DataFrame, features: Dict):
        # Mismos features, mismos parámetros, cálculo centralizado
        ofi = features['ofi']
        # ...
```

**Beneficios**:
- ✅ Cálculo centralizado (una sola vez)
- ✅ Parámetros consistentes entre estrategias
- ✅ Features en `features` dict ya calculados
- ✅ Cache automático
- ✅ Logging consistente

## Integración en StrategyOrchestrator

```python
from src.core.microstructure_engine import MicrostructureEngine

class StrategyOrchestrator:
    def __init__(self):
        # Crear engine compartido
        self.microstructure_engine = MicrostructureEngine(config={
            'ofi_window': 20,
            'vpin_bucket_size': 50000,
            'vpin_num_buckets': 50,
            'cvd_window': 20
        })

        self.strategies = self._initialize_strategies()

    def process_market_data(self, market_data: pd.DataFrame):
        # 1. Calcular features UNA VEZ para todas las estrategias
        microstructure_features = self.microstructure_engine.calculate_features(
            market_data,
            use_cache=True  # Cache entre llamadas del mismo bar
        )

        # 2. Agregar a features dict existente
        features = {
            **self._calculate_other_features(market_data),
            **microstructure_features  # OFI, VPIN, CVD, etc.
        }

        # 3. Evaluar estrategias con features unificados
        signals = []
        for strategy in self.strategies.values():
            strategy_signals = strategy.evaluate(market_data, features)
            signals.extend(strategy_signals)

        return signals
```

## Configuración Avanzada

### Custom Parameters

```python
engine = MicrostructureEngine(config={
    # OFI settings
    'ofi_window': 30,  # Larger window for longer-term flow

    # VPIN settings
    'vpin_bucket_size': 100000,  # Larger buckets for less liquid instruments
    'vpin_num_buckets': 100,     # More buckets for longer history

    # CVD settings
    'cvd_window': 50  # Longer cumulative window
})
```

### Feature Summary

```python
features = engine.calculate_features(market_data)

# Get human-readable summary
summary = engine.get_feature_summary(features)
logger.info(summary)
# Output: "OFI: Strong BUY flow (+0.72) | VPIN: CLEAN (0.18) | CVD: Cumulative BUYING (+0.45)"
```

## Interpretación de Features

### OFI (Order Flow Imbalance)

| Valor | Interpretación | Acción |
|-------|----------------|--------|
| +0.7 a +1.0 | Strong institutional BUYING | Bullish signal (high confidence) |
| +0.3 a +0.7 | Moderate BUYING | Bullish signal (medium confidence) |
| -0.3 a +0.3 | Balanced flow | Neutral (wait) |
| -0.7 a -0.3 | Moderate SELLING | Bearish signal (medium confidence) |
| -1.0 a -0.7 | Strong institutional SELLING | Bearish signal (high confidence) |

### VPIN (Flow Toxicity)

| Valor | Interpretación | Acción |
|-------|----------------|--------|
| 0.0 - 0.2 | CLEAN - Informed institutional flow | ✅ Safe to trade with flow |
| 0.2 - 0.4 | Moderate toxicity | ⚠️ Caution - verify with other signals |
| 0.4 - 0.6 | Elevated toxicity | ⚠️ Risky - reduce size |
| 0.6+ | TOXIC - Uninformed/panic flow | ❌ Avoid trading (false signals) |

### CVD (Cumulative Volume Delta)

| Valor | Interpretación | Acción |
|-------|----------------|--------|
| +0.5 a +1.0 | Strong cumulative BUYING | Bullish momentum confirmed |
| +0.2 a +0.5 | Moderate cumulative BUYING | Bullish bias |
| -0.2 a +0.2 | Balanced | Neutral |
| -0.5 a -0.2 | Moderate cumulative SELLING | Bearish bias |
| -1.0 a -0.5 | Strong cumulative SELLING | Bearish momentum confirmed |

## Patrones Institucionales

### Patrón 1: Institutional Buy Setup
```python
if features['ofi'] > 0.5 and features['vpin'] < 0.3 and features['cvd'] > 0.3:
    # Strong BUY flow + CLEAN + Cumulative buying
    # HIGH PROBABILITY BUY SIGNAL
    confidence = 0.85
```

### Patrón 2: Toxic Sell-off (AVOID)
```python
if features['ofi'] < -0.5 and features['vpin'] > 0.6:
    # Strong SELL flow + TOXIC
    # PANIC SELLING - Don't fade, don't follow
    # WAIT for VPIN to drop below 0.3
    action = "AVOID"
```

### Patrón 3: Reversal Setup
```python
if features['ofi'] > 0.6 and features['cvd'] < -0.5:
    # Strong BUY flow but cumulative SELLING
    # Potential REVERSAL from oversold
    # Institutions absorbing supply
    confidence = 0.75
```

## Performance & Caching

### Caching Mechanism

```python
# Primera llamada - calcula features
features_1 = engine.calculate_features(market_data)  # ~5-10ms

# Segunda llamada mismo timestamp - usa cache
features_2 = engine.calculate_features(market_data, use_cache=True)  # ~0.1ms

# Nueva barra - recalcula
new_data = get_next_bar()
features_3 = engine.calculate_features(new_data)  # ~5-10ms (recalcula)
```

### Reset Engine

```python
# Reset cache y estado VPIN (ej: nuevo instrumento)
engine.reset()
```

## Testing

```python
import pytest
from src.core.microstructure_engine import MicrostructureEngine

def test_microstructure_engine():
    # Crear engine
    engine = MicrostructureEngine()

    # Datos sintéticos
    data = create_sample_data(bars=100)

    # Calcular features
    features = engine.calculate_features(data)

    # Validar
    assert -1 <= features['ofi'] <= 1
    assert 0 <= features['vpin'] <= 1
    assert -1 <= features['cvd'] <= 1
    assert features['spread_pct'] >= 0

    # Test caching
    features_cached = engine.calculate_features(data, use_cache=True)
    assert features == features_cached
```

## Migración de Estrategias Existentes

### Paso 1: Identificar Features Usados

```python
# OLD CODE
class MyStrategy:
    def evaluate(self, data):
        # Buscar estos patterns:
        ofi = calculate_ofi(data, ...)          # ← OFI
        vpin = self.vpin_calc.get_vpin()        # ← VPIN
        cvd = calculate_cumulative_volume_delta(...)  # ← CVD
```

### Paso 2: Reemplazar con Features Dict

```python
# NEW CODE
class MyStrategy(StrategyBase):
    def evaluate(self, market_data: pd.DataFrame, features: Dict):
        # Features ya calculados por engine
        ofi = features['ofi']
        vpin = features['vpin']
        cvd = features['cvd']

        # Resto de lógica sin cambios
        if ofi > 0.5 and vpin < 0.3:
            return self._generate_signal(...)
```

### Paso 3: Actualizar Tests

```python
def test_my_strategy():
    strategy = MyStrategy(config)

    # Crear features mock
    features = {
        'ofi': 0.6,
        'vpin': 0.25,
        'cvd': 0.4,
        'atr': 0.0015,
        # ... other features
    }

    signals = strategy.evaluate(market_data, features)
    assert len(signals) > 0
```

## Roadmap

### MVP (Actual)
- ✅ OFI, VPIN, CVD calculation
- ✅ Caching mechanism
- ✅ Feature summary
- ✅ Basic documentation

### Phase 2 (Post-MVP)
- [ ] Multi-timeframe features (OFI_1m, OFI_5m, etc.)
- [ ] Advanced VPIN (with L2 data when available)
- [ ] Order book depth analytics
- [ ] Footprint charts integration
- [ ] Real-time streaming mode

### Phase 3 (Advanced)
- [ ] Machine learning feature engineering
- [ ] Regime-adaptive parameter tuning
- [ ] Cross-instrument flow correlation
- [ ] Institutional whale detection

---

**Author**: Elite Institutional Trading System
**Version**: 1.0 MVP
**PLAN OMEGA**: FASE 3.1 - Ecosystem Integration
**Date**: 2025-11-16
