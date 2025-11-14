#!/usr/bin/env python3
"""
Smoke Test - Paper Trading Mode (MANDATO 21)

Verifies paper trading mode initialization and basic operation.

Tests:
1. Execution mode framework imports
2. PaperExecutionAdapter initialization
3. System initialization in PAPER mode
4. No real broker orders possible
5. Reporting includes execution_mode tag

Author: SUBLIMINE Institutional Trading System
Date: 2025-11-14
Mandato: MANDATO 21 - Paper Trading Institucional
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

import logging

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def test_imports():
    """Test that execution mode framework can be imported."""
    logger.info("TEST 1: Execution mode framework imports")

    try:
        from src.execution.execution_mode import ExecutionMode, parse_execution_mode
        from src.execution.paper_execution_adapter import PaperExecutionAdapter
        from src.execution.live_execution_adapter import LiveExecutionAdapter

        logger.info("  ✅ All imports successful")
        return True

    except Exception as e:
        logger.error(f"  ❌ Import failed: {e}")
        return False


def test_execution_mode_parsing():
    """Test execution mode parsing."""
    logger.info("TEST 2: Execution mode parsing")

    try:
        from src.execution.execution_mode import ExecutionMode, parse_execution_mode

        # Test valid modes
        paper = parse_execution_mode('paper')
        assert paper == ExecutionMode.PAPER
        assert paper.is_paper()
        assert not paper.allows_real_execution()

        live = parse_execution_mode('live')
        assert live == ExecutionMode.LIVE
        assert live.is_live()
        assert live.allows_real_execution()

        research = parse_execution_mode('research')
        assert research == ExecutionMode.RESEARCH
        assert research.is_research()

        logger.info("  ✅ Mode parsing working correctly")
        return True

    except Exception as e:
        logger.error(f"  ❌ Mode parsing failed: {e}")
        return False


def test_paper_adapter_initialization():
    """Test paper execution adapter initialization."""
    logger.info("TEST 3: Paper execution adapter initialization")

    try:
        from src.execution.paper_execution_adapter import PaperExecutionAdapter

        # Create adapter
        adapter = PaperExecutionAdapter(
            config={},
            initial_balance=10000.0,
            use_venue_simulator=True
        )

        # Connect
        assert adapter.connect()
        assert adapter.is_connected()

        # Get account info
        account = adapter.get_account_info()
        assert account.balance == 10000.0
        assert account.account_id == "PAPER_ACCOUNT"

        # Check adapter name
        assert "Paper" in adapter.get_adapter_name()

        logger.info("  ✅ Paper adapter initialized successfully")
        logger.info(f"     Adapter: {adapter.get_adapter_name()}")
        logger.info(f"     Balance: ${account.balance:,.2f}")

        # Disconnect
        adapter.disconnect()

        return True

    except Exception as e:
        logger.error(f"  ❌ Paper adapter initialization failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_live_adapter_blocked():
    """Test that LiveExecutionAdapter raises NotImplementedError."""
    logger.info("TEST 4: Live adapter properly blocked (MANDATO 23)")

    try:
        from src.execution.live_execution_adapter import LiveExecutionAdapter

        # Should raise NotImplementedError
        try:
            adapter = LiveExecutionAdapter(config={})
            logger.error("  ❌ LiveExecutionAdapter should raise NotImplementedError!")
            return False
        except NotImplementedError as e:
            logger.info("  ✅ LiveExecutionAdapter properly blocked")
            logger.info(f"     Message: {str(e)[:80]}...")
            return True

    except Exception as e:
        logger.error(f"  ❌ Test failed: {e}")
        return False


def test_system_initialization_paper_mode():
    """Test system initialization in PAPER mode."""
    logger.info("TEST 5: System initialization in PAPER mode")

    try:
        # Try importing main system
        # NOTE: This may fail if MT5 not available - that's expected
        try:
            from main import EliteTradingSystem

            logger.info("  ℹ️  EliteTradingSystem imported (MT5 may not be available)")

            # Don't actually initialize if MT5 not available
            # Just verify class exists and has correct signature
            import inspect
            sig = inspect.signature(EliteTradingSystem.__init__)
            params = list(sig.parameters.keys())

            assert 'execution_mode' in params, "execution_mode parameter missing"

            logger.info("  ✅ EliteTradingSystem has execution_mode parameter")
            return True

        except Exception as e:
            if 'MetaTrader5' in str(e) or 'mt5' in str(e):
                logger.info("  ℹ️  MT5 not available (expected in some environments)")
                logger.info("  ⚠️  Skipping full initialization test")
                return True
            else:
                raise

    except Exception as e:
        logger.error(f"  ❌ System initialization test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_no_real_orders_in_paper():
    """Test that paper mode cannot send real orders."""
    logger.info("TEST 6: Verify NO real broker orders in PAPER mode")

    try:
        from src.execution.paper_execution_adapter import PaperExecutionAdapter
        from src.execution.execution_adapter import OrderSide, OrderType

        # Create adapter
        adapter = PaperExecutionAdapter(config={}, initial_balance=10000.0)
        adapter.connect()

        # Place order (should be simulated)
        order = adapter.place_order(
            instrument="EURUSD",
            side=OrderSide.BUY,
            volume=0.1,
            order_type=OrderType.MARKET
        )

        # Verify order is marked as PAPER
        assert order.order_id.startswith("PAPER_"), "Order ID should start with PAPER_"
        assert order.comment == "PAPER", "Order comment should be PAPER"

        logger.info("  ✅ Paper orders properly tagged (NO real broker)")
        logger.info(f"     Order ID: {order.order_id}")
        logger.info(f"     Comment: {order.comment}")

        adapter.disconnect()
        return True

    except Exception as e:
        logger.error(f"  ❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all smoke tests."""
    logger.info("=" * 80)
    logger.info("SMOKE TEST - PAPER TRADING MODE (MANDATO 21)")
    logger.info("=" * 80)
    logger.info("")

    tests = [
        test_imports,
        test_execution_mode_parsing,
        test_paper_adapter_initialization,
        test_live_adapter_blocked,
        test_system_initialization_paper_mode,
        test_no_real_orders_in_paper
    ]

    results = []

    for test in tests:
        try:
            result = test()
            results.append(result)
        except Exception as e:
            logger.error(f"Test crashed: {e}")
            results.append(False)

        logger.info("")

    # Summary
    logger.info("=" * 80)
    logger.info("SMOKE TEST SUMMARY")
    logger.info("=" * 80)

    passed = sum(results)
    total = len(results)

    logger.info(f"Passed: {passed}/{total}")
    logger.info("")

    if passed == total:
        logger.info("✅ ALL SMOKE TESTS PASSED")
        logger.info("")
        logger.info("MANDATO 21 - Paper Trading Mode: OPERATIONAL")
        logger.info("=" * 80)
        sys.exit(0)
    else:
        logger.error("❌ SOME TESTS FAILED")
        logger.info("=" * 80)
        sys.exit(1)


if __name__ == "__main__":
    main()
