# HALLAZGOS CRÍTICOS - AUDITORÍA src/features/

## Resumen Ejecutivo
- **Fecha**: 2025-11-13
- **Ramas Analizadas**: main
- **Módulos**: 12
- **Hallazgos Críticos**: 7
- **Hallazgos Importantes**: 11
- **Hallazgos Menores**: 6
- **Total Problemas**: 24

---

## 🔴 HALLAZGOS CRÍTICOS (BLOQUEAN PRODUCCIÓN)

### C1: technical_indicators.py:340 - detect_divergence() INCOMPLETA
**Ubicación**: `/home/user/TradingSystem/src/features/technical_indicators.py:340`

**Problema**: 
```python
def detect_divergence(prices, indicator, lookback=20):
    divergence = pd.Series(0, index=prices.index)
    price_highs, price_lows = identify_swing_points(prices, order=lookback//2)
    ind_highs, ind_lows = identify_swing_points(indicator, order=lookback//2)
    return divergence  # ← RETORNA SIEMPRE CEROS, NUNCA USA LOS HIGHS/LOWS
```

**Impacto**: Feature completamente no funcional, siempre retorna neutro
**Acción**: Implementar lógica de detección usando los swing points

---

### C2: statistical_models.py:683,875 - calculate_spread_zscore() DUPLICADA
**Ubicación**: `/home/user/TradingSystem/src/features/statistical_models.py`

**Problema**: 
Función definida DOS VECES con implementaciones diferentes:
- Línea 683: `if std <= 0: raise ValueError(...)`
- Línea 875: `if std < 1e-10: return 0.0`

**Impacto**: Última definición sobrescribe la primera, comportamiento impredecible
**Acción**: Mantener una sola implementación con validación clara

---

### C3: statistical_models.py:816,902 - detect_spread_divergence() DUPLICADA
**Ubicación**: `/home/user/TradingSystem/src/features/statistical_models.py`

**Problema**: 
Función definida DOS VECES CON SIGNATURES DIFERENTES:
- Línea 816: `detect_spread_divergence(spread, kalman_filter, ...)`
- Línea 902: `detect_spread_divergence(z_score, ...)`

**Impacto**: Código que llama a versión con KalmanPairsFilter fallará silenciosamente
**Acción**: Consolidar o renombrar una de las versiones explícitamente

---

### C4: statistical_models.py:793,852 - calculate_spread() DUPLICADA
**Ubicación**: `/home/user/TradingSystem/src/features/statistical_models.py`

**Problema**: 
- Línea 793: `calculate_spread_from_prices(prices_x, prices_y, hedge_ratio)`
- Línea 852: `calculate_spread(price_y, price_x, beta)`

Mismo cálculo, diferentes nombres, diferentes interfaces
**Impacto**: Confusión en la interfaz pública
**Acción**: Consolidar en función única con nombres consistentes

---

### C5: mtf.py:9 - project_htf_to_ltf() STUB INCOMPLETO
**Ubicación**: `/home/user/TradingSystem/src/features/mtf.py:9`

**Código**:
```python
def project_htf_to_ltf(h4_zones, m1_bars, tolerance_pips=2):
    # TODO: Full implementation
    return []
```

**Impacto**: Feature NO FUNCIONA, siempre retorna lista vacía
**Acción**: Implementar la funcionalidad completa

---

### C6: gaps.py:9 - detect_fvg() STUB INCOMPLETO
**Ubicación**: `/home/user/TradingSystem/src/features/gaps.py:9`

**Código**:
```python
def detect_fvg(bars_df, atr_min=0.5, vol_check=True):
    # TODO: Full implementation
    return []
```

**Impacto**: Feature NO FUNCIONA
**Acción**: Implementar la funcionalidad completa

---

### C7: tns.py:8 - parse_time_sales() STUB INCOMPLETO
**Ubicación**: `/home/user/TradingSystem/src/features/tns.py:8`

**Código**:
```python
def parse_time_sales(raw_ticks):
    # TODO: Full implementation
    return pd.DataFrame()
```

**Impacto**: Feature NO FUNCIONA
**Acción**: Implementar la funcionalidad completa

---

## 🟠 HALLAZGOS IMPORTANTES (PRÓXIMA ITERACIÓN)

### I1-I4: División por Cero en Technical Indicators
**Ubicaciones**:
- technical_indicators.py:156 - `calculate_stochastic()` 
- technical_indicators.py:293 - `calculate_williams_r()`
- technical_indicators.py:317 - `calculate_cci()`

**Problema**: Divisor puede ser cero sin validación
**Impacto**: RuntimeWarning, valores inf/nan en outputs
**Acción**: Agregar chequeo `if denominator < EPSILON:`

---

### I5: Sin Validación de Inputs
**Ubicaciones**: Múltiples en technical_indicators.py

**Problema**: No validan si inputs son None, vacíos, NaN
**Impacto**: AttributeError o resultados inesperados
**Acción**: Agregar validación al inicio de cada función

---

### I6-I7: Inconsistencias en Cálculos
**Ubicaciones**:
- microstructure.py:299 - `calculate_kyle_lambda()` con np.cov
- order_flow.py:329 - `calculate_amihud_illiquidity()` división por volume

**Problema**: Tipos inconsistentes, falta validación
**Acción**: Estandarizar conversión de tipos y validación

---

### I8-I9: Acceso Sin Validación
**Ubicaciones**:
- orderbook_l2.py:141 - acceso a 'timestamp' sin verificar
- orderbook_l2.py:161 - precisión hardcoded 0.00001

**Problema**: KeyError potencial, no escalable
**Acción**: Validar existencia de claves antes de acceso

---

### I10-I11: Errores de Tipo
**Ubicaciones**:
- delta_volume.py:46 - np.where retorna float, no int
- delta_volume.py:196 - index access sin validación

**Problema**: Type mismatch, IndexError potencial
**Acción**: Validar tipos y existencia de elementos

---

## 🟡 HALLAZGOS MENORES (REFACTOR FUTURO)

### M1-M2: ofi.py
- Hardcoded `1e-10` en lugar de constante EPSILON
- Módulo sin type hints

### M3-M4: Naming Inconsistencias
- `volatility_regime` no documentado (0=low, 1=high)
- Múltiples módulos con spread calculations con nombres similares

### M5-M6: Documentación
- Hardcoded precision no escalable
- pct_change() NaN handling no documentado

---

## MATRIZ DE ACCIÓN

| ID  | Severidad | Módulo | Función | Fix Time | Prioridad |
|-----|-----------|--------|---------|----------|-----------|
| C1  | CRÍTICO   | technical_indicators | detect_divergence | 30min | 1 |
| C2  | CRÍTICO   | statistical_models | calculate_spread_zscore | 15min | 1 |
| C3  | CRÍTICO   | statistical_models | detect_spread_divergence | 20min | 1 |
| C4  | CRÍTICO   | statistical_models | calculate_spread | 20min | 1 |
| C5  | CRÍTICO   | mtf | project_htf_to_ltf | 2h | 1 |
| C6  | CRÍTICO   | gaps | detect_fvg | 2h | 1 |
| C7  | CRÍTICO   | tns | parse_time_sales | 2h | 1 |
| I1-4| IMPORTANTE| technical_indicators | 4 div-by-zero | 45min | 2 |
| I5  | IMPORTANTE| technical_indicators | input validation | 1h | 2 |
| I6-11| IMPORTANTE| 5 módulos | various | 2h | 2 |

**Tiempo Total de Fix Estimado**:
- Críticos: 8.5 horas
- Importantes: 3 horas
- Menores: 1 hora
- **TOTAL**: ~12.5 horas

---

## REFERENCIAS A ARCHIVOS AUDITADOS

Archivos completos con detalles:
- `/home/user/TradingSystem/AUDIT_FEATURES_DETAILED.md` - Análisis completo
- `/home/user/TradingSystem/AUDIT_FEATURES_SUMMARY.txt` - Resumen visual
- `/home/user/TradingSystem/AUDIT_CRITICAL_FINDINGS.md` - Este archivo

Módulos analizados en:
- `/home/user/TradingSystem/src/features/technical_indicators.py`
- `/home/user/TradingSystem/src/features/statistical_models.py`
- `/home/user/TradingSystem/src/features/microstructure.py`
- `/home/user/TradingSystem/src/features/order_flow.py`
- `/home/user/TradingSystem/src/features/ofi.py`
- `/home/user/TradingSystem/src/features/mtf.py`
- `/home/user/TradingSystem/src/features/gaps.py`
- `/home/user/TradingSystem/src/features/tns.py`
- `/home/user/TradingSystem/src/features/orderbook_l2.py`
- `/home/user/TradingSystem/src/features/displacement.py`
- `/home/user/TradingSystem/src/features/delta_volume.py`
- `/home/user/TradingSystem/src/features/derived_features.py`
