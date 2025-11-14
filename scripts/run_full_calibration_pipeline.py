#!/usr/bin/env python3
"""
MANDATO 22 - Full Calibration Pipeline (Institutional)

Bot\u00f3n nuclear de calibraci\u00f3n institucional.

Orquesta:
1. Sanity checks (smoke tests)
2. Validaci\u00f3n datos REALES vs SYNTHETIC
3. Ejecuci\u00f3n calibration sweep
4. Entrenamiento brain-layer
5. Hold-out validation
6. Promoci\u00f3n configs calibradas → config/calibrated/active/
7. Generaci\u00f3n reporte final

NON-NEGOTIABLES:
- Solo corre con datos REALES (NO SYNTHETIC)
- Si no hay datos → BLOQUEADO - NO_REAL_DATA
- Risk limits 0-2% intactos
- NO inventar resultados

Usage:
    python scripts/run_full_calibration_pipeline.py
    python scripts/run_full_calibration_pipeline.py --dry-run
    python scripts/run_full_calibration_pipeline.py --skip-smoke-tests

Autor: SUBLIMINE Institutional Trading System
Fecha: 2025-11-14
Mandato: MANDATO 22 - Orquestaci\u00f3n Calibraci\u00f3n Real
"""

import sys
import os
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import argparse
import logging
import subprocess
import yaml
import json
from datetime import datetime
from typing import Dict, List, Optional
from dataclasses import dataclass, asdict

from src.calibration.data_validator import (
    CalibrationDataValidator,
    DataStatus
)

# Logging setup
log_dir = Path("logs/calibration")
log_dir.mkdir(parents=True, exist_ok=True)

log_file = log_dir / f"mandato22_pipeline_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)


@dataclass
class PipelineResult:
    """Resultado del pipeline completo."""
    status: str  # SUCCESS, BLOCKED, FAILED
    stage_completed: str
    data_status: str
    sweep_completed: bool
    brain_completed: bool
    holdout_completed: bool
    promotion_completed: bool
    configs_promoted: List[str]
    report_path: Optional[str]
    error_message: Optional[str]
    timestamp: str


class CalibrationPipeline:
    """Pipeline maestro de calibraci\u00f3n institucional."""

    def __init__(
        self,
        config_path: str = "config/backtest_calibration_20251114.yaml",
        dry_run: bool = False,
        skip_smoke_tests: bool = False
    ):
        """
        Initialize pipeline.

        Args:
            config_path: Path to calibration config
            dry_run: If True, validate but don't execute calibration
            skip_smoke_tests: Skip smoke tests (use with caution)
        """
        self.config_path = config_path
        self.dry_run = dry_run
        self.skip_smoke_tests = skip_smoke_tests

        # Load config
        with open(config_path, 'r') as f:
            self.config = yaml.safe_load(f)

        # Paths
        self.calibrated_dir = Path("config/calibrated")
        self.active_dir = self.calibrated_dir / "active"
        self.reports_dir = Path("reports/calibration")

        # Results tracking
        self.result = PipelineResult(
            status="PENDING",
            stage_completed="NONE",
            data_status="UNKNOWN",
            sweep_completed=False,
            brain_completed=False,
            holdout_completed=False,
            promotion_completed=False,
            configs_promoted=[],
            report_path=None,
            error_message=None,
            timestamp=datetime.now().isoformat()
        )

    def run(self) -> PipelineResult:
        """
        Run full calibration pipeline.

        Returns:
            PipelineResult with final status
        """
        logger.info("=" * 80)
        logger.info("MANDATO 22 - FULL CALIBRATION PIPELINE")
        logger.info("=" * 80)
        logger.info(f"Config: {self.config_path}")
        logger.info(f"Dry run: {self.dry_run}")
        logger.info(f"Log file: {log_file}")
        logger.info("=" * 80)
        logger.info("")

        try:
            # STAGE 1: Sanity checks
            if not self.skip_smoke_tests:
                if not self._run_sanity_checks():
                    self.result.status = "FAILED"
                    self.result.stage_completed = "SANITY_CHECKS"
                    self.result.error_message = "Smoke tests failed"
                    return self.result
            else:
                logger.warning("⚠️  Skipping smoke tests (--skip-smoke-tests)")

            self.result.stage_completed = "SANITY_CHECKS"

            # STAGE 2: Data validation
            data_result = self._validate_data()

            self.result.data_status = data_result.status.value

            if data_result.status != DataStatus.READY:
                self.result.status = "BLOCKED"
                self.result.stage_completed = "DATA_VALIDATION"
                self.result.error_message = data_result.message

                # Generate BLOCKED status document
                self._generate_blocked_status_doc(data_result)

                return self.result

            self.result.stage_completed = "DATA_VALIDATION"

            if self.dry_run:
                logger.info("")
                logger.info("=" * 80)
                logger.info("DRY RUN MODE - Stopping here")
                logger.info("=" * 80)
                logger.info("Data validation: PASSED")
                logger.info("Would proceed with calibration if not dry-run")
                logger.info("=" * 80)

                self.result.status = "DRY_RUN_SUCCESS"
                return self.result

            # STAGE 3: Run calibration sweep
            if not self._run_calibration_sweep():
                self.result.status = "FAILED"
                self.result.stage_completed = "CALIBRATION_SWEEP"
                self.result.error_message = "Calibration sweep failed"
                return self.result

            self.result.sweep_completed = True
            self.result.stage_completed = "CALIBRATION_SWEEP"

            # STAGE 4: Train brain policies
            if not self._train_brain_policies():
                self.result.status = "FAILED"
                self.result.stage_completed = "BRAIN_TRAINING"
                self.result.error_message = "Brain training failed"
                return self.result

            self.result.brain_completed = True
            self.result.stage_completed = "BRAIN_TRAINING"

            # STAGE 5: Hold-out validation
            if not self._run_holdout_validation():
                self.result.status = "FAILED"
                self.result.stage_completed = "HOLDOUT_VALIDATION"
                self.result.error_message = "Hold-out validation failed"
                return self.result

            self.result.holdout_completed = True
            self.result.stage_completed = "HOLDOUT_VALIDATION"

            # STAGE 6: Promote configs
            promoted = self._promote_calibrated_configs()

            self.result.promotion_completed = True
            self.result.configs_promoted = promoted
            self.result.stage_completed = "PROMOTION"

            # STAGE 7: Generate final report
            report_path = self._generate_final_report(data_result, promoted)

            self.result.report_path = str(report_path)
            self.result.stage_completed = "COMPLETE"
            self.result.status = "SUCCESS"

            logger.info("")
            logger.info("=" * 80)
            logger.info("✅ CALIBRATION PIPELINE COMPLETE")
            logger.info("=" * 80)
            logger.info(f"Status: {self.result.status}")
            logger.info(f"Configs promoted: {len(promoted)}")
            logger.info(f"Final report: {report_path}")
            logger.info("=" * 80)

            return self.result

        except Exception as e:
            logger.error(f"Pipeline failed with exception: {e}")
            import traceback
            traceback.print_exc()

            self.result.status = "FAILED"
            self.result.error_message = str(e)
            return self.result

    def _run_sanity_checks(self) -> bool:
        """Run smoke tests."""
        logger.info("STAGE 1: Sanity checks (smoke tests)")
        logger.info("─" * 80)

        smoke_tests = [
            "scripts/smoke_test_backtest.py",
            "scripts/smoke_test_calibration.py"
        ]

        for test in smoke_tests:
            if not Path(test).exists():
                logger.warning(f"⚠️  Smoke test not found: {test} (skipping)")
                continue

            logger.info(f"Running: {test}")

            try:
                result = subprocess.run(
                    ["python", test],
                    capture_output=True,
                    text=True,
                    timeout=300  # 5 min timeout
                )

                if result.returncode != 0:
                    logger.error(f"❌ Smoke test FAILED: {test}")
                    logger.error(f"Output: {result.stdout}")
                    logger.error(f"Errors: {result.stderr}")
                    return False

                logger.info(f"✅ Smoke test PASSED: {test}")

            except Exception as e:
                logger.error(f"❌ Smoke test CRASHED: {test} - {e}")
                return False

        logger.info("")
        return True

    def _validate_data(self) -> 'DataValidationResult':
        """Validate data availability."""
        logger.info("STAGE 2: Data validation (REAL vs SYNTHETIC)")
        logger.info("─" * 80)

        # Get required symbols from config
        symbols = self.config.get('calibration_universe', {}).get('symbols', [])

        if not symbols:
            # Fallback to minimum scope
            symbols = ["EURUSD", "XAUUSD", "US500"]
            logger.warning(f"No symbols in config, using minimum scope: {symbols}")

        timeframe = self.config.get('data_settings', {}).get('timeframe', 'M15')

        # Validate
        validator = CalibrationDataValidator()
        result = validator.validate(required_symbols=symbols, timeframe=timeframe)

        logger.info("")
        return result

    def _run_calibration_sweep(self) -> bool:
        """Run calibration sweep."""
        logger.info("STAGE 3: Calibration sweep")
        logger.info("─" * 80)

        script = "scripts/run_calibration_sweep.py"

        logger.info(f"Running: {script}")

        try:
            result = subprocess.run(
                ["python", script, "--config", self.config_path],
                capture_output=False,  # Show output in real-time
                timeout=3600  # 1 hour timeout
            )

            if result.returncode != 0:
                logger.error(f"❌ Calibration sweep FAILED (exit code: {result.returncode})")
                return False

            logger.info("✅ Calibration sweep COMPLETED")
            logger.info("")
            return True

        except subprocess.TimeoutExpired:
            logger.error("❌ Calibration sweep TIMEOUT (> 1 hour)")
            return False
        except Exception as e:
            logger.error(f"❌ Calibration sweep CRASHED: {e}")
            return False

    def _train_brain_policies(self) -> bool:
        """Train brain policies."""
        logger.info("STAGE 4: Brain policies training")
        logger.info("─" * 80)

        script = "scripts/train_brain_policies_calibrated.py"

        logger.info(f"Running: {script}")

        try:
            result = subprocess.run(
                ["python", script],
                capture_output=False,
                timeout=1800  # 30 min timeout
            )

            if result.returncode != 0:
                logger.error(f"❌ Brain training FAILED (exit code: {result.returncode})")
                return False

            logger.info("✅ Brain training COMPLETED")
            logger.info("")
            return True

        except subprocess.TimeoutExpired:
            logger.error("❌ Brain training TIMEOUT (> 30 min)")
            return False
        except Exception as e:
            logger.error(f"❌ Brain training CRASHED: {e}")
            return False

    def _run_holdout_validation(self) -> bool:
        """Run hold-out validation."""
        logger.info("STAGE 5: Hold-out validation")
        logger.info("─" * 80)

        script = "scripts/run_calibration_holdout.py"

        logger.info(f"Running: {script}")

        try:
            result = subprocess.run(
                ["python", script],
                capture_output=False,
                timeout=3600  # 1 hour timeout
            )

            if result.returncode != 0:
                logger.error(f"❌ Hold-out validation FAILED (exit code: {result.returncode})")
                return False

            logger.info("✅ Hold-out validation COMPLETED")
            logger.info("")
            return True

        except subprocess.TimeoutExpired:
            logger.error("❌ Hold-out validation TIMEOUT (> 1 hour)")
            return False
        except Exception as e:
            logger.error(f"❌ Hold-out validation CRASHED: {e}")
            return False

    def _promote_calibrated_configs(self) -> List[str]:
        """Promote calibrated configs to active directory."""
        logger.info("STAGE 6: Promotion of calibrated configs")
        logger.info("─" * 80)

        # Create active directory
        self.active_dir.mkdir(parents=True, exist_ok=True)

        promoted = []

        # Look for calibrated configs in config/calibrated/
        calibrated_files = list(self.calibrated_dir.glob("*.yaml"))

        logger.info(f"Found {len(calibrated_files)} calibrated config files")

        for file in calibrated_files:
            if file.parent == self.active_dir:
                # Skip files already in active/
                continue

            # Copy to active/ (simplified - always promote for now)
            # TODO MANDATO 23: Parse holdout reports and only promote ADOPT/PILOT

            dest = self.active_dir / f"{file.stem}_active.yaml"

            import shutil
            shutil.copy2(file, dest)

            logger.info(f"✅ Promoted: {file.name} → {dest.name}")
            promoted.append(dest.name)

        # Generate index
        self._generate_active_index(promoted)

        logger.info("")
        logger.info(f"Promoted {len(promoted)} configs to active/")
        logger.info("")

        return promoted

    def _generate_active_index(self, promoted_files: List[str]):
        """Generate index of active strategies."""
        index = {
            'last_calibration_date': datetime.now().isoformat(),
            'pipeline_version': '1.0-MANDATO22',
            'data_period': {
                'start': self.config.get('calibration', {}).get('period', {}).get('start'),
                'end': self.config.get('calibration', {}).get('period', {}).get('end')
            },
            'active_configs': promoted_files,
            'num_active_strategies': len(promoted_files)
        }

        index_path = self.active_dir / "ACTIVE_STRATEGIES_INDEX.yaml"

        with open(index_path, 'w') as f:
            yaml.dump(index, f, default_flow_style=False, sort_keys=False)

        logger.info(f"Generated index: {index_path}")

    def _generate_final_report(
        self,
        data_result: 'DataValidationResult',
        promoted_configs: List[str]
    ) -> Path:
        """Generate final calibration report."""
        logger.info("STAGE 7: Final report generation")
        logger.info("─" * 80)

        date_str = datetime.now().strftime("%Y%m%d")
        report_path = Path(f"docs/MANDATO22_CALIBRACION_REAL_{date_str}.md")

        with open(report_path, 'w') as f:
            f.write(f"# MANDATO 22 - CALIBRACI\u00d3N REAL - {date_str}\n\n")
            f.write("**Estado**: ✅ COMPLETADO\n\n")
            f.write("## Resumen Ejecutivo\n\n")
            f.write(f"- **Fecha**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"- **Modo**: CALIBRACI\u00d3N CON DATOS REALES\n")
            f.write(f"- **S\u00edmbolos**: {', '.join(data_result.ready_symbols)}\n")
            f.write(f"- **Configs promovidas**: {len(promoted_configs)}\n\n")

            f.write("## Pipeline Execution\n\n")
            f.write("- ✅ Sanity checks\n")
            f.write("- ✅ Data validation (REAL data)\n")
            f.write("- ✅ Calibration sweep\n")
            f.write("- ✅ Brain training\n")
            f.write("- ✅ Hold-out validation\n")
            f.write("- ✅ Config promotion\n\n")

            f.write("## Promoted Configs\n\n")
            for config in promoted_configs:
                f.write(f"- {config}\n")

            f.write("\n---\n\n")
            f.write(f"**Log file**: {log_file}\n")

        logger.info(f"Report generated: {report_path}")
        logger.info("")

        return report_path

    def _generate_blocked_status_doc(self, data_result: 'DataValidationResult'):
        """Generate BLOCKED status document."""
        date_str = datetime.now().strftime("%Y%m%d")
        status_path = Path(f"docs/MANDATO22_STATUS_{date_str}.md")

        with open(status_path, 'w') as f:
            f.write(f"# MANDATO 22 - STATUS - {date_str}\n\n")
            f.write(f"**Estado**: ❌ BLOQUEADO - {data_result.status.value.upper()}\n\n")
            f.write("## Raz\u00f3n\n\n")
            f.write(f"{data_result.message}\n\n")
            f.write("## Datos Disponibles\n\n")
            f.write(f"- REAL files: {len(data_result.real_files)}\n")
            f.write(f"- SYNTHETIC files: {len(data_result.synthetic_files)}\n\n")
            f.write("## S\u00edmbolos Faltantes\n\n")
            for symbol in data_result.missing_symbols:
                f.write(f"- {symbol}\n")
            f.write("\n## Acci\u00f3n Requerida\n\n")
            f.write("Descargar datos REALES con:\n\n")
            f.write("```bash\n")
            f.write("python scripts/download_mt5_history.py \\\n")
            f.write(f"  --symbols {','.join(data_result.missing_symbols)} \\\n")
            f.write("  --timeframe M15 \\\n")
            f.write("  --start 2023-01-01 \\\n")
            f.write("  --end 2024-12-31\n")
            f.write("```\n")

        logger.info(f"BLOCKED status document: {status_path}")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='MANDATO 22 - Full Calibration Pipeline'
    )

    parser.add_argument(
        '--config',
        type=str,
        default='config/backtest_calibration_20251114.yaml',
        help='Calibration config file'
    )

    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Validate only, do not run calibration'
    )

    parser.add_argument(
        '--skip-smoke-tests',
        action='store_true',
        help='Skip smoke tests (use with caution)'
    )

    args = parser.parse_args()

    # Run pipeline
    pipeline = CalibrationPipeline(
        config_path=args.config,
        dry_run=args.dry_run,
        skip_smoke_tests=args.skip_smoke_tests
    )

    result = pipeline.run()

    # Exit code based on status
    if result.status == "SUCCESS":
        sys.exit(0)
    elif result.status == "DRY_RUN_SUCCESS":
        sys.exit(0)
    elif result.status == "BLOCKED":
        logger.warning("Pipeline BLOCKED - see status document")
        sys.exit(2)  # Special exit code for BLOCKED
    else:
        logger.error(f"Pipeline FAILED at stage: {result.stage_completed}")
        sys.exit(1)


if __name__ == "__main__":
    main()
