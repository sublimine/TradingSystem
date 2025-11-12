"""
Volatility Regime Adaptation Strategy

Adjusts trading parameters dynamically based on volatility regime identification.
Uses Hidden Markov Model to detect low and high volatility states, adapting
entry thresholds, stop distances, and position sizing accordingly.
"""

import numpy as np
import pandas as pd
from typing import List, Dict, Optional
import logging
from datetime import datetime
from .strategy_base import StrategyBase, Signal


class VolatilityRegimeAdaptation(StrategyBase):
    """
    Strategy that adapts parameters based on detected volatility regime.
    
    During high volatility periods, applies conservative thresholds and wider stops
    to avoid whipsaws. During low volatility periods, uses aggressive thresholds
    to capture smaller movements with higher frequency.
    """

    def __init__(self, config: Dict):
        """
        Initialize volatility regime adaptation strategy.

        Required config parameters:
            - lookback_period: Period for volatility calculation (typically 20)
            - regime_lookback: Recent observations for regime prediction (typically 50)
            - low_vol_entry_threshold: Entry threshold for low vol regime (typically 1.5)
            - high_vol_entry_threshold: Entry threshold for high vol regime (typically 2.5)
            - low_vol_stop_multiplier: ATR multiplier for stops in low vol (typically 1.5)
            - high_vol_stop_multiplier: ATR multiplier for stops in high vol (typically 2.5)
            - low_vol_sizing_boost: Sizing boost factor for low vol (typically 1.2)
            - high_vol_sizing_reduction: Sizing reduction factor for high vol (typically 0.7)
            - min_regime_confidence: Minimum confidence to apply regime (typically 0.7)
        """
        super().__init__(config)

        self.lookback_period = config.get('lookback_period', 20)
        self.regime_lookback = config.get('regime_lookback', 40)
        self.low_vol_entry_threshold = config.get('low_vol_entry_threshold', 1.0)  # Entrada mÃƒÂ¡s temprana
        self.high_vol_entry_threshold = config.get('high_vol_entry_threshold', 2.0)
        self.low_vol_stop_multiplier = config.get('low_vol_stop_multiplier', 1.5)
        self.high_vol_stop_multiplier = config.get('high_vol_stop_multiplier', 2.5)
        self.low_vol_sizing_boost = config.get('low_vol_sizing_boost', 1.2)
        self.high_vol_sizing_reduction = config.get('high_vol_sizing_reduction', 0.7)
        self.min_regime_confidence = config.get('min_regime_confidence', 0.6)

        self.hmm_model = None
        self.volatility_history = []
        self.current_regime = None
        self.regime_confidence = 0.0

        self.logger = logging.getLogger(self.__class__.__name__)

        self._initialize_hmm()

    def _initialize_hmm(self):
        """Initialize Hidden Markov Model for regime detection."""
        try:
            from src.features.statistical_models import VolatilityHMM
            self.hmm_model = VolatilityHMM(random_seed=42)
        except ImportError:
            raise ImportError("VolatilityHMM not found in statistical_models module")

    def evaluate(self, market_data: pd.DataFrame, features: Dict) -> List[Signal]:
        """
        Evaluate market for trading opportunities with regime-adapted parameters.

        Args:
            market_data: Recent OHLCV data
            features: Pre-calculated features including technical indicators

        Returns:
            List of signals with regime-adapted parameters
        """
        if not self.validate_inputs(market_data, features):
            return []

        if len(market_data) < self.lookback_period:
            return []

        signals = []

        current_volatility = self._calculate_current_volatility(market_data)
        self.volatility_history.append(current_volatility)

        if len(self.volatility_history) > 200:
            self.volatility_history.pop(0)

        if len(self.volatility_history) >= 100 and not self.hmm_model.fitted:
            self._fit_regime_model()

        if self.hmm_model.fitted and len(self.volatility_history) >= self.regime_lookback:
            regime_probs = self._predict_current_regime()
            self.current_regime = 0 if regime_probs[0] > regime_probs[1] else 1
            self.regime_confidence = max(regime_probs)

            if self.regime_confidence < self.min_regime_confidence:
                return []

            entry_signal = self._evaluate_entry_conditions(market_data, features)
            if entry_signal:
                adapted_signal = self._adapt_signal_to_regime(entry_signal, market_data)
                if adapted_signal:
                    signals.append(adapted_signal)

        return signals

    def _calculate_current_volatility(self, market_data: pd.DataFrame) -> float:
        """Calculate current realized volatility from recent returns."""
        try:
            from src.features.statistical_models import calculate_realized_volatility

            closes = market_data['close'].tail(self.lookback_period + 1).values
            returns = np.diff(closes) / closes[:-1]

            if len(returns) < 2:
                return 0.01

            volatility = calculate_realized_volatility(returns, window=min(len(returns), self.lookback_period))
            current_vol = volatility[-1] if len(volatility) > 0 and not np.isnan(volatility[-1]) else 0.01

            return max(current_vol, 0.001)

        except Exception as e:
            closes = market_data['close'].tail(self.lookback_period + 1).values
            if len(closes) < 2:
                return 0.01
            returns = np.diff(closes) / closes[:-1]
            return np.std(returns) * np.sqrt(252) if len(returns) > 0 else 0.01

    def _fit_regime_model(self):
        """Fit HMM to accumulated volatility history."""
        try:
            fit_results = self.hmm_model.fit(
                self.volatility_history,
                max_iterations=100,
                tolerance=1e-4
            )
        except Exception as e:
            pass

    def _predict_current_regime(self) -> np.ndarray:
        """Predict current regime probabilities from recent volatility."""
        recent_vol = self.volatility_history[-self.regime_lookback:]
        try:
            regime_probs = self.hmm_model.predict_state(recent_vol)
            return regime_probs
        except Exception as e:
            return np.array([0.5, 0.5])

    def _evaluate_entry_conditions(self, market_data: pd.DataFrame, features: Dict) -> Optional[Dict]:
        """Evaluate basic entry conditions using technical indicators."""
        if 'rsi' not in features or 'macd_histogram' not in features:
            return None

        rsi = features['rsi']
        macd_hist = features['macd_histogram']
        current_price = market_data['close'].iloc[-1]

        entry_threshold = self.low_vol_entry_threshold if self.current_regime == 0 else self.high_vol_entry_threshold

        signal_dict = None

        if rsi < (30 + entry_threshold * 10) and macd_hist > 0:
            signal_dict = {
                'direction': 'LONG',
                'price': current_price,
                'rsi': rsi,
                'macd_histogram': macd_hist,
                'signal_strength': abs(30 - rsi) / 30
            }
        elif rsi > (70 - entry_threshold * 10) and macd_hist < 0:
            signal_dict = {
                'direction': 'SHORT',
                'price': current_price,
                'rsi': rsi,
                'macd_histogram': macd_hist,
                'signal_strength': abs(rsi - 70) / 30
            }

        return signal_dict

    def _adapt_signal_to_regime(self, signal_dict: Dict, market_data: pd.DataFrame) -> Optional[Signal]:
        """Adapt signal parameters based on current volatility regime."""
        symbol = market_data['symbol'].iloc[-1] if 'symbol' in market_data.columns else 'UNKNOWN'
        current_time = market_data['time'].iloc[-1]
        current_price = signal_dict['price']
        direction = signal_dict['direction']

        atr = (market_data['high'].tail(14) - market_data['low'].tail(14)).mean()

        stop_multiplier = self.low_vol_stop_multiplier if self.current_regime == 0 else self.high_vol_stop_multiplier

        if direction == 'LONG':
            stop_loss = current_price - (atr * stop_multiplier)
            take_profit = current_price + (atr * stop_multiplier * 2.0)
        else:
            stop_loss = current_price + (atr * stop_multiplier)
            take_profit = current_price - (atr * stop_multiplier * 2.0)

        base_sizing_level = 3
        if self.current_regime == 0:
            if self.regime_confidence > 0.85:
                adjusted_sizing = min(base_sizing_level + 1, 5)
            else:
                adjusted_sizing = base_sizing_level
        else:
            if self.regime_confidence > 0.85:
                adjusted_sizing = max(base_sizing_level - 1, 1)
            else:
                adjusted_sizing = base_sizing_level

        metadata = {
            'regime': 'LOW_VOLATILITY' if self.current_regime == 0 else 'HIGH_VOLATILITY',
            'regime_confidence': float(self.regime_confidence),
            'current_volatility': float(self.volatility_history[-1]),
            'entry_threshold_used': float(self.low_vol_entry_threshold if self.current_regime == 0 else self.high_vol_entry_threshold),
            'stop_multiplier_used': float(stop_multiplier),
            'rsi': float(signal_dict['rsi']),
            'macd_histogram': float(signal_dict['macd_histogram']),
            'signal_strength': float(signal_dict['signal_strength']),
            'strategy_version': '1.0'
        }

        signal = Signal(
            timestamp=current_time,
            symbol=symbol,
            strategy_name=self.name,
            direction=direction,
            entry_price=float(current_price),
            stop_loss=float(stop_loss),
            take_profit=float(take_profit),
            sizing_level=adjusted_sizing,
            metadata=metadata
        )

        return signal

