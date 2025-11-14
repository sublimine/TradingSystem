# GOBERNANZA INSTITUCIONAL DE ESTRATEGIAS

**Proyecto**: SUBLIMINE TradingSystem
**Fecha**: 2025-11-14
**Mandato**: MANDATO 9 (Cirugía Estratégica) - FASE 1
**Autor**: Sistema de Gobernanza Institucional

---

## PROPÓSITO

Este documento define el ciclo de vida completo de estrategias de trading en SUBLIMINE TradingSystem, desde concepción hasta retiro. Establece criterios objetivos, medibles y auditables para promoción, degradación y retiro de estrategias.

**Principio rector**: Ninguna estrategia entra a producción sin evidencia empírica cuantitativa de edge. Ninguna estrategia permanece en producción si se degrada.

---

## ESTADOS DEL CICLO DE VIDA

### 1. EXPERIMENTAL

**Definición**: Estrategia en fase de investigación/desarrollo inicial. Concepto no validado.

**Criterios de entrada**:
- Idea fundamentada en:
  - Paper académico peer-reviewed, O
  - Evidencia empírica preliminar (backtest exploratório >0), O
  - Observación cuantificable de edge en mercado real
- Código implementado con:
  - Clase que hereda de `StrategyBase`
  - Método `evaluate()` funcional
  - Tests unitarios básicos (casos: sin datos, datos válidos, datos corruptos)
- Documentación mínima:
  - Edge declarado (qué ineficiencia explota)
  - Inputs requeridos (OHLCV, features, microestructura, etc.)
  - Outputs generados (señales con entry, SL, TP)

**Restricciones**:
- ❌ **NO puede operar en paper trading**
- ❌ **NO puede operar en producción**
- ✅ **Solo backtest en datos históricos**
- ✅ **No consume capital real ni simulado**

**Métricas requeridas**: Ninguna (exploratório)

**Duración máxima**: Indefinida (mientras se investiga)

**Responsable**: Research Team

---

### 2. PILOT

**Definición**: Estrategia con backtest exitoso. Concepto validado empíricamente. Entrando a paper trading.

**Criterios de promoción desde EXPERIMENTAL**:

#### Backtest in-sample (IS):
- **Período mínimo**: 12 meses de datos históricos
- **Sharpe ratio**: >1.0
- **Win rate**: >50%
- **Max drawdown**: <15%
- **Profit factor**: >1.3
- **Número de trades**: >50 (suficiente muestra estadística)

#### Backtest out-of-sample (OOS):
- **Período mínimo**: 20% del dataset total (mínimo 3 meses)
- **Degradación aceptable**:
  - Sharpe OOS ≥ 0.85 × Sharpe IS (máximo 15% degradación)
  - Win rate OOS ≥ Winrate IS - 5pp (ej: 60% → 55%)
  - Max DD OOS ≤ Max DD IS + 5pp (ej: 10% → 15%)

#### Walk-forward validation (WF):
- **Número de ventanas**: ≥3 períodos
- **Consistencia**: Sharpe >0.8 en al menos 2 de 3 ventanas

#### Integración arquitectónica:
- ✅ Genera señales compatibles con `QualityScorer`
- ✅ Respeta límites de `ExposureManager`
- ✅ Integración con `MicrostructureEngine` (si usa VPIN/OFI/depth)
- ✅ Integración con `MultiframeContext` (si usa HTF/LTF)
- ✅ SL/TP institucionales (no ATR, sino niveles estructurales)

#### Documentación:
- ✅ Archivo `docs/strategies/DESIGN_<nombre>_20251114.md` con:
  - Descripción cuantitativa del edge
  - Modelos matemáticos utilizados
  - Inputs/outputs detallados
  - Riesgos específicos y mitigaciones
  - Resultados de backtest (IS, OOS, WF)

**Restricciones**:
- ✅ **Puede operar en paper trading**
- ❌ **NO puede operar en producción con capital real**
- ✅ **Límite de riesgo**: 0.5% por trade (vs 2.0% en PRODUCTION)
- ✅ **Límite de exposición**: Máximo 2 trades simultáneos
- ✅ **Monitoreo estricto**: Revisión semanal de métricas

**Métricas de monitoreo (paper trading)**:
- Sharpe ratio (ventana 30 días)
- Win rate (ventana 30 días)
- Max DD (desde inicio de paper trading)
- Profit factor
- Average R-multiple
- Número de trades ejecutados

**Duración mínima**: 3 meses de paper trading exitoso

**Responsable**: Research Team + Risk Manager

**Criterios de degradación a EXPERIMENTAL**:
- Sharpe <0.5 durante 2 meses consecutivos en paper trading
- Drawdown >20% en paper trading
- Win rate <40% durante 2 meses
- Detección de data leakage o bug crítico

---

### 3. PRODUCTION

**Definición**: Estrategia aprobada para operar con capital real. Edge validado en vivo.

**Criterios de promoción desde PILOT**:

#### Paper trading exitoso:
- **Duración mínima**: 3 meses consecutivos
- **Sharpe ratio**: >1.3 (ventana 90 días)
- **Win rate**: >52%
- **Max drawdown**: <12%
- **Profit factor**: >1.5
- **Consistencia**: Sin spikes anómalos de PnL (±5σ)

#### Validación de comportamiento:
- ✅ Comportamiento estable (no errores, no crashes)
- ✅ Latencia de generación de señal <100ms
- ✅ No hay señales espurias (falsos positivos <5%)
- ✅ Integración con Risk Engine sin rechazos anómalos

#### Model Risk approval:
- ✅ Revisión por Risk Manager o Lead Developer
- ✅ Signoff en `docs/strategies/APPROVAL_<nombre>_20251114.md`:
  - Edge claramente definido
  - Backtests reproducibles
  - Paper trading exitoso documentado
  - Riesgos específicos identificados
  - Plan de monitoreo definido

#### Stress testing:
- ✅ Backtest en crisis históricas (2008, 2020, 2022)
- ✅ Comportamiento aceptable (no colapso)
- ✅ Drawdown en crisis <25%

**Restricciones**:
- ✅ **Puede operar con capital real**
- ✅ **Límite de riesgo**: 0.5% - 2.0% por trade (según `QualityScorer`)
- ✅ **Límite de exposición**:
  - Máximo 5 trades simultáneos por estrategia
  - Máximo 3% exposición total por estrategia (considerando correlación)
- ✅ **Monitoreo continuo**: Revisión diaria de métricas

**Métricas de monitoreo (producción)**:
- **Performance**:
  - Sharpe ratio (ventanas: 30d, 90d, 365d)
  - Sortino ratio
  - Win rate
  - Profit factor
  - Average R-multiple
  - Max DD desde peak
  - Ulcer Index
- **Operacional**:
  - Número de trades ejecutados vs esperado
  - Latencia de señal (p50, p95, p99)
  - Tasa de rechazo por Risk Engine
  - Slippage promedio
- **Risk**:
  - VaR 95% y 99%
  - CVaR (Expected Shortfall)
  - Drawdown actual vs límite
  - Correlación con otras estrategias activas

**Alertas automáticas**:
- ⚠️ Sharpe <1.0 durante 30 días → WARNING
- ⚠️ Drawdown >15% → WARNING
- ⚠️ Win rate <45% durante 30 días → WARNING
- 🚨 Sharpe <0.5 durante 60 días → CRITICAL (considerar degradación)
- 🚨 Drawdown >20% → CRITICAL
- 🚨 Win rate <40% durante 60 días → CRITICAL

**Responsable**: Portfolio Manager + Risk Manager

**Duración**: Indefinida (mientras métricas sean aceptables)

**Criterios de degradación a DEGRADED**:
- Sharpe <0.5 durante 2 meses consecutivos
- Drawdown >20% en 1 mes
- Win rate <40% durante 2 meses
- Profit factor <1.0 durante 2 meses
- Detección de regime change estructural que invalida edge

---

### 4. DEGRADED

**Definición**: Estrategia en producción con performance decaída. Bajo observación para recuperación o retiro.

**Entrada automática desde PRODUCTION** (cumple criterios de degradación)

**Acciones inmediatas**:
1. **Reducción de exposición**:
   - Límite de riesgo: 0.33% por trade (vs 2.0% en PRODUCTION)
   - Máximo 2 trades simultáneos (vs 5 en PRODUCTION)
   - Exposición total: 1.0% (vs 3.0% en PRODUCTION)

2. **Análisis de causas**:
   - ✅ **Regime change**: ¿Mercado cambió de estructura? (ej: trend → range, low vol → high vol)
   - ✅ **Strategy decay**: ¿Edge explotado por otros participantes?
   - ✅ **Data quality issues**: ¿Feeds degradados, VPIN/OFI erróneos?
   - ✅ **Bug introducido**: ¿Cambio reciente en código rompió algo?
   - ✅ **Parameter drift**: ¿Thresholds hardcoded quedaron obsoletos?

3. **Documentación**:
   - Crear `docs/strategies/DEGRADATION_ANALYSIS_<nombre>_20251114.md`:
     - Fecha de degradación
     - Métricas pre vs post degradación
     - Análisis de causas (ver arriba)
     - Plan de acción: recalibrar, reescribir o retirar

**Restricciones**:
- ⚠️ **Opera con capital real PERO con exposición reducida**
- ⚠️ **Monitoreo diario estricto**
- ⚠️ **Revisión semanal de métricas**

**Métricas de monitoreo (degraded)**:
- Mismas que PRODUCTION, pero con alertas más agresivas
- Comparación diaria vs baseline (última performance PRODUCTION)

**Salidas posibles**:

#### A) Recuperación → PRODUCTION
**Criterios**:
- Sharpe >1.0 durante 30 días consecutivos (tras recalibración/fix)
- Drawdown <10%
- Win rate >50%
- Causa de degradación identificada y corregida

#### B) Retiro → RETIRED
**Criterios**:
- Sharpe negativo durante 3 meses
- No se identifica causa corregible
- Edge estructuralmente desaparecido
- Costo de mantenimiento > beneficio esperado

**Duración máxima**: 6 meses (si no recupera → RETIRED)

**Responsable**: Portfolio Manager + Risk Manager + Research Team

---

### 5. RETIRED

**Definición**: Estrategia desactivada permanentemente. No opera. Archivada para referencia histórica.

**Criterios de entrada**:
- Desde DEGRADED: No recupera en 6 meses O cumple criterios de retiro
- Desde PRODUCTION: Detección de bug crítico O data leakage O fraude conceptual
- Desde PILOT: Falló paper trading (no promocionó en 12 meses)
- Desde EXPERIMENTAL: Investigación abandonada

**Acciones**:
1. **Desactivación completa**:
   - ❌ Eliminar de lista activa en `brain.py` / `config/active_strategies.yaml`
   - ❌ Cerrar todas las posiciones abiertas (si las hay)
   - ❌ No generar más señales

2. **Archivado**:
   - ✅ Mover código a `src/strategies/retired/`
   - ✅ Crear `docs/strategies/RETIREMENT_<nombre>_20251114.md`:
     - Fecha de retiro
     - Motivo (degradación, bug, data leakage, etc.)
     - Performance histórica (mejor Sharpe, peor DD, etc.)
     - Lecciones aprendidas (qué funcionó, qué falló)

3. **Preservación de datos**:
   - ✅ Archivar backtests en `backtests/retired/<nombre>/`
   - ✅ Archivar trades históricos (si operó en vivo)
   - ✅ Mantener documentación para auditoría futura

**Restricciones**:
- ❌ **NO puede operar nunca más** (sin resurrección directa)
- ❌ **NO consume recursos computacionales**
- ✅ **Código preservado para referencia**

**Re-activación**:
- Requiere crear **nueva estrategia** (nuevo ID, nuevo nombre)
- Pasar por EXPERIMENTAL → PILOT → PRODUCTION desde cero
- Documentar qué cambió vs versión anterior RETIRED

**Responsable**: Research Team (archivado) + Portfolio Manager (signoff)

---

## CRITERIOS TRANSVERSALES

### Criterios de calidad de señal

Toda estrategia en PILOT o superior debe generar señales que incluyan:

#### Campos obligatorios:
```python
{
    'strategy_name': str,          # Nombre de estrategia
    'symbol': str,                 # Símbolo (ej: 'EURUSD.pro')
    'direction': str,              # 'LONG' o 'SHORT'
    'entry_price': float,          # Precio de entrada
    'stop_loss': float,            # SL institucional (nivel estructural, NO ATR)
    'take_profit': float,          # TP (opcional, puede ser trailing)
    'metadata': {
        'signal_strength': float,       # 0.0-1.0
        'confluence_score': float,      # 0.0-1.0
        'mtf_confluence': float,        # 0.0-1.0 (si usa multiframe)
        'regime_confidence': float,     # 0.0-1.0
        'vpin': float,                  # Si usa microestructura
        'ofi': float,                   # Si usa microestructura
        'structure_alignment': float,   # 0.0-1.0
    }
}
```

#### Stop Loss institucional (NO ATR):
- ❌ **Prohibido**: SL basado en ATR (ej: 2×ATR)
- ❌ **Prohibido**: SL a distancia fija (ej: 20 pips, 50 pips)
- ✅ **Obligatorio**: SL donde la idea de trading es **inválida**
  - Breakout: SL detrás del rango
  - Order block: SL más allá del OB
  - Liquidity sweep: SL más allá del nivel swept
  - Mean reversion: SL en extremo opuesto del rango

#### Take Profit institucional:
- ✅ **Preferido**: TP basado en:
  - Estructura (próximo swing, order block, FVG)
  - Estadísticas (MFE promedio, percentile 75-90 de winners)
  - Ratio R:R mínimo 1.5:1 (preferido 2:1+)
- ✅ **Alternativo**: Trailing stop basado en estructura
- ❌ **Evitar**: TP fijo arbitrario sin justificación

### Criterios de compatibilidad con Risk Engine

Toda estrategia debe ser compatible con:

#### QualityScorer:
- Metadata contiene campos requeridos (signal_strength, confluence, etc.)
- Quality score resultante ≥0.60 para señales válidas

#### RiskAllocator:
- Respeta límites dinámicos (0.33%-2.0% según quality)
- No intenta forzar posiciones cuando RiskAllocator rechaza

#### ExposureManager:
- Respeta límites de exposición:
  - Total: 6.0%
  - Por símbolo: 2.0%
  - Por estrategia: 3.0%
  - Por correlación: 5.0%

#### CircuitBreaker:
- Si CircuitBreaker está abierto → NO generar señales

### Criterios de naming honesto

#### ❌ Naming prohibido (engañoso):
- Términos académicos sin implementación real:
  - "Johansen" → sin uso de `statsmodels.tsa.vector_ar.vecm.coint_johansen()`
  - "Topological Data Analysis" → sin GUDHI/Ripser
  - "Fractal" → sin análisis de dimensión fractal real
- Términos vagos:
  - "quality", "smart", "elite", "advanced" sin definición cuantitativa
- Buzzwords retail:
  - "killer", "sniper", "holy grail"

#### ✅ Naming correcto (honesto):
- Describe QUÉ HACE la estrategia:
  - `momentum_multiframe_confluence` (momentum + MTF)
  - `liquidity_sweep_reversal` (liquidity sweep + reversión)
  - `order_flow_vpin_reversal` (order flow + VPIN extremo)
- Indica EDGE explotado:
  - `breakout_volume_confirmation` (breakout validado por volumen)
  - `mean_reversion_statistical` (mean reversion con z-score)

---

## MATRIZ DE COMPATIBILIDAD SÍMBOLO-ESTRATEGIA

Toda estrategia debe declarar símbolos compatibles:

```python
class MomentumQuality(StrategyBase):
    METADATA = {
        'supported_symbols': ['EURUSD', 'GBPUSD', 'XAUUSD', 'BTCUSD', 'US50'],
        'unsupported_symbols': ['EXOTIC_PAIRS'],  # ej: USDTRY (demasiado volátil)
    }
```

**Validación en runtime**:
- Si señal generada para símbolo no soportado → rechazo automático con log WARNING

**Matriz global** (ejemplo):

| Estrategia | FX Majors | FX Minors | Metals | Crypto | Indices | Commodities |
|------------|-----------|-----------|--------|--------|---------|-------------|
| S001 - momentum_quality | ✅ | ⚠️ | ✅ | ✅ | ✅ | ❌ |
| S004 - liquidity_sweep | ✅ | ✅ | ✅ | ⚠️ | ⚠️ | ❌ |
| S014 - mean_reversion_statistical | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ |
| S015 - kalman_pairs_trading | ✅ (pares correlacionados) | ❌ | ❌ | ✅ (pares) | ❌ | ❌ |

---

## PROCESO DE REVISIÓN PERIÓDICA

### Revisión mensual (todas las estrategias PRODUCTION)
**Responsable**: Portfolio Manager + Risk Manager

**Checklist**:
- [ ] Sharpe ratio vs target (>1.3)
- [ ] Win rate vs target (>52%)
- [ ] Max DD vs límite (<12%)
- [ ] Número de trades ejecutados vs esperado (±30%)
- [ ] Slippage promedio vs baseline
- [ ] Correlación con otras estrategias (detectar factor crowding)
- [ ] Alertas disparadas (WARNING/CRITICAL)

**Salidas**:
- ✅ **PASS**: Continúa en PRODUCTION
- ⚠️ **WATCH**: Bajo observación (1 métrica degradada)
- 🚨 **DEGRADE**: Promoción a DEGRADED

### Revisión trimestral (todas las estrategias)
**Responsable**: Research Team + Portfolio Manager + Risk Manager

**Checklist**:
- [ ] Análisis de regime changes (¿estrategia sigue alineada con régimen actual?)
- [ ] Thresholds hardcoded obsoletos (¿necesitan recalibración?)
- [ ] Backtests actualizados (últimos 12 meses)
- [ ] Correlación entre estrategias (factor crowding)
- [ ] Estrategias PILOT: ¿listas para PRODUCTION?
- [ ] Estrategias DEGRADED: ¿recuperan o se retiran?

**Salidas**:
- Plan de acción trimestral (recalibraciones, upgrades, retiros)

### Revisión anual (portfolio completo)
**Responsable**: CTO + Portfolio Manager + Risk Manager

**Checklist**:
- [ ] Performance del portfolio completo (Sharpe, Sortino, Calmar)
- [ ] Diversificación real (correlaciones, factor exposures)
- [ ] Estrategias retiradas: lecciones aprendidas
- [ ] Pipeline de nuevas estrategias (EXPERIMENTAL → PILOT)
- [ ] Roadmap de research para siguiente año

**Salidas**:
- Estrategia de portfolio anual
- Presupuesto de research

---

## PROCESS FLOWCHART

```
EXPERIMENTAL
     |
     | Backtest exitoso (Sharpe >1.0, 12 meses, OOS validation)
     ↓
  PILOT
     |
     | Paper trading exitoso (3 meses, Sharpe >1.3, sin anomalías)
     ↓
PRODUCTION
     |
     |---→ Performance degrada (Sharpe <0.5, DD >20%, WR <40%)
     |          ↓
     |      DEGRADED
     |          |
     |          |---→ Recupera (Sharpe >1.0, 30 días) → PRODUCTION
     |          |
     |          |---→ No recupera (6 meses) → RETIRED
     |          |
     |          |---→ Causa no corregible → RETIRED
     |
     |---→ Bug crítico / Data leakage → RETIRED
```

---

## ANTI-PATTERNS (PROHIBIDOS)

### ❌ Promoción prematura
- NO promover EXPERIMENTAL → PILOT sin backtest riguroso (12 meses + OOS)
- NO promover PILOT → PRODUCTION sin paper trading (3 meses mínimo)

### ❌ Mantener estrategias zombie
- NO mantener estrategias DEGRADED >6 meses sin recuperación
- NO mantener estrategias con Sharpe negativo en PRODUCTION

### ❌ Promoción por presión
- NO promover estrategia porque "llevamos X meses desarrollándola"
- NO promover estrategia porque "necesitamos más estrategias"

### ❌ Retiro prematuro
- NO retirar estrategia PRODUCTION por 1 mes malo (usar DEGRADED primero)
- NO retirar sin análisis de causas documentado

---

## MÉTRICAS DE CALIDAD DEL PORTFOLIO

**Target de diversificación**:
- Correlación promedio entre estrategias PRODUCTION: <0.40
- Máximo 3 estrategias del mismo cluster (Order Flow, Liquidity, etc.)
- Al menos 2 tipos de edge diferentes (momentum, mean reversion, liquidity, etc.)

**Target de performance**:
- Sharpe del portfolio: >1.5
- Sortino ratio: >2.0
- Calmar ratio: >2.0
- Max DD histórico: <20%
- Win rate: >55%

**Target operacional**:
- Latencia p95 de generación de señal: <100ms
- Uptime del sistema: >99.5%
- Tasa de rechazo por Risk Engine: <30% (señales de baja calidad filtradas correctamente)

---

## APÉNDICE: PLANTILLAS

### Plantilla: DESIGN_<nombre>_20251114.md

```markdown
# DISEÑO DE ESTRATEGIA: <nombre>

**Fecha**: 2025-11-14
**Autor**: Research Team
**Estado**: EXPERIMENTAL / PILOT / PRODUCTION / DEGRADED / RETIRED

---

## EDGE DECLARADO

Descripción cuantitativa del edge:
- ¿Qué ineficiencia de mercado explota?
- ¿Por qué funciona? (base teórica)
- ¿Cuándo deja de funcionar? (límites del edge)

---

## MODELOS MATEMÁTICOS

### Entrada
- Condiciones: ...
- Thresholds: ...
- Confirmaciones: ...

### Stop Loss
- Lógica: SL donde idea es inválida
- Cálculo: ...

### Take Profit
- Lógica: Estructura / MFE / R:R
- Cálculo: ...

---

## INPUTS REQUERIDOS

- OHLCV: Sí/No, timeframe, lookback
- Features: VPIN, OFI, ATR, etc.
- Microestructura: Sí/No (depth, footprint, etc.)
- Multiframe: Sí/No (HTF, MTF, LTF)
- News feed: Sí/No

---

## OUTPUTS GENERADOS

- Señales: Formato completo (ver criterios de calidad)
- Metadata: signal_strength, confluence, etc.

---

## RIESGOS ESPECÍFICOS

1. **Riesgo de régimen**: ¿En qué régimen NO funciona? (ej: mean reversion en trends)
2. **Riesgo de data**: ¿Qué pasa si VPIN/OFI degradado?
3. **Riesgo de latencia**: ¿Es sensible a slippage?
4. **Riesgo de crowding**: ¿Overlap con otras estrategias?

---

## MITIGACIONES

- Régimen: Filtro de régimen (volatility_regime_adaptation)
- Data: Health checks, fallback a modo degradado
- Latencia: Límites de slippage, rechazo si >X pips
- Crowding: Análisis de correlación, límites de cluster

---

## BACKTEST RESULTS

### In-sample
- Período: YYYY-MM-DD a YYYY-MM-DD
- Sharpe: X.XX
- Win rate: XX%
- Max DD: XX%
- Profit factor: X.XX
- Trades: NNN

### Out-of-sample
- Período: YYYY-MM-DD a YYYY-MM-DD
- Sharpe: X.XX (degradación: X%)
- Win rate: XX%
- Max DD: XX%

### Walk-forward
- Ventana 1: Sharpe X.XX
- Ventana 2: Sharpe X.XX
- Ventana 3: Sharpe X.XX

---

## PAPER TRADING RESULTS (si aplica)

- Inicio: YYYY-MM-DD
- Sharpe (90 días): X.XX
- Win rate: XX%
- Max DD: XX%

---

## PRODUCCIÓN RESULTS (si aplica)

- Inicio: YYYY-MM-DD
- Sharpe (365 días): X.XX
- Win rate: XX%
- Max DD: XX%

---
```

---

**FIN DE GOBERNANZA INSTITUCIONAL**

**Responsable de mantenimiento**: Portfolio Manager + Risk Manager
**Revisión**: Trimestral (o cuando cambios significativos)
