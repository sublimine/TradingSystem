# ESTRATEGIAS DEPRECATED - CONCEPTOS RETAIL SMC

**Autor:** Arquitecto Cuant Institucional
**Fecha:** 2025-11-16
**Mandato:** DELTA - Sistema Cerrado, 24 Estrategias, CERO ATR

---

## ❌ ESTRATEGIAS MARCADAS COMO DEPRECATED

Las siguientes estrategias están **DESACTIVADAS** y marcadas para deprecation debido a que sus conceptos base son **RETAIL SMC (Smart Money Concepts)**, no institucionales cuantitativos.

### 1. **fvg_institutional.py** - Fair Value Gaps
**Problema:**
- FVG (Fair Value Gap) es concepto SMC retail sin base cuantitativa
- "Gap must fill" NO tiene evidencia institucional
- Los gaps se rellenan cuando hay razón microestructural específica, NO automáticamente
- **No hay papers académicos que validen FVG como concepto institucional**

**Veredicto:** RETAIL PATTERN MATCHING
**Acción:** DESACTIVAR. No incluir en perfiles de producción.

---

### 2. **order_block_institutional.py** - Order Blocks
**Problema:**
- Order Block es concepto SMC (Smart Money Concepts) - marketing retail disfrazado de "institucional"
- Un "order block" es solo un swing high/low con volumen
- NO hay evidencia de que institucionales "dejan órdenes" en bloques específicos más que en cualquier otro soporte/resistencia
- Es observación post-hoc sin poder predictivo cuantificable

**Veredicto:** SMC MARKETING, NO INSTITUCIONAL REAL
**Acción:** DESACTIVAR. No incluir en perfiles de producción.

---

### 3. **idp_inducement_distribution.py** - IDP Pattern
**Problema:**
- IDP (Inducement-Distribution-Phase) es Wyckoff-style pattern matching bastardizado
- Subjetivo, no quantificable
- No tiene backtests institucionales published
- Es "story telling" chart reading, NO order flow cuantitativo

**Veredicto:** WYCKOFF FOLKLÓRICO, NO INSTITUCIONAL
**Acción:** DESACTIVAR. No incluir en perfiles de producción.

---

### 4. **htf_ltf_liquidity.py** - HTF-LTF Multi-Timeframe
**Problema:**
- HTF-LTF (Higher Timeframe - Lower Timeframe) es pattern matching multi-timeframe retail
- "Price touched HTF level on LTF" NO es edge
- Es observación post-hoc sin poder predictivo
- Falta validación con order flow institucional (OFI/CVD/VPIN)

**Veredicto:** MULTI-TIMEFRAME RETAIL PATTERN MATCHING
**Acción:** DESACTIVAR. No incluir en perfiles de producción.

---

## ¿POR QUÉ ESTAS 4 SON RETAIL, NO INSTITUCIONALES?

**Criterios de clasificación:**

| Criterio | Institucional (GREEN) | Retail (BROKEN) |
|----------|----------------------|-----------------|
| **Base teórica** | Papers académicos (Easley, Hasbrouck, Harris) | Marketing SMC / Wyckoff folklórico |
| **Edge** | Microestructura cuantificada (OFI, CVD, VPIN) | Pattern matching subjetivo |
| **Backtest** | Quantificable, replicable | Subjetivo, post-hoc observation |
| **Institucional real** | Sí (usado por hedge funds/prop) | No (retail educators) |

**Todas las 4 BROKEN tienen confirmación OFI/CVD añadida**, pero el **edge base es retail**. Es como poner motor Ferrari en un Fiat Panda - sigue siendo un Panda.

---

## ALTERNATIVAS INSTITUCIONALES

En lugar de estas 4 retail, usar las **5 estrategias GREEN institucionales**:

1. **breakout_volume_confirmation** - Breakouts institucionales con OFI surge
2. **liquidity_sweep** - Stop hunts + absorción institucional
3. **ofi_refinement** - OFI extremes (z-score) + VPIN clean
4. **order_flow_toxicity** - Fade toxic flow (VPIN extremes)
5. **vpin_reversal_extreme** - VPIN exhaustion reversals

Estas 5 tienen:
- ✅ Edge basado en microestructura real (order flow)
- ✅ Research académico sólido
- ✅ Lógica cuantificable y replicable
- ✅ CERO ATR en SL/TP (estructural)

---

## ACCIÓN REQUERIDA

**Para desactivar estas 4 estrategias:**

1. **En runtime profiles:** Comentar o remover estas 4 de `active_strategies`
2. **En backtests:** NO incluir en validaciones
3. **En producción:** NUNCA activar

**Si en el futuro se decide rescatarlas:**

Requeriría **reescritura COMPLETA** del edge base, reemplazando conceptos SMC con:
- Microestructura real (OFI, CVD, VPIN)
- Research académico validado
- SL/TP estructural (NO ATR)
- Backtests cuantitativos replicables

**Hasta entonces:** DEPRECATED.

---

**Nota institucional:**
Un sistema cuantitativo serio NO puede contener conceptos retail disfrazados de "institucionales". Estos 4 fallan el comité de inversión institucional.

**Veredicto final:** USE LAS 5 GREEN. IGNORE LAS 4 BROKEN.
