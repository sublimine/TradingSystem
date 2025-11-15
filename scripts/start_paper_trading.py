#!/usr/bin/env python3
"""
Start Paper Trading - Script de inicio PAPER con health checks

MANDATO 26: Production Hardening

Valida prerequisites antes de lanzar PAPER trading:
- Health checks (smoke test)
- Config cargado
- Sistema funcional
- Confirmación del operador

Usage:
    python scripts/start_paper_trading.py --capital 10000
    python scripts/start_paper_trading.py --capital 10000 --skip-health-check
    python scripts/start_paper_trading.py --capital 10000 --force-start

Author: SUBLIMINE Institutional Trading System
Date: 2025-11-15
Mandate: M26
"""

import sys
import os
import argparse
import subprocess
import logging
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


class PaperTradingLauncher:
    """
    Launcher para PAPER trading con health checks integrados.
    """

    def __init__(self, capital: float, skip_health_check: bool = False, force_start: bool = False):
        """
        Inicializa launcher.

        Args:
            capital: Capital inicial
            skip_health_check: Skip smoke tests (NOT RECOMMENDED)
            force_start: Force start despite P1 failures (NEEDS APPROVAL)
        """
        self.capital = capital
        self.skip_health_check = skip_health_check
        self.force_start = force_start

    def run(self):
        """
        Ejecuta validaciones y lanza PAPER trading.
        """
        logger.info("=" * 80)
        logger.info("PAPER TRADING LAUNCHER - MANDATO 26")
        logger.info("=" * 80)
        logger.info(f"Capital: ${self.capital:,.2f}")
        logger.info("=" * 80)

        # Step 1: Run health checks (smoke test)
        if not self.skip_health_check:
            logger.info("")
            logger.info("Step 1/3: Running health checks...")
            health_status = self._run_health_checks()

            if health_status == 1:
                # P0 failure - ABORT
                logger.error("")
                logger.error("=" * 80)
                logger.error("❌ P0 HEALTH CHECK FAILURE - ABORTING LAUNCH")
                logger.error("=" * 80)
                logger.error("Infrastructure is broken. DO NOT START trading.")
                logger.error("Fix P0 issues and re-run smoke test.")
                logger.error("")
                logger.error("To view detailed report:")
                logger.error("  ls -lt reports/health/SMOKE_TEST_INSTITUTIONAL_*.md | head -1")
                logger.error("=" * 80)
                return False

            elif health_status == 2:
                # P1 failure - WARNING
                logger.warning("")
                logger.warning("=" * 80)
                logger.warning("⚠️  P1 HEALTH CHECK FAILURES DETECTED")
                logger.warning("=" * 80)
                logger.warning("Core functionality may be impaired.")
                logger.warning("")

                if not self.force_start:
                    logger.warning("Options:")
                    logger.warning("  1. ABORT and fix P1 issues (RECOMMENDED)")
                    logger.warning("  2. Force start with --force-start (REQUIRES APPROVAL)")
                    logger.warning("")
                    logger.warning("Aborting launch for safety.")
                    logger.warning("=" * 80)
                    return False
                else:
                    logger.warning("⚠️  FORCE START enabled - proceeding despite P1 failures")
                    logger.warning("⚠️  This requires Risk Manager approval")
                    logger.warning("⚠️  Document this decision in operational log")
                    logger.warning("=" * 80)
                    # Continue with force start

            elif health_status == 3:
                # P2 warnings
                logger.info("")
                logger.info("⚠️  P2 warnings detected (non-critical) - proceeding")
                logger.info("")

            else:
                # All pass
                logger.info("✅ Health checks passed")
                logger.info("")
        else:
            logger.warning("")
            logger.warning("⚠️  HEALTH CHECKS SKIPPED (--skip-health-check)")
            logger.warning("⚠️  This is NOT RECOMMENDED for production use")
            logger.warning("")

        # Step 2: Confirm with operator
        logger.info("Step 2/3: Operator confirmation...")
        if not self._confirm_with_operator():
            logger.info("Launch cancelled by operator")
            return False

        # Step 3: Launch PAPER trading
        logger.info("")
        logger.info("Step 3/3: Launching PAPER trading...")
        logger.info("=" * 80)
        logger.info("🚀 LAUNCHING PAPER TRADING")
        logger.info("=" * 80)
        logger.info("")

        self._launch_paper_trading()

        return True

    def _run_health_checks(self) -> int:
        """
        Ejecuta smoke test institucional.

        Returns:
            Exit code from smoke test (0=pass, 1=P0 fail, 2=P1 fail, 3=P2 warn)
        """
        script_path = Path(__file__).parent / "smoke_test_institutional.py"

        if not script_path.exists():
            logger.warning(f"⚠️  Smoke test not found: {script_path}")
            logger.warning("⚠️  Proceeding without health checks")
            return 0

        try:
            # Run smoke test with production subset (faster)
            result = subprocess.run(
                [sys.executable, str(script_path), "--subset", "production"],
                capture_output=True,
                text=True,
                timeout=30
            )

            # Print output
            if result.stdout:
                print(result.stdout)

            return result.returncode

        except subprocess.TimeoutExpired:
            logger.error("❌ Health check timed out (>30s)")
            logger.error("❌ This may indicate a system problem")
            return 1  # Treat timeout as P0 failure

        except Exception as e:
            logger.error(f"❌ Health check failed to run: {e}")
            return 1  # Treat errors as P0 failure

    def _confirm_with_operator(self) -> bool:
        """
        Solicita confirmación del operador.

        Returns:
            True si operador confirma, False si cancela
        """
        print("")
        print("=" * 80)
        print("OPERATOR CONFIRMATION REQUIRED")
        print("=" * 80)
        print(f"Mode: PAPER (simulated)")
        print(f"Capital: ${self.capital:,.2f}")
        print(f"Risk: NO REAL MONEY")
        print("")
        print("Ready to start PAPER trading?")
        print("=" * 80)

        response = input("Type 'YES' to confirm, anything else to cancel: ")

        if response.strip().upper() == "YES":
            logger.info("✅ Operator confirmed launch")
            return True
        else:
            logger.warning("❌ Operator cancelled launch")
            return False

    def _launch_paper_trading(self):
        """
        Lanza main_institutional.py en modo PAPER.
        """
        logger.info(f"Launching: main_institutional.py --mode paper --capital {self.capital}")
        logger.info("")

        try:
            # Launch main_institutional.py
            main_script = Path(__file__).parent.parent / "main_institutional.py"

            if not main_script.exists():
                logger.error(f"❌ main_institutional.py not found: {main_script}")
                return

            # Use subprocess to launch (allows Ctrl+C to work)
            subprocess.run([
                sys.executable,
                str(main_script),
                "--mode", "paper",
                "--capital", str(self.capital)
            ])

        except KeyboardInterrupt:
            logger.info("")
            logger.info("=" * 80)
            logger.info("🛑 PAPER trading stopped by operator (Ctrl+C)")
            logger.info("=" * 80)

        except Exception as e:
            logger.error("")
            logger.error("=" * 80)
            logger.error(f"❌ PAPER trading crashed: {e}")
            logger.error("=" * 80)


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Start PAPER trading with health checks")
    parser.add_argument('--capital', type=float, required=True, help="Initial capital")
    parser.add_argument('--skip-health-check', action='store_true',
                       help="Skip health checks (NOT RECOMMENDED)")
    parser.add_argument('--force-start', action='store_true',
                       help="Force start despite P1 failures (REQUIRES APPROVAL)")

    args = parser.parse_args()

    launcher = PaperTradingLauncher(
        capital=args.capital,
        skip_health_check=args.skip_health_check,
        force_start=args.force_start
    )

    success = launcher.run()

    if not success:
        logger.error("")
        logger.error("Launch aborted")
        sys.exit(1)


if __name__ == '__main__':
    main()
