# DISEÑO INSTITUCIONAL: Correlation Divergence - Mean Reversion

**Proyecto**: SUBLIMINE TradingSystem
**Mandato**: MANDATO 9 - Fase 2 (Reescritura BROKEN)
**Fecha**: 2025-11-14
**Estado**: BROKEN → REESCRITURA INSTITUCIONAL
**Clasificación Original**: ❌ BROKEN (Error conceptual de base)

---

## VEREDICTO INICIAL

**ERROR CONCEPTUAL DETECTADO**:
- Estrategia NO diferencia correlación **instantánea** vs **estructural**
- Spread calculado como simple diferencia `Y - X` sin hedge ratio
- Usa ATR para SL (PROHIBIDO según gobernanza institucional)
- Lógica de "divergencia" vaga: ¿Qué significa correlación "baja"?
- Sin validación empírica de que divergencias revierten

**DECISIÓN**: REESCRITURA con lógica institucional rigurosa.

**VEREDICTO FINAL**: REESCRIBIR con:
1. Correlación **rolling** (ventana móvil) vs **estructural** (lookback largo)
2. Hedge ratio dinámico (rolling OLS)
3. SL estructural (spread breakdown, NO ATR)
4. Thresholds calibrados empíricamente

---

## DEFINICIÓN CUANTITATIVA HONESTA

### Concepto

Estrategia de **mean reversion** basada en divergencias de correlación entre pares relacionados:

1. **Correlación estructural**: Correlación histórica (60-200 días) entre pares
2. **Correlación rolling**: Correlación reciente (10-20 días)
3. **Divergencia**: Rolling correlation cae significativamente vs estructural
4. **Hedge ratio dinámico**: OLS rolling para calcular spread correcto
5. **Mean reversion trade**: Fade la divergencia, esperar convergencia

### Diferencia vs Johansen

| Aspecto | Correlation Divergence | Johansen |
|---------|------------------------|----------|
| Test estadístico | Correlation coefficient | Cointegration test |
| Relación | Short-term correlation | Long-term equilibrium |
| Frecuencia | Medium (2-6h holds) | Lower (2-8h holds) |
| Pairs | Correlacionados (>0.75) | Cointegrados |
| Edge | Correlation breakdown reversions | Cointegration spread mean reversion |

**Key**: Correlation divergence es más **táctico** (breakdowns temporales), Johansen es más **estratégico** (equilibrio de largo plazo).

---

## DEFINICIÓN MATEMÁTICA

### Correlación Estructural

```python
ρ_structural = corr(Y[-200:], X[-200:])
```

**Threshold**: `ρ_structural > 0.75` (mínimo para considerar par)

### Correlación Rolling

```python
ρ_rolling = corr(Y[-20:], X[-20:])
```

### Divergencia

**Divergencia detectada cuando**:

```python
divergence_ratio = (ρ_structural - ρ_rolling) / ρ_structural

is_diverged = divergence_ratio > divergence_threshold  # Default: 0.30
```

**Ejemplo**:
- `ρ_structural = 0.80` (high correlation)
- `ρ_rolling = 0.50` (correlation dropped)
- `divergence_ratio = (0.80 - 0.50) / 0.80 = 0.375` → DIVERGED

### Hedge Ratio Dinámico

**NO** simple diferencia. Usar **rolling OLS**:

```python
# OLS: Y = α + β*X + ε
model = OLS(Y[-60:], add_constant(X[-60:]))
results = model.fit()
hedge_ratio = results.params[1]
```

### Spread

```python
spread_t = Y_t - (hedge_ratio * X_t)
```

### Z-Score del Spread

```python
spread_mean = mean(spread[-60:])
spread_std = std(spread[-60:])
z_score = (spread_current - spread_mean) / spread_std
```

### Condición de Entrada

**LONG spread** (comprar Y, vender X):

1. Divergencia confirmada: `divergence_ratio > 0.30`
2. Spread extremo: `z_score < -2.0`
3. Correlación rolling rebotando: `ρ_rolling` subiendo en últimas 3 barras

**SHORT spread**:

1. Divergencia confirmada
2. `z_score > +2.0`
3. Correlación rolling rebotando

---

## INPUTS DE DATOS

### Timeframes

- **HTF**: H4 (correlación estructural, 200 barras = 33 días)
- **MTF**: H1 (correlación rolling, detección de divergencia)
- **LTF**: M15 (timing de entrada)

### Datos Multi-Symbol

**Pares sugeridos** (FX):

```yaml
high_correlation_pairs:
  - [EURUSD, GBPUSD]      # EUR correlation
  - [AUDUSD, NZDUSD]      # Oceanic correlation
  - [EURJPY, USDJPY]      # JPY crosses
  - [USDCAD, USDCHF]      # USD safe havens
  - [XAUUSD, XAGUSD]      # Metals
```

**Criterios de selección**:
- `ρ_structural > 0.75` (últimos 200 días H1)
- Líquidos (spread < 2 pips)
- Sin eventos de calendario divergentes (e.g., EUR PMI vs USD NFP mismo día)

### Features de Microestructura

- **OFI**: Confirmar instituciones posicionándose para convergencia
- **CVD**: Validar dirección de convergencia
- **VPIN**: Filtrar toxic flow durante divergencia
- **Depth imbalance**: Detectar absorción institucional

---

## LÓGICA DE SEÑAL

### Condiciones de Entrada LONG

1. **Divergencia estructural**:
   ```python
   ρ_structural > 0.75
   ρ_rolling < (ρ_structural * 0.70)  # Correlation dropped 30%
   ```

2. **Spread extremo**:
   ```python
   z_score < -2.0  # Y underperforming vs X
   ```

3. **Reversión iniciando**:
   ```python
   ρ_rolling[-1] > ρ_rolling[-2]  # Correlation rebounding
   ```

4. **OFI confirmation**:
   ```python
   ofi_Y > 1.5  # Buying pressure en Y (underperforming asset)
   ```

5. **VPIN clean**:
   ```python
   vpin < 0.40  # Not toxic
   ```

6. **CVD alignment**:
   ```python
   cvd_Y > 0.4  # Accumulation en Y
   ```

### Filtros de Régimen

**NO operar si**:
- **Crisis mode**: `volatility_regime == CRISIS`
- **News divergence**: Eventos de calendario diferentes en los 2 pares (EUR PMI vs USD data)
- **Correlation breakdown completo**: `ρ_rolling < 0.30` (relación rota, no temporal)
- **Data quality**: `data_health_score < 0.75`

### Campos de Salida

```python
{
    'signal_strength': float,  # 0.0-1.0
    'confluence_score': float,  # 0.0-5.0
    'microstructure_score': float,
    'multiframe_score': float,
    'pair_key': str,  # "EURUSD_GBPUSD"
    'correlation_structural': float,
    'correlation_rolling': float,
    'divergence_ratio': float,
    'spread_zscore': float,
    'hedge_ratio': float,
    'correlation_rebound': bool
}
```

**signal_strength**:

```python
# Z-score contribution (0.0-0.5)
z_contrib = min(abs(zscore) / 3.0, 1.0) * 0.5

# Divergence magnitude (0.0-0.3)
div_contrib = min(divergence_ratio / 0.50, 1.0) * 0.3

# Correlation rebound (0.0-0.2)
rebound = 0.2 if ρ_rolling[-1] > ρ_rolling[-2] else 0.0

signal_strength = z_contrib + div_contrib + rebound
```

**confluence_score** (5 criteria, 0-5.0):

1. **Divergence magnitude**: `divergence_ratio / 0.50` (0-1.0)
2. **Spread extreme**: `abs(z_score) / 3.0` (0-1.0)
3. **OFI alignment** (0-1.0)
4. **CVD confirmation** (0-1.0)
5. **VPIN clean** (0-1.0)

---

## GESTIÓN DE RIESGO Y SALIDA

### Stop Loss Estructural

**Idea inválida cuando**:
- **Correlation breakdown permanente**: `ρ_rolling` sigue cayendo < 0.30
- **Spread sigue divergiendo**: `z_score < -3.5` (long) o `> +3.5` (short)

**SL basado en spread breakdown**:

```python
if direction == 'LONG':
    # If spread continues diverging beyond -3.5σ, idea is wrong
    SL_spread_z = -3.5
    SL_price = entry_price - ((abs(z_score_entry) + 1.5) * spread_std / hedge_ratio)
else:
    SL_spread_z = +3.5
    SL_price = entry_price + ((abs(z_score_entry) + 1.5) * spread_std / hedge_ratio)
```

**NO ATR**. SL es spread-based.

### Take Profit y Parciales

**Basados en convergencia del spread**:

1. **50% @ z = ±1.0σ**: Spread revirtiendo significativamente
2. **30% @ z = ±0.5σ**: Casi normalizado
3. **20% @ z = 0**: Spread completamente convergido

**Correlation rebound target**:
- Exit completo si `ρ_rolling > (ρ_structural * 0.90)` → Correlation restored

### Trailing Stop

- **Activar**: Cuando `z_score` cruza ±1.0σ (a favor)
- **Trail**: Mantener SL @ z = ±1.5σ (proteger ganancias)

---

## INTEGRACIÓN CON ARQUITECTURA

### QualityScorer

```python
{
    'signal_strength': 0.0-1.0,
    'confluence_score': 0.0-5.0,
    'microstructure_score': ofi_quality + vpin_quality,
    'multiframe_score': htf_structural_corr + mtf_divergence + ltf_rebound
}
```

### TradeManager

- `stop_loss`: Spread breakdown (z < -3.5 o > +3.5)
- `take_profit`: Parciales @ z = ±1.0, ±0.5, 0
- `trailing`: Activado @ z = ±1.0σ

### RiskAllocator

- `sizing_level`: 2-4
  - 2: Standard (z = 2.0-2.5, divergence_ratio = 0.30-0.40)
  - 3: Medium (z = 2.5-3.0, divergence_ratio = 0.40-0.50, OFI aligned)
  - 4: High (z > 3.0, divergence_ratio > 0.50, OFI + CVD + rebound confirmed)

### ExposureManager

- **Factor**: CORRELATION_DIVERGENCE
- **Max exposure**: 15% del portafolio
- **Overlap check**: No tradear >2 pares correlacionados simultáneamente (e.g., EURUSD_GBPUSD + EURUSD_USDCHF = overlap EUR)

---

## RIESGOS ESPECÍFICOS

### Cuándo NO operar

1. **Correlation breakdown permanente**: `ρ_rolling < 0.30` (relación rota)
2. **Crisis mode**: Correlaciones se rompen sistemáticamente
3. **News divergence**: Eventos diferentes en los 2 símbolos mismo día
4. **VPIN toxic**: > 0.50 (dumping institucional)
5. **Data quality**: < 0.75

### Señales de Decay

**Pasar a DEGRADED**:
- Win rate < 60% (esperado: 66-72%)
- Sharpe < 1.0
- Max drawdown > 12%
- Divergencias NO revierten (mercado cambió estructura)

**RETIRED**:
- Win rate < 55% durante 3 meses
- Sharpe < 0.6
- Correlaciones estructurales caen < 0.65 en mayoría de pares (régimen cambió)

---

## DIFERENCIAS vs VERSIÓN BROKEN

| Aspecto | BROKEN | INSTITUCIONAL |
|---------|--------|---------------|
| Correlación | Instantánea única | Estructural vs Rolling |
| Spread | Y - X (simple diff) | Y - β*X (hedge ratio) |
| Divergencia | Vaga (corr < 0.50) | Cuantitativa (ratio > 0.30) |
| SL | ATR-based | Spread breakdown (z < -3.5) |
| TP | ATR-based R multiple | Z-score parciales (1.0, 0.5, 0) |
| Hedge ratio | No existe | Rolling OLS (60 bars) |
| Validación | Ninguna | OFI + CVD + VPIN + correlation rebound |

---

## IMPLEMENTACIÓN

### Librerías Requeridas

```python
import numpy as np
import pandas as pd
import statsmodels.api as sm
from scipy.stats import pearsonr
```

### Estructura de Código

```python
class CorrelationDivergence(StrategyBase):

    def _calculate_correlations(self, prices1, prices2):
        """Calculate structural and rolling correlations."""
        corr_structural = np.corrcoef(prices1[-200:], prices2[-200:])[0, 1]
        corr_rolling = np.corrcoef(prices1[-20:], prices2[-20:])[0, 1]

        divergence_ratio = (corr_structural - corr_rolling) / corr_structural if corr_structural > 0 else 0

        return corr_structural, corr_rolling, divergence_ratio

    def _calculate_hedge_ratio(self, prices1, prices2):
        """Rolling OLS for dynamic hedge ratio."""
        Y = prices1[-60:]
        X = prices2[-60:]

        model = sm.OLS(Y, sm.add_constant(X))
        results = model.fit()

        return results.params[1]  # β

    def _calculate_spread_zscore(self, prices1, prices2, hedge_ratio):
        """Calculate z-score of hedged spread."""
        spread = prices1[-60:] - (hedge_ratio * prices2[-60:])
        spread_mean = np.mean(spread)
        spread_std = np.std(spread)

        current_spread = prices1[-1] - (hedge_ratio * prices2[-1])
        z_score = (current_spread - spread_mean) / spread_std if spread_std > 0 else 0

        return z_score, spread_std

    def _check_correlation_rebound(self, prices1, prices2):
        """Check if correlation is rebounding (recent uptick)."""
        corr_history = []
        for i in range(3):
            window_start = -(20 + i*5)
            window_end = -(i*5) if i > 0 else None
            corr = np.corrcoef(prices1[window_start:window_end], prices2[window_start:window_end])[0, 1]
            corr_history.append(corr)

        # Correlation increasing in last 3 windows?
        is_rebounding = corr_history[0] > corr_history[1]

        return is_rebounding

    def evaluate(self, market_data, features):
        # Calculate correlations (structural vs rolling)
        # Detect divergence
        # Calculate hedge ratio and spread z-score
        # Check correlation rebound
        # Validate with OFI/CVD/VPIN
        # Generate signal
        ...
```

---

## BACKTESTING Y VALIDACIÓN

### Métricas Esperadas

- **Win Rate**: 66-72%
- **Sharpe Ratio**: 1.3-1.9
- **Max Drawdown**: < 12%
- **Avg RR**: 2.0:1
- **Frecuencia**: 20-30 trades/mes (5 pares)

### Validación

- **In-sample**: 2020-2022
- **Out-of-sample**: 2023-2024
- **Walk-forward**: 6 meses rolling

### Sensibilidad

- **divergence_threshold**: 0.25, 0.30, 0.40
- **z_entry**: 1.8, 2.0, 2.5
- **correlation_structural_min**: 0.70, 0.75, 0.80

---

## REFERENCIAS

1. Gatev, E., Goetzmann, W. N., & Rouwenhorst, K. G. (2006). "Pairs Trading: Performance of a Relative-Value Arbitrage Rule". Review of Financial Studies.
2. Vidyamurthy, G. (2004). "Pairs Trading: Quantitative Methods and Analysis". Wiley.
3. Easley, D. et al. (2012). "Flow Toxicity and Liquidity in a High-Frequency World". Review of Financial Studies.
4. Elliott, R. J., Van Der Hoek, J., & Malcolm, W. P. (2005). "Pairs trading". Quantitative Finance.

---

**ESTADO**: DISEÑO COMPLETADO → IMPLEMENTACIÓN PENDIENTE
**PRÓXIMO PASO**: Reescribir `src/strategies/correlation_divergence.py` según este diseño.
