# INVENTARIO COMPLETO DE ESTRATEGIAS
## ALGORITMO INSTITUCIONAL SUBLIMINE

**Fecha**: 2025-11-13
**Total Estrategias**: 24
**Líneas Totales**: ~9,700 (sin contar strategy_base)

---

## LISTA COMPLETA (ordenadas por tamaño)

| # | Estrategia | Clase | Líneas | Estado Inicial |
|---|------------|-------|--------|----------------|
| 1 | nfp_news_event_handler | NFPNewsEventHandler | 777 | ⏳ Pendiente auditoría |
| 2 | fvg_institutional | FVGInstitutional | 574 | ⏳ Pendiente auditoría |
| 3 | footprint_orderflow_clusters | FootprintOrderflowClusters | 531 | ⏳ Pendiente auditoría |
| 4 | htf_ltf_liquidity | HTFLTFLiquidity | 501 | ⏳ Pendiente auditoría |
| 5 | breakout_volume_confirmation | (nombre por confirmar) | 462 | ⏳ Pendiente auditoría |
| 6 | statistical_arbitrage_johansen | StatisticalArbitrageJohansen | 445 | ⏳ Pendiente auditoría |
| 7 | idp_inducement_distribution | (nombre por confirmar) | 445 | ⏳ Pendiente auditoría |
| 8 | order_flow_toxicity | OrderFlowToxicityStrategy | 437 | ⏳ Pendiente auditoría |
| 9 | liquidity_sweep | LiquiditySweepStrategy | 426 | ⚠️ 2 bugs críticos detectados |
| 10 | mean_reversion_statistical | MeanReversionStatistical | 405 | ⏳ Pendiente auditoría |
| 11 | order_block_institutional | OrderBlockInstitutional | 395 | ⏳ Pendiente auditoría |
| 12 | calendar_arbitrage_flows | CalendarArbitrageFlows | 395 | ⏳ Pendiente auditoría |
| 13 | iceberg_detection | IcebergDetection | 357 | ⏳ Pendiente auditoría |
| 14 | crisis_mode_volatility_spike | CrisisModeVolatilitySpike | 349 | ⏳ Pendiente auditoría |
| 15 | vpin_reversal_extreme | VPINReversalExtreme | 345 | ⏳ Pendiente auditoría |
| 16 | ofi_refinement | OFIRefinement | 322 | ⚠️ Z-score clipping verificado OK |
| 17 | topological_data_analysis_regime | TopologicalDataAnalysisRegime | 303 | ⏳ Pendiente auditoría |
| 18 | fractal_market_structure | FractalMarketStructure | 295 | ⏳ Pendiente auditoría |
| 19 | kalman_pairs_trading | KalmanPairsTrading | 294 | ✅ Auditoría previa: LIMPIO |
| 20 | correlation_cascade_detection | CorrelationCascadeDetection | 275 | ⏳ Pendiente auditoría |
| 21 | volatility_regime_adaptation | VolatilityRegimeAdaptation | 267 | ⚠️ 1 bug (deque pop redundante) |
| 22 | correlation_divergence | CorrelationDivergence | 253 | ⏳ Pendiente auditoría |
| 23 | momentum_quality | MomentumQuality | 243 | ⚠️ 1 bug crítico (index out of bounds) |
| 24 | spoofing_detection_l2 | SpoofingDetectionL2 | 192 | ⏳ Pendiente auditoría |

---

## CLASIFICACIÓN PRELIMINAR POR CATEGORÍA

### Order Flow & Microstructure (9)
1. footprint_orderflow_clusters
2. order_flow_toxicity
3. ofi_refinement
4. iceberg_detection
5. spoofing_detection_l2
6. order_block_institutional
7. liquidity_sweep
8. idp_inducement_distribution
9. vpin_reversal_extreme

### Statistical & Mean Reversion (4)
1. mean_reversion_statistical
2. statistical_arbitrage_johansen
3. kalman_pairs_trading
4. correlation_divergence

### Institutional Patterns (4)
1. fvg_institutional (Fair Value Gap)
2. htf_ltf_liquidity (Higher/Lower Timeframe)
3. breakout_volume_confirmation
4. fractal_market_structure

### Regime & Volatility (4)
1. volatility_regime_adaptation
2. crisis_mode_volatility_spike
3. momentum_quality
4. topological_data_analysis_regime

### Event-Driven (3)
1. nfp_news_event_handler
2. calendar_arbitrage_flows
3. correlation_cascade_detection

---

## UBICACIÓN EN REPOSITORIO

**Directorio principal**: `src/strategies/`

**Archivos relacionados**:
- `strategy_base.py` (154 líneas) - Clase base abstracta
- `__init__.py` - Registro de estrategias

**Documentación existente**:
- `dossier/03_ESTRATEGIAS/` - Docs por estrategia (parcial)
- `transfer/01_docs/strategies/` - Docs legacy

---

## ESTADO DE BUGS CONOCIDOS (Auditoría Mandato 1)

### Críticos
- liquidity_sweep: Array bounds sin validación (L214, L320)
- momentum_quality: Index out of bounds (L226)

### Importantes
- volatility_regime_adaptation: Deque pop redundante (L95)
- order_flow_toxicity: Deque pop redundante (L143-145)
- 6 estrategias adicionales con issues menores

### Limpias
- kalman_pairs_trading: ✅ Sin issues detectados

---

## PRÓXIMOS PASOS

1. ⏳ Auditoría exhaustiva institucional vs retail (MANDATO 2)
2. ⏳ Evaluación de fundamento cuantitativo
3. ⏳ Clasificación por estado: funcional / retail / duplicado
4. ⏳ Propuestas de mejora o reimplementación
5. ⏳ Creación de documentación unificada en `docs/estrategias/`

---

**Status**: Inventario completo - Listo para auditoría detallada
**Timestamp**: 2025-11-13
