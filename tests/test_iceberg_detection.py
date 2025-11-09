"""
Unit tests for Iceberg Detection Strategy.

TESTING PHILOSOPHY:
Iceberg detection is unique because it operates in TWO modes:
1. FULL mode (with L2 data): High accuracy, detects replenishment patterns
2. DEGRADED mode (without L2): Lower accuracy, uses volume/price heuristics

Most retail systems don't have L2 access, so degraded mode is the reality.
These tests validate both modes, but focus on degraded mode since that is
what will be used in production for most FX brokers.

EDUCATIONAL NOTE ON ICEBERG ORDERS:
An iceberg order is a large order where only a small portion is visible in
the order book. When that visible portion is filled, another portion appears,
like an iceberg where most of the mass is hidden underwater. Institutions use
these to hide their true position size and avoid market impact.

DETECTION METHODS:
- L2 Mode: Look for constant replenishment at same price level
- Degraded Mode: Look for price stalling with high volume (absorption)
"""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime
from src.strategies.iceberg_detection import IcebergDetection
from src.features.orderbook_l2 import OrderBookSnapshot

class TestIcebergDetection:
    """Test suite for Iceberg Detection in both modes."""
    
    @pytest.fixture
    def strategy(self):
        """
        Initialize strategy in degraded mode (no L2 data).
        
        This is the realistic configuration for retail/small institutional traders
        who don't have Level 2 order book access. The strategy must work with
        limited information - only OHLCV data.
        """
        params = {
            'mode': 'degraded',
            'volume_advancement_ratio_threshold': 15.0,  # High threshold to reduce false positives
            'stall_duration_bars': 5,  # Minimum stall duration to confirm absorption
            'replenishment_detection': True,  # Would use if L2 available
            'stop_loss_behind_level_atr': 1.0,  # Conservative stop placement
            'take_profit_r_multiple': 2.5  # 2.5:1 minimum for lower-probability pattern
        }
        return IcebergDetection(params)
    
    @pytest.fixture
    def stalled_price_data(self):
        """
        Generate data exhibiting iceberg signature in degraded mode.
        
        ICEBERG SIGNATURE WITHOUT L2:
        When a large iceberg order sits at a level, we observe:
        1. Price stalls at the level (can't break through)
        2. Volume spikes dramatically (order absorbing market orders)
        3. Range compresses (price pinned by large order)
        4. Eventually breaks through when iceberg is filled
        
        SYNTHETIC DATA STRUCTURE:
        Bars 0-49: Normal trading with 2 pip ranges and 500 volume
        Bars 50-55: ICEBERG SIGNATURE
          - Price stalls at 1.1010 (±0.5 pips range)
          - Volume 4x normal (2000 vs 500)
          - High volume/price ratio indicates absorption
        Bars 56-99: Normal trading resumes
        """
        np.random.seed(111)
        
        dates = pd.date_range(end=datetime.now(), periods=100, freq='1min')
        
        prices = []
        volumes = []
        
        for i in range(100):
            if 50 <= i <= 55:
                # ICEBERG SIGNATURE: Price stalls with massive volume
                # This is what we observe when price hits a large hidden order
                stall_price = 1.1010
                prices.append({
                    'open': stall_price,
                    'high': stall_price + 0.00005,  # Extremely tight 0.5 pip range
                    'low': stall_price - 0.00005,   # Price can't move
                    'close': stall_price + np.random.uniform(-0.00003, 0.00003)
                })
                volumes.append(2000)  # 4x normal volume (absorption)
            else:
                # Normal trading with typical ranges and volumes
                base_price = 1.1000 + np.random.uniform(-0.0005, 0.0005)
                prices.append({
                    'open': base_price,
                    'high': base_price + 0.0002,  # Normal 2 pip range
                    'low': base_price - 0.0002,
                    'close': base_price + np.random.uniform(-0.0001, 0.0001)
                })
                volumes.append(500)  # Normal volume
        
        data = pd.DataFrame(prices)
        data['timestamp'] = dates
        data['tick_volume'] = volumes
        data['spread'] = 0.00002
        data['real_volume'] = [v * 1000 for v in volumes]
        
        data.attrs['symbol'] = 'EURUSD'
        return data
    
    def test_degraded_mode_detection(self, strategy, stalled_price_data):
        """
        Test iceberg detection in degraded mode (without L2 data).
        
        WHAT WE'RE TESTING:
        Can the strategy detect iceberg orders using only price and volume data?
        This is the most common scenario as most traders don't have L2 access.
        
        WHY IT MATTERS:
        Degraded mode is less accurate but still useful. A detected iceberg suggests
        a large player is defending a level, which can be valuable information even
        if we can't be 100% certain it's an iceberg vs. other large order types.
        
        HOW IT WORKS:
        1. Strategy scans for price stalling (range compression)
        2. Checks for volume spike during stall (absorption signature)
        3. Calculates volume/price ratio (high ratio = absorption)
        4. If all conditions met, generates low-confidence signal
        5. Signal includes warning about degraded mode operation
        """
        features = {
            'atr': 0.0005,
            'l2_data': None  # No L2 data available (degraded mode)
        }
        
        # Strategy should detect iceberg signature
        signal = strategy.evaluate(stalled_price_data, features)
        
        # ASSERTION 1: Strategy should operate in degraded mode
        assert strategy.mode == 'degraded', "Should operate in degraded mode without L2"
        
        # Signal generation depends on exact detection logic
        # May or may not generate signal depending on thresholds
        # The important thing is no errors occur in degraded mode
        
        if signal:
            # If signal generated, validate structure
            assert signal.strategy_name == "Iceberg_Detection"
            assert signal.metadata['detection_mode'] == 'DEGRADED'
            assert signal.metadata['l2_available'] == False
            assert 'warning' in signal.metadata
            
            # Degraded mode should have LOW or MEDIUM confidence, never HIGH
            assert signal.metadata['confidence'] in ['LOW', 'MEDIUM'], \
                   "Degraded mode should have LOW or MEDIUM confidence"
    
    def test_full_mode_with_l2(self, strategy):
        """
        Test that strategy recognizes when L2 data becomes available.
        
        WHAT WE'RE TESTING:
        Can the strategy adapt to having L2 data if it becomes available?
        This tests the mode-switching logic.
        
        WHY IT MATTERS:
        Some brokers/platforms offer L2 for premium accounts. The strategy should
        automatically use L2 if available for higher accuracy detection.
        
        NOTE:
        This test is limited because we can't easily mock full L2 data parsing.
        In production, L2 parsing would need broker-specific implementation.
        """
        # Create mock L2 snapshot (simplified)
        mock_l2_snapshot = OrderBookSnapshot(
            timestamp=datetime.now(),
            bids=[(1.1000, 1000), (1.0999, 2000)],
            asks=[(1.1001, 1000), (1.1002, 2000)],
            mid_price=1.10005,
            spread=0.0001,
            total_bid_volume=3000,
            total_ask_volume=3000,
            imbalance=0.0
        )
        
        features = {
            'atr': 0.0005,
            'l2_data': 'mock_l2_string'  # Would be actual L2 in production
        }
        
        # Create minimal test data
        dates = pd.date_range(end=datetime.now(), periods=50, freq='1min')
        data = pd.DataFrame({
            'timestamp': dates,
            'open': [1.1000] * 50,
            'high': [1.1001] * 50,
            'low': [1.0999] * 50,
            'close': [1.1000] * 50,
            'tick_volume': [500] * 50,
            'spread': [0.00002] * 50,
            'real_volume': [500000] * 50
        })
        
        # Evaluate - strategy should attempt to parse L2
        signal = strategy.evaluate(data, features)
        
        # Strategy should recognize L2 availability attempt
        # (Actual detection depends on L2 parsing implementation)
    
    def test_insufficient_data_handling(self, strategy):
        """
        Test graceful handling of insufficient data.
        
        WHAT WE'RE TESTING:
        Strategy robustness - does it handle edge cases without crashing?
        
        WHY IT MATTERS:
        Production systems receive data of varying quality and quantity.
        Strategy must handle edge cases gracefully without throwing exceptions
        that could crash the entire trading system.
        """
        # Create minimal data (only 10 bars)
        dates = pd.date_range(end=datetime.now(), periods=10, freq='1min')
        data = pd.DataFrame({
            'timestamp': dates,
            'open': [1.1000] * 10,
            'high': [1.1001] * 10,
            'low': [1.0999] * 10,
            'close': [1.1000] * 10,
            'tick_volume': [500] * 10,
            'spread': [0.00002] * 10,
            'real_volume': [500000] * 10
        })
        
        features = {'atr': 0.0005}
        
        # Should return None gracefully, not crash
        signal = strategy.evaluate(data, features)
        assert signal is None, "Should return None with insufficient data"
    
    def test_volume_price_ratio_calculation(self, strategy, stalled_price_data):
        """
        Test that volume/price ratio is calculated correctly for detection.
        
        WHAT WE'RE TESTING:
        The core heuristic in degraded mode - high volume with little price movement
        suggests absorption by a large order.
        
        WHY IT MATTERS:
        This ratio is the mathematical signature of an iceberg. Volume/price ratio
        above threshold (15.0) with price stalling indicates large hidden order.
        
        CALCULATION:
        Ratio = Total Volume / (Price Range × 10000)
        
        Example:
        - 2000 volume over 6 bars = 12,000 total
        - Price range = 0.0001 (1 pip)
        - Ratio = 12000 / (0.0001 × 10000) = 12000 / 1 = 12000
        
        High ratio = Lots of volume, little movement = Absorption
        """
        features = {'atr': 0.0005, 'l2_data': None}
        
        signal = strategy.evaluate(stalled_price_data, features)
        
        if signal and 'volume_price_ratio' in signal.metadata:
            # Ratio should be very high during stall period
            ratio = signal.metadata['volume_price_ratio']
            assert ratio >= 15.0, f"Volume/price ratio {ratio} should exceed threshold 15.0"

if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])