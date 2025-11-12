"""
Test suite for OrderFlowToxicityStrategy
Validates detection of toxic order flow via VPIN monitoring
"""

import unittest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from src.strategies.order_flow_toxicity import OrderFlowToxicityStrategy
from src.strategies.strategy_base import Signal


class TestOrderFlowToxicityStrategy(unittest.TestCase):
    """Test cases for OrderFlowToxicityStrategy"""
    
    def setUp(self):
        """Initialize strategy with standard configuration before each test"""
        self.config = {
            'vpin_threshold': 0.65,
            'min_consecutive_buckets': 3,
            'flow_direction_threshold': 0.20,
            'context_verification_enabled': True,
            'max_extension_atr_multiple': 2.0
        }
        self.strategy = OrderFlowToxicityStrategy(self.config)
        
        # Create synthetic market data with 100 bars
        base_time = datetime(2025, 11, 1, 9, 0, 0)
        self.market_data = pd.DataFrame({
            'time': [base_time + timedelta(minutes=i) for i in range(100)],
            'open': np.linspace(1.1000, 1.1050, 100),
            'high': np.linspace(1.1005, 1.1055, 100),
            'low': np.linspace(0.9995, 1.1045, 100),
            'close': np.linspace(1.1002, 1.1052, 100),
            'volume': np.random.randint(1000, 5000, 100)
        })
    
    def test_initialization(self):
        """Test strategy initializes correctly with configuration parameters"""
        self.assertEqual(self.strategy.name, 'OrderFlowToxicityStrategy')
        self.assertEqual(self.strategy.config['vpin_threshold'], 0.65)
        self.assertEqual(self.strategy.config['min_consecutive_buckets'], 3)
        self.assertEqual(self.strategy.config['flow_direction_threshold'], 0.20)
        self.assertTrue(self.strategy.config['context_verification_enabled'])
        self.assertEqual(self.strategy.config['max_extension_atr_multiple'], 2.0)
        self.assertIsInstance(self.strategy.vpin_history, list)
        self.assertEqual(len(self.strategy.vpin_history), 0)
    
    def test_sustained_toxicity_check_insufficient_history(self):
        """Test sustained toxicity returns False with insufficient VPIN history"""
        # Add only 2 values when 3 required
        self.strategy.vpin_history = [0.70, 0.72]
        result = self.strategy._check_sustained_toxicity()
        self.assertFalse(result)
    
    def test_sustained_toxicity_check_values_below_threshold(self):
        """Test sustained toxicity returns False when values below threshold"""
        # Add 3 values but one below threshold
        self.strategy.vpin_history = [0.70, 0.60, 0.72]
        result = self.strategy._check_sustained_toxicity()
        self.assertFalse(result)
    
    def test_sustained_toxicity_check_success(self):
        """Test sustained toxicity returns True with sufficient high values"""
        # Add 3 consecutive values all above threshold
        self.strategy.vpin_history = [0.70, 0.68, 0.72]
        result = self.strategy._check_sustained_toxicity()
        self.assertTrue(result)
    
    def test_flow_direction_determination_bullish(self):
        """Test flow direction correctly identifies bullish flow"""
        # Imbalance of +0.30 exceeds threshold of 0.20
        features = {'order_flow_imbalance': 0.30}
        direction = self.strategy._determine_flow_direction(features)
        self.assertEqual(direction, 1)
    
    def test_flow_direction_determination_bearish(self):
        """Test flow direction correctly identifies bearish flow"""
        # Imbalance of -0.35 exceeds threshold of 0.20 in magnitude
        features = {'order_flow_imbalance': -0.35}
        direction = self.strategy._determine_flow_direction(features)
        self.assertEqual(direction, -1)
    
    def test_flow_direction_determination_neutral(self):
        """Test flow direction returns zero for insufficient imbalance"""
        # Imbalance of 0.15 below threshold of 0.20
        features = {'order_flow_imbalance': 0.15}
        direction = self.strategy._determine_flow_direction(features)
        self.assertEqual(direction, 0)
    
    def test_market_context_verification_aligned(self):
        """Test context verification returns True when price and flow aligned"""
        # Create data with upward price movement
        data_uptrend = self.market_data.copy()
        data_uptrend['close'] = np.linspace(1.1000, 1.1050, 100)
        
        # Flow direction +1 (bullish) should align with upward price
        result = self.strategy._verify_market_context(data_uptrend, flow_direction=1)
        self.assertTrue(result)
    
    def test_market_context_verification_misaligned(self):
        """Test context verification returns False when price and flow misaligned"""
        # Create data with downward price movement
        data_downtrend = self.market_data.copy()
        data_downtrend['close'] = np.linspace(1.1050, 1.1000, 100)
        
        # Flow direction +1 (bullish) conflicts with downward price
        result = self.strategy._verify_market_context(data_downtrend, flow_direction=1)
        self.assertFalse(result)
    
    def test_evaluate_missing_features(self):
        """Test evaluate returns empty list when required features missing"""
        # Features missing 'vpin'
        features = {'order_flow_imbalance': 0.30}
        signals = self.strategy.evaluate(self.market_data, features)
        self.assertIsInstance(signals, list)
        self.assertEqual(len(signals), 0)
    
    def test_evaluate_with_valid_conditions(self):
        """Test evaluate generates valid signal with all conditions met"""
        # Build up VPIN history with sustained toxicity
        self.strategy.vpin_history = [0.70, 0.68, 0.72]
        
        # Create features with toxic flow and bullish imbalance
        features = {
            'vpin': 0.75,
            'order_flow_imbalance': 0.35
        }
        
        # Create uptrending market data for context alignment
        data_uptrend = self.market_data.copy()
        data_uptrend['close'] = np.linspace(1.1000, 1.1050, 100)
        
        signals = self.strategy.evaluate(data_uptrend, features)
        
        self.assertIsInstance(signals, list)
        self.assertEqual(len(signals), 1)
        
        signal = signals[0]
        self.assertIsInstance(signal, Signal)
        self.assertEqual(signal.direction, 'LONG')
        self.assertEqual(signal.strategy_name, 'OrderFlowToxicityStrategy')
        self.assertIsNotNone(signal.entry_price)
        self.assertIsNotNone(signal.stop_loss)
        self.assertIsNotNone(signal.take_profit)
        self.assertEqual(signal.sizing_level, 3)
        self.assertIn('vpin_current', signal.metadata)
        self.assertIn('flow_imbalance', signal.metadata)
        self.assertIn('flow_direction', signal.metadata)
        self.assertIn('consecutive_toxic_periods', signal.metadata)
    
    def test_signal_generation_structure(self):
        """Test generated signal has correct structure and risk-reward ratio"""
        # Setup for signal generation
        self.strategy.vpin_history = [0.70, 0.68, 0.72, 0.75]
        
        features = {
            'vpin': 0.77,
            'order_flow_imbalance': -0.40  # Bearish flow
        }
        
        # Create downtrending data for bearish alignment
        data_downtrend = self.market_data.copy()
        data_downtrend['close'] = np.linspace(1.1050, 1.1000, 100)
        
        signals = self.strategy.evaluate(data_downtrend, features)
        
        self.assertEqual(len(signals), 1)
        signal = signals[0]
        
        # Verify SHORT signal for bearish flow
        self.assertEqual(signal.direction, 'SHORT')
        
        # Verify risk-reward ratio is positive and reasonable
        risk = abs(signal.entry_price - signal.stop_loss)
        reward = abs(signal.take_profit - signal.entry_price)
        self.assertGreater(risk, 0)
        self.assertGreater(reward, 0)
        
        risk_reward_ratio = reward / risk
        self.assertGreater(risk_reward_ratio, 1.0)
        self.assertLess(risk_reward_ratio, 2.0)  # Should be ~1.5
        
        # Verify metadata completeness
        self.assertEqual(signal.metadata['flow_direction'], -1)
        self.assertGreaterEqual(signal.metadata['consecutive_toxic_periods'], 3)
        self.assertIn('strategy_version', signal.metadata)


if __name__ == '__main__':
    unittest.main()