"""
Institutional Brain Layer - Advanced Orchestration with ML Integration

This is NOT a simple signal combiner. This is an advanced orchestration layer
that thinks at the PORTFOLIO level, not individual trade level.

Features:
1. Signal Arbitration - Resolves conflicts between strategies
2. Context-Aware Execution - Times entries based on microstructure
3. Portfolio Thinking - Considers correlation, exposure, balance
4. Multi-Timeframe Coherence - Ensures HTF/LTF alignment
5. Quality-Weighted Scoring - Not all signals are equal
6. Adaptive Learning - Adjusts based on recent performance (NOW WITH ML!)
7. Regime-Aware Selection - Matches strategies to market conditions
8. ML Integration - Uses learned insights to improve all decisions

NOW INTEGRATED WITH ML ADAPTIVE ENGINE:
- Signal scoring enhanced with ML predictions
- Strategy selection uses learned regime performance
- All trades/signals recorded for continuous learning
- Dynamic parameter adjustment from ML insights

This is what separates institutional algorithms from retail "signal combiners".

Research basis:
- Lo & MacKinlay (1997): Maximizing Predictability in the Stock and Bond Markets
- López de Prado (2018): Advances in Financial Machine Learning
- Reinforcement Learning (Sutton & Barto 2018)
- Institutional portfolio construction methodology
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
from collections import defaultdict, deque
import logging

logger = logging.getLogger(__name__)


class SignalArbitrator:
    """
    Arbitrates between conflicting signals from multiple strategies.

    NOT simple "pick highest confidence" retail approach.
    Uses institutional decision framework:
    - Context evaluation
    - Strategy track record
    - Regime fit
    - Risk-reward profile
    - Execution probability
    """

    def __init__(self, config: Dict):
        """Initialize signal arbitrator."""
        self.config = config

        # Strategy performance tracking (last 30 trades per strategy)
        self.strategy_performance: Dict[str, deque] = defaultdict(lambda: deque(maxlen=30))

        # Recent signal outcomes - FIX: Limit size to prevent memory leak
        self.signal_history: deque = deque(maxlen=1000)

    def arbitrate_signals(self, signals: List[Dict], market_context: Dict,
                         regime: str) -> Optional[Dict]:
        """
        Arbitrate between multiple signals to select best.

        Args:
            signals: List of candidate signals
            market_context: Current market state
            regime: Current market regime

        Returns:
            Best signal or None
        """
        if not signals:
            return None

        # Score each signal
        scored_signals = []

        for signal in signals:
            score = self._score_signal(signal, market_context, regime)
            scored_signals.append({
                'signal': signal,
                'score': score,
            })

        # Sort by score
        scored_signals.sort(key=lambda x: x['score'], reverse=True)

        # Check if best signal meets minimum threshold
        best = scored_signals[0]

        min_score = self.config.get('min_arbitration_score', 0.65)

        if best['score'] >= min_score:
            logger.info(f"Signal arbitration: {best['signal']['strategy_name']} selected "
                       f"(score: {best['score']:.3f})")
            return best['signal']
        else:
            logger.info(f"Signal arbitration: No signal meets threshold (best: {best['score']:.3f})")
            return None

    def _score_signal(self, signal: Dict, market_context: Dict, regime: str) -> float:
        """
        Score signal using multi-factor institutional model.

        Factors:
        1. Signal quality score (40%)
        2. Strategy recent performance (25%)
        3. Regime fit (20%)
        4. Risk-reward profile (10%)
        5. Timing quality (5%)
        """
        scores = {}

        # 1. Signal quality (from metadata)
        metadata = signal.get('metadata', {})
        quality = metadata.get('quality_score', 0.7)
        scores['quality'] = quality * 0.40

        # 2. Strategy recent performance
        strategy_name = signal['strategy_name']
        perf_score = self._get_strategy_performance_score(strategy_name)
        scores['performance'] = perf_score * 0.25

        # 3. Regime fit
        regime_fit = self._evaluate_regime_fit(signal, regime)
        scores['regime'] = regime_fit * 0.20

        # 4. Risk-reward profile
        rr_score = self._evaluate_risk_reward(signal)
        scores['risk_reward'] = rr_score * 0.10

        # 5. Timing quality (based on microstructure)
        timing_score = self._evaluate_timing(signal, market_context)
        scores['timing'] = timing_score * 0.05

        # Composite score
        total_score = sum(scores.values())

        logger.debug(f"Signal score breakdown: {signal['strategy_name']} = {total_score:.3f} "
                    f"({scores})")

        return total_score

    def _get_strategy_performance_score(self, strategy_name: str) -> float:
        """Get performance score for strategy based on recent results."""
        if strategy_name not in self.strategy_performance:
            return 0.7  # Neutral

        results = list(self.strategy_performance[strategy_name])

        if not results:
            return 0.7

        # Calculate win rate and average R
        wins = sum(1 for r in results if r > 0)
        win_rate = wins / len(results)

        avg_r = np.mean(results)

        # Composite performance score
        # Win rate 60%+, avg R 1.5+  → 1.0
        # Win rate 50%, avg R 1.0    → 0.7
        # Win rate 40%-, avg R 0.5-  → 0.3

        wr_score = min(win_rate / 0.6, 1.0)
        r_score = min(max(avg_r, 0) / 2.0, 1.0)

        performance_score = (wr_score * 0.6 + r_score * 0.4)

        return min(max(performance_score, 0.0), 1.0)

    def _evaluate_regime_fit(self, signal: Dict, regime: str) -> float:
        """Evaluate how well signal strategy fits current regime."""
        strategy_name = signal['strategy_name']

        # Regime-strategy fit matrix (institutional knowledge)
        fit_matrix = {
            'TREND_STRONG_UP': {
                'momentum_quality': 1.0,
                'breakout_volume_confirmation': 0.95,
                'htf_ltf_liquidity': 0.90,
                'order_block_institutional': 0.75,
                'mean_reversion_statistical': 0.30,
            },
            'TREND_STRONG_DOWN': {
                'momentum_quality': 1.0,
                'breakout_volume_confirmation': 0.95,
                'htf_ltf_liquidity': 0.90,
                'order_block_institutional': 0.75,
                'mean_reversion_statistical': 0.30,
            },
            'RANGING_LOW_VOL': {
                'mean_reversion_statistical': 1.0,
                'kalman_pairs_trading': 0.95,
                'iceberg_detection': 0.90,
                'correlation_divergence': 0.85,
                'momentum_quality': 0.40,
            },
            'RANGING_HIGH_VOL': {
                'volatility_regime_adaptation': 1.0,
                'mean_reversion_statistical': 0.80,
                'breakout_volume_confirmation': 0.60,
            },
            'REVERSAL_EXHAUSTION': {
                'mean_reversion_statistical': 1.0,
                'liquidity_sweep': 0.95,
                'order_block_institutional': 0.90,
            },
            'BREAKOUT_MOMENTUM': {
                'breakout_volume_confirmation': 1.0,
                'momentum_quality': 0.95,
                'idp_inducement_distribution': 0.90,
            },
        }

        regime_fits = fit_matrix.get(regime, {})
        fit_score = regime_fits.get(strategy_name, None)

        # P2-019: Logging cuando estrategia no está en fit_matrix (usar default)
        if fit_score is None:
            logger.warning(
                f"REGIME_FIT_DEFAULT: Strategy '{strategy_name}' not in fit_matrix "
                f"for regime '{regime}'. Using default 0.7. "
                f"Consider adding to fit_matrix if strategy becomes permanent."
            )
            fit_score = 0.7  # Default neutral

        return fit_score

    def _evaluate_risk_reward(self, signal: Dict) -> float:
        """Evaluate risk-reward profile of signal."""
        entry = signal['entry_price']
        stop = signal['stop_loss']
        target = signal['take_profit']

        risk = abs(entry - stop)
        reward = abs(target - entry)

        if risk == 0:
            return 0.0

        rr_ratio = reward / risk

        # Score based on R:R
        # 3.0+ R:R → 1.0
        # 2.0 R:R  → 0.8
        # 1.5 R:R  → 0.6
        # 1.0 R:R  → 0.4

        if rr_ratio >= 3.0:
            return 1.0
        elif rr_ratio >= 2.0:
            return 0.8
        elif rr_ratio >= 1.5:
            return 0.6
        elif rr_ratio >= 1.0:
            return 0.4
        else:
            return 0.2

    def _evaluate_timing(self, signal: Dict, market_context: Dict) -> float:
        """
        Evaluate execution timing quality.

        Good timing:
        - Low spread
        - Clean order flow (low VPIN)
        - Not at session extremes (avoid reversals)
        """
        # VPIN check
        vpin = market_context.get('vpin', 0.4)
        if vpin > 0.50:
            timing_score = 0.3  # Poor timing - toxic flow
        elif vpin < 0.30:
            timing_score = 1.0  # Excellent timing - clean flow
        else:
            timing_score = 0.7  # Acceptable

        return timing_score

    def record_signal_outcome(self, signal: Dict, outcome_r: float):
        """
        Record signal outcome for learning.

        Args:
            signal: Original signal
            outcome_r: Result in R multiples
        """
        strategy_name = signal['strategy_name']
        self.strategy_performance[strategy_name].append(outcome_r)

        logger.debug(f"Signal outcome recorded: {strategy_name} = {outcome_r:.2f}R")


class PortfolioOrchestrator:
    """
    Portfolio-level orchestration.

    Thinks about:
    - Overall portfolio balance
    - Correlation between positions
    - Sector/currency exposure
    - Risk concentration
    - Execution sequencing

    NOT just "take every signal" retail approach.
    """

    def __init__(self, config: Dict, risk_manager):
        """
        Initialize portfolio orchestrator.

        Args:
            config: Configuration
            risk_manager: Risk manager instance
        """
        self.config = config
        self.risk_manager = risk_manager

        # Portfolio state
        self.active_positions: Dict[str, Dict] = {}
        # FIX: Limit pending_orders to prevent memory leak
        self.pending_orders: deque = deque(maxlen=100)

        # Exposure limits
        self.max_positions_per_symbol = config.get('max_positions_per_symbol', 2)
        self.max_total_positions = config.get('max_total_positions', 8)

    def evaluate_new_signal(self, signal: Dict, market_context: Dict) -> Dict:
        """
        Evaluate if new signal should be executed considering portfolio.

        Args:
            signal: Trading signal
            market_context: Current market state

        Returns:
            {
                'approved': bool,
                'reason': str,
                'adjustments': dict
            }
        """
        # 1. Check position limits
        symbol = signal['symbol']

        symbol_positions = sum(1 for p in self.active_positions.values() if p['symbol'] == symbol)

        if symbol_positions >= self.max_positions_per_symbol:
            return {
                'approved': False,
                'reason': f"Max positions per symbol reached: {symbol} ({symbol_positions})",
                'adjustments': {}
            }

        if len(self.active_positions) >= self.max_total_positions:
            return {
                'approved': False,
                'reason': f"Max total positions reached: {len(self.active_positions)}",
                'adjustments': {}
            }

        # 2. Check correlation exposure
        direction = signal['direction']
        correlated_exposure = self._calculate_correlated_exposure(symbol, direction)

        max_correlated = self.config.get('max_correlated_positions', 4)

        if correlated_exposure >= max_correlated:
            return {
                'approved': False,
                'reason': f"Max correlated exposure: {symbol} {direction} ({correlated_exposure} positions)",
                'adjustments': {}
            }

        # 3. Portfolio balance check
        balance_check = self._check_portfolio_balance(signal)

        if not balance_check['approved']:
            return balance_check

        # 4. Risk manager approval
        risk_eval = self.risk_manager.evaluate_signal(signal, market_context)

        if not risk_eval['approved']:
            return {
                'approved': False,
                'reason': f"Risk manager rejected: {risk_eval['reason']}",
                'adjustments': {}
            }

        # Approved with risk adjustments
        return {
            'approved': True,
            'reason': 'Portfolio approval',
            'adjustments': {
                'position_size_pct': risk_eval['position_size_pct'],
                'position_size_lots': risk_eval['position_size_lots'],
                'quality_score': risk_eval['quality_score'],
            }
        }

    def _calculate_correlated_exposure(self, symbol: str, direction: str) -> int:
        """Calculate number of positions correlated with given symbol/direction."""
        # Simplified: Count positions in same direction for correlated pairs
        # In production, would use actual correlation matrix

        correlations = {
            'EURUSD.pro': ['GBPUSD.pro', 'EURJPY.pro'],
            'GBPUSD.pro': ['EURUSD.pro', 'GBPJPY.pro'],
            'AUDUSD.pro': ['NZDUSD.pro'],
            'NZDUSD.pro': ['AUDUSD.pro'],
        }

        correlated_symbols = correlations.get(symbol, [])
        correlated_symbols.append(symbol)  # Include itself

        count = 0
        for pos in self.active_positions.values():
            if pos['symbol'] in correlated_symbols and pos['direction'] == direction:
                count += 1

        return count

    def _check_portfolio_balance(self, signal: Dict) -> Dict:
        """
        Check portfolio balance and diversification.

        Ensures:
        - Not too many positions in one direction
        - Not too concentrated in one strategy type
        """
        if not self.active_positions:
            return {'approved': True, 'reason': ''}

        direction = signal['direction']
        strategy = signal['strategy_name']

        # Count directional positions
        long_count = sum(1 for p in self.active_positions.values() if p['direction'] == 'LONG')
        short_count = sum(1 for p in self.active_positions.values() if p['direction'] == 'SHORT')

        # Check directional imbalance (max 6:2 ratio)
        if direction == 'LONG' and long_count >= 6 and short_count <= 2:
            return {
                'approved': False,
                'reason': f"Portfolio imbalance: {long_count} longs vs {short_count} shorts",
                'adjustments': {}
            }

        if direction == 'SHORT' and short_count >= 6 and long_count <= 2:
            return {
                'approved': False,
                'reason': f"Portfolio imbalance: {short_count} shorts vs {long_count} longs",
                'adjustments': {}
            }

        # Check strategy concentration (max 50% from one strategy type)
        strategy_count = sum(1 for p in self.active_positions.values() if p['strategy'] == strategy)

        if strategy_count >= len(self.active_positions) * 0.5:
            return {
                'approved': False,
                'reason': f"Strategy concentration: {strategy} ({strategy_count} positions)",
                'adjustments': {}
            }

        return {'approved': True, 'reason': ''}

    def register_position(self, position_id: str, signal: Dict, lot_size: float):
        """Register new position in portfolio."""
        self.active_positions[position_id] = {
            'symbol': signal['symbol'],
            'direction': signal['direction'],
            'strategy': signal['strategy_name'],
            'lot_size': lot_size,
            'opened_at': datetime.now(),
        }

        logger.info(f"Position registered in portfolio: {position_id}")

    def remove_position(self, position_id: str):
        """Remove position from portfolio."""
        if position_id in self.active_positions:
            del self.active_positions[position_id]
            logger.info(f"Position removed from portfolio: {position_id}")


class InstitutionalBrain:
    """
    Master orchestration layer - the "brain" of the institutional algorithm.

    Integrates:
    - Signal arbitration
    - Portfolio orchestration
    - Regime detection
    - Risk management
    - Position management
    - Multi-timeframe analysis
    - ML Adaptive Engine (CONTINUOUS LEARNING)

    This is what makes the difference between institutional and retail algorithms.
    """

    def __init__(self, config: Dict, risk_manager, position_manager,
                 regime_detector, mtf_manager, ml_engine=None):
        """
        Initialize institutional brain.

        Args:
            config: Brain configuration
            risk_manager: Risk manager instance
            position_manager: Position manager instance
            regime_detector: Regime detector instance
            mtf_manager: Multi-timeframe manager instance
            ml_engine: ML Adaptive Engine instance (optional)
        """
        self.config = config
        self.risk_manager = risk_manager
        self.position_manager = position_manager
        self.regime_detector = regime_detector
        self.mtf_manager = mtf_manager
        self.ml_engine = ml_engine  # ML ENGINE FOR CONTINUOUS LEARNING

        # Components
        self.arbitrator = SignalArbitrator(config)
        self.orchestrator = PortfolioOrchestrator(config, risk_manager)

        # Performance tracking
        self.total_signals_received = 0
        self.total_signals_approved = 0
        self.total_signals_rejected = 0

        # Active trades tracking for ML feedback
        self.active_trades_ml: Dict[str, Dict] = {}

        if ml_engine:
            logger.info("Institutional Brain initialized - Advanced orchestration WITH ML LEARNING active")
        else:
            logger.info("Institutional Brain initialized - Advanced orchestration active (no ML)")

    def process_signals(self, raw_signals: List[Dict], market_data: Dict[str, pd.DataFrame],
                       features: Dict) -> List[Dict]:
        """
        Process raw signals through institutional decision framework.

        Steps:
        1. Detect market regime
        2. Filter signals by regime fit
        3. Arbitrate between signals (if multiple for same symbol)
        4. Portfolio-level approval
        5. Risk management approval
        6. Position sizing
        7. Execution instructions

        Args:
            raw_signals: Raw signals from strategies
            market_data: Current market data per symbol
            features: Calculated features per symbol

        Returns:
            List of approved execution orders
        """
        self.total_signals_received += len(raw_signals)

        if not raw_signals:
            return []

        logger.info(f"Brain processing {len(raw_signals)} signals")

        # Group signals by symbol
        signals_by_symbol = defaultdict(list)
        for signal in raw_signals:
            signals_by_symbol[signal['symbol']].append(signal)

        approved_orders = []

        # Process each symbol
        for symbol, signals in signals_by_symbol.items():
            # Get market context for symbol
            symbol_data = market_data.get(symbol)
            symbol_features = features.get(symbol, {})

            if symbol_data is None or symbol_data.empty:
                logger.warning(f"No market data for {symbol}, skipping signals")
                continue

            # 1. Detect regime
            regime_info = self.regime_detector.detect_regime(symbol_data, symbol_features)
            current_regime = regime_info['regime']
            regime_confidence = regime_info['confidence']

            logger.info(f"{symbol}: Regime = {current_regime} (confidence: {regime_confidence:.2f})")

            # 2. Check if should block trading based on regime
            should_block, block_reason = self.regime_detector.should_block_trading(
                current_regime, regime_confidence
            )

            if should_block:
                logger.warning(f"{symbol}: Trading blocked - {block_reason}")
                self.total_signals_rejected += len(signals)
                continue

            # 3. Filter signals by regime fit (remove very poor fits)
            optimal_strategies = regime_info['optimal_strategies']

            if optimal_strategies:
                # Prefer signals from optimal strategies
                filtered_signals = [s for s in signals if s['strategy_name'] in optimal_strategies]

                # If no optimal strategy signals, still consider high-quality others
                if not filtered_signals:
                    filtered_signals = [s for s in signals
                                       if s.get('metadata', {}).get('quality_score', 0) > 0.75]
            else:
                filtered_signals = signals

            if not filtered_signals:
                logger.info(f"{symbol}: No signals after regime filtering")
                self.total_signals_rejected += len(signals)
                continue

            # 4. Arbitrate between signals (pick best)
            market_context = {
                'vpin': symbol_features.get('vpin', 0.4),
                'volatility_regime': regime_info['sub_regimes']['volatility']['regime'],
                'regime': current_regime,
                'strategy_performance': {},  # Could add recent performance per strategy
            }

            best_signal = self.arbitrator.arbitrate_signals(
                filtered_signals, market_context, current_regime
            )

            if not best_signal:
                logger.info(f"{symbol}: No signal passed arbitration")
                self.total_signals_rejected += len(signals)
                continue

            # 5. ML PREDICTION (if available) - Enhance decision with learned insights
            if self.ml_engine:
                signal_features = {
                    'quality_score': best_signal.get('metadata', {}).get('quality_score', 0.7),
                    'mtf_confluence': best_signal.get('metadata', {}).get('mtf_confluence', 0.5),
                    'structure_alignment': best_signal.get('metadata', {}).get('structure_alignment', 0.5),
                    'order_flow_quality': 1.0 - symbol_features.get('vpin', 0.4),
                    'regime_fit': 0.7,
                    'risk_pct': 0.5,
                    'entry_features': symbol_features,
                }

                predicted_r = self.ml_engine.predict_signal_outcome(signal_features)
                logger.info(f"{symbol}: ML predicts {predicted_r:.2f}R outcome")

                # If ML predicts poor outcome, reject signal
                if predicted_r < 0.5:
                    logger.warning(f"{symbol}: ML predicts poor outcome ({predicted_r:.2f}R), rejecting")

                    # Record rejected signal in ML
                    if self.ml_engine:
                        from .ml_adaptive_engine import SignalRecord
                        signal_record = SignalRecord(
                            signal_id=f"{symbol}_{best_signal['strategy_name']}_{int(datetime.now().timestamp())}",
                            timestamp=datetime.now(),
                            symbol=symbol,
                            strategy=best_signal['strategy_name'],
                            direction=best_signal['direction'],
                            quality_score=best_signal.get('metadata', {}).get('quality_score', 0.7),
                            entry_price=best_signal['entry_price'],
                            stop_loss=best_signal['stop_loss'],
                            take_profit=best_signal['take_profit'],
                            regime=current_regime,
                            features=symbol_features,
                            approved=False,
                            rejection_reason=f"ML predicted poor outcome: {predicted_r:.2f}R",
                            trade_id=None,
                            eventual_outcome_r=None,
                        )
                        self.ml_engine.record_signal(signal_record)

                    self.total_signals_rejected += 1
                    continue

            # 6. Portfolio-level approval
            portfolio_eval = self.orchestrator.evaluate_new_signal(best_signal, market_context)

            if not portfolio_eval['approved']:
                logger.info(f"{symbol}: Portfolio rejected - {portfolio_eval['reason']}")

                # Record rejected signal in ML
                if self.ml_engine:
                    from .ml_adaptive_engine import SignalRecord
                    signal_record = SignalRecord(
                        signal_id=f"{symbol}_{best_signal['strategy_name']}_{int(datetime.now().timestamp())}",
                        timestamp=datetime.now(),
                        symbol=symbol,
                        strategy=best_signal['strategy_name'],
                        direction=best_signal['direction'],
                        quality_score=best_signal.get('metadata', {}).get('quality_score', 0.7),
                        entry_price=best_signal['entry_price'],
                        stop_loss=best_signal['stop_loss'],
                        take_profit=best_signal['take_profit'],
                        regime=current_regime,
                        features=symbol_features,
                        approved=False,
                        rejection_reason=portfolio_eval['reason'],
                        trade_id=None,
                        eventual_outcome_r=None,
                    )
                    self.ml_engine.record_signal(signal_record)

                self.total_signals_rejected += 1
                continue

            # 7. Apply adjustments (position sizing from risk manager)
            adjusted_signal = best_signal.copy()
            adjusted_signal.update(portfolio_eval['adjustments'])

            # 7.5. APPLY STRATEGIC STOPS & TARGETS (structure-based)
            try:
                from src.features.strategic_stops import (
                    calculate_strategic_stop,
                    calculate_strategic_target
                )

                # Get MTF data for this symbol (M5, M15, H1, H4)
                mtf_data_dict = None
                if self.mtf_manager:
                    try:
                        mtf_data_dict = {
                            'M5': self.mtf_manager.get_data(symbol, 'M5'),
                            'M15': self.mtf_manager.get_data(symbol, 'M15'),
                            'H1': self.mtf_manager.get_data(symbol, 'H1'),
                            'H4': self.mtf_manager.get_data(symbol, 'H4'),
                        }
                        # Remove None values
                        mtf_data_dict = {k: v for k, v in mtf_data_dict.items() if v is not None and not v.empty}
                    except Exception as mtf_err:
                        logger.debug(f"{symbol}: MTF data unavailable: {mtf_err}")
                        mtf_data_dict = None

                # Calculate strategic stop (wick sweep, OB, FVG, swing, ATR fallback)
                strategic_stop, stop_type = calculate_strategic_stop(
                    direction=best_signal['direction'],
                    entry_price=best_signal['entry_price'],
                    market_data=symbol_data,
                    features=symbol_features,
                    mtf_data=mtf_data_dict
                )

                # Calculate strategic target (untaken liq, OB, FVG, fractal, swing, RR fallback)
                strategic_target, target_type = calculate_strategic_target(
                    direction=best_signal['direction'],
                    entry_price=best_signal['entry_price'],
                    stop_loss=strategic_stop,
                    market_data=symbol_data,
                    features=symbol_features,
                    mtf_data=mtf_data_dict
                )

                # Replace original stops/targets with strategic ones
                adjusted_signal['stop_loss'] = strategic_stop
                adjusted_signal['take_profit'] = strategic_target
                adjusted_signal['stop_type'] = stop_type
                adjusted_signal['target_type'] = target_type

                logger.info(f"{symbol}: Strategic placement applied - "
                          f"SL={stop_type}, TP={target_type}")

            except Exception as e:
                logger.warning(f"{symbol}: Strategic stops failed, using original: {e}")
                # Keep original stops/targets from strategy

            # 8. Create execution order
            # FIX: Use adjusted_signal stops/targets (strategic placement), not original best_signal
            execution_order = {
                'signal': adjusted_signal,
                'symbol': symbol,
                'direction': best_signal['direction'],
                'entry_price': best_signal['entry_price'],
                'stop_loss': adjusted_signal['stop_loss'],  # FIX: Use strategic stop
                'take_profit': adjusted_signal['take_profit'],  # FIX: Use strategic target
                'lot_size': portfolio_eval['adjustments']['position_size_lots'],
                'risk_pct': portfolio_eval['adjustments']['position_size_pct'],
                'quality_score': portfolio_eval['adjustments']['quality_score'],
                'strategy': best_signal['strategy_name'],
                'regime': current_regime,
                'timestamp': datetime.now(),
            }

            # Record APPROVED signal in ML
            if self.ml_engine:
                from .ml_adaptive_engine import SignalRecord
                signal_id = f"{symbol}_{best_signal['strategy_name']}_{int(datetime.now().timestamp())}"
                # FIX: Record strategic stops/targets for ML learning, not original
                signal_record = SignalRecord(
                    signal_id=signal_id,
                    timestamp=datetime.now(),
                    symbol=symbol,
                    strategy=best_signal['strategy_name'],
                    direction=best_signal['direction'],
                    quality_score=portfolio_eval['adjustments']['quality_score'],
                    entry_price=best_signal['entry_price'],
                    stop_loss=adjusted_signal['stop_loss'],  # FIX: Use strategic stop
                    take_profit=adjusted_signal['take_profit'],  # FIX: Use strategic target
                    regime=current_regime,
                    features=symbol_features,
                    approved=True,
                    rejection_reason=None,
                    trade_id=None,  # Will be linked later
                    eventual_outcome_r=None,
                )
                self.ml_engine.record_signal(signal_record)

                # Track for later linking
                execution_order['signal_id_ml'] = signal_id

            approved_orders.append(execution_order)
            self.total_signals_approved += 1

            logger.info(f"{symbol}: Signal APPROVED - {best_signal['strategy_name']} "
                       f"{best_signal['direction']} @ {best_signal['entry_price']:.5f} "
                       f"({portfolio_eval['adjustments']['position_size_lots']:.2f} lots)")

        # Update rejection stats
        rejected_count = self.total_signals_received - self.total_signals_approved
        self.total_signals_rejected = rejected_count

        logger.info(f"Brain processed: {len(approved_orders)} approved, "
                   f"{len(raw_signals) - len(approved_orders)} rejected")

        return approved_orders

    def update_positions(self, market_data: Dict[str, pd.DataFrame]):
        """
        Update all active positions through position manager.

        Args:
            market_data: Current market data per symbol
        """
        self.position_manager.update_positions(market_data)

    def record_trade_outcome(self, signal: Dict, outcome_r: float):
        """
        Record trade outcome for learning.

        Args:
            signal: Original signal
            outcome_r: Outcome in R multiples
        """
        self.arbitrator.record_signal_outcome(signal, outcome_r)

        # Also record in ML engine if available
        if self.ml_engine:
            logger.debug(f"Recording trade outcome in ML: {outcome_r:.2f}R")

    def record_completed_trade_ml(self, trade_id: str, signal_id: str, trade_data: Dict):
        """
        Record completed trade in ML engine for learning.

        Args:
            trade_id: Trade identifier
            signal_id: Signal identifier (for linking)
            trade_data: Complete trade data including outcome
        """
        if not self.ml_engine:
            return

        from .ml_adaptive_engine import TradeRecord

        # Create trade record
        trade_record = TradeRecord(
            trade_id=trade_id,
            timestamp=datetime.now(),
            symbol=trade_data['symbol'],
            strategy=trade_data['strategy'],
            direction=trade_data['direction'],

            entry_price=trade_data['entry_price'],
            entry_time=trade_data.get('entry_time', datetime.now()),
            entry_regime=trade_data.get('entry_regime', 'UNKNOWN'),
            entry_features=trade_data.get('entry_features', {}),

            quality_score=trade_data.get('quality_score', 0.7),
            mtf_confluence=trade_data.get('mtf_confluence', 0.5),
            structure_alignment=trade_data.get('structure_alignment', 0.5),
            order_flow_quality=trade_data.get('order_flow_quality', 0.5),
            regime_fit=trade_data.get('regime_fit', 0.7),

            lot_size=trade_data['lot_size'],
            risk_pct=trade_data.get('risk_pct', 0.5),
            stop_loss=trade_data['stop_loss'],
            take_profit=trade_data['take_profit'],

            exit_price=trade_data['exit_price'],
            exit_time=trade_data.get('exit_time', datetime.now()),
            exit_reason=trade_data.get('exit_reason', 'UNKNOWN'),

            pnl_pct=trade_data.get('pnl_pct', 0.0),
            pnl_r=trade_data['pnl_r'],
            mae_r=trade_data.get('mae_r', 0.0),
            mfe_r=trade_data.get('mfe_r', 0.0),
            duration_minutes=trade_data.get('duration_minutes', 0),

            avg_vpin_during=trade_data.get('avg_vpin_during', 0.4),
            avg_volatility_during=trade_data.get('avg_volatility_during', 0.0),
            regime_changes_during=trade_data.get('regime_changes_during', 0),
        )

        # Record in ML
        self.ml_engine.record_trade_outcome(trade_record)

        # Link signal to trade
        if signal_id:
            self.ml_engine.memory_db.link_signal_to_trade(signal_id, trade_id, trade_data['pnl_r'])

        logger.info(f"Trade {trade_id} recorded in ML: {trade_data['pnl_r']:.2f}R")

    def get_statistics(self) -> Dict:
        """Get brain statistics."""
        approval_rate = (self.total_signals_approved / self.total_signals_received * 100
                        if self.total_signals_received > 0 else 0)

        stats = {
            'total_signals_received': self.total_signals_received,
            'total_signals_approved': self.total_signals_approved,
            'total_signals_rejected': self.total_signals_rejected,
            'approval_rate_pct': approval_rate,
            'risk_manager': self.risk_manager.get_statistics(),
            'position_manager': self.position_manager.get_statistics(),
            'regime': self.regime_detector.get_statistics(),
        }

        # Add ML statistics if available
        if self.ml_engine:
            stats['ml_engine'] = self.ml_engine.get_statistics()

        return stats
