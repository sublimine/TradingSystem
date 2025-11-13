# RISK EXECUTION PROFILES – QUALITY SCORE Y GESTIÓN DE OPERACIONES

**Sistema**: TradingSystem
**Fecha**: 2025-11-13
**Mandato**: MANDATO 4 - Risk Manager institucional
**Estado**: Diseño completo - Fase 1

---

## ÍNDICE

1. [Sistema de Quality Score](#1-sistema-de-quality-score)
2. [Mapeo Score a Riesgo](#2-mapeo-score-a-riesgo)
3. [Perfiles de Ejecución por Estrategia](#3-perfiles-de-ejecución-por-estrategia)
4. [SL/TP Estructural sin ATR](#4-sltp-estructural-sin-atr)
5. [Trailing y Break-Even Inteligente](#5-trailing-y-break-even-inteligente)
6. [Ejemplos Completos](#6-ejemplos-completos)
7. [Calibración y Aprendizaje](#7-calibración-y-aprendizaje)

---

## 1. SISTEMA DE QUALITY SCORE

### 1.1. Fórmula Completa

```python
Quality_Score = (
    0.25 * pedigree_score +      # Histórico estrategia
    0.25 * signal_score +         # Fuerza señal actual
    0.20 * microstructure_score + # Liquidez y spread
    0.15 * data_health_score +    # Calidad datos
    0.15 * portfolio_score        # Exposición actual
)
```

### 1.2. Cálculo Detallado por Dimensión

#### Dimensión 1: Pedigrí (0.25)

```python
def calculate_pedigree_score(strategy_name, regime):
    """
    Evalúa calidad histórica de la estrategia.
    """
    # Obtener métricas de performance store
    perf = PERFORMANCE_STORE.get_strategy_stats(
        strategy=strategy_name,
        regime=regime,
        lookback_days=90
    )

    # Normalizar Sharpe a [0, 1]
    # Sharpe 0 → 0.0, Sharpe 2.0 → 0.8, Sharpe 3.0+ → 1.0
    sharpe_norm = min(perf.sharpe_ratio / 3.0, 1.0)

    # Hit rate directo [0, 1]
    hit_rate = perf.win_rate

    # Normalizar Calmar (return/max_dd)
    # Calmar 0.5 → 0.0, Calmar 2.0 → 0.7, Calmar 4.0+ → 1.0
    calmar_norm = min((perf.calmar_ratio - 0.5) / 3.5, 1.0)

    # Bonus por tier
    tier_bonus = {
        'ofi_refinement': 0.20,
        'spoofing_l2': 0.20,
        'vpin_reversal': 0.20,
        'momentum_quality': 0.10,
        'liquidity_sweep': 0.10,
        'order_block_institutional': 0.10
    }.get(strategy_name, 0.0)

    pedigree = (
        0.40 * sharpe_norm +
        0.30 * hit_rate +
        0.20 * calmar_norm +
        0.10 * tier_bonus
    )

    return pedigree
```

#### Dimensión 2: Fuerza de Señal (0.25)

```python
def calculate_signal_score(signal, regime, fit_matrix):
    """
    Evalúa fuerza de la señal actual.
    """
    # 1. Strength interna de estrategia normalizada
    # Cada estrategia debe proveer signal_strength [0, 1]
    strength_norm = signal.signal_strength

    # 2. Distance to threshold
    # Si threshold = 0.6 y strength = 0.9 → (0.9-0.6)/(1-0.6) = 0.75
    threshold = signal.min_threshold or 0.6
    if signal.signal_strength < threshold:
        distance_score = 0.0
    else:
        distance_score = (signal.signal_strength - threshold) / (1.0 - threshold)

    # 3. Confluence score
    max_confluences = 5  # HTF, LTF, OFI, VPIN, volume
    confluence_score = len(signal.confluence_factors) / max_confluences

    # 4. Regime fit
    regime_fit = fit_matrix.get(regime, {}).get(signal.strategy_name, 0.7)

    signal_score = (
        0.35 * strength_norm +
        0.25 * distance_score +
        0.20 * confluence_score +
        0.20 * regime_fit
    )

    return signal_score
```

#### Dimensión 3: Microestructura (0.20)

```python
def calculate_microstructure_score(market_context, symbol):
    """
    Evalúa condiciones de microestructura.
    """
    # 1. Spread normalizado (menor = mejor)
    typical_spread = MARKET_DATA.get_typical_spread(symbol)
    current_spread = market_context.spread_bps
    spread_norm = 1.0 - min(current_spread / (typical_spread * 2.0), 1.0)

    # 2. Depth score [0, 1] (del order book o proxy)
    depth_score = market_context.depth_score

    # 3. VPIN quality
    vpin = market_context.vpin
    if vpin < 0.30:
        vpin_quality = 1.0  # Clean flow
    elif vpin < 0.50:
        vpin_quality = 0.5  # Neutral
    else:
        vpin_quality = 0.0  # Toxic

    micro_score = (
        0.40 * spread_norm +
        0.30 * depth_score +
        0.30 * vpin_quality
    )

    return micro_score
```

#### Dimensión 4: Data Health (0.15)

```python
def calculate_data_health_score(signal, market_context):
    """
    Evalúa sanidad de datos y modelo.
    """
    # 1. Completitud (sin NaNs)
    features = signal.features
    total_features = len(features)
    valid_features = sum(1 for v in features.values() if not np.isnan(v))
    completeness = valid_features / total_features

    # 2. Sanity check (sin outliers extremos)
    outliers_detected = 0
    for key, value in features.items():
        historical_dist = FEATURE_STORE.get_distribution(key, lookback=30)
        z_score = (value - historical_dist.mean) / historical_dist.std
        if abs(z_score) > 5.0:
            outliers_detected += 1

    sanity = 1.0 - (outliers_detected / total_features)

    # 3. Consistencia entre módulos
    # Verificar que features, gatekeepers y strategy estén alineados
    gatekeeper_pass = all(g.passed for g in signal.gatekeeper_results)
    consistency = 1.0 if gatekeeper_pass else 0.5

    health_score = (
        0.50 * completeness +
        0.30 * sanity +
        0.20 * consistency
    )

    return health_score
```

#### Dimensión 5: Portfolio Position (0.15)

```python
def calculate_portfolio_score(signal, portfolio_state):
    """
    Evalúa impacto de exposición actual.
    """
    # 1. Exposure ratio en símbolo
    current_exposure = portfolio_state.get_exposure(symbol=signal.symbol)
    max_exposure = RISK_LIMITS.max_risk_per_symbol_pct
    exposure_ratio = current_exposure / max_exposure
    exposure_component = 1.0 - exposure_ratio

    # 2. Correlation penalty
    correlation = CORRELATION_MATRIX.get_correlation_with_portfolio(signal)

    if correlation < 0.3:
        correlation_penalty = 0.0  # Baja correlación = bueno
    elif correlation < 0.7:
        correlation_penalty = 0.3  # Media correlación
    else:
        correlation_penalty = 0.7  # Alta correlación = malo

    correlation_component = 1.0 - correlation_penalty

    portfolio_score = (
        0.50 * exposure_component +
        0.50 * correlation_component
    )

    return portfolio_score
```

### 1.3. Ejemplos Numéricos

**Ejemplo 1: Señal de Alta Calidad**
```
Strategy: momentum_quality (Tier 2)
Regime: TREND_STRONG_UP
Sharpe: 2.8, Hit rate: 0.68, Calmar: 3.2

Pedigrí:
- sharpe_norm: 2.8/3.0 = 0.93
- hit_rate: 0.68
- calmar_norm: (3.2-0.5)/3.5 = 0.77
- tier_bonus: 0.10
→ pedigree_score = 0.40*0.93 + 0.30*0.68 + 0.20*0.77 + 0.10*0.10 = 0.79

Signal:
- strength: 0.88
- distance_to_threshold: (0.88-0.60)/(1-0.60) = 0.70
- confluence: 4/5 = 0.80
- regime_fit: 1.0 (momentum en TREND_STRONG = perfecto)
→ signal_score = 0.35*0.88 + 0.25*0.70 + 0.20*0.80 + 0.20*1.0 = 0.84

Microstructure:
- spread_norm: 0.85 (spread apretado)
- depth_score: 0.75
- vpin_quality: 1.0 (VPIN = 0.25)
→ micro_score = 0.40*0.85 + 0.30*0.75 + 0.30*1.0 = 0.87

Data Health:
- completeness: 1.0
- sanity: 0.95
- consistency: 1.0
→ health_score = 0.50*1.0 + 0.30*0.95 + 0.20*1.0 = 0.99

Portfolio:
- exposure_ratio: 0.15 (15% de límite usado)
- correlation: 0.25 (baja)
→ portfolio_score = 0.50*(1-0.15) + 0.50*(1-0.0) = 0.93

QUALITY SCORE FINAL:
= 0.25*0.79 + 0.25*0.84 + 0.20*0.87 + 0.15*0.99 + 0.15*0.93
= 0.1975 + 0.21 + 0.174 + 0.1485 + 0.1395
= 0.8695 ≈ 0.87 (ALTA CALIDAD)
```

**Ejemplo 2: Señal Rechazada (Baja Calidad)**
```
Strategy: nueva_estrategia_test (Tier 3)
Regime: RANGING_HIGH_VOL
Sharpe: 0.8, Hit rate: 0.48, Calmar: 0.9

Pedigrí:
- sharpe_norm: 0.8/3.0 = 0.27
- hit_rate: 0.48
- calmar_norm: (0.9-0.5)/3.5 = 0.11
- tier_bonus: 0.00
→ pedigree_score = 0.40*0.27 + 0.30*0.48 + 0.20*0.11 + 0.10*0.0 = 0.27

Signal:
- strength: 0.65
- distance_to_threshold: (0.65-0.60)/(1-0.60) = 0.13
- confluence: 1/5 = 0.20
- regime_fit: 0.40 (mal fit para este régimen)
→ signal_score = 0.35*0.65 + 0.25*0.13 + 0.20*0.20 + 0.20*0.40 = 0.39

Microstructure:
- spread_norm: 0.30 (spread amplio)
- depth_score: 0.45
- vpin_quality: 0.0 (VPIN = 0.62, tóxico)
→ micro_score = 0.40*0.30 + 0.30*0.45 + 0.30*0.0 = 0.26

Data Health:
- completeness: 0.85 (algunos NaNs)
- sanity: 0.70 (1 outlier detectado)
- consistency: 0.50 (gatekeeper warnings)
→ health_score = 0.50*0.85 + 0.30*0.70 + 0.20*0.50 = 0.74

Portfolio:
- exposure_ratio: 0.75 (75% límite usado)
- correlation: 0.85 (alta correlación)
→ portfolio_score = 0.50*(1-0.75) + 0.50*(1-0.7) = 0.28

QUALITY SCORE FINAL:
= 0.25*0.27 + 0.25*0.39 + 0.20*0.26 + 0.15*0.74 + 0.15*0.28
= 0.0675 + 0.0975 + 0.052 + 0.111 + 0.042
= 0.37 (RECHAZADA - por debajo de threshold 0.50)
```

---

## 2. MAPEO SCORE A RIESGO

### 2.1. Función de Mapeo

```python
def quality_to_risk(quality_score: float) -> float:
    """
    Mapea Quality Score [0, 1] a riesgo % [0, 2.0].
    Función sigmoidea escalada para acelerar en quality alta.
    """
    if quality_score < 0.50:
        return 0.0  # NO TRADE

    # Normalizar score a [0, 1] desde [0.5, 1.0]
    adjusted = (quality_score - 0.50) / 0.50

    # Sigmoidea: más agresiva en quality alta
    risk_pct = 2.0 * (1 / (1 + np.exp(-5 * (adjusted - 0.5))))

    return min(risk_pct, 2.0)
```

### 2.2. Tabla de Referencia

| Quality Score | Risk Base | Banda       | Descripción              |
|---------------|-----------|-------------|--------------------------|
| < 0.50        | 0.00%     | NO TRADE    | Rechazado                |
| 0.50          | 0.27%     | Bajo        | Calidad mínima aceptable |
| 0.55          | 0.36%     | Bajo        | Calidad baja-media       |
| 0.60          | 0.45%     | Bajo        | Calidad media            |
| 0.65          | 0.57%     | Medio-bajo  | Calidad media-alta       |
| 0.70          | 0.69%     | Medio       | Calidad buena            |
| 0.75          | 0.84%     | Medio-alto  | Calidad muy buena        |
| 0.80          | 1.05%     | Alto        | Calidad alta             |
| 0.85          | 1.30%     | Alto        | Calidad muy alta         |
| 0.90          | 1.48%     | Muy alto    | Calidad excelente        |
| 0.95          | 1.73%     | Máximo      | Calidad excepcional      |
| 1.00          | 1.97%     | Máximo      | Calidad perfecta (teórica)|

### 2.3. Ajustes Post-Mapeo

El riesgo base se ajusta por:

```python
def apply_risk_adjustments(risk_base, signal, portfolio):
    """
    Ajusta riesgo base según contexto.
    """
    adjustment_factor = 1.0
    adjustments_log = {}

    # Ajuste 1: Budget disponible
    budget_ratio = get_available_budget(signal.strategy_name) / TOTAL_CAPITAL
    if budget_ratio < 0.5:
        adj = 0.7
        adjustment_factor *= adj
        adjustments_log['budget_constraint'] = adj

    # Ajuste 2: Exposición símbolo
    symbol_exposure_ratio = portfolio.get_exposure(signal.symbol) / MAX_SYMBOL_EXPOSURE
    if symbol_exposure_ratio > 0.7:
        adj = 1.0 - symbol_exposure_ratio
        adjustment_factor *= adj
        adjustments_log['symbol_exposure'] = adj

    # Ajuste 3: Correlación
    correlation = get_correlation_with_portfolio(signal, portfolio)
    if correlation > 0.7:
        adj = 0.5
        adjustment_factor *= adj
        adjustments_log['high_correlation'] = adj

    # Ajuste 4: Volatilidad extrema
    vol_percentile = signal.volatility_percentile
    if vol_percentile > 0.95:  # Volatilidad en top 5%
        adj = 0.8
        adjustment_factor *= adj
        adjustments_log['extreme_volatility'] = adj

    risk_adjusted = risk_base * adjustment_factor

    # Hard cap
    risk_final = min(risk_adjusted, MAX_RISK_PER_IDEA)

    return risk_final, adjustments_log
```

---

## 3. PERFILES DE EJECUCIÓN POR ESTRATEGIA

Cada familia de estrategias tiene un perfil de ejecución característico.

### 3.1. Order Flow Strategies (OFI, VPIN, Spoofing)

**Características:**
- Alta frecuencia de señales
- Holding periods cortos (minutos a pocas horas)
- SL ajustados (invalidación rápida)
- TPs en zonas de liquidez cercanas

**Profile:**
```python
ORDER_FLOW_PROFILE = {
    'sl_logic': 'microstructure_invalidation',
    'sl_typical_distance_pips': (8, 15),  # Rango típico
    'tp_count': 2,
    'tp_logic': 'nearest_liquidity_zones',
    'partial_distribution': [0.70, 0.30],  # 70% TP1, 30% runner
    'trailing_trigger': 'TP1_HIT',
    'breakeven_threshold_r': 1.5,
    'max_holding_bars': 50,
    'timeout_action': 'close_at_market'
}
```

### 3.2. Momentum Strategies

**Características:**
- Tendencias establecidas
- Holding periods medios (horas a días)
- SL en swings estructurales
- TPs en múltiples objetivos (runners frecuentes)

**Profile:**
```python
MOMENTUM_PROFILE = {
    'sl_logic': 'swing_break',
    'sl_typical_distance_pips': (20, 40),
    'tp_count': 3,
    'tp_logic': 'structure_levels_htf',
    'partial_distribution': [0.50, 0.30, 0.20],  # Agresivo con runners
    'trailing_trigger': 'NEW_SWING_FORMED',
    'trailing_buffer_pips': 5,
    'breakeven_threshold_r': 1.2,
    'breakeven_requires_swing': True,
    'max_holding_bars': 200
}
```

### 3.3. Mean Reversion Strategies

**Características:**
- Extremos estadísticos
- Holding periods cortos-medios
- SL en invalidación estadística (ej: 2.5 sigma)
- TPs conservadores (regreso a media)

**Profile:**
```python
MEAN_REVERSION_PROFILE = {
    'sl_logic': 'statistical_invalidation',
    'sl_distance_sigma': 2.5,
    'tp_count': 2,
    'tp_logic': 'mean_reversion_targets',  # Media móvil, bandas, etc.
    'partial_distribution': [0.80, 0.20],  # Conservador
    'trailing_trigger': 'NONE',  # No trailing típicamente
    'breakeven_threshold_r': 1.0,  # Rápido a BE
    'max_holding_bars': 100,
    'timeout_action': 'close_at_profit_if_any'
}
```

### 3.4. Liquidity Sweep Strategies

**Características:**
- Setup específico (hunt + reversal)
- Holding variable
- SL detrás de swept level
- TPs en zonas de liquidez opuestas

**Profile:**
```python
LIQUIDITY_SWEEP_PROFILE = {
    'sl_logic': 'swept_level_invalidation',
    'sl_buffer_pips': 5,
    'tp_count': 2,
    'tp_logic': 'opposing_liquidity_zones',
    'partial_distribution': [0.60, 0.40],
    'trailing_trigger': 'TP1_HIT_AND_NEW_OB',
    'trailing_buffer_pips': 3,
    'breakeven_threshold_r': 1.3,
    'max_holding_bars': 150
}
```

---

## 4. SL/TP ESTRUCTURAL SIN ATR

### 4.1. Stop Loss por Tipo de Setup

#### Order Block

```python
def calculate_ob_sl(signal, market_structure):
    """
    SL detrás del order block que genera la señal.
    """
    ob_origin = market_structure.order_blocks[-1]  # Último OB relevante

    if signal.direction == 'LONG':
        # SL debajo del low del order block
        sl = ob_origin.low - BUFFER_PIPS[signal.symbol]
    else:
        # SL encima del high del order block
        sl = ob_origin.high + BUFFER_PIPS[signal.symbol]

    # Validar distancia mínima
    min_distance = get_min_sl_distance(signal.symbol)
    actual_distance = abs(signal.entry_price - sl)

    if actual_distance < min_distance:
        logger.warning(f"SL too tight: {actual_distance} pips < {min_distance}")
        sl = signal.entry_price - (signal.direction_multiplier * min_distance)

    return sl, "order_block_invalidation"
```

#### Liquidity Sweep

```python
def calculate_sweep_sl(signal, market_structure):
    """
    SL donde el sweep se invalida (retroceso excesivo).
    """
    swept_level = signal.swept_level_price

    if signal.direction == 'LONG':
        # Si LONG tras sweep de low, SL debajo del swept low
        sl = swept_level - INVALIDATION_BUFFER[signal.symbol]
    else:
        # Si SHORT tras sweep de high, SL encima del swept high
        sl = swept_level + INVALIDATION_BUFFER[signal.symbol]

    return sl, "sweep_invalidation"
```

#### Momentum Breakout

```python
def calculate_momentum_sl(signal, market_structure):
    """
    SL en último swing antes del breakout.
    """
    if signal.direction == 'LONG':
        # Último swing low antes del breakout
        sl = market_structure.get_last_swing_low()
    else:
        # Último swing high antes del breakout
        sl = market_structure.get_last_swing_high()

    # Buffer pequeño
    sl = sl - (signal.direction_multiplier * 3)  # 3 pips buffer

    return sl, "swing_break"
```

#### Mean Reversion

```python
def calculate_mean_reversion_sl(signal, statistical_context):
    """
    SL en over-extension estadística (ej: 2.5 sigma).
    """
    mean = statistical_context.mean_price
    sigma = statistical_context.std_dev

    if signal.direction == 'LONG':
        # Estamos comprando oversold, SL en over-oversold extremo
        sl = signal.entry_price - (2.5 * sigma)
    else:
        # Estamos vendiendo overbought, SL en over-overbought extremo
        sl = signal.entry_price + (2.5 * sigma)

    return sl, "statistical_invalidation"
```

### 4.2. Take Profit Estructural

```python
def calculate_structural_tps(signal, market_structure, strategy_profile):
    """
    TPs en zonas de liquidez y MFE histórico.
    """
    tps = []

    # Obtener zonas de liquidez en dirección del trade
    liquidity_zones = market_structure.get_liquidity_zones(
        direction=signal.direction,
        min_distance_pips=20,
        max_count=5
    )

    # TP1: Percentil 60-70 de MFE + primera liquidez
    mfe_p70 = strategy_profile.get_mfe_percentile(0.70, regime=signal.regime)
    target_price_mfe = signal.entry_price + (signal.direction_multiplier * mfe_p70)

    # Buscar zona de liquidez más cercana a target MFE
    tp1_candidates = [lz for lz in liquidity_zones
                      if abs(lz.price - target_price_mfe) < 0.0015]  # ~15 pips tolerance

    if tp1_candidates:
        tp1 = min(tp1_candidates, key=lambda lz: abs(lz.price - target_price_mfe))
        tps.append({
            'price': tp1.price,
            'reason': f"liquidity_zone + mfe_p70",
            'volume_pct': 0.60
        })
    else:
        # Si no hay liquidez cercana, usar MFE directo
        tps.append({
            'price': target_price_mfe,
            'reason': "mfe_p70",
            'volume_pct': 0.60
        })

    # TP2: Percentil 85 de MFE + segunda liquidez
    mfe_p85 = strategy_profile.get_mfe_percentile(0.85, regime=signal.regime)
    target_price_mfe2 = signal.entry_price + (signal.direction_multiplier * mfe_p85)

    remaining_zones = [lz for lz in liquidity_zones if lz.price != tps[0]['price']]
    tp2_candidates = [lz for lz in remaining_zones
                      if abs(lz.price - target_price_mfe2) < 0.0025]

    if tp2_candidates:
        tp2 = min(tp2_candidates, key=lambda lz: abs(lz.price - target_price_mfe2))
        tps.append({
            'price': tp2.price,
            'reason': f"liquidity_zone + mfe_p85",
            'volume_pct': 0.40
        })
    else:
        tps.append({
            'price': target_price_mfe2,
            'reason': "mfe_p85",
            'volume_pct': 0.40
        })

    return tps
```

---

## 5. TRAILING Y BREAK-EVEN INTELIGENTE

### 5.1. Trailing Estructural

```python
class TrailingManager:
    """
    Gestiona trailing stops basado en estructura, no ATR.
    """

    def evaluate_trailing(self, trade, current_market_data):
        """
        Evalúa si mover trailing según reglas estructurales.
        """
        for rule in trade.trailing_rules:
            if rule['trigger'] == 'TP1_HIT' and trade.tp1_executed:
                # Mover a BE estructural
                new_sl = self.calculate_be_structural(
                    entry=trade.entry_price,
                    spread=trade.entry_spread_pips
                )
                return self.move_sl(trade, new_sl, reason='tp1_hit_be')

            elif rule['trigger'] == 'NEW_SWING_FORMED':
                # Detectar nuevo swing en dirección favorable
                swing = self.detect_new_swing(
                    current_market_data,
                    direction=trade.direction,
                    min_bars=rule['condition']['min_bars_since_entry']
                )

                if swing and swing.confirms_direction:
                    new_sl = swing.price - (trade.direction_multiplier * rule['buffer_pips'])

                    # Solo mover si nuevo SL es mejor que actual
                    if self.is_better_sl(new_sl, trade.current_sl, trade.direction):
                        return self.move_sl(trade, new_sl, reason='new_swing')

            elif rule['trigger'] == 'NEW_OB_FORMED':
                # Trailing basado en nuevo order block
                ob = self.detect_new_order_block(
                    current_market_data,
                    direction=trade.direction
                )

                if ob and ob.strength >= rule['condition']['ob_strength']:
                    if trade.direction == 'LONG':
                        new_sl = ob.low - rule['buffer_pips']
                    else:
                        new_sl = ob.high + rule['buffer_pips']

                    if self.is_better_sl(new_sl, trade.current_sl, trade.direction):
                        return self.move_sl(trade, new_sl, reason='new_ob')

            elif rule['trigger'] == 'TIME_STALL':
                # Trailing por tiempo si sin progreso
                bars_stalled = self.calculate_bars_without_progress(trade, current_market_data)

                if bars_stalled >= rule['condition']['bars_without_progress']:
                    current_profit_r = self.calculate_current_r(trade, current_market_data)

                    if current_profit_r > 0.5:
                        # Tighten SL a mitad de camino entre actual y entry
                        new_sl = (trade.current_sl + trade.entry_price) / 2
                        return self.move_sl(trade, new_sl, reason='time_stall_tighten')

        return None  # No trailing needed
```

### 5.2. Break-Even Inteligente

```python
def evaluate_breakeven(trade, current_market_data, strategy_profile):
    """
    Evalúa si mover a break-even según condiciones inteligentes.
    """
    be_rules = trade.breakeven_rules

    # Check 1: ¿Condición de elegibilidad cumplida?
    eligible = False

    if 'TP1_HIT' in be_rules['eligible_conditions'] and trade.tp1_executed:
        eligible = True

    if 'PROFIT_EXCEEDS_THRESHOLD' in be_rules['eligible_conditions']:
        current_r = calculate_current_r(trade, current_market_data)
        if current_r >= be_rules['profit_threshold_r']:
            eligible = True

    if not eligible:
        return None  # No elegible todavía

    # Check 2: Validaciones adicionales
    for check in be_rules['additional_checks']:
        if check == 'NEW_SWING_FORMED':
            swing = detect_new_swing(current_market_data, trade.direction)
            if not swing or not swing.confirms_direction:
                return None  # Swing no formado, no mover a BE

        elif check.startswith('MAE_CURRENT'):
            # Verificar que MAE actual no excede típico
            current_mae = calculate_current_mae(trade, current_market_data)
            mae_limit = strategy_profile.get_mae_percentile(0.75, regime=trade.regime)

            if current_mae > mae_limit:
                logger.info(f"BE denied: current MAE {current_mae} > typical {mae_limit}")
                return None

    # Todas las checks pasaron → mover a BE
    be_level = trade.entry_price + (trade.direction_multiplier * be_rules['spread_buffer_pips'])

    return {
        'action': 'MOVE_TO_BE',
        'new_sl': be_level,
        'reason': 'breakeven_conditions_met'
    }
```

---

## 6. EJEMPLOS COMPLETOS

### 6.1. Ejemplo: Momentum Trade Alta Calidad

```
SEÑAL:
- Strategy: momentum_quality
- Symbol: EURUSD
- Direction: LONG
- Entry: 1.0850
- Regime: TREND_STRONG_UP
- Signal Strength: 0.88
- VPIN: 0.22 (clean)
- Confluence: [HTF_aligned, volume_surge, OFI_bullish, clean_microstructure]

QUALITY SCORE:
- Pedigree: 0.79 (Tier 2, Sharpe 2.8, WR 68%)
- Signal: 0.84 (fuerza alta, confluencia 4/5)
- Microstructure: 0.87 (spread tight, clean flow)
- Data Health: 0.99 (todo válido)
- Portfolio: 0.93 (baja exposición)
→ FINAL: 0.87

RISK ALLOCATION:
- Risk base: 1.30% (de tabla para score 0.87)
- Adjustments: ninguna (todo favorable)
- Risk final: 1.30%
- Capital: 100,000 EUR
- Risk EUR: 1,300 EUR

STOP LOSS:
- Tipo: swing_break
- Market structure: Último swing low = 1.0822
- SL: 1.0822 - 3 pips = 1.0819
- Distance: 1.0850 - 1.0819 = 31 pips

VOLUME CALCULATION:
- Risk EUR / Distance pips = 1,300 / 31 = 41.94 EUR per pip
- EURUSD: 1 pip = 10 EUR per 1.0 lot
- Volume: 41.94 / 10 = 4.19 lots → 4.2 lots

TAKE PROFITS:
- TP1: 1.0905 (liquidity zone + MFE p70)
  - Distance: 55 pips = 1.77R
  - Volume: 60% = 2.52 lots
- TP2: 1.0975 (HTF resistance + MFE p85)
  - Distance: 125 pips = 4.03R
  - Volume: 40% = 1.68 lots

TRAILING:
- Trigger 1: TP1 hit → SL to 1.0852 (BE + 2 pips)
- Trigger 2: New swing low forms > 1.0852 → trail SL detrás

BREAKEVEN:
- Threshold: +1.2R (37 pips profit)
- Additional: Requiere nuevo swing formado
- BE Level: 1.0852 (entry + 2 pips spread buffer)

EXECUTION PROFILE:
Entry Order: BUY 4.2 lots EURUSD @ 1.0850
SL: 1.0819 (-31 pips, -1.0R, -1,300 EUR)
TP1: 1.0905 (+55 pips, +1.77R, +2,300 EUR) [2.52 lots]
TP2: 1.0975 (+125 pips, +4.03R, +5,240 EUR) [1.68 lots]

Expected Value (si TP1 hit 70%, TP2 hit 30%):
= 0.70 * 1.77R * 0.60 + 0.30 * 4.03R * 1.0
= 0.745R + 1.209R
= 1.95R esperado
```

### 6.2. Ejemplo: Mean Reversion Trade Media Calidad

```
SEÑAL:
- Strategy: mean_reversion_statistical
- Symbol: GBPUSD
- Direction: LONG
- Entry: 1.2450 (oversold extremo)
- Regime: RANGING_LOW_VOL
- Signal Strength: 0.72
- Z-score: -2.8 (2.8 sigma bajo media)
- VPIN: 0.35 (neutral)

QUALITY SCORE:
- Pedigree: 0.71 (Tier 2, Sharpe 2.2, WR 63%)
- Signal: 0.68 (fuerza media, fit perfecto para ranging)
- Microstructure: 0.62 (spread normal, VPIN neutral)
- Data Health: 0.92
- Portfolio: 0.78 (exposición media)
→ FINAL: 0.71

RISK ALLOCATION:
- Risk base: 0.69% (de tabla)
- Adjustments: x0.9 (exposición media en GBP)
- Risk final: 0.62%
- Capital: 100,000 EUR
- Risk EUR: 620 EUR

STOP LOSS:
- Tipo: statistical_invalidation
- Mean: 1.2520
- Sigma: 0.0030 (30 pips)
- SL: Entry - 2.5*sigma = 1.2450 - 0.0075 = 1.2375
- Distance: 75 pips

VOLUME:
- 620 / 75 = 8.27 EUR per pip
- GBPUSD: 1 pip = 10 EUR per 1.0 lot
- Volume: 0.83 lots → 0.8 lots

TAKE PROFITS:
- TP1: 1.2520 (mean reversion to 20-EMA)
  - Distance: 70 pips = 0.93R
  - Volume: 80% = 0.64 lots (conservador)
- TP2: 1.2570 (upper Bollinger band)
  - Distance: 120 pips = 1.60R
  - Volume: 20% = 0.16 lots

TRAILING: NONE (típico de mean reversion)

BREAKEVEN:
- Threshold: +1.0R (75 pips profit)
- Rápido a BE para asegurar en reversiones

EXECUTION PROFILE:
Entry: BUY 0.8 lots GBPUSD @ 1.2450
SL: 1.2375 (-75 pips, -1.0R, -620 EUR)
TP1: 1.2520 (+70 pips, +0.93R, +577 EUR) [0.64 lots]
TP2: 1.2570 (+120 pips, +1.60R, +992 EUR) [0.16 lots]

Expected Value (MR típico: TP1 80%, TP2 20%):
= 0.80 * 0.93R * 0.80 + 0.20 * 1.60R * 1.0
= 0.60R + 0.32R
= 0.92R esperado
```

---

## 7. CALIBRACIÓN Y APRENDIZAJE

### 7.1. Análisis Post-Trade

Cada trade cerrado alimenta el sistema de aprendizaje:

```python
class TradeAnalyzer:
    """
    Analiza outcomes para calibrar Quality Score.
    """

    def analyze_trade(self, trade_record):
        """
        Extrae insights del trade completado.
        """
        analysis = {
            'trade_id': trade_record.trade_id,
            'quality_score': trade_record.pre_trade_quality_score,
            'outcome_r': trade_record.final_r_multiple,
            'outcome_binary': 1 if trade_record.outcome == 'WIN' else 0,
            'mae_pct': trade_record.max_adverse_excursion_pct,
            'mfe_pct': trade_record.max_favorable_excursion_pct,
            'duration_bars': trade_record.duration_bars,
            'sl_adjustments': len(trade_record.sl_adjustments),
            'tp_sequence': trade_record.tp_fills_sequence
        }

        # Calcular discrepancia score vs outcome
        expected_r = self.estimate_expected_r(trade_record.quality_score)
        actual_r = trade_record.final_r_multiple
        discrepancy = abs(expected_r - actual_r)

        analysis['score_outcome_discrepancy'] = discrepancy

        # Flags de anomalías
        if trade_record.quality_score > 0.80 and actual_r < 0:
            analysis['anomaly'] = 'high_score_loss'
        elif trade_record.quality_score < 0.60 and actual_r > 2.0:
            analysis['anomaly'] = 'low_score_big_win'

        # Guardar en MemoryStore
        MEMORY_STORE.add_trade_analysis(analysis)

        return analysis
```

### 7.2. Recalibración Periódica

```python
def recalibrate_quality_scorer(lookback_days=30):
    """
    Ajusta pesos de dimensiones basado en performance real.
    """
    trades = MEMORY_STORE.get_trades(lookback_days=lookback_days)

    # Feature matrix: scores de 5 dimensiones
    X = np.array([
        [
            t.quality_breakdown['pedigree'],
            t.quality_breakdown['signal'],
            t.quality_breakdown['microstructure'],
            t.quality_breakdown['data_health'],
            t.quality_breakdown['portfolio']
        ]
        for t in trades
    ])

    # Target: outcome binario (win/loss)
    y = np.array([1 if t.outcome == 'WIN' else 0 for t in trades])

    # Regresión logística para encontrar pesos óptimos
    model = LogisticRegression(penalty='l2', C=1.0)
    model.fit(X, y)

    # Coeficientes = importancia relativa de cada dimensión
    coefficients = np.abs(model.coef_[0])
    new_weights = coefficients / coefficients.sum()  # Normalizar a suma 1.0

    logger.info(f"Dimensión weights recalibrados:")
    logger.info(f"  Pedigree: {new_weights[0]:.3f} (original 0.25)")
    logger.info(f"  Signal: {new_weights[1]:.3f} (original 0.25)")
    logger.info(f"  Microstructure: {new_weights[2]:.3f} (original 0.20)")
    logger.info(f"  Data Health: {new_weights[3]:.3f} (original 0.15)")
    logger.info(f"  Portfolio: {new_weights[4]:.3f} (original 0.15)")

    # Análisis de predictive power
    y_pred_proba = model.predict_proba(X)[:, 1]
    auc_score = roc_auc_score(y, y_pred_proba)
    logger.info(f"Model AUC: {auc_score:.3f}")

    if auc_score > 0.65:
        # Si model tiene poder predictivo, aplicar nuevos pesos
        logger.info("Applying new weights to QualityScorer")
        QUALITY_SCORER.update_weights(new_weights)
    else:
        logger.warning(f"AUC too low ({auc_score}), keeping current weights")

    return new_weights, auc_score
```

### 7.3. Detección de Strategy Decay

```python
def detect_strategy_decay():
    """
    Identifica estrategias cuya performance se está degradando.
    """
    strategies = STRATEGY_REGISTRY.get_all_strategies()

    for strategy in strategies:
        # Performance últimos 30 días
        recent_perf = PERFORMANCE_STORE.get_strategy_stats(
            strategy=strategy.name,
            lookback_days=30
        )

        # Performance últimos 90 días (baseline)
        baseline_perf = PERFORMANCE_STORE.get_strategy_stats(
            strategy=strategy.name,
            lookback_days=90
        )

        # Comparar métricas clave
        sharpe_decay = baseline_perf.sharpe_ratio - recent_perf.sharpe_ratio
        wr_decay = baseline_perf.win_rate - recent_perf.win_rate

        if sharpe_decay > 0.5 or wr_decay > 0.10:
            logger.warning(f"STRATEGY_DECAY detected: {strategy.name}")
            logger.warning(f"  Sharpe: {baseline_perf.sharpe_ratio:.2f} → {recent_perf.sharpe_ratio:.2f}")
            logger.warning(f"  Win Rate: {baseline_perf.win_rate:.2%} → {recent_perf.win_rate:.2%}")

            # Acción: reducir tier bonus o pausar estrategia
            if sharpe_decay > 1.0:
                logger.critical(f"PAUSING strategy {strategy.name} due to severe decay")
                STRATEGY_REGISTRY.pause_strategy(strategy.name)
            else:
                logger.warning(f"Reducing tier bonus for {strategy.name}")
                QUALITY_SCORER.reduce_strategy_tier(strategy.name)
```

---

## CONCLUSIÓN

Este sistema de Risk Management es **columna vertebral institucional**:

✅ **Quality Score** con 5 dimensiones cuantificables
✅ **Riesgo proporcional** a calidad (0-2% hard cap)
✅ **SL/TP estructurales** sin ATR ni retail logic
✅ **Trailing inteligente** basado en nueva estructura
✅ **Break-even condicional** con validaciones
✅ **Memoria completa** para calibración continua

**Cada operación queda definida con precisión matemática. Nada retail. Nada aleatorio. Solo lógica perfecta.**

---

**Ref**: MANDATO 4 - Risk Manager institucional con Quality Score
**Próximo**: Implementación de componentes y testing exhaustivo
