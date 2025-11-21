"""
Tests for MicrostructureEngine - FASE 3.1
"""
import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

from src.core.microstructure_engine import MicrostructureEngine


def create_sample_data(bars=100, seed=42):
    """Create synthetic market data for testing."""
    np.random.seed(seed)

    timestamps = [datetime.now() + timedelta(minutes=i) for i in range(bars)]
    base_price = 1.1000

    data = {
        'timestamp': timestamps,
        'open': base_price + np.random.randn(bars) * 0.0001,
        'high': base_price + np.abs(np.random.randn(bars)) * 0.0002,
        'low': base_price - np.abs(np.random.randn(bars)) * 0.0002,
        'close': base_price + np.random.randn(bars) * 0.0001,
        'volume': np.random.randint(1000, 10000, bars)
    }

    df = pd.DataFrame(data)

    # Ensure OHLC consistency
    df['high'] = df[['open', 'high', 'close']].max(axis=1)
    df['low'] = df[['open', 'low', 'close']].min(axis=1)

    return df


class TestMicrostructureEngine:
    """Test suite for MicrostructureEngine."""

    def test_initialization(self):
        """Test engine initializes correctly."""
        engine = MicrostructureEngine()

        assert engine.ofi_window == 20
        assert engine.vpin_bucket_size == 50000
        assert engine.vpin_num_buckets == 50
        assert engine.cvd_window == 20

    def test_initialization_with_config(self):
        """Test engine initializes with custom config."""
        config = {
            'ofi_window': 30,
            'vpin_bucket_size': 100000,
            'cvd_window': 50
        }
        engine = MicrostructureEngine(config)

        assert engine.ofi_window == 30
        assert engine.vpin_bucket_size == 100000
        assert engine.cvd_window == 50

    def test_calculate_features_basic(self):
        """Test basic feature calculation."""
        engine = MicrostructureEngine()
        data = create_sample_data(bars=100)

        features = engine.calculate_features(data)

        # Check all features present
        assert 'ofi' in features
        assert 'vpin' in features
        assert 'cvd' in features
        assert 'spread_pct' in features
        assert 'ob_imbalance' in features

    def test_feature_ranges(self):
        """Test features are in expected ranges."""
        engine = MicrostructureEngine()
        data = create_sample_data(bars=100)

        features = engine.calculate_features(data)

        # OFI: -1 to +1
        assert -1 <= features['ofi'] <= 1

        # VPIN: 0 to 1
        assert 0 <= features['vpin'] <= 1

        # CVD: -1 to +1
        assert -1 <= features['cvd'] <= 1

        # Spread: positive
        assert features['spread_pct'] >= 0

        # OB Imbalance: -1 to +1
        assert -1 <= features['ob_imbalance'] <= 1

    def test_caching(self):
        """Test feature caching works."""
        engine = MicrostructureEngine()
        data = create_sample_data(bars=100)

        # First call
        features1 = engine.calculate_features(data, use_cache=True)

        # Second call (same data)
        features2 = engine.calculate_features(data, use_cache=True)

        # Should be exact same (from cache)
        assert features1 == features2
        assert engine.last_cache_timestamp is not None

    def test_cache_invalidation(self):
        """Test cache invalidates with new data."""
        engine = MicrostructureEngine()
        data1 = create_sample_data(bars=100)

        # First call
        features1 = engine.calculate_features(data1, use_cache=True)

        # New data with different timestamp
        data2 = create_sample_data(bars=101)

        # Second call (new data)
        features2 = engine.calculate_features(data2, use_cache=True)

        # Should be different (cache invalidated)
        assert features1 != features2

    def test_insufficient_data(self):
        """Test handles insufficient data gracefully."""
        engine = MicrostructureEngine()
        data = create_sample_data(bars=5)  # Too few bars

        features = engine.calculate_features(data)

        # Should return zeros
        assert features['ofi'] == 0.0
        assert features['vpin'] == 0.0
        assert features['cvd'] == 0.0

    def test_trending_up_data(self):
        """Test features with trending up data."""
        engine = MicrostructureEngine()

        # Create uptrend data
        bars = 100
        timestamps = [datetime.now() + timedelta(minutes=i) for i in range(bars)]
        base_price = 1.1000
        prices = base_price + np.cumsum(np.abs(np.random.randn(bars))) * 0.0001

        data = pd.DataFrame({
            'timestamp': timestamps,
            'open': prices,
            'high': prices + 0.0001,
            'low': prices - 0.00005,
            'close': prices + 0.00008,  # Close near high (buying)
            'volume': np.random.randint(1000, 10000, bars)
        })

        features = engine.calculate_features(data)

        # In uptrend, expect positive OFI and CVD
        assert features['ofi'] > 0  # Positive flow
        assert features['cvd'] > 0  # Positive cumulative volume

    def test_trending_down_data(self):
        """Test features with trending down data."""
        engine = MicrostructureEngine()

        # Create downtrend data
        bars = 100
        timestamps = [datetime.now() + timedelta(minutes=i) for i in range(bars)]
        base_price = 1.1000
        prices = base_price - np.cumsum(np.abs(np.random.randn(bars))) * 0.0001

        data = pd.DataFrame({
            'timestamp': timestamps,
            'open': prices,
            'high': prices + 0.00005,
            'low': prices - 0.0001,
            'close': prices - 0.00008,  # Close near low (selling)
            'volume': np.random.randint(1000, 10000, bars)
        })

        features = engine.calculate_features(data)

        # In downtrend, expect negative OFI and CVD
        assert features['ofi'] < 0  # Negative flow
        assert features['cvd'] < 0  # Negative cumulative volume

    def test_reset(self):
        """Test reset clears state."""
        engine = MicrostructureEngine()
        data = create_sample_data(bars=100)

        # Calculate features
        engine.calculate_features(data)

        assert len(engine.feature_cache) > 0
        assert engine.last_cache_timestamp is not None

        # Reset
        engine.reset()

        assert len(engine.feature_cache) == 0
        assert engine.last_cache_timestamp is None

    def test_get_feature_summary(self):
        """Test feature summary generation."""
        engine = MicrostructureEngine()

        features = {
            'ofi': 0.6,
            'vpin': 0.25,
            'cvd': 0.4
        }

        summary = engine.get_feature_summary(features)

        assert isinstance(summary, str)
        assert 'OFI' in summary
        assert 'VPIN' in summary
        assert 'CVD' in summary
        assert '0.60' in summary or '+0.60' in summary

    def test_multiple_calculations(self):
        """Test engine handles multiple sequential calculations."""
        engine = MicrostructureEngine()

        for i in range(10):
            data = create_sample_data(bars=100, seed=i)
            features = engine.calculate_features(data)

            # Validate each calculation
            assert -1 <= features['ofi'] <= 1
            assert 0 <= features['vpin'] <= 1
            assert -1 <= features['cvd'] <= 1


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
