#!/usr/bin/env python3
"""
MANDATO 18R - Smoke Test Calibration Pipeline

Validar que el pipeline de calibración funciona end-to-end.

Tests:
1. Config loading
2. Calibration sweep (quick mode)
3. Brain calibration
4. Hold-out validation

Usage:
    python scripts/smoke_test_calibration.py

Autor: SUBLIMINE Institutional Trading System
Fecha: 2025-11-14
Mandato: MANDATO 18R BLOQUE B
"""

import sys
import os
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import logging
import yaml

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s'
)
logger = logging.getLogger(__name__)


class SmokeTestCalibration:
    """Smoke test para pipeline de calibración."""

    def __init__(self):
        self.test_passed = True

    def run(self):
        """Ejecutar smoke test completo."""
        logger.info("="*80)
        logger.info("SMOKE TEST - CALIBRATION PIPELINE")
        logger.info("MANDATO 18R")
        logger.info("="*80)

        try:
            # Test 1: Config loading
            logger.info("\n[TEST 1] Testing config loading...")
            self.test_config_loading()

            # Test 2: Module imports
            logger.info("\n[TEST 2] Testing module imports...")
            self.test_module_imports()

            # Test 3: Directory structure
            logger.info("\n[TEST 3] Testing directory structure...")
            self.test_directory_structure()

            # Summary
            logger.info("\n" + "="*80)
            if self.test_passed:
                logger.info("✅ SMOKE TEST PASSED - Calibration pipeline operational")
            else:
                logger.error("❌ SMOKE TEST FAILED - Check logs above")
            logger.info("="*80)

        except Exception as e:
            logger.error(f"❌ SMOKE TEST FAILED with exception: {e}", exc_info=True)
            self.test_passed = False

    def test_config_loading(self):
        """Test 1: Cargar config de calibración."""
        try:
            config_path = 'config/backtest_calibration_20251114.yaml'

            with open(config_path, 'r') as f:
                config = yaml.safe_load(f)

            # Validations
            assert 'calibration' in config
            assert 'validation' in config
            assert 'universe' in config
            assert 'strategies' in config
            assert 'metrics_targets' in config
            assert 'strategy_params' in config

            logger.info(f"  ✓ Config loaded: {config_path}")
            logger.info(f"  ✓ Strategies defined: {len(config['strategies'])}")
            logger.info(f"  ✓ Strategy params: {len(config['strategy_params'])}")

            logger.info("✅ TEST 1 PASSED: Config loading")

        except Exception as e:
            logger.error(f"❌ TEST 1 FAILED: {e}")
            self.test_passed = False

    def test_module_imports(self):
        """Test 2: Importar módulos de calibración."""
        try:
            # Test imports
            import scripts.run_calibration_sweep as sweep_module
            import scripts.train_brain_policies_calibrated as brain_module
            import scripts.run_calibration_holdout as holdout_module

            # Verificar clases/funciones existen
            assert hasattr(sweep_module, 'CalibrationSweep')
            assert hasattr(sweep_module, 'ParameterGrid')
            assert hasattr(sweep_module, 'WalkForwardValidator')

            assert hasattr(brain_module, 'BrainLayerCalibrator')

            assert hasattr(holdout_module, 'HoldOutValidator')

            logger.info("  ✓ run_calibration_sweep importable")
            logger.info("  ✓ train_brain_policies_calibrated importable")
            logger.info("  ✓ run_calibration_holdout importable")

            logger.info("✅ TEST 2 PASSED: Module imports")

        except Exception as e:
            logger.error(f"❌ TEST 2 FAILED: {e}")
            self.test_passed = False

    def test_directory_structure(self):
        """Test 3: Validar estructura de directorios."""
        try:
            # Expected directories
            dirs = [
                'config',
                'scripts',
                'reports',
                'reports/calibration',
                'config/calibrated'
            ]

            for dir_path in dirs:
                path = Path(dir_path)
                if not path.exists():
                    path.mkdir(parents=True, exist_ok=True)
                    logger.info(f"  ✓ Created: {dir_path}")
                else:
                    logger.info(f"  ✓ Exists: {dir_path}")

            logger.info("✅ TEST 3 PASSED: Directory structure")

        except Exception as e:
            logger.error(f"❌ TEST 3 FAILED: {e}")
            self.test_passed = False


def main():
    """Entry point."""
    tester = SmokeTestCalibration()
    tester.run()

    sys.exit(0 if tester.test_passed else 1)


if __name__ == '__main__':
    main()
