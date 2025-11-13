"""
Test suite for VolatilityRegimeAdaptation strategy
Validates regime detection and parameter adaptation logic
"""

import unittest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from src.strategies.volatility_regime_adaptation import VolatilityRegimeAdaptation
from src.strategies.strategy_base import Signal


class TestVolatilityRegimeAdaptation(unittest.TestCase):
    """Test cases for VolatilityRegimeAdaptation strategy"""

    def setUp(self):
        """Initialize strategy with standard configuration before each test"""
        self.config = {
            'lookback_period': 20,
            'regime_lookback': 50,
            'low_vol_entry_threshold': 1.5,
            'high_vol_entry_threshold': 2.5,
            'low_vol_stop_multiplier': 1.5,
            'high_vol_stop_multiplier': 2.5,
            'low_vol_sizing_boost': 1.2,
            'high_vol_sizing_reduction': 0.7,
            'min_regime_confidence': 0.7
        }
        self.strategy = VolatilityRegimeAdaptation(self.config)

        base_time = datetime(2025, 11, 1, 9, 0, 0)
        
        data_points = []
        for i in range(150):
            time_point = base_time + timedelta(minutes=i)
            base_price = 1.1000
            
            if i < 75:
                price_change = np.random.normal(0, 0.0001)
            else:
                price_change = np.random.normal(0, 0.0005)
            
            price = base_price + (i * 0.00001) + price_change
            
            data_points.append({
                'time': time_point,
                'symbol': 'EURUSD.pro',
                'open': price - 0.0001,
                'high': price + 0.0002,
                'low': price - 0.0002,
                'close': price,
                'volume': np.random.randint(1000, 5000)
            })

        self.market_data = pd.DataFrame(data_points)

    def test_initialization(self):
        """Test strategy initializes correctly with configuration parameters"""
        self.assertEqual(self.strategy.name, 'VolatilityRegimeAdaptation')
        self.assertEqual(self.strategy.lookback_period, 20)
        self.assertEqual(self.strategy.regime_lookback, 50)
        self.assertEqual(self.strategy.low_vol_entry_threshold, 1.5)
        self.assertEqual(self.strategy.high_vol_entry_threshold, 2.5)
        self.assertEqual(self.strategy.low_vol_stop_multiplier, 1.5)
        self.assertEqual(self.strategy.high_vol_stop_multiplier, 2.5)
        self.assertEqual(self.strategy.min_regime_confidence, 0.7)
        self.assertIsNotNone(self.strategy.hmm_model)
        self.assertIsInstance(self.strategy.volatility_history, list)
        self.assertEqual(len(self.strategy.volatility_history), 0)

    def test_calculate_current_volatility(self):
        """Test volatility calculation from recent price data"""
        volatility = self.strategy._calculate_current_volatility(self.market_data)
        
        self.assertIsInstance(volatility, float)
        self.assertGreater(volatility, 0.0)
        self.assertLess(volatility, 1.0)

    def test_volatility_history_accumulation(self):
        """Test volatility history accumulates correctly over time"""
        features = {'rsi': 50.0, 'macd_histogram': 0.0}
        
        for i in range(30):
            data_slice = self.market_data.head(20 + i)
            self.strategy.evaluate(data_slice, features)
        
        self.assertGreater(len(self.strategy.volatility_history), 0)
        self.assertLessEqual(len(self.strategy.volatility_history), 200)

    def test_regime_model_fitting(self):
        """Test HMM model fits when sufficient history available"""
        features = {'rsi': 50.0, 'macd_histogram': 0.0}
        
        for i in range(120):
            data_slice = self.market_data.head(20 + i)
            self.strategy.evaluate(data_slice, features)
        
        self.assertTrue(self.strategy.hmm_model.fitted)

    def test_regime_prediction(self):
        """Test regime prediction returns valid probabilities"""
        for i in range(100):
            vol = 0.01 if i < 50 else 0.03
            self.strategy.volatility_history.append(vol)
        
        self.strategy._fit_regime_model()
        
        if self.strategy.hmm_model.fitted:
            regime_probs = self.strategy._predict_current_regime()
            
            self.assertIsInstance(regime_probs, np.ndarray)
            self.assertEqual(len(regime_probs), 2)
            self.assertAlmostEqual(np.sum(regime_probs), 1.0, places=5)
            self.assertTrue(all(0 <= p <= 1 for p in regime_probs))

    def test_evaluate_insufficient_data(self):
        """Test evaluate returns empty list with insufficient data"""
        short_data = self.market_data.head(10)
        features = {'rsi': 50.0, 'macd_histogram': 0.0}
        
        signals = self.strategy.evaluate(short_data, features)
        
        self.assertIsInstance(signals, list)
        self.assertEqual(len(signals), 0)

    def test_signal_generation_with_regime(self):
        """Test signal generation includes regime metadata"""
        for i in range(120):
            data_slice = self.market_data.head(20 + i)
            vol = self.strategy._calculate_current_volatility(data_slice)
            self.strategy.volatility_history.append(vol)
        
        self.strategy._fit_regime_model()
        
        features = {
            'rsi': 25.0,
            'macd_histogram': 0.5
        }
        
        signals = self.strategy.evaluate(self.market_data, features)
        
        if len(signals) > 0:
            signal = signals[0]
            self.assertIsInstance(signal, Signal)
            self.assertIn('regime', signal.metadata)
            self.assertIn(signal.metadata['regime'], ['LOW_VOLATILITY', 'HIGH_VOLATILITY'])
            self.assertIn('regime_confidence', signal.metadata)
            self.assertIn('current_volatility', signal.metadata)
            self.assertIn('entry_threshold_used', signal.metadata)
            self.assertIn('stop_multiplier_used', signal.metadata)


if __name__ == '__main__':
    unittest.main()
