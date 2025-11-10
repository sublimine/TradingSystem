"""
Unit tests for statistical models module
"""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / 'src' / 'features'))

import numpy as np
import pandas as pd

from statistical_models import (
    KalmanPairsFilter,
    VolatilityHMM,
    calculate_realized_volatility,
    calculate_spread_zscore,
    estimate_hedge_ratio
)


class TestKalmanPairsFilter(unittest.TestCase):
    
    def test_initialization(self):
        kf = KalmanPairsFilter(process_variance=0.001, measurement_variance=0.01)
        self.assertIsNotNone(kf.state_mean)
        self.assertEqual(kf.process_variance, 0.001)
        print("✓ Kalman initialization test passed")
    
    def test_single_update(self):
        kf = KalmanPairsFilter(process_variance=0.001, measurement_variance=0.01)
        initial_mean = kf.get_estimated_mean()
        kf.update(0.5)
        updated_mean = kf.get_estimated_mean()
        self.assertNotEqual(initial_mean, updated_mean)
        print("✓ Single update test passed")
    
    def test_convergence(self):
        kf = KalmanPairsFilter(process_variance=0.0001, measurement_variance=0.01)
        for _ in range(100):
            kf.update(1.5)
        estimated_mean = kf.get_estimated_mean()
        self.assertAlmostEqual(estimated_mean, 1.5, places=2)
        print("✓ Convergence test passed")
    
    def test_confidence_band(self):
        kf = KalmanPairsFilter(process_variance=0.001, measurement_variance=0.01)
        for _ in range(20):
            kf.update(1.0)
        lower, upper = kf.get_confidence_band(num_std=2.0)
        mean = kf.get_estimated_mean()
        self.assertLess(lower, mean)
        self.assertGreater(upper, mean)
        print("✓ Confidence band test passed")


class TestVolatilityHMM(unittest.TestCase):
    
    def test_initialization(self):
        hmm = VolatilityHMM()
        self.assertEqual(hmm.n_states, 2)
        self.assertIsNotNone(hmm.transition_matrix)
        print("✓ HMM initialization test passed")
    
    def test_fit_basic(self):
        hmm = VolatilityHMM()
        np.random.seed(42)
        observations = np.random.gamma(2, 2, 100)
        result = hmm.fit(observations, max_iterations=10)
        self.assertTrue(hmm.fitted)
        self.assertIsNotNone(hmm.emission_means)
        self.assertIn('log_likelihood', result)
        print("✓ HMM fit test passed")
    
    def test_predict_state(self):
        hmm = VolatilityHMM()
        np.random.seed(42)
        observations = np.random.gamma(2, 2, 100)
        hmm.fit(observations, max_iterations=10)
        new_obs = np.array([0.01, 0.02, 0.05])
        state_probs = hmm.predict_state(new_obs)
        self.assertEqual(len(state_probs), 2)
        self.assertAlmostEqual(sum(state_probs), 1.0, places=6)
        print("✓ HMM predict state test passed")


class TestAuxiliaryFunctions(unittest.TestCase):
    
    def test_realized_volatility(self):
        np.random.seed(42)
        returns = pd.Series(np.random.normal(0, 0.01, 100))
        vol = calculate_realized_volatility(returns, window=20)
        vol_values = vol if isinstance(vol, np.ndarray) else vol.values
        valid_vol = vol_values[~np.isnan(vol_values)]
        self.assertTrue(len(valid_vol) > 0)
        self.assertTrue((valid_vol > 0).all())
        print("✓ Realized volatility test passed")
    
    def test_spread_zscore(self):
        zscore = calculate_spread_zscore(0.5, 0.0, 0.1)
        self.assertAlmostEqual(zscore, 5.0, places=6)
        print("✓ Z-score test passed")
    
    def test_estimate_hedge_ratio(self):
        np.random.seed(42)
        x = pd.Series(100 + np.cumsum(np.random.normal(0, 1, 100)))
        y = pd.Series(200 + 2.0 * (x - 100) + np.random.normal(0, 2, 100))
        result = estimate_hedge_ratio(x, y, use_log_prices=False)
        self.assertIsInstance(result, dict)
        self.assertIn('beta', result)
        self.assertIn('r_squared', result)
        beta = result['beta']
        self.assertGreater(beta, 0)
        self.assertLess(abs(beta - 2.0), 1.0)
        print("✓ Hedge ratio test passed")


if __name__ == '__main__':
    print("="*60)
    print("Running Statistical Models Tests")
    print("="*60)
    unittest.main(verbosity=2)