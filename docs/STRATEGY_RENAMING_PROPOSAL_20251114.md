# PROPUESTA DE RENAMING INSTITUCIONAL

**Proyecto**: SUBLIMINE TradingSystem
**Fecha**: 2025-11-14
**Mandato**: MANDATO 9 (Cirugía Estratégica) - FASE 1
**Autor**: Sistema de Gobernanza Institucional

---

## PROPÓSITO

Este documento lista estrategias con naming engañoso o poco claro y propone renaming honesto que refleje lo que realmente hacen.

**Principio rector**: El nombre debe describir QUÉ HACE la estrategia, NO usar buzzwords académicos sin implementación real.

---

## ESTRATEGIAS REQUIRIENDO RENAMING

### 1. momentum_quality → momentum_multiframe_confluence

**Archivo actual**: `momentum_quality.py`

**Problema con nombre actual**:
- "Quality" es vago y suena a institutional-washing
- No describe qué hace la estrategia
- Suena a marketing retail ("quality momentum")

**Qué hace realmente**:
- Momentum con confluencia multi-timeframe (HTF/LTF)
- Filtra con VPIN clean (order flow)
- Usa múltiples factores (price action + volume + order flow + MTF)

**Nombre propuesto**: `momentum_multiframe_confluence.py`

**Justificación**:
- "multiframe" describe el edge principal (confluencia HTF/LTF)
- "confluence" indica múltiples factores convergiendo
- Honesto: describe lo que hace

**Acción**:
```bash
git mv src/strategies/momentum_quality.py src/strategies/momentum_multiframe_confluence.py
# Actualizar imports en brain.py, config, tests
```

---

### 2. htf_ltf_liquidity → liquidity_multiframe_zones

**Archivo actual**: `htf_ltf_liquidity.py`

**Problema con nombre actual**:
- Acrónimos confusos (HTF/LTF no son intuitivos)
- No describe el edge claramente

**Qué hace realmente**:
- Detecta liquidity zones en HTF (Higher Timeframe)
- Busca sweep de liquidez en LTF (Lower Timeframe)
- Entrada en LTF cuando HTF liquidity zone es tocada

**Nombre propuesto**: `liquidity_multiframe_zones.py`

**Justificación**:
- "multiframe" reemplaza acrónimo HTF/LTF
- "zones" describe que busca zonas de liquidez (no solo sweeps)
- Más descriptivo del edge (liquidez en múltiples timeframes)

**Acción**:
```bash
git mv src/strategies/htf_ltf_liquidity.py src/strategies/liquidity_multiframe_zones.py
```

---

### 3. nfp_news_event_handler → news_nfp_handler

**Archivo actual**: `nfp_news_event_handler.py`

**Problema con nombre actual**:
- Demasiado largo (24 caracteres)
- Redundancia: "news" y "event" son sinónimos en este contexto

**Qué hace realmente**:
- Maneja eventos NFP (Non-Farm Payrolls)
- Pre-positioning antes de NFP
- Post-reaction tras release

**Nombre propuesto**: `news_nfp_handler.py`

**Justificación**:
- Más corto (16 caracteres)
- Mantiene información clave: news + NFP + handler
- Consistencia con posible futura familia `news_<evento>_handler` (PMI, CPI, etc.)

**Acción**:
```bash
git mv src/strategies/nfp_news_event_handler.py src/strategies/news_nfp_handler.py
```

---

### 4. fractal_market_structure → multiframe_structure_alignment

**Archivo actual**: `fractal_market_structure.py`

**Problema con nombre actual**:
- **ENGAÑOSO**: "Fractal" implica análisis de dimensión fractal (matemática avanzada)
- Sin evidencia de implementación de fractal dimension (Hausdorff, box-counting, etc.)
- Probablemente es solo estructura multi-timeframe simple

**Qué hace realmente** (auditoría de código pendiente):
- Detecta estructura de mercado (BOS, CHoCH) en múltiples timeframes
- Busca alineación HTF/LTF
- NO usa matemática fractal real

**Nombre propuesto**: `multiframe_structure_alignment.py`

**Justificación**:
- Honesto: describe alineación de estructura en múltiples timeframes
- Elimina buzzword engañoso ("fractal")
- Si realmente usa fractales → mantener nombre original pero agregar implementación real

**Acción**:
```bash
# PRIMERO: Auditar código para confirmar que NO usa fractales reales
# SI confirma que no usa fractales:
git mv src/strategies/fractal_market_structure.py src/strategies/multiframe_structure_alignment.py

# SI usa fractales reales:
# Mantener nombre, agregar documentación de cálculo de dimensión fractal
```

---

### 5. topological_data_analysis_regime → regime_detection_advanced

**Archivo actual**: `topological_data_analysis_regime.py`

**Problema con nombre actual**:
- **POTENCIALMENTE FRAUDULENTO**: "Topological Data Analysis" (TDA) implica:
  - Persistent homology
  - Betti numbers
  - Uso de bibliotecas GUDHI, Ripser, giotto-tda
- Sin evidencia de importación de estas bibliotecas
- Probablemente es regime detection simple con naming académico

**Qué hace realmente** (auditoría de código pendiente):
- Detecta regímenes de mercado (TREND, RANGE, VOLATILITY)
- Clasifica según volatilidad, autocorrelación, etc.
- NO usa TDA real (persistent homology)

**Nombre propuesto**: `regime_detection_advanced.py`

**Justificación**:
- Honesto: si no usa TDA real, no puede llevar ese nombre
- "advanced" permite cierta sofisticación sin prometer TDA
- Si realmente usa TDA → mantener nombre + documentar algoritmos TDA

**Acción**:
```bash
# PRIMERO: Auditoría CRÍTICA de código
grep -r "gudhi\|ripser\|giotto\|persistent.*homology\|betti" src/strategies/topological_data_analysis_regime.py

# SI NO encuentra TDA real:
git mv src/strategies/topological_data_analysis_regime.py src/strategies/regime_detection_advanced.py

# SI encuentra TDA real:
# Mantener nombre, agregar documentación completa de TDA implementation
```

---

### 6. statistical_arbitrage_johansen → RENAMING CONDICIONAL

**Archivo actual**: `statistical_arbitrage_johansen.py`

**Problema con nombre actual**:
- **POTENCIALMENTE FRAUDULENTO**: "Johansen" implica Johansen cointegration test
- Auditoría indica que NO usa `statsmodels.tsa.vector_ar.vecm.coint_johansen()`
- Si no usa Johansen test → FRAUDE CONCEPTUAL

**Qué hace realmente** (auditoría de código pendiente):
- Auditar si realmente usa `statsmodels.johansen()`
- Si NO → probablemente es pairs trading simple con correlación (NO cointegración)

**Nombres propuestos** (condicional):

#### Opción A: SI NO USA JOHANSEN REAL
**Nombre**: `pairs_trading_correlation.py` (renaming honesto)

**Justificación**:
- Honesto: pairs trading con correlación (NO cointegración Johansen)
- Elimina fraude conceptual

#### Opción B: SI USA JOHANSEN PARCIALMENTE
**Nombre**: `pairs_trading_coint_basic.py`

**Justificación**:
- Usa cointegración pero NO test de Johansen completo (VECM)
- "basic" indica que no es implementación completa

#### Opción C: SI USA JOHANSEN REAL
**Nombre**: Mantener `statistical_arbitrage_johansen.py`

**Justificación**:
- Nombre correcto si implementa Johansen + VECM

**Acción**:
```bash
# PRIMERO: Auditoría CRÍTICA de código
grep -r "from statsmodels.tsa.vector_ar.vecm import coint_johansen" src/strategies/statistical_arbitrage_johansen.py
grep -r "johansen\(" src/strategies/statistical_arbitrage_johansen.py

# SI NO encuentra importación de Johansen:
git mv src/strategies/statistical_arbitrage_johansen.py src/strategies/pairs_trading_correlation.py
# + Actualizar docstring para eliminar mención a "Johansen"

# SI encuentra Johansen real:
# Mantener nombre, validar implementación completa (test + VECM)
```

---

## CAMBIOS ADICIONALES EN DOCUMENTACIÓN

### Actualizar en todos los archivos renombrados:

1. **Docstring de clase**:
   - Eliminar buzzwords engañosos
   - Describir honestamente qué hace
   - Si tenía "ELITE INSTITUTIONAL" → reemplazar con descripción técnica

2. **Comentarios agresivos**:
   - Eliminar frases como:
     - "NO RETAIL GARBAGE"
     - "REAL INSTITUTIONAL - NO DISPLACEMENT GARBAGE"
     - "🏆 ELITE"
   - Reemplazar con lenguaje profesional

3. **Imports y referencias**:
   - Actualizar todos los imports en:
     - `src/core/brain.py`
     - `src/core/portfolio_manager.py`
     - `config/active_strategies.yaml`
     - `tests/strategies/test_*.py`

---

## PLAN DE EJECUCIÓN

### Fase 1: Auditoría de código (CRÍTICO)
**Estrategias que requieren auditoría ANTES de renaming**:
1. `fractal_market_structure.py` → Verificar si usa fractales reales
2. `topological_data_analysis_regime.py` → Verificar si usa TDA real (GUDHI/Ripser)
3. `statistical_arbitrage_johansen.py` → Verificar si usa Johansen test real

**Método**:
```bash
# Fractal
grep -r "hausdorff\|box.counting\|fractal.*dimension" src/strategies/fractal_market_structure.py

# TDA
grep -r "gudhi\|ripser\|giotto\|persistent\|homology\|betti" src/strategies/topological_data_analysis_regime.py

# Johansen
grep -r "from statsmodels.*johansen\|coint_johansen\|VECM" src/strategies/statistical_arbitrage_johansen.py
```

**Decisión**:
- Si NO implementa lo que promete → RENAMING obligatorio
- Si implementa parcialmente → RENAMING a versión "basic"
- Si implementa completamente → MANTENER nombre + documentar rigurosamente

---

### Fase 2: Renaming seguro (sin auditoría previa)

**Estrategias con renaming directo** (sin auditoría de código):
1. `momentum_quality.py` → `momentum_multiframe_confluence.py`
2. `htf_ltf_liquidity.py` → `liquidity_multiframe_zones.py`
3. `nfp_news_event_handler.py` → `news_nfp_handler.py`

**Proceso**:
1. Crear rama desde AIS:
   ```bash
   git checkout ALGORITMO_INSTITUCIONAL_SUBLIMINE
   git checkout -b claude/mandato9-phase1-renaming-20251114-<session-id>
   ```

2. Renombrar archivos:
   ```bash
   git mv src/strategies/momentum_quality.py src/strategies/momentum_multiframe_confluence.py
   git mv src/strategies/htf_ltf_liquidity.py src/strategies/liquidity_multiframe_zones.py
   git mv src/strategies/nfp_news_event_handler.py src/strategies/news_nfp_handler.py
   ```

3. Actualizar referencias:
   - `src/core/brain.py`: imports + fit_matrix keys
   - `config/active_strategies.yaml`: nombres
   - `tests/strategies/`: nombres de archivos de test

4. Actualizar docstrings:
   - Eliminar buzzwords agresivos
   - Lenguaje profesional

5. Commit:
   ```bash
   git add .
   git commit -m "refactor(strategies): Renaming honesto institucional (3 estrategias)

   - momentum_quality → momentum_multiframe_confluence
   - htf_ltf_liquidity → liquidity_multiframe_zones
   - nfp_news_event_handler → news_nfp_handler

   Razones:
   - Eliminar naming vago/engañoso
   - Describir edge real (multiframe confluence, zones)
   - Reducir longitud excesiva (nfp handler)
   - Alineación con estándares institucionales

   Refs: MANDATO 9 Fase 1 - Catálogo institucional"
   ```

---

### Fase 3: Renaming condicional (tras auditoría)

**Estrategias pendientes de auditoría**:
1. `fractal_market_structure.py`
2. `topological_data_analysis_regime.py`
3. `statistical_arbitrage_johansen.py`

**Proceso**:
1. Ejecutar auditoría de código (grep patterns arriba)
2. Decisión basada en hallazgos
3. Si renaming necesario → aplicar en rama separada:
   ```bash
   git checkout -b claude/mandato9-phase1-renaming-audit-20251114-<session-id>
   ```
4. Documentar hallazgos en commit message:
   ```
   AUDITORÍA REALIZADA: <estrategia>
   Resultado: NO implementa <concepto prometido>
   Evidencia: No se encontró <import/función esperada>
   Acción: Renaming honesto
   ```

---

## IMPACTO DEL RENAMING

### Archivos afectados (por cada renaming):
- ✅ `src/strategies/<nombre>.py` (renombrado)
- ✅ `src/core/brain.py` (imports + fit_matrix)
- ✅ `src/core/portfolio_manager.py` (imports si aplica)
- ✅ `config/active_strategies.yaml` (lista de estrategias)
- ✅ `tests/strategies/test_<nombre>.py` (renombrado)
- ✅ `docs/STRATEGY_CATALOGUE_20251114.md` (actualizar IDs)

### Riesgo:
- **Bajo**: Renaming es refactoring puro (no cambia lógica)
- **Mitigación**: Tests unitarios deben pasar post-renaming

### Testing post-renaming:
```bash
# Verificar que imports resuelven
python -c "from src.strategies.momentum_multiframe_confluence import MomentumQuality; print('OK')"

# Ejecutar tests
pytest tests/strategies/ -v
```

---

## CRONOGRAMA

### Semana 1 (MANDATO 9 Fase 1):
- [x] Crear `STRATEGY_CATALOGUE_20251114.md` (identifica naming engañoso)
- [x] Crear `STRATEGY_GOVERNANCE_20251114.md` (criterios de naming honesto)
- [x] Crear `STRATEGY_RENAMING_PROPOSAL_20251114.md` (este documento)

### Semana 2 (MANDATO 9 Fase 1 - continuación):
- [ ] Auditoría de código (fractal, TDA, Johansen)
- [ ] Renaming seguro (momentum, htf_ltf, nfp)
- [ ] Renaming condicional (fractal, TDA, Johansen)
- [ ] Commit + Push
- [ ] PR a ALGORITMO_INSTITUCIONAL_SUBLIMINE

---

## REFERENCIAS

- **MANDATO 9**: Cirugía Estratégica Institucional
- **AUDITORIA_MANDATOS_1_A_5_20251113.md**: Identifica naming engañoso
- **STRATEGY_CATALOGUE_20251114.md**: Catálogo completo de 24 estrategias
- **STRATEGY_GOVERNANCE_20251114.md**: Criterios de calidad de naming

---

**FIN DE PROPUESTA DE RENAMING**

**Decisión pendiente**: Operador humano aprueba renaming y timing de ejecución.
