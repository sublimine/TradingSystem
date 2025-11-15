"""
Elite Trading System - Main Entry Point with LIVE/PAPER Execution

MANDATO 23: Integración de sistema de ejecución institucional con separación quirúrgica.

Features:
- ExecutionMode explícito: RESEARCH, PAPER, LIVE
- PaperExecutionAdapter: Simulación realista (VenueSimulator)
- LiveExecutionAdapter: Ejecución REAL con KillSwitch
- Kill Switch multi-capa para LIVE mode
- Separación total PAPER vs LIVE

Usage:
    # Paper trading (simulado, zero riesgo)
    python main_with_execution.py --mode paper --capital 10000

    # Live trading (REAL, dinero en riesgo)
    python main_with_execution.py --mode live --capital 10000

    # Backtest mode
    python main_with_execution.py --mode backtest --days 90

Author: SUBLIMINE Institutional Trading System
Version: 2.1 - MANDATO 23
Date: 2025-11-14
"""

import argparse
import logging
import sys
from pathlib import Path
from datetime import datetime
import yaml

# Import execution system (MANDATO 23)
from src.execution import (
    ExecutionMode,
    ExecutionAdapter,
    PaperExecutionAdapter,
    LiveExecutionAdapter,
    KillSwitch,
    KillSwitchState,
    CircuitBreakerManager
)

# Import core components
from src.core.brain import InstitutionalBrain
from src.core.ml_adaptive_engine import MLAdaptiveEngine
from src.core.ml_supervisor import MLSupervisor
from src.core.risk_manager import RiskManager
from src.core.position_manager import PositionManager
from src.core.regime_detector import RegimeDetector
from src.core.mtf_manager import MultiTimeframeManager

# Import reporting
from src.reporting.institutional_reports import InstitutionalReportingSystem

# Import strategy orchestrator
from src.strategy_orchestrator import StrategyOrchestrator

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/trading_system.log'),
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)


class EliteTradingSystemV2:
    """
    Main trading system orchestrator with execution adapters (MANDATO 23).

    Features:
    - Execution mode selection (RESEARCH, PAPER, LIVE)
    - Paper execution via PaperExecutionAdapter
    - Live execution via LiveExecutionAdapter + KillSwitch
    - Separación quirúrgica PAPER/LIVE
    """

    def __init__(
        self,
        config_path: str = 'config/system_config.yaml',
        execution_mode: str = 'paper',
        auto_ml: bool = True
    ):
        """
        Initialize trading system.

        Args:
            config_path: Path to configuration file
            execution_mode: 'research', 'paper', or 'live'
            auto_ml: Auto-initialize ML engine (default: True)
        """
        logger.info("=" * 80)
        logger.info("ELITE INSTITUTIONAL TRADING SYSTEM V2.1 (MANDATO 23) - INITIALIZING")
        logger.info("=" * 80)

        # Parse execution mode
        self.execution_mode = ExecutionMode.from_string(execution_mode)

        logger.critical(f"Execution Mode: {self.execution_mode.value.upper()}")
        logger.critical(f"Description: {self.execution_mode.get_description()}")
        logger.critical(f"Risk Level: {self.execution_mode.get_risk_level()}")

        # Load configuration
        self.config = self._load_config(config_path)

        # Merge live trading config if LIVE mode
        if self.execution_mode == ExecutionMode.LIVE:
            self._load_live_trading_config()

        # Create output directories
        self._create_directories()

        # Initialize execution system (MANDATO 23)
        self.execution_adapter = None
        self.kill_switch = None
        self._initialize_execution_system()

        # Initialize core components
        logger.info("Initializing core components...")

        # 1. Risk Manager
        self.risk_manager = RiskManager(self.config)
        logger.info("✓ Risk Manager initialized")

        # 2. Position Manager
        self.position_manager = PositionManager(self.config)
        logger.info("✓ Position Manager initialized")

        # 3. Regime Detector
        self.regime_detector = RegimeDetector(self.config)
        logger.info("✓ Regime Detector initialized")

        # 4. Multi-Timeframe Manager
        self.mtf_manager = MultiTimeframeManager(self.config)
        logger.info("✓ Multi-Timeframe Manager initialized")

        # 5. ML Adaptive Engine (AUTO-INITIALIZED)
        self.ml_engine = None
        if auto_ml:
            try:
                self.ml_engine = MLAdaptiveEngine(self.config)
                logger.info("✓✓ ML Adaptive Engine ENABLED (auto-learning active)")
            except Exception as e:
                logger.warning(f"⚠️  ML Engine initialization failed: {e}")
                logger.warning("⚠️  Continuing without ML (manual mode)")
        else:
            logger.info("⚠️  ML Adaptive Engine DISABLED (manual mode)")

        # 6. Institutional Brain
        self.brain = InstitutionalBrain(
            config=self.config,
            risk_manager=self.risk_manager,
            position_manager=self.position_manager,
            regime_detector=self.regime_detector,
            mtf_manager=self.mtf_manager,
            ml_engine=self.ml_engine  # Pass ML engine (can be None)
        )
        logger.info("✓ Institutional Brain initialized")

        # 7. Strategy Orchestrator
        self.strategy_orchestrator = StrategyOrchestrator(
            config_path='config/strategies_institutional.yaml',
            brain=self.brain
        )
        logger.info(f"✓ Strategy Orchestrator initialized ({len(self.strategy_orchestrator.strategies)} strategies)")

        # 8. Reporting System
        self.reporting = InstitutionalReportingSystem(output_dir='reports/')
        logger.info("✓ Institutional Reporting System initialized")

        # 9. ML Supervisor (AUTO-ENABLED - Takes autonomous action)
        self.ml_supervisor = MLSupervisor(
            config=self.config,
            ml_engine=self.ml_engine,
            strategy_orchestrator=self.strategy_orchestrator,
            reporting_system=self.reporting
        )
        logger.info("✓✓ ML Supervisor ENABLED (autonomous decision-making active)")

        # State
        self.is_running = False
        self.closed_trades = []  # Track all closed trades

        logger.info("=" * 80)
        logger.info("SYSTEM INITIALIZATION COMPLETE")
        logger.info(f"Execution Mode: {self.execution_mode.value.upper()}")
        logger.info(f"Execution Adapter: {self.execution_adapter.get_mode_name()}")
        logger.info(f"ML Engine: {'ENABLED ✓' if self.ml_engine else 'DISABLED ✗'}")
        logger.info(f"Strategies Loaded: {len(self.strategy_orchestrator.strategies)}")

        if self.execution_mode == ExecutionMode.LIVE:
            logger.critical("⚠️⚠️⚠️  LIVE MODE: REAL MONEY AT RISK  ⚠️⚠️⚠️")
            logger.critical(f"Kill Switch: {self.kill_switch.get_state().value}")

        logger.info("=" * 80)

    def _load_config(self, config_path: str) -> dict:
        """Load system configuration."""
        try:
            with open(config_path, 'r') as f:
                config = yaml.safe_load(f)
            logger.info(f"✓ Configuration loaded from {config_path}")
            return config
        except FileNotFoundError:
            logger.warning(f"⚠️  Config file not found: {config_path}")
            logger.info("⚠️  Using default configuration")
            return self._get_default_config()

    def _load_live_trading_config(self):
        """Load live trading specific config."""
        try:
            with open('config/live_trading_config.yaml', 'r') as f:
                live_config = yaml.safe_load(f)

            # Merge live config
            if 'live_trading' not in self.config:
                self.config['live_trading'] = {}

            self.config['live_trading'].update(live_config.get('live_trading', {}))

            logger.info("✓ Live trading config loaded")

        except FileNotFoundError:
            logger.warning("⚠️  Live trading config not found, using defaults")

            # Default live trading config
            self.config['live_trading'] = {
                'enabled': False,  # MUST be explicitly enabled
                'max_latency_ms': 500,
                'max_ping_age_seconds': 30,
                'max_corrupted_ticks': 10,
                'max_order_retries': 3,
                'retry_delay_ms': 100
            }

    def _get_default_config(self) -> dict:
        """Get default configuration if file not found."""
        return {
            'risk': {
                'max_risk_per_trade': 0.01,
                'max_portfolio_risk': 0.06,
                'max_correlation': 0.7,
                'max_concurrent_positions': 5
            },
            'execution': {
                'slippage_pips': 0.5,
                'max_spread_pips': 3.0,
                'commission_per_lot': 7.0
            },
            'paper_trading': {
                'initial_balance': 10000.0,
                'fill_probability': 0.98,
                'hold_time_ms': 50.0
            },
            'live_trading': {
                'enabled': False,
                'max_latency_ms': 500,
                'max_ping_age_seconds': 30,
                'max_corrupted_ticks': 10
            },
            'reporting': {
                'generate_daily': True,
                'generate_weekly': True,
                'generate_monthly': True
            },
            'ml': {
                'enabled': True,
                'learning_rate': 0.01,
                'min_trades_for_learning': 20
            }
        }

    def _create_directories(self):
        """Create necessary directories for reports and logs."""
        directories = [
            'logs',
            'reports',
            'backtest_reports',
            'ml_data',
            'trade_history'
        ]

        for dir_name in directories:
            Path(dir_name).mkdir(parents=True, exist_ok=True)

        logger.info("✓ Output directories created/verified")

    def _initialize_execution_system(self):
        """
        Initialize execution system based on mode.

        CRITICAL: Separate PAPER vs LIVE initialization.
        """
        logger.info("=" * 80)
        logger.info(f"INITIALIZING EXECUTION SYSTEM: {self.execution_mode.value.upper()}")
        logger.info("=" * 80)

        if self.execution_mode == ExecutionMode.PAPER:
            # PAPER: Simulación, zero riesgo
            logger.warning("⚠️  PAPER MODE: All execution is SIMULATED")
            logger.warning("⚠️  NO REAL ORDERS will be sent to broker")

            self.execution_adapter = PaperExecutionAdapter(config=self.config)

            if not self.execution_adapter.initialize():
                raise RuntimeError("PaperExecutionAdapter initialization failed")

            logger.info("✓ PaperExecutionAdapter initialized")

        elif self.execution_mode == ExecutionMode.LIVE:
            # LIVE: Ejecución REAL, KillSwitch required
            logger.critical("🚨🚨🚨  LIVE MODE: INITIALIZING REAL EXECUTION  🚨🚨🚨")

            # Initialize KillSwitch
            self.kill_switch = KillSwitch(
                config=self.config,
                circuit_breaker_manager=None  # TODO: integrate with existing
            )

            logger.info("✓ Kill Switch initialized")

            # Check if live trading is enabled in config
            if not self.config.get('live_trading', {}).get('enabled', False):
                logger.critical(
                    "⚠️⚠️⚠️  LIVE TRADING DISABLED IN CONFIG  ⚠️⚠️⚠️"
                )
                logger.critical(
                    "To enable: Set 'live_trading.enabled: true' in config/live_trading_config.yaml"
                )
                raise RuntimeError(
                    "Live trading is DISABLED in config. "
                    "Enable it explicitly to proceed."
                )

            # Initialize LiveExecutionAdapter
            self.execution_adapter = LiveExecutionAdapter(
                config=self.config,
                kill_switch=self.kill_switch
            )

            if not self.execution_adapter.initialize():
                raise RuntimeError("LiveExecutionAdapter initialization failed")

            logger.critical("✅ LiveExecutionAdapter initialized")
            logger.critical(f"Kill Switch State: {self.kill_switch.get_state().value}")

            # Check kill switch
            if not self.kill_switch.can_send_orders():
                logger.critical("⚠️  Kill Switch is BLOCKING orders")
                status = self.kill_switch.get_status()
                logger.critical(f"Failed layers: {status.failed_layers}")
                logger.critical(f"Reason: {status.reason}")

        else:
            # RESEARCH: No execution (backtest only)
            logger.info("RESEARCH MODE: No execution adapter needed")
            self.execution_adapter = None

        logger.info("=" * 80)

    def run_paper_trading(self):
        """
        Run system in paper trading mode (demo account).

        Uses PaperExecutionAdapter for simulated fills.
        """
        logger.info("=" * 80)
        logger.info("STARTING PAPER TRADING MODE")
        logger.info("=" * 80)

        if self.execution_mode != ExecutionMode.PAPER:
            logger.error(f"Cannot run paper trading in {self.execution_mode.value} mode")
            return

        self.is_running = True

        # Main trading loop
        try:
            while self.is_running:
                # Trading logic aquí (simplified for now)
                # TODO: Implement full trading loop

                import time
                time.sleep(60)  # 1 minute between updates

        except KeyboardInterrupt:
            logger.info("\n⚠️  Shutdown requested by user")
            self.shutdown()

    def run_live_trading(self):
        """
        Run system in live trading mode (real account).

        Uses LiveExecutionAdapter + KillSwitch for REAL execution.
        """
        logger.critical("=" * 80)
        logger.critical("STARTING LIVE TRADING MODE")
        logger.critical("=" * 80)

        if self.execution_mode != ExecutionMode.LIVE:
            logger.error(f"Cannot run live trading in {self.execution_mode.value} mode")
            return

        # Triple confirmation
        logger.critical("⚠️⚠️⚠️  LIVE TRADING MODE - REAL MONEY AT RISK  ⚠️⚠️⚠️")
        logger.critical(f"Kill Switch State: {self.kill_switch.get_state().value}")

        confirm1 = input("Type 'YES' to confirm live trading: ")
        if confirm1 != 'YES':
            logger.info("Live trading cancelled")
            return

        confirm2 = input("Type 'CONFIRM' to proceed with REAL money: ")
        if confirm2 != 'CONFIRM':
            logger.info("Live trading cancelled")
            return

        confirm3 = input("Final confirmation - Type 'LIVE' to start: ")
        if confirm3 != 'LIVE':
            logger.info("Live trading cancelled")
            return

        logger.critical("✅ Live trading confirmed - Starting...")

        self.is_running = True

        # Main trading loop (same as paper but with LiveExecutionAdapter)
        try:
            while self.is_running:
                # Check kill switch periodically
                if not self.kill_switch.can_send_orders():
                    logger.critical(
                        f"⚠️  KILL SWITCH ACTIVE: {self.kill_switch.get_state().value}"
                    )
                    # Pause trading but don't exit
                    import time
                    time.sleep(60)
                    continue

                # Trading logic aquí
                # TODO: Implement full trading loop

                import time
                time.sleep(60)  # 1 minute between updates

        except KeyboardInterrupt:
            logger.critical("\n⚠️  EMERGENCY SHUTDOWN REQUESTED BY USER")
            self.shutdown()

    def shutdown(self):
        """Gracefully shutdown system."""
        logger.critical("=" * 80)
        logger.critical("SHUTTING DOWN SYSTEM")
        logger.critical("=" * 80)

        self.is_running = False

        # Shutdown execution adapter
        if self.execution_adapter:
            self.execution_adapter.shutdown()

        logger.critical("=" * 80)
        logger.critical("SHUTDOWN COMPLETE")
        logger.critical("=" * 80)


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='Elite Institutional Trading System V2.1 (MANDATO 23)'
    )

    parser.add_argument(
        '--mode',
        type=str,
        choices=['research', 'paper', 'live', 'backtest'],
        default='paper',
        help='Trading mode: research, paper (demo), live (real), or backtest'
    )

    parser.add_argument(
        '--capital',
        type=float,
        default=10000.0,
        help='Starting capital'
    )

    parser.add_argument(
        '--days',
        type=int,
        default=90,
        help='Number of days for backtesting'
    )

    parser.add_argument(
        '--no-ml',
        action='store_true',
        help='Disable ML adaptive engine'
    )

    parser.add_argument(
        '--config',
        type=str,
        default='config/system_config.yaml',
        help='Path to configuration file'
    )

    args = parser.parse_args()

    # Initialize system
    try:
        system = EliteTradingSystemV2(
            config_path=args.config,
            execution_mode=args.mode,
            auto_ml=not args.no_ml
        )

        # Run in selected mode
        if args.mode == 'paper':
            system.run_paper_trading()
        elif args.mode == 'live':
            system.run_live_trading()
        elif args.mode in ['backtest', 'research']:
            logger.info("Backtest/Research mode - No execution")
            # TODO: Implement backtest

    except Exception as e:
        logger.critical(f"FATAL ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
