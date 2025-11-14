# CATÁLOGO INSTITUCIONAL DE ESTRATEGIAS

**Proyecto**: SUBLIMINE TradingSystem
**Fecha**: 2025-11-14
**Mandato**: MANDATO 9 (Cirugía Estratégica) - FASE 1
**Autor**: Sistema de Gobernanza Institucional

---

## RESUMEN EJECUTIVO

**Total de estrategias**: 24
**Clasificación**:
- ✅ **APROBAR (13)**: Estrategias institucionalmente sólidas, requieren endurecimiento
- ⚠️ **HYBRID (8)**: Estrategias con componentes retail/SMC, requieren elevación institucional
- ❌ **BROKEN (3)**: Estrategias con fraude conceptual o errores graves, requieren reescritura total

**Estado del portafolio**: ZOO SIN GOBERNANZA
**Riesgos críticos detectados**:
- Factor crowding masivo (múltiples estrategias = misma idea)
- Solapamiento: Order Flow (3), Liquidity (4), Order Blocks/SMC (3), Correlación (2), Pairs Trading (2)
- Naming engañoso en 5+ estrategias
- Sin backtests documentados
- Sin integración explícita con Risk Engine/Microestructura/Multiframe

---

## CLASIFICACIÓN POR CATEGORÍA

### 1. MOMENTUM (3 estrategias)

#### S001 - momentum_quality
- **Archivo**: `momentum_quality.py`
- **Clasificación**: ⚠️ **HYBRID**
- **Tipo**: Momentum con confluencia multi-factor
- **Símbolos aplicables**: EURUSD, GBPUSD, XAUUSD, BTCUSD, US50
- **Holding típico**: 2-6 horas
- **Dependencies**:
  - Microestructura: VPIN, OFI
  - Multiframe: HTF trend
  - Data health: >0.70
- **Edge declarado**: Momentum con calidad de price action + order flow clean + MTF confluence
- **Problemas detectados**:
  - Naming engañoso: "quality" es vago, debería llamarse `momentum_multiframe_confluence`
  - Usa thresholds hardcoded (`vpin_clean_max=0.30`, `volume_threshold=1.40`)
  - Sin backtest documentado
- **Acción requerida**: Renaming + externalizar thresholds + integración explícita Multiframe
- **Estado propuesto**: PILOT → PRODUCTION (tras elevación)

#### S002 - breakout_volume_confirmation
- **Archivo**: `breakout_volume_confirmation.py`
- **Clasificación**: ✅ **APROBAR**
- **Tipo**: Breakout con confirmación de volumen
- **Símbolos aplicables**: Todos (FX majors, metals, crypto, indices)
- **Holding típico**: 1-3 horas
- **Dependencies**:
  - Básicas: OHLCV, ATR
  - Opcional: VPIN para filtrar false breakouts
- **Edge declarado**: Breakout de rango con volumen >1.5x promedio
- **Problemas detectados**:
  - Estrategia clásica, probablemente robusta pero sin validación empírica
  - Requiere integración con Microestructura (depth imbalance en breakout)
- **Acción requerida**: Backtest + integración con order book depth
- **Estado propuesto**: PILOT → PRODUCTION

#### S003 - crisis_mode_volatility_spike
- **Archivo**: `crisis_mode_volatility_spike.py`
- **Clasificación**: ✅ **APROBAR**
- **Tipo**: Volatility spike (news/crisis)
- **Símbolos aplicables**: XAUUSD, VIX, índices
- **Holding típico**: Minutos a 1 hora
- **Dependencies**:
  - Volatility regime detection
  - News feed (opcional pero recomendado)
- **Edge declarado**: Capturar spikes de volatilidad en eventos extremos
- **Problemas detectados**:
  - Necesita integración con news feed para anticipar eventos
  - Riesgo de slippage extremo
- **Acción requerida**: Backtest + news feed integration + slippage model
- **Estado propuesto**: EXPERIMENTAL → PILOT

---

### 2. LIQUIDITY (4 estrategias)

#### S004 - liquidity_sweep
- **Archivo**: `liquidity_sweep.py`
- **Clasificación**: ✅ **APROBAR**
- **Tipo**: Liquidity sweep (stop hunt + reversal)
- **Símbolos aplicables**: FX majors, XAUUSD
- **Holding típico**: <1 hora (scalping-day trading)
- **Dependencies**:
  - Microestructura: VPIN, OFI, depth
  - Swing levels detection
- **Edge declarado**: Stop hunt de niveles clave + reversión con OFI absorption
- **Problemas detectados**:
  - Overlap con `idp_inducement_distribution` (ambos hacen stop hunts)
  - Thresholds hardcoded (`penetration_min=3`, `volume_threshold=1.3`)
- **Acción requerida**: Backtest + diferenciación clara vs IDP
- **Estado propuesto**: PRODUCTION (tras validación)

#### S005 - htf_ltf_liquidity
- **Archivo**: `htf_ltf_liquidity.py`
- **Clasificación**: ⚠️ **HYBRID**
- **Tipo**: Liquidity con confluencia HTF/LTF
- **Símbolos aplicables**: FX majors
- **Holding típico**: 1-4 horas
- **Dependencies**:
  - Multiframe: HTF levels + LTF entries
  - Microestructura: liquidity detection
- **Edge declarado**: HTF liquidity zones + LTF sweep confirmation
- **Problemas detectados**:
  - Overlap con `liquidity_sweep` (factor crowding)
  - Naming confuso: debería ser `liquidity_multiframe_zones`
  - Conceptos SMC residuales sin formalización completa
- **Acción requerida**: Elevación institucional + renaming + deduplicación con S004
- **Estado propuesto**: PILOT

#### S006 - iceberg_detection
- **Archivo**: `iceberg_detection.py`
- **Clasificación**: ✅ **APROBAR**
- **Tipo**: Iceberg order detection (Level 2)
- **Símbolos aplicables**: Liquid FX majors, XAUUSD
- **Holding típico**: Minutos a 1 hora
- **Dependencies**:
  - Level 2 order book (depth)
  - Tick-by-tick data
- **Edge declarado**: Detectar órdenes iceberg institucionales y tradear en dirección
- **Problemas detectados**:
  - Requiere Level 2 data (¿disponible en VPS/broker?)
  - Alta frecuencia, sensible a latencia
- **Acción requerida**: Validar disponibilidad de Level 2 + latency tests
- **Estado propuesto**: EXPERIMENTAL (pending data availability)

#### S007 - spoofing_detection_l2
- **Archivo**: `spoofing_detection_l2.py`
- **Clasificación**: ✅ **APROBAR**
- **Tipo**: Spoofing detection + fade
- **Símbolos aplicables**: Liquid instruments
- **Holding típico**: Minutos
- **Dependencies**:
  - Level 2 order book
  - High-frequency tick data
- **Edge declarado**: Detectar spoofing (fake orders) y tradear contra spoofers
- **Problemas detectados**:
  - Requiere Level 2 data de alta calidad
  - Overlap con `iceberg_detection` (ambos usan L2)
- **Acción requerida**: Data validation + deduplicación L2 strategies
- **Estado propuesto**: EXPERIMENTAL (pending data)

---

### 3. ORDER FLOW (3 estrategias)

#### S008 - order_flow_toxicity
- **Archivo**: `order_flow_toxicity.py`
- **Clasificación**: ✅ **APROBAR**
- **Tipo**: Order flow toxicity (VPIN-based)
- **Símbolos aplicables**: Todos
- **Holding típico**: 30min - 2 horas
- **Dependencies**:
  - Microestructura: VPIN
  - Volume classification
- **Edge declarado**: Evitar toxic flow, entrar en clean flow favorable
- **Problemas detectados**:
  - Overlap con `ofi_refinement` y `footprint_orderflow_clusters` (FACTOR CROWDING crítico)
  - Las 3 estrategias miran VPIN/OFI → correlación ~1.0
- **Acción requerida**: URGENTE - análisis de correlación entre S008/S009/S010 + considerar fusión
- **Estado propuesto**: PRODUCTION (representante del cluster Order Flow)

#### S009 - ofi_refinement
- **Archivo**: `ofi_refinement.py`
- **Clasificación**: ✅ **APROBAR**
- **Tipo**: Order Flow Imbalance refinement
- **Símbolos aplicables**: FX majors, liquid instruments
- **Holding típico**: 30min - 2 horas
- **Dependencies**:
  - Microestructura: OFI, delta volume
- **Edge declarado**: OFI imbalance detection para dirección institucional
- **Problemas detectados**:
  - FACTOR CROWDING con S008 y S010
  - Casi idéntica a `order_flow_toxicity` (ambas usan OFI/VPIN)
- **Acción requerida**: CRÍTICO - fusionar con S008 o retirar
- **Estado propuesto**: DEGRADED → considerar RETIRED

#### S010 - footprint_orderflow_clusters
- **Archivo**: `footprint_orderflow_clusters.py`
- **Clasificación**: ✅ **APROBAR**
- **Tipo**: Footprint chart analysis (order flow clusters)
- **Símbolos aplicables**: Liquid instruments
- **Holding típico**: 1-3 horas
- **Dependencies**:
  - Microestructura: Footprint data (bid/ask volume per price level)
  - High-frequency data
- **Edge declarado**: Detectar clusters institucionales en footprint chart
- **Problemas detectados**:
  - FACTOR CROWDING con S008/S009 (tercer miembro del cluster Order Flow)
  - Requiere datos tick-by-tick de muy alta calidad
- **Acción requerida**: Validar disponibilidad de footprint data + análisis correlación
- **Estado propuesto**: PILOT (si data available) o RETIRED (si overlap excesivo)

---

### 4. ORDER BLOCKS / SMC (3 estrategias)

#### S011 - order_block_institutional
- **Archivo**: `order_block_institutional.py`
- **Clasificación**: ⚠️ **HYBRID**
- **Tipo**: Order blocks con order flow
- **Símbolos aplicables**: FX majors, XAUUSD
- **Holding típico**: 1-4 horas
- **Dependencies**:
  - Microestructura: OFI absorption, volume sigma
  - Structural levels
- **Edge declarado**: Order blocks (último volumen antes de displacement) + OFI absorption + retest
- **Problemas detectados**:
  - Conceptos SMC/ICT con formalización parcial (mejora vs retail pero aún subjetivo)
  - Overlap con `fvg_institutional` y `idp_inducement_distribution`
  - Naming agresivo: "NO RETAIL DISPLACEMENT GARBAGE" poco profesional
- **Acción requerida**: Validación empírica rigurosa + limpieza de comentarios + diferenciación vs FVG/IDP
- **Estado propuesto**: PILOT

#### S012 - fvg_institutional
- **Archivo**: `fvg_institutional.py`
- **Clasificación**: ⚠️ **HYBRID**
- **Tipo**: Fair Value Gaps con order flow
- **Símbolos aplicables**: FX majors
- **Holding típico**: 1-4 horas
- **Dependencies**:
  - Gap detection (OHLC)
  - Order flow confirmation (VPIN, OFI)
- **Edge declarado**: FVGs (imbalance zones) + order flow fill confirmation
- **Problemas detectados**:
  - Concepto SMC/ICT, necesita validación empírica robusta
  - Overlap con `order_block_institutional` (ambos buscan zonas de imbalance)
  - Sin backtest que demuestre que FVGs realmente funcionan cuantitativamente
- **Acción requerida**: Backtest riguroso + validación out-of-sample + diferenciación vs Order Blocks
- **Estado propuesto**: EXPERIMENTAL → PILOT (pending validation)

#### S013 - idp_inducement_distribution
- **Archivo**: `idp_inducement_distribution.py`
- **Clasificación**: ❌ **BROKEN**
- **Tipo**: IDP pattern (Inducement-Distribution-Price delivery)
- **Símbolos aplicables**: FX majors
- **Holding típico**: 2-6 horas
- **Dependencies**:
  - Microestructura: OFI, CVD, VPIN
  - Swing levels detection
- **Edge declarado**: Patrón institucional de 3 fases (stop hunt → acumulación → displacement)
- **Problemas críticos**:
  - **Aproximaciones débiles**: Definición de "inducement", "distribution", "displacement" es subjetiva
  - **Overlap masivo** con `liquidity_sweep` (ambos hacen stop hunts) y `order_block_institutional`
  - **Sin formalización cuantitativa rigurosa**: ¿Cómo se mide "distribution"? ¿CVD threshold? ¿Duración?
  - Conceptos SMC puros (Wyckoff) sin traducción institucional completa
- **Acción requerida**: **REESCRITURA TOTAL** con definiciones cuantitativas rigurosas o RETIRED
- **Estado propuesto**: BROKEN → REESCRIBIR o RETIRED

---

### 5. MEAN REVERSION (1 estrategia)

#### S014 - mean_reversion_statistical
- **Archivo**: `mean_reversion_statistical.py`
- **Clasificación**: ✅ **APROBAR**
- **Tipo**: Mean reversion estadística (Bollinger, Z-score)
- **Símbolos aplicables**: FX majors (range-bound pairs)
- **Holding típico**: 30min - 2 horas
- **Dependencies**:
  - Bollinger Bands, Z-score
  - Volatility regime (funciona mejor en LOW vol)
- **Edge declarado**: Mean reversion en extremos estadísticos (±2σ) en rangos
- **Problemas detectados**:
  - Estrategia clásica, probablemente robusta en regímenes correctos
  - Necesita regime filter estricto (DEGRADED en TREND regimes)
- **Acción requerida**: Backtest + regime filtering + validación en rangos vs trends
- **Estado propuesto**: PRODUCTION (con regime filter)

---

### 6. PAIRS TRADING / ARBITRAGE (2 estrategias)

#### S015 - kalman_pairs_trading
- **Archivo**: `kalman_pairs_trading.py`
- **Clasificación**: ✅ **APROBAR**
- **Tipo**: Pairs trading con Kalman Filter
- **Símbolos aplicables**: FX majors correlacionados, crypto pairs
- **Holding típico**: 1-8 horas
- **Dependencies**:
  - Multi-symbol data
  - Kalman Filter implementation
- **Edge declarado**: Pairs trading con spread dinámico (Kalman) en vez de estático
- **Problemas detectados**:
  - Overlap con `statistical_arbitrage_johansen` (ambos hacen pairs trading)
  - Requiere multi-symbol data feed
- **Acción requerida**: Backtest + diferenciación vs Johansen + validación de pairs
- **Estado propuesto**: PILOT

#### S016 - statistical_arbitrage_johansen
- **Archivo**: `statistical_arbitrage_johansen.py`
- **Clasificación**: ❌ **BROKEN**
- **Tipo**: Stat arb con cointegración (supuestamente Johansen test)
- **Símbolos aplicables**: 10-15 FX pairs correlacionados
- **Holding típico**: 2-8 horas
- **Dependencies**:
  - Multi-symbol data
  - Cointegration test (Johansen)
- **Edge declarado**: Cointegración real (Johansen) + VECM + mean reversion
- **Problemas CRÍTICOS**:
  - **FRAUDE CONCEPTUAL**: Auditoría indica que NO implementa Johansen test real
  - Código importa scipy.stats pero NO usa `johansen()` de statsmodels
  - Probablemente hace pairs trading simple con naming engañoso
  - Overlap con `kalman_pairs_trading`
- **Acción requerida**: **REESCRITURA TOTAL** con Johansen test REAL o RETIRED + renaming honesto
- **Estado propuesto**: BROKEN → REESCRIBIR (implementar Johansen real) o RETIRED

---

### 7. CORRELATION (2 estrategias)

#### S017 - correlation_divergence
- **Archivo**: `correlation_divergence.py`
- **Clasificación**: ❌ **BROKEN**
- **Tipo**: Correlation divergence + order flow
- **Símbolos aplicables**: Pares correlacionados (EURUSD/GBPUSD, AUDUSD/NZDUSD)
- **Holding típico**: 2-6 horas
- **Dependencies**:
  - Multi-symbol data
  - Correlation calculation
  - Microestructura: OFI, CVD, VPIN
- **Edge declarado**: Detectar divergencias de correlación + convergence trade con OFI confirmation
- **Problemas CRÍTICOS**:
  - **ERROR CONCEPTUAL**: Auditoría indica error de base en lógica de divergencia
  - Correlación instantánea vs estructural mal diferenciada
  - Overlap con `correlation_cascade_detection` (casi idénticas)
  - Sin validación empírica de que "divergencias" revierten
- **Acción requerida**: **REESCRITURA** con lógica de correlación corregida o RETIRED
- **Estado propuesto**: BROKEN → REESCRIBIR o RETIRED

#### S018 - correlation_cascade_detection
- **Archivo**: `correlation_cascade_detection.py`
- **Clasificación**: ⚠️ **HYBRID**
- **Tipo**: Correlation cascade (multi-pair)
- **Símbolos aplicables**: Múltiples pares FX
- **Holding típico**: 1-4 horas
- **Dependencies**:
  - Multi-symbol data
  - Cascade detection logic
- **Edge declarado**: Detectar cascadas de correlación (cuando 1 par mueve y otros siguen)
- **Problemas detectados**:
  - Casi idéntica a `correlation_divergence` (OVERLAP)
  - Lógica de "cascade" no está bien formalizada
  - Requiere datos multi-par de alta calidad
- **Acción requerida**: Validación empírica + diferenciación vs S017 o fusión
- **Estado propuesto**: PILOT (pending validation) o RETIRED (si overlap excesivo)

---

### 8. REGIME ADAPTATION (1 estrategia)

#### S019 - volatility_regime_adaptation
- **Archivo**: `volatility_regime_adaptation.py`
- **Clasificación**: ✅ **APROBAR**
- **Tipo**: Meta-strategy (regime-based strategy selector)
- **Símbolos aplicables**: Todos
- **Holding típico**: N/A (selecciona otras estrategias)
- **Dependencies**:
  - Volatility regime detection (LOW, NORMAL, HIGH, CRISIS)
  - Fit matrix de estrategias
- **Edge declarado**: Seleccionar estrategias óptimas según régimen de volatilidad
- **Problemas detectados**:
  - Fit matrix hardcoded sin calibración empírica
  - Overlap con Brain-layer (brain.py también hace regime fitting)
- **Acción requerida**: Calibración de fit matrix + integración con Brain-layer
- **Estado propuesto**: PRODUCTION (componente de Brain-layer)

---

### 9. NEWS / EVENT-DRIVEN (2 estrategias)

#### S020 - nfp_news_event_handler
- **Archivo**: `nfp_news_event_handler.py`
- **Clasificación**: ⚠️ **HYBRID**
- **Tipo**: News event (NFP specific)
- **Símbolos aplicables**: USD pairs (EURUSD, GBPUSD, USDJPY, etc.)
- **Holding típico**: Minutos (pre/post NFP)
- **Dependencies**:
  - News feed API
  - High-frequency data
  - Slippage model
- **Edge declarado**: Tradear NFP (Non-Farm Payrolls) con pre-positioning + post-reaction
- **Problemas detectados**:
  - **Sin integración con news feed** (crítico para estrategia event-driven)
  - Naming muy largo: debería ser `news_nfp_handler`
  - Riesgo de slippage extremo
- **Acción requerida**: News feed integration + backtest + slippage model + renaming
- **Estado propuesto**: EXPERIMENTAL → PILOT (pending news feed)

#### S021 - calendar_arbitrage_flows
- **Archivo**: `calendar_arbitrage_flows.py`
- **Clasificación**: ⚠️ **HYBRID**
- **Tipo**: Calendar arbitrage (economic events)
- **Símbolos aplicables**: Múltiples según calendario
- **Holding típico**: Minutos a horas
- **Dependencies**:
  - Economic calendar API
  - News feed
  - High-frequency data
- **Edge declarado**: Arbitraje de flujos pre/post eventos de calendario económico
- **Problemas detectados**:
  - Sin integración con calendar API (crítico)
  - Overlap con `nfp_news_event_handler` (ambos event-driven)
  - Concepto de "arbitrage" vago
- **Acción requerida**: Calendar API integration + clarificación de edge + backtest
- **Estado propuesto**: EXPERIMENTAL

---

### 10. MICROSTRUCTURE / ADVANCED (3 estrategias)

#### S022 - vpin_reversal_extreme
- **Archivo**: `vpin_reversal_extreme.py`
- **Clasificación**: ✅ **APROBAR**
- **Tipo**: VPIN extreme reversals
- **Símbolos aplicables**: Liquid instruments
- **Holding típico**: 30min - 2 horas
- **Dependencies**:
  - Microestructura: VPIN
  - Volume classification
- **Edge declarado**: Reversión cuando VPIN >0.70 (toxic extremo) + primera señal de reversión
- **Problemas detectados**:
  - Overlap con `order_flow_toxicity` (ambas usan VPIN)
  - Necesita validación empírica de que VPIN extremo → reversión
- **Acción requerida**: Backtest + diferenciación vs order_flow_toxicity
- **Estado propuesto**: PILOT

#### S023 - fractal_market_structure
- **Archivo**: `fractal_market_structure.py`
- **Clasificación**: ⚠️ **HYBRID**
- **Tipo**: Fractal analysis (multi-timeframe structure)
- **Símbolos aplicables**: FX majors
- **Holding típico**: 2-8 horas
- **Dependencies**:
  - Multiframe context
  - Structure detection
- **Edge declarado**: Estructura fractal (self-similar across timeframes)
- **Problemas detectados**:
  - **Naming engañoso**: "fractal" suena a matemática avanzada pero probablemente es MTF structure simple
  - Concepto vago, sin formalización matemática clara
  - Overlap con Multiframe engine general
- **Acción requerida**: Renaming honesto (`multiframe_structure_alignment`) + validación empírica
- **Estado propuesto**: PILOT (tras renaming)

#### S024 - topological_data_analysis_regime
- **Archivo**: `topological_data_analysis_regime.py`
- **Clasificación**: ⚠️ **HYBRID**
- **Tipo**: Topological data analysis (TDA)
- **Símbolos aplicables**: Todos
- **Holding típico**: Variable
- **Dependencies**:
  - TDA libraries (GUDHI, Ripser)
  - High-dimensional feature space
- **Edge declarado**: Detección de regímenes mediante persistent homology (TDA)
- **Problemas detectados**:
  - **Naming sospechoso**: TDA es avanzado, ¿realmente implementa persistent homology?
  - Sin evidencia de uso de bibliotecas TDA (GUDHI, Ripser)
  - Probablemente es regime detection simple con naming académico
- **Acción requerida**: Auditoría de código + renaming honesto si no es TDA real + backtest
- **Estado propuesto**: EXPERIMENTAL (pending code audit)

---

## RESUMEN DE CLASIFICACIÓN

### ✅ APROBAR (13 estrategias)

**Lista**:
1. S002 - breakout_volume_confirmation
2. S003 - crisis_mode_volatility_spike
3. S004 - liquidity_sweep
4. S006 - iceberg_detection
5. S007 - spoofing_detection_l2
6. S008 - order_flow_toxicity
7. S009 - ofi_refinement
8. S010 - footprint_orderflow_clusters
9. S014 - mean_reversion_statistical
10. S015 - kalman_pairs_trading
11. S019 - volatility_regime_adaptation
12. S022 - vpin_reversal_extreme

**Acción general**:
- Backtest riguroso con métricas institucionales
- Integración explícita con Risk Engine (QualityScorer, RiskAllocator)
- Integración con Microestructura (VPIN, OFI, depth) donde aplique
- Integración con Multiframe (HTF/MTF/LTF) donde aplique
- Endurecimiento de SL/TP institucional (no ATR, sino niveles estructurales)

---

### ⚠️ HYBRID (8 estrategias)

**Lista**:
1. S001 - momentum_quality
2. S005 - htf_ltf_liquidity
3. S011 - order_block_institutional
4. S012 - fvg_institutional
5. S018 - correlation_cascade_detection
6. S020 - nfp_news_event_handler
7. S021 - calendar_arbitrage_flows
8. S023 - fractal_market_structure
9. S024 - topological_data_analysis_regime

**Problemas comunes**:
- Componentes retail/SMC residuales
- Naming engañoso (momentum "quality", "fractal", "topological")
- Falta de integración completa con arquitectura institucional
- Thresholds hardcoded sin calibración

**Acción general**:
- Elevación a INSTITUTIONAL GRADE:
  - Eliminar heurísticas retail
  - Formalización cuantitativa completa
  - Renaming honesto
  - Integración forzada con Microestructura + Multiframe + Risk Engine
- Backtest riguroso post-elevación
- Tests de integración end-to-end

---

### ❌ BROKEN (3 estrategias)

**Lista**:
1. S013 - idp_inducement_distribution (Aproximaciones débiles, overlap masivo)
2. S016 - statistical_arbitrage_johansen (Fraude conceptual: NO es Johansen real)
3. S017 - correlation_divergence (Error conceptual de base)

**Problemas críticos**:
- **S016**: Naming fraudulento (dice "Johansen" pero no implementa test de Johansen real)
- **S017**: Lógica de correlación-divergencia incorrecta
- **S013**: Conceptos SMC sin traducción institucional rigurosa (inducement, distribution, displacement vagos)

**Acción general**:
- **REESCRITURA TOTAL**:
  - S016: Implementar Johansen test REAL (statsmodels) + VECM o RETIRED
  - S017: Corregir lógica de correlación o RETIRED
  - S013: Formalizar IDP cuantitativamente (umbrales OFI/CVD/VPIN rigurosos) o RETIRED
- Documentar diseño cuantitativo ANTES de código
- Backtest riguroso con out-of-sample validation
- Si no pasan validación → RETIRED definitivo

---

## FACTOR CROWDING DETECTADO

### Cluster 1: ORDER FLOW (3 estrategias)
- S008 - order_flow_toxicity
- S009 - ofi_refinement
- S010 - footprint_orderflow_clusters

**Problema**: Las 3 miran VPIN/OFI → correlación ~1.0 → sobre-exposición al factor "order flow"

**Acción**:
- Análisis de correlación de señales históricas
- Considerar fusión en 1 sola estrategia representante: `order_flow_institutional` (fusión de S008/S009)
- Retirar S010 si overlap >0.80

---

### Cluster 2: LIQUIDITY (4 estrategias)
- S004 - liquidity_sweep
- S005 - htf_ltf_liquidity
- S006 - iceberg_detection
- S007 - spoofing_detection_l2

**Problema**: Las 4 miran liquidez/Level 2 → overlap significativo

**Acción**:
- S006 + S007 requieren Level 2 (verificar disponibilidad)
- Si Level 2 no disponible → RETIRED
- S004 + S005: Diferenciar claramente (S004 = single TF, S005 = multi TF) o fusionar

---

### Cluster 3: ORDER BLOCKS / SMC (3 estrategias)
- S011 - order_block_institutional
- S012 - fvg_institutional
- S013 - idp_inducement_distribution

**Problema**: Las 3 buscan zonas de imbalance con conceptos SMC/ICT → overlap masivo

**Acción**:
- S013 → REESCRIBIR o RETIRED (BROKEN)
- S011 + S012: Validación empírica URGENTE
- Si ambas pasan backtest: fusionar en `orderblock_fvg_institutional`
- Si solo 1 pasa: RETIRED la otra

---

### Cluster 4: CORRELATION (2 estrategias)
- S017 - correlation_divergence (BROKEN)
- S018 - correlation_cascade_detection

**Problema**: Casi idénticas (ambas miran correlación entre pares)

**Acción**:
- S017 → REESCRIBIR o RETIRED
- S018 → Validar si edge es real o fusionar con S017 (post-reescritura)

---

### Cluster 5: PAIRS TRADING (2 estrategias)
- S015 - kalman_pairs_trading
- S016 - statistical_arbitrage_johansen (BROKEN)

**Problema**: Ambas hacen pairs trading

**Acción**:
- S016 → REESCRIBIR con Johansen REAL o RETIRED
- S015: Validar backtest
- Si ambas pasan: fusionar en `pairs_trading_advanced` (Kalman + Johansen + VECM)

---

## NAMING ENGAÑOSO DETECTADO

### Estrategias que requieren renaming:

1. **momentum_quality** → `momentum_multiframe_confluence`
   - "Quality" es vago e institucional-washing

2. **htf_ltf_liquidity** → `liquidity_multiframe_zones`
   - Naming actual es acrónimos confusos

3. **nfp_news_event_handler** → `news_nfp_handler`
   - Demasiado largo

4. **fractal_market_structure** → `multiframe_structure_alignment`
   - "Fractal" suena a matemática avanzada pero probablemente no lo es

5. **topological_data_analysis_regime** → `regime_detection_advanced` (si no es TDA real)
   - TDA implica persistent homology, sin evidencia de implementación real

6. **statistical_arbitrage_johansen** → `pairs_trading_kalman` (si no implementa Johansen) o REESCRIBIR
   - Fraude conceptual si no usa Johansen test

---

## DEPENDENCIAS CRÍTICAS NO SATISFECHAS

### Estrategias bloqueadas por falta de data/API:

1. **S006, S007**: Requieren Level 2 order book (¿disponible en broker/VPS?)
2. **S020, S021**: Requieren news feed / economic calendar API (NO implementado)
3. **S010**: Requiere footprint data de alta calidad (¿disponible?)
4. **Todas**: Requieren integración explícita con Microestructura/Multiframe (NO implementada)

---

## PRÓXIMOS PASOS (POST-FASE 1)

### FASE 2: Reescritura de BROKEN (3 estrategias)
- S013: IDP (reescribir con definiciones cuantitativas)
- S016: Johansen (implementar test real o retired)
- S017: Correlation divergence (corregir lógica o retired)

### FASE 3: Elevación de HYBRID (8 estrategias)
- Eliminar componentes retail
- Renaming honesto
- Integración forzada con arquitectura institucional
- Backtest riguroso

### FASE 4: Endurecimiento de APROBAR (13 estrategias)
- Backtest completo con métricas institucionales
- Integración end-to-end con Risk Engine
- Tests de integración
- Definir métricas de PRODUCTION vs DEGRADED

---

**FIN DEL CATÁLOGO INSTITUCIONAL**

**Veredicto**: Sistema tiene 24 estrategias pero solo ~8-10 son institucionalmente defendibles tras cirugía completa. El resto requiere reescritura o retiro.

**Recomendación**: NO desplegar más de 5 estrategias PRODUCTION hasta completar MANDATO 9 completo (Fases 2-4).
