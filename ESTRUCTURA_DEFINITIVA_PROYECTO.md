# ESTRUCTURA DEFINITIVA DEL PROYECTO
## ALGORITMO INSTITUCIONAL SUBLIMINE

**Fecha**: 2025-11-13
**Estándar**: Institucional - Orden Militar

---

## ARQUITECTURA PROPUESTA

```
ALGORITMO_INSTITUCIONAL_SUBLIMINE/
├── README.md                           # Entry point principal
├── CHANGELOG.md                        # Historial de cambios
├── LICENSE                             # Licencia
│
├── src/                                # CÓDIGO PRINCIPAL
│   ├── __init__.py
│   ├── core/                           # Orquestación y motores
│   │   ├── __init__.py
│   │   ├── brain.py                    # Orquestador central
│   │   ├── signal_bus.py               # Sistema de eventos
│   │   ├── conflict_arbiter.py         # Resolución de conflictos
│   │   ├── decision_ledger.py          # Registro de decisiones
│   │   ├── portfolio_manager.py        # Gestión de portfolio
│   │   ├── position_manager.py         # Gestión de posiciones
│   │   ├── risk_manager.py             # Gestión de riesgo
│   │   ├── regime_engine.py            # Detección de régimen
│   │   ├── regime_detector.py          # Detector de régimen
│   │   ├── ml_supervisor.py            # Supervisor ML
│   │   ├── ml_adaptive_engine.py       # Motor adaptativo ML
│   │   ├── mtf_data_manager.py         # Manager multi-timeframe
│   │   ├── position_sizer.py           # Cálculo de tamaño
│   │   ├── budget_manager.py           # Gestión de presupuesto
│   │   ├── correlation_tracker.py      # Tracking de correlación
│   │   ├── signal_schema.py            # Schema de señales
│   │   └── strategy_adapter.py         # Adapter de estrategias
│   │
│   ├── strategies/                     # ESTRATEGIAS DE TRADING
│   │   ├── __init__.py
│   │   ├── strategy_base.py            # Clase base abstracta
│   │   │
│   │   ├── order_flow/                 # Order Flow Strategies (APROBADAS)
│   │   │   ├── __init__.py
│   │   │   ├── ofi_refinement.py                    # ⭐ ELITE
│   │   │   ├── spoofing_detection_l2.py             # ⭐ ELITE
│   │   │   ├── vpin_reversal_extreme.py             # ⭐ ELITE
│   │   │   ├── order_flow_toxicity.py               # ✅ INSTITUCIONAL
│   │   │   ├── order_block_institutional.py         # ✅ INSTITUCIONAL
│   │   │   ├── footprint_orderflow_clusters.py      # ⚠️ MEJORAR (degraded mode)
│   │   │   ├── iceberg_detection.py                 # ⚠️ MEJORAR (proxies)
│   │   │   └── liquidity_sweep.py                   # ⚠️ MEJORAR (level detection)
│   │   │
│   │   ├── statistical/                # Statistical Strategies
│   │   │   ├── __init__.py
│   │   │   ├── kalman_pairs_trading.py              # ⚠️ MEJORAR (sin cointegration)
│   │   │   └── mean_reversion_statistical.py        # ⚠️ MEJORAR (sin ADF test)
│   │   │
│   │   ├── patterns/                   # Institutional Patterns (APROBADAS)
│   │   │   ├── __init__.py
│   │   │   ├── fvg_institutional.py                 # ✅ INSTITUCIONAL
│   │   │   ├── htf_ltf_liquidity.py                 # ✅ INSTITUCIONAL
│   │   │   ├── breakout_volume_confirmation.py      # ✅ INSTITUCIONAL
│   │   │   └── swing_structure_breaks.py            # ⚠️ RENOMBRADO (ex-fractal)
│   │   │
│   │   ├── regime/                     # Regime Detection (APROBADAS)
│   │   │   ├── __init__.py
│   │   │   ├── volatility_regime_adaptation.py      # ✅ INSTITUCIONAL
│   │   │   ├── crisis_mode_volatility_spike.py      # ✅ INSTITUCIONAL
│   │   │   ├── momentum_confluence.py               # ⚠️ RENOMBRADO (ex-momentum_quality)
│   │   │   └── point_cloud_regime.py                # ⚠️ RENOMBRADO (ex-TDA)
│   │   │
│   │   ├── event_driven/               # Event-Driven (APROBADAS)
│   │   │   ├── __init__.py
│   │   │   ├── nfp_news_event_handler.py            # ✅ INSTITUCIONAL
│   │   │   ├── calendar_arbitrage_flows.py          # ✅ INSTITUCIONAL
│   │   │   └── correlation_cascade_detection.py     # ✅ INSTITUCIONAL
│   │   │
│   │   └── deprecated/                 # Estrategias obsoletas (NO USAR)
│   │       ├── __init__.py
│   │       ├── README_DEPRECATED.md                 # Razones de deprecación
│   │       ├── statistical_arbitrage_johansen.py    # 🔴 FRAUDE (no es Johansen real)
│   │       ├── correlation_divergence.py            # 🔴 ERROR CONCEPTUAL
│   │       └── idp_inducement_distribution.py       # 🔴 APROXIMACIONES DÉBILES
│   │
│   ├── features/                       # FEATURE ENGINEERING
│   │   ├── __init__.py
│   │   ├── technical_indicators.py     # Indicadores técnicos
│   │   ├── order_flow.py               # Order flow metrics
│   │   ├── microstructure.py           # Microestructura
│   │   ├── statistical_models.py       # Modelos estadísticos
│   │   ├── derived_features.py         # Features derivadas
│   │   ├── gaps.py                     # Gap analysis
│   │   ├── mtf.py                      # Multi-timeframe
│   │   ├── ofi.py                      # Order Flow Imbalance
│   │   ├── orderbook_l2.py             # Level 2 orderbook
│   │   └── tns.py                      # TNS metrics
│   │
│   ├── gatekeepers/                    # CONTROL DE CALIDAD
│   │   ├── __init__.py
│   │   ├── spread_monitor.py           # Monitor de spread
│   │   ├── kyles_lambda.py             # Kyle's Lambda estimator
│   │   ├── epin_estimator.py           # ePIN estimator
│   │   ├── gatekeeper_adapter.py       # Adapter
│   │   └── gatekeeper_integrator.py    # Integrador
│   │
│   ├── execution/                      # EJECUCIÓN
│   │   ├── __init__.py
│   │   ├── mt5_connector.py            # Conector MT5
│   │   ├── apr_executor.py             # Executor APR
│   │   └── circuit_breakers.py         # Circuit breakers
│   │
│   ├── risk/                           # GESTIÓN DE RIESGO
│   │   ├── __init__.py
│   │   ├── risk_management.py          # Risk management
│   │   └── factor_limits.py            # Factor limits
│   │
│   ├── governance/                     # AUDITORÍA Y VERSIONADO
│   │   ├── __init__.py
│   │   ├── event_store.py              # Event store inmutable
│   │   ├── audit_viewer.py             # Visor de auditoría
│   │   ├── data_lineage.py             # Lineage de datos
│   │   ├── id_generation.py            # Generación de IDs
│   │   ├── model_registry.py           # Registro de modelos
│   │   └── version_manager.py          # Versionado
│   │
│   ├── backtesting/                    # BACKTESTING
│   │   ├── __init__.py
│   │   ├── backtest_engine.py          # Motor de backtesting
│   │   └── performance_analyzer.py     # Análisis de performance
│   │
│   ├── reporting/                      # REPORTES
│   │   ├── __init__.py
│   │   └── institutional_reports.py    # Reportes institucionales
│   │
│   ├── signal_generator/               # GENERADOR DE SEÑALES
│   │   └── __init__.py
│   │
│   └── utils/                          # UTILIDADES
│       ├── __init__.py
│       ├── structured_logging.py       # Logging estructurado
│       ├── download_historical_data.py
│       └── test_data_availability.py
│
├── config/                             # CONFIGURACIÓN
│   ├── system_config.yaml              # Config principal del sistema
│   ├── strategies_institutional.yaml   # Config de estrategias
│   ├── strategy_config_master.yaml     # Config master
│   ├── .env.template                   # Template de variables de entorno
│   └── production/
│       └── config.yaml                 # Config de producción
│
├── scripts/                            # SCRIPTS OPERACIONALES
│   ├── live_trading_engine_institutional.py  # Motor de trading live
│   ├── pre_flight_check.py                   # Checks pre-vuelo
│   ├── adaptive_backtest.py
│   ├── consolidated_backtest.py
│   ├── etl_incremental.py
│   ├── extract_all_features.py
│   ├── institutional_backtest.py
│   ├── master_installer.py
│   ├── migrate_to_vps.py
│   ├── real_backtest.py
│   ├── surgical_analysis.py
│   ├── validate_quick.py
│   ├── verify_data.py
│   ├── verify_features.py
│   └── (otros 12 scripts operacionales)
│
├── deployment/                         # DEPLOYMENT
│   ├── vps/
│   │   ├── INTEGRATE_VPS.sh            # Script integración Linux
│   │   ├── INTEGRATE_VPS.ps1           # Script integración Windows
│   │   ├── deploy_to_vps.sh
│   │   ├── start_trading.sh
│   │   ├── start_trading.ps1
│   │   ├── monitor.sh
│   │   └── monitor.ps1
│   ├── docker/
│   │   ├── Dockerfile
│   │   ├── docker-compose.yml
│   │   └── .dockerignore
│   └── kubernetes/
│       ├── deployment.yaml
│       └── service.yaml
│
├── tests/                              # TESTS
│   ├── __init__.py
│   ├── unit/                           # Tests unitarios
│   │   ├── test_core/
│   │   ├── test_strategies/
│   │   ├── test_features/
│   │   └── test_gatekeepers/
│   ├── integration/                    # Tests de integración
│   │   ├── test_integration_full.py
│   │   └── test_execution_pipeline.py
│   ├── validation/                     # Tests de validación
│   │   ├── validate_strategies.py
│   │   ├── validate_circuit_breakers.py
│   │   ├── validate_correlation.py
│   │   ├── validate_equity_tracker.py
│   │   └── verify_data_quality.py
│   └── golden/                         # Golden cases
│       ├── __init__.py
│       └── test_golden_cases.py
│
├── docs/                               # DOCUMENTACIÓN
│   ├── README.md                       # Índice de documentación
│   │
│   ├── arquitectura/                   # ARQUITECTURA DEL SISTEMA
│   │   ├── 00_RESUMEN_EJECUTIVO.md
│   │   ├── 01_ARQUITECTURA_SISTEMA.md
│   │   ├── ARCHITECTURE_CATALOG.md
│   │   ├── DEPENDENCY_MATRIX.md
│   │   └── CATALOG_SUMMARY.md
│   │
│   ├── estrategias/                    # DOCUMENTACIÓN DE ESTRATEGIAS
│   │   ├── README.md                   # Índice de estrategias
│   │   ├── _template.md                # Template para nuevas estrategias
│   │   │
│   │   ├── order_flow/                 # Docs Order Flow
│   │   │   ├── ofi_refinement.md
│   │   │   ├── spoofing_detection_l2.md
│   │   │   ├── vpin_reversal_extreme.md
│   │   │   ├── order_flow_toxicity.md
│   │   │   ├── order_block_institutional.md
│   │   │   ├── footprint_orderflow_clusters.md
│   │   │   ├── iceberg_detection.md
│   │   │   └── liquidity_sweep.md
│   │   │
│   │   ├── statistical/                # Docs Statistical
│   │   │   ├── kalman_pairs_trading.md
│   │   │   └── mean_reversion_statistical.md
│   │   │
│   │   ├── patterns/                   # Docs Patterns
│   │   │   ├── fvg_institutional.md
│   │   │   ├── htf_ltf_liquidity.md
│   │   │   ├── breakout_volume_confirmation.md
│   │   │   └── swing_structure_breaks.md
│   │   │
│   │   ├── regime/                     # Docs Regime
│   │   │   ├── volatility_regime_adaptation.md
│   │   │   ├── crisis_mode_volatility_spike.md
│   │   │   ├── momentum_confluence.md
│   │   │   └── point_cloud_regime.md
│   │   │
│   │   └── event_driven/               # Docs Event-Driven
│   │       ├── nfp_news_event_handler.md
│   │       ├── calendar_arbitrage_flows.md
│   │       └── correlation_cascade_detection.md
│   │
│   ├── features/                       # CATÁLOGO DE FEATURES
│   │   └── CATALOGO_FEATURES.md
│   │
│   ├── deployment/                     # GUÍAS DE DEPLOYMENT
│   │   ├── DEPLOYMENT.md
│   │   ├── DEPLOYMENT_GUIDE.md
│   │   └── BACKTESTING_GUIDE.md
│   │
│   ├── api/                            # API REFERENCE
│   │   ├── core_api.md
│   │   ├── strategies_api.md
│   │   └── features_api.md
│   │
│   └── auditorias/                     # AUDITORÍAS
│       ├── AUDIT_INDEX.md
│       ├── AUDIT_CORE_20251113.md
│       ├── AUDIT_ESTRATEGIAS_20251113.md
│       ├── AUDIT_FEATURES_DETAILED.md
│       ├── AUDITORIA_ESTRATEGIAS_CONSOLIDADA.md
│       └── INFORME_EJECUTIVO_MANDATO_1.md
│
├── examples/                           # EJEMPLOS
│   ├── backtest_example.py
│   └── motor_with_pml.py
│
├── data/                               # DATOS (NO EN GIT)
│   ├── historical/
│   ├── features/
│   └── checkpoints/
│
├── logs/                               # LOGS (NO EN GIT)
│   └── .gitkeep
│
├── output/                             # OUTPUTS (NO EN GIT)
│   ├── reports/
│   ├── signals/
│   └── trades/
│
├── .gitignore                          # Git ignore
├── .gitattributes                      # Git attributes
├── setup.py                            # Setup de instalación
├── pyproject.toml                      # Config proyecto Python
├── requirements.txt                    # Dependencias principales
├── requirements.lock                   # Dependencias locked
├── test_requirements.txt               # Dependencias de test
├── constraints                         # Constraints de versiones
├── pytest.ini                          # Config pytest
└── SBOM.json                           # Software Bill of Materials
```

---

## BASURA HISTÓRICA A ELIMINAR

### Directorio Raíz (eliminar)

```
❌ ELIMINAR:
/analyze_params.py                      # Script temporal
/calculate_cointegration.py             # Script one-off
/check_path.py                          # Debug script
/debug_backtest.py                      # Debug script
/download_historical_data.py            # Duplicado (mover a src/utils/)
/final_fix_breakout.py                  # Fix one-off
/fix1_timestamp.py                      # Fix one-off
/fix2_overflows.py                      # Fix one-off
/fix_calculate_features.py              # Fix one-off
/fix_definitive.py                      # Fix one-off
/fix_iceberg_final.py                   # Fix one-off
/fix_iceberg_logging.py                 # Fix one-off
/fix_strategy_params.py                 # Fix one-off
/fix_symbol_attrs.py                    # Fix one-off
/fix_syntax_error.py                    # Fix one-off
/full_strategy_analysis.py              # Script temporal
/generate_checkpoint.py                 # Script one-off
/generate_checkpoints.py                # Script one-off
/generate_dossier.py                    # Script one-off
/generate_env.py                        # Script one-off
/generate_hashes.py                     # Script one-off
/generate_synthetic_data.py             # Script one-off
/generate_transfer_package.py           # Script one-off
/temp_verify_mt5.py                     # Debug script
/temp_verify_pg.py                      # Debug script
/test_adapter.py                        # Mover a tests/
/test_adapter_simple.py                 # Mover a tests/
/test_backtest_engine.py                # Mover a tests/
/test_backtest_improved.py              # Mover a tests/
/test_data_validation.py                # Mover a tests/
/test_execution_imports.py              # Mover a tests/
/test_execution_pipeline.py             # Mover a tests/
/test_gatekeepers.py                    # Mover a tests/
/test_governance.py                     # Mover a tests/
/test_imports.py                        # Mover a tests/
/test_integration_full.py               # Mover a tests/
/test_ml_components.py                  # Mover a tests/
/test_research_imports.py               # Mover a tests/
/validate_strategies.py                 # Mover a tests/validation/
/verify_all_strategies.py               # Mover a tests/validation/
/verify_data_quality.py                 # Mover a tests/validation/
/verify_integrity.py                    # Mover a tests/validation/

❌ OUTPUTS TEMPORALES:
/adapter_test_result.txt
/calculate_features_code.txt
/load_strategies_code.txt
/motor_errors.txt
/motor_loop_analysis.txt
/motor_main_section.txt
/motor_output.txt
/signals_real_structure.txt
/startup_diagnostic.txt
/strategy_params_report.txt
/trades_real_structure.txt
/validation_log.txt
/validation_report.html
/validation_results.json

❌ BACKUPS REDUNDANTES:
/backups/                               # Mantener solo checkpoint final
/checkpoint/                            # Consolidar en data/checkpoints/
/checkpoint_CANONICO_20251105/          # Consolidar
/checkpoints/                           # Consolidar
```

### Documentación en Raíz (consolidar en docs/)

```
✅ CONSOLIDAR EN docs/:
/AGENT_IMPLEMENTATION_INSTRUCTIONS_ELITE.md
/ANALISIS_INSTITUCIONAL_COMPLETO.md
/BACKTESTING_GUIDE.md                   → docs/deployment/
/DEPLOYMENT.md                          → docs/deployment/
/DEPLOYMENT_GUIDE.md                    → docs/deployment/
/IMPLEMENTATION_COMPLETE.md
/IMPLEMENTATION_COMPLETE_FINAL.md
/INSTITUTIONAL_AUDIT_REPORT.md
/INSTITUTIONAL_UPGRADE_COMPLETE.md
/LEVEL2_INTEGRATION_REPORT.md
/ML_ADAPTIVE_SYSTEM.md
/PLAN_IMPLEMENTACION_AGENTE.md
/REPORTES_Y_DOCUMENTOS.md
/RETAIL_CONCEPTS_ANALYSIS_ELITE_UPGRADE.md
/SIGNAL_QUALITY_SCORING_DESIGN.md
/SYMBOL_EXPANSION_ANALYSIS.md
/SYSTEM_COMPLETE_FINAL.md
/SYSTEM_COMPLETE_V2.md
/TRADE_REDUCTION_ANALYSIS.md

✅ AUDITORÍAS (ya en docs/auditorias/):
/AUDIT_*.md                             → docs/auditorias/
/auditorias/                            → docs/auditorias/
```

### Directorios Obsoletos

```
❌ ELIMINAR O CONSOLIDAR:
/dossier/                               → docs/arquitectura/
/migration_pack_20251105/               → docs/migration/ (histórico)
/transfer/                              → docs/migration/ (histórico)
/archive/                               # Eliminar si vacío
/_quarantine/                           # Revisar contenido, probablemente eliminar
/governance_test/                       # Mover a tests/integration/
/test_integration/                      # Consolidar en tests/integration/
/validation/                            # Consolidar en tests/validation/
```

---

## REORGANIZACIÓN DE ESTRATEGIAS

### Crear Subdirectorios por Categoría

```bash
# Crear estructura
mkdir -p src/strategies/{order_flow,statistical,patterns,regime,event_driven,deprecated}

# Mover estrategias a categorías
# (comandos detallados en siguiente sección)
```

### Renombrar Estrategias con Naming Dishonesto

```bash
# 1. fractal_market_structure.py → swing_structure_breaks.py
git mv src/strategies/fractal_market_structure.py \
       src/strategies/patterns/swing_structure_breaks.py

# 2. momentum_quality.py → momentum_confluence.py
git mv src/strategies/momentum_quality.py \
       src/strategies/regime/momentum_confluence.py

# 3. topological_data_analysis_regime.py → point_cloud_regime.py
git mv src/strategies/topological_data_analysis_regime.py \
       src/strategies/regime/point_cloud_regime.py
```

### Deprecar Estrategias Broken

```bash
# Mover a deprecated/
git mv src/strategies/statistical_arbitrage_johansen.py \
       src/strategies/deprecated/

git mv src/strategies/correlation_divergence.py \
       src/strategies/deprecated/

git mv src/strategies/idp_inducement_distribution.py \
       src/strategies/deprecated/
```

---

## ESTRUCTURA DE DOCUMENTACIÓN docs/estrategias/

### Template para Cada Estrategia

```markdown
# [NOMBRE ESTRATEGIA]

## Descripción

[Explicación clara en lenguaje sencillo]

## Objetivo y Contexto

**Objetivo**: [Para qué se usa]
**Contexto óptimo**: [Condiciones ideales]
**Frecuencia**: [Cuántos trades/día esperados]

## Lógica Conceptual

### Paso 1: [Nombre]
[Explicación]

### Paso 2: [Nombre]
[Explicación]

... [N pasos]

## Criterios Institucionales

- ✅ [Criterio 1]: [Cómo se cumple]
- ✅ [Criterio 2]: [Cómo se cumple]
...

## Supuestos y Limitaciones

**Supuestos**:
- [Supuesto 1]
- [Supuesto 2]

**Limitaciones**:
- [Limitación 1]
- [Limitación 2]

## Performance Esperada

- **Win Rate**: [X-Y%]
- **Risk/Reward**: [R:R ratio]
- **Max Drawdown**: [%]
- **Sharpe Ratio**: [valor]

## Degraded Mode (si aplica)

⚠️ **Esta estrategia opera en degraded mode** sin Level 2 data:
- [Qué datos faltan]
- [Qué proxies usa]
- [Impacto en win rate]

## Historial de Cambios

### 2025-11-13 - Auditoría Mandato 2
- [Cambios realizados]

### [Fecha anterior]
- [Cambios]

## Referencias

- [Paper 1]
- [Paper 2]
...
```

---

## PRIORIDAD DE IMPLEMENTACIÓN

### Fase 1: LIMPIEZA (HOY) - 2-3 horas

1. ✅ Crear directorios de estructura definitiva
2. ✅ Mover estrategias a categorías
3. ✅ Renombrar 3 estrategias
4. ✅ Mover 3 a deprecated/
5. ✅ Eliminar scripts one-off y debug
6. ✅ Consolidar documentación en docs/
7. ✅ Commit: "chore: Estructura definitiva institucional + cleanup"

### Fase 2: DOCUMENTACIÓN (MAÑANA) - 8-10 horas

1. ✅ Crear docs/estrategias/ con 24 archivos .md
2. ✅ Usar template consistente
3. ✅ Commit por categoría de estrategias

### Fase 3: TESTS (PRÓXIMA SEMANA) - 12-16 horas

1. ⏳ Reorganizar tests/ según estructura nueva
2. ⏳ Crear tests faltantes para estrategias aprobadas
3. ⏳ CI/CD básico

---

## CRITERIOS DE ACEPTACIÓN

### Para Considerar Estructura Completa

- ✅ 24 estrategias organizadas en 6 categorías
- ✅ 3 estrategias renombradas honestamente
- ✅ 3 estrategias deprecated documentadas
- ✅ Basura histórica eliminada
- ✅ Documentación en docs/ consolidada
- ✅ 24 archivos en docs/estrategias/ con template consistente
- ✅ README principal actualizado con nueva estructura
- ✅ CHANGELOG con cambios de Mandato 2

### Para Considerar Sistema Production-Ready

- ⏳ Tests reorganizados y completos
- ⏳ CI/CD funcional
- ⏳ 3 estrategias broken reescritas o eliminadas
- ⏳ 8 estrategias HYBRID mejoradas
- ⏳ Documentación API completa

---

**Arquitecto Principal - ALGORITMO_INSTITUCIONAL_SUBLIMINE**
**Fecha**: 2025-11-13
**Status**: ESTRUCTURA DEFINITIVA DISEÑADA - Lista para implementar
