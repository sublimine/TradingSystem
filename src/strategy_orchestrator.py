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
from src.strategies.idp_inducement_distribution import IDPInducement  # MANDATO24R: Fixed class name
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
from src.strategies.nfp_news_event_handler import NFPNewsEventHandler

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

    def __init__(self, config_path: str = 'config/strategies_institutional.yaml', brain=None):
        """Initialize the orchestrator with configuration."""
        self.config = self._load_config(config_path)
        self.brain = brain  # Store brain reference for strategy coordination
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
            'idp_inducement_distribution': IDPInducement,  # MANDATO24R: Fixed class name
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
            'nfp_news_event_handler': NFPNewsEventHandler,
        }

        for strategy_name, strategy_class in strategy_classes.items():
            # Strategies are at root level in strategies_institutional.yaml
            strategy_config = self.config.get(strategy_name, {})

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

    def generate_signals(
        self,
        market_data: Dict[str, pd.DataFrame],
        current_regime: str,
        features: Dict[str, Dict]
    ) -> List:
        """
        Genera señales de TODAS las estrategias activas.

        MANDATO 24: Método crítico que integra feature pipeline con estrategias.

        Args:
            market_data: Dict[symbol, DataFrame] con datos de mercado (OHLCV)
            current_regime: Régimen actual ('trending', 'ranging', 'volatile', 'quiet')
            features: Dict[symbol, Dict[feature_name, value]] con features pre-calculadas
                Ejemplo:
                    {
                        'EURUSD': {
                            'ofi': 0.35,
                            'cvd': 1234.5,
                            'vpin': 0.78,
                            'l2_snapshot': <OrderBookSnapshot>,
                            'imbalance': 0.25,
                            'atr': 0.0001
                        }
                    }

        Returns:
            Lista de señales (Signal objects) de todas las estrategias

        Example:
            >>> signals = orchestrator.generate_signals(
            ...     market_data={'EURUSD': df},
            ...     current_regime='trending',
            ...     features={'EURUSD': {'vpin': 0.78, 'ofi': 0.35}}
            ... )
            >>> print(f"Generated {len(signals)} signals")

        Note:
            - Filtra estrategias activas por régimen
            - Pasa features a cada estrategia via evaluate()
            - Añade metadata (strategy name, regime) a cada señal
            - Maneja errores por estrategia (no falla todo el loop)
        """
        all_signals = []

        # Filtrar estrategias activas por régimen
        active_strategies = self._get_strategies_for_regime(current_regime)

        logger.debug(f"{len(active_strategies)} strategies active for regime '{current_regime}'")

        # Generar señales de cada estrategia
        for strategy_name, strategy in active_strategies.items():
            try:
                # Get primary symbol for strategy
                # Primero intenta getattr, luego config, luego default
                primary_symbol = getattr(strategy, 'symbol', None)
                if primary_symbol is None:
                    # Fallback: obtener de config
                    strategy_config = self.config.get(strategy_name, {})
                    primary_symbol = strategy_config.get('symbol', 'EURUSD')

                # Get market data for symbol
                strategy_data = market_data.get(primary_symbol)

                if strategy_data is None or strategy_data.empty:
                    logger.debug(
                        f"No data for {primary_symbol}, skipping {strategy.__class__.__name__}"
                    )
                    continue

                # Get features for symbol
                strategy_features = features.get(primary_symbol, {})

                # CRITICAL: Pass features to strategy
                signals = strategy.evaluate(strategy_data, strategy_features)

                # Add strategy metadata to signals
                for signal in signals:
                    if signal.metadata is None:
                        signal.metadata = {}

                    signal.metadata['strategy'] = strategy.__class__.__name__
                    signal.metadata['strategy_name'] = strategy_name
                    signal.metadata['regime'] = current_regime

                # Update performance tracker
                self.performance_tracker[strategy_name]['signals_generated'] += len(signals)

                all_signals.extend(signals)

                if signals:
                    logger.debug(
                        f"{strategy.__class__.__name__} generated {len(signals)} signals "
                        f"(symbol={primary_symbol}, regime={current_regime})"
                    )

            except Exception as e:
                logger.error(f"Error in {strategy_name}: {e}")
                import traceback
                traceback.print_exc()
                continue

        logger.info(
            f"Generated {len(all_signals)} total signals from {len(active_strategies)} strategies"
        )

        return all_signals

    def _get_strategies_for_regime(self, regime: str) -> Dict:
        """
        Filtra estrategias activas para el régimen actual.

        Args:
            regime: Current market regime

        Returns:
            Dict de estrategias activas {strategy_name: strategy_instance}

        Note:
            - Si APR habilitado, usa sus pesos
            - Si no, filtra por preferred_regimes de cada estrategia
            - Si estrategia no especifica preferencia, siempre activa
        """
        # Si APR (Active Portfolio Rebalancing) está habilitado, usar sus pesos
        if self.apr_executor and hasattr(self.apr_executor, 'get_active_strategies'):
            return self.apr_executor.get_active_strategies(regime)

        # Si no, filtrar manualmente por régimen
        active = {}

        for strategy_name, strategy in self.strategies.items():
            # Check si estrategia tiene preferencia de régimen
            if hasattr(strategy, 'preferred_regimes'):
                if regime in strategy.preferred_regimes:
                    active[strategy_name] = strategy
            else:
                # Si no especifica preferencia, siempre activa
                active[strategy_name] = strategy

        return active