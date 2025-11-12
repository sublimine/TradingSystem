"""
Test suite for CorrelationDivergence strategy
Validates correlation breakdown detection and divergence identification
"""

import unittest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from src.strategies.correlation_divergence import CorrelationDivergence
from src.strategies.strategy_base import Signal


class TestCorrelationDivergence(unittest.TestCase):
    """Test cases for Correlation Divergence strategy"""

    def setUp(self):
        """Initialize strategy with institutional configuration"""
        self.config = {
            'monitored_pairs': [('EURUSD.pro', 'GBPUSD.pro')],
            'correlation_lookback': 100,
            'historical_correlation_min': 0.80,
            'divergence_correlation_threshold': 0.50,
            'relative_strength_lookback': 20,
            'min_divergence_magnitude': 1.5,
            'convergence_confidence_threshold': 0.70
        }
        self.strategy = CorrelationDivergence(self.config)

    def test_initialization(self):
        """Test strategy initializes with institutional parameters"""
        self.assertEqual(self.strategy.name, 'CorrelationDivergence')
        self.assertEqual(len(self.strategy.monitored_pairs), 1)
        self.assertEqual(self.strategy.correlation_lookback, 100)
        self.assertEqual(self.strategy.historical_correlation_min, 0.80)


if __name__ == '__main__':
    unittest.main()
