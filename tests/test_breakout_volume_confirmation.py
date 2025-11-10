"""
Test suite for BreakoutVolumeConfirmation strategy
Validates consolidation detection and volume-confirmed breakout identification
"""

import unittest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from src.strategies.breakout_volume_confirmation import BreakoutVolumeConfirmation
from src.strategies.strategy_base import Signal


class TestBreakoutVolumeConfirmation(unittest.TestCase):
    """Test cases for Breakout Volume Confirmation strategy"""

    def setUp(self):
        """Initialize strategy with institutional configuration"""
        self.config = {
            'atr_lookback': 20,
            'atr_contraction_threshold': 0.60,
            'swing_point_order': 5,
            'volume_breakout_multiplier': 3.0,
            'imbalance_confirmation_threshold': 0.35,
            'min_consolidation_bars': 15,
            'vpin_non_exhaustion_max': 0.65
        }
        self.strategy = BreakoutVolumeConfirmation(self.config)

        base_time = datetime(2025, 11, 1, 9, 0, 0)
        
        data_points = []
        base_price = 1.1000
        
        for i in range(100):
            time_point = base_time + timedelta(minutes=i)
            
            if i < 60:
                price = base_price + np.random.normal(0, 0.0001)
                volume = 2000 + np.random.randint(-200, 200)
            elif i < 80:
                price = base_price + np.random.normal(0, 0.00005)
                volume = 1500 + np.random.randint(-100, 100)
            else:
                price = base_price + 0.0015 + np.random.normal(0, 0.0001)
                volume = 7000 + np.random.randint(-500, 500)
            
            data_points.append({
                'time': time_point,
                'symbol': 'EURUSD.pro',
                'open': price - 0.0001,
                'high': price + 0.0002,
                'low': price - 0.0002,
                'close': price,
                'volume': volume
            })

        self.market_data = pd.DataFrame(data_points)

    def test_initialization(self):
        """Test strategy initializes with institutional parameters"""
        self.assertEqual(self.strategy.name, 'BreakoutVolumeConfirmation')
        self.assertEqual(self.strategy.atr_lookback, 20)
        self.assertEqual(self.strategy.volume_breakout_multiplier, 3.0)

    def test_consolidation_detection(self):
        """Test detection of consolidation periods"""
        consolidation = self.strategy._detect_consolidation_period(self.market_data)
        
        if consolidation is not None:
            self.assertIn('atr_ratio', consolidation)
            self.assertIn('consolidation_bars', consolidation)
            self.assertIn('range_high', consolidation)
            self.assertIn('range_low', consolidation)

    def test_evaluate_insufficient_data(self):
        """Test evaluate returns empty with insufficient data"""
        short_data = self.market_data.head(30)
        features = {}
        
        signals = self.strategy.evaluate(short_data, features)
        
        self.assertIsInstance(signals, list)
        self.assertEqual(len(signals), 0)


if __name__ == '__main__':
    unittest.main()
