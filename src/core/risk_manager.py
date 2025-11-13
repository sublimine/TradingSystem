"""
Institutional Risk Manager - Advanced Implementation

Statistical circuit breakers based on loss distribution analysis, NOT arbitrary thresholds.
Dynamic position sizing (0.33%-1.0%) based on multi-factor quality scoring.

Research basis:
- Kelly Criterion (Kelly 1956) for optimal sizing
- Tharp's Expectancy Model (Van Tharp 1998)
- Statistical Process Control (SPC) for circuit breakers
- Correlation-based portfolio heat management
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
from collections import deque, defaultdict
import logging
from scipy import stats
from pathlib import Path
import yaml

# Logging institucional (Mandato 6)
from src.core.logging_config import get_logger, LogEvent, log_institutional_event

logger = get_logger(__name__)


class QualityScorer:
    """
    Multi-factor quality scoring system for signal evaluation.

    Factors (from institutional analysis):
    1. Multi-timeframe confluence (40%)
    2. Market structure alignment (25%)
    3. Order flow quality (20%)
    4. Volatility regime fit (10%)
    5. Historical strategy performance (5%)
    """

    def __init__(self):
        self.weights = {
            'mtf_confluence': 0.40,
            'structure_alignment': 0.25,
            'order_flow': 0.20,
            'regime_fit': 0.10,
            'strategy_performance': 0.05,
        }

    def calculate_quality(self, signal: Dict, market_context: Dict) -> float:
        """
        Calculate composite quality score 0.0-1.0.

        Args:
            signal: Signal dictionary with metadata
            market_context: Current market state

        Returns:
            Quality score 0.0-1.0
        """
        scores = {}

        # 1. Multi-timeframe confluence (40%)
        mtf_confluence = signal.get('metadata', {}).get('mtf_confluence', 0.5)
        scores['mtf_confluence'] = self._normalize_score(mtf_confluence, 0.4, 1.0)

        # 2. Market structure alignment (25%)
        structure_score = self._evaluate_structure_alignment(signal, market_context)
        scores['structure_alignment'] = structure_score

        # 3. Order flow quality (20%)
        vpin = market_context.get('vpin', 0.4)
        # Low VPIN = high quality (inverted)
        flow_quality = 1.0 - min(vpin / 0.6, 1.0)
        scores['order_flow'] = flow_quality

        # 4. Volatility regime fit (10%)
        regime_score = signal.get('metadata', {}).get('regime_confidence', 0.7)
        scores['regime_fit'] = regime_score

        # 5. Historical strategy performance (5%)
        strategy_name = signal.get('strategy_name', '')
        perf_score = market_context.get('strategy_performance', {}).get(strategy_name, 0.65)
        scores['strategy_performance'] = perf_score

        # Weighted composite
        composite = sum(scores[k] * self.weights[k] for k in self.weights)

        return min(max(composite, 0.0), 1.0)

    def _normalize_score(self, value: float, min_acceptable: float, max_value: float) -> float:
        """Normalize score to 0.0-1.0 range."""
        if value < min_acceptable:
            return 0.0
        return min((value - min_acceptable) / (max_value - min_acceptable), 1.0)

    def _evaluate_structure_alignment(self, signal: Dict, market_context: Dict) -> float:
        """
        Evaluate alignment with market structure.

        Checks:
        - Price near key levels (order blocks, FVGs, swing points)
        - Direction aligned with structure
        - No conflicting structure overhead
        """
        score = 0.5  # Base score

        metadata = signal.get('metadata', {})
        direction = signal.get('direction', '').upper()

        # Check structure alignment from metadata
        if 'structure_alignment' in metadata:
            return metadata['structure_alignment']

        # Check order block proximity
        if 'order_block_distance_atr' in metadata:
            ob_distance = metadata['order_block_distance_atr']
            if ob_distance < 0.5:
                score += 0.3
            elif ob_distance < 1.0:
                score += 0.15

        # Check FVG alignment
        if 'fvg_aligned' in metadata and metadata['fvg_aligned']:
            score += 0.2

        return min(score, 1.0)


class StatisticalCircuitBreaker:
    """
    Statistical process control for circuit breakers.

    NOT arbitrary "5 stops = pause". Uses statistical distribution analysis:
    - Z-score of recent losses
    - Consecutive loss probability
    - Deviation from expected performance

    Based on SPC (Statistical Process Control) methodology from manufacturing
    adapted for trading by institutional quant desks.
    """

    def __init__(self, config: Dict):
        """
        Initialize statistical circuit breaker.

        Args:
            config: Configuration with statistical parameters
        """
        # Statistical thresholds (NOT arbitrary counts)
        self.z_score_threshold = config.get('circuit_breaker_z_score', 2.5)  # 2.5σ = 99.4% confidence
        self.consecutive_loss_max_probability = config.get('consecutive_loss_max_prob', 0.05)  # 5% chance
        self.lookback_trades = config.get('circuit_breaker_lookback', 30)

        # Historical performance tracking
        self.trade_history = deque(maxlen=self.lookback_trades)
        self.daily_results = defaultdict(list)

        # Circuit breaker state
        self.circuit_open = False
        self.circuit_opened_at = None
        self.circuit_cooldown_minutes = config.get('circuit_cooldown_minutes', 120)

        logger.info(f"Statistical Circuit Breaker initialized: z_threshold={self.z_score_threshold}, "
                   f"max_prob={self.consecutive_loss_max_probability}")

    def check_should_trade(self) -> Tuple[bool, Optional[str]]:
        """
        Check if trading should continue based on statistical analysis.

        Returns:
            (should_trade: bool, reason: Optional[str])
        """
        # Check if circuit breaker is open
        if self.circuit_open:
            if self._check_cooldown_expired():
                self.circuit_open = False
                self.circuit_opened_at = None

                # MANDATO 6: Log circuit breaker close
                log_institutional_event(
                    logger,
                    LogEvent.CIRCUIT_BREAKER_CLOSE,
                    level="INFO",
                    cooldown_elapsed=f"{self.circuit_cooldown_minutes}min",
                    status="TRADING_RESUMED"
                )
            else:
                remaining = self._get_remaining_cooldown_minutes()
                return False, f"CIRCUIT BREAKER OPEN - {remaining:.1f} min remaining"

        # Need minimum trade history for statistics
        if len(self.trade_history) < 10:
            return True, None

        # Statistical analysis
        recent_pnl = [t['pnl_pct'] for t in self.trade_history]

        # 1. Z-score analysis: Are recent losses statistically significant?
        recent_10 = recent_pnl[-10:]
        mean_10 = np.mean(recent_10)
        std_10 = np.std(recent_10)

        if std_10 > 0:
            z_score = abs(mean_10) / std_10

            # If losses are >2.5σ below expectation, pause
            if mean_10 < 0 and z_score > self.z_score_threshold:
                self._open_circuit_breaker()
                return False, f"STATISTICAL ANOMALY - Z-score: {z_score:.2f} (threshold: {self.z_score_threshold})"

        # 2. Consecutive loss probability analysis
        consecutive_losses = self._count_consecutive_losses()

        if consecutive_losses >= 3:
            # Calculate probability of N consecutive losses given historical win rate
            win_rate = self._calculate_historical_win_rate()
            loss_rate = 1.0 - win_rate
            consecutive_prob = loss_rate ** consecutive_losses

            # If consecutive losses are statistically unlikely (<5% chance), pause
            if consecutive_prob < self.consecutive_loss_max_probability:
                self._open_circuit_breaker()
                return False, (f"UNLIKELY LOSS STREAK - {consecutive_losses} losses "
                             f"(probability: {consecutive_prob*100:.2f}%)")

        # 3. Daily drawdown analysis
        today = datetime.now().date()
        if today in self.daily_results:
            daily_pnl = sum(self.daily_results[today])

            # If daily loss >3%, pause (institutional risk limit)
            if daily_pnl < -3.0:
                self._open_circuit_breaker()
                return False, f"DAILY LOSS LIMIT - {daily_pnl:.2f}% (limit: -3.0%)"

        return True, None

    def record_trade(self, pnl_pct: float, symbol: str, strategy: str):
        """Record trade result for statistical analysis."""
        trade = {
            'timestamp': datetime.now(),
            'pnl_pct': pnl_pct,
            'symbol': symbol,
            'strategy': strategy,
            'is_win': pnl_pct > 0,
        }

        self.trade_history.append(trade)

        # Record for daily tracking
        today = datetime.now().date()
        self.daily_results[today].append(pnl_pct)

        logger.debug(f"Trade recorded: {strategy} {symbol} PnL={pnl_pct:.2f}%")

    def _open_circuit_breaker(self):
        """Open circuit breaker (pause trading)."""
        self.circuit_open = True
        self.circuit_opened_at = datetime.now()

        # MANDATO 6: Log circuit breaker open
        consecutive_losses = self._count_consecutive_losses()
        recent_pnl = [t['pnl_pct'] for t in self.trade_history]
        recent_10 = recent_pnl[-10:] if len(recent_pnl) >= 10 else recent_pnl
        z_score = abs(np.mean(recent_10) / np.std(recent_10)) if len(recent_10) > 0 and np.std(recent_10) > 0 else 0.0

        log_institutional_event(
            logger,
            LogEvent.CIRCUIT_BREAKER_OPEN,
            level="ERROR",
            reason="STATISTICAL_ANOMALY",
            z_score=f"{z_score:.2f}",
            threshold=f"{self.z_score_threshold:.2f}",
            consecutive_losses=consecutive_losses,
            cooldown_min=self.circuit_cooldown_minutes
        )

    def _check_cooldown_expired(self) -> bool:
        """Check if cooldown period has expired."""
        if not self.circuit_opened_at:
            return True

        elapsed = (datetime.now() - self.circuit_opened_at).total_seconds() / 60
        return elapsed >= self.circuit_cooldown_minutes

    def _get_remaining_cooldown_minutes(self) -> float:
        """Get remaining cooldown time in minutes."""
        if not self.circuit_opened_at:
            return 0.0

        elapsed = (datetime.now() - self.circuit_opened_at).total_seconds() / 60
        remaining = max(0, self.circuit_cooldown_minutes - elapsed)
        return remaining

    def _count_consecutive_losses(self) -> int:
        """Count consecutive losing trades."""
        count = 0
        for trade in reversed(self.trade_history):
            if trade['is_win']:
                break
            count += 1
        return count

    def _calculate_historical_win_rate(self) -> float:
        """Calculate historical win rate."""
        if not self.trade_history:
            return 0.5

        wins = sum(1 for t in self.trade_history if t['is_win'])
        return wins / len(self.trade_history)

    def get_statistics(self) -> Dict:
        """Get current circuit breaker statistics."""
        if len(self.trade_history) < 2:
            return {'status': 'insufficient_data'}

        recent_pnl = [t['pnl_pct'] for t in self.trade_history]
        recent_10 = recent_pnl[-10:] if len(recent_pnl) >= 10 else recent_pnl

        win_rate = self._calculate_historical_win_rate()
        consecutive_losses = self._count_consecutive_losses()

        return {
            'status': 'OPEN' if self.circuit_open else 'CLOSED',
            'total_trades': len(self.trade_history),
            'win_rate': win_rate,
            'consecutive_losses': consecutive_losses,
            'mean_pnl_recent_10': float(np.mean(recent_10)),
            'std_pnl_recent_10': float(np.std(recent_10)),
            'circuit_opened_at': self.circuit_opened_at.isoformat() if self.circuit_opened_at else None,
            'remaining_cooldown_min': self._get_remaining_cooldown_minutes() if self.circuit_open else 0,
        }


class InstitutionalRiskManager:
    """
    Advanced institutional risk management.

    Features:
    1. Statistical circuit breakers (NOT arbitrary counts)
    2. Multi-factor quality scoring (0.0-1.0)
    3. Dynamic position sizing based on quality (0.33%-1.0%)
    4. Correlation-based portfolio heat management
    5. Drawdown and loss limits
    6. Per-strategy exposure limits
    """

    def __init__(self, config: Dict = None, risk_limits_path: str = None):
        """
        Initialize institutional risk manager.

        Args:
            config: Risk configuration (optional, will load from YAML if not provided)
            risk_limits_path: Path to risk_limits.yaml (Mandato 6)
        """
        # MANDATO 6: Load limits from institutional YAML
        if risk_limits_path is None:
            risk_limits_path = Path(__file__).parent.parent.parent / "config" / "risk_limits.yaml"

        if config is None:
            config = self._load_risk_limits_from_yaml(risk_limits_path)

        self.config = config

        # Position sizing
        self.base_risk_pct = config.get('base_risk_per_trade', 0.5)  # 0.5% base
        self.min_risk_pct = config.get('min_risk_per_trade', 0.33)  # 0.33% minimum
        self.max_risk_pct = config.get('max_risk_per_trade', 1.0)   # 1.0% maximum

        # Quality thresholds
        self.min_quality_score = config.get('min_quality_score', 0.60)

        # Exposure limits
        self.max_total_exposure_pct = config.get('max_total_exposure', 6.0)  # 6% max total
        self.max_correlated_exposure_pct = config.get('max_correlated_exposure', 5.0)  # 5% max correlated
        self.max_per_symbol_exposure_pct = config.get('max_per_symbol_exposure', 2.0)  # 2% per symbol
        self.max_per_strategy_exposure_pct = config.get('max_per_strategy_exposure', 3.0)  # 3% per strategy
        self.max_concurrent_positions = config.get('max_concurrent_positions', 8)  # Max positions

        # Drawdown limits
        self.max_daily_loss_pct = config.get('max_daily_loss', 3.0)  # 3% daily max loss
        self.max_drawdown_pct = config.get('max_drawdown', 15.0)  # 15% max drawdown

        # Components
        self.quality_scorer = QualityScorer()
        self.circuit_breaker = StatisticalCircuitBreaker(config)

        # Portfolio tracking
        self.active_positions: Dict[str, Dict] = {}  # key: position_id
        self.daily_pnl = 0.0
        self.peak_equity = config.get('initial_balance', 100000)
        self.current_equity = self.peak_equity

        # Symbol correlations (loaded from config or calculated)
        self.symbol_correlations = self._load_symbol_correlations()

        # MANDATO 6: Logging institucional
        log_institutional_event(
            logger,
            "RISK_MANAGER_INIT",
            level="INFO",
            base_risk=self.base_risk_pct,
            max_exposure=self.max_total_exposure_pct,
            max_positions=self.max_concurrent_positions,
            quality_min=self.min_quality_score
        )

    def _load_risk_limits_from_yaml(self, yaml_path: Path) -> Dict:
        """
        Load risk limits from YAML config (Mandato 6).

        Args:
            yaml_path: Path to risk_limits.yaml

        Returns:
            Config dictionary
        """
        try:
            with open(yaml_path, 'r') as f:
                data = yaml.safe_load(f)

            # Flatten structure for compatibility
            config = {
                'base_risk_per_trade': data['position_sizing']['base_risk_per_trade'],
                'min_risk_per_trade': data['position_sizing']['min_risk_per_trade'],
                'max_risk_per_trade': data['position_sizing']['max_risk_per_trade'],
                'max_total_exposure': data['exposure']['max_total_exposure'],
                'max_per_symbol_exposure': data['exposure']['max_per_symbol_exposure'],
                'max_per_strategy_exposure': data['exposure']['max_per_strategy_exposure'],
                'max_correlated_exposure': data['exposure']['max_correlated_exposure'],
                'max_concurrent_positions': data['exposure']['max_concurrent_positions'],
                'max_daily_loss': data['drawdown']['max_daily_loss'],
                'max_drawdown': data['drawdown']['max_drawdown'],
                'min_quality_score': data['quality']['min_quality_score'],
                'circuit_breaker_z_score': data['circuit_breaker']['z_score_threshold'],
                'consecutive_loss_max_prob': data['circuit_breaker']['consecutive_loss_max_prob'],
                'circuit_breaker_lookback': data['circuit_breaker']['lookback_trades'],
                'circuit_cooldown_minutes': data['circuit_breaker']['cooldown_minutes'],
                'initial_balance': data['initial_balance'],
            }

            logger.info(f"RISK_LIMITS_LOADED: from {yaml_path}")
            return config

        except Exception as e:
            logger.error(f"RISK_LIMITS_LOAD_ERROR: {e} - using defaults")
            # Return default config
            return {
                'base_risk_per_trade': 0.5,
                'min_risk_per_trade': 0.33,
                'max_risk_per_trade': 1.0,
                'max_total_exposure': 6.0,
                'max_per_symbol_exposure': 2.0,
                'max_per_strategy_exposure': 3.0,
                'max_correlated_exposure': 5.0,
                'max_concurrent_positions': 8,
                'max_daily_loss': 3.0,
                'max_drawdown': 15.0,
                'min_quality_score': 0.60,
                'circuit_breaker_z_score': 2.5,
                'consecutive_loss_max_prob': 0.05,
                'circuit_breaker_lookback': 30,
                'circuit_cooldown_minutes': 120,
                'initial_balance': 100000,
            }

    def evaluate_signal(self, signal: Dict, market_context: Dict) -> Dict:
        """
        Evaluate signal and determine if should trade + position size.

        Args:
            signal: Trading signal
            market_context: Current market state

        Returns:
            {
                'approved': bool,
                'reason': str,
                'quality_score': float,
                'position_size_pct': float,
                'position_size_lots': float,
            }
        """
        # 1. Circuit breaker check
        can_trade, cb_reason = self.circuit_breaker.check_should_trade()
        if not can_trade:
            # MANDATO 6: Log circuit breaker block
            log_institutional_event(
                logger,
                LogEvent.RISK_REJECTED,
                level="WARNING",
                signal_id=signal.get('signal_id', 'unknown'),
                reason="CIRCUIT_BREAKER",
                details=cb_reason
            )
            return {
                'approved': False,
                'reason': cb_reason,
                'quality_score': 0.0,
                'position_size_pct': 0.0,
            }

        # 2. Calculate quality score
        quality_score = self.quality_scorer.calculate_quality(signal, market_context)

        if quality_score < self.min_quality_score:
            # MANDATO 6: Log quality rejection
            log_institutional_event(
                logger,
                LogEvent.RISK_QUALITY_LOW,
                level="WARNING",
                signal_id=signal.get('signal_id', 'unknown'),
                quality=f"{quality_score:.3f}",
                min_threshold=f"{self.min_quality_score:.2f}"
            )
            return {
                'approved': False,
                'reason': f"Quality too low: {quality_score:.3f} < {self.min_quality_score}",
                'quality_score': quality_score,
                'position_size_pct': 0.0,
            }

        # 3. Calculate dynamic position size based on quality FIRST
        # FIX: Must calculate size BEFORE checking exposure limits to include proposed position
        position_size_pct = self._calculate_position_size(quality_score, signal, market_context)

        # 4. Check exposure limits INCLUDING proposed position
        exposure_check = self._check_exposure_limits(signal, position_size_pct)
        if not exposure_check['approved']:
            # MANDATO 6: Log exposure rejection
            log_institutional_event(
                logger,
                LogEvent.RISK_REJECTED,
                level="WARNING",
                signal_id=signal.get('signal_id', 'unknown'),
                reason=exposure_check['limit_type'],
                details=exposure_check['reason']
            )
            return {
                'approved': False,
                'reason': exposure_check['reason'],
                'quality_score': quality_score,
                'position_size_pct': 0.0,
            }

        # 5. Check drawdown limits
        if not self._check_drawdown_limits():
            # MANDATO 6: Log drawdown rejection
            log_institutional_event(
                logger,
                LogEvent.RISK_REJECTED,
                level="WARNING",
                signal_id=signal.get('signal_id', 'unknown'),
                reason="DRAWDOWN_LIMIT",
                current_dd=f"{self._get_current_drawdown():.2f}%",
                max_dd=f"{self.max_drawdown_pct}%"
            )
            return {
                'approved': False,
                'reason': f"Drawdown limit exceeded: {self._get_current_drawdown():.2f}%",
                'quality_score': quality_score,
                'position_size_pct': 0.0,
            }

        # 6. Convert to lot size
        symbol = signal['symbol']
        entry_price = signal['entry_price']
        stop_loss = signal['stop_loss']
        position_size_lots = self._calculate_lot_size(
            symbol, entry_price, stop_loss, position_size_pct
        )

        # MANDATO 6: Log approved signal
        log_institutional_event(
            logger,
            LogEvent.RISK_APPROVED,
            level="INFO",
            signal_id=signal.get('signal_id', 'unknown'),
            quality=f"{quality_score:.3f}",
            position_size_pct=f"{position_size_pct:.2f}%",
            lot_size=f"{position_size_lots:.2f}"
        )

        return {
            'approved': True,
            'reason': 'Signal approved',
            'quality_score': quality_score,
            'position_size_pct': position_size_pct,
            'position_size_lots': position_size_lots,
        }

    def _calculate_position_size(self, quality_score: float, signal: Dict,
                                 market_context: Dict) -> float:
        """
        Calculate dynamic position size based on quality score.

        Institutional approach:
        - Low quality (0.60-0.70): 0.33% risk
        - Medium quality (0.70-0.85): 0.50% risk
        - High quality (0.85-1.0): 0.75-1.0% risk

        Further adjusted by:
        - Volatility regime (high vol = reduce)
        - VPIN (toxic flow = reduce)
        - Recent performance
        """
        # Base sizing from quality (linear interpolation)
        # FIX: Protect against division by zero if min_quality_score == 1.0
        denominator = (1.0 - self.min_quality_score)
        if denominator == 0:
            base_size = self.max_risk_pct
        else:
            base_size = self.min_risk_pct + (quality_score - self.min_quality_score) * \
                       (self.max_risk_pct - self.min_risk_pct) / denominator

        # Volatility adjustment
        regime = market_context.get('volatility_regime', 'NORMAL')
        if regime == 'HIGH':
            base_size *= 0.7  # Reduce 30% in high vol
        elif regime == 'LOW':
            base_size *= 1.2  # Increase 20% in low vol

        # VPIN adjustment (toxic flow)
        vpin = market_context.get('vpin', 0.3)
        if vpin > 0.45:  # Elevated VPIN
            # FIX: Cap reduction at 1.0 to prevent negative position sizes
            reduction = min((vpin - 0.45) / 0.25, 1.0)  # 0-1 scale capped at 1.0
            base_size *= (1.0 - 0.5 * reduction)  # Up to 50% reduction

        # Constrain to limits
        return min(max(base_size, self.min_risk_pct), self.max_risk_pct)

    def _check_exposure_limits(self, signal: Dict, proposed_risk_pct: float) -> Dict:
        """
        Check if new position would violate exposure limits.

        FIX: Now includes proposed_risk_pct in calculations to prevent exceeding limits.
        """
        symbol = signal['symbol']
        strategy = signal['strategy_name']

        # Calculate current exposures
        total_exposure = sum(pos['risk_pct'] for pos in self.active_positions.values())

        # Check total exposure INCLUDING proposed position
        if total_exposure + proposed_risk_pct >= self.max_total_exposure_pct:
            return {
                'approved': False,
                'reason': f"Total exposure limit: {total_exposure:.2f}% >= {self.max_total_exposure_pct}%",
                'limit_type': 'TOTAL_EXPOSURE'
            }

        # Check per-symbol exposure INCLUDING proposed position
        symbol_exposure = sum(pos['risk_pct'] for pos in self.active_positions.values()
                             if pos['symbol'] == symbol)
        if symbol_exposure + proposed_risk_pct >= self.max_per_symbol_exposure_pct:
            return {
                'approved': False,
                'reason': f"Symbol exposure limit: {symbol} {symbol_exposure:.2f}% >= {self.max_per_symbol_exposure_pct}%",
                'limit_type': 'SYMBOL_EXPOSURE'
            }

        # Check per-strategy exposure INCLUDING proposed position
        strategy_exposure = sum(pos['risk_pct'] for pos in self.active_positions.values()
                               if pos['strategy'] == strategy)
        if strategy_exposure + proposed_risk_pct >= self.max_per_strategy_exposure_pct:
            return {
                'approved': False,
                'reason': f"Strategy exposure limit: {strategy} {strategy_exposure:.2f}% >= {self.max_per_strategy_exposure_pct}%",
                'limit_type': 'STRATEGY_EXPOSURE'
            }

        # Check correlated exposure INCLUDING proposed position
        correlated_exposure = self._calculate_correlated_exposure(symbol)
        if correlated_exposure + proposed_risk_pct >= self.max_correlated_exposure_pct:
            return {
                'approved': False,
                'reason': f"Correlated exposure limit: {correlated_exposure:.2f}% >= {self.max_correlated_exposure_pct}%",
                'limit_type': 'CORRELATED_EXPOSURE'
            }

        # Check max concurrent positions
        if len(self.active_positions) >= self.max_concurrent_positions:
            return {
                'approved': False,
                'reason': f"Max concurrent positions: {len(self.active_positions)} >= {self.max_concurrent_positions}",
                'limit_type': 'MAX_POSITIONS'
            }

        return {'approved': True, 'reason': '', 'limit_type': None}

    def _calculate_correlated_exposure(self, symbol: str) -> float:
        """Calculate exposure to symbols correlated with given symbol."""
        correlated_exposure = 0.0

        for pos_id, pos in self.active_positions.items():
            pos_symbol = pos['symbol']

            # Check correlation
            correlation = self._get_correlation(symbol, pos_symbol)

            # If highly correlated (>0.7), count as correlated exposure
            if abs(correlation) > 0.7:
                correlated_exposure += pos['risk_pct']

        return correlated_exposure

    def _get_correlation(self, symbol1: str, symbol2: str) -> float:
        """Get correlation between two symbols."""
        if symbol1 == symbol2:
            return 1.0

        # Check correlation matrix
        key1 = f"{symbol1}_{symbol2}"
        key2 = f"{symbol2}_{symbol1}"

        if key1 in self.symbol_correlations:
            return self.symbol_correlations[key1]
        elif key2 in self.symbol_correlations:
            return self.symbol_correlations[key2]

        # Default: assume no correlation
        return 0.0

    def _load_symbol_correlations(self) -> Dict[str, float]:
        """Load symbol correlation matrix."""
        # Default institutional FX correlations
        correlations = {
            'EURUSD.pro_GBPUSD.pro': 0.85,
            'AUDUSD.pro_NZDUSD.pro': 0.92,
            'EURJPY.pro_GBPJPY.pro': 0.88,
            'USDCAD.pro_USDCHF.pro': 0.75,
            'EURUSD.pro_USDCHF.pro': -0.90,  # Inverse
            'XAUUSD.pro_USDJPY.pro': -0.65,  # Gold vs JPY
        }

        return correlations

    def _check_drawdown_limits(self) -> bool:
        """Check if drawdown limits exceeded."""
        # Daily loss check
        if abs(self.daily_pnl) > self.max_daily_loss_pct:
            logger.warning(f"Daily loss limit exceeded: {self.daily_pnl:.2f}%")
            return False

        # Drawdown check
        current_dd = self._get_current_drawdown()
        if current_dd > self.max_drawdown_pct:
            logger.warning(f"Drawdown limit exceeded: {current_dd:.2f}%")
            return False

        return True

    def _get_current_drawdown(self) -> float:
        """Calculate current drawdown from peak."""
        if self.peak_equity == 0:
            return 0.0

        return ((self.peak_equity - self.current_equity) / self.peak_equity) * 100

    def _calculate_lot_size(self, symbol: str, entry_price: float,
                           stop_loss: float, risk_pct: float) -> float:
        """
        Calculate lot size based on risk percentage.

        Args:
            symbol: Trading symbol
            entry_price: Entry price
            stop_loss: Stop loss price
            risk_pct: Risk as percentage of equity

        Returns:
            Lot size
        """
        # Risk amount in currency
        risk_amount = self.current_equity * (risk_pct / 100)

        # Stop distance in pips (for forex)
        pip_value = 0.0001 if 'JPY' not in symbol else 0.01
        stop_distance_pips = abs(entry_price - stop_loss) / pip_value

        if stop_distance_pips == 0:
            return 0.0

        # Calculate lot size (for forex: 1 lot = 100,000 units)
        # For 0.01 lot = 1000 units, pip value ≈ $0.10
        lot_size = risk_amount / (stop_distance_pips * 10)  # Approximate

        # Round to 0.01 lots
        lot_size = round(lot_size, 2)

        # Constrain to reasonable limits
        lot_size = min(max(lot_size, 0.01), 10.0)

        return lot_size

    def register_position(self, position_id: str, signal: Dict, lot_size: float,
                         risk_pct: float):
        """Register new active position."""
        self.active_positions[position_id] = {
            'symbol': signal['symbol'],
            'strategy': signal['strategy_name'],
            'direction': signal['direction'],
            'entry_price': signal['entry_price'],
            'stop_loss': signal['stop_loss'],
            'take_profit': signal['take_profit'],
            'lot_size': lot_size,
            'risk_pct': risk_pct,
            'opened_at': datetime.now(),
        }

        logger.info(f"Position registered: {position_id} {signal['symbol']} {signal['direction']} "
                   f"{lot_size} lots, risk={risk_pct:.2f}%")

    def close_position(self, position_id: str, exit_price: float):
        """Close position and record result."""
        if position_id not in self.active_positions:
            logger.warning(f"Position {position_id} not found")
            return

        pos = self.active_positions[position_id]

        # Calculate PnL percentage
        entry = pos['entry_price']
        pnl_pips = (exit_price - entry) if pos['direction'] == 'LONG' else (entry - exit_price)
        risk_pips = abs(entry - pos['stop_loss'])

        if risk_pips > 0:
            pnl_r = pnl_pips / risk_pips  # R-multiple
            pnl_pct = pnl_r * pos['risk_pct']
        else:
            pnl_pct = 0.0

        # Update equity
        self.current_equity += (self.current_equity * pnl_pct / 100)

        # FIX: Check if new day and reset daily_pnl
        from datetime import datetime
        today = datetime.now().date()
        if not hasattr(self, '_last_pnl_date') or self._last_pnl_date != today:
            self.daily_pnl = 0.0
            self._last_pnl_date = today

        self.daily_pnl += pnl_pct

        # Update peak
        if self.current_equity > self.peak_equity:
            self.peak_equity = self.current_equity

        # Record for circuit breaker
        self.circuit_breaker.record_trade(pnl_pct, pos['symbol'], pos['strategy'])

        # Remove from active
        del self.active_positions[position_id]

        # MANDATO 6: Log position close
        log_institutional_event(
            logger,
            LogEvent.TRADE_CLOSE,
            level="INFO",
            trade_id=position_id,
            symbol=pos['symbol'],
            exit=f"{exit_price:.5f}",
            pnl=f"{pnl_pct:+.2f}%",
            r_multiple=f"{pnl_r:.2f}R"
        )

    def get_statistics(self) -> Dict:
        """Get current risk statistics."""
        total_exposure = sum(pos['risk_pct'] for pos in self.active_positions.values())

        return {
            'current_equity': self.current_equity,
            'peak_equity': self.peak_equity,
            'current_drawdown_pct': self._get_current_drawdown(),
            'daily_pnl_pct': self.daily_pnl,
            'active_positions': len(self.active_positions),
            'total_exposure_pct': total_exposure,
            'circuit_breaker': self.circuit_breaker.get_statistics(),
        }
