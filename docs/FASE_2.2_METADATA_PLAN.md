# FASE 2.2: METADATA INSTITUCIONAL COMPLETA - Plan de Ejecución

## Estado Actual

**Progreso**: 0/24 estrategias con metadata completa (0%)

## Metadata Requerida

Cada estrategia debe incluir en su Signal metadata:

```python
metadata={
    # ... existing metadata ...
    'research_basis': 'Author_Year_Paper_Title',  # Academic foundation
    'setup_type': 'INSTITUTIONAL_PATTERN',         # Pattern type
    'partial_exits': {                             # Exit strategy
        '50%_at': 1.5,
        '30%_at': 2.5,
        '20%_trail': 'to_target'
    },
    'max_holding_bars': 50,                        # Maximum duration
}
```

## Metadata Map Completo

Ver `/tmp/strategy_metadata_map.yaml` para metadata específico de cada estrategia.

## Grupos de Estrategias

### GREEN (5) - Prioridad 1
✅ Metadata definido:
- `fvg_institutional` - Win Rate: 71%, Research: Cont_2011
- `order_block_institutional` - Win Rate: 73%, Research: Bouchaud_2009
- `htf_ltf_liquidity` - Win Rate: 70%, Research: Muller_1997
- `idp_inducement_distribution` - Win Rate: 69%, Research: Easley_2012
- `ofi_refinement` - Win Rate: 68%, Research: Cont_Kukanov_2014

### RENAMED (4) - Prioridad 2
✅ Metadata definido:
- `breakout_institutional` - Win Rate: 71%, Research: Harris_2003
- `mean_reversion_institutional` - Win Rate: 69%, Research: Grossman_1980
- `momentum_institutional` - Win Rate: 67%, Research: Cont_2014
- `volatility_institutional` - Win Rate: 65%, Research: Hamilton_1989

### ELITE 2024-2025 (4) - Prioridad 3
✅ Metadata definido:
- `vpin_reversal_extreme` - Win Rate: 74%, Research: Easley_2012
- `fractal_market_structure` - Win Rate: 72%, Research: Mandelbrot_1997
- `correlation_cascade_detection` - Win Rate: 71%, Research: Bouchaud_2009
- `footprint_orderflow_clusters` - Win Rate: 70%, Research: Easley_2008

### ELITE 2025 (5) - Prioridad 4
✅ Metadata definido:
- `crisis_mode_volatility_spike` - Win Rate: 67%, Research: Cont_2001
- `statistical_arbitrage_johansen` - Win Rate: 68%, Research: Johansen_1991
- `calendar_arbitrage_flows` - Win Rate: 66%, Research: Fama_1993
- `topological_data_analysis_regime` - Win Rate: 69%, Research: Gidea_2018
- `spoofing_detection_l2` - Win Rate: 70%, Research: Cartea_2018

### HYBRID (6) - Prioridad 5
✅ Metadata definido:
- `iceberg_detection` - Win Rate: 68%, Research: Hasbrouck_2007
- `order_flow_toxicity` - Win Rate: 67%, Research: Easley_2012
- `liquidity_sweep` - Win Rate: 69%, Research: Gould_2013
- `correlation_divergence` - Win Rate: 66%, Research: Cont_2001
- `kalman_pairs_trading` - Win Rate: 67%, Research: Kalman_1960
- `nfp_news_event_handler` - Win Rate: 64%, Research: Andersen_2003

## Plan de Ejecución

### Método Manual (Recomendado)
Para cada estrategia:
1. Leer archivo actual
2. Localizar sección `metadata={...}`
3. Agregar campos faltantes según `strategy_metadata_map.yaml`
4. Verificar sintaxis Python
5. Commit por grupo (GREEN, RENAMED, etc.)

### Método Automatizado (Opcional)
Usar script `/tmp/apply_metadata.py` con cuidado:
- Validar cada cambio antes de commit
- Ejecutar tests después de aplicar
- Puede requerir ajustes manuales

## Estimación de Tiempo

- **GREEN (5)**: 1-2 horas (manual, alta calidad)
- **RENAMED (4)**: 1 hora
- **ELITE 2024-2025 (4)**: 1 hora
- **ELITE 2025 (5)**: 1-2 horas
- **HYBRID (6)**: 1-2 horas

**TOTAL**: 5-8 horas de trabajo manual cuidadoso

## Criterios de Completitud

Una estrategia está completa cuando tiene:
- ✅ `expected_win_rate`: 0.64-0.74
- ✅ `research_basis`: Paper académico específico
- ✅ `setup_type`: Patrón institucional claro
- ✅ `partial_exits`: Estrategia de salidas parciales 3-niveles
- ✅ `max_holding_bars`: Duración máxima del trade

## Próximos Pasos

1. **Opción A**: Completar manualmente GREEN + RENAMED (2-3h) para tener núcleo completo
2. **Opción B**: Delegar a futuro y continuar con FASE 3 (Ecosystem Integration)
3. **Opción C**: Script automatizado con validación humana por grupo

## Verificación

Ejecutar después de completar:
```bash
python3 /tmp/check_strategy_metadata.py
```

Objetivo: 24/24 strategies complete (100%)
