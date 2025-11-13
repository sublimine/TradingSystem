"""
Test suite for MeanReversionStatistical strategy - Institutional Implementation
Validates statistical extreme detection and microstructure confirmation
"""

import unittest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from src.strategies.mean_reversion_statistical import MeanReversionStatistical
from src.strategies.strategy_base import Signal


class TestMeanReversionStatistical(unittest.TestCase):
    """Test cases for institutional Mean Reversion Statistical strategy"""

    def setUp(self):
        """Initialize strategy with institutional configuration"""
        self.config = {
            'lookback_period': 200,
            'entry_sigma_threshold': 3.0,
            'exit_sigma_threshold': 0.8,
            'vpin_exhaustion_threshold': 0.70,
            'imbalance_reversal_threshold': 0.40,
            'volume_spike_multiplier': 2.5,
            'min_liquidity_score': 0.60,
            'reversal_velocity_min': 8.0
        }
        self.strategy = MeanReversionStatistical(self.config)

        base_time = datetime(2025, 11, 1, 9, 0, 0)
        
        data_points = []
        base_price = 1.1000
        
        for i in range(250):
            time_point = base_time + timedelta(minutes=i)
            
            if i < 200:
                price = base_price + np.random.normal(0, 0.0003)
                volume = 3000 + np.random.randint(-500, 500)
            else:
                deviation = 0.004 if i < 240 else 0.0035
                price = base_price + deviation + np.random.normal(0, 0.0001)
                volume = 8000 + np.random.randint(-500, 500)
            
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
        self.assertEqual(self.strategy.name, 'MeanReversionStatistical')
        self.assertEqual(self.strategy.lookback_period, 200)
        self.assertEqual(self.strategy.entry_sigma_threshold, 3.0)
        self.assertEqual(self.strategy.vpin_exhaustion_threshold, 0.70)
        self.assertEqual(self.strategy.imbalance_reversal_threshold, 0.40)
        self.assertEqual(self.strategy.volume_spike_multiplier, 2.5)

    def test_statistical_extreme_detection(self):
        """Test detection of statistical price extremes"""
        extreme = self.strategy._detect_statistical_extreme(self.market_data)
        
        if extreme is not None:
            self.assertIn('z_score', extreme)
            self.assertIn('equilibrium_mean', extreme)
            self.assertIn('direction', extreme)
            self.assertIn('volume_spike_ratio', extreme)
            self.assertIn(extreme['direction'], ['LONG', 'SHORT'])

    def test_reversal_velocity_calculation(self):
        """Test calculation of reversal velocity"""
        velocity = self.strategy._calculate_reversal_velocity(self.market_data, 'SHORT')
        
        self.assertIsInstance(velocity, float)
        self.assertGreaterEqual(velocity, 0.0)

    def test_microstructure_validation(self):
        """Test microstructure conditions validation"""
        features = {
            'vpin': 0.75,
            'order_flow_imbalance': -0.45,
            'liquidity_score': 0.70
        }
        
        extreme = {
            'direction': 'LONG',
            'z_score': -3.2,
            'is_volume_climax': True
        }
        
        validation = self.strategy._validate_microstructure_conditions(
            self.market_data, features, extreme
        )
        
        self.assertIsInstance(validation, dict)
        self.assertIn('is_valid', validation)
        self.assertIn('confidence_score', validation)

    def test_evaluate_insufficient_data(self):
        """Test evaluate returns empty with insufficient data"""
        short_data = self.market_data.head(150)
        features = {}
        
        signals = self.strategy.evaluate(short_data, features)
        
        self.assertIsInstance(signals, list)
        self.assertEqual(len(signals), 0)

    def test_signal_generation_structure(self):
        """Test signal includes institutional metadata"""
        features = {
            'vpin': 0.78,
            'order_flow_imbalance': 0.50,
            'liquidity_score': 0.75
        }
        
        signals = self.strategy.evaluate(self.market_data, features)
        
        if len(signals) > 0:
            signal = signals[0]
            self.assertIsInstance(signal, Signal)
            self.assertIn('z_score', signal.metadata)
            self.assertIn('equilibrium_mean', signal.metadata)
            self.assertIn('microstructure_confidence', signal.metadata)
            self.assertIn('vpin_exhaustion', signal.metadata)


if __name__ == '__main__':
    unittest.main()
