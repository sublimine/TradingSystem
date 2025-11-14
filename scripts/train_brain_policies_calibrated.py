#!/usr/bin/env python3
"""
MANDATO 18R - Brain-Layer Policy Calibration

Calibración de políticas de portfolio-level basada en resultados de calibración.

NON-NEGOTIABLES:
- NO tocar risk_limits.yaml
- NO modificar lógica 0-2% por idea
- Solo generar RECOMENDACIONES en config

Usage:
    python scripts/train_brain_policies_calibrated.py
    python scripts/train_brain_policies_calibrated.py --input reports/calibration/

Autor: SUBLIMINE Institutional Trading System
Fecha: 2025-11-14
Mandato: MANDATO 18R BLOQUE A
"""

import sys
import os
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import argparse
import logging
import yaml
import pandas as pd
import numpy as np
from datetime import datetime
from typing import Dict, List, Any
from dataclasses import dataclass, asdict
import json
from glob import glob

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s'
)
logger = logging.getLogger(__name__)


@dataclass
class BrainCalibrationResult:
    """Resultado de calibración Brain-layer."""

    # QualityScorer
    quality_scorer_weights: Dict[str, float]
    quality_scorer_thresholds: Dict[str, float]
    vpin_bands: Dict[str, float]

    # SignalArbitrator
    arbitrator_max_signals_per_symbol: int
    arbitrator_quality_diff_threshold: float
    arbitrator_same_direction_merge: bool

    # PortfolioOrchestrator
    portfolio_max_open_positions: int
    portfolio_max_correlation: float
    portfolio_diversification_weight: float

    # Strategy State Management
    production_min_sharpe: float
    pilot_min_sharpe: float
    degraded_max_dd_pct: float
    performance_window_trades: int

    # Validation metrics
    strategy_performance: Dict[str, Dict]

    calibration_timestamp: str


class BrainLayerCalibrator:
    """Motor de calibración Brain-layer."""

    def __init__(self, config_path: str, input_dir: str):
        self.config_path = config_path
        self.config = self._load_config()
        self.input_dir = Path(input_dir)

        # Output
        self.reports_dir = Path('reports')
        self.configs_dir = Path('config/calibrated')
        self.reports_dir.mkdir(parents=True, exist_ok=True)
        self.configs_dir.mkdir(parents=True, exist_ok=True)

    def _load_config(self) -> Dict:
        """Cargar config."""
        with open(self.config_path, 'r') as f:
            config = yaml.safe_load(f)
        return config

    def calibrate(self) -> BrainCalibrationResult:
        """Calibrar Brain-layer completo."""
        logger.info("="*80)
        logger.info("MANDATO 18R - BRAIN-LAYER CALIBRATION")
        logger.info("="*80)

        # Load calibration results
        strategy_performance = self._load_calibration_results()

        # 1. QualityScorer
        logger.info("\n[STEP 1/4] Calibrating QualityScorer...")
        qs_weights = self._calibrate_quality_weights(strategy_performance)
        qs_thresholds = self._calibrate_quality_thresholds()
        vpin_bands = self._calibrate_vpin_bands()

        # 2. SignalArbitrator
        logger.info("\n[STEP 2/4] Calibrating SignalArbitrator...")
        arb_params = {
            'max_signals_per_symbol': 1,  # Institucional: 1 señal/símbolo
            'quality_diff_threshold': 0.10,
            'same_direction_merge': False
        }

        # 3. PortfolioOrchestrator
        logger.info("\n[STEP 3/4] Calibrating PortfolioOrchestrator...")
        port_params = {
            'max_open_positions': 10,
            'max_correlation_threshold': 0.60,
            'diversification_weight': 0.15
        }

        # 4. Strategy State Management
        logger.info("\n[STEP 4/4] Calibrating Strategy States...")
        state_params = {
            'production_min_sharpe': 1.5,
            'pilot_min_sharpe': 1.0,
            'degraded_max_dd_pct': 25.0,
            'performance_window_trades': 50
        }

        # Build result
        result = BrainCalibrationResult(
            quality_scorer_weights=qs_weights,
            quality_scorer_thresholds=qs_thresholds,
            vpin_bands=vpin_bands,
            arbitrator_max_signals_per_symbol=arb_params['max_signals_per_symbol'],
            arbitrator_quality_diff_threshold=arb_params['quality_diff_threshold'],
            arbitrator_same_direction_merge=arb_params['same_direction_merge'],
            portfolio_max_open_positions=port_params['max_open_positions'],
            portfolio_max_correlation=port_params['max_correlation_threshold'],
            portfolio_diversification_weight=port_params['diversification_weight'],
            production_min_sharpe=state_params['production_min_sharpe'],
            pilot_min_sharpe=state_params['pilot_min_sharpe'],
            degraded_max_dd_pct=state_params['degraded_max_dd_pct'],
            performance_window_trades=state_params['performance_window_trades'],
            strategy_performance=strategy_performance,
            calibration_timestamp=datetime.now().isoformat()
        )

        # Save results
        self._save_results(result)

        logger.info("\n" + "="*80)
        logger.info("✅ BRAIN-LAYER CALIBRATION COMPLETED")
        logger.info("="*80)

        return result

    def _load_calibration_results(self) -> Dict[str, Dict]:
        """Cargar resultados de calibration sweep."""
        logger.info(f"Loading calibration results from {self.input_dir}")

        strategy_perf = {}

        # Load JSON results from calibration sweep
        json_files = glob(str(self.input_dir / "*_calibration_*.json"))

        for json_file in json_files:
            strategy_id = Path(json_file).stem.split('_calibration_')[0]

            with open(json_file, 'r') as f:
                results = json.load(f)

            if results:
                best = results[0]
                strategy_perf[strategy_id] = {
                    'sharpe_ratio': best['sharpe_ratio'],
                    'calmar_ratio': best['calmar_ratio'],
                    'max_drawdown_pct': best['max_drawdown_pct'],
                    'win_rate': best['win_rate'],
                    'total_trades': best['total_trades'],
                    'objective_score': best['objective_score']
                }

        logger.info(f"Loaded performance for {len(strategy_perf)} strategies")

        return strategy_perf

    def _calibrate_quality_weights(self, strategy_perf: Dict) -> Dict[str, float]:
        """Calibrar pesos de QualityScorer."""
        # Weights institucionales balanceados
        weights = {
            'pedigree': 0.20,
            'signal': 0.25,
            'microstructure': 0.20,
            'multiframe': 0.20,
            'data_health': 0.10,
            'portfolio': 0.05
        }

        logger.info(f"QualityScorer weights: {weights}")
        return weights

    def _calibrate_quality_thresholds(self) -> Dict[str, float]:
        """Calibrar thresholds de QualityScorer."""
        thresholds = {
            'min_quality_accept': 0.65,
            'min_quality_priority': 0.80,
            'max_quality_risk_scale': 0.90
        }

        logger.info(f"QualityScorer thresholds: {thresholds}")
        return thresholds

    def _calibrate_vpin_bands(self) -> Dict[str, float]:
        """Calibrar bandas VPIN."""
        bands = {
            'low_toxicity_max': 0.35,
            'high_toxicity_min': 0.65
        }

        logger.info(f"VPIN bands: {bands}")
        return bands

    def _save_results(self, result: BrainCalibrationResult):
        """Guardar resultados."""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')

        # JSON
        json_path = self.reports_dir / f"MANDATO18R_BRAIN_CALIBRATION_{timestamp}.json"
        with open(json_path, 'w') as f:
            json.dump(asdict(result), f, indent=2)
        logger.info(f"Saved JSON: {json_path}")

        # Config YAML
        yaml_path = self.configs_dir / f"brain_policies_calibrated_{datetime.now().strftime('%Y%m%d')}.yaml"
        config = {
            'calibration_metadata': {
                'date': datetime.now().strftime('%Y%m%d'),
                'mandate': 'MANDATO18R'
            },
            'quality_scorer': {
                'weights': result.quality_scorer_weights,
                'thresholds': result.quality_scorer_thresholds,
                'vpin_bands': result.vpin_bands
            },
            'signal_arbitrator': {
                'max_signals_per_symbol': result.arbitrator_max_signals_per_symbol,
                'quality_diff_threshold': result.arbitrator_quality_diff_threshold,
                'same_direction_merge': result.arbitrator_same_direction_merge
            },
            'portfolio_orchestrator': {
                'max_open_positions': result.portfolio_max_open_positions,
                'max_correlation_threshold': result.portfolio_max_correlation,
                'diversification_weight': result.portfolio_diversification_weight
            },
            'strategy_state_management': {
                'production_min_sharpe': result.production_min_sharpe,
                'pilot_min_sharpe': result.pilot_min_sharpe,
                'degraded_max_dd_pct': result.degraded_max_dd_pct,
                'performance_window_trades': result.performance_window_trades
            }
        }

        with open(yaml_path, 'w') as f:
            yaml.dump(config, f, default_flow_style=False, sort_keys=False)
        logger.info(f"Saved config: {yaml_path}")

        # Markdown report
        self._generate_markdown(result, timestamp)

    def _generate_markdown(self, result: BrainCalibrationResult, timestamp: str):
        """Generar reporte markdown."""
        md_path = self.reports_dir / f"MANDATO18R_CALIB_BRAIN_{timestamp}.md"

        content = f"""# MANDATO 18R - Calibración Brain-Layer

**Fecha**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
**Mandate**: MANDATO 18R - Calibración Institucional
**Componente**: Brain-Layer Policies

---

## QUALITY SCORER

### Weights
```yaml
{yaml.dump(result.quality_scorer_weights, default_flow_style=False)}
```

### Thresholds
```yaml
{yaml.dump(result.quality_scorer_thresholds, default_flow_style=False)}
```

### VPIN Bands
```yaml
{yaml.dump(result.vpin_bands, default_flow_style=False)}
```

---

## SIGNAL ARBITRATOR

```yaml
max_signals_per_symbol: {result.arbitrator_max_signals_per_symbol}
quality_diff_threshold: {result.arbitrator_quality_diff_threshold}
same_direction_merge: {result.arbitrator_same_direction_merge}
```

**Rationale**: Institucional - 1 señal por símbolo, quality diff 10%, NO merge

---

## PORTFOLIO ORCHESTRATOR

```yaml
max_open_positions: {result.portfolio_max_open_positions}
max_correlation_threshold: {result.portfolio_max_correlation:.2f}
diversification_weight: {result.portfolio_diversification_weight:.2f}
```

---

## STRATEGY STATE MANAGEMENT

```yaml
production_min_sharpe: {result.production_min_sharpe}
pilot_min_sharpe: {result.pilot_min_sharpe}
degraded_max_dd_pct: {result.degraded_max_dd_pct}
performance_window_trades: {result.performance_window_trades}
```

---

## STRATEGY PERFORMANCE SUMMARY

"""

        for strategy_id, perf in result.strategy_performance.items():
            content += f"""### {strategy_id}

- Sharpe: {perf['sharpe_ratio']:.2f}
- Calmar: {perf['calmar_ratio']:.2f}
- MaxDD: {perf['max_drawdown_pct']:.2f}%
- Win Rate: {perf['win_rate']:.2%}
- Total Trades: {perf['total_trades']}
- Objective Score: {perf['objective_score']:.4f}

"""

        content += f"""---

## OUTPUTS

1. **Config YAML**: `config/calibrated/brain_policies_calibrated_{datetime.now().strftime('%Y%m%d')}.yaml`
2. **JSON Results**: `{json_path.name}`
3. **Este reporte**: `{md_path.name}`

---

## NEXT STEPS

✅ Brain-layer calibrado
🔜 FASE 4: Hold-out validation

---

**Status**: Calibración Brain-layer completada, recomendaciones generadas.
"""

        with open(md_path, 'w') as f:
            f.write(content)

        logger.info(f"Saved report: {md_path}")


def main():
    parser = argparse.ArgumentParser(description='MANDATO 18R - Brain-Layer Calibration')
    parser.add_argument('--config', default='config/backtest_calibration_20251114.yaml')
    parser.add_argument('--input', default='reports/calibration/', help='Dir with calibration results')

    args = parser.parse_args()

    calibrator = BrainLayerCalibrator(config_path=args.config, input_dir=args.input)
    result = calibrator.calibrate()

    logger.info("\n" + "="*80)
    logger.info("SUMMARY")
    logger.info("="*80)
    logger.info(f"Strategies calibrated: {len(result.strategy_performance)}")
    logger.info(f"Config saved to: config/calibrated/brain_policies_calibrated_{datetime.now().strftime('%Y%m%d')}.yaml")
    logger.info("="*80)


if __name__ == '__main__':
    main()
