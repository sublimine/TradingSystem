"""
Unit tests for Order Block Institutional Strategy.
"""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from src.strategies.order_block_institutional import OrderBlockInstitutional

class TestOrderBlockInstitutional:
    
    @pytest.fixture
    def strategy(self):
        params = {
            'volume_sigma_threshold': 2.5,
            'displacement_atr_multiplier': 2.0,
            'no_retest_enforcement': True,
            'buffer_atr': 0.5,
            'stop_loss_buffer_atr': 0.75,
            'take_profit_r_multiple': [1.5, 3.0],
            'require_ofi_confirmation': False,
            'require_footprint_confirmation': False
        }
        return OrderBlockInstitutional(params)
    
    def test_initialization(self, strategy):
        assert strategy is not None
        assert strategy.displacement_atr_multiplier == 2.0

if __name__ == '__main__':
    pytest.main([__file__, '-v'])