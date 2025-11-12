"""
Statistical Models Module for Algorithmic Trading System

This module implements advanced statistical models for quantitative trading:
1. Adaptive Kalman Filter for pairs trading spread estimation
2. Hidden Markov Model for volatility regime detection

Author: Trading System Engineering Team
Date: November 2024
Python Version: 3.13
"""

import numpy as np
import pandas as pd
from typing import Tuple, List, Optional, Union, Dict
from dataclasses import dataclass
import warnings
from enum import IntEnum


# Constants for numerical stability
EPSILON = 1e-10
MAX_VARIANCE = 1e6
MIN_VARIANCE = 1e-10

class VolatilityState(IntEnum):
    """Enumeration for volatility regime states"""
    LOW_VOLATILITY = 0
    HIGH_VOLATILITY = 1


@dataclass
class KalmanState:
    """Container for Kalman Filter state variables"""
    mean: float
    covariance: float
    prediction_mean: float
    prediction_covariance: float
    innovation: float
    innovation_covariance: float
    kalman_gain: float
    log_likelihood: float


class KalmanPairsFilter:
    """
    Adaptive Kalman Filter for pairs trading spread estimation.
    
    This implementation uses a univariate Kalman Filter to track the time-varying
    mean of a spread between two correlated instruments. The filter assumes:
    - State transition: x(t) = x(t-1) + w(t), where w ~ N(0, Q)
    - Observation: z(t) = x(t) + v(t), where v ~ N(0, R)
    
    Attributes:
        process_variance (float): Process noise variance (Q)
        measurement_variance (float): Measurement noise variance (R)
        state_mean (float): Current estimated mean of the spread
        state_covariance (float): Current estimation error covariance
        initialized (bool): Whether filter has processed at least one observation
        update_count (int): Number of updates processed
        log_likelihood_sum (float): Cumulative log-likelihood for model validation
    """
    
    def __init__(self, process_variance: float = 0.01, 
                 measurement_variance: float = 0.1,
                 initial_mean: Optional[float] = None,
                 initial_covariance: Optional[float] = None):
        """
        Initialize Kalman Filter with specified noise parameters.
        
        Args:
            process_variance: Variance of the process noise (Q parameter)
            measurement_variance: Variance of the measurement noise (R parameter)
            initial_mean: Initial state estimate (default 0)
            initial_covariance: Initial estimation error covariance (default 1)
        
        Raises:
            ValueError: If variance parameters are non-positive
        """
        if process_variance <= 0 or measurement_variance <= 0:
            raise ValueError("Variance parameters must be positive")
            
        self.process_variance = process_variance
        self.measurement_variance = measurement_variance
        
        # Initialize state estimates
        self.state_mean = initial_mean if initial_mean is not None else 0.0
        self.state_covariance = initial_covariance if initial_covariance is not None else 1.0
        
        # Ensure covariance is bounded for numerical stability
        self.state_covariance = np.clip(self.state_covariance, MIN_VARIANCE, MAX_VARIANCE)
        
        # State transition and observation matrices (scalar for univariate case)
        self.A = 1.0  # State transition
        self.H = 1.0  # Observation model
        
        # Tracking variables
        self.initialized = False
        self.update_count = 0
        self.log_likelihood_sum = 0.0
        self.last_state = None
        
    def update(self, spread_observation: float) -> KalmanState:
        """
        Process new spread observation and update state estimates.
        
        Implements the standard Kalman Filter equations:
        1. Prediction step: x_pred = A*x, P_pred = A*P*A' + Q
        2. Update step: K = P_pred*H'/(H*P_pred*H' + R), x = x_pred + K*(z - H*x_pred)
        3. Covariance update: P = (1 - K*H)*P_pred (Joseph form for stability)
        
        Args:
            spread_observation: New observed spread value
            
        Returns:
            KalmanState: Complete state information after update
            
        Raises:
            ValueError: If observation is NaN or infinite
        """
        if not np.isfinite(spread_observation):
            raise ValueError("Observation must be finite")
        
        # Prediction step
        # x(t|t-1) = A * x(t-1|t-1)
        prediction_mean = self.A * self.state_mean
        
        # P(t|t-1) = A * P(t-1|t-1) * A' + Q
        prediction_covariance = self.A * self.state_covariance * self.A + self.process_variance
        
        # Bound prediction covariance for numerical stability
        prediction_covariance = np.clip(prediction_covariance, MIN_VARIANCE, MAX_VARIANCE)
        
        # Innovation (measurement residual)
        # y(t) = z(t) - H * x(t|t-1)
        innovation = spread_observation - self.H * prediction_mean
        
        # Innovation covariance
        # S(t) = H * P(t|t-1) * H' + R
        innovation_covariance = self.H * prediction_covariance * self.H + self.measurement_variance
        
        # Ensure innovation covariance doesn't become too small
        innovation_covariance = max(innovation_covariance, EPSILON)
        
        # Kalman gain
        # K(t) = P(t|t-1) * H' / S(t)
        kalman_gain = prediction_covariance * self.H / innovation_covariance
        
        # State update
        # x(t|t) = x(t|t-1) + K(t) * y(t)
        self.state_mean = prediction_mean + kalman_gain * innovation
        
        # Covariance update using Joseph form for numerical stability
        # P(t|t) = (I - K(t)*H) * P(t|t-1) * (I - K(t)*H)' + K(t)*R*K(t)'
        # Simplified for scalar case: P(t|t) = (1 - K*H) * P(t|t-1)
        factor = 1 - kalman_gain * self.H
        self.state_covariance = factor * prediction_covariance * factor + \
                                kalman_gain * self.measurement_variance * kalman_gain
        
        # Ensure covariance remains positive and bounded
        self.state_covariance = np.clip(self.state_covariance, MIN_VARIANCE, MAX_VARIANCE)
        
        # Calculate log-likelihood for this observation (for model validation)
        log_likelihood = -0.5 * (np.log(2 * np.pi * innovation_covariance) + 
                                 innovation**2 / innovation_covariance)
        self.log_likelihood_sum += log_likelihood
        
        # Update tracking
        self.initialized = True
        self.update_count += 1
        
        # Store complete state
        self.last_state = KalmanState(
            mean=self.state_mean,
            covariance=self.state_covariance,
            prediction_mean=prediction_mean,
            prediction_covariance=prediction_covariance,
            innovation=innovation,
            innovation_covariance=innovation_covariance,
            kalman_gain=kalman_gain,
            log_likelihood=log_likelihood
        )
        
        return self.last_state
    
    def get_estimated_mean(self) -> float:
        """
        Get current estimated mean of the spread.
        
        Returns:
            float: Current state mean estimate
        """
        return self.state_mean
    
    def get_estimation_uncertainty(self) -> float:
        """
        Get current estimation uncertainty (variance of state estimate).
        
        The uncertainty represents the variance of the Kalman Filter's
        state estimate. Lower values indicate higher confidence in the
        estimate after observing consistent data. Higher values indicate
        uncertainty during initialization or after observing volatile data.
        
        Returns:
            Current estimation variance (P)
        
        Example:
            >>> filter = KalmanPairsFilter(process_variance=0.001, measurement_variance=0.01)
            >>> filter.update(0.015)
            >>> uncertainty = filter.get_estimation_uncertainty()
            >>> print(f"Uncertainty: {uncertainty:.6f}")
        """
        return self.state_covariance
    
    def get_confidence_band(self, num_std: float = 2.0) -> Tuple[float, float]:
        """
        Get confidence band around estimated mean.
        
        Args:
            num_std: Number of standard deviations for confidence band
            
        Returns:
            Tuple[float, float]: (lower_bound, upper_bound)
        """
        std_dev = np.sqrt(self.state_covariance)
        return (
            self.state_mean - num_std * std_dev,
            self.state_mean + num_std * std_dev
        )
    
    def get_prediction(self, steps_ahead: int = 1) -> Tuple[float, float]:
        """
        Get multi-step ahead prediction with uncertainty.
        
        Args:
            steps_ahead: Number of steps to predict ahead
            
        Returns:
            Tuple[float, float]: (predicted_mean, predicted_variance)
        """
        if steps_ahead < 1:
            raise ValueError("steps_ahead must be positive")
            
        # For random walk model: mean stays same, variance increases linearly
        predicted_mean = self.state_mean
        predicted_variance = self.state_covariance + steps_ahead * self.process_variance
        
        return predicted_mean, predicted_variance
    
    def reset(self):
        """Reset filter to initial state."""
        self.state_mean = 0.0
        self.state_covariance = 1.0
        self.initialized = False
        self.update_count = 0
        self.log_likelihood_sum = 0.0
        self.last_state = None


class VolatilityHMM:
    """
    Hidden Markov Model for volatility regime detection.
    
    This implementation uses a 2-state HMM with Gaussian emissions to identify
    low and high volatility regimes in market data. The model uses:
    - Forward-backward algorithm for state inference
    - Baum-Welch algorithm for parameter estimation
    - Scaled computations to prevent numerical underflow
    
    Attributes:
        n_states (int): Number of hidden states (fixed at 2)
        transition_matrix (np.ndarray): State transition probabilities
        emission_means (np.ndarray): Mean volatility for each state
        emission_stds (np.ndarray): Std deviation of volatility for each state
        initial_probs (np.ndarray): Initial state probabilities
        fitted (bool): Whether model has been fitted to data
    """
    
    def __init__(self, random_seed: Optional[int] = None):
        """
        Initialize HMM with default parameters for 2-state volatility model.
        
        Args:
            random_seed: Random seed for reproducibility
        """
        self.n_states = 2  # Low and High volatility
        self.random_seed = random_seed
        
        if random_seed is not None:
            np.random.seed(random_seed)
        
        # Initialize with reasonable defaults for volatility regimes
        # Transition matrix: tendency to stay in same regime
        self.transition_matrix = np.array([
            [0.95, 0.05],  # Low vol: 95% stay low, 5% to high
            [0.10, 0.90]   # High vol: 10% to low, 90% stay high
        ])
        
        # Emission parameters (will be updated by fit)
        self.emission_means = np.array([0.01, 0.03])  # Low and high vol means
        self.emission_stds = np.array([0.005, 0.015])  # Low and high vol stds
        
        # Initial state probabilities
        self.initial_probs = np.array([0.7, 0.3])  # Start with 70% low vol
        
        # Model state
        self.fitted = False
        self.n_observations = 0
        self.log_likelihood = -np.inf
        
    def _gaussian_density(self, observation: float, mean: float, std: float) -> float:
        """
        Calculate Gaussian probability density.
        
        Args:
            observation: Observed value
            mean: Distribution mean
            std: Distribution standard deviation
            
        Returns:
            float: Probability density value
        """
        # Add small epsilon to std to prevent division by zero
        std = max(std, EPSILON)
        
        # Calculate normalized Gaussian density
        coefficient = 1.0 / (std * np.sqrt(2 * np.pi))
        exponent = -0.5 * ((observation - mean) / std) ** 2
        
        # Prevent underflow
        density = coefficient * np.exp(max(exponent, -100))
        
        return max(density, EPSILON)
    
    def _forward_pass(self, observations: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        """
        Forward algorithm to compute forward probabilities.
        
        Args:
            observations: Sequence of volatility observations
            
        Returns:
            Tuple[np.ndarray, np.ndarray]: (forward_probs, scaling_factors)
        """
        T = len(observations)
        forward = np.zeros((T, self.n_states))
        scaling = np.zeros(T)
        
        # Initialize first observation
        for j in range(self.n_states):
            forward[0, j] = self.initial_probs[j] * \
                           self._gaussian_density(observations[0], 
                                                 self.emission_means[j],
                                                 self.emission_stds[j])
        
        # Scale to prevent underflow
        scaling[0] = np.sum(forward[0, :])
        if scaling[0] > EPSILON:
            forward[0, :] /= scaling[0]
        else:
            forward[0, :] = 1.0 / self.n_states
            scaling[0] = 1.0
        
        # Forward recursion
        for t in range(1, T):
            for j in range(self.n_states):
                # Sum over all previous states
                forward[t, j] = np.sum(forward[t-1, :] * self.transition_matrix[:, j])
                
                # Multiply by emission probability
                forward[t, j] *= self._gaussian_density(observations[t],
                                                       self.emission_means[j],
                                                       self.emission_stds[j])
            
            # Scale
            scaling[t] = np.sum(forward[t, :])
            if scaling[t] > EPSILON:
                forward[t, :] /= scaling[t]
            else:
                forward[t, :] = forward[t-1, :]  # Use previous if numerical issues
                scaling[t] = 1.0
        
        return forward, scaling
    
    def _backward_pass(self, observations: np.ndarray, scaling: np.ndarray) -> np.ndarray:
        """
        Backward algorithm to compute backward probabilities.
        
        Args:
            observations: Sequence of volatility observations
            scaling: Scaling factors from forward pass
            
        Returns:
            np.ndarray: Backward probabilities
        """
        T = len(observations)
        backward = np.zeros((T, self.n_states))
        
        # Initialize last observation
        backward[T-1, :] = 1.0
        
        # Backward recursion
        for t in range(T-2, -1, -1):
            for i in range(self.n_states):
                backward[t, i] = 0
                for j in range(self.n_states):
                    emission_prob = self._gaussian_density(observations[t+1],
                                                          self.emission_means[j],
                                                          self.emission_stds[j])
                    backward[t, i] += self.transition_matrix[i, j] * \
                                     emission_prob * backward[t+1, j]
            
            # Scale using same factors as forward pass
            if scaling[t+1] > EPSILON:
                backward[t, :] /= scaling[t+1]
        
        return backward
    
    def _compute_gamma(self, forward: np.ndarray, backward: np.ndarray) -> np.ndarray:
        """
        Compute posterior state probabilities.
        
        Args:
            forward: Forward probabilities
            backward: Backward probabilities
            
        Returns:
            np.ndarray: Posterior state probabilities gamma(t, i)
        """
        T = forward.shape[0]
        gamma = np.zeros((T, self.n_states))
        
        for t in range(T):
            denominator = np.sum(forward[t, :] * backward[t, :])
            if denominator > EPSILON:
                gamma[t, :] = (forward[t, :] * backward[t, :]) / denominator
            else:
                gamma[t, :] = 1.0 / self.n_states
        
        return gamma
    
    def fit(self, volatility_observations: Union[List[float], np.ndarray], 
            max_iterations: int = 100,
            tolerance: float = 1e-4) -> Dict[str, float]:
        """
        Estimate HMM parameters using Baum-Welch algorithm.
        
        Args:
            volatility_observations: Sequence of volatility observations
            max_iterations: Maximum EM iterations
            tolerance: Convergence tolerance for log-likelihood
            
        Returns:
            Dict with fit statistics including log-likelihood and iterations
            
        Raises:
            ValueError: If observations are invalid or too few
        """
        observations = np.asarray(volatility_observations)
        
        # Validate input
        if len(observations) < 10:
            raise ValueError("Need at least 10 observations for fitting")
        if not np.all(np.isfinite(observations)):
            raise ValueError("Observations must be finite")
        if np.any(observations < 0):
            raise ValueError("Volatility observations must be non-negative")
        
        T = len(observations)
        self.n_observations = T
        
        # Initialize emission parameters from data
        sorted_obs = np.sort(observations)
        split_point = T // 2
        
        # Low volatility state: lower half of observations
        self.emission_means[0] = np.mean(sorted_obs[:split_point])
        self.emission_stds[0] = np.std(sorted_obs[:split_point]) + EPSILON
        
        # High volatility state: upper half of observations
        self.emission_means[1] = np.mean(sorted_obs[split_point:])
        self.emission_stds[1] = np.std(sorted_obs[split_point:]) + EPSILON
        
        # Ensure means are ordered
        if self.emission_means[0] > self.emission_means[1]:
            self.emission_means = self.emission_means[::-1]
            self.emission_stds = self.emission_stds[::-1]
        
        # EM algorithm iterations
        prev_log_likelihood = -np.inf
        
        for iteration in range(max_iterations):
            # E-step: compute state probabilities
            forward, scaling = self._forward_pass(observations)
            backward = self._backward_pass(observations, scaling)
            gamma = self._compute_gamma(forward, backward)
            
            # Compute xi for transition updates
            xi = np.zeros((T-1, self.n_states, self.n_states))
            for t in range(T-1):
                denominator = np.sum(forward[t, :] * backward[t, :])
                if denominator > EPSILON:
                    for i in range(self.n_states):
                        for j in range(self.n_states):
                            emission_prob = self._gaussian_density(observations[t+1],
                                                                  self.emission_means[j],
                                                                  self.emission_stds[j])
                            xi[t, i, j] = forward[t, i] * self.transition_matrix[i, j] * \
                                         emission_prob * backward[t+1, j] / denominator
            
            # M-step: update parameters
            
            # Update initial probabilities
            self.initial_probs = gamma[0, :]
            
            # Update transition matrix
            for i in range(self.n_states):
                denominator = np.sum(gamma[:-1, i])
                if denominator > EPSILON:
                    for j in range(self.n_states):
                        self.transition_matrix[i, j] = np.sum(xi[:, i, j]) / denominator
            
            # Normalize transition matrix rows
            for i in range(self.n_states):
                row_sum = np.sum(self.transition_matrix[i, :])
                if row_sum > EPSILON:
                    self.transition_matrix[i, :] /= row_sum
                else:
                    self.transition_matrix[i, :] = 1.0 / self.n_states
            
            # Update emission parameters
            for j in range(self.n_states):
                gamma_sum = np.sum(gamma[:, j])
                if gamma_sum > EPSILON:
                    self.emission_means[j] = np.sum(gamma[:, j] * observations) / gamma_sum
                    
                    # Update standard deviation
                    diff = observations - self.emission_means[j]
                    self.emission_stds[j] = np.sqrt(np.sum(gamma[:, j] * diff**2) / gamma_sum)
                    self.emission_stds[j] = max(self.emission_stds[j], EPSILON)
            
            # Compute log-likelihood
            log_likelihood = np.sum(np.log(scaling + EPSILON))
            
            # Check convergence
            if abs(log_likelihood - prev_log_likelihood) < tolerance:
                break
            
            prev_log_likelihood = log_likelihood
        
        self.fitted = True
        self.log_likelihood = log_likelihood
        
        return {
            'log_likelihood': log_likelihood,
            'iterations': iteration + 1,
            'converged': iteration < max_iterations - 1
        }
    
    def predict_state(self, recent_observations: Union[List[float], np.ndarray]) -> np.ndarray:
        """
        Predict state probabilities for recent observations.
        
        Args:
            recent_observations: Recent volatility observations
            
        Returns:
            np.ndarray: Probability of each state for last observation
            
        Raises:
            RuntimeError: If model hasn't been fitted
        """
        if not self.fitted:
            raise RuntimeError("Model must be fitted before prediction")
        
        observations = np.asarray(recent_observations)
        if len(observations) == 0:
            raise ValueError("Need at least one observation for prediction")
        
        # Run forward algorithm
        forward, _ = self._forward_pass(observations)
        
        # Return probabilities for last observation
        state_probs = forward[-1, :]
        
        # Ensure normalization
        prob_sum = np.sum(state_probs)
        if prob_sum > EPSILON:
            state_probs /= prob_sum
        else:
            state_probs = np.ones(self.n_states) / self.n_states
        
        return state_probs
    
    def get_most_likely_states(self, observations: Union[List[float], np.ndarray]) -> np.ndarray:
        """
        Find most likely state sequence using Viterbi algorithm.
        
        Args:
            observations: Sequence of volatility observations
            
        Returns:
            np.ndarray: Most likely state sequence
        """
        if not self.fitted:
            raise RuntimeError("Model must be fitted before decoding")
        
        observations = np.asarray(observations)
        T = len(observations)
        
        # Viterbi algorithm
        viterbi = np.zeros((T, self.n_states))
        backtrack = np.zeros((T, self.n_states), dtype=int)
        
        # Initialize
        for j in range(self.n_states):
            viterbi[0, j] = np.log(self.initial_probs[j] + EPSILON) + \
                           np.log(self._gaussian_density(observations[0],
                                                        self.emission_means[j],
                                                        self.emission_stds[j]))
        
        # Recursion
        for t in range(1, T):
            for j in range(self.n_states):
                prob_transitions = viterbi[t-1, :] + np.log(self.transition_matrix[:, j] + EPSILON)
                backtrack[t, j] = np.argmax(prob_transitions)
                viterbi[t, j] = np.max(prob_transitions) + \
                               np.log(self._gaussian_density(observations[t],
                                                            self.emission_means[j],
                                                            self.emission_stds[j]))
        
        # Backtrack
        states = np.zeros(T, dtype=int)
        states[T-1] = np.argmax(viterbi[T-1, :])
        for t in range(T-2, -1, -1):
            states[t] = backtrack[t+1, states[t+1]]
        
        return states


# Auxiliary functions

def calculate_realized_volatility(returns: Union[List[float], np.ndarray, pd.Series], 
                                 window: int = 20) -> np.ndarray:
    """
    Calculate realized volatility using rolling window of returns.
    
    Realized volatility is calculated as the standard deviation of returns
    over a rolling window, annualized assuming 252 trading days.
    
    Args:
        returns: Array of returns (not log returns)
        window: Rolling window size for volatility calculation
        
    Returns:
        np.ndarray: Realized volatility for each point (NaN for initial points)
        
    Raises:
        ValueError: If window size is invalid
    """
    if window < 2:
        raise ValueError("Window must be at least 2")
    
    if isinstance(returns, pd.Series):
        # Use pandas rolling for efficiency if available
        vol = returns.rolling(window=window, min_periods=window).std()
        # Annualize assuming 252 trading days
        return vol.values * np.sqrt(252)
    else:
        returns = np.asarray(returns)
        T = len(returns)
        volatility = np.full(T, np.nan)
        
        for i in range(window - 1, T):
            window_returns = returns[i - window + 1:i + 1]
            # Calculate standard deviation
            if len(window_returns) == window:
                volatility[i] = np.std(window_returns, ddof=1) * np.sqrt(252)
        
        return volatility


def calculate_spread_zscore(spread: float, mean: float, std: float) -> float:
    """
    Calculate z-score of spread for normalized signal generation.
    
    Z-score indicates how many standard deviations the spread is from its mean,
    useful for identifying trading signals in pairs trading.
    
    Args:
        spread: Current spread value
        mean: Estimated mean of spread
        std: Standard deviation of spread
        
    Returns:
        float: Z-score of spread
        
    Raises:
        ValueError: If standard deviation is non-positive
    """
    if std <= 0:
        raise ValueError("Standard deviation must be positive")
    
    return (spread - mean) / std


def estimate_hedge_ratio(prices_x: Union[List[float], np.ndarray, pd.Series],
                        prices_y: Union[List[float], np.ndarray, pd.Series],
                        use_log_prices: bool = False) -> Dict[str, float]:
    """
    Estimate optimal hedge ratio for pairs trading using OLS regression.
    
    The hedge ratio (beta) minimizes the variance of the spread:
    spread = prices_y - beta * prices_x
    
    Args:
        prices_x: Prices of first instrument
        prices_y: Prices of second instrument  
        use_log_prices: Whether to use log prices for estimation
        
    Returns:
        Dict containing:
            - 'beta': Optimal hedge ratio
            - 'alpha': Intercept from regression
            - 'r_squared': R-squared of regression
            - 'residual_std': Standard deviation of residuals
            
    Raises:
        ValueError: If price arrays have different lengths or too few observations
    """
    # Convert to numpy arrays
    x = np.asarray(prices_x)
    y = np.asarray(prices_y)
    
    # Validate inputs
    if len(x) != len(y):
        raise ValueError("Price arrays must have same length")
    if len(x) < 3:
        raise ValueError("Need at least 3 observations for regression")
    if not np.all(np.isfinite(x)) or not np.all(np.isfinite(y)):
        raise ValueError("Prices must be finite")
    if np.any(x <= 0) or np.any(y <= 0):
        raise ValueError("Prices must be positive")
    
    # Transform to log prices if requested
    if use_log_prices:
        x = np.log(x)
        y = np.log(y)
    
    # Calculate regression coefficients using OLS
    # y = alpha + beta * x + epsilon
    
    n = len(x)
    x_mean = np.mean(x)
    y_mean = np.mean(y)
    
    # Calculate beta (slope)
    numerator = np.sum((x - x_mean) * (y - y_mean))
    denominator = np.sum((x - x_mean) ** 2)
    
    if abs(denominator) < EPSILON:
        # Perfect correlation or no variation in x
        warnings.warn("Insufficient variation in x prices for regression")
        beta = 1.0
    else:
        beta = numerator / denominator
    
    # Calculate alpha (intercept)
    alpha = y_mean - beta * x_mean
    
    # Calculate R-squared
    y_pred = alpha + beta * x
    ss_res = np.sum((y - y_pred) ** 2)
    ss_tot = np.sum((y - y_mean) ** 2)
    
    if ss_tot > EPSILON:
        r_squared = 1 - (ss_res / ss_tot)
    else:
        r_squared = 1.0 if ss_res < EPSILON else 0.0
    
    # Calculate residual standard deviation
    residuals = y - y_pred
    residual_std = np.std(residuals, ddof=2) if n > 2 else 0.0
    
    return {
        'beta': beta,
        'alpha': alpha,
        'r_squared': r_squared,
        'residual_std': residual_std
    }


def calculate_spread_from_prices(prices_x: Union[List[float], np.ndarray],
                                prices_y: Union[List[float], np.ndarray],
                                hedge_ratio: float) -> np.ndarray:
    """
    Calculate spread between two price series given a hedge ratio.
    
    Args:
        prices_x: Prices of first instrument
        prices_y: Prices of second instrument
        hedge_ratio: Beta coefficient for hedging
        
    Returns:
        np.ndarray: Spread series (y - beta * x)
    """
    x = np.asarray(prices_x)
    y = np.asarray(prices_y)
    
    if len(x) != len(y):
        raise ValueError("Price arrays must have same length")
    
    return y - hedge_ratio * x


def detect_spread_divergence(spread: float, 
                            kalman_filter: KalmanPairsFilter,
                            entry_threshold: float = 2.0,
                            exit_threshold: float = 0.5) -> str:
    """
    Detect trading signals based on spread divergence from Kalman-estimated mean.
    
    Args:
        spread: Current spread value
        kalman_filter: Fitted Kalman filter with spread history
        entry_threshold: Z-score threshold for entry signal
        exit_threshold: Z-score threshold for exit signal
        
    Returns:
        str: Signal type ('LONG', 'SHORT', 'EXIT', 'HOLD')
    """
    if not kalman_filter.initialized:
        return 'HOLD'
    
    mean = kalman_filter.get_estimated_mean()
    std = np.sqrt(kalman_filter.state_covariance)
    
    if std < EPSILON:
        return 'HOLD'
    
    z_score = calculate_spread_zscore(spread, mean, std)
    
    if z_score > entry_threshold:
        return 'SHORT'  # Spread too high, expect reversion down
    elif z_score < -entry_threshold:
        return 'LONG'   # Spread too low, expect reversion up
    elif abs(z_score) <= exit_threshold:
        return 'EXIT'   # Close to mean, close position
    else:
        return 'HOLD'

def calculate_spread(price_y: float, price_x: float, beta: float) -> float:
    """
    Calculate synthetic spread between two instruments.
    
    The spread is calculated as: spread = price_y - beta * price_x
    where beta is the hedge ratio that relates the two instruments.
    
    Args:
        price_y: Price of Y instrument (dependent variable)
        price_x: Price of X instrument (independent variable)
        beta: Hedge ratio (slope coefficient from regression)
    
    Returns:
        Spread value in units of price_y
    
    Example:
        >>> calculate_spread(1.0900, 1.2700, 0.85)
        0.01050
    """
    spread = price_y - beta * price_x
    return spread


def calculate_spread_zscore(spread: float, mean: float, std: float) -> float:
    """
    Calculate z-score of spread normalized by mean and standard deviation.
    
    Z-score measures how many standard deviations the spread is from its mean.
    Positive z-scores indicate spread above mean, negative indicate below mean.
    
    Args:
        spread: Current spread value
        mean: Mean of spread (typically from Kalman Filter)
        std: Standard deviation of spread
    
    Returns:
        Z-score (number of standard deviations from mean)
    
    Example:
        >>> calculate_spread_zscore(0.025, 0.010, 0.005)
        3.0
    """
    # Handle edge case of zero or very small std
    if std < 1e-10:
        return 0.0
    
    z_score = (spread - mean) / std
    return z_score


def detect_spread_divergence(
    z_score: float,
    entry_threshold: float = 2.0,
    exit_threshold: float = 0.5
) -> str:
    """
    Generate trading signal based on z-score of spread.
    
    Implements mean reversion logic for pairs trading:
    - LONG: Spread too low (z-score < -entry_threshold), expect reversion up
    - SHORT: Spread too high (z-score > entry_threshold), expect reversion down
    - EXIT: Spread near mean (|z-score| < exit_threshold), close positions
    - HOLD: No actionable signal
    
    Args:
        z_score: Current z-score of spread
        entry_threshold: Magnitude threshold for entry signals (default 2.0)
        exit_threshold: Magnitude threshold for exit signals (default 0.5)
    
    Returns:
        Signal string: 'LONG', 'SHORT', 'EXIT', or 'HOLD'
    
    Example:
        >>> detect_spread_divergence(2.5, entry_threshold=2.0)
        'SHORT'
        >>> detect_spread_divergence(-2.3, entry_threshold=2.0)
        'LONG'
        >>> detect_spread_divergence(0.3, exit_threshold=0.5)
        'EXIT'
    """
    abs_z = abs(z_score)
    
    # Exit signal: spread near mean
    if abs_z < exit_threshold:
        return 'EXIT'
    
    # Entry signals: spread significantly deviated
    if z_score > entry_threshold:
        # Spread too high: short the spread (short Y, long X)
        return 'SHORT'
    elif z_score < -entry_threshold:
        # Spread too low: long the spread (long Y, short X)
        return 'LONG'
    
    # No actionable signal
    return 'HOLD'