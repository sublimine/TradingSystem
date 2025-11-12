"""
Kalman Filter Pairs Trading Strategy

Implements statistical pairs trading using Kalman Filter for dynamic spread estimation.
Generates signals when spread deviates significantly from estimated equilibrium.
"""

import numpy as np
import pandas as pd
from typing import List, Dict, Optional, Tuple
from datetime import datetime
from .strategy_base import StrategyBase, Signal


class KalmanPairsTrading(StrategyBase):
    """
    Pairs trading strategy using Kalman Filter for adaptive spread tracking.
    
    Monitors correlated instrument pairs, estimates dynamic spread mean via Kalman Filter,
    and enters mean-reversion trades when spread deviates beyond threshold.
    """

    def __init__(self, config: Dict):
        """
        Initialize Kalman pairs trading strategy.

        Required config parameters:
            - monitored_pairs: List of tuples [(symbol_y, symbol_x), ...]
            - z_score_entry_threshold: Z-score for entry (typically 2.0)
            - z_score_exit_threshold: Z-score for exit (typically 0.5)
            - kalman_process_variance: Process noise Q (typically 0.001)
            - kalman_measurement_variance: Measurement noise R (typically 0.01)
            - min_correlation: Minimum historical correlation (typically 0.75)
            - lookback_period: Period for correlation calculation (typically 200)
        """
        super().__init__(config)

        self.monitored_pairs = config.get('monitored_pairs', [])
        self.z_entry_threshold = config.get('z_score_entry_threshold', 1.5)
        self.z_exit_threshold = config.get('z_score_exit_threshold', 0.5)
        self.process_variance = config.get('kalman_process_variance', 0.001)
        self.measurement_variance = config.get('kalman_measurement_variance', 0.01)
        self.min_correlation = config.get('min_correlation', 0.70)
        self.lookback_period = config.get('lookback_period', 150)

        self.kalman_filters = {}
        self.hedge_ratios = {}
        self.correlation_cache = {}

        self._initialize_filters()

    def _initialize_filters(self):
        """Initialize Kalman Filter instance for each monitored pair."""
        try:
            from src.features.statistical_models import KalmanPairsFilter
            
            for pair in self.monitored_pairs:
                pair_key = f"{pair[0]}_{pair[1]}"
                self.kalman_filters[pair_key] = KalmanPairsFilter(
                    process_variance=self.process_variance,
                    measurement_variance=self.measurement_variance
                )
                self.hedge_ratios[pair_key] = None
                self.correlation_cache[pair_key] = None
        except ImportError:
            raise ImportError("KalmanPairsFilter not found in statistical_models module")

    def evaluate(self, market_data: pd.DataFrame, features: Dict) -> List[Signal]:
        """
        Evaluate pairs for mean-reversion opportunities.

        Args:
            market_data: Recent OHLCV data containing both instruments of each pair
            features: Pre-calculated features (not heavily used in this strategy)

        Returns:
            List of pair trade signals generated
        """
        if not self.validate_inputs(market_data, features):
            return []

        signals = []

        for pair in self.monitored_pairs:
            symbol_y, symbol_x = pair
            pair_key = f"{symbol_y}_{symbol_x}"

            pair_data_y = self._extract_symbol_data(market_data, symbol_y)
            pair_data_x = self._extract_symbol_data(market_data, symbol_x)

            if pair_data_y is None or pair_data_x is None:
                continue

            if len(pair_data_y) < self.lookback_period or len(pair_data_x) < self.lookback_period:
                continue

            correlation = self._calculate_correlation(pair_data_y, pair_data_x, pair_key)
            if correlation < self.min_correlation:
                continue

            hedge_ratio = self._calculate_hedge_ratio(pair_data_y, pair_data_x, pair_key)
            if hedge_ratio is None:
                continue

            spread = self._calculate_spread(pair_data_y, pair_data_x, hedge_ratio)
            current_spread = spread.iloc[-1]

            kalman_filter = self.kalman_filters[pair_key]
            kalman_filter.update(current_spread)

            estimated_mean = kalman_filter.get_estimated_mean()
            estimated_std = np.sqrt(kalman_filter.get_estimation_uncertainty())

            z_score = (current_spread - estimated_mean) / estimated_std if estimated_std > 0 else 0.0

            if abs(z_score) >= self.z_entry_threshold:
                signal = self._generate_pairs_signal(
                    pair_data_y, pair_data_x, symbol_y, symbol_x,
                    z_score, hedge_ratio, estimated_mean, estimated_std
                )
                if signal:
                    signals.append(signal)

        return signals

    def _extract_symbol_data(self, market_data: pd.DataFrame, symbol: str) -> Optional[pd.DataFrame]:
        """Extract data for specific symbol from market data."""
        if 'symbol' not in market_data.columns:
            return None

        symbol_data = market_data[market_data['symbol'] == symbol].copy()
        
        if len(symbol_data) == 0:
            return None

        return symbol_data.sort_values('time').reset_index(drop=True)

    def _calculate_correlation(self, data_y: pd.DataFrame, data_x: pd.DataFrame, pair_key: str) -> float:
        """Calculate rolling correlation between two instruments."""
        if self.correlation_cache.get(pair_key) is not None:
            return self.correlation_cache[pair_key]

        prices_y = data_y['close'].tail(self.lookback_period).values
        prices_x = data_x['close'].tail(self.lookback_period).values

        if len(prices_y) != len(prices_x):
            return 0.0

        correlation = np.corrcoef(prices_y, prices_x)[0, 1]
        self.correlation_cache[pair_key] = correlation

        return correlation

    def _calculate_hedge_ratio(self, data_y: pd.DataFrame, data_x: pd.DataFrame, pair_key: str) -> Optional[float]:
        """Calculate hedge ratio using linear regression."""
        try:
            from src.features.statistical_models import estimate_hedge_ratio

            prices_y = data_y['close'].tail(self.lookback_period).values
            prices_x = data_x['close'].tail(self.lookback_period).values

            if len(prices_y) != len(prices_x) or len(prices_y) < 50:
                return None

            result = estimate_hedge_ratio(prices_y, prices_x, use_log_prices=False)
            hedge_ratio = result['beta']

            self.hedge_ratios[pair_key] = hedge_ratio

            return hedge_ratio

        except Exception as e:
            return None

    def _calculate_spread(self, data_y: pd.DataFrame, data_x: pd.DataFrame, hedge_ratio: float) -> pd.Series:
        """Calculate synthetic spread between pair."""
        try:
            from src.features.statistical_models import calculate_spread

            prices_y = data_y['close'].values
            prices_x = data_x['close'].values

            min_length = min(len(prices_y), len(prices_x))
            prices_y = prices_y[-min_length:]
            prices_x = prices_x[-min_length:]

            spread = calculate_spread(prices_y, prices_x, hedge_ratio)

            return pd.Series(spread)

        except Exception as e:
            prices_y = data_y['close'].values
            prices_x = data_x['close'].values
            min_length = min(len(prices_y), len(prices_x))
            spread = prices_y[-min_length:] - (hedge_ratio * prices_x[-min_length:])
            return pd.Series(spread)

    def _generate_pairs_signal(self, data_y: pd.DataFrame, data_x: pd.DataFrame,
                               symbol_y: str, symbol_x: str,
                               z_score: float, hedge_ratio: float,
                               estimated_mean: float, estimated_std: float) -> Optional[Signal]:
        """Generate pair trade signal based on spread divergence."""
        current_time = data_y['time'].iloc[-1]
        price_y = data_y['close'].iloc[-1]
        price_x = data_x['close'].iloc[-1]

        atr_y = (data_y['high'].tail(14) - data_y['low'].tail(14)).mean()
        atr_x = (data_x['high'].tail(14) - data_x['low'].tail(14)).mean()

        if z_score > self.z_entry_threshold:
            direction = 'SHORT'
            leg_y_direction = 'SHORT'
            leg_x_direction = 'LONG'
            
            entry_spread = price_y - (hedge_ratio * price_x)
            stop_spread = estimated_mean + (3.5 * estimated_std)
            target_spread = estimated_mean

            stop_loss_y = price_y + (atr_y * 1.5)
            take_profit_y = price_y - (abs(entry_spread - target_spread))

        elif z_score < -self.z_entry_threshold:
            direction = 'LONG'
            leg_y_direction = 'LONG'
            leg_x_direction = 'SHORT'
            
            entry_spread = price_y - (hedge_ratio * price_x)
            stop_spread = estimated_mean - (3.5 * estimated_std)
            target_spread = estimated_mean

            stop_loss_y = price_y - (atr_y * 1.5)
            take_profit_y = price_y + (abs(entry_spread - target_spread))

        else:
            return None

        metadata = {
            'pair_y': symbol_y,
            'pair_x': symbol_x,
            'hedge_ratio': float(hedge_ratio),
            'z_score': float(z_score),
            'estimated_mean': float(estimated_mean),
            'estimated_std': float(estimated_std),
            'entry_spread': float(entry_spread),
            'target_spread': float(target_spread),
            'stop_spread': float(stop_spread),
            'leg_y_direction': leg_y_direction,
            'leg_x_direction': leg_x_direction,
            'price_y': float(price_y),
            'price_x': float(price_x),
            'strategy_version': '1.0'
        }

        signal = Signal(
            timestamp=current_time,
            symbol=f"{symbol_y}/{symbol_x}",
            strategy_name=self.name,
            direction=direction,
            entry_price=float(price_y),
            stop_loss=float(stop_loss_y),
            take_profit=float(take_profit_y),
            sizing_level=3,
            metadata=metadata
        )

        return signal
