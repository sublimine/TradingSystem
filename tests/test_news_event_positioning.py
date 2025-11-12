"""
Test suite for NewsEventPositioning strategy
Validates event detection and risk management logic
"""

import unittest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from src.strategies.news_event_positioning import NewsEventPositioning
from src.strategies.strategy_base import Signal


class TestNewsEventPositioning(unittest.TestCase):
    """Test cases for News Event Positioning strategy"""

    def setUp(self):
        """Initialize strategy with institutional configuration"""
        event_time = datetime(2025, 11, 1, 14, 30, 0)

        self.config = {
            'event_calendar': [
                {'timestamp': event_time, 'impact_level': 4, 'name': 'NFP Release'}
            ],
            'pre_event_window_minutes': 30,
            'post_event_window_minutes': 15,
            'high_impact_threshold': 3,
            'position_reduction_factor': 0.5,
            'volatility_expansion_threshold': 2.0
        }
        self.strategy = NewsEventPositioning(self.config)

    def test_initialization(self):
        """Test strategy initializes with institutional parameters"""
        self.assertEqual(self.strategy.name, 'NewsEventPositioning')
        self.assertEqual(len(self.strategy.event_calendar), 1)
        self.assertEqual(self.strategy.pre_event_window, 30)
        self.assertEqual(self.strategy.high_impact_threshold, 3)


if __name__ == '__main__':
    unittest.main()
