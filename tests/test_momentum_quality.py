"""
Test suite for MomentumQuality strategy
Validates momentum quality evaluation and confluence analysis
"""

import unittest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from src.strategies.momentum_quality import MomentumQuality
from src.strategies.strategy_base import Signal


class TestMomentumQuality(unittest.TestCase):
    """Test cases for MomentumQuality strategy"""

    def setUp(self):
        """Initialize strategy with standard configuration before each test"""
        self.config = {
            'momentum_period': 14,
            'price_threshold': 0.5,
            'volume_threshold': 1.5,
            'vpin_threshold': 0.60,
            'min_quality_score': 0.70,
            'lookback_window': 20,
            'use_regime_filter': True
        }
        self.strategy = MomentumQuality(self.config)

        base_time = datetime(2025, 11, 1, 9, 0, 0)
        
        data_points = []
        base_price = 1.1000
        
        for i in range(50):
            time_point = base_time + timedelta(minutes=i)
            
            if i < 20:
                price = base_price + (i * 0.00002)
                volume = 2000 + np.random.randint(-200, 200)
            else:
                price = base_price + (20 * 0.00002) + ((i - 20) * 0.0005)
                volume = 4000 + np.random.randint(-300, 300)
            
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
        """Test strategy initializes correctly with configuration parameters"""
        self.assertEqual(self.strategy.name, 'MomentumQuality')
        self.assertEqual(self.strategy.momentum_period, 14)
        self.assertEqual(self.strategy.price_threshold, 0.5)
        self.assertEqual(self.strategy.volume_threshold, 1.5)
        self.assertEqual(self.strategy.vpin_threshold, 0.60)
        self.assertEqual(self.strategy.min_quality_score, 0.70)
        self.assertEqual(self.strategy.lookback_window, 20)
        self.assertTrue(self.strategy.use_regime_filter)

    def test_momentum_analysis_calculation(self):
        """Test momentum quality analysis calculates all components"""
        features = {
            'vpin': 0.70,
            'order_flow_imbalance': 0.35
        }
        
        analysis = self.strategy._analyze_momentum_quality(self.market_data, features)
        
        self.assertIsNotNone(analysis)
        self.assertIn('direction', analysis)
        self.assertIn('price_change_pct', analysis)
        self.assertIn('price_strength', analysis)
        self.assertIn('volume_confirmation', analysis)
        self.assertIn('flow_confirmation', analysis)
        self.assertIn('quality_score', analysis)
        
        self.assertIn(analysis['direction'], [-1, 1])
        self.assertIsInstance(analysis['quality_score'], float)
        self.assertGreaterEqual(analysis['quality_score'], 0.0)
        self.assertLessEqual(analysis['quality_score'], 1.0)

    def test_momentum_below_threshold(self):
        """Test strategy rejects momentum below price threshold"""
        flat_data = self.market_data.copy()
        flat_data['close'] = 1.1000
        
        features = {'vpin': 0.70, 'order_flow_imbalance': 0.35}
        
        analysis = self.strategy._analyze_momentum_quality(flat_data, features)
        
        self.assertIsNone(analysis)

    def test_swing_point_identification(self):
        """Test identification of recent swing points"""
        swing_points = self.strategy._identify_recent_swing_points(self.market_data)
        
        self.assertIsInstance(swing_points, dict)
        self.assertIn('swing_high', swing_points)
        self.assertIn('swing_low', swing_points)

    def test_evaluate_insufficient_data(self):
        """Test evaluate returns empty list with insufficient data"""
        short_data = self.market_data.head(10)
        features = {'vpin': 0.70, 'order_flow_imbalance': 0.35}
        
        signals = self.strategy.evaluate(short_data, features)
        
        self.assertIsInstance(signals, list)
        self.assertEqual(len(signals), 0)

    def test_quality_score_weighting(self):
        """Test quality score correctly weights components"""
        features = {
            'vpin': 0.75,
            'order_flow_imbalance': 0.40
        }
        
        analysis = self.strategy._analyze_momentum_quality(self.market_data, features)
        
        if analysis:
            expected_score = (analysis['price_strength'] * 0.4) + \
                           (analysis['volume_confirmation'] * 0.3) + \
                           (analysis['flow_confirmation'] * 0.3)
            
            self.assertAlmostEqual(analysis['quality_score'], expected_score, places=5)

    def test_signal_generation_with_high_quality(self):
        """Test signal generation includes quality score metadata"""
        features = {
            'vpin': 0.80,
            'order_flow_imbalance': 0.45
        }
        
        signals = self.strategy.evaluate(self.market_data, features)
        
        if len(signals) > 0:
            signal = signals[0]
            self.assertIsInstance(signal, Signal)
            self.assertIn(signal.direction, ['LONG', 'SHORT'])
            self.assertEqual(signal.strategy_name, 'MomentumQuality')
            self.assertIn('quality_score', signal.metadata)
            self.assertIn('price_strength', signal.metadata)
            self.assertIn('volume_confirmation', signal.metadata)
            self.assertIn('flow_confirmation', signal.metadata)
            self.assertGreaterEqual(signal.metadata['quality_score'], self.strategy.min_quality_score)


if __name__ == '__main__':
    unittest.main()
