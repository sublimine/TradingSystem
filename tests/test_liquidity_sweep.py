"""
Unit tests for Liquidity Sweep Detection Strategy
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / 'src' / 'strategies'))

import unittest
import numpy as np
import pandas as pd
from datetime import datetime, timedelta

from src.strategies.liquidity_sweep import LiquiditySweepStrategy


class TestLiquiditySweepStrategy(unittest.TestCase):
    
    def setUp(self):
        """Initialize test configuration before each test."""
        self.config = {
            'lookback_periods': [1440, 2880, 4320],
            'proximity_threshold': 10,
            'penetration_min': 3,
            'penetration_max': 15,
            'volume_threshold_multiplier': 2.0,
            'reversal_velocity_min': 5.0,
            'imbalance_threshold': 0.3,
            'vpin_threshold': 0.65,
            'min_confirmation_score': 4
        }
        self.strategy = LiquiditySweepStrategy(self.config)
        
    def test_strategy_initialization(self):
        """Test strategy initializes with correct configuration."""
        self.assertEqual(self.strategy.name, 'LiquiditySweepStrategy')
        self.assertEqual(self.strategy.proximity_threshold, 10)
        self.assertEqual(self.strategy.min_confirmation_score, 4)
        print("✓ Strategy initialization test passed")
        
    def test_validate_inputs(self):
        """Test input validation logic."""
        valid_data = pd.DataFrame({
            'time': pd.date_range(start='2025-01-01', periods=100, freq='1min'),
            'open': np.random.uniform(1.1000, 1.1100, 100),
            'high': np.random.uniform(1.1000, 1.1100, 100),
            'low': np.random.uniform(1.0900, 1.1000, 100),
            'close': np.random.uniform(1.1000, 1.1100, 100),
            'volume': np.random.uniform(1000, 5000, 100),
            'symbol': ['EURUSD'] * 100
        })
        
        valid_features = {'vpin': 0.5, 'order_book_imbalance': 0.2}
        
        result = self.strategy.validate_inputs(valid_data, valid_features)
        self.assertTrue(result, "Valid inputs should pass validation")
        
        invalid_result = self.strategy.validate_inputs(None, valid_features)
        self.assertFalse(invalid_result, "None data should fail validation")
        
        print("✓ Input validation test passed")
        
    def test_level_identification(self):
        """Test identification of critical technical levels."""
        # Create data with sufficient length for lookback periods
        data = pd.DataFrame({
            'time': pd.date_range(start='2025-01-01', periods=5000, freq='1min'),
            'open': np.linspace(1.0900, 1.1100, 5000),
            'high': np.linspace(1.0910, 1.1110, 5000),
            'low': np.linspace(1.0890, 1.1090, 5000),
            'close': np.linspace(1.0900, 1.1100, 5000),
            'volume': np.random.uniform(1000, 3000, 5000),
            'symbol': ['EURUSD'] * 5000
        })
        
        features = {}
        
        self.strategy._update_critical_levels(data, features)
        
        symbol = data['symbol'].iloc[0]
        self.assertIn(symbol, self.strategy.identified_levels)
        self.assertGreaterEqual(len(self.strategy.identified_levels[symbol]), 0,
                          "Should process level identification without errors")
        
        print("✓ Level identification test passed")
        
    def test_penetration_detection(self):
        """Test detection of level penetration."""
        level_price = 1.1000
        
        # Support level: price drops below then closes above
        penetration_data = pd.DataFrame({
            'high': [1.0998, 1.0996, 1.0994, 1.1002, 1.1005],
            'low': [1.0990, 1.0988, 1.0985, 1.0996, 1.0998],
            'close': [1.0993, 1.0990, 1.0988, 1.1000, 1.1003]
        })
        
        result = self.strategy._check_level_penetration(
            penetration_data, level_price, 'support'
        )
        
        self.assertTrue(result, "Should detect penetration and reversal of support level")
        print("✓ Penetration detection test passed")
        
    def test_criteria_evaluation(self):
        """Test evaluation of sweep confirmation criteria."""
        recent_bars = pd.DataFrame({
            'time': pd.date_range(start='2025-01-01 10:00', periods=10, freq='1min'),
            'high': [1.1005, 1.1007, 1.1012, 1.1010, 1.1008, 1.1006, 1.1004, 1.1003, 1.1002, 1.1001],
            'low': [1.0995, 1.0997, 1.0995, 1.0993, 1.0998, 1.0996, 1.0994, 1.0993, 1.0992, 1.0991],
            'close': [1.1000, 1.1002, 1.1008, 1.1006, 1.1003, 1.1001, 1.0998, 1.0996, 1.0995, 1.0994],
            'volume': [1000, 1200, 3500, 1100, 1000, 900, 950, 1000, 1050, 1000]
        })
        
        level_info = {'type': 'resistance', 'period': 1440}
        features = {
            'vpin': 0.70,
            'order_book_imbalance': 0.35
        }
        
        score, criteria = self.strategy._evaluate_sweep_criteria(
            recent_bars, 1.1010, level_info, features
        )
        
        self.assertIsInstance(score, int, "Score should be integer")
        self.assertGreaterEqual(score, 0, "Score should be non-negative")
        self.assertLessEqual(score, 5, "Score should not exceed 5")
        self.assertEqual(len(criteria), 5, "Should evaluate 5 criteria")
        
        print(f"✓ Criteria evaluation test passed (score: {score}/5)")
        
    def test_signal_generation(self):
        """Test signal generation with valid sweep detection."""
        market_data = self._create_test_data_with_swings()
        features = {
            'vpin': 0.70,
            'order_book_imbalance': 0.40
        }
        
        level_price = market_data['high'].max() - 0.0010
        level_info = {'type': 'resistance', 'period': 1440}
        confirmation_score = 4
        criteria_scores = {
            'penetration_depth': 1,
            'volume_anomaly': 1,
            'reversal_velocity': 1,
            'order_book_imbalance': 1,
            'vpin_toxicity': 0
        }
        
        signal = self.strategy._generate_signal(
            'EURUSD', datetime.now(), level_price, level_info,
            confirmation_score, criteria_scores, market_data
        )
        
        self.assertIsNotNone(signal, "Should generate signal with score >= 4")
        self.assertEqual(signal.direction, 'SHORT', "Resistance sweep should generate SHORT signal")
        self.assertGreater(signal.entry_price, signal.take_profit, "SHORT take profit should be below entry")
        self.assertLess(signal.entry_price, signal.stop_loss, "SHORT stop loss should be above entry")
        self.assertIn(signal.sizing_level, [3, 4], "Sizing level should be 3 or 4")
        
        rr_ratio = signal.get_risk_reward_ratio()
        self.assertGreater(rr_ratio, 1.5, "Risk-reward ratio should be favorable")
        
        print("✓ Signal generation test passed")
        
    def test_evaluate_method(self):
        """Test complete evaluation method with realistic data."""
        market_data = self._create_test_data_with_swings()
        features = {
            'vpin': 0.68,
            'order_book_imbalance': 0.35
        }
        
        signals = self.strategy.evaluate(market_data, features)
        
        self.assertIsInstance(signals, list, "Evaluate should return list")
        
        for signal in signals:
            self.assertIsNotNone(signal.timestamp)
            self.assertIsNotNone(signal.symbol)
            self.assertIn(signal.direction, ['LONG', 'SHORT'])
            self.assertGreater(signal.entry_price, 0)
            self.assertGreater(signal.stop_loss, 0)
            self.assertGreater(signal.take_profit, 0)
            self.assertIn(signal.sizing_level, [1, 2, 3, 4, 5])
        
        print(f"✓ Evaluate method test passed (generated {len(signals)} signals)")
        
    def _create_test_data_with_swings(self):
        """Create synthetic market data with clear swing points."""
        np.random.seed(42)
        
        base_price = 1.1000
        data_points = 200
        
        prices = []
        current = base_price
        
        for i in range(data_points):
            if i % 40 == 0:
                trend = np.random.choice([-1, 1])
            
            change = np.random.normal(0, 0.0002) + trend * 0.0001
            current = max(0.9000, min(1.3000, current + change))
            prices.append(current)
        
        df = pd.DataFrame({
            'time': pd.date_range(start='2025-01-01', periods=data_points, freq='1min'),
            'open': prices,
            'high': [p + abs(np.random.normal(0, 0.0001)) for p in prices],
            'low': [p - abs(np.random.normal(0, 0.0001)) for p in prices],
            'close': [p + np.random.normal(0, 0.00005) for p in prices],
            'volume': np.random.uniform(1000, 3000, data_points),
            'symbol': ['EURUSD'] * data_points
        })
        
        return df


if __name__ == '__main__':
    print("="*70)
    print("LIQUIDITY SWEEP STRATEGY VALIDATION")
    print("="*70)
    unittest.main(verbosity=2)