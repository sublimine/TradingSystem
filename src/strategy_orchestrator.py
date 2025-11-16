"""
Strategy Orchestrator - Multi-Strategy Coordination System

This module manages the lifecycle of multiple trading strategies, including:
- Strategy initialization and configuration
- Signal aggregation from multiple sources
- Position sizing across strategies
- Risk management at portfolio level
- Performance tracking and attribution
"""

import yaml
import logging
from typing import Dict, List, Optional
from datetime import datetime
import pandas as pd

from src.strategies.ofi_refinement import OFIRefinement
from src.strategies.fvg_institutional import FVGInstitutional
from src.strategies.order_block_institutional import OrderBlockInstitutional
from src.strategies.htf_ltf_liquidity import HTFLTFLiquidity
from src.strategies.volatility_institutional import VolatilityInstitutional
from src.strategies.momentum_institutional import MomentumInstitutional
from src.strategies.mean_reversion_institutional import MeanReversionInstitutional
from src.strategies.idp_inducement_distribution import IDPInducementDistribution
from src.strategies.iceberg_detection import IcebergDetection
from src.strategies.breakout_institutional import BreakoutInstitutional
from src.strategies.correlation_divergence import CorrelationDivergence
from src.strategies.kalman_pairs_trading import KalmanPairsTrading
from src.strategies.liquidity_sweep import LiquiditySweepStrategy
from src.strategies.order_flow_toxicity import OrderFlowToxicityStrategy

# ELITE 2024-2025 strategies
from src.strategies.vpin_reversal_extreme import VPINReversalExtreme
from src.strategies.fractal_market_structure import FractalMarketStructure
from src.strategies.correlation_cascade_detection import CorrelationCascadeDetection
from src.strategies.footprint_orderflow_clusters import FootprintOrderflowClusters

# ELITE 2025 strategies (crisis/arbitrage/TDA)
from src.strategies.crisis_mode_volatility_spike import CrisisModeVolatilitySpike
from src.strategies.statistical_arbitrage_johansen import StatisticalArbitrageJohansen
from src.strategies.calendar_arbitrage_flows import CalendarArbitrageFlows
from src.strategies.topological_data_analysis_regime import TopologicalDataAnalysisRegime
from src.strategies.spoofing_detection_l2 import SpoofingDetectionL2
from src.strategies.nfp_news_event_handler import NFPNewsEventHandler

from src.execution.adaptive_participation_rate import APRExecutor
from src.core.microstructure_engine import MicrostructureEngine
from src.strategies.strategy_base import Signal
from src.execution.execution_manager import ExecutionManager
from src.execution.execution_mode import ExecutionConfig

logger = logging.getLogger(__name__)

class StrategyOrchestrator:
    """
    Orchestrates multiple trading strategies in a coordinated system.

    The orchestrator is responsible for:
    1. Loading strategy configurations from YAML
    2. Initializing all enabled strategies
    3. Coordinating signal generation across strategies
    4. Managing position sizing based on strategy allocations
    5. Enforcing correlation limits between strategies
    6. Tracking performance attribution by strategy
    """

    def __init__(self, config_path: str = 'config/strategies_institutional.yaml',
                 brain=None,
                 execution_config: Optional[ExecutionConfig] = None,
                 profile: Optional[str] = None):
        """
        Initialize the orchestrator with configuration.

        Args:
            config_path: Path to strategy configuration YAML
            brain: Brain reference for coordination (optional)
            execution_config: ExecutionConfig for automatic execution (optional)
                If None, orchestrator only generates signals without executing
            profile: Runtime profile name (optional)
                Options: 'green_only', 'full_24', or None for all enabled strategies
                PLAN OMEGA FASE 3.4: Runtime profile support
        """
        self.config = self._load_config(config_path)
        self.brain = brain  # Store brain reference for strategy coordination
        self.strategies = {}
        self.active_positions = {}
        self.performance_tracker = {}
        self.apr_executor = None

        # Load and apply runtime profile (PLAN OMEGA FASE 3.4)
        self.profile_config = None
        self.profile_name = None
        if profile:
            self.profile_config = self._load_profile(profile)
            self.profile_name = profile
            logger.info(f"Runtime profile '{profile}' loaded: "
                       f"{len(self.profile_config.get('enabled_strategies', []))} strategies enabled")

        # Initialize MicrostructureEngine for centralized feature calculation
        # PLAN OMEGA FASE 3.1b: Integration
        self.microstructure_engine = MicrostructureEngine()
        logger.info("MicrostructureEngine initialized for live trading")

        # Initialize ExecutionManager for order execution
        # PLAN OMEGA FASE 3.2: ExecutionMode + Adapters
        self.execution_manager: Optional[ExecutionManager] = None
        if execution_config:
            self.execution_manager = ExecutionManager(execution_config)
            logger.info(f"ExecutionManager initialized in {execution_config.mode} mode")
        else:
            logger.info("ExecutionManager not initialized - signal generation only")

        self._initialize_strategies()
        self._initialize_apr()

        logger.info(f"Strategy Orchestrator initialized with {len(self.strategies)} strategies" +
                   (f" (profile: {profile})" if profile else ""))

    def _load_config(self, config_path: str) -> Dict:
        """Load configuration from YAML file."""
        try:
            with open(config_path, 'r') as f:
                config = yaml.safe_load(f)
            logger.info(f"Configuration loaded from {config_path}")
            return config
        except Exception as e:
            logger.error(f"Failed to load configuration: {str(e)}")
            raise

    def _load_profile(self, profile_name: str) -> Dict:
        """
        Load runtime profile configuration.

        PLAN OMEGA FASE 3.4: Runtime profile support

        Args:
            profile_name: Profile name ('green_only', 'full_24')

        Returns:
            Profile configuration dict

        Raises:
            FileNotFoundError: If profile not found
            ValueError: If profile invalid
        """
        # Build profile path
        profile_path = f'config/profiles/{profile_name}.yaml'

        try:
            with open(profile_path, 'r') as f:
                profile_config = yaml.safe_load(f)

            # Validate profile structure
            if 'enabled_strategies' not in profile_config:
                raise ValueError(f"Profile '{profile_name}' missing 'enabled_strategies' key")

            logger.info(f"✅ Profile loaded: {profile_config.get('profile_name', profile_name)} "
                       f"({profile_config.get('profile_type', 'unknown')} mode)")

            return profile_config

        except FileNotFoundError:
            logger.error(f"Profile '{profile_name}' not found at {profile_path}")
            logger.info("Available profiles: green_only, full_24")
            raise
        except Exception as e:
            logger.error(f"Failed to load profile '{profile_name}': {e}")
            raise

    def _initialize_strategies(self):
        """Initialize all enabled strategies from configuration."""
        strategy_classes = {
            # Core institutional strategies
            'ofi_refinement': OFIRefinement,
            'fvg_institutional': FVGInstitutional,
            'order_block_institutional': OrderBlockInstitutional,
            'htf_ltf_liquidity': HTFLTFLiquidity,
            'volatility_regime_adaptation': VolatilityInstitutional,
            'momentum_quality': MomentumInstitutional,
            'mean_reversion_statistical': MeanReversionInstitutional,
            'idp_inducement_distribution': IDPInducementDistribution,
            'iceberg_detection': IcebergDetection,
            'breakout_volume_confirmation': BreakoutInstitutional,
            'correlation_divergence': CorrelationDivergence,
            'kalman_pairs_trading': KalmanPairsTrading,
            'liquidity_sweep': LiquiditySweepStrategy,
            'order_flow_toxicity': OrderFlowToxicityStrategy,
            # ELITE 2024-2025 strategies (70%+ win rates)
            'vpin_reversal_extreme': VPINReversalExtreme,
            'fractal_market_structure': FractalMarketStructure,
            'correlation_cascade_detection': CorrelationCascadeDetection,
            'footprint_orderflow_clusters': FootprintOrderflowClusters,
            # ELITE 2025 strategies (crisis/arbitrage/TDA)
            'crisis_mode_volatility_spike': CrisisModeVolatilitySpike,
            'statistical_arbitrage_johansen': StatisticalArbitrageJohansen,
            'calendar_arbitrage_flows': CalendarArbitrageFlows,
            'topological_data_analysis_regime': TopologicalDataAnalysisRegime,
            'spoofing_detection_l2': SpoofingDetectionL2,
            'nfp_news_event_handler': NFPNewsEventHandler,
        }

        for strategy_name, strategy_class in strategy_classes.items():
            # Strategies are at root level in strategies_institutional.yaml
            strategy_config = self.config.get(strategy_name, {})

            # Check if strategy should be loaded
            should_load = False

            if self.profile_config:
                # PROFILE MODE: Only load strategies in profile's enabled_strategies list
                # PLAN OMEGA FASE 3.4: Profile filtering
                enabled_in_profile = strategy_name in self.profile_config.get('enabled_strategies', [])
                if enabled_in_profile:
                    should_load = True
                    logger.debug(f"Strategy '{strategy_name}' enabled by profile '{self.profile_name}'")
            else:
                # NORMAL MODE: Load all strategies with enabled=True
                should_load = strategy_config.get('enabled', False)

            if should_load:
                try:
                    self.strategies[strategy_name] = strategy_class(strategy_config)
                    self.performance_tracker[strategy_name] = {
                        'signals_generated': 0,
                        'trades_executed': 0,
                        'winning_trades': 0,
                        'losing_trades': 0,
                        'total_pnl': 0.0
                    }
                    logger.info(f"✅ Strategy '{strategy_name}' initialized successfully")
                except Exception as e:
                    logger.error(f"❌ Failed to initialize strategy '{strategy_name}': {str(e)}")

    def _initialize_apr(self):
        """Initialize Adaptive Participation Rate executor."""
        # TODO: Implementation
        pass

    def evaluate_strategies(self, market_data: pd.DataFrame) -> List[Signal]:
        """
        Evaluate all enabled strategies on current market data.

        PLAN OMEGA FASE 3.1b: MicrostructureEngine Integration
        Calculates institutional features once, then passes to all strategies.

        Args:
            market_data: DataFrame with OHLCV data
                Required columns: 'timestamp', 'open', 'high', 'low', 'close', 'volume'

        Returns:
            List of Signal objects from all strategies
        """
        if len(market_data) < 20:
            logger.debug("Insufficient market data for strategy evaluation")
            return []

        # STEP 1: Calculate features ONCE using MicrostructureEngine
        try:
            features = self.microstructure_engine.calculate_features(
                market_data,
                use_cache=True  # Cache for live trading (same bar = same features)
            )
            logger.debug(f"Features calculated: OFI={features.get('ofi', 0):.3f}, "
                        f"VPIN={features.get('vpin', 0):.3f}, CVD={features.get('cvd', 0):.3f}")
        except Exception as e:
            logger.error(f"Feature calculation failed: {e}")
            return []

        # STEP 2: Evaluate each enabled strategy
        all_signals = []

        for strategy_name, strategy in self.strategies.items():
            try:
                # Each strategy gets the same features dict
                signals = strategy.evaluate(market_data, features)

                if signals:
                    # Ensure signals is a list
                    if not isinstance(signals, list):
                        signals = [signals]

                    # Track signals generated
                    self.performance_tracker[strategy_name]['signals_generated'] += len(signals)

                    all_signals.extend(signals)
                    logger.info(f"Strategy '{strategy_name}' generated {len(signals)} signal(s)")

            except Exception as e:
                logger.error(f"Strategy '{strategy_name}' evaluation failed: {e}", exc_info=True)

        logger.info(f"Total signals generated: {len(all_signals)} from {len(self.strategies)} strategies")

        return all_signals

    def evaluate_and_execute(self, market_data: pd.DataFrame) -> Dict:
        """
        Evaluar estrategias Y ejecutar señales automáticamente.

        PLAN OMEGA FASE 3.2: ExecutionMode Integration
        Workflow completo: Features → Señales → Ejecución

        Args:
            market_data: DataFrame con datos OHLCV
                Required columns: 'timestamp', 'open', 'high', 'low', 'close', 'volume'

        Returns:
            Dictionary con resultados:
                - 'signals': Lista de señales generadas
                - 'executed': Número de señales ejecutadas
                - 'positions': Posiciones abiertas actuales
                - 'balance': Balance de la cuenta
                - 'equity': Equity de la cuenta
        """
        # PASO 1: Evaluar estrategias y generar señales
        signals = self.evaluate_strategies(market_data)

        result = {
            'signals': signals,
            'executed': 0,
            'positions': [],
            'balance': 0.0,
            'equity': 0.0
        }

        # PASO 2: Ejecutar señales si hay ExecutionManager
        if self.execution_manager and signals:
            # Obtener precio actual del mercado
            current_price = market_data['close'].iloc[-1]
            symbol = market_data.attrs.get('symbol', 'EURUSD')

            market_prices = {symbol: current_price}

            # Actualizar posiciones con datos actuales
            market_bar = {
                symbol: {
                    'bid': current_price,
                    'ask': current_price,
                    'high': market_data['high'].iloc[-1],
                    'low': market_data['low'].iloc[-1],
                    'close': current_price
                }
            }
            self.execution_manager.update_positions(market_bar)

            # Ejecutar señales
            executed = self.execution_manager.execute_signals(signals, market_prices)
            result['executed'] = executed

            logger.info(f"Executed {executed}/{len(signals)} signals")

        # PASO 3: Obtener estado actual
        if self.execution_manager:
            result['positions'] = self.execution_manager.get_positions()
            result['balance'] = self.execution_manager.get_account_balance()
            result['equity'] = self.execution_manager.get_account_equity()

        return result

    def get_execution_statistics(self) -> Optional[Dict]:
        """
        Obtener estadísticas de ejecución.

        Returns:
            Dict con estadísticas o None si no hay ExecutionManager
        """
        if self.execution_manager:
            return self.execution_manager.get_statistics()
        return None