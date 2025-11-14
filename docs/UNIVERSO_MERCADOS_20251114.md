# UNIVERSO DE MERCADOS INSTITUCIONAL

**Proyecto**: SUBLIMINE TradingSystem
**Mandato**: MANDATO 10 (Universo de Símbolos)
**Fecha**: 2025-11-14
**Total de Símbolos**: 27
**Estado**: DISEÑO INICIAL

---

## RESUMEN EJECUTIVO

**Criterios de Selección Institucional**:
- ✅ Liquidez alta (spread < 2 pips en FX, < 0.5% en índices/commodities)
- ✅ Microestructura razonable (VPIN, OFI, L2 depth disponibles o estimables)
- ✅ Diversificación por clase de activo, región y tipo de edge
- ✅ Accesibilidad en brokers institucionales (MT5, LMAX, IC Markets, etc.)
- ✅ Historial de datos suficiente (>3 años)

**Distribución**:
- **FX (14 símbolos)**: 52% del universo
- **Índices (6 símbolos)**: 22%
- **Commodities (5 símbolos)**: 19%
- **Crypto (2 símbolos)**: 7%

---

## CRITERIOS INSTITUCIONALES DE SELECCIÓN

### 1. Liquidez y Spreads

| Clase de Activo | Spread Máximo Aceptable | Volumen Diario Min |
|----------------|------------------------|-------------------|
| FX majors | < 1.5 pips | > $500M |
| FX crosses | < 2.5 pips | > $100M |
| Índices | < 0.5% | > $1B |
| Commodities | < 0.8% | > $500M |
| Crypto | < 0.1% | > $2B |

### 2. Microestructura

**Requisitos**:
- VPIN calculable (volumen clasificado en buy/sell)
- OFI estimable (order flow imbalance)
- Depth razonable (L2 data disponible o proxy viable)
- No shitcoins ilíquidos ni FX exóticos sin liquidez

### 3. Diversificación

#### Por Clase de Activo

**FX (14)**: Principales pares (majors) + crosses líquidos
**Índices (6)**: US, Europa, Asia
**Commodities (5)**: Metales preciosos, energía
**Crypto (2)**: BTC, ETH únicamente (alta liquidez, microestructura razonable)

#### Por Región

**US (10)**: USD pairs, US índices, WTI
**Europa (7)**: EUR/GBP pairs, índices europeos
**Asia-Pacífico (5)**: JPY/AUD/NZD pairs, Nikkei
**Global (5)**: Metales, crypto

#### Por Tipo de Edge

**Tendencia (12 símbolos)**: FX majors, índices, WTI
**Mean Reversion (8)**: Pares correlacionados, range-bound FX
**Order Flow (15)**: Alta liquidez, good depth
**Liquidity Sweep (10)**: Stop clusters en niveles clave
**News/Events (5)**: USD pairs, índices US

---

## SÍMBOLOS SELECCIONADOS (27 TOTAL)

### FX MAJORS (7)

#### EURUSD
- **Asset Class**: FX
- **Región**: EU_US
- **Rol**: core_fx, benchmark
- **Spread típico**: 0.6-1.0 pips
- **Estrategias elegibles**:
  - breakout_volume_confirmation
  - liquidity_sweep
  - momentum_quality (MTF confluence)
  - order_flow_toxicity
  - vpin_reversal_extreme
  - statistical_arbitrage_johansen (con GBPUSD)
  - correlation_divergence (con GBPUSD)
- **Notas**: Par más líquido del mundo, microestructura excelente, bajo slippage

#### GBPUSD
- **Asset Class**: FX
- **Región**: EU_US
- **Rol**: core_fx, volatility_proxy
- **Spread típico**: 0.8-1.2 pips
- **Estrategias elegibles**:
  - breakout_volume_confirmation
  - liquidity_sweep
  - vpin_reversal_extreme
  - crisis_mode_volatility_spike (alta volatilidad intraday)
  - statistical_arbitrage_johansen (con EURUSD)
  - correlation_divergence (con EURUSD)
- **Notas**: Alta volatilidad, buena liquidez, sensible a eventos UK/EU

#### USDJPY
- **Asset Class**: FX
- **Región**: US_ASIA
- **Rol**: core_fx, safe_haven_proxy
- **Spread típico**: 0.6-1.0 pips
- **Estrategias elegibles**:
  - breakout_volume_confirmation
  - liquidity_sweep
  - order_flow_toxicity
  - statistical_arbitrage_johansen (con EURJPY)
- **Notas**: Safe haven, carry trade proxy, sensible a BoJ policy

#### USDCHF
- **Asset Class**: FX
- **Región**: US_EU
- **Rol**: safe_haven, correlation_proxy
- **Spread típico**: 1.0-1.5 pips
- **Estrategias elegibles**:
  - liquidity_sweep
  - mean_reversion_statistical (range-bound en períodos de calma)
  - statistical_arbitrage_johansen (con EURUSD)
- **Notas**: Safe haven, correlación inversa con EURUSD, liquidez moderada

#### AUDUSD
- **Asset Class**: FX
- **Región**: ASIA_PACIFIC
- **Rol**: commodity_currency, risk_proxy
- **Spread típico**: 0.8-1.2 pips
- **Estrategias elegibles**:
  - breakout_volume_confirmation
  - liquidity_sweep
  - order_flow_toxicity
  - statistical_arbitrage_johansen (con NZDUSD)
  - correlation_divergence (con NZDUSD)
- **Notas**: Risk-on proxy, commodity correlation (oro, hierro)

#### NZDUSD
- **Asset Class**: FX
- **Región**: ASIA_PACIFIC
- **Rol**: commodity_currency, carry_trade
- **Spread típico**: 1.2-1.8 pips
- **Estrategias elegibles**:
  - liquidity_sweep
  - mean_reversion_statistical
  - statistical_arbitrage_johansen (con AUDUSD)
  - correlation_divergence (con AUDUSD)
- **Notas**: Alta correlación con AUDUSD, carry trade popular

#### USDCAD
- **Asset Class**: FX
- **Región**: US_CANADA
- **Rol**: commodity_currency, oil_proxy
- **Spread típico**: 1.0-1.5 pips
- **Estrategias elegibles**:
  - breakout_volume_confirmation
  - liquidity_sweep
  - correlation_divergence (con WTI)
- **Notas**: Correlación inversa con WTI (petróleo), liquidez buena

---

### FX CROSSES (7)

#### EURGBP
- **Asset Class**: FX
- **Región**: EU
- **Rol**: regional_correlation, range_bound
- **Spread típico**: 1.2-1.8 pips
- **Estrategias elegibles**:
  - mean_reversion_statistical (range-bound frecuente)
  - liquidity_sweep
  - statistical_arbitrage_johansen (con EURUSD/GBPUSD)
- **Notas**: Range-bound común, Brexit volatility proxy

#### EURJPY
- **Asset Class**: FX
- **Región**: EU_ASIA
- **Rol**: risk_proxy, carry_trade
- **Spread típico**: 1.2-1.8 pips
- **Estrategias elegibles**:
  - breakout_volume_confirmation
  - liquidity_sweep
  - vpin_reversal_extreme
  - statistical_arbitrage_johansen (con USDJPY, GBPJPY)
- **Notas**: Risk-on/risk-off barometer, carry trade popular

#### GBPJPY
- **Asset Class**: FX
- **Región**: EU_ASIA
- **Rol**: volatility_beast, momentum_proxy
- **Spread típico**: 1.5-2.5 pips
- **Estrategias elegibles**:
  - breakout_volume_confirmation
  - liquidity_sweep
  - vpin_reversal_extreme
  - crisis_mode_volatility_spike (spikes extremos)
- **Notas**: Altísima volatilidad, slippage risk, para momentum puro

#### AUDJPY
- **Asset Class**: FX
- **Región**: ASIA_PACIFIC
- **Rol**: risk_proxy, commodity_carry
- **Spread típico**: 1.5-2.0 pips
- **Estrategias elegibles**:
  - breakout_volume_confirmation
  - liquidity_sweep
  - statistical_arbitrage_johansen (con NZDJPY)
- **Notas**: Risk-on barometer, commodity + carry trade

#### NZDJPY
- **Asset Class**: FX
- **Región**: ASIA_PACIFIC
- **Rol**: high_beta_risk
- **Spread típico**: 2.0-2.5 pips
- **Estrategias elegibles**:
  - liquidity_sweep
  - statistical_arbitrage_johansen (con AUDJPY)
- **Notas**: Menor liquidez, alta correlación con AUDJPY

#### EURAUD
- **Asset Class**: FX
- **Región**: EU_ASIA_PACIFIC
- **Rol**: risk_divergence
- **Spread típico**: 1.8-2.5 pips
- **Estrategias elegibles**:
  - breakout_volume_confirmation
  - liquidity_sweep
  - correlation_divergence (EU vs commodity cycles)
- **Notas**: Refleja divergencia EU vs commodity economies

#### EURCAD
- **Asset Class**: FX
- **Región**: EU_CANADA
- **Rol**: regional_divergence
- **Spread típico**: 1.8-2.5 pips
- **Estrategias elegibles**:
  - breakout_volume_confirmation
  - liquidity_sweep
  - statistical_arbitrage_johansen (con USDCAD)
- **Notas**: EU vs oil economy divergence

---

### ÍNDICES (6)

#### US500 (S&P 500)
- **Asset Class**: INDEX
- **Región**: US
- **Rol**: core_equity, market_benchmark
- **Spread típico**: 0.3-0.5 pts (0.01-0.02%)
- **Estrategias elegibles**:
  - breakout_volume_confirmation
  - liquidity_sweep
  - crisis_mode_volatility_spike (VIX spikes)
  - vpin_reversal_extreme (extremos de flow)
  - order_flow_toxicity
- **Notas**: Máxima liquidez, microestructura excelente, futuro ES

#### NAS100 (Nasdaq 100)
- **Asset Class**: INDEX
- **Región**: US
- **Rol**: tech_proxy, high_beta
- **Spread típico**: 0.5-0.8 pts (0.03-0.05%)
- **Estrategias elegibles**:
  - breakout_volume_confirmation
  - liquidity_sweep
  - vpin_reversal_extreme
  - crisis_mode_volatility_spike
- **Notas**: Tech-heavy, alta volatilidad, correlación con BTCUSD

#### US30 (Dow Jones)
- **Asset Class**: INDEX
- **Región**: US
- **Rol**: blue_chip_proxy
- **Spread típico**: 1.0-2.0 pts (0.03-0.05%)
- **Estrategias elegibles**:
  - breakout_volume_confirmation
  - liquidity_sweep
  - mean_reversion_statistical
- **Notas**: Menor volatilidad que NAS100, más defensivo

#### DE40 (DAX)
- **Asset Class**: INDEX
- **Región**: EU
- **Rol**: eu_equity_benchmark
- **Spread típico**: 1.0-1.5 pts (0.05-0.08%)
- **Estrategias elegibles**:
  - breakout_volume_confirmation
  - liquidity_sweep
  - vpin_reversal_extreme
- **Notas**: Europa equity proxy, sensible a EUR strength

#### UK100 (FTSE 100)
- **Asset Class**: INDEX
- **Región**: EU
- **Rol**: uk_equity, brexit_proxy
- **Spread típico**: 1.0-2.0 pts (0.05-0.10%)
- **Estrategias elegibles**:
  - breakout_volume_confirmation
  - liquidity_sweep
  - crisis_mode_volatility_spike (Brexit events)
- **Notas**: Commodity-heavy (energy, mining), GBP correlation

#### JP225 (Nikkei 225)
- **Asset Class**: INDEX
- **Región**: ASIA
- **Rol**: asia_equity_benchmark
- **Spread típico**: 2.0-5.0 pts (0.05-0.15%)
- **Estrategias elegibles**:
  - breakout_volume_confirmation
  - liquidity_sweep
- **Notas**: Asia equity proxy, JPY inverse correlation, menor liquidez que US

---

### COMMODITIES (5)

#### XAUUSD (Gold)
- **Asset Class**: COMMODITY
- **Región**: GLOBAL
- **Rol**: safe_haven, inflation_hedge
- **Spread típico**: $0.10-0.30 (0.005-0.015%)
- **Estrategias elegibles**:
  - breakout_volume_confirmation
  - liquidity_sweep (niveles psicológicos)
  - vpin_reversal_extreme
  - crisis_mode_volatility_spike (flight to quality)
  - order_flow_toxicity
  - statistical_arbitrage_johansen (con XAGUSD)
- **Notas**: Máxima liquidez en metales, microestructura excelente, crisis proxy

#### XAGUSD (Silver)
- **Asset Class**: COMMODITY
- **Región**: GLOBAL
- **Rol**: industrial_metal, gold_proxy
- **Spread típico**: $0.02-0.05 (0.08-0.20%)
- **Estrategias elegibles**:
  - breakout_volume_confirmation
  - liquidity_sweep
  - vpin_reversal_extreme
  - statistical_arbitrage_johansen (con XAUUSD)
  - correlation_divergence (con XAUUSD)
- **Notas**: Alta correlación con oro, más volatilidad, industrial demand

#### XTIUSD (WTI Crude Oil)
- **Asset Class**: COMMODITY
- **Región**: US
- **Rol**: energy_benchmark, risk_proxy
- **Spread típico**: $0.02-0.05 (0.03-0.06%)
- **Estrategias elegibles**:
  - breakout_volume_confirmation
  - liquidity_sweep
  - crisis_mode_volatility_spike (geopolítica)
  - vpin_reversal_extreme
  - correlation_divergence (con USDCAD inverse)
- **Notas**: Geopolitical risk, correlación con USD/CAD, storage events

#### XBRUSD (Brent Crude Oil)
- **Asset Class**: COMMODITY
- **Región**: EU
- **Rol**: energy_benchmark_eu
- **Spread típico**: $0.02-0.05 (0.03-0.06%)
- **Estrategias elegibles**:
  - breakout_volume_confirmation
  - liquidity_sweep
  - correlation_divergence (con WTI)
- **Notas**: EU benchmark, spread WTI-Brent tradeable

#### NATGAS (Natural Gas)
- **Asset Class**: COMMODITY
- **Región**: US
- **Rol**: energy_volatility
- **Spread típico**: $0.005-0.01 (0.20-0.50%)
- **Estrategias elegibles**:
  - breakout_volume_confirmation (solo expertos)
  - crisis_mode_volatility_spike (winter demand)
- **Notas**: **EXTREMADAMENTE VOLÁTIL**, slippage risk altísimo, solo crisis mode

---

### CRYPTO (2)

#### BTCUSD (Bitcoin)
- **Asset Class**: CRYPTO
- **Región**: GLOBAL
- **Rol**: crypto_benchmark, high_beta_risk
- **Spread típico**: $5-20 (0.01-0.05%)
- **Estrategias elegibles**:
  - breakout_volume_confirmation
  - liquidity_sweep (niveles psicológicos)
  - vpin_reversal_extreme (extremos de flow)
  - order_flow_toxicity (whale watching)
  - crisis_mode_volatility_spike
- **Notas**: Alta liquidez 24/7, microestructura razonable en Binance/Coinbase, gap risk weekends

#### ETHUSD (Ethereum)
- **Asset Class**: CRYPTO
- **Región**: GLOBAL
- **Rol**: crypto_beta, defi_proxy
- **Spread típico**: $0.50-2.00 (0.02-0.08%)
- **Estrategias elegibles**:
  - breakout_volume_confirmation
  - liquidity_sweep
  - vpin_reversal_extreme
  - correlation_divergence (con BTCUSD)
- **Notas**: Segunda cripto más líquida, correlación con BTC, DeFi events

---

## MAPEO ESTRATEGIA → SÍMBOLOS

### APROBAR (13 estrategias)

#### S002 - breakout_volume_confirmation
**Símbolos (18)**: EURUSD, GBPUSD, USDJPY, AUDUSD, USDCAD, EURJPY, GBPJPY, AUDJPY, EURAUD, EURCAD, US500, NAS100, US30, DE40, UK100, JP225, XAUUSD, BTCUSD
**Tipo**: Universal (todos los líquidos)

#### S003 - crisis_mode_volatility_spike
**Símbolos (10)**: GBPUSD, XAUUSD, US500, NAS100, UK100, XTIUSD, XBRUSD, NATGAS, BTCUSD, ETHUSD
**Tipo**: Alta volatilidad, news-driven

#### S004 - liquidity_sweep
**Símbolos (20)**: Todos los FX majors/crosses, US500, NAS100, XAUUSD, XAGUSD, XTIUSD, BTCUSD
**Tipo**: Stop clusters en niveles clave

#### S006 - iceberg_detection
**Símbolos (5)**: EURUSD, GBPUSD, USDJPY, US500, XAUUSD
**Tipo**: Requiere L2 data de alta calidad (limitado)

#### S007 - spoofing_detection_l2
**Símbolos (5)**: EURUSD, GBPUSD, US500, BTCUSD, ETHUSD
**Tipo**: Requiere L2 data, crypto mejor que FX

#### S008 - order_flow_toxicity
**Símbolos (12)**: EURUSD, GBPUSD, USDJPY, AUDUSD, EURJPY, US500, NAS100, XAUUSD, XTIUSD, BTCUSD
**Tipo**: Alta liquidez, VPIN calculable

#### S009 - ofi_refinement
**Símbolos (10)**: EURUSD, GBPUSD, USDJPY, AUDUSD, EURJPY, US500, XAUUSD
**Tipo**: FX majors + índices líquidos

#### S010 - footprint_orderflow_clusters
**Símbolos (8)**: EURUSD, GBPUSD, USDJPY, US500, NAS100, XAUUSD, BTCUSD
**Tipo**: Requiere footprint data de alta calidad

#### S014 - mean_reversion_statistical
**Símbolos (8)**: EURGBP, USDCHF, NZDUSD, USDCAD, EURAUD, US30, XAGUSD (range-bound pairs)
**Tipo**: Pares con tendencia a range

#### S015 - kalman_pairs_trading
**Símbolos (pares)**: [EURUSD, GBPUSD], [AUDUSD, NZDUSD], [EURJPY, USDJPY], [XAUUSD, XAGUSD], [XTIUSD, XBRUSD]
**Tipo**: Pares correlacionados

#### S016 - statistical_arbitrage_johansen (REESCRITO)
**Símbolos (pares)**: [EURUSD, GBPUSD], [AUDUSD, NZDUSD], [EURJPY, USDJPY], [AUDJPY, NZDJPY], [EURCAD, USDCAD], [XAUUSD, XAGUSD]
**Tipo**: Cointegración (Johansen test real)

#### S017 - correlation_divergence (REESCRITO)
**Símbolos (pares)**: [EURUSD, GBPUSD], [AUDUSD, NZDUSD], [EURJPY, USDJPY], [USDCAD, XTIUSD], [XAUUSD, XAGUSD], [BTCUSD, ETHUSD]
**Tipo**: Correlación alta histórica

#### S022 - vpin_reversal_extreme
**Símbolos (12)**: EURUSD, GBPUSD, EURJPY, GBPJPY, US500, NAS100, XAUUSD, XTIUSD, BTCUSD
**Tipo**: Extremos de VPIN (toxic flow reversals)

---

## DIVERSIFICACIÓN Y RIESGO

### Correlación entre Símbolos

**Clusters de Alta Correlación** (evitar sobre-exposición):

1. **USD pairs cluster**: EURUSD, GBPUSD, AUDUSD, NZDUSD (todos inversos USD)
2. **JPY crosses cluster**: EURJPY, GBPJPY, AUDJPY, NZDJPY (todos JPY + risk-on)
3. **Equity indices cluster**: US500, NAS100, US30 (correlación ~0.90)
4. **Metals cluster**: XAUUSD, XAGUSD (correlación ~0.80)
5. **Oil cluster**: XTIUSD, XBRUSD (correlación ~0.95)
6. **Crypto cluster**: BTCUSD, ETHUSD (correlación ~0.85)

**Acción**: ExposureManager debe limitar exposición simultánea en clusters.

### Límites de Exposición por Clase

- **FX**: Máximo 40% del portafolio (diversificar entre majors/crosses)
- **Índices**: Máximo 30% (diversificar US/EU/Asia)
- **Commodities**: Máximo 20% (máximo 10% en petróleo/gas)
- **Crypto**: Máximo 10% (alta volatilidad)

---

## PRÓXIMOS PASOS

### Fase 1: Validación de Datos (INMEDIATA)
- Verificar disponibilidad de datos históricos (>3 años) en todos los símbolos
- Confirmar spreads actuales vs esperados
- Validar calidad de VPIN/OFI/depth data

### Fase 2: Integración con ExposureManager (Mandato 11)
- Mapeo símbolos → estrategias en código
- Límites de exposición por clase/región
- Correlación matrix para cluster management

### Fase 3: Backtesting (Mandato 12)
- Backtest completo de estrategias APROBAR en símbolos elegibles
- Validación out-of-sample
- Ajuste de universo según performance

### Fase 4: Expansion (Opcional)
- Añadir más símbolos si performance justifica (máximo 40 total)
- Considerar ETFs sectoriales (XLE, XLF, etc.) si micro estructura adecuada
- Añadir crypto altcoins solo si liquidez >$1B y microestructura probada

---

**ESTADO**: DISEÑO COMPLETADO
**TOTAL SÍMBOLOS**: 27
**PRÓXIMO MANDATO**: Integración con config/universe.yaml + ExposureManager
