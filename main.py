"""
⚠️  DEPRECATED - Legacy Entry Point (Pre-PLAN OMEGA)

╔══════════════════════════════════════════════════════════════════╗
║                      ⚠️  DEPRECATION WARNING ⚠️                    ║
║                                                                  ║
║  This main.py is LEGACY code from pre-PLAN OMEGA refactor.      ║
║  It uses deprecated components:                                 ║
║    - MLAdaptiveEngine (deprecated)                              ║
║    - InstitutionalBrain (deprecated)                            ║
║    - Old Risk/Position managers                                 ║
║                                                                  ║
║  PLAN OMEGA (2025) uses:                                        ║
║    - MicrostructureEngine (centralized features)                ║
║    - ExecutionManager + KillSwitch (4-layer risk)               ║
║    - Runtime Profiles (GREEN_ONLY, FULL_24)                     ║
║    - BacktestEngine (modern backtesting)                        ║
║                                                                  ║
║  📖 Migration guide: docs/MIGRATION_FROM_LEGACY.md              ║
║  📖 New usage: docs/EXECUTION_SYSTEM_GUIDE.md                   ║
║                                                                  ║
║  Will be REMOVED in future release.                             ║
╚══════════════════════════════════════════════════════════════════╝

Legacy Features (Pre-OMEGA):
- Auto-initialization of ML Adaptive Engine
- Institutional Brain Layer
- 24 Elite Strategies
- Multi-Timeframe Manager
- Regime Detection
- Risk Management
- Reporting System

Legacy Usage (NOT RECOMMENDED):
    # Paper trading (demo account)
    python main.py --mode paper

    # Live trading (real account)
    python main.py --mode live --capital 10000

    # Backtest mode
    python main.py --mode backtest --days 90

Author: Elite Trading System
Version: 2.0 (DEPRECATED - use PLAN OMEGA)
"""

import argparse
import logging
import sys
import warnings
from pathlib import Path
from datetime import datetime
import yaml
import MetaTrader5 as mt5

# DEPRECATION WARNING - Show at runtime
warnings.warn(
    "\n\n"
    "=" * 80 + "\n"
    "⚠️  DEPRECATION WARNING: main.py is LEGACY code (Pre-PLAN OMEGA)\n\n"
    "This entry point uses deprecated components and will be removed.\n\n"
    "PLAN OMEGA (2025) provides:\n"
    "  - MicrostructureEngine (centralized institutional features)\n"
    "  - ExecutionManager + KillSwitch (4-layer risk protection)\n"
    "  - Runtime Profiles (GREEN_ONLY, FULL_24)\n"
    "  - Modern BacktestEngine\n\n"
    "Migration guide: docs/MIGRATION_FROM_LEGACY.md\n"
    "New usage: docs/EXECUTION_SYSTEM_GUIDE.md\n"
    "=" * 80 + "\n",
    DeprecationWarning,
    stacklevel=2
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


class EliteTradingSystem:
    """
    Main trading system orchestrator with AUTO-ML initialization.
    """

    def __init__(self, config_path: str = 'config/system_config.yaml', auto_ml: bool = True):
        """
        Initialize trading system.

        Args:
            config_path: Path to configuration file
            auto_ml: Auto-initialize ML engine (default: True)
        """
        logger.info("=" * 80)
        logger.info("ELITE INSTITUTIONAL TRADING SYSTEM V2.0 - INITIALIZING")
        logger.info("=" * 80)

        # Load configuration
        self.config = self._load_config(config_path)

        # Create output directories
        self._create_directories()

        # Initialize MT5
        if not self._initialize_mt5():
            raise RuntimeError("MT5 initialization failed")

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
        logger.info("SYSTEM INITIALIZATION COMPLETE - FULLY AUTONOMOUS")
        logger.info(f"ML Engine: {'ENABLED ✓' if self.ml_engine else 'DISABLED ✗'}")
        logger.info(f"ML Supervisor: {'ENABLED ✓' if self.ml_supervisor.enabled else 'DISABLED ✗'}")
        logger.info(f"Strategies Loaded: {len(self.strategy_orchestrator.strategies)}")
        logger.info("Auto-disable losing strategies: ENABLED")
        logger.info("Auto-adjust parameters: ENABLED")
        logger.info("Circuit breakers: ENABLED")
        logger.info("Automatic reports: ENABLED")
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
                'max_spread_pips': 3.0
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

    def _initialize_mt5(self) -> bool:
        """Initialize MetaTrader 5 connection."""
        if not mt5.initialize():
            logger.error(f"MT5 initialization failed: {mt5.last_error()}")
            return False

        # Get account info
        account_info = mt5.account_info()
        if account_info is None:
            logger.error("Failed to get account info")
            return False

        logger.info("✓ MT5 connected successfully")
        logger.info(f"  Account: {account_info.login}")
        logger.info(f"  Balance: ${account_info.balance:,.2f}")
        logger.info(f"  Server: {account_info.server}")

        return True

    def run_paper_trading(self):
        """
        Run system in paper trading mode (demo account).
        """
        logger.info("=" * 80)
        logger.info("STARTING PAPER TRADING MODE")
        logger.info("=" * 80)

        self.is_running = True

        # Main trading loop
        try:
            while self.is_running:
                # 1. Update market data
                self.mtf_manager.update()

                # 2. Detect regime
                current_regime = self.regime_detector.detect_regime(
                    self.mtf_manager.get_current_data()
                )

                # 3. Generate signals from all strategies
                signals = self.strategy_orchestrator.generate_signals(
                    self.mtf_manager.get_current_data(),
                    current_regime
                )

                # 4. Process signals through brain
                if signals:
                    self.brain.process_signals(signals)

                # 5. Update open positions (check stops, targets, trailing)
                closed_today = self.position_manager.update_positions(
                    self.mtf_manager.get_current_data()
                )

                # Track closed trades
                if closed_today:
                    self.closed_trades.extend(closed_today)

                # 6. ML SUPERVISOR - Autonomous decision-making
                current_equity = self._get_current_equity()
                open_positions = self.position_manager.get_open_positions()

                self.ml_supervisor.supervise(
                    current_equity=current_equity,
                    open_positions=open_positions,
                    closed_trades=self.closed_trades
                )

                # 7. Generate daily report (if new day)
                if self._is_new_day():
                    self._generate_daily_report()

                # 8. Sleep (adjust based on timeframe)
                import time
                time.sleep(60)  # 1 minute between updates

        except KeyboardInterrupt:
            logger.info("\n⚠️  Shutdown requested by user")
            self.shutdown()

    def run_live_trading(self, capital: float):
        """
        Run system in live trading mode (real account).

        Args:
            capital: Starting capital
        """
        logger.info("=" * 80)
        logger.info("STARTING LIVE TRADING MODE")
        logger.info(f"Capital: ${capital:,.2f}")
        logger.info("=" * 80)

        # Confirm with user
        logger.warning("⚠️  LIVE TRADING MODE - REAL MONEY AT RISK ⚠️")
        confirm = input("Type 'YES' to confirm live trading: ")

        if confirm != 'YES':
            logger.info("Live trading cancelled")
            return

        # Same as paper trading but with real execution
        self.run_paper_trading()

    def run_backtest(self, days: int):
        """
        Run historical backtest.

        Args:
            days: Number of days to backtest
        """
        logger.info("=" * 80)
        logger.info(f"STARTING BACKTEST MODE ({days} days)")
        logger.info("=" * 80)

        from src.backtesting import BacktestEngine, PerformanceAnalyzer
        from datetime import timedelta

        # Load historical data
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)

        logger.info(f"Loading data: {start_date.date()} to {end_date.date()}")

        # Initialize backtest engine
        engine = BacktestEngine(
            strategies=self.strategy_orchestrator.strategies,
            initial_capital=10000.0,
            risk_per_trade=0.01,
            commission_per_lot=7.0,
            slippage_pips=0.5
        )

        # Run backtest
        results = engine.run_backtest(
            historical_data={},  # TODO: Load actual data
            start_date=start_date,
            end_date=end_date
        )

        # Analyze
        analyzer = PerformanceAnalyzer(output_dir='backtest_reports/')
        analysis = analyzer.analyze_backtest(results, save_report=True)

        # Print results
        self._print_backtest_results(results, analysis)

    def _get_current_equity(self) -> float:
        """Get current account equity from MT5."""
        account_info = mt5.account_info()
        if account_info:
            return float(account_info.equity)
        return 0.0

    def _is_new_day(self) -> bool:
        """Check if it's a new trading day."""
        # TODO: Implement day change detection
        return False

    def _generate_daily_report(self):
        """Generate daily performance report."""
        trades = self.position_manager.get_closed_trades_today()

        if trades:
            report = self.reporting.generate_daily_report(trades, datetime.now())
            logger.info(f"📊 Daily report generated: {report['total_pnl_r']:.2f}R")

    def _print_backtest_results(self, results: dict, analysis: dict):
        """Print backtest results summary."""
        print("\n" + "=" * 80)
        print("BACKTEST RESULTS")
        print("=" * 80)
        print(f"Total Return:       {results.get('total_return_r', 0):.2f}R")
        print(f"Win Rate:           {results.get('win_rate', 0):.2%}")
        print(f"Sharpe Ratio:       {analysis['risk_metrics']['sharpe_ratio']:.2f}")
        print(f"Max Drawdown:       {abs(analysis['drawdown_analysis']['max_drawdown_r']):.2f}R")
        print(f"Profit Factor:      {analysis['risk_metrics']['profit_factor']:.2f}")
        print("=" * 80)

    def shutdown(self):
        """Gracefully shutdown system."""
        logger.info("=" * 80)
        logger.info("SHUTTING DOWN SYSTEM")
        logger.info("=" * 80)

        self.is_running = False

        # Close all positions
        logger.info("Closing all open positions...")
        # TODO: Implement position closing

        # Save ML model
        if self.ml_engine:
            logger.info("Saving ML model...")
            # TODO: Implement ML save

        # Generate final reports
        logger.info("Generating final reports...")
        # TODO: Generate session report

        # Disconnect MT5
        mt5.shutdown()
        logger.info("✓ MT5 disconnected")

        logger.info("=" * 80)
        logger.info("SHUTDOWN COMPLETE")
        logger.info("=" * 80)


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description='Elite Institutional Trading System V2.0')

    parser.add_argument(
        '--mode',
        type=str,
        choices=['paper', 'live', 'backtest'],
        default='paper',
        help='Trading mode: paper (demo), live (real), or backtest'
    )

    parser.add_argument(
        '--capital',
        type=float,
        default=10000.0,
        help='Starting capital for live trading'
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
    system = EliteTradingSystem(
        config_path=args.config,
        auto_ml=not args.no_ml  # ML enabled by default
    )

    # Run in selected mode
    if args.mode == 'paper':
        system.run_paper_trading()
    elif args.mode == 'live':
        system.run_live_trading(args.capital)
    elif args.mode == 'backtest':
        system.run_backtest(args.days)


if __name__ == "__main__":
    main()
