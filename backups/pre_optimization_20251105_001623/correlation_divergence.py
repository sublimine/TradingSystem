"""
Correlation Divergence Strategy - Institutional Implementation

Detects temporary breakdowns in correlation between normally related instruments,
identifying mean reversion opportunities when historical relationships deviate.
Uses statistical correlation analysis and relative strength measurement.
"""

import numpy as np
import pandas as pd
from typing import List, Dict, Optional
from datetime import datetime
from .strategy_base import StrategyBase, Signal


class CorrelationDivergence(StrategyBase):
    """
    Institutional pairs divergence strategy using correlation breakdown detection.
    
    Monitors instrument pairs with strong historical correlation, identifies temporary
    divergences when correlation drops significantly, determines which instrument is
    outlier through relative strength analysis, and enters anticipating convergence.
    """

    def __init__(self, config: Dict):
        """
        Initialize correlation divergence strategy.

        Required config parameters:
            - monitored_pairs: List of correlated pairs to monitor
            - correlation_lookback: Period for correlation calculation (typically 100)
            - historical_correlation_min: Minimum historical correlation (typically 0.80)
            - divergence_correlation_threshold: Correlation indicating divergence (typically 0.50)
            - relative_strength_lookback: Period for RS calculation (typically 20)
            - min_divergence_magnitude: Minimum divergence in percentage (typically 1.5)
            - convergence_confidence_threshold: Confidence for entry (typically 0.70)
        """
        super().__init__(config)

        self.monitored_pairs = config.get('monitored_pairs', [])
        self.correlation_lookback = config.get('correlation_lookback', 100)
        self.historical_correlation_min = config.get('historical_correlation_min', 0.80)
        self.divergence_correlation_threshold = config.get('divergence_correlation_threshold', 0.50)
        self.relative_strength_lookback = config.get('relative_strength_lookback', 20)
        self.min_divergence_magnitude = config.get('min_divergence_magnitude', 1.5)
        self.convergence_confidence_threshold = config.get('convergence_confidence_threshold', 0.70)

        self.correlation_cache = {}

    def evaluate(self, market_data: pd.DataFrame, features: Dict) -> List[Signal]:
        """
        Evaluate correlated pairs for divergence opportunities.

        Args:
            market_data: Recent OHLCV data for multiple instruments
            features: Pre-calculated features (minimal use for this strategy)

        Returns:
            List of signals for correlation divergence trades
        """
        if not self.validate_inputs(market_data, features):
            return []

        signals = []

        for pair in self.monitored_pairs:
            symbol_a, symbol_b = pair

            data_a = self._extract_instrument_data(market_data, symbol_a)
            data_b = self._extract_instrument_data(market_data, symbol_b)

            if data_a is None or data_b is None:
                continue

            if len(data_a) < self.correlation_lookback or len(data_b) < self.correlation_lookback:
                continue

            divergence_analysis = self._analyze_correlation_divergence(data_a, data_b, symbol_a, symbol_b)

            if divergence_analysis is None:
                continue

            if divergence_analysis['divergence_detected']:
                signal = self._generate_divergence_signal(data_a, data_b, divergence_analysis)
                if signal:
                    signals.append(signal)

        return signals

    def _extract_instrument_data(self, market_data: pd.DataFrame, symbol: str) -> Optional[pd.DataFrame]:
        """Extract data for specific instrument."""
        if 'symbol' not in market_data.columns:
            return None

        instrument_data = market_data[market_data['symbol'] == symbol].copy()

        if len(instrument_data) == 0:
            return None

        return instrument_data.sort_values('time').reset_index(drop=True)

    def _analyze_correlation_divergence(self, data_a: pd.DataFrame, data_b: pd.DataFrame,
                                       symbol_a: str, symbol_b: str) -> Optional[Dict]:
        """Analyze correlation breakdown between instrument pair."""
        closes_a = data_a['close'].tail(self.correlation_lookback).values
        closes_b = data_b['close'].tail(self.correlation_lookback).values

        if len(closes_a) != len(closes_b):
            return None

        historical_correlation = np.corrcoef(closes_a, closes_b)[0, 1]

        if historical_correlation < self.historical_correlation_min:
            return None

        recent_closes_a = closes_a[-self.relative_strength_lookback:]
        recent_closes_b = closes_b[-self.relative_strength_lookback:]

        current_correlation = np.corrcoef(recent_closes_a, recent_closes_b)[0, 1]

        divergence_detected = current_correlation < self.divergence_correlation_threshold

        if not divergence_detected:
            return None

        performance_a = ((recent_closes_a[-1] - recent_closes_a[0]) / recent_closes_a[0]) * 100
        performance_b = ((recent_closes_b[-1] - recent_closes_b[0]) / recent_closes_b[0]) * 100

        divergence_magnitude = abs(performance_a - performance_b)

        if divergence_magnitude < self.min_divergence_magnitude:
            return None

        if performance_a > performance_b:
            strong_instrument = symbol_a
            weak_instrument = symbol_b
            strong_performance = performance_a
            weak_performance = performance_b
        else:
            strong_instrument = symbol_b
            weak_instrument = symbol_a
            strong_performance = performance_b
            weak_performance = performance_a

        analysis = {
            'divergence_detected': True,
            'historical_correlation': float(historical_correlation),
            'current_correlation': float(current_correlation),
            'correlation_drop': float(historical_correlation - current_correlation),
            'strong_instrument': strong_instrument,
            'weak_instrument': weak_instrument,
            'strong_performance': float(strong_performance),
            'weak_performance': float(weak_performance),
            'divergence_magnitude': float(divergence_magnitude),
            'current_price_a': float(data_a['close'].iloc[-1]),
            'current_price_b': float(data_b['close'].iloc[-1]),
            'timestamp': data_a['time'].iloc[-1]
        }

        return analysis

    def _generate_divergence_signal(self, data_a: pd.DataFrame, data_b: pd.DataFrame,
                                   analysis: Dict) -> Optional[Signal]:
        """Generate pair trade signal anticipating correlation convergence."""
        strong_instrument = analysis['strong_instrument']
        weak_instrument = analysis['weak_instrument']

        strong_data = data_a if data_a['symbol'].iloc[0] == strong_instrument else data_b
        weak_data = data_b if data_b['symbol'].iloc[0] == weak_instrument else data_a

        atr_strong = (strong_data['high'].tail(14) - strong_data['low'].tail(14)).mean()
        atr_weak = (weak_data['high'].tail(14) - weak_data['low'].tail(14)).mean()

        correlation_drop = analysis['correlation_drop']
        divergence_magnitude = analysis['divergence_magnitude']

        if correlation_drop >= 0.40 and divergence_magnitude >= 2.5:
            sizing_level = 3
        elif correlation_drop >= 0.30 and divergence_magnitude >= 2.0:
            sizing_level = 2
        else:
            sizing_level = 1

        symbol = f"{strong_instrument}/{weak_instrument}"
        current_time = analysis['timestamp']
        entry_price = analysis['current_price_a']

        stop_loss = entry_price + (atr_strong * 2.0)
        take_profit = entry_price - (divergence_magnitude / 100 * entry_price * 0.6)

        metadata = {
            'pair_structure': 'SHORT_strong_LONG_weak',
            'strong_instrument': strong_instrument,
            'weak_instrument': weak_instrument,
            'strong_performance_pct': analysis['strong_performance'],
            'weak_performance_pct': analysis['weak_performance'],
            'historical_correlation': analysis['historical_correlation'],
            'current_correlation': analysis['current_correlation'],
            'correlation_drop': correlation_drop,
            'divergence_magnitude_pct': divergence_magnitude,
            'convergence_target': 'historical_mean',
            'strategy_version': '1.0'
        }

        signal = Signal(
            timestamp=current_time,
            symbol=symbol,
            strategy_name=self.name,
            direction='SHORT',
            entry_price=float(entry_price),
            stop_loss=float(stop_loss),
            take_profit=float(take_profit),
            sizing_level=sizing_level,
            metadata=metadata
        )

        return signal
