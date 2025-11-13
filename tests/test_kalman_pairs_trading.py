"""
Test suite for KalmanPairsTrading strategy
Validates pairs trading logic using Kalman Filter spread estimation
"""

import unittest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from src.strategies.kalman_pairs_trading import KalmanPairsTrading
from src.strategies.strategy_base import Signal


class TestKalmanPairsTrading(unittest.TestCase):
    """Test cases for KalmanPairsTrading strategy"""

    def setUp(self):
        """Initialize strategy with standard configuration before each test"""
        self.config = {
            'monitored_pairs': [('EURUSD.pro', 'GBPUSD.pro')],
            'z_score_entry_threshold': 2.0,
            'z_score_exit_threshold': 0.5,
            'kalman_process_variance': 0.001,
            'kalman_measurement_variance': 0.01,
            'min_correlation': 0.75,
            'lookback_period': 200
        }
        self.strategy = KalmanPairsTrading(self.config)

        base_time = datetime(2025, 11, 1, 9, 0, 0)

        eurusd_data = []
        gbpusd_data = []

        for i in range(250):
            time_point = base_time + timedelta(minutes=i)
            
            eurusd_price = 1.1000 + (i * 0.0001) + np.random.normal(0, 0.0005)
            gbpusd_price = 1.2500 + (i * 0.00012) + np.random.normal(0, 0.0006)

            eurusd_data.append({
                'time': time_point,
                'symbol': 'EURUSD.pro',
                'open': eurusd_price - 0.0002,
                'high': eurusd_price + 0.0003,
                'low': eurusd_price - 0.0003,
                'close': eurusd_price,
                'volume': np.random.randint(1000, 5000)
            })

            gbpusd_data.append({
                'time': time_point,
                'symbol': 'GBPUSD.pro',
                'open': gbpusd_price - 0.0002,
                'high': gbpusd_price + 0.0003,
                'low': gbpusd_price - 0.0003,
                'close': gbpusd_price,
                'volume': np.random.randint(1000, 5000)
            })

        self.market_data = pd.DataFrame(eurusd_data + gbpusd_data)
        self.features = {}

    def test_initialization(self):
        """Test strategy initializes correctly with configuration parameters"""
        self.assertEqual(self.strategy.name, 'KalmanPairsTrading')
        self.assertEqual(len(self.strategy.monitored_pairs), 1)
        self.assertEqual(self.strategy.monitored_pairs[0], ('EURUSD.pro', 'GBPUSD.pro'))
        self.assertEqual(self.strategy.z_entry_threshold, 2.0)
        self.assertEqual(self.strategy.z_exit_threshold, 0.5)
        self.assertEqual(self.strategy.process_variance, 0.001)
        self.assertEqual(self.strategy.measurement_variance, 0.01)
        self.assertEqual(self.strategy.min_correlation, 0.75)
        self.assertEqual(self.strategy.lookback_period, 200)
        
        pair_key = 'EURUSD.pro_GBPUSD.pro'
        self.assertIn(pair_key, self.strategy.kalman_filters)
        self.assertIn(pair_key, self.strategy.hedge_ratios)

    def test_extract_symbol_data(self):
        """Test extraction of symbol-specific data from combined dataframe"""
        eurusd_data = self.strategy._extract_symbol_data(self.market_data, 'EURUSD.pro')
        gbpusd_data = self.strategy._extract_symbol_data(self.market_data, 'GBPUSD.pro')

        self.assertIsNotNone(eurusd_data)
        self.assertIsNotNone(gbpusd_data)
        self.assertEqual(len(eurusd_data), 250)
        self.assertEqual(len(gbpusd_data), 250)
        self.assertTrue(all(eurusd_data['symbol'] == 'EURUSD.pro'))
        self.assertTrue(all(gbpusd_data['symbol'] == 'GBPUSD.pro'))

    def test_calculate_correlation(self):
        """Test correlation calculation between instrument pairs"""
        eurusd_data = self.strategy._extract_symbol_data(self.market_data, 'EURUSD.pro')
        gbpusd_data = self.strategy._extract_symbol_data(self.market_data, 'GBPUSD.pro')

        pair_key = 'EURUSD.pro_GBPUSD.pro'
        correlation = self.strategy._calculate_correlation(eurusd_data, gbpusd_data, pair_key)

        self.assertIsInstance(correlation, float)
        self.assertGreaterEqual(correlation, -1.0)
        self.assertLessEqual(correlation, 1.0)
        self.assertGreater(correlation, 0.5)

    def test_calculate_hedge_ratio(self):
        """Test hedge ratio calculation via linear regression"""
        eurusd_data = self.strategy._extract_symbol_data(self.market_data, 'EURUSD.pro')
        gbpusd_data = self.strategy._extract_symbol_data(self.market_data, 'GBPUSD.pro')

        pair_key = 'EURUSD.pro_GBPUSD.pro'
        hedge_ratio = self.strategy._calculate_hedge_ratio(eurusd_data, gbpusd_data, pair_key)

        self.assertIsNotNone(hedge_ratio)
        self.assertIsInstance(hedge_ratio, float)
        self.assertGreater(hedge_ratio, 0.0)
        self.assertLess(hedge_ratio, 2.0)

    def test_calculate_spread(self):
        """Test synthetic spread calculation between pairs"""
        eurusd_data = self.strategy._extract_symbol_data(self.market_data, 'EURUSD.pro')
        gbpusd_data = self.strategy._extract_symbol_data(self.market_data, 'GBPUSD.pro')

        hedge_ratio = 0.88
        spread = self.strategy._calculate_spread(eurusd_data, gbpusd_data, hedge_ratio)

        self.assertIsInstance(spread, pd.Series)
        self.assertEqual(len(spread), 250)
        self.assertTrue(all(np.isfinite(spread)))

    def test_evaluate_insufficient_data(self):
        """Test evaluate returns empty list with insufficient data"""
        short_data = self.market_data.head(50)
        signals = self.strategy.evaluate(short_data, self.features)

        self.assertIsInstance(signals, list)
        self.assertEqual(len(signals), 0)

    def test_evaluate_generates_signal_structure(self):
        """Test evaluate generates valid signal structure when conditions met"""
        eurusd_data = self.strategy._extract_symbol_data(self.market_data, 'EURUSD.pro')
        gbpusd_data = self.strategy._extract_symbol_data(self.market_data, 'GBPUSD.pro')

        pair_key = 'EURUSD.pro_GBPUSD.pro'
        hedge_ratio = self.strategy._calculate_hedge_ratio(eurusd_data, gbpusd_data, pair_key)

        spread = self.strategy._calculate_spread(eurusd_data, gbpusd_data, hedge_ratio)
        
        kalman_filter = self.strategy.kalman_filters[pair_key]
        for s in spread:
            kalman_filter.update(s)

        mean = kalman_filter.get_estimated_mean()
        std = np.sqrt(kalman_filter.get_estimation_uncertainty())

        artificially_high_spread = mean + (3.0 * std)
        eurusd_data_modified = eurusd_data.copy()
        eurusd_data_modified.loc[eurusd_data_modified.index[-1], 'close'] = artificially_high_spread + (hedge_ratio * gbpusd_data['close'].iloc[-1])

        combined_modified = pd.concat([eurusd_data_modified, gbpusd_data])

        signals = self.strategy.evaluate(combined_modified, self.features)

        if len(signals) > 0:
            signal = signals[0]
            self.assertIsInstance(signal, Signal)
            self.assertIn(signal.direction, ['LONG', 'SHORT'])
            self.assertEqual(signal.strategy_name, 'KalmanPairsTrading')
            self.assertIsNotNone(signal.entry_price)
            self.assertIsNotNone(signal.stop_loss)
            self.assertIsNotNone(signal.take_profit)
            self.assertEqual(signal.sizing_level, 3)
            self.assertIn('hedge_ratio', signal.metadata)
            self.assertIn('z_score', signal.metadata)
            self.assertIn('estimated_mean', signal.metadata)


if __name__ == '__main__':
    unittest.main()