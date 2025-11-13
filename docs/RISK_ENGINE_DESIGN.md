# RISK ENGINE DESIGN – SISTEMA INSTITUCIONAL DE GESTIÓN DEL RIESGO

**Sistema**: TradingSystem  
**Fecha**: 2025-11-13  
**Mandato**: MANDATO 4 - Risk Manager institucional con Quality Score  
**Estado**: Diseño arquitectónico - Fase 1

---

## ÍNDICE

1. [Resumen Ejecutivo](#1-resumen-ejecutivo)
2. [Principios Fundamentales](#2-principios-fundamentales)
3. [Arquitectura General](#3-arquitectura-general)
4. [Componente 1: QualityScorer](#4-componente-1-qualityscorer)
5. [Componente 2: RiskAllocator](#5-componente-2-riskallocator)
6. [Componente 3: TradeManager](#6-componente-3-trademanager)
7. [Componente 4: ExposureManager](#7-componente-4-exposuremanager)
8. [Flujos de Datos](#8-flujos-de-datos)
9. [Interfaces de Integración](#9-interfaces-de-integración)
10. [Sistema de Memoria y Aprendizaje](#10-sistema-de-memoria-y-aprendizaje)

---

## 1. RESUMEN EJECUTIVO

El **Risk Engine** es el sistema central de gestión del riesgo que evalúa, asigna y gestiona cada operación con precisión institucional. Cada trade queda definido con exactitud clínica: lotaje calculado, stops estructurales, targets basados en liquidez, trailing inteligente.

### Objetivos Primarios

1. **Quality Score**: Puntuar cada señal [0-1] integrando 5 dimensiones de calidad
2. **Risk Allocation**: Asignar riesgo óptimo según calidad (max 2% por idea)
3. **Structural Execution**: Gestionar SL/TP/trailing/parciales sin ATR ni retail logic
4. **Exposure Control**: Prevenir concentraciones y correlaciones excesivas
5. **Learning Loop**: Memoria de trades para calibración continua

### Restricciones No Negociables

- **Riesgo máximo por idea**: 2.0% del capital total
- **Prohibido ATR**: SL/TP basados en estructura, no volatilidad ciega
- **Prohibido retail**: Sin distancias fijas arbitrarias (20 pips, 1.5R, etc.)
- **Todo trazable**: Cada decisión de riesgo registrada con inputs y outputs

---

## 2. PRINCIPIOS FUNDAMENTALES

### 2.1. Calidad Sobre Cantidad

Operamos SOLO cuando:
- Quality Score >= threshold mínimo (0.50)
- Riesgo disponible suficiente
- Estructura de mercado válida
- Exposición de cartera permisible

**Mejor 3 trades excelentes que 10 trades mediocres.**

### 2.2. Riesgo Proporcional a Calidad

Relación monótona estricta:
```
Risk = f(Quality Score, Available Budget, Exposure)
donde f es creciente en Quality Score
```

Bandas orientativas:
- Score < 0.50 → NO TRADE
- Score 0.50-0.70 → Riesgo bajo (0.25-0.50%)
- Score 0.70-0.85 → Riesgo medio (0.50-1.00%)
- Score 0.85-0.95 → Riesgo alto (1.00-1.50%)
- Score 0.95-1.00 → Riesgo máximo (1.50-2.00%)

### 2.3. Stops Estructurales, No Emocionales

El SL se ubica donde **la idea es inválida**, no donde duele menos:
- Order blocks violados
- Zonas de liquidez consumidas
- Invalidación de régimen detectado por RegimeEngine
- Ruptura de estructura confirmada por microstructure

### 2.4. Targets Basados en Liquidez

TPs alineados con:
- Zonas de liquidez conocidas (HTF levels, session levels)
- MFE histórico de la estrategia en ese régimen
- Profundidad del order book (cuando disponible)
- Resistencias/soportes estructurales

### 2.5. Memoria Obligatoria

Cada trade genera:
- Pre-trade: Quality Score inputs + risk allocation decision
- During-trade: Path del precio, SL/TP adjustments
- Post-trade: Outcome, MAE, MFE, R-multiple, learning signals

---

## 3. ARQUITECTURA GENERAL

### 3.1. Diagrama de Alto Nivel

```
┌─────────────────────────────────────────────────────────────────┐
│                        RISK ENGINE                               │
│                                                                   │
│  ┌──────────────┐   ┌──────────────┐   ┌──────────────┐        │
│  │QualityScorer │──→│RiskAllocator │──→│ TradeManager │        │
│  │              │   │              │   │              │        │
│  │ Score: 0-1   │   │ Risk: 0-2%   │   │ SL/TP/Trail  │        │
│  └──────────────┘   └──────────────┘   └──────────────┘        │
│         ↓                   ↓                   ↓                │
│  ┌──────────────────────────────────────────────────────┐       │
│  │           ExposureManager (Control Global)            │       │
│  │  - Portfolio exposure tracking                        │       │
│  │  - Correlation monitoring                             │       │
│  │  - Budget allocation per strategy/symbol              │       │
│  └──────────────────────────────────────────────────────┘       │
│                          ↓                                        │
│  ┌──────────────────────────────────────────────────────┐       │
│  │        MemoryStore (Learning & Calibration)           │       │
│  │  - Trade history with Quality Scores                  │       │
│  │  - MAE/MFE distributions per strategy                 │       │
│  │  - Score-to-outcome mapping for recalibration         │       │
│  └──────────────────────────────────────────────────────┘       │
└─────────────────────────────────────────────────────────────────┘
```

### 3.2. Flujo de Procesamiento

1. **Signal arrives** → Estrategia genera señal bruta
2. **QualityScorer** → Evalúa señal + contexto → emite Quality Score
3. **ExposureManager** → Verifica constraints de exposición
4. **RiskAllocator** → Asigna riesgo % según score y disponibilidad
5. **TradeManager** → Diseña execution profile (SL/TP/trailing/parciales/lotaje)
6. **Decision** → EXECUTE o REJECT
7. **MemoryStore** → Registra decisión y contexto para aprendizaje

---

## 4. COMPONENTE 1: QUALITYSCORER

### 4.1. Responsabilidad

Evaluar la **calidad integral** de cada señal candidata mediante análisis multidimensional.

### 4.2. Inputs

```python
class SignalCandidate:
    # Identificación
    signal_id: str
    strategy_name: str
    symbol: str
    direction: Literal['LONG', 'SHORT']
    
    # Pricing
    entry_price: float
    sl_structural: float  # Sugerido por estrategia
    tp_levels: List[float]
    
    # Contexto estrategia
    signal_strength: float  # Interno de estrategia (ej. z-score, confidence)
    distance_to_threshold: float  # Cuánto supera threshold de activación
    confluence_factors: List[str]  # Qué confluye (HTF, LTF, OFI, etc.)
    
    # Contexto mercado
    regime: str  # Del RegimeEngine
    vpin: float
    spread_bps: float
    depth_score: float  # Proxy de profundidad de book
    volatility_percentile: float  # Volatilidad actual vs histórica
    
    # Contexto cartera
    current_exposure_pct: float
    correlated_positions: List[str]
    total_risk_deployed_pct: float
```

### 4.3. Dimensiones de Calidad

El Quality Score integra **5 dimensiones**, cada una ponderada:

#### Dimensión 1: Pedigrí de Estrategia (peso: 0.25)

```
pedigree_score = (
    0.40 * sharpe_ratio_normalized +
    0.30 * hit_rate_in_regime +
    0.20 * calmar_ratio_normalized +
    0.10 * strategy_tier_bonus
)
```

Donde:
- `sharpe_ratio_normalized`: Sharpe histórico de estrategia normalizado [0-1]
- `hit_rate_in_regime`: Win rate en el régimen actual [0-1]
- `calmar_ratio_normalized`: Calmar ratio (return/max_dd) normalizado [0-1]
- `strategy_tier_bonus`: Bonus para estrategias élite
  - Tier 1 (élite): +0.20 (ofi_refinement, spoofing_l2, vpin_reversal)
  - Tier 2 (probadas): +0.10 (momentum_quality, liquidity_sweep, order_block)
  - Tier 3 (nuevas): +0.00

#### Dimensión 2: Fuerza de Señal (peso: 0.25)

```
signal_score = (
    0.35 * signal_strength_normalized +
    0.25 * distance_to_threshold_score +
    0.20 * confluence_score +
    0.20 * regime_fit_score
)
```

Donde:
- `signal_strength_normalized`: Fuerza interna [0-1] (z-score, probability, etc.)
- `distance_to_threshold_score`: Cuánto supera threshold mínimo
  - Si threshold = 0.6 y signal = 0.9 → score = (0.9-0.6)/(1.0-0.6) = 0.75
- `confluence_score`: Número de factores que confluyen / max posible
  - Ej: 3 confluencias de 5 posibles = 0.60
- `regime_fit_score`: Fit de estrategia con régimen actual (del brain.py fit_matrix)

#### Dimensión 3: Microestructura y Liquidez (peso: 0.20)

```
microstructure_score = (
    0.40 * (1 - spread_normalized) +  # Spread bajo = bueno
    0.30 * depth_score +
    0.30 * vpin_quality_score
)
```

Donde:
- `spread_normalized`: Spread actual vs spread típico del símbolo [0-1]
  - Spread estrecho → score alto
- `depth_score`: Profundidad visible/estimada [0-1]
  - Alta profundidad → ejecución limpia → score alto
- `vpin_quality_score`: Calidad del flow según VPIN
  - VPIN < 0.30 (clean flow) → 1.0
  - VPIN 0.30-0.50 (neutral) → 0.5
  - VPIN > 0.50 (toxic flow) → 0.0

#### Dimensión 4: Salud de Datos y Modelo (peso: 0.15)

```
data_health_score = (
    0.50 * data_completeness +
    0.30 * signal_sanity_check +
    0.20 * model_consistency
)
```

Donde:
- `data_completeness`: % de features sin NaN/outliers [0-1]
- `signal_sanity_check`: Señal dentro de rango esperado [0-1]
  - Outliers patológicos (>5 sigma) → penalización
- `model_consistency`: Coherencia entre módulos (features, gatekeepers, strategies)
  - Contradicciones detectadas → penalización

#### Dimensión 5: Posición de Cartera (peso: 0.15)

```
portfolio_score = (
    0.50 * (1 - exposure_ratio) +
    0.50 * (1 - correlation_penalty)
)
```

Donde:
- `exposure_ratio`: Exposición actual en símbolo/sector/factor / límite
  - Baja exposición → score alto
- `correlation_penalty`: Grado de correlación con posiciones abiertas
  - Sin correlación → penalty = 0 → score alto
  - Alta correlación (misma dirección, mismo factor) → penalty = 1 → score bajo

### 4.4. Fórmula Final del Quality Score

```
Quality_Score = (
    0.25 * pedigree_score +
    0.25 * signal_score +
    0.20 * microstructure_score +
    0.15 * data_health_score +
    0.15 * portfolio_score
)

Resultado: [0.0, 1.0]
```

### 4.5. Output

```python
class QualityEvaluation:
    score: float  # [0.0, 1.0]
    breakdown: Dict[str, float]  # Score por dimensión
    flags: List[str]  # Warnings o notas (ej: "high_correlation", "toxic_flow")
    timestamp: datetime
    inputs_snapshot: Dict  # Snapshot de inputs para trazabilidad
```

### 4.6. Calibración y Aprendizaje

El QualityScorer debe ajustar sus parámetros con el tiempo:

1. **Análisis post-trade**:
   - Correlacionar Quality Score con outcomes (R-multiple, Sharpe, MAE/MFE)
   - Identificar qué dimensiones predicen mejor el éxito

2. **Recalibración periódica** (ej: semanal):
   - Ajustar pesos de las 5 dimensiones mediante regresión o ML
   - Actualizar thresholds de los sub-scores
   - Re-evaluar strategy tier bonuses basados en performance real

3. **Feedback loop**:
   - Trades con score alto pero outcome pobre → investigar qué falló
   - Trades con score bajo pero outcome excelente → identificar blind spots

---

## 5. COMPONENTE 2: RISKALLOCATOR

### 5.1. Responsabilidad

Asignar **riesgo óptimo** a cada operación según Quality Score, budget disponible y constraints de exposición.

### 5.2. Inputs

```python
class RiskAllocationRequest:
    quality_evaluation: QualityEvaluation
    signal_candidate: SignalCandidate
    available_budget: Dict[str, float]  # Por estrategia, símbolo, total
    current_portfolio: PortfolioState
    risk_limits: RiskLimits
```

### 5.3. Restricciones Duras

```python
class RiskLimits:
    # Límite absoluto por idea
    max_risk_per_idea_pct: float = 2.0  # NO NEGOCIABLE
    
    # Límites agregados
    max_total_risk_deployed_pct: float = 10.0  # Max 10% total en riesgo
    max_risk_per_symbol_pct: float = 4.0  # Max 4% en un símbolo (sumando ideas)
    max_risk_per_strategy_pct: float = 5.0  # Max 5% en una estrategia
    max_risk_per_sector_pct: float = 6.0  # Max 6% en un sector (ej: FX majors)
    
    # Correlaciones
    max_correlated_risk_pct: float = 5.0  # Max 5% en posiciones correlacionadas
    
    # Calidad mínima
    min_quality_score: float = 0.50  # Threshold absoluto
```

### 5.4. Mapeo Quality Score → Riesgo Base

Función de mapeo base (antes de ajustes):

```python
def quality_to_base_risk(quality_score: float) -> float:
    """
    Mapea Quality Score a riesgo base mediante función sigmoidea escalada.
    
    Bandas:
    - Score < 0.50 → 0.00% (NO TRADE)
    - Score 0.50-0.70 → 0.25-0.50%
    - Score 0.70-0.85 → 0.50-1.00%
    - Score 0.85-0.95 → 1.00-1.50%
    - Score 0.95-1.00 → 1.50-2.00%
    """
    if quality_score < 0.50:
        return 0.0
    
    # Mapeo no lineal que acelera en quality alta
    adjusted_score = (quality_score - 0.50) / 0.50  # Normalizar [0.5, 1.0] → [0, 1]
    
    # Función sigmoidea para acelerar en quality alta
    risk_pct = 2.0 * (1 / (1 + np.exp(-5 * (adjusted_score - 0.5))))
    
    return min(risk_pct, 2.0)  # Cap a 2%
```

Ejemplos numéricos:
- Score 0.50 → 0.27%
- Score 0.60 → 0.45%
- Score 0.70 → 0.69%
- Score 0.80 → 1.05%
- Score 0.90 → 1.48%
- Score 0.95 → 1.73%
- Score 1.00 → 1.97%

### 5.5. Ajustes por Contexto

El riesgo base se ajusta según:

#### 5.5.1. Disponibilidad de Budget

```python
available_ratio = available_budget['strategy'] / total_capital
if available_ratio < 0.5:  # Budget strategy < 50% del máximo
    risk_adjustment_factor *= 0.7  # Reducir riesgo 30%
```

#### 5.5.2. Exposición Actual

```python
symbol_exposure_ratio = current_exposure[symbol] / max_risk_per_symbol
if symbol_exposure_ratio > 0.7:  # Ya tenemos 70%+ del límite en este símbolo
    risk_adjustment_factor *= (1 - symbol_exposure_ratio)  # Reducir proporcionalmente
```

#### 5.5.3. Correlación con Posiciones Abiertas

```python
correlation_score = calculate_correlation_with_open_positions(signal, portfolio)
if correlation_score > 0.7:  # Alta correlación
    risk_adjustment_factor *= 0.5  # Reducir riesgo 50%
```

#### 5.5.4. Fórmula de Riesgo Final

```
risk_final = min(
    risk_base * risk_adjustment_factor,
    available_budget['strategy'],
    max_risk_per_idea_pct,
    remaining_limits...
)
```

### 5.6. Distribución entre Múltiples Entradas

Cuando una idea tiene múltiples puntos de interés (ej: 3 niveles de liquidez):

```python
def distribute_risk_across_entries(
    total_risk_pct: float,
    entry_points: List[EntryPoint]
) -> List[float]:
    """
    Distribuye riesgo total entre N entry points según calidad relativa.
    """
    # Asignar peso a cada entry según:
    # - Calidad del nivel (ej: orden book depth en ese nivel)
    # - Distancia a SL desde ese entry
    # - Prioridad (ej: entry 1 = setup principal, entry 2-3 = add-ons)
    
    weights = []
    for ep in entry_points:
        weight = (
            0.50 * ep.level_quality_score +
            0.30 * ep.priority_score +
            0.20 * (1 / ep.distance_to_sl_normalized)  # Menor dist = más atractivo
        )
        weights.append(weight)
    
    # Normalizar weights
    total_weight = sum(weights)
    risk_per_entry = [total_risk_pct * (w / total_weight) for w in weights]
    
    return risk_per_entry
```

Ejemplo:
- Idea con Quality Score = 0.88 → risk_base = 1.40%
- 3 entry points → distribución 60/25/15
- Entry 1: 0.84% (60%)
- Entry 2: 0.35% (25%)
- Entry 3: 0.21% (15%)
- **Total**: 1.40% ≤ 2.0% ✓

### 5.7. Output

```python
class RiskAllocation:
    approved: bool
    total_risk_pct: float
    entries: List[EntryRisk]
    rejection_reason: Optional[str]
    adjustments_applied: Dict[str, float]
    
class EntryRisk:
    entry_id: str
    entry_price: float
    sl_price: float
    tp_levels: List[float]
    risk_pct: float
    volume: float  # Calculado como: (capital * risk_pct) / abs(entry - sl)
```

---

## 6. COMPONENTE 3: TRADEMANAGER

### 6.1. Responsabilidad

Diseñar el **execution profile completo** para cada trade aprobado: SL estructural, TPs basados en liquidez, trailing inteligente, parciales, break-even.

### 6.2. Inputs

```python
class TradeSetupRequest:
    risk_allocation: RiskAllocation
    signal_candidate: SignalCandidate
    market_structure: MarketStructure  # Order blocks, liquidez, niveles HTF
    strategy_profile: StrategyProfile  # Histórico MAE/MFE, típicos R-multiples
```

### 6.3. Stop Loss Estructural

**Prohibido ATR. Prohibido distancias fijas.**

El SL se ubica en:

#### 6.3.1. Lógica de Invalidación

```python
def calculate_structural_sl(signal, market_structure):
    """
    SL = donde la idea es INVÁLIDA, no donde duele menos.
    """
    if signal.strategy_type == 'order_block':
        # SL detrás del order block que originó la señal
        sl = market_structure.order_block_origin - buffer_pips
        
    elif signal.strategy_type == 'liquidity_sweep':
        # SL donde el sweep se invalida (retroceso excesivo)
        sl = market_structure.swept_level + invalidation_buffer
        
    elif signal.strategy_type == 'momentum':
        # SL en ruptura de swing bajo (LONG) o swing alto (SHORT)
        sl = market_structure.last_swing_extreme
        
    elif signal.strategy_type == 'mean_reversion':
        # SL en zona de over-extension estadística
        sl = signal.entry_price + (signal.direction * 2.5 * sigma_historical)
        
    # Validar que SL no sea demasiado cercano (slippage risk)
    min_sl_distance_pips = get_min_sl_distance(symbol, spread_current)
    if abs(signal.entry_price - sl) < min_sl_distance_pips:
        sl = signal.entry_price - (signal.direction * min_sl_distance_pips)
        
    return sl
```

#### 6.3.2. Validación de SL vs Riesgo

```python
# Verificar que el riesgo asignado es consistente con SL estructural
sl_distance_pips = abs(entry_price - sl_structural)
implied_volume = (capital * risk_pct) / (sl_distance_pips * pip_value)

if implied_volume < min_volume_broker:
    # SL demasiado lejano para el riesgo asignado
    # OPCIÓN 1: Aumentar riesgo (si quality permite)
    # OPCIÓN 2: Rechazar trade
    # OPCIÓN 3: Ajustar SL a posición estructural más cercana
    pass
    
if implied_volume > max_volume_broker:
    # SL demasiado cercano, riesgo de slippage
    # Reducir riesgo o mover SL a siguiente nivel estructural
    pass
```

### 6.4. Targets (TPs) Basados en Liquidez

TPs alineados con **zonas de toma de liquidez previsible**:

```python
def calculate_structural_tps(signal, market_structure, strategy_profile):
    """
    TPs en zonas de liquidez, no distancias arbitrarias.
    """
    tps = []
    
    # TP1: Primera zona de liquidez relevante
    tp1_candidates = market_structure.get_next_liquidity_zones(
        from_price=signal.entry_price,
        direction=signal.direction,
        min_distance_pips=20,  # Threshold mínimo para evitar TP demasiado cercano
        max_candidates=5
    )
    
    # Elegir TP1 que coincida con:
    # - MFE típico de la estrategia (percentil 60-70)
    # - Primera resistencia/soporte estructural
    mfe_p70 = strategy_profile.get_mfe_percentile(0.70, regime=current_regime)
    tp1 = select_tp_near_mfe(tp1_candidates, mfe_p70, tolerance=0.15)
    tps.append(tp1)
    
    # TP2: Segunda zona (MFE percentil 85-90)
    mfe_p85 = strategy_profile.get_mfe_percentile(0.85, regime=current_regime)
    tp2 = select_tp_near_mfe(
        market_structure.get_next_liquidity_zones(from_price=tp1, ...),
        mfe_p85,
        tolerance=0.20
    )
    tps.append(tp2)
    
    # TP3 (opcional): Extension target para runners
    if quality_score > 0.85 and strategy_supports_runners:
        mfe_p95 = strategy_profile.get_mfe_percentile(0.95, regime=current_regime)
        tp3 = select_tp_near_mfe(..., mfe_p95, tolerance=0.30)
        tps.append(tp3)
    
    return tps
```

### 6.5. Parciales

Distribución de volumen entre TPs:

```python
def calculate_partial_distribution(tps, quality_score, strategy_profile):
    """
    Distribución de parciales según calidad y comportamiento histórico.
    """
    if len(tps) == 2:
        # Esquema básico 2 TPs
        if quality_score < 0.75:
            # Baja-media calidad: asegurar rápido
            return [0.80, 0.20]  # 80% en TP1, 20% runner
        else:
            # Alta calidad: más confianza en extension
            return [0.60, 0.40]  # 60% en TP1, 40% runner
            
    elif len(tps) == 3:
        # Esquema avanzado 3 TPs
        if quality_score < 0.75:
            return [0.70, 0.20, 0.10]  # Conservador
        elif quality_score < 0.90:
            return [0.60, 0.25, 0.15]  # Balanceado
        else:
            return [0.50, 0.30, 0.20]  # Agresivo (más confianza en runners)
    
    # Ajustar según histórico de la estrategia
    if strategy_profile.runner_success_rate > 0.65:
        # Estrategia con buenos runners → aumentar % en TPs lejanos
        pass
    
    return partial_distribution
```

### 6.6. Trailing Stop

**Prohibido trailing basado en ATR.**

Trailing estructural:

```python
def calculate_trailing_rules(signal, market_structure, strategy_profile):
    """
    Trailing basado en nueva estructura formada, no distancia fija.
    """
    trailing_rules = []
    
    # REGLA 1: Tras hit TP1, mover SL a break-even estructural
    trailing_rules.append({
        'trigger': 'TP1_HIT',
        'action': 'MOVE_SL_TO_BE_STRUCTURAL',
        'be_level': calculate_be_structural(signal.entry_price, spread_at_entry)
    })
    
    # REGLA 2: Tras formación de nuevo swing low/high favorable
    trailing_rules.append({
        'trigger': 'NEW_SWING_FORMED',
        'condition': {
            'min_bars_since_entry': 10,
            'swing_confirms_direction': True
        },
        'action': 'MOVE_SL_TO_SWING',
        'buffer_pips': 5  # Buffer pequeño detrás del swing
    })
    
    # REGLA 3: Trailing basado en nuevo order block formado
    if signal.strategy_type in ['order_block', 'liquidity_sweep']:
        trailing_rules.append({
            'trigger': 'NEW_OB_FORMED',
            'condition': {
                'ob_direction': signal.direction,
                'ob_strength': 'medium_or_higher'
            },
            'action': 'MOVE_SL_BEHIND_OB',
            'buffer_pips': 3
        })
    
    # REGLA 4: Trailing por tiempo (si stall prolongado)
    trailing_rules.append({
        'trigger': 'TIME_STALL',
        'condition': {
            'bars_without_progress': 20,  # 20 barras sin avance hacia TP
            'profit_current': '>0.5R'  # Solo si ya hay profit
        },
        'action': 'TIGHTEN_SL',
        'new_sl': 'halfway_between_current_and_entry'
    })
    
    return trailing_rules
```

### 6.7. Break-Even

Break-even NO es automático al +1R:

```python
def calculate_breakeven_rules(signal, strategy_profile):
    """
    Break-even inteligente basado en MAE histórico y estructura.
    """
    mae_distribution = strategy_profile.get_mae_distribution(regime=current_regime)
    
    # Solo mover a BE si:
    # 1. TP1 ejecutado O precio > 1.0R
    # 2. MAE típico de esta estrategia no sugiere retesteo
    # 3. Estructura formada (nuevo swing) protege la entrada
    
    mae_p75 = mae_distribution.percentile(0.75)  # 75% de trades tienen MAE menor
    
    be_rules = {
        'eligible_conditions': [
            'TP1_HIT',  # Opción 1: TP1 ejecutado
            'PROFIT_EXCEEDS_THRESHOLD'  # Opción 2: Profit > threshold
        ],
        'profit_threshold_r': 1.2,  # Debe estar en +1.2R (no +1.0R)
        'additional_checks': [
            'NEW_SWING_FORMED',  # Debe haber confirmación estructural
            f'MAE_CURRENT < {mae_p75}'  # MAE actual no excede típico
        ],
        'be_level': 'entry_price + spread_buffer',
        'spread_buffer_pips': 2  # 2 pips sobre entry para cubrir spread
    }
    
    return be_rules
```

### 6.8. Output

```python
class ExecutionProfile:
    trade_id: str
    entries: List[Entry]
    
class Entry:
    entry_id: str
    entry_price: float
    volume: float
    risk_pct: float
    
    # Stop Loss
    sl_initial: float
    sl_reason: str  # "order_block_invalidation", "swing_break", etc.
    
    # Targets
    tps: List[TP]
    
    # Management rules
    partial_distribution: List[float]
    trailing_rules: List[TrailingRule]
    breakeven_rules: BERule
    
class TP:
    price: float
    volume_pct: float
    reason: str  # "liquidity_zone", "mfe_p70", etc.
```

---

## 7. COMPONENTE 4: EXPOSUREMANAGER

### 7.1. Responsabilidad

Controlar **exposición agregada** y prevenir concentraciones excesivas.

### 7.2. Dimensiones de Control

#### 7.2.1. Por Símbolo

```python
max_risk_per_symbol = 4.0%  # Suma de todos los trades en EURUSD <= 4%
```

#### 7.2.2. Por Estrategia

```python
max_risk_per_strategy = 5.0%  # Suma de trades de momentum_quality <= 5%
```

#### 7.2.3. Por Dirección

```python
max_directional_imbalance = 6.0%  # Max 6% neto LONG en FX
```

#### 7.2.4. Por Factor

```python
# Factores macro: USD strength, risk-on/risk-off, commodity correlation
max_risk_per_factor = 6.0%

# Ejemplo: Si tengo EURUSD short + GBPUSD short + USDJPY long
# → Factor = "USD strength" → suma = X%
```

#### 7.2.5. Por Correlación

```python
# Detectar trades correlacionados (misma narrativa macro, misma dirección)
max_correlated_risk = 5.0%

# Ejemplo: EURUSD LONG + GBPUSD LONG correlación = 0.85
# → Limitar suma de ambos a 5%
```

### 7.3. Matriz de Correlaciones

El ExposureManager mantiene matriz de correlaciones:

```python
class CorrelationMatrix:
    # Correlación rolling de returns entre pares
    symbol_correlation: Dict[Tuple[str, str], float]
    
    # Mapping símbolo → factores macro
    factor_exposure: Dict[str, List[str]]
    # Ej: 'EURUSD' → ['USD_strength', 'EUR_weakness', 'risk_on']
    
    def get_correlation_with_portfolio(self, new_signal: Signal) -> float:
        """
        Calcula correlación del nuevo signal con cartera actual.
        """
        portfolio_positions = self.get_open_positions()
        
        correlation_scores = []
        for pos in portfolio_positions:
            if pos.symbol == new_signal.symbol:
                # Mismo símbolo, misma dirección
                if pos.direction == new_signal.direction:
                    correlation_scores.append(1.0)  # Perfecta correlación
                else:
                    correlation_scores.append(-1.0)  # Anti-correlación
            else:
                # Símbolos diferentes, consultar matriz histórica
                corr = self.symbol_correlation.get((pos.symbol, new_signal.symbol), 0.0)
                
                # Ajustar por dirección
                if pos.direction != new_signal.direction:
                    corr *= -1
                    
                correlation_scores.append(corr)
        
        # Correlación media ponderada por risk de cada posición
        weighted_corr = np.average(
            correlation_scores,
            weights=[p.risk_pct for p in portfolio_positions]
        )
        
        return weighted_corr
```

### 7.4. Flujo de Verificación

Antes de aprobar un trade:

```python
def check_exposure_constraints(new_trade: RiskAllocation) -> ExposureCheck:
    """
    Verifica todas las constraints de exposición.
    """
    checks = []
    
    # Check 1: Símbolo
    current_symbol_risk = sum_risk_in_symbol(new_trade.symbol)
    if current_symbol_risk + new_trade.total_risk_pct > max_risk_per_symbol:
        checks.append({
            'constraint': 'symbol_limit',
            'violated': True,
            'reduction_required': (current_symbol_risk + new_trade.total_risk_pct) - max_risk_per_symbol
        })
    
    # Check 2: Estrategia
    current_strategy_risk = sum_risk_in_strategy(new_trade.strategy_name)
    if current_strategy_risk + new_trade.total_risk_pct > max_risk_per_strategy:
        checks.append({...})
    
    # Check 3: Dirección
    current_directional_risk = sum_risk_in_direction(new_trade.direction)
    if current_directional_risk + new_trade.total_risk_pct > max_directional_imbalance:
        checks.append({...})
    
    # Check 4: Factor
    factors = get_factors_for_symbol(new_trade.symbol, new_trade.direction)
    for factor in factors:
        current_factor_risk = sum_risk_in_factor(factor)
        if current_factor_risk + new_trade.total_risk_pct > max_risk_per_factor:
            checks.append({...})
    
    # Check 5: Correlación
    correlation_score = correlation_matrix.get_correlation_with_portfolio(new_trade)
    if correlation_score > 0.7:  # Alta correlación
        correlated_risk = sum_correlated_risk(new_trade, correlation_score)
        if correlated_risk > max_correlated_risk:
            checks.append({...})
    
    # Decisión
    if any(check['violated'] for check in checks):
        return ExposureCheck(
            approved=False,
            violations=checks,
            suggested_action='REDUCE_RISK' or 'REJECT'
        )
    else:
        return ExposureCheck(approved=True, violations=[])
```

### 7.5. Output

```python
class ExposureCheck:
    approved: bool
    violations: List[Dict]
    suggested_action: Optional[str]  # 'REDUCE_RISK', 'REJECT', None
    max_allowable_risk_pct: Optional[float]  # Si reduce, cuánto máximo
```

---

## 8. FLUJOS DE DATOS

### 8.1. Flujo Completo: Signal → Execution

```
┌─────────────────┐
│  SIGNAL ARRIVES │
│   (Strategy)    │
└────────┬────────┘
         │
         ↓
┌─────────────────────────────────────┐
│  STEP 1: QualityScorer              │
│  - Evalúa 5 dimensiones             │
│  - Emite Quality Score [0-1]        │
│  - Flags de warnings                │
└────────┬────────────────────────────┘
         │
         ↓
┌─────────────────────────────────────┐
│  STEP 2: ExposureManager            │
│  - Verifica constraints              │
│  - Calcula correlaciones             │
│  - Devuelve APPROVED o REJECTED      │
└────────┬────────────────────────────┘
         │
         ↓ (si APPROVED)
┌─────────────────────────────────────┐
│  STEP 3: RiskAllocator              │
│  - Mapea Score → Riesgo base        │
│  - Aplica ajustes (budget, exposure)│
│  - Distribuye entre entries         │
│  - Calcula volumes                   │
└────────┬────────────────────────────┘
         │
         ↓
┌─────────────────────────────────────┐
│  STEP 4: TradeManager               │
│  - SL estructural                    │
│  - TPs basados en liquidez           │
│  - Trailing rules                    │
│  - Breakeven rules                   │
│  - Parciales distribution            │
└────────┬────────────────────────────┘
         │
         ↓
┌─────────────────────────────────────┐
│  EXECUTION DECISION                  │
│  - ExecutionProfile completo         │
│  - Ready para enviar a broker        │
└─────────────────────────────────────┘
```

### 8.2. Flujo Post-Trade: Learning Loop

```
┌─────────────────┐
│  TRADE CLOSED   │
└────────┬────────┘
         │
         ↓
┌─────────────────────────────────────┐
│  OUTCOME CAPTURE                     │
│  - Final P&L (€ y R-multiple)        │
│  - MAE (Maximum Adverse Excursion)   │
│  - MFE (Maximum Favorable Excursion) │
│  - Path del precio (SL hits, TP hits)│
│  - Duration (bars, time)             │
└────────┬────────────────────────────┘
         │
         ↓
┌─────────────────────────────────────┐
│  MemoryStore.record()                │
│  - Asocia outcome con Quality Score  │
│  - Asocia con inputs originales      │
│  - Actualiza estadísticas estrategia │
└────────┬────────────────────────────┘
         │
         ↓
┌─────────────────────────────────────┐
│  ANALYSIS & CALIBRATION              │
│  - Score-to-outcome correlation      │
│  - Ajustar pesos de dimensiones      │
│  - Actualizar strategy tiers         │
│  - Refinar SL/TP heuristics          │
└─────────────────────────────────────┘
```

---

## 9. INTERFACES DE INTEGRACIÓN

### 9.1. Integración con Estrategias

Las estrategias deben enviar señales enriquecidas:

```python
# En strategy.evaluate()
signal = InstitutionalSignal(
    strategy_name=self.name,
    symbol=symbol,
    direction='LONG',
    entry_price=entry_price,
    
    # NUEVO: Información estructural
    sl_structural=self.calculate_structural_sl(market_data),
    tp_suggested=self.calculate_structural_tps(market_data),
    
    # NUEVO: Información de calidad
    signal_strength=z_score,  # Interna de estrategia
    distance_to_threshold=(z_score - self.threshold) / (max_z - self.threshold),
    confluence_factors=['HTF_aligned', 'OFI_confirmation', 'VPIN_clean'],
    
    # Contexto estrategia
    regime_required=['TREND_STRONG_UP', 'BREAKOUT_MOMENTUM'],
    min_quality_score=0.65,  # Threshold mínimo que acepta la estrategia
)
```

### 9.2. Integración con Arbiter

El Arbiter debe consultar Risk Engine antes de decisión final:

```python
# En conflict_arbiter.py
def arbitrate(signals, market_context):
    # 1. Seleccionar mejor señal (lógica actual)
    best_signal = self._select_best_signal(signals)
    
    # 2. NUEVO: Evaluar con Risk Engine
    risk_evaluation = RISK_ENGINE.evaluate_signal(
        signal=best_signal,
        market_context=market_context,
        portfolio_state=self.get_portfolio_state()
    )
    
    if not risk_evaluation.approved:
        logger.warning(f"RISK_REJECTED: {risk_evaluation.rejection_reason}")
        return SILENCE
    
    # 3. Devolver señal con execution profile adjunto
    best_signal.execution_profile = risk_evaluation.execution_profile
    return best_signal
```

### 9.3. Integración con Brain-Layer (Mandato 3)

Cuando el brain-layer esté operativo, puede influir en Quality Score:

```python
# En QualityScorer.calculate()
def calculate_quality_score(signal, context):
    # ... cálculo base de 5 dimensiones ...
    
    # HOOK: Brain-layer adjustment
    if BRAIN_LAYER_AVAILABLE:
        brain_adjustment = brain_layer.evaluate_signal_meta(
            signal=signal,
            base_quality_score=base_score,
            recent_performance=self.strategy_performance[signal.strategy_name]
        )
        
        # Brain puede ajustar ±0.10 el score basado en memoria y aprendizaje
        final_score = np.clip(base_score + brain_adjustment, 0.0, 1.0)
    else:
        final_score = base_score
    
    return final_score
```

### 9.4. Integración con DecisionLedger

Cada decisión de riesgo debe registrarse:

```python
# En RiskAllocator.allocate()
def allocate_risk(signal, quality_eval):
    # ... lógica de asignación ...
    
    # Registrar decisión
    decision_uid = generate_decision_uid(signal)
    DECISION_LEDGER.write(
        decision_uid=decision_uid,
        payload={
            'signal_id': signal.id,
            'quality_score': quality_eval.score,
            'quality_breakdown': quality_eval.breakdown,
            'risk_allocated_pct': risk_final,
            'risk_adjustments': adjustments_applied,
            'exposure_checks': exposure_checks,
            'timestamp': datetime.now().isoformat()
        }
    )
```

---

## 10. SISTEMA DE MEMORIA Y APRENDIZAJE

### 10.1. Trade Record Schema

Cada trade genera un registro completo:

```python
class TradeRecord:
    # Identificación
    trade_id: str
    strategy_name: str
    symbol: str
    direction: str
    
    # Pre-trade
    quality_score: float
    quality_breakdown: Dict[str, float]
    risk_allocated_pct: float
    entries: List[EntryRecord]
    
    # During-trade
    entry_fills: List[Fill]
    sl_adjustments: List[SLAdjustment]
    tp_fills: List[Fill]
    max_adverse_excursion_pct: float  # MAE
    max_favorable_excursion_pct: float  # MFE
    duration_bars: int
    duration_minutes: int
    
    # Post-trade
    final_pnl_eur: float
    final_r_multiple: float
    outcome: Literal['WIN', 'LOSS', 'BE']
    exit_reason: str  # 'TP_HIT', 'SL_HIT', 'TRAILING_EXIT', 'TIME_EXIT'
    
    # Context snapshot
    regime_at_entry: str
    vpin_at_entry: float
    spread_at_entry_bps: float
    portfolio_exposure_at_entry: Dict
```

### 10.2. Análisis Periódico

Cada semana/mes, análisis de calibración:

```python
def calibrate_risk_engine(trade_history: List[TradeRecord]):
    """
    Análisis de calidad predictiva del Quality Score.
    """
    # 1. Correlación Score vs Outcome
    scores = [t.quality_score for t in trade_history]
    outcomes = [t.final_r_multiple for t in trade_history]
    
    correlation = np.corrcoef(scores, outcomes)[0, 1]
    logger.info(f"Score-Outcome correlation: {correlation:.3f}")
    
    # 2. Análisis por banda de score
    for band in [(0.5, 0.7), (0.7, 0.85), (0.85, 0.95), (0.95, 1.0)]:
        trades_in_band = [t for t in trade_history if band[0] <= t.quality_score < band[1]]
        
        win_rate = len([t for t in trades_in_band if t.outcome == 'WIN']) / len(trades_in_band)
        avg_r = np.mean([t.final_r_multiple for t in trades_in_band])
        
        logger.info(f"Band {band}: WR={win_rate:.2%}, Avg R={avg_r:.2f}")
    
    # 3. Ajustar pesos de dimensiones
    # Regresión para encontrar qué dimensiones predicen mejor
    X = np.array([[t.quality_breakdown[dim] for dim in DIMENSIONS] for t in trade_history])
    y = np.array([1 if t.outcome == 'WIN' else 0 for t in trade_history])
    
    model = LogisticRegression()
    model.fit(X, y)
    
    new_weights = normalize(np.abs(model.coef_[0]))
    logger.info(f"Suggested dimension weights: {dict(zip(DIMENSIONS, new_weights))}")
    
    # 4. Identificar estrategias que sobreprometen
    for strategy in STRATEGIES:
        strat_trades = [t for t in trade_history if t.strategy_name == strategy]
        avg_score = np.mean([t.quality_score for t in strat_trades])
        avg_outcome = np.mean([t.final_r_multiple for t in strat_trades])
        
        score_outcome_ratio = avg_outcome / avg_score
        
        if score_outcome_ratio < 0.5:
            logger.warning(f"STRATEGY_OVERPROMISE: {strategy} scores high but delivers low")
```

### 10.3. Hooks para Brain-Layer

Cuando brain-layer esté activo, puede:

1. **Ajustar Quality Score dinámicamente** basado en patrones no obvios
2. **Sugerir risk adjustments** más allá de reglas fijas
3. **Identificar regímenes emergentes** donde calibración es obsoleta
4. **Detectar anomalías** (strategy decay, regime shift, data quality issues)

---

## CONCLUSIÓN

Este Risk Engine es la **columna vertebral institucional** del sistema. Cada operación queda definida con precisión matemática: calidad medida, riesgo calculado, stops estructurales, targets en liquidez, trailing inteligente.

**Nada retail. Nada aleatorio. Solo lógica perfecta.**

---

**Próximos pasos**:
1. Revisar y aprobar diseño
2. Implementar componentes en orden: QualityScorer → RiskAllocator → TradeManager → ExposureManager
3. Integrar con estrategias y arbiter
4. Testing exhaustivo con backtesting histórico
5. Deploy gradual con monitoring intensivo

**Ref**: MANDATO 4 - Risk Manager institucional
