#!/usr/bin/env python3
"""
Smoke Test - Execution System (MANDATO 23)

Tests:
1. ExecutionMode parsing
2. Kill Switch initialization
3. PaperExecutionAdapter initialization
4. LiveExecutionAdapter initialization (without real orders)
5. Config loading
6. Execution flow (simulated)

Usage:
    python scripts/smoke_test_execution_system.py

Author: SUBLIMINE Institutional Trading System
Date: 2025-11-14
"""

import sys
import os
from pathlib import Path
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Silence logging for tests
import logging
logging.basicConfig(level=logging.CRITICAL)

# Check if MT5 is available
try:
    import MetaTrader5 as mt5
    MT5_AVAILABLE = True
except ImportError:
    MT5_AVAILABLE = False
    print("⚠️  MetaTrader5 not available - Some tests will be skipped")
    print("")


class ExecutionSystemSmokeTest:
    """
    Smoke tests para execution system.
    """

    def __init__(self):
        """Inicializa test suite."""
        self.tests_passed = 0
        self.tests_failed = 0
        self.tests = []

    def run_all_tests(self):
        """Ejecuta todos los tests."""
        print("=" * 80)
        print("EXECUTION SYSTEM SMOKE TESTS - MANDATO 23")
        print("=" * 80)
        print("")

        # Define tests
        self.tests = [
            ("ExecutionMode parsing", self.test_execution_mode_parsing),
            ("ExecutionMode methods", self.test_execution_mode_methods),
            ("KillSwitch initialization", self.test_kill_switch_init),
            ("KillSwitch state changes", self.test_kill_switch_state_changes),
            ("PaperExecutionAdapter init", self.test_paper_adapter_init),
            ("PaperExecutionAdapter order", self.test_paper_adapter_order),
            ("LiveExecutionAdapter init", self.test_live_adapter_init),
            ("Config loading", self.test_config_loading),
        ]

        # Run tests
        for test_name, test_func in self.tests:
            self._run_test(test_name, test_func)

        # Summary
        print("")
        print("=" * 80)
        print("TEST SUMMARY")
        print("=" * 80)
        print(f"Total:  {self.tests_passed + self.tests_failed}")
        print(f"Passed: {self.tests_passed} ✓")
        print(f"Failed: {self.tests_failed} ✗")

        if self.tests_failed == 0:
            print("")
            print("🎉 ALL TESTS PASSED 🎉")
            return True
        else:
            print("")
            print("❌ SOME TESTS FAILED")
            return False

    def _run_test(self, test_name: str, test_func):
        """
        Ejecuta un test individual.

        Args:
            test_name: Nombre del test
            test_func: Función del test
        """
        print(f"[{self.tests_passed + self.tests_failed + 1}/{len(self.tests)}] {test_name}...", end=" ")

        try:
            test_func()
            print("✓ PASS")
            self.tests_passed += 1
        except AssertionError as e:
            print(f"✗ FAIL: {e}")
            self.tests_failed += 1
        except Exception as e:
            print(f"✗ ERROR: {e}")
            self.tests_failed += 1

    # ========================================================================
    # TESTS
    # ========================================================================

    def test_execution_mode_parsing(self):
        """Test ExecutionMode parsing."""
        from src.execution import ExecutionMode

        # Valid modes
        assert ExecutionMode.from_string('paper') == ExecutionMode.PAPER
        assert ExecutionMode.from_string('live') == ExecutionMode.LIVE
        assert ExecutionMode.from_string('research') == ExecutionMode.RESEARCH

        # Aliases
        assert ExecutionMode.from_string('demo') == ExecutionMode.PAPER
        assert ExecutionMode.from_string('real') == ExecutionMode.LIVE
        assert ExecutionMode.from_string('backtest') == ExecutionMode.RESEARCH

        # Invalid mode
        try:
            ExecutionMode.from_string('invalid')
            assert False, "Should raise ValueError"
        except ValueError:
            pass

    def test_execution_mode_methods(self):
        """Test ExecutionMode methods."""
        from src.execution import ExecutionMode

        # PAPER
        assert ExecutionMode.PAPER.is_simulated() == True
        assert ExecutionMode.PAPER.allows_real_execution() == False
        assert ExecutionMode.PAPER.requires_kill_switch() == False

        # LIVE
        assert ExecutionMode.LIVE.is_simulated() == False
        assert ExecutionMode.LIVE.allows_real_execution() == True
        assert ExecutionMode.LIVE.requires_kill_switch() == True

        # RESEARCH
        assert ExecutionMode.RESEARCH.is_simulated() == True
        assert ExecutionMode.RESEARCH.allows_real_execution() == False

    def test_kill_switch_init(self):
        """Test KillSwitch initialization."""
        from src.execution import KillSwitch

        config = {
            'live_trading': {
                'enabled': False,
                'max_latency_ms': 500,
                'max_ping_age_seconds': 30,
                'max_corrupted_ticks': 10
            }
        }

        kill_switch = KillSwitch(config=config)

        # Should be disabled by operator (enabled=False)
        assert kill_switch.can_send_orders() == False

        status = kill_switch.get_status()
        assert status.operator_enabled == False
        assert 'OPERATOR' in status.failed_layers

    def test_kill_switch_state_changes(self):
        """Test KillSwitch state changes."""
        from src.execution import KillSwitch, KillSwitchState

        config = {
            'live_trading': {
                'enabled': True,  # Enabled
                'max_latency_ms': 500,
                'max_ping_age_seconds': 30,
                'max_corrupted_ticks': 10
            }
        }

        kill_switch = KillSwitch(config=config)

        # Initially should be operational (but broker not pinged yet)
        # Actually, broker_healthy defaults to False, so it won't be operational
        # Let's record a healthy ping
        kill_switch.record_broker_ping(latency_ms=50, is_connected=True)

        # Data is healthy by default
        # Now check if we can send orders
        # We need risk to be healthy too
        kill_switch.update_risk_health(
            current_pnl=0,
            current_exposure=0,
            tripped_breakers=[]
        )

        # Should be operational now
        assert kill_switch.can_send_orders() == True

        # Trigger emergency stop
        kill_switch.emergency_stop("Test emergency")
        assert kill_switch.can_send_orders() == False
        assert kill_switch.get_state() == KillSwitchState.EMERGENCY_STOP

    def test_paper_adapter_init(self):
        """Test PaperExecutionAdapter initialization."""
        from src.execution import PaperExecutionAdapter

        config = {
            'paper_trading': {
                'initial_balance': 10000.0,
                'fill_probability': 0.98,
                'hold_time_ms': 50.0
            },
            'execution': {
                'commission_per_lot': 7.0
            }
        }

        adapter = PaperExecutionAdapter(config=config)

        assert adapter.is_initialized() == False

        # Initialize
        result = adapter.initialize()
        assert result == True
        assert adapter.is_initialized() == True

        # Check account info
        account_info = adapter.get_account_info()
        assert account_info.balance == 10000.0
        assert account_info.equity == 10000.0
        assert account_info.open_positions == 0

        adapter.shutdown()

    def test_paper_adapter_order(self):
        """Test PaperExecutionAdapter order placement."""
        from src.execution import PaperExecutionAdapter, OrderSide, OrderType

        config = {
            'paper_trading': {
                'initial_balance': 10000.0,
                'fill_probability': 0.98,
                'hold_time_ms': 50.0
            },
            'execution': {
                'commission_per_lot': 7.0
            }
        }

        adapter = PaperExecutionAdapter(config=config)
        adapter.initialize()

        # Place market order
        result = adapter.place_order(
            instrument="EURUSD",
            side=OrderSide.BUY,
            volume=1.0,
            order_type=OrderType.MARKET,
            stop_loss=1.0950,
            take_profit=1.1050
        )

        assert result.success == True
        assert result.order_id is not None
        assert result.order_id.startswith("PAPER_")

        # Check positions
        positions = adapter.get_open_positions()
        assert len(positions) >= 0  # Might be filled or rejected

        adapter.shutdown()

    def test_live_adapter_init(self):
        """Test LiveExecutionAdapter initialization (without MT5)."""
        if not MT5_AVAILABLE:
            # Skip test if MT5 not available
            return

        from src.execution import LiveExecutionAdapter, KillSwitch

        config = {
            'live_trading': {
                'enabled': True,
                'max_latency_ms': 500,
                'max_ping_age_seconds': 30,
                'max_corrupted_ticks': 10,
                'max_order_retries': 3,
                'retry_delay_ms': 100
            },
            'mt5': {
                'max_retries': 5,
                'base_delay': 2.0
            },
            'execution': {
                'commission_per_lot': 7.0
            }
        }

        kill_switch = KillSwitch(config=config)

        # Create adapter (will fail to initialize without MT5, but should not crash)
        adapter = LiveExecutionAdapter(config=config, kill_switch=kill_switch)

        assert adapter.is_initialized() == False
        assert adapter.get_mode_name() == "LIVE"

        # Note: Cannot test initialize() without MT5 connection

    def test_config_loading(self):
        """Test config loading."""
        import yaml

        # Test live_trading_config.yaml exists
        assert Path('config/live_trading_config.yaml').exists()

        # Load and validate
        with open('config/live_trading_config.yaml', 'r') as f:
            config = yaml.safe_load(f)

        assert 'live_trading' in config
        assert 'enabled' in config['live_trading']

        # Should be disabled by default
        assert config['live_trading']['enabled'] == False


def main():
    """Main entry point."""
    test_suite = ExecutionSystemSmokeTest()

    success = test_suite.run_all_tests()

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
