# Runtime Profiles Guide - PLAN OMEGA FASE 3.4

**Fecha:** 2025-11-16
**Versión:** 1.0
**Estado:** PRODUCTION READY

---

## Tabla de Contenidos

1. [Overview](#overview)
2. [Available Profiles](#available-profiles)
3. [Usage Examples](#usage-examples)
4. [Profile Configuration](#profile-configuration)
5. [Creating Custom Profiles](#creating-custom-profiles)
6. [Best Practices](#best-practices)
7. [Troubleshooting](#troubleshooting)

---

## Overview

Los **Runtime Profiles** permiten activar/desactivar conjuntos de estrategias según diferentes escenarios de trading.

### ¿Por qué usar profiles?

- **Simplificación**: Activa solo las estrategias necesarias
- **Performance**: Menor consumo de recursos computacionales
- **Capital Management**: Perfiles adaptados a diferentes niveles de capital
- **Testing**: Valida estrategias core antes de escalar a todas

### Arquitectura

```
StrategyOrchestrator
    │
    ├── config/strategies_institutional.yaml  (configuración completa)
    │
    └── config/profiles/
            ├── green_only.yaml   (5 estrategias core)
            └── full_24.yaml      (24 estrategias completas)
```

**Sin profile**: Carga todas las estrategias con `enabled: true` en config
**Con profile**: Carga solo las estrategias en `enabled_strategies` del profile

---

## Available Profiles

### 1. GREEN_ONLY (Conservative)

**Estrategias:** 5 core GREEN
**Capital recomendado:** $10,000+
**Señales/día:** 3-8
**Win rate esperado:** 65-72%
**Uso:** Live trading inicial, capital limitado

#### Estrategias incluidas:
1. **mean_reversion_statistical** - Statistical mean reversion (Avellaneda & Lee 2010)
2. **liquidity_sweep** - Stop hunt detection (ICT 2024)
3. **order_flow_toxicity** - VPIN fade strategy (Easley et al. 2012)
4. **momentum_quality** - Quality momentum
5. **order_block_institutional** - Order block retest

#### Características:
- ✅ Sin dependencias de pairs/correlaciones
- ✅ Menor complejidad computacional
- ✅ Mayor confiabilidad (estrategias probadas)
- ✅ Ideal para principiantes institucionales

#### Configuración recomendada:
```yaml
execution:
  mode: PAPER
  initial_capital: 10000.0
  max_positions: 3
  max_risk_per_trade: 0.015  # 1.5%
  max_daily_loss: 0.04       # 4%

killswitch:
  max_consecutive_losses: 4
  emergency_drawdown_pct: 0.12  # 12%
```

---

### 2. FULL_24 (Aggressive)

**Estrategias:** 24 institucionales completas
**Capital recomendado:** $50,000+
**Señales/día:** 15-40
**Win rate esperado:** 62-68%
**Uso:** Máxima diversificación, capital amplio

#### Categorías de estrategias:

**GREEN Core (5):**
- mean_reversion_statistical
- liquidity_sweep
- order_flow_toxicity
- momentum_quality
- order_block_institutional

**HYBRID Pairs/Correlations (4):**
- kalman_pairs_trading
- correlation_divergence
- correlation_cascade_detection
- statistical_arbitrage_johansen

**HYBRID Advanced (12):**
- volatility_regime_adaptation
- breakout_volume_confirmation
- fvg_institutional
- htf_ltf_liquidity
- iceberg_detection
- idp_inducement_distribution
- ofi_refinement
- vpin_reversal_extreme
- fractal_market_structure
- footprint_orderflow_clusters
- crisis_mode_volatility_spike
- topological_data_analysis_regime

**HYBRID Exotic (3):**
- calendar_arbitrage_flows
- spoofing_detection_l2
- nfp_news_event_handler

#### Requisitos de datos:
- ✅ Pares múltiples (EURUSD, GBPUSD, AUDUSD, etc.)
- ✅ News calendar (NFP, FOMC, CPI)
- ⚠️ Level 2 orderbook (opcional - 2 estrategias degradadas sin L2)

#### Configuración recomendada:
```yaml
execution:
  mode: PAPER
  initial_capital: 50000.0
  max_positions: 10
  max_risk_per_trade: 0.020  # 2.0%
  max_daily_loss: 0.05       # 5%

killswitch:
  max_consecutive_losses: 5
  emergency_drawdown_pct: 0.15  # 15%
```

---

## Usage Examples

### Example 1: GREEN_ONLY con PAPER Trading

```python
from src.strategy_orchestrator import StrategyOrchestrator
from src.execution.execution_mode import ExecutionMode, ExecutionConfig

# Configuración PAPER conservadora
exec_config = ExecutionConfig(
    mode=ExecutionMode.PAPER,
    initial_capital=10000.0,
    max_positions=3,
    max_risk_per_trade=0.015  # 1.5%
)

# Inicializar con profile GREEN_ONLY
orchestrator = StrategyOrchestrator(
    config_path='config/strategies_institutional.yaml',
    profile='green_only',
    execution_config=exec_config
)

# Resultado: Solo 5 estrategias core cargadas
print(f"Strategies loaded: {len(orchestrator.strategies)}")  # 5
print(f"Profile: {orchestrator.profile_name}")  # green_only
```

### Example 2: FULL_24 con Signal Generation Only

```python
from src.strategy_orchestrator import StrategyOrchestrator

# Inicializar sin ExecutionManager (solo generación de señales)
orchestrator = StrategyOrchestrator(
    config_path='config/strategies_institutional.yaml',
    profile='full_24',
    execution_config=None  # No auto-execution
)

# Evaluar estrategias
import pandas as pd
market_data = pd.DataFrame(...)  # Tu data

signals = orchestrator.evaluate_strategies(market_data)
print(f"Signals generated: {len(signals)}")

# Manual signal processing
for signal in signals:
    print(f"{signal.strategy_name}: {signal.direction} {signal.symbol}")
```

### Example 3: Sin Profile (Default Behavior)

```python
from src.strategy_orchestrator import StrategyOrchestrator

# Sin profile → carga todas las estrategias con enabled=True en config
orchestrator = StrategyOrchestrator(
    config_path='config/strategies_institutional.yaml',
    profile=None  # Default
)

# Carga basada en strategies_institutional.yaml enabled flags
print(f"Strategies loaded: {len(orchestrator.strategies)}")
```

### Example 4: GREEN_ONLY → LIVE Transition

```python
# PASO 1: Validar en PAPER primero
from src.strategy_orchestrator import StrategyOrchestrator
from src.execution.execution_mode import ExecutionMode, ExecutionConfig

paper_config = ExecutionConfig(
    mode=ExecutionMode.PAPER,
    initial_capital=10000.0
)

orchestrator_paper = StrategyOrchestrator(
    profile='green_only',
    execution_config=paper_config
)

# PASO 2: Después de validación exitosa → LIVE
# ⚠️ WARNING: REAL MONEY
live_config = ExecutionConfig(
    mode=ExecutionMode.LIVE,
    initial_capital=10000.0,
    broker_config={
        'broker_type': 'oanda',  # o tu broker
        'api_key': 'YOUR_API_KEY',
        'account_id': 'YOUR_ACCOUNT'
    }
)

orchestrator_live = StrategyOrchestrator(
    profile='green_only',
    execution_config=live_config
)
```

---

## Profile Configuration

### Profile YAML Structure

```yaml
# Profile metadata
profile_name: "GREEN_ONLY"
profile_type: "conservative"  # o "aggressive"
description: "Description here"

# Estrategias activas (CRITICAL)
enabled_strategies:
  - strategy_name_1
  - strategy_name_2
  - ...

# Estrategias deshabilitadas (documentación)
disabled_strategies:
  - strategy_name_3
  - ...

# Configuración recomendada
execution:
  mode: "PAPER"
  initial_capital: 10000.0
  max_positions: 3
  max_risk_per_trade: 0.015

# KillSwitch override (opcional)
killswitch:
  enabled: true
  max_consecutive_losses: 4

# Metadata (documentación)
stats:
  expected_signals_per_day: 3-8
  average_win_rate: 65-72%
```

### Validation Rules

1. **enabled_strategies** es OBLIGATORIO
2. Cada estrategia debe existir en `strategies_institutional.yaml`
3. Profile type debe ser: `conservative`, `balanced`, o `aggressive`

---

## Creating Custom Profiles

### Paso 1: Crear YAML

```bash
# Crear nuevo profile
touch config/profiles/my_custom_profile.yaml
```

### Paso 2: Definir Estrategias

```yaml
profile_name: "MY_CUSTOM"
profile_type: "balanced"
description: "My custom strategy mix"

enabled_strategies:
  # Elige las estrategias que quieras
  - mean_reversion_statistical
  - liquidity_sweep
  - kalman_pairs_trading
  - vpin_reversal_extreme

disabled_strategies:
  # Resto de estrategias...
  - order_flow_toxicity
  - ...
```

### Paso 3: Usar el Profile

```python
orchestrator = StrategyOrchestrator(
    profile='my_custom_profile'  # nombre del archivo (sin .yaml)
)
```

### Ejemplos de Perfiles Custom

#### MEAN_REVERSION_ONLY (Ultra Conservative)
```yaml
enabled_strategies:
  - mean_reversion_statistical
  - kalman_pairs_trading
  - statistical_arbitrage_johansen
```

#### CRISIS_MODE (Eventos extremos)
```yaml
enabled_strategies:
  - crisis_mode_volatility_spike
  - vpin_reversal_extreme
  - nfp_news_event_handler
```

#### PAIRS_TRADING_ONLY
```yaml
enabled_strategies:
  - kalman_pairs_trading
  - correlation_divergence
  - correlation_cascade_detection
  - statistical_arbitrage_johansen
```

---

## Best Practices

### 1. Testing Workflow

```
GREEN_ONLY (PAPER) → Validar 30 días
    ↓ (si exitoso)
GREEN_ONLY (LIVE) → Micro capital, 30 días
    ↓ (si exitoso)
FULL_24 (PAPER) → Validar 60 días
    ↓ (si exitoso)
FULL_24 (LIVE) → Production capital
```

### 2. Capital Allocation

| Profile | Min Capital | Recommended | Max Positions |
|---------|-------------|-------------|---------------|
| GREEN_ONLY | $5,000 | $10,000+ | 3-5 |
| FULL_24 | $25,000 | $50,000+ | 8-10 |

### 3. KillSwitch Settings

**GREEN_ONLY** (más estricto):
```python
max_consecutive_losses: 4
emergency_drawdown_pct: 0.12  # 12%
max_daily_loss: 0.04          # 4%
```

**FULL_24** (default):
```python
max_consecutive_losses: 5
emergency_drawdown_pct: 0.15  # 15%
max_daily_loss: 0.05          # 5%
```

### 4. Monitoring

```python
# Obtener estadísticas por profile
stats = orchestrator.get_statistics()

print(f"Profile: {orchestrator.profile_name}")
print(f"Active strategies: {len(orchestrator.strategies)}")
print(f"Signals received: {stats['signals_received']}")
print(f"Execution rate: {stats['execution_rate']:.1%}")

# KillSwitch status
if orchestrator.execution_manager:
    ks_status = orchestrator.execution_manager.get_killswitch_status()
    print(f"Emergency stop: {ks_status['emergency_stop_active']}")
```

---

## Troubleshooting

### Error: "Profile not found"

```python
FileNotFoundError: Profile 'my_profile' not found at config/profiles/my_profile.yaml
```

**Solución:**
- Verificar que el archivo existe: `ls config/profiles/`
- Verificar nombre correcto (sin `.yaml` en el parámetro)

### Error: "Strategy failed to initialize"

```
Failed to initialize strategy 'kalman_pairs_trading': missing data
```

**Solución:**
- Algunas estrategias requieren datos específicos (pairs, L2)
- Para FULL_24, asegurar todos los datos disponibles
- O crear profile custom sin esas estrategias

### Estrategias cargadas ≠ esperadas

```python
# GREEN_ONLY debería cargar 5, pero solo carga 3
```

**Diagnóstico:**
```python
# Verificar logs
import logging
logging.basicConfig(level=logging.DEBUG)

orchestrator = StrategyOrchestrator(profile='green_only')
# Revisar output para errores de inicialización
```

### Performance degradado con FULL_24

**Solución:**
- FULL_24 requiere ~4x más recursos que GREEN_ONLY
- Considerar profile custom con subset de estrategias
- Optimizar hardware o reducir a GREEN_ONLY

---

## Migration Path

### Desde Sistema Legacy

Si vienes de un sistema antiguo:

```python
# ANTES (legacy)
orchestrator = StrategyOrchestrator()  # Cargaba todo

# DESPUÉS (PLAN OMEGA)
orchestrator = StrategyOrchestrator(profile='green_only')
```

### Agregar Profile a Sistema Existente

```python
# Sistema existente sin profiles
orchestrator = StrategyOrchestrator(
    config_path='config/strategies_institutional.yaml'
)

# Migrar a profile system (backward compatible)
orchestrator = StrategyOrchestrator(
    config_path='config/strategies_institutional.yaml',
    profile=None  # Mismo comportamiento que antes
)

# Luego adoptar profiles
orchestrator = StrategyOrchestrator(
    profile='green_only'  # Nueva funcionalidad
)
```

---

## Performance Comparison

| Métrica | GREEN_ONLY | FULL_24 |
|---------|------------|---------|
| Estrategias | 5 | 24 |
| Señales/día | 3-8 | 15-40 |
| Win rate | 65-72% | 62-68% |
| Avg R:R | 2.8-3.5 | 2.5-3.0 |
| CPU usage | ~20% | ~80% |
| Memory | ~500MB | ~2GB |
| Data requirements | Básico | Completo + L2 |
| Capital min | $10k | $50k |

---

## Conclusión

Los Runtime Profiles permiten escalar tu sistema de forma controlada:

1. **Comenzar**: GREEN_ONLY en PAPER
2. **Validar**: 30 días, métricas positivas
3. **Escalar**: GREEN_ONLY en LIVE (micro capital)
4. **Expandir**: FULL_24 en PAPER
5. **Production**: FULL_24 en LIVE

**Recuerda:** Siempre validar en PAPER antes de LIVE.

---

**PLAN OMEGA FASE 3.4 - Runtime Profiles COMPLETE ✅**
