"""
Institutional Trading System - Unified Entry Point

MANDATO 24: Sistema de trading institucional unificado con integración completa.

Features:
- ExecutionMode explícito: RESEARCH, PAPER, LIVE
- Feature Pipeline completo (OFI, CVD, VPIN, L2)
- StrategyOrchestrator con generate_signals()
- Brain filtering integrado
- Kill Switch multi-capa para LIVE
- NON-NEGOTIABLES enforced

Replaces:
- main.py (v1 - loop structure)
- main_with_execution.py (v2 - execution adapters)
- scripts/live_trading_engine*.py (legacy)

Usage:
    # Research mode (backtest)
    python main_institutional.py --mode research --days 90 --capital 10000

    # Paper trading (simulado)
    python main_institutional.py --mode paper --capital 10000

    # Live trading (REAL money)
    python main_institutional.py --mode live --capital 10000

Author: SUBLIMINE Institutional Trading System
Date: 2025-11-15
Version: 3.0 - MANDATO 24
"""

import argparse
import logging
import sys
import time
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
    KillSwitchState
)

# Import core components
from src.core.brain import InstitutionalBrain
from src.core.ml_adaptive_engine import MLAdaptiveEngine
from src.core.ml_supervisor import MLSupervisor
from src.core.risk_manager import RiskManager
from src.core.position_manager import PositionManager
from src.core.regime_detector import RegimeDetector
from src.core.mtf_manager import MultiTimeframeManager

# Import feature pipeline (MANDATO 24)
from src.microstructure import MicrostructureEngine

# Import reporting
from src.reporting.institutional_reports import InstitutionalReportingSystem

# Import strategy orchestrator
from src.strategy_orchestrator import StrategyOrchestrator

# Import backtest engine
from src.backtesting.backtest_engine import BacktestEngine

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


class InstitutionalTradingSystem:
    """
    Sistema de trading institucional unificado (MANDATO 24).

    Soporta 3 modos de ejecución:
    - RESEARCH: Backtest solamente (usa BacktestEngine)
    - PAPER: Trading simulado (PaperExecutionAdapter)
    - LIVE: Trading REAL (LiveExecutionAdapter + KillSwitch)

    Features MANDATO 24:
    - Feature Pipeline completo (MicrostructureEngine)
    - Loop unificado para PAPER/LIVE
    - generate_signals() con features
    - Brain filtering
    - NON-NEGOTIABLES enforced
    """

    def __init__(
        self,
        config_path: str = 'config/system_config.yaml',
        execution_mode: str = 'paper',
        auto_ml: bool = True
    ):
        """
        Inicializa sistema de trading institucional.

        Args:
            config_path: Path to system configuration file
            execution_mode: 'research', 'paper', or 'live'
            auto_ml: Auto-initialize ML engine (default: True)
        """
        logger.info("=" * 80)
        logger.info("INSTITUTIONAL TRADING SYSTEM V3.0 (MANDATO 24) - INITIALIZING")
        logger.info("=" * 80)

        # Parse execution mode
        self.execution_mode = ExecutionMode.from_string(execution_mode)

        logger.critical(f"Execution Mode: {self.execution_mode.value.upper()}")
        logger.critical(f"Description: {self.execution_mode.get_description()}")
        logger.critical(f"Risk Level: {self.execution_mode.get_risk_level()}")

        # Load configuration
        self.config = self._load_configs(config_path)

        # Create output directories
        self._create_directories()

        # Initialize core components
        self._initialize_core_components(auto_ml)

        # Initialize feature pipeline (MANDATO 24)
        self._initialize_feature_pipeline()

        # Initialize execution system (mode-specific)
        self.execution_adapter = None
        self.kill_switch = None
        self._initialize_execution_system()

        # State
        self.is_running = False
        self.update_interval = self.config.get('trading', {}).get('update_interval', 60)

        logger.info("=" * 80)
        logger.info("SYSTEM INITIALIZATION COMPLETE")
        logger.info(f"Execution Mode: {self.execution_mode.value.upper()}")
        if self.execution_adapter:
            logger.info(f"Execution Adapter: {self.execution_adapter.get_mode_name()}")
        logger.info(f"ML Engine: {'ENABLED ✓' if self.ml_engine else 'DISABLED ✗'}")
        logger.info(f"Strategies Loaded: {len(self.strategy_orchestrator.strategies)}")
        logger.info(f"Feature Pipeline: MicrostructureEngine ENABLED ✓")

        if self.execution_mode == ExecutionMode.LIVE:
            logger.critical("⚠️⚠️⚠️  LIVE MODE: REAL MONEY AT RISK  ⚠️⚠️⚠️")
            logger.critical(f"Kill Switch: {self.kill_switch.get_state().value}")

        logger.info("=" * 80)

    def _load_configs(self, config_path: str) -> dict:
        """
        Carga configuraciones (system + live trading si LIVE mode).

        Args:
            config_path: Path to system config

        Returns:
            Merged config dict
        """
        # Load system config
        try:
            with open(config_path, 'r') as f:
                config = yaml.safe_load(f)
            logger.info(f"✓ System config loaded from {config_path}")
        except FileNotFoundError:
            logger.warning(f"⚠️  Config file not found: {config_path}, using defaults")
            config = self._get_default_config()

        # Merge live trading config if LIVE mode
        if self.execution_mode == ExecutionMode.LIVE:
            try:
                with open('config/live_trading_config.yaml', 'r') as f:
                    live_config = yaml.safe_load(f)

                if 'live_trading' not in config:
                    config['live_trading'] = {}

                config['live_trading'].update(live_config.get('live_trading', {}))
                logger.info("✓ Live trading config loaded")

            except FileNotFoundError:
                logger.warning("⚠️  Live trading config not found, using defaults")
                config['live_trading'] = {
                    'enabled': False,
                    'max_latency_ms': 500,
                    'max_ping_age_seconds': 30,
                    'max_corrupted_ticks': 10
                }

        return config

    def _get_default_config(self) -> dict:
        """Get default configuration if file not found."""
        return {
            'risk': {
                'max_risk_per_trade': 0.01,  # 1% max
                'max_portfolio_risk': 0.06,
                'max_correlation': 0.7,
                'max_concurrent_positions': 5
            },
            'execution': {
                'slippage_pips': 0.5,
                'max_spread_pips': 3.0,
                'commission_per_lot': 7.0
            },
            'trading': {
                'update_interval': 60  # 60 seconds
            },
            'features': {
                'ofi_lookback': 20,
                'vpin': {
                    'bucket_size': 50000,
                    'num_buckets': 50
                }
            },
            'live_trading': {
                'enabled': False
            }
        }

    def _create_directories(self):
        """Create necessary output directories."""
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

    def _initialize_core_components(self, auto_ml: bool):
        """
        Inicializa componentes core del sistema.

        Args:
            auto_ml: Si True, inicializa ML engine
        """
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

        # 5. ML Adaptive Engine
        self.ml_engine = None
        if auto_ml:
            try:
                self.ml_engine = MLAdaptiveEngine(self.config)
                logger.info("✓✓ ML Adaptive Engine ENABLED (auto-learning active)")
            except Exception as e:
                logger.warning(f"⚠️  ML Engine initialization failed: {e}")
                logger.warning("⚠️  Continuing without ML (manual mode)")

        # 6. Institutional Brain
        self.brain = InstitutionalBrain(
            config=self.config,
            risk_manager=self.risk_manager,
            position_manager=self.position_manager,
            regime_detector=self.regime_detector,
            mtf_manager=self.mtf_manager,
            ml_engine=self.ml_engine
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

        # 9. ML Supervisor
        self.ml_supervisor = MLSupervisor(
            config=self.config,
            ml_engine=self.ml_engine,
            strategy_orchestrator=self.strategy_orchestrator,
            reporting_system=self.reporting
        )
        logger.info("✓✓ ML Supervisor ENABLED (autonomous decision-making active)")

    def _initialize_feature_pipeline(self):
        """
        Inicializa feature pipeline (MANDATO 24).

        Crea MicrostructureEngine para cálculo de OFI, CVD, VPIN, L2.
        """
        logger.info("Initializing feature pipeline (MANDATO 24)...")

        self.microstructure_engine = MicrostructureEngine(self.config)

        logger.info("✓✓ MicrostructureEngine initialized (OFI, CVD, VPIN, L2)")

    def _initialize_execution_system(self):
        """
        Inicializa sistema de ejecución basado en modo.

        RESEARCH: No execution adapter (backtest only)
        PAPER: PaperExecutionAdapter
        LIVE: LiveExecutionAdapter + KillSwitch
        """
        logger.info("=" * 80)
        logger.info(f"INITIALIZING EXECUTION SYSTEM: {self.execution_mode.value.upper()}")
        logger.info("=" * 80)

        if self.execution_mode == ExecutionMode.PAPER:
            # PAPER: Simulación
            logger.warning("⚠️  PAPER MODE: All execution is SIMULATED")

            self.execution_adapter = PaperExecutionAdapter(config=self.config)

            if not self.execution_adapter.initialize():
                raise RuntimeError("PaperExecutionAdapter initialization failed")

            logger.info("✓ PaperExecutionAdapter initialized")

        elif self.execution_mode == ExecutionMode.LIVE:
            # LIVE: Ejecución REAL + KillSwitch
            logger.critical("🚨🚨🚨  LIVE MODE: INITIALIZING REAL EXECUTION  🚨🚨🚨")

            # Initialize KillSwitch
            self.kill_switch = KillSwitch(
                config=self.config,
                circuit_breaker_manager=None
            )

            logger.info("✓ Kill Switch initialized")

            # Check if live trading enabled in config
            if not self.config.get('live_trading', {}).get('enabled', False):
                logger.critical("⚠️⚠️⚠️  LIVE TRADING DISABLED IN CONFIG  ⚠️⚠️⚠️")
                logger.critical("To enable: Set 'live_trading.enabled: true' in config/live_trading_config.yaml")
                raise RuntimeError("Live trading is DISABLED in config")

            # Initialize LiveExecutionAdapter
            self.execution_adapter = LiveExecutionAdapter(
                config=self.config,
                kill_switch=self.kill_switch
            )

            if not self.execution_adapter.initialize():
                raise RuntimeError("LiveExecutionAdapter initialization failed")

            logger.critical("✅ LiveExecutionAdapter initialized")
            logger.critical(f"Kill Switch State: {self.kill_switch.get_state().value}")

        else:
            # RESEARCH: No execution
            logger.info("RESEARCH MODE: No execution adapter (backtest only)")

        logger.info("=" * 80)

    def run_unified_loop(self):
        """
        Loop unificado para PAPER y LIVE modes (MANDATO 24).

        Flow:
        1. MTF Update
        2. Feature Calculation (OFI, CVD, VPIN, L2) ← MANDATO 24
        3. Regime Detection
        4. Signal Generation (via StrategyOrchestrator) ← MANDATO 24
        5. Brain Filtering
        6. Execution (mode-aware)
        7. Reporting
        8. ML Supervisor hooks
        """
        logger.info("=" * 80)
        logger.info(f"STARTING UNIFIED TRADING LOOP ({self.execution_mode.value.upper()})")
        logger.info("=" * 80)

        self.is_running = True
        iteration = 0

        try:
            while self.is_running:
                iteration += 1
                logger.debug(f"Loop iteration {iteration}")

                # === STEP 1: MTF UPDATE ===
                self.mtf_manager.update()
                current_data = self.mtf_manager.get_current_data()

                if not current_data:
                    logger.warning("No market data available, skipping iteration")
                    time.sleep(self.update_interval)
                    continue

                # === STEP 2: FEATURE CALCULATION (MANDATO 24) ===
                features_by_symbol = self._calculate_all_features(current_data)

                # === STEP 3: REGIME DETECTION ===
                current_regime = self.regime_detector.detect_regime(current_data)
                logger.debug(f"Current regime: {current_regime}")

                # === STEP 4: SIGNAL GENERATION (MANDATO 24) ===
                # CRITICAL: Pasa features a estrategias
                raw_signals = self.strategy_orchestrator.generate_signals(
                    market_data=current_data,
                    current_regime=current_regime,
                    features=features_by_symbol
                )

                logger.info(f"Generated {len(raw_signals)} raw signals")

                if not raw_signals:
                    logger.debug("No signals generated this iteration")
                    time.sleep(self.update_interval)
                    continue

                # === STEP 5: BRAIN FILTERING ===
                filtered_signals = self.brain.filter_signals(
                    signals=raw_signals,
                    market_data=current_data,
                    current_regime=current_regime
                )

                logger.info(f"Brain filtered to {len(filtered_signals)} signals")

                if not filtered_signals:
                    logger.debug("All signals rejected by Brain")
                    time.sleep(self.update_interval)
                    continue

                # === STEP 6: EXECUTION (MODE-AWARE) ===
                if self.execution_mode == ExecutionMode.LIVE:
                    # LIVE: Check Kill Switch ANTES de ejecutar
                    if not self.kill_switch.can_send_orders():
                        status = self.kill_switch.get_status()

                        logger.critical("=" * 80)
                        logger.critical("⚠️  KILL SWITCH BLOCKING ORDERS")
                        logger.critical(f"State: {status.state.value}")
                        logger.critical(f"Reason: {status.reason}")
                        logger.critical(f"Failed Layers: {status.failed_layers}")
                        logger.critical("=" * 80)

                        # NO ejecutar, pero continuar loop
                        time.sleep(self.update_interval)
                        continue

                # Ejecutar señales (PAPER o LIVE via ExecutionAdapter)
                executed_trades = self._execute_signals(filtered_signals)

                logger.info(f"Executed {len(executed_trades)} trades")

                # === STEP 7: REPORTING ===
                if executed_trades:
                    self._update_reports(executed_trades, current_data)

                # === STEP 8: ML SUPERVISOR HOOKS ===
                self.ml_supervisor.on_iteration_complete(
                    signals=filtered_signals,
                    executed_trades=executed_trades,
                    market_data=current_data
                )

                # Sleep hasta próximo update
                time.sleep(self.update_interval)

        except KeyboardInterrupt:
            logger.info("\n⚠️  Shutdown requested by user")
            self.shutdown()

        except Exception as e:
            logger.error(f"FATAL ERROR in trading loop: {e}")
            import traceback
            traceback.print_exc()

            # En LIVE, errores críticos activan kill switch
            if self.execution_mode == ExecutionMode.LIVE and self.kill_switch:
                logger.critical("⚠️  Activating kill switch due to loop error")
                self.kill_switch.emergency_stop(f"Loop error: {e}")

            self.shutdown()

    def _calculate_all_features(self, current_data: dict) -> dict:
        """
        Calcula features para TODOS los símbolos (MANDATO 24).

        Args:
            current_data: Dict[symbol, DataFrame]

        Returns:
            Dict[symbol, Dict[feature_name, value]]
        """
        features_by_symbol = {}

        for symbol, df in current_data.items():
            # Get L2 data if LIVE mode (optional)
            l2_data = None
            if self.execution_mode == ExecutionMode.LIVE:
                try:
                    import MetaTrader5 as mt5
                    l2_data = mt5.market_book_get(symbol)
                except:
                    pass  # L2 no disponible

            # Calculate features via MicrostructureEngine
            features = self.microstructure_engine.calculate_features(
                symbol=symbol,
                market_data=df,
                l2_data=l2_data
            )

            # Convert to dict
            features_by_symbol[symbol] = self.microstructure_engine.get_features_dict(features)

        return features_by_symbol

    def _execute_signals(self, signals: list) -> list:
        """
        Ejecuta señales via ExecutionAdapter.

        Args:
            signals: Lista de señales filtradas por Brain

        Returns:
            Lista de trades ejecutados
        """
        executed_trades = []

        for signal in signals:
            try:
                # Ejecutar via adapter (PAPER o LIVE)
                trade = self.execution_adapter.execute_signal(signal)

                if trade:
                    executed_trades.append(trade)
                    logger.info(
                        f"✓ Executed: {signal.symbol} {signal.direction} "
                        f"@ {signal.entry_price:.5f}"
                    )

            except Exception as e:
                logger.error(f"Execution error for {signal.symbol}: {e}")
                continue

        return executed_trades

    def _update_reports(self, executed_trades: list, market_data: dict):
        """Update reporting system with executed trades."""
        try:
            self.reporting.log_trades(executed_trades)
        except Exception as e:
            logger.warning(f"Reporting update error: {e}")

    def run_backtest(self, start_date: str, end_date: str, capital: float):
        """
        Run backtest (RESEARCH mode).

        Args:
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)
            capital: Initial capital

        Returns:
            Backtest results
        """
        if self.execution_mode != ExecutionMode.RESEARCH:
            raise ValueError("Backtest requires RESEARCH mode")

        logger.info("=" * 80)
        logger.info("STARTING BACKTEST (RESEARCH MODE)")
        logger.info(f"Period: {start_date} to {end_date}")
        logger.info(f"Capital: ${capital:,.2f}")
        logger.info("=" * 80)

        # Use existing BacktestEngine (already has feature calculation)
        backtest_engine = BacktestEngine(
            config=self.config,
            strategies=list(self.strategy_orchestrator.strategies.values()),
            initial_capital=capital
        )

        # TODO: Load historical data
        # historical_data = self._load_historical_data(start_date, end_date)

        # Run backtest
        # results = backtest_engine.run_backtest(
        #     historical_data,
        #     start_date,
        #     end_date,
        #     regime_detector=self.regime_detector
        # )

        logger.warning("⚠️  Backtest implementation pending (use existing backtest scripts)")

        return None

    def run_paper_trading(self):
        """Run PAPER mode (simulated execution)."""
        if self.execution_mode != ExecutionMode.PAPER:
            raise ValueError("Paper trading requires PAPER mode")

        logger.warning("⚠️  PAPER MODE: All execution is SIMULATED")

        # Run unified loop
        self.run_unified_loop()

    def run_live_trading(self):
        """Run LIVE mode (REAL execution with triple confirmation)."""
        if self.execution_mode != ExecutionMode.LIVE:
            raise ValueError("Live trading requires LIVE mode")

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

        # Run unified loop
        self.run_unified_loop()

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
        description='Institutional Trading System V3.0 (MANDATO 24)'
    )

    parser.add_argument(
        '--mode',
        type=str,
        choices=['research', 'paper', 'live'],
        default='paper',
        help='Trading mode: research (backtest), paper (demo), or live (real)'
    )

    parser.add_argument(
        '--capital',
        type=float,
        default=10000.0,
        help='Starting capital (default: 10000)'
    )

    parser.add_argument(
        '--days',
        type=int,
        default=90,
        help='Number of days for backtesting (default: 90)'
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
        help='Path to system configuration file'
    )

    args = parser.parse_args()

    # Initialize system
    try:
        system = InstitutionalTradingSystem(
            config_path=args.config,
            execution_mode=args.mode,
            auto_ml=not args.no_ml
        )

        # Run in selected mode
        if args.mode == 'paper':
            system.run_paper_trading()
        elif args.mode == 'live':
            system.run_live_trading()
        elif args.mode == 'research':
            # Calculate start/end dates
            from datetime import datetime, timedelta
            end_date = datetime.now()
            start_date = end_date - timedelta(days=args.days)

            system.run_backtest(
                start_date.strftime('%Y-%m-%d'),
                end_date.strftime('%Y-%m-%d'),
                capital=args.capital
            )

    except Exception as e:
        logger.critical(f"FATAL ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
