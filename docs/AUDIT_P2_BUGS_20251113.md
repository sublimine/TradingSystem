# AUDITORÍA P2 - BUGS MENORES

**Sistema:** TradingSystem  
**Fecha:** 2025-11-13  
**Bugs P0 corregidos:** 12  
**Bugs P1 corregidos:** 27  
**Bugs P2 identificados:** 26

---

## CATEGORÍA 1: HARDCODED VALUES (11 bugs)

### BUG-P2-001: Min arbitration score hardcoded
- **Archivo**: `src/core/brain.py`
- **Línea**: 97
- **Categoría**: hardcoded
- **Descripción**: `min_arbitration_score = 0.65` está hardcodeado en lugar de parametrizado en config. Este threshold crítico debería ser configurable para diferentes regímenes de mercado.
- **Fix sugerido**: Mover a config con `self.config.get('min_arbitration_score', 0.65)` y documentar su impacto.

### BUG-P2-002: VPIN thresholds hardcoded en timing evaluation
- **Archivo**: `src/core/brain.py`
- **Líneas**: 266-272
- **Categoría**: hardcoded
- **Descripción**: Thresholds de VPIN (0.50, 0.30) están hardcodeados en `_evaluate_timing()`. Diferentes instrumentos requieren diferentes thresholds.
- **Fix sugerido**: Parametrizar como `vpin_toxic_threshold=0.50` y `vpin_clean_threshold=0.30` en config por instrumento.

### BUG-P2-003: Min quality score sin explicación
- **Archivo**: `src/core/risk_manager.py`
- **Línea**: 336
- **Categoría**: hardcoded
- **Descripción**: `self.min_quality_score = config.get('min_quality_score', 0.60)` - el valor 0.60 carece de justificación teórica o empírica documentada.
- **Fix sugerido**: Documentar en comentario el research basis para este threshold o hacerlo dinámico según performance histórico.

### BUG-P2-004: Portfolio imbalance ratio hardcoded
- **Archivo**: `src/core/brain.py`
- **Líneas**: 438-439
- **Categoría**: hardcoded
- **Descripción**: Ratio 6:2 de imbalance direccional hardcodeado sin justificación. ¿Por qué 6:2 y no 5:3 o 7:1?
- **Fix sugerido**: Parametrizar como `max_directional_imbalance_ratio` en config con research basis documentado.

### BUG-P2-005: Position management R thresholds hardcoded
- **Archivo**: `src/core/position_manager.py`
- **Líneas**: 236-239
- **Categoría**: hardcoded
- **Descripción**: `min_r_for_breakeven=1.5`, `min_r_for_trailing=2.0`, `min_r_for_partial=2.5` - valores fijos que podrían optimizarse por estrategia.
- **Fix sugerido**: Hacer configurables por estrategia y permitir ajuste dinámico basado en ML feedback.

### BUG-P2-006: Momentum quality thresholds sin explicación
- **Archivo**: `src/strategies/momentum_quality.py`
- **Líneas**: 40-46
- **Categoría**: hardcoded
- **Descripción**: Múltiples thresholds (`price_threshold=0.30`, `volume_threshold=1.40`, `vpin_clean_max=0.30`) sin documentación de origen.
- **Fix sugerido**: Agregar comentario explicando research basis o backtesting que justifica cada valor.

### BUG-P2-007: Liquidity sweep thresholds todos hardcoded
- **Archivo**: `src/strategies/liquidity_sweep.py`
- **Líneas**: 42-50
- **Categoría**: hardcoded
- **Descripción**: Todos los thresholds críticos (`penetration_min=3`, `penetration_max=15`, `volume_threshold=1.3`) carecen de explicación.
- **Fix sugerido**: Documentar en docstring por qué estos valores específicos y agregar referencia a backtesting results.

### BUG-P2-008: VPIN bucket parameters hardcoded
- **Archivo**: `src/features/order_flow.py`
- **Líneas**: 20, 28
- **Categoría**: hardcoded
- **Descripción**: `bucket_size=50000` y `num_buckets=50` sin justificación. Estos valores afectan sensibilidad de VPIN.
- **Fix sugerido**: Documentar en comentario basándose en Easley et al. (2012) o hacer configurables por instrumento según ADV.

### BUG-P2-009: Kyle's Lambda warm-up thresholds sin documentar
- **Archivo**: `src/gatekeepers/kyles_lambda.py`
- **Líneas**: 48-49
- **Categoría**: hardcoded
- **Descripción**: `warm_up_threshold=100`, `warm_up_absolute_lambda=0.05` - valores críticos sin research basis documentado.
- **Fix sugerido**: Agregar comentario explicando por qué 100 trades y threshold 0.05 basado en análisis empírico.

### BUG-P2-010: ePIN warm-up values hardcoded
- **Archivo**: `src/gatekeepers/epin_estimator.py`
- **Líneas**: 51-52
- **Categoría**: hardcoded
- **Descripción**: `warm_up_threshold=100`, `warm_up_absolute_pin=0.75` sin justificación estadística.
- **Fix sugerido**: Documentar rational para estos valores o hacerlos adaptativos basados en instrument volatility.

### BUG-P2-011: ML analysis interval hardcoded
- **Archivo**: `src/core/ml_adaptive_engine.py`
- **Línea**: 678
- **Categoría**: hardcoded
- **Descripción**: `self.analysis_interval_hours = 6` hardcodeado - debería ser configurable según frecuencia de trading.
- **Fix sugerido**: Parametrizar en config como `ml_analysis_interval_hours` con default 6.

---

## CATEGORÍA 2: DOCUMENTACIÓN FALTANTE (7 bugs)

### BUG-P2-012: SignalArbitrator.__init__ sin documentar parámetros config
- **Archivo**: `src/core/brain.py`
- **Líneas**: 55-57
- **Categoría**: documentation
- **Descripción**: El `__init__` de SignalArbitrator no documenta qué parámetros debe contener el dict `config`.
- **Fix sugerido**: Agregar docstring listando parámetros esperados en config dict con formato Args.

### BUG-P2-013: QualityScorer sin docstring
- **Archivo**: `src/core/risk_manager.py`
- **Líneas**: 25-36
- **Categoría**: documentation
- **Descripción**: La clase QualityScorer y su `__init__` carecen de docstring explicando el propósito y algoritmo de scoring.
- **Fix sugerido**: Agregar docstring clase + método explicando los 5 factores de calidad y sus pesos.

### BUG-P2-014: RegimeDetector.__init__ no documenta config params
- **Archivo**: `src/core/regime_detector.py`
- **Líneas**: 42-68
- **Categoría**: documentation
- **Descripción**: `__init__` recibe config dict pero no documenta los ~10 parámetros esperados.
- **Fix sugerido**: Agregar Args docstring listando todos los config parameters con sus defaults y significado.

### BUG-P2-015: PositionManager.__init__ documentación incompleta
- **Archivo**: `src/core/position_manager.py`
- **Líneas**: 220-248
- **Categoría**: documentation
- **Descripción**: Docstring de `__init__` no documenta parámetros críticos como `min_r_for_breakeven`, `structure_proximity_atr`.
- **Fix sugerido**: Completar Args section con todos los config parameters.

### BUG-P2-016: Función compleja sin docstring explicativo
- **Archivo**: `src/strategies/order_block_institutional.py`
- **Líneas**: 201-302
- **Categoría**: documentation
- **Descripción**: `_evaluate_institutional_confirmation` es función de 100+ líneas con lógica compleja pero solo 1 línea de docstring.
- **Fix sugerido**: Agregar docstring detallado explicando los 5 criterios de evaluación y su scoring.

### BUG-P2-017: detect_displacement sin explicar algoritmo
- **Archivo**: `src/features/displacement.py`
- **Líneas**: 41-89
- **Categoría**: documentation
- **Descripción**: Función crítica de detección de order blocks carece de docstring explicando el algoritmo estadístico usado.
- **Fix sugerido**: Agregar docstring explicando volume sigma detection, displacement magnitude calculation y research basis.

### BUG-P2-018: PerformanceAttributionAnalyzer sin docstring
- **Archivo**: `src/core/ml_adaptive_engine.py`
- **Líneas**: 289-298
- **Categoría**: documentation
- **Descripción**: Clase crítica de ML attribution analysis no tiene docstring explicando su propósito y métodos.
- **Fix sugerido**: Agregar class-level docstring explicando qué analiza y cómo se usa.

---

## CATEGORÍA 3: EDGE CASES MENORES (6 bugs)

### BUG-P2-019: fit_matrix incompleto en regime detection
- **Archivo**: `src/core/brain.py`
- **Líneas**: 183-223
- **Categoría**: edge-case
- **Descripción**: `fit_matrix` solo cubre 6 regímenes y ~15 estrategias. Estrategias nuevas retornan default 0.7 sin logging.
- **Fix sugerido**: Agregar logging cuando se usa default y documentar que nuevas estrategias deben agregarse al matrix.

### BUG-P2-020: Division por zero check débil
- **Archivo**: `src/core/risk_manager.py`
- **Líneas**: 458-463
- **Categoría**: edge-case
- **Descripción**: Check `if denominator == 0:` es débil, debería ser `< epsilon` para evitar división casi-cero.
- **Fix sugerido**: Cambiar a `if abs(denominator) < 1e-6:` para robustez numérica.

### BUG-P2-021: _find_structure_near_price retorna None sin logging
- **Archivo**: `src/core/position_manager.py`
- **Líneas**: 363-371
- **Categoría**: edge-case
- **Descripción**: Cuando no hay estructura cercana, retorna None silenciosamente. Esto puede causar stops subóptimos sin aviso.
- **Fix sugerido**: Agregar `logger.debug()` cuando no se encuentra estructura para debugging.

### BUG-P2-022: Swing point detection sin validación robusta
- **Archivo**: `src/strategies/liquidity_sweep.py`
- **Líneas**: 113-121
- **Categoría**: edge-case
- **Descripción**: Loop simple sin validar bounds cuando data tiene < 5 barras. Puede causar IndexError en edge cases.
- **Fix sugerido**: Agregar check `if len(highs) < 5: return []` antes del loop.

### BUG-P2-023: trade_direction==0 retorna None sin handling
- **Archivo**: `src/features/order_flow.py`
- **Líneas**: 46-47
- **Categoría**: edge-case
- **Descripción**: Cuando trade_direction es 0 (neutral), retorna None. El caller debe validar None o puede crashear.
- **Fix sugerido**: Documentar en docstring que puede retornar None y caller debe validar, o manejar internamente.

### BUG-P2-024: detect_divergence función stub sin implementar
- **Archivo**: `src/features/technical_indicators.py`
- **Línea**: 354
- **Categoría**: edge-case
- **Descripción**: Función `detect_divergence` retorna Series vacío (solo 0s). Es un stub no implementado que puede causar bugs silenciosos.
- **Fix sugerido**: Implementar la lógica o agregar `raise NotImplementedError("Divergence detection not yet implemented")`.

---

## CATEGORÍA 4: CALIDAD DE CÓDIGO (2 bugs)

### BUG-P2-025: fit_matrix gigante hardcoded debería estar en config
- **Archivo**: `src/core/brain.py`
- **Líneas**: 183-220
- **Categoría**: code-quality
- **Descripción**: Dict `fit_matrix` de 40+ líneas está hardcodeado en código. Debería estar en archivo JSON/YAML de configuración.
- **Fix sugerido**: Mover a `config/regime_strategy_fit_matrix.json` y cargar en `__init__` con `_load_fit_matrix()`.

### BUG-P2-026: features.extend con slice arbitrario [:10]
- **Archivo**: `src/core/ml_adaptive_engine.py`
- **Líneas**: 448-457, 512
- **Categoría**: code-quality
- **Descripción**: `features.extend(list(trade.entry_features.values())[:10])` - slice arbitrario puede causar inconsistencia si features cambian de orden.
- **Fix sugerido**: Usar claves específicas en lugar de slice para garantizar consistencia.

---

## RESUMEN POR CATEGORÍA

| Categoría | Cantidad | Impacto |
|-----------|----------|---------|
| Hardcoded Values | 11 | Medio - Dificulta optimización |
| Documentación Faltante | 7 | Bajo - Reduce mantenibilidad |
| Edge Cases Menores | 6 | Bajo-Medio - Pueden causar bugs silenciosos |
| Calidad de Código | 2 | Bajo - Deuda técnica |
| **TOTAL** | **26** | **MENOR** |

---

## PRIORIDAD DE CORRECCIÓN

**Alta prioridad:**
- P2-024: Función stub puede causar bugs silenciosos
- P2-019: fit_matrix incompleto afecta nuevas estrategias
- P2-022: Validación bounds en swing detection

**Media prioridad:**
- P2-001 a P2-011: Parametrizar hardcoded values
- P2-025: Mover fit_matrix a config

**Baja prioridad:**
- P2-012 a P2-018: Mejorar documentación
- P2-026: Mejorar robustez ML features

---

## PLAN DE CORRECCIÓN

Los 26 bugs P2 se corregirán en orden de prioridad según las categorías establecidas. Se creará un PR único consolidado que incluya todas las correcciones.

**Ref**: MANDATO 3 - Cierre total de pendientes
