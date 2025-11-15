#!/usr/bin/env python3
"""
Start Live Trading - Script de inicio LIVE con validaciones

MANDATO 23: Live Execution & Kill Switch
MANDATO 26: Production Hardening (health checks integrated)

Valida prerequisites antes de lanzar LIVE trading:
- HEALTH CHECKS (smoke test) - MANDATO 26
- Config LIVE habilitado
- MT5 conectado
- Kill Switch operacional
- Risk limits configurados
- Confirmación del operador

Usage:
    python scripts/start_live_trading.py --capital 10000
    python scripts/start_live_trading.py --capital 10000 --skip-health-check
    python scripts/start_live_trading.py --capital 10000 --force-start

Author: SUBLIMINE Institutional Trading System
Date: 2025-11-15 (Updated for MANDATO 26)
"""

import sys
import os
import argparse
import yaml
import logging
import subprocess
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

import MetaTrader5 as mt5
from src.mt5_connector import MT5Connector

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


class LiveTradingLauncher:
    """
    Launcher para LIVE trading con validaciones completas.
    """

    def __init__(self, capital: float, skip_health_check: bool = False, force_start: bool = False):
        """
        Inicializa launcher.

        Args:
            capital: Capital inicial
            skip_health_check: Skip smoke tests (NOT RECOMMENDED FOR LIVE)
            force_start: Force start despite P1 failures (CRITICAL APPROVAL REQUIRED)
        """
        self.capital = capital
        self.skip_health_check = skip_health_check
        self.force_start = force_start
        self.config = None
        self.live_config = None

    def run(self):
        """
        Ejecuta validaciones y lanza LIVE trading.
        """
        logger.critical("=" * 80)
        logger.critical("🚨 LIVE TRADING LAUNCHER - MANDATO 26 🚨")
        logger.critical("=" * 80)
        logger.critical(f"Capital: ${self.capital:,.2f}")
        logger.critical("⚠️  REAL MONEY AT RISK  ⚠️")
        logger.critical("=" * 80)

        # Step 0: HEALTH CHECKS (MANDATO 26)
        if not self.skip_health_check:
            logger.critical("")
            logger.critical("Step 0/6: Running MANDATORY health checks...")
            health_status = self._run_health_checks()

            if health_status == 1:
                # P0 failure - ABORT (MANDATORY)
                logger.critical("")
                logger.critical("=" * 80)
                logger.critical("❌ P0 HEALTH CHECK FAILURE - LAUNCH ABORTED")
                logger.critical("=" * 80)
                logger.critical("Infrastructure is broken. DO NOT START LIVE TRADING.")
                logger.critical("Fix P0 issues and re-run smoke test before attempting LIVE.")
                logger.critical("")
                logger.critical("To view detailed report:")
                logger.critical("  ls -lt reports/health/SMOKE_TEST_INSTITUTIONAL_*.md | head -1")
                logger.critical("=" * 80)
                return False

            elif health_status == 2:
                # P1 failure - CRITICAL WARNING
                logger.critical("")
                logger.critical("=" * 80)
                logger.critical("🚨 P1 HEALTH CHECK FAILURES DETECTED 🚨")
                logger.critical("=" * 80)
                logger.critical("Core trading functionality may be impaired.")
                logger.critical("LAUNCHING LIVE WITH P1 FAILURES IS EXTREMELY RISKY.")
                logger.critical("")

                if not self.force_start:
                    logger.critical("Options:")
                    logger.critical("  1. ABORT and fix P1 issues (STRONGLY RECOMMENDED)")
                    logger.critical("  2. Force start with --force-start")
                    logger.critical("     ⚠️  REQUIRES: Risk Manager + CTO approval")
                    logger.critical("     ⚠️  MUST: Document in compliance log")
                    logger.critical("")
                    logger.critical("ABORTING LAUNCH FOR SAFETY.")
                    logger.critical("=" * 80)
                    return False
                else:
                    logger.critical("🚨 FORCE START ENABLED - PROCEEDING WITH P1 FAILURES 🚨")
                    logger.critical("⚠️  This decision MUST be approved by:")
                    logger.critical("    - Risk Manager")
                    logger.critical("    - CTO / Technical Lead")
                    logger.critical("⚠️  Document this in compliance/operational log")
                    logger.critical("=" * 80)
                    input("Press ENTER to acknowledge and continue...")
                    # Continue with force start

            elif health_status == 3:
                # P2 warnings
                logger.critical("")
                logger.critical("⚠️  P2 warnings detected (non-critical) - proceeding")
                logger.critical("")

            else:
                # All pass
                logger.critical("✅ Health checks PASSED")
                logger.critical("")
        else:
            logger.critical("")
            logger.critical("=" * 80)
            logger.critical("🚨 HEALTH CHECKS SKIPPED (--skip-health-check) 🚨")
            logger.critical("=" * 80)
            logger.critical("⚠️  THIS IS EXTREMELY DANGEROUS FOR LIVE TRADING")
            logger.critical("⚠️  Skipping health checks can result in REAL MONEY LOSS")
            logger.critical("⚠️  This override MUST be approved by CTO")
            logger.critical("=" * 80)
            confirm = input("Type 'I UNDERSTAND THE RISKS' to continue: ")
            if confirm != "I UNDERSTAND THE RISKS":
                logger.critical("Launch cancelled")
                return False
            logger.critical("")

        # Step 1: Load configs
        if not self._load_configs():
            return False

        # Step 2: Validate live trading enabled
        if not self._validate_live_enabled():
            return False

        # Step 3: Validate MT5 connection
        if not self._validate_mt5_connection():
            return False

        # Step 4: Validate risk limits
        if not self._validate_risk_limits():
            return False

        # Step 5: Confirm with operator
        if not self._confirm_with_operator():
            return False

        # Step 6: Launch LIVE trading
        logger.critical("=" * 80)
        logger.critical("🚀 LAUNCHING LIVE TRADING 🚀")
        logger.critical("=" * 80)

        self._launch_live_trading()

        return True

    def _run_health_checks(self) -> int:
        """
        Ejecuta smoke test institucional (MANDATORY para LIVE).

        Returns:
            Exit code from smoke test (0=pass, 1=P0 fail, 2=P1 fail, 3=P2 warn)
        """
        script_path = Path(__file__).parent / "smoke_test_institutional.py"

        if not script_path.exists():
            logger.critical(f"❌ CRITICAL: Smoke test not found: {script_path}")
            logger.critical("❌ Cannot launch LIVE without health checks")
            return 1  # Treat missing smoke test as P0 failure for LIVE

        try:
            # Run FULL smoke test for LIVE (not just production subset)
            logger.critical("Running FULL smoke test (LIVE mode requires comprehensive checks)...")
            result = subprocess.run(
                [sys.executable, str(script_path)],
                capture_output=True,
                text=True,
                timeout=60
            )

            # Print output
            if result.stdout:
                print(result.stdout)

            return result.returncode

        except subprocess.TimeoutExpired:
            logger.critical("❌ Health check timed out (>60s)")
            logger.critical("❌ This indicates a serious system problem")
            return 1  # Treat timeout as P0 failure

        except Exception as e:
            logger.critical(f"❌ Health check failed to run: {e}")
            return 1  # Treat errors as P0 failure

    def _load_configs(self) -> bool:
        """
        Carga configuraciones.

        Returns:
            True si exitoso, False si falla
        """
        logger.info("Loading configurations...")

        try:
            # System config
            with open('config/system_config.yaml', 'r') as f:
                self.config = yaml.safe_load(f)

            logger.info("✓ System config loaded")

            # Live trading config
            with open('config/live_trading_config.yaml', 'r') as f:
                self.live_config = yaml.safe_load(f)

            logger.info("✓ Live trading config loaded")

            return True

        except FileNotFoundError as e:
            logger.error(f"Config file not found: {e}")
            return False

        except yaml.YAMLError as e:
            logger.error(f"YAML parsing error: {e}")
            return False

    def _validate_live_enabled(self) -> bool:
        """
        Valida que LIVE trading esté habilitado en config.

        Returns:
            True si habilitado, False si no
        """
        logger.info("Validating LIVE trading enabled...")

        enabled = self.live_config.get('live_trading', {}).get('enabled', False)

        if not enabled:
            logger.critical("⚠️⚠️⚠️  LIVE TRADING IS DISABLED  ⚠️⚠️⚠️")
            logger.critical("")
            logger.critical("To enable LIVE trading:")
            logger.critical("1. Edit config/live_trading_config.yaml")
            logger.critical("2. Set 'live_trading.enabled: true'")
            logger.critical("3. Review all risk limits")
            logger.critical("4. Save and re-run this script")
            logger.critical("")
            logger.critical("WARNING: Enabling LIVE trading means REAL MONEY AT RISK")
            return False

        logger.critical("✅ LIVE trading is ENABLED in config")
        logger.critical("⚠️  REAL MONEY AT RISK  ⚠️")

        return True

    def _validate_mt5_connection(self) -> bool:
        """
        Valida conexión a MT5.

        Returns:
            True si conectado, False si no
        """
        logger.info("Validating MT5 connection...")

        connector = MT5Connector()

        if not connector.connect():
            logger.critical("❌ Cannot connect to MT5")
            logger.critical("")
            logger.critical("Please ensure:")
            logger.critical("1. MT5 is running")
            logger.critical("2. Account credentials are correct")
            logger.critical("3. Internet connection is stable")
            return False

        # Get account info
        account_info = mt5.account_info()

        if account_info is None:
            logger.critical("❌ Cannot get MT5 account info")
            connector.disconnect()
            return False

        logger.info("✓ MT5 connected successfully")
        logger.info(f"  Account: {account_info.login}")
        logger.info(f"  Server: {account_info.server}")
        logger.info(f"  Balance: ${account_info.balance:,.2f}")
        logger.info(f"  Equity: ${account_info.equity:,.2f}")

        # Check if account is REAL
        if 'demo' in account_info.server.lower():
            logger.warning("⚠️  DEMO ACCOUNT DETECTED")
            logger.warning("This is NOT a real money account")
            confirm = input("Continue with demo account? (yes/no): ")
            if confirm.lower() != 'yes':
                connector.disconnect()
                return False
        else:
            logger.critical("🚨 REAL ACCOUNT DETECTED")
            logger.critical(f"Server: {account_info.server}")
            logger.critical(f"Balance: ${account_info.balance:,.2f}")

        connector.disconnect()
        return True

    def _validate_risk_limits(self) -> bool:
        """
        Valida risk limits configurados.

        Returns:
            True si OK, False si no
        """
        logger.info("Validating risk limits...")

        risk_limits = self.live_config.get('live_trading', {}).get('risk_limits', {})

        logger.info("Risk Limits:")
        logger.info(f"  Max Daily Loss: {risk_limits.get('max_daily_loss_pct', 0)*100:.1f}%")
        logger.info(f"  Max Reject Rate: {risk_limits.get('max_reject_rate_pct', 0)*100:.1f}%")
        logger.info(f"  Max Exposure: {risk_limits.get('max_exposure_pct', 0)*100:.1f}%")

        # Check if risk limits are reasonable
        max_daily_loss = risk_limits.get('max_daily_loss_pct', 0)

        if max_daily_loss > 0.05:  # > 5%
            logger.warning(f"⚠️  Daily loss limit is high: {max_daily_loss*100:.1f}%")
            logger.warning("Consider reducing to <= 2% for institutional trading")

        if max_daily_loss <= 0:
            logger.critical("❌ Invalid daily loss limit")
            return False

        logger.info("✓ Risk limits validated")

        return True

    def _confirm_with_operator(self) -> bool:
        """
        Confirmación final con operador.

        Returns:
            True si confirmado, False si no
        """
        logger.critical("=" * 80)
        logger.critical("FINAL CONFIRMATION REQUIRED")
        logger.critical("=" * 80)

        logger.critical(f"Capital: ${self.capital:,.2f}")
        logger.critical("Mode: LIVE (REAL MONEY)")

        risk_limits = self.live_config.get('live_trading', {}).get('risk_limits', {})
        max_daily_loss_usd = self.capital * risk_limits.get('max_daily_loss_pct', 0.02)

        logger.critical(f"Max Daily Loss: ${max_daily_loss_usd:,.2f} ({risk_limits.get('max_daily_loss_pct', 0.02)*100:.1f}%)")

        logger.critical("")
        logger.critical("⚠️⚠️⚠️  READY TO START LIVE TRADING  ⚠️⚠️⚠️")
        logger.critical("")

        confirm1 = input("Type 'YES' to confirm: ")
        if confirm1 != 'YES':
            logger.info("Launch cancelled")
            return False

        confirm2 = input("Type 'CONFIRM' to proceed with REAL money: ")
        if confirm2 != 'CONFIRM':
            logger.info("Launch cancelled")
            return False

        confirm3 = input("Final confirmation - Type 'LIVE' to start: ")
        if confirm3 != 'LIVE':
            logger.info("Launch cancelled")
            return False

        logger.critical("✅ CONFIRMED - Launching LIVE trading...")

        return True

    def _launch_live_trading(self):
        """
        Lanza LIVE trading via main_institutional.py (MANDATO 24).
        """
        import subprocess

        cmd = [
            sys.executable,
            'main_institutional.py',  # MANDATO 24: Unified entry point
            '--mode', 'live',
            '--capital', str(self.capital)
        ]

        logger.info(f"Executing: {' '.join(cmd)}")

        try:
            subprocess.run(cmd, check=True)
        except subprocess.CalledProcessError as e:
            logger.critical(f"LIVE trading failed: {e}")
        except KeyboardInterrupt:
            logger.critical("LIVE trading interrupted by user")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='Start LIVE trading with validations (MANDATO 26: Health checks integrated)'
    )

    parser.add_argument(
        '--capital',
        type=float,
        default=10000.0,
        help='Starting capital (default: 10000)'
    )

    parser.add_argument(
        '--skip-health-check',
        action='store_true',
        help='Skip health checks (EXTREMELY DANGEROUS - requires CTO approval)'
    )

    parser.add_argument(
        '--force-start',
        action='store_true',
        help='Force start despite P1 failures (requires Risk Manager + CTO approval)'
    )

    args = parser.parse_args()

    launcher = LiveTradingLauncher(
        capital=args.capital,
        skip_health_check=args.skip_health_check,
        force_start=args.force_start
    )

    try:
        launcher.run()
    except Exception as e:
        logger.critical(f"FATAL ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
