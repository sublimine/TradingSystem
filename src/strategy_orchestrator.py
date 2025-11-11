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
from src.strategies.volatility_regime_adaptation import VolatilityRegimeAdaptation
from src.strategies.momentum_quality import MomentumQuality
from src.strategies.mean_reversion_statistical import MeanReversionStatistical
from src.strategies.idp_inducement_distribution import IDPInducementDistribution
from src.strategies.iceberg_detection import IcebergDetection
from src.strategies.breakout_volume_confirmation import BreakoutVolumeConfirmation
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

from src.execution.adaptive_participation_rate import APRExecutor

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

    def __init__(self, config_path: str = 'config/strategy_config_master.yaml'):
        """Initialize the orchestrator with configuration."""
        self.config = self._load_config(config_path)
        self.strategies = {}
        self.active_positions = {}
        self.performance_tracker = {}
        self.apr_executor = None

        self._initialize_strategies()
        self._initialize_apr()

        logger.info(f"Strategy Orchestrator initialized with {len(self.strategies)} strategies")

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

    def _initialize_strategies(self):
        """Initialize all enabled strategies from configuration."""
        strategy_classes = {
            # Core institutional strategies
            'ofi_refinement': OFIRefinement,
            'fvg_institutional': FVGInstitutional,
            'order_block_institutional': OrderBlockInstitutional,
            'htf_ltf_liquidity': HTFLTFLiquidity,
            'volatility_regime_adaptation': VolatilityRegimeAdaptation,
            'momentum_quality': MomentumQuality,
            'mean_reversion_statistical': MeanReversionStatistical,
            'idp_inducement_distribution': IDPInducementDistribution,
            'iceberg_detection': IcebergDetection,
            'breakout_volume_confirmation': BreakoutVolumeConfirmation,
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
        }

        for strategy_name, strategy_class in strategy_classes.items():
            strategy_config = self.config['strategies'].get(strategy_name, {})

            if strategy_config.get('enabled', False):
                try:
                    self.strategies[strategy_name] = strategy_class(strategy_config)
                    self.performance_tracker[strategy_name] = {
                        'signals_generated': 0,
                        'trades_executed': 0,
                        'winning_trades': 0,
                        'losing_trades': 0,
                        'total_pnl': 0.0
                    }
                    logger.info(f"Strategy '{strategy_name}' initialized successfully")
                except Exception as e:
                    logger.error(f"Failed to initialize strategy '{strategy_name}': {str(e)}")

    def _initialize_apr(self):
        """Initialize Adaptive Participation Rate executor."""
        # TODO: Implementation
        pass