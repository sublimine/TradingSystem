# DISEÑO INSTITUCIONAL: Statistical Arbitrage - Johansen Cointegration

**Proyecto**: SUBLIMINE TradingSystem
**Mandato**: MANDATO 9 - Fase 2 (Reescritura BROKEN)
**Fecha**: 2025-11-14
**Estado**: BROKEN → REESCRITURA INSTITUCIONAL
**Clasificación Original**: ❌ BROKEN (Fraude conceptual)

---

## VEREDICTO INICIAL

**FRAUDE CONCEPTUAL DETECTADO**:
- Estrategia afirma implementar Johansen cointegration test (1988, 1991)
- Código NO usa `statsmodels.tsa.johansen` ni implementa test real
- Método `_johansen_test()` es OLS simple + heurística de stationarity
- Naming engañoso: "Johansen" sin Johansen real

**DECISIÓN**: REESCRITURA TOTAL con implementación institucional rigurosa de Johansen test real o RETIRED.

**VEREDICTO FINAL**: REESCRIBIR con Johansen test REAL (statsmodels).

---

## DEFINICIÓN CUANTITATIVA HONESTA

### Concepto

Statistical arbitrage basado en **cointegración real** detectada vía **Johansen test** (no OLS aproximado):

1. **Johansen Test** (statsmodels): Detectar cointegración entre 2+ series temporales
2. **VECM** (Vector Error Correction Model): Modelar relación dinámica
3. **Spread**: Calcular spread usando vector de cointegración
4. **Mean Reversion**: Tradear reversión del spread a la media
5. **Order Flow Validation**: Confirmar con OFI/CVD/VPIN

### Base Matemática

#### Johansen Test (1988, 1991)

Para series `Y_t` y `X_t`, test de cointegración:

```
H0: No cointegration (rank = 0)
H1: Cointegration (rank ≥ 1)
```

**Implementación**:
```python
from statsmodels.tsa.vector_ar.vecm import coint_johansen

result = coint_johansen(data, det_order=0, k_ar_diff=1)
trace_stat = result.lr1  # Trace statistic
critical_values = result.cvt  # Critical values (90%, 95%, 99%)

# Cointegrated if trace_stat > critical_value at desired confidence
is_cointegrated = trace_stat[0] > critical_values[0][1]  # 95% confidence
cointegration_vector = result.evec[:, 0]  # First eigenvector
```

#### Spread Calculation

Spread usando vector de cointegración `β`:

```
spread_t = Y_t - β * X_t
```

Donde `β` proviene de `result.evec[:, 0]`.

#### Mean Reversion Test

**Half-life** del spread (Ornstein-Uhlenbeck process):

```
spread_t = α + ρ * spread_(t-1) + ε_t
half_life = -log(2) / log(ρ)
```

**Thresholds**:
- `half_life_max`: 5 días (120 horas). Si > 5 días, reversión demasiado lenta.
- `z_score_entry`: ±2.5σ (entrada)
- `z_score_exit`: ±0.5σ (salida)

#### Stop Loss Estructural

SL NO es ATR-based. SL es **z-score estructural**:

```
SL_long: spread_z_score < -4.0  (spread sigue divergiendo, idea inválida)
SL_short: spread_z_score > +4.0
```

Convertido a precio:
```
SL_price = entry_price ± (4.0 * spread_std / hedge_ratio)
```

#### Take Profit

TP basado en estadísticas del spread:

1. **TP primario**: z-score vuelve a 0 (spread normalizado)
2. **Parciales**:
   - 50% a z = ±1.0 (1σ reversión)
   - 30% a z = ±0.5 (0.5σ reversión)
   - 20% trailing a z = 0

---

## INPUTS DE DATOS

### Timeframes

- **HTF**: D1 (calibración de cointegración, lookback 200-250 días)
- **MTF**: H4 (detección de divergencias extremas)
- **LTF**: H1 (timing de entrada)

### Datos Multi-Symbol

**Requiere**:
- Precios de 10-15 pares correlacionados simultáneamente
- Sincronización de timestamps
- Calidad mínima: `data_health_score > 0.80`

**Pares sugeridos** (FX):
```yaml
pairs:
  - [EURUSD, GBPUSD]
  - [EURUSD, USDCHF]
  - [AUDUSD, NZDUSD]
  - [EURJPY, GBPJPY]
  - [EURJPY, USDJPY]
  - [AUDJPY, NZDJPY]
  - [EURCAD, USDCAD]
  - [EURGBP, GBPUSD]
  - [EURAUD, AUDUSD]
  - [XAUUSD, XAGUSD]  # Metals
```

### Features de Microestructura

- **VPIN**: Filtrar toxic flow durante divergencia
- **OFI**: Detectar instituciones posicionándose para convergencia
- **CVD**: Confirmar dirección de convergencia

### Calibración Periódica

- **Retest interval**: 20 barras (H1) = 20 horas
- Recalcular Johansen test cada 20h o cuando correlación cambie >10%

---

## LÓGICA DE SEÑAL

### Condiciones de Entrada

**LONG spread** (comprar Y, vender X):

1. **Johansen test**: Cointegración confirmada (trace_stat > critical_value @ 95%)
2. **Spread z-score < -2.5**: Spread extremadamente bajo
3. **Half-life**: 0.5 < half_life < 5.0 días (reversión razonable)
4. **OFI alignment**: OFI > 0 (buying pressure en Y)
5. **VPIN clean**: vpin < 0.40 (not toxic)
6. **CVD confirmation**: cvd > 0 (acumulación en Y)

**SHORT spread** (vender Y, comprar X):

1. Johansen test confirmado
2. Spread z-score > +2.5
3. Half-life válido
4. OFI < 0 (selling pressure en Y)
5. VPIN < 0.40
6. CVD < 0 (distribución en Y)

### Filtros de Régimen

**NO operar si**:
- `volatility_regime == CRISIS` (spreads pueden no revertir)
- `data_health_score < 0.70` (datos corruptos)
- Cointegración perdida (trace_stat < critical_value)
- Half-life > 5 días (reversión demasiado lenta)

### Campos de Salida

**Signal Output**:

```python
{
    'signal_strength': float,  # 0.0-1.0, función de z-score + half_life
    'confluence_score': float,  # OFI + CVD + VPIN alignment
    'microstructure_score': float,  # VPIN + OFI quality
    'multiframe_score': float,  # HTF cointegration + MTF divergence + LTF entry
    'regime_fit': str,  # NORMAL, HIGH_VOL (crisis = no trade)
    'pair_key': str,  # "EURUSD_GBPUSD"
    'hedge_ratio': float,  # β from Johansen
    'spread_zscore': float,
    'half_life_days': float
}
```

**signal_strength calculation**:

```python
# Z-score contribution (0.0-0.6)
z_contrib = min(abs(zscore) / 3.0, 1.0) * 0.6

# Half-life contribution (0.0-0.4)
hl_contrib = max(0, 1.0 - half_life / 5.0) * 0.4

signal_strength = z_contrib + hl_contrib
```

**confluence_score** (5 criteria, 0-5.0):

1. OFI alignment (0-1.0)
2. CVD confirmation (0-1.0)
3. VPIN clean (0-1.0)
4. Cointegration strength (trace_stat vs critical value, 0-1.0)
5. Z-score extreme (0-1.0)

---

## GESTIÓN DE RIESGO Y SALIDA

### Stop Loss Estructural

**Idea inválida cuando**:
- Spread sigue divergiendo: z > 4.0 (short) o z < -4.0 (long)
- Cointegración perdida (Johansen test fails)

**SL price**:
```python
if direction == 'LONG':
    SL = entry_price - (4.0 * spread_std / hedge_ratio)
else:
    SL = entry_price + (4.0 * spread_std / hedge_ratio)
```

### Take Profit y Parciales

**Basados en reversión estadística del spread**:

1. **50% @ z = ±1.0σ**: Primera reversión significativa
2. **30% @ z = ±0.5σ**: Casi normalizado
3. **20% trailing**: Trail to z = 0 (spread completamente normalizado)

**TP final**: z-score cruza 0 (spread revierte completamente).

### Trailing Stop

Si spread revierte favorablemente:
- Mover SL a breakeven cuando z = ±1.5σ
- Activar trailing si z = ±1.0σ

---

## INTEGRACIÓN CON ARQUITECTURA

### QualityScorer

```python
{
    'signal_strength': 0.0-1.0,
    'confluence_score': 0.0-5.0,
    'microstructure_score': vpin_quality + ofi_quality,
    'multiframe_score': htf_coint + mtf_divergence + ltf_entry
}
```

### TradeManager

- `stop_loss`: Estructural (z-score > 4.0)
- `take_profit`: Parciales basados en z-score
- `trailing`: Activado @ z = ±1.0σ

### RiskAllocator

- `sizing_level`: 2-5
  - 2: Standard (z = 2.5-2.8, half_life 3-5 días)
  - 3: Medium (z = 2.8-3.2, half_life 2-3 días, OFI aligned)
  - 4: High (z > 3.2, half_life < 2 días, OFI + CVD aligned, VPIN < 0.25)
  - 5: Maximum (z > 3.5, half_life < 1 día, perfect alignment)

### ExposureManager

- **Factor**: PAIRS_TRADING
- **Max exposure**: 20% del portafolio en pairs trading total
- **Correlación entre pairs**: Verificar que pares elegidos no estén todos correlacionados (diversificar)

---

## RIESGOS ESPECÍFICOS

### Cuándo NO operar

1. **Crisis mode**: Regímenes extremos rompen cointegración
2. **Cointegración perdida**: Johansen test falla en retest
3. **Half-life demasiado larga**: > 5 días (reversión glacial)
4. **VPIN toxic**: > 0.40 (institutional dumping, no reversión)
5. **Data quality baja**: < 0.70 (Johansen test poco fiable)
6. **News events**: NFP, FOMC en cualquiera de los pares (spreads volátiles)

### Señales de Decay

**Pasar a DEGRADED**:
- Win rate cae < 60% (esperado: 68-74%)
- Sharpe ratio < 1.2
- Max drawdown > 15%
- Cointegración perdida en >50% de pares monitored

**RETIRED**:
- Win rate < 55% durante 3 meses
- Sharpe < 0.8
- Johansen test sistemáticamente falla (mercados no cointegran más)

---

## IMPLEMENTACIÓN

### Librerías Requeridas

```python
import statsmodels.api as sm
from statsmodels.tsa.vector_ar.vecm import coint_johansen
import numpy as np
import pandas as pd
```

### Estructura de Código

```python
class StatisticalArbitrageJohansen(StrategyBase):

    def _johansen_test_real(self, prices1, prices2):
        """REAL Johansen test using statsmodels."""
        data = np.column_stack([prices1, prices2])
        result = coint_johansen(data, det_order=0, k_ar_diff=1)

        # Check cointegration at 95% confidence
        trace_stat = result.lr1[0]
        critical_value = result.cvt[0][1]  # 95%

        is_cointegrated = trace_stat > critical_value
        cointegration_vector = result.evec[:, 0]

        return is_cointegrated, cointegration_vector

    def _calculate_half_life(self, spread):
        """Calculate mean reversion half-life."""
        # AR(1): spread_t = α + ρ * spread_(t-1) + ε
        spread_lag = spread[:-1]
        spread_current = spread[1:]

        model = sm.OLS(spread_current, sm.add_constant(spread_lag))
        results = model.fit()
        rho = results.params[1]

        if 0 < rho < 1:
            half_life = -np.log(2) / np.log(rho)
            return half_life
        else:
            return None  # Not mean reverting

    def evaluate(self, market_data, features):
        # Update cointegration tests periodically
        # Calculate spreads for cointegrated pairs
        # Generate signals for extreme z-scores with OFI/CVD/VPIN confirmation
        ...
```

---

## BACKTESTING Y VALIDACIÓN

### Métricas Esperadas

- **Win Rate**: 68-74%
- **Sharpe Ratio**: 1.5-2.2
- **Max Drawdown**: < 12%
- **Avg RR**: 2.5:1
- **Frecuencia**: 15-25 trades/mes (10 pares)

### Validación Out-of-Sample

- Train: 2020-2022
- Test: 2023-2024
- Walk-forward: 6 meses rolling

### Sensibilidad

- **z_entry**: 2.0, 2.5, 3.0
- **half_life_max**: 3, 5, 7 días
- **vpin_threshold**: 0.30, 0.40, 0.50

---

## REFERENCIAS

1. Johansen, S. (1988). "Statistical analysis of cointegration vectors". Journal of Economic Dynamics and Control.
2. Johansen, S. (1991). "Estimation and Hypothesis Testing of Cointegration Vectors in Gaussian Vector Autoregressive Models". Econometrica.
3. Vidyamurthy, G. (2004). "Pairs Trading: Quantitative Methods and Analysis". Wiley.
4. Avellaneda, M., & Lee, J. (2010). "Statistical Arbitrage in the U.S. Equities Market". Quantitative Finance.
5. Easley, D. et al. (2012). "Flow Toxicity and Liquidity in a High-Frequency World". Review of Financial Studies.

---

**ESTADO**: DISEÑO COMPLETADO → IMPLEMENTACIÓN PENDIENTE
**PRÓXIMO PASO**: Reescribir `src/strategies/statistical_arbitrage_johansen.py` según este diseño.
