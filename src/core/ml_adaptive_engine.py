"""
Machine Learning Adaptive Engine - Continuous Learning System

This is the TRUE institutional edge: A system that LEARNS from every trade,
every signal, every market condition and IMPROVES all components dynamically.

NOT static parameters - ADAPTIVE parameters based on real market feedback.

Components:
1. Trade Memory Database - Stores EVERYTHING
2. Performance Attribution - Analyzes WHAT works and WHY
3. Parameter Optimizer - Adjusts strategy parameters dynamically
4. Feature Importance Tracker - Identifies most predictive features
5. Strategy Performance Predictor - Predicts which strategies will work
6. Market Regime Learner - Refines regime classification
7. Risk Parameter Adapter - Optimizes risk limits dynamically

Research basis:
- Reinforcement Learning (Sutton & Barto 2018)
- Online Learning (Cesa-Bianchi & Lugosi 2006)
- Adaptive Filtering (Haykin 2002)
- Portfolio Optimization (Markowitz 1952, Kelly 1956)
- Feature Selection (Guyon & Elisseeff 2003)
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime, timedelta
from collections import defaultdict, deque
import logging
import json
import pickle
from pathlib import Path
from dataclasses import dataclass, asdict
from scipy import stats
from sklearn.preprocessing import StandardScaler
from sklearn.ensemble import RandomForestClassifier, GradientBoostingRegressor
from sklearn.linear_model import Ridge
import warnings
warnings.filterwarnings('ignore')

logger = logging.getLogger(__name__)


@dataclass
class TradeRecord:
    """Complete record of a trade for learning."""
    trade_id: str
    timestamp: datetime
    symbol: str
    strategy: str
    direction: str

    # Entry conditions
    entry_price: float
    entry_time: datetime
    entry_regime: str
    entry_features: Dict[str, float]

    # Signal quality at entry
    quality_score: float
    mtf_confluence: float
    structure_alignment: float
    order_flow_quality: float
    regime_fit: float

    # Position details
    lot_size: float
    risk_pct: float
    stop_loss: float
    take_profit: float

    # Exit details
    exit_price: float
    exit_time: datetime
    exit_reason: str  # 'STOP', 'TARGET', 'TRAIL', 'PARTIAL', 'MANUAL'

    # Performance metrics
    pnl_pct: float
    pnl_r: float  # R-multiples
    mae_r: float  # Max Adverse Excursion
    mfe_r: float  # Max Favorable Excursion
    duration_minutes: int

    # Market conditions during trade
    avg_vpin_during: float
    avg_volatility_during: float
    regime_changes_during: int

    def to_dict(self) -> Dict:
        """Convert to dictionary for storage."""
        d = asdict(self)
        # Convert datetime to string
        d['timestamp'] = self.timestamp.isoformat()
        d['entry_time'] = self.entry_time.isoformat()
        d['exit_time'] = self.exit_time.isoformat()
        return d

    @classmethod
    def from_dict(cls, d: Dict):
        """Create from dictionary."""
        d['timestamp'] = datetime.fromisoformat(d['timestamp'])
        d['entry_time'] = datetime.fromisoformat(d['entry_time'])
        d['exit_time'] = datetime.fromisoformat(d['exit_time'])
        return cls(**d)


@dataclass
class SignalRecord:
    """Record of a signal (approved or rejected) for learning."""
    signal_id: str
    timestamp: datetime
    symbol: str
    strategy: str
    direction: str

    # Signal details
    quality_score: float
    entry_price: float
    stop_loss: float
    take_profit: float

    # Market context
    regime: str
    features: Dict[str, float]

    # Brain decision
    approved: bool
    rejection_reason: Optional[str]

    # If approved, eventual outcome
    trade_id: Optional[str]
    eventual_outcome_r: Optional[float]

    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        d = asdict(self)
        d['timestamp'] = self.timestamp.isoformat()
        return d

    @classmethod
    def from_dict(cls, d: Dict):
        """Create from dictionary."""
        d['timestamp'] = datetime.fromisoformat(d['timestamp'])
        return cls(**d)


class TradeMemoryDatabase:
    """
    Persistent database of ALL trades and signals.

    This is the MEMORY of the system - everything is recorded and can be
    analyzed to improve future decisions.
    """

    def __init__(self, storage_path: Path):
        """
        Initialize trade memory database.

        Args:
            storage_path: Path to store database
        """
        self.storage_path = storage_path
        self.storage_path.mkdir(parents=True, exist_ok=True)

        # In-memory caches - FIX: Limit size to prevent memory leaks
        self.trades: deque = deque(maxlen=5000)  # Keep last 5000 trades
        self.signals: deque = deque(maxlen=10000)  # Keep last 10000 signals

        # Performance indexes
        self.trades_by_strategy: Dict[str, List[TradeRecord]] = defaultdict(list)
        self.trades_by_symbol: Dict[str, List[TradeRecord]] = defaultdict(list)
        self.trades_by_regime: Dict[str, List[TradeRecord]] = defaultdict(list)

        # Load existing data
        self._load_from_disk()

        logger.info(f"Trade Memory Database initialized: {len(self.trades)} trades, {len(self.signals)} signals")

    def record_trade(self, trade: TradeRecord):
        """Record completed trade."""
        self.trades.append(trade)
        self.trades_by_strategy[trade.strategy].append(trade)
        self.trades_by_symbol[trade.symbol].append(trade)
        self.trades_by_regime[trade.entry_regime].append(trade)

        # Save to disk (append mode)
        self._save_trade_to_disk(trade)

        logger.info(f"Trade recorded: {trade.trade_id} {trade.strategy} {trade.pnl_r:.2f}R")

    def record_signal(self, signal: SignalRecord):
        """Record signal (approved or rejected)."""
        self.signals.append(signal)

        # Save to disk
        self._save_signal_to_disk(signal)

        logger.debug(f"Signal recorded: {signal.signal_id} {signal.strategy} approved={signal.approved}")

    def link_signal_to_trade(self, signal_id: str, trade_id: str, outcome_r: float):
        """Link signal to eventual trade outcome."""
        for signal in self.signals:
            if signal.signal_id == signal_id:
                signal.trade_id = trade_id
                signal.eventual_outcome_r = outcome_r
                break

    def get_strategy_trades(self, strategy: str, lookback_days: int = 30) -> List[TradeRecord]:
        """Get recent trades for strategy."""
        cutoff = datetime.now() - timedelta(days=lookback_days)
        return [t for t in self.trades_by_strategy[strategy] if t.timestamp >= cutoff]

    def get_regime_trades(self, regime: str, lookback_days: int = 90) -> List[TradeRecord]:
        """Get trades that occurred in specific regime."""
        cutoff = datetime.now() - timedelta(days=lookback_days)
        return [t for t in self.trades_by_regime[regime] if t.timestamp >= cutoff]

    def get_winning_trades(self, strategy: Optional[str] = None) -> List[TradeRecord]:
        """Get all winning trades."""
        trades = self.trades_by_strategy[strategy] if strategy else self.trades
        return [t for t in trades if t.pnl_r > 0]

    def get_losing_trades(self, strategy: Optional[str] = None) -> List[TradeRecord]:
        """Get all losing trades."""
        trades = self.trades_by_strategy[strategy] if strategy else self.trades
        return [t for t in trades if t.pnl_r <= 0]

    def _save_trade_to_disk(self, trade: TradeRecord):
        """Save trade to disk."""
        trades_file = self.storage_path / 'trades.jsonl'
        with open(trades_file, 'a') as f:
            f.write(json.dumps(trade.to_dict()) + '\n')

    def _save_signal_to_disk(self, signal: SignalRecord):
        """Save signal to disk."""
        signals_file = self.storage_path / 'signals.jsonl'
        with open(signals_file, 'a') as f:
            f.write(json.dumps(signal.to_dict()) + '\n')

    def _load_from_disk(self):
        """Load existing data from disk."""
        # Load trades
        trades_file = self.storage_path / 'trades.jsonl'
        if trades_file.exists():
            with open(trades_file, 'r') as f:
                for line in f:
                    trade_dict = json.loads(line)
                    trade = TradeRecord.from_dict(trade_dict)
                    self.trades.append(trade)
                    self.trades_by_strategy[trade.strategy].append(trade)
                    self.trades_by_symbol[trade.symbol].append(trade)
                    self.trades_by_regime[trade.entry_regime].append(trade)

        # Load signals
        signals_file = self.storage_path / 'signals.jsonl'
        if signals_file.exists():
            with open(signals_file, 'r') as f:
                for line in f:
                    signal_dict = json.loads(line)
                    signal = SignalRecord.from_dict(signal_dict)
                    self.signals.append(signal)

    def get_statistics(self) -> Dict:
        """Get database statistics."""
        if not self.trades:
            return {'total_trades': 0}

        total_trades = len(self.trades)
        winning_trades = len([t for t in self.trades if t.pnl_r > 0])
        losing_trades = len([t for t in self.trades if t.pnl_r <= 0])

        avg_win = np.mean([t.pnl_r for t in self.trades if t.pnl_r > 0]) if winning_trades > 0 else 0
        avg_loss = np.mean([t.pnl_r for t in self.trades if t.pnl_r <= 0]) if losing_trades > 0 else 0

        return {
            'total_trades': total_trades,
            'winning_trades': winning_trades,
            'losing_trades': losing_trades,
            'win_rate': winning_trades / total_trades if total_trades > 0 else 0,
            'avg_win_r': avg_win,
            'avg_loss_r': avg_loss,
            'expectancy_r': np.mean([t.pnl_r for t in self.trades]),
            'total_signals': len(self.signals),
        }


class PerformanceAttributionAnalyzer:
    """
    Analyzes WHAT works and WHY.

    Identifies:
    - Which features predict winners vs losers
    - Which regimes are most profitable
    - Which quality score ranges perform best
    - Which parameter combinations work
    """

    def __init__(self, memory_db: TradeMemoryDatabase):
        """Initialize performance attribution analyzer."""
        self.memory_db = memory_db

        # ML models for prediction
        self.win_predictor: Optional[RandomForestClassifier] = None
        self.outcome_predictor: Optional[GradientBoostingRegressor] = None

        logger.info("Performance Attribution Analyzer initialized")

    def analyze_feature_importance(self, strategy: Optional[str] = None) -> Dict[str, float]:
        """
        Analyze which features are most important for predicting outcomes.

        Returns:
            Dict of {feature_name: importance_score}
        """
        trades = self.memory_db.get_strategy_trades(strategy, lookback_days=90) if strategy else self.memory_db.trades[-200:]

        if len(trades) < 30:
            logger.warning("Not enough trades for feature importance analysis")
            return {}

        # Prepare data
        X = []
        y = []
        feature_names = []

        for trade in trades:
            features = []

            # Quality metrics
            features.append(trade.quality_score)
            features.append(trade.mtf_confluence)
            features.append(trade.structure_alignment)
            features.append(trade.order_flow_quality)
            features.append(trade.regime_fit)

            # Entry features (flatten dict)
            if not feature_names:  # First iteration
                feature_names = ['quality_score', 'mtf_confluence', 'structure_alignment',
                               'order_flow_quality', 'regime_fit']
                feature_names.extend(list(trade.entry_features.keys()))

            features.extend(list(trade.entry_features.values()))

            X.append(features)
            y.append(1 if trade.pnl_r > 0 else 0)  # Binary: win or loss

        X = np.array(X)
        y = np.array(y)

        # Train Random Forest for feature importance
        rf = RandomForestClassifier(n_estimators=100, max_depth=10, random_state=42)
        rf.fit(X, y)

        # Get feature importances
        importances = rf.feature_importances_

        importance_dict = dict(zip(feature_names, importances))

        # Sort by importance
        importance_dict = dict(sorted(importance_dict.items(), key=lambda x: x[1], reverse=True))

        logger.info(f"Feature importance analysis complete: Top feature = {list(importance_dict.keys())[0]}")

        return importance_dict

    def analyze_regime_performance(self) -> Dict[str, Dict]:
        """
        Analyze performance by regime.

        Returns:
            Dict of {regime: {win_rate, avg_r, expectancy, count}}
        """
        regime_stats = {}

        for regime in set(t.entry_regime for t in self.memory_db.trades):
            trades = self.memory_db.get_regime_trades(regime, lookback_days=90)

            if len(trades) < 5:
                continue

            wins = [t for t in trades if t.pnl_r > 0]
            losses = [t for t in trades if t.pnl_r <= 0]

            regime_stats[regime] = {
                'count': len(trades),
                'win_rate': len(wins) / len(trades),
                'avg_r': np.mean([t.pnl_r for t in trades]),
                'avg_win_r': np.mean([t.pnl_r for t in wins]) if wins else 0,
                'avg_loss_r': np.mean([t.pnl_r for t in losses]) if losses else 0,
                'expectancy': np.mean([t.pnl_r for t in trades]),
            }

        # Sort by expectancy
        regime_stats = dict(sorted(regime_stats.items(), key=lambda x: x[1]['expectancy'], reverse=True))

        return regime_stats

    def analyze_quality_score_performance(self) -> Dict[str, Dict]:
        """
        Analyze performance by quality score range.

        Returns:
            Dict of {score_range: {win_rate, avg_r, count}}
        """
        bins = [(0.60, 0.70), (0.70, 0.80), (0.80, 0.90), (0.90, 1.0)]

        score_stats = {}

        for min_score, max_score in bins:
            range_key = f"{min_score:.2f}-{max_score:.2f}"

            trades = [t for t in self.memory_db.trades
                     if min_score <= t.quality_score < max_score]

            if len(trades) < 5:
                continue

            wins = [t for t in trades if t.pnl_r > 0]

            score_stats[range_key] = {
                'count': len(trades),
                'win_rate': len(wins) / len(trades),
                'avg_r': np.mean([t.pnl_r for t in trades]),
                'expectancy': np.mean([t.pnl_r for t in trades]),
            }

        return score_stats

    def train_outcome_predictor(self) -> float:
        """
        Train ML model to predict trade outcomes (R-multiple).

        Returns:
            R-squared score of model
        """
        trades = self.memory_db.trades[-500:]  # Use last 500 trades

        if len(trades) < 50:
            logger.warning("Not enough trades to train outcome predictor")
            return 0.0

        # Prepare data
        X = []
        y = []

        for trade in trades:
            features = [
                trade.quality_score,
                trade.mtf_confluence,
                trade.structure_alignment,
                trade.order_flow_quality,
                trade.regime_fit,
                trade.risk_pct,
            ]
            features.extend(list(trade.entry_features.values())[:10])  # Limit features

            X.append(features)
            y.append(trade.pnl_r)

        X = np.array(X)
        y = np.array(y)

        # Train/test split
        split = int(len(X) * 0.8)
        X_train, X_test = X[:split], X[split:]
        y_train, y_test = y[:split], y[split:]

        # Train Gradient Boosting Regressor
        self.outcome_predictor = GradientBoostingRegressor(
            n_estimators=100,
            max_depth=5,
            learning_rate=0.1,
            random_state=42
        )

        self.outcome_predictor.fit(X_train, y_train)

        # Evaluate
        score = self.outcome_predictor.score(X_test, y_test)

        logger.info(f"Outcome predictor trained: R² = {score:.3f}")

        return score

    def predict_trade_outcome(self, signal_features: Dict) -> float:
        """
        Predict expected R-multiple for a signal.

        Args:
            signal_features: Features of the signal

        Returns:
            Predicted R-multiple
        """
        if self.outcome_predictor is None:
            return 1.0  # Default expectation

        # Extract features (same order as training)
        features = [
            signal_features.get('quality_score', 0.7),
            signal_features.get('mtf_confluence', 0.5),
            signal_features.get('structure_alignment', 0.5),
            signal_features.get('order_flow_quality', 0.5),
            signal_features.get('regime_fit', 0.7),
            signal_features.get('risk_pct', 0.5),
        ]

        # Add entry features (limit to 10)
        entry_features = signal_features.get('entry_features', {})
        features.extend(list(entry_features.values())[:10])

        # Pad if necessary
        while len(features) < 16:
            features.append(0.0)

        X = np.array([features])

        prediction = self.outcome_predictor.predict(X)[0]

        return float(prediction)


class AdaptiveParameterOptimizer:
    """
    Optimizes strategy parameters based on recent performance.

    This is where the system LEARNS and IMPROVES:
    - If strategy performing poorly with current parameters → adjust
    - If regime changes → adapt parameters for new regime
    - If features change importance → adjust weights
    """

    def __init__(self, memory_db: TradeMemoryDatabase, attribution: PerformanceAttributionAnalyzer):
        """Initialize adaptive parameter optimizer."""
        self.memory_db = memory_db
        self.attribution = attribution

        # Parameter adjustment history
        self.adjustment_history: Dict[str, List[Dict]] = defaultdict(list)

        # Minimum trades before optimization
        self.min_trades_for_optimization = 20

        logger.info("Adaptive Parameter Optimizer initialized")

    def optimize_strategy_parameters(self, strategy: str) -> Dict[str, float]:
        """
        Optimize parameters for strategy based on recent performance.

        Returns:
            Dict of {parameter: adjusted_value}
        """
        trades = self.memory_db.get_strategy_trades(strategy, lookback_days=30)

        if len(trades) < self.min_trades_for_optimization:
            logger.info(f"Not enough trades for {strategy} optimization ({len(trades)} < {self.min_trades_for_optimization})")
            return {}

        # Analyze current performance
        wins = [t for t in trades if t.pnl_r > 0]
        losses = [t for t in trades if t.pnl_r <= 0]

        win_rate = len(wins) / len(trades)
        expectancy = np.mean([t.pnl_r for t in trades])

        adjustments = {}

        # Strategy-specific optimization logic
        if strategy == 'mean_reversion_statistical':
            adjustments = self._optimize_mean_reversion(trades, win_rate, expectancy)

        elif strategy == 'liquidity_sweep':
            adjustments = self._optimize_liquidity_sweep(trades, win_rate, expectancy)

        elif strategy == 'momentum_quality':
            adjustments = self._optimize_momentum(trades, win_rate, expectancy)

        # Record adjustment
        if adjustments:
            self.adjustment_history[strategy].append({
                'timestamp': datetime.now(),
                'win_rate_before': win_rate,
                'expectancy_before': expectancy,
                'adjustments': adjustments,
            })

            logger.info(f"Parameters optimized for {strategy}: {adjustments}")

        return adjustments

    def _optimize_mean_reversion(self, trades: List[TradeRecord], win_rate: float, expectancy: float) -> Dict:
        """Optimize mean reversion parameters."""
        adjustments = {}

        # If win rate too low, make entry more selective
        if win_rate < 0.50:
            adjustments['entry_sigma_threshold'] = 'INCREASE'  # Higher threshold = fewer but better trades
            adjustments['volume_spike_multiplier'] = 'INCREASE'  # Require stronger volume
            adjustments['confirmations_required_pct'] = 'INCREASE'  # More confirmations

        # If win rate good but expectancy low (winners too small)
        elif win_rate >= 0.60 and expectancy < 1.0:
            adjustments['take_profit_r_multiple'] = 'INCREASE'  # Let winners run
            adjustments['min_r_for_partial'] = 'INCREASE'  # Don't exit too early

        # If too many stops (MAE analysis)
        avg_mae = np.mean([t.mae_r for t in trades])
        if avg_mae > 0.7:  # Stops too tight
            adjustments['stop_loss_atr_multiplier'] = 'INCREASE'  # Wider stops

        return adjustments

    def _optimize_liquidity_sweep(self, trades: List[TradeRecord], win_rate: float, expectancy: float) -> Dict:
        """Optimize liquidity sweep parameters."""
        adjustments = {}

        # If win rate low, tighten requirements
        if win_rate < 0.55:
            adjustments['penetration_max'] = 'DECREASE'  # Smaller penetration = more valid sweep
            adjustments['volume_threshold'] = 'INCREASE'  # Require stronger volume
            adjustments['reversal_velocity_min'] = 'INCREASE'  # Stronger reversal

        # If too few trades
        elif len(trades) < 10:
            adjustments['penetration_max'] = 'INCREASE'  # Allow slightly larger penetration
            adjustments['volume_threshold'] = 'DECREASE'  # Lower volume requirement

        return adjustments

    def _optimize_momentum(self, trades: List[TradeRecord], win_rate: float, expectancy: float) -> Dict:
        """Optimize momentum parameters."""
        adjustments = {}

        # If win rate low
        if win_rate < 0.55:
            adjustments['momentum_threshold'] = 'INCREASE'  # Stronger momentum required
            adjustments['min_mtf_confluence'] = 'INCREASE'  # Better HTF alignment
            adjustments['vpin_clean_max'] = 'DECREASE'  # Only cleanest flow

        return adjustments

    def get_optimization_history(self, strategy: str) -> List[Dict]:
        """Get parameter optimization history for strategy."""
        return self.adjustment_history[strategy]


class MLAdaptiveEngine:
    """
    Master Machine Learning Adaptive Engine.

    This is the LEARNING BRAIN of the system. Integrates with main Brain
    to provide:
    - Learned insights about what works
    - Dynamic parameter adjustments
    - Predictive signals about trade outcomes
    - Regime-specific strategy selection
    """

    def __init__(self, storage_path: Path):
        """
        Initialize ML Adaptive Engine.

        Args:
            storage_path: Path to store learning data
        """
        self.storage_path = storage_path
        self.storage_path.mkdir(parents=True, exist_ok=True)

        # Core components
        self.memory_db = TradeMemoryDatabase(storage_path / 'memory')
        self.attribution = PerformanceAttributionAnalyzer(self.memory_db)
        self.optimizer = AdaptiveParameterOptimizer(self.memory_db, self.attribution)

        # Learning state
        self.last_analysis_time = datetime.now()
        self.analysis_interval_hours = 6  # Re-analyze every 6 hours

        # Performance tracking
        self.learning_iterations = 0

        logger.info("=" * 80)
        logger.info("ML ADAPTIVE ENGINE INITIALIZED")
        logger.info("=" * 80)
        logger.info(f"Memory Database: {len(self.memory_db.trades)} trades loaded")
        logger.info(f"Storage Path: {storage_path}")
        logger.info("System will learn from every trade and adapt parameters dynamically")
        logger.info("=" * 80)

    def record_trade_outcome(self, trade: TradeRecord):
        """
        Record completed trade - the system LEARNS from this.

        Args:
            trade: Completed trade record
        """
        self.memory_db.record_trade(trade)

        # Check if should re-analyze and optimize
        time_since_analysis = (datetime.now() - self.last_analysis_time).total_seconds() / 3600

        if time_since_analysis >= self.analysis_interval_hours:
            self._run_learning_cycle()

    def record_signal(self, signal: SignalRecord):
        """
        Record signal (approved or rejected) - learn from decisions.

        Args:
            signal: Signal record
        """
        self.memory_db.record_signal(signal)

    def get_strategy_adjustment_factors(self, strategy: str) -> Dict[str, float]:
        """
        Get adjustment factors for strategy based on learning.

        Returns:
            Dict of {parameter: multiplier} to adjust strategy parameters
        """
        # Get recent performance
        trades = self.memory_db.get_strategy_trades(strategy, lookback_days=30)

        if len(trades) < 10:
            return {}  # Not enough data

        # Calculate performance metrics
        win_rate = len([t for t in trades if t.pnl_r > 0]) / len(trades)
        expectancy = np.mean([t.pnl_r for t in trades])

        # Adjustment factors based on performance
        factors = {}

        # If performing well, be more aggressive
        if win_rate >= 0.65 and expectancy >= 1.2:
            factors['position_size_multiplier'] = 1.2  # Increase size 20%
            factors['min_quality_score'] = 0.9  # Lower threshold slightly

        # If performing poorly, be more conservative
        elif win_rate < 0.45 or expectancy < 0.5:
            factors['position_size_multiplier'] = 0.7  # Reduce size 30%
            factors['min_quality_score'] = 1.1  # Higher threshold

        return factors

    def predict_signal_outcome(self, signal_dict: Dict) -> float:
        """
        Predict expected outcome (R-multiple) for a signal.

        Uses trained ML model based on historical trades.

        Args:
            signal_dict: Signal dictionary with features

        Returns:
            Predicted R-multiple
        """
        return self.attribution.predict_trade_outcome(signal_dict)

    def get_best_strategies_for_regime(self, regime: str) -> List[Tuple[str, float]]:
        """
        Get strategies ranked by performance in given regime.

        Args:
            regime: Market regime

        Returns:
            List of (strategy, expectancy) tuples, sorted by expectancy
        """
        regime_trades = self.memory_db.get_regime_trades(regime, lookback_days=90)

        if len(regime_trades) < 10:
            return []

        # Group by strategy
        strategy_performance = defaultdict(list)

        for trade in regime_trades:
            strategy_performance[trade.strategy].append(trade.pnl_r)

        # Calculate expectancy per strategy
        strategy_expectancy = []

        for strategy, pnls in strategy_performance.items():
            if len(pnls) >= 5:  # Minimum sample
                expectancy = np.mean(pnls)
                strategy_expectancy.append((strategy, expectancy))

        # Sort by expectancy
        strategy_expectancy.sort(key=lambda x: x[1], reverse=True)

        return strategy_expectancy

    def _run_learning_cycle(self):
        """Run complete learning cycle - analyze and optimize."""
        logger.info("\n" + "=" * 80)
        logger.info("RUNNING ML LEARNING CYCLE")
        logger.info("=" * 80)

        self.learning_iterations += 1

        # 1. Analyze feature importance
        logger.info("Analyzing feature importance...")
        feature_importance = self.attribution.analyze_feature_importance()

        if feature_importance:
            top_features = list(feature_importance.items())[:5]
            logger.info(f"Top 5 predictive features:")
            for feature, importance in top_features:
                logger.info(f"  {feature}: {importance:.4f}")

        # 2. Analyze regime performance
        logger.info("\nAnalyzing regime performance...")
        regime_stats = self.attribution.analyze_regime_performance()

        if regime_stats:
            logger.info(f"Regime performance (by expectancy):")
            for regime, stats in list(regime_stats.items())[:5]:
                logger.info(f"  {regime}: WR={stats['win_rate']:.2%}, E={stats['expectancy']:.2f}R, n={stats['count']}")

        # 3. Analyze quality score performance
        logger.info("\nAnalyzing quality score performance...")
        quality_stats = self.attribution.analyze_quality_score_performance()

        if quality_stats:
            for range_key, stats in quality_stats.items():
                logger.info(f"  Quality {range_key}: WR={stats['win_rate']:.2%}, E={stats['expectancy']:.2f}R, n={stats['count']}")

        # 4. Train outcome predictor
        logger.info("\nTraining outcome predictor...")
        r_squared = self.attribution.train_outcome_predictor()
        logger.info(f"Outcome predictor R²: {r_squared:.3f}")

        # 5. Optimize parameters for each strategy
        logger.info("\nOptimizing strategy parameters...")
        strategies = set(t.strategy for t in self.memory_db.trades)

        for strategy in strategies:
            adjustments = self.optimizer.optimize_strategy_parameters(strategy)
            if adjustments:
                logger.info(f"  {strategy}: {adjustments}")

        self.last_analysis_time = datetime.now()

        logger.info(f"\nLearning cycle #{self.learning_iterations} complete")
        logger.info("=" * 80 + "\n")

    def get_statistics(self) -> Dict:
        """Get ML engine statistics."""
        db_stats = self.memory_db.get_statistics()

        return {
            'memory_database': db_stats,
            'learning_iterations': self.learning_iterations,
            'last_analysis': self.last_analysis_time.isoformat(),
            'hours_since_analysis': (datetime.now() - self.last_analysis_time).total_seconds() / 3600,
        }
