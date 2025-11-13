# ESTRATEGIAS DEPRECATED
## NO USAR EN PRODUCCIÓN

**Fecha de Deprecación**: 2025-11-13
**Razón**: Auditoría Mandato 2 - Estándar Institucional

---

## ESTRATEGIAS EN ESTE DIRECTORIO

### 1. statistical_arbitrage_johansen.py

**Status**: 🔴 **FRAUDE ESTADÍSTICO**

**Problema Crítico**:
- Se llama "Johansen" pero usa OLS regression simple
- NO implementa test de cointegración de Johansen real
- Falta: eigenvalue decomposition, trace statistics, critical values
- Línea 214: `"This is a simplified OLS-based approximation"` ← ESTO NO ES JOHANSEN

**Acción Requerida**:
- REESCRIBIR con `statsmodels.tsa.vector_ar.vecm.coint_johansen`
- O renombrar a `pairs_ols_simple.py` si se mantiene OLS

**Severidad**: CRÍTICA

---

### 2. correlation_divergence.py

**Status**: 🔴 **ERROR CONCEPTUAL FUNDAMENTAL**

**Problema Crítico**:
- Confunde correlación con cointegración
- Dos series con alta correlación pueden NO ser cointegradas
- Trading basado en correlation drop = pérdidas garantizadas
- No valida stationarity del spread
- No calcula half-life

**Acción Requerida**:
- REESCRIBIR con test de cointegración formal (ADF, Engle-Granger, Johansen)
- Validar stationarity antes de trading
- Calcular half-life para mean reversion
- O ELIMINAR y usar estrategia Johansen (cuando esté correctamente implementada)

**Severidad**: CRÍTICA

---

### 3. idp_inducement_distribution.py

**Status**: 🔴 **APROXIMACIONES DÉBILES**

**Problema Crítico**:
- Concepto Wyckoff IDP válido pero implementación aproximada
- Level detection es retail (swing patterns + round numbers)
- OFI estimation es "rough" y "simplified" (líneas 275-286)
- Confirmation scores basados en approximated data
- Dependencia de `identify_idp_pattern()` sin validar implementación

**Acción Requerida**:
- REESCRIBIR level detection con:
  - Volume profile concentration zones
  - OFI reversal points históricos
  - Statistical price levels
- REESCRIBIR OFI tracking para capturar:
  - OFI DURANTE inducement (no estimate)
  - OFI DURANTE distribution (rolling window)
  - OFI surge DURANTE displacement (real-time)
- Verificar implementación de `identify_idp_pattern()` en features module

**Severidad**: ALTA

---

## TIMELINE DE REACTIVACIÓN

### P0 - URGENTE (Esta Semana)

1. **statistical_arbitrage_johansen.py**: Reescribir o renombrar
2. **correlation_divergence.py**: Reescribir o eliminar

### P1 - ALTA (Próximas 2-4 Semanas)

3. **idp_inducement_distribution.py**: Reescribir con real order flow tracking

---

## ALTERNATIVAS DISPONIBLES

Mientras estas estrategias están deprecated, usar:

**Para Statistical Arbitrage**:
- ✅ `kalman_pairs_trading.py` (requiere agregar cointegration testing)
- ✅ `mean_reversion_statistical.py` (requiere agregar ADF test)

**Para IDP Pattern Trading**:
- ✅ `order_block_institutional.py` (similar concept, mejor implementación)
- ✅ `liquidity_sweep.py` (stop hunts institucionales)

---

## NOTAS PARA DESARROLLADORES

**NO** intentes usar estas estrategias:
- Causarán pérdidas en producción
- No pasan estándares institucionales
- Tienen bugs conceptuales fundamentales

Si necesitas reimplementar:
1. Lee el informe de auditoría completo en `/docs/auditorias/`
2. Consulta papers académicos citados
3. Implementa tests formales (ADF, Johansen, half-life)
4. Valida out-of-sample antes de deployment

---

**Arquitecto Principal - ALGORITMO_INSTITUCIONAL_SUBLIMINE**
**Fecha**: 2025-11-13
