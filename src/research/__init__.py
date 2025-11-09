"""Research modules for backtesting and data science."""
from .backtesting_engine import (
    BacktestEngine, BacktestConfig, BacktestTrade, BacktestResults
)
from .labeling import triple_barrier_label, meta_labeling, calculate_label_statistics
from .purged_cv import PurgedKFold, CombinatorialPurgedKFold, calculate_sample_weights
from .drift_detection import ADWIN, SPRT, DriftDetector
from .feature_contracts import FeatureContract, FeatureContractRegistry

__all__ = [
    'BacktestEngine', 'BacktestConfig', 'BacktestTrade', 'BacktestResults',
    'triple_barrier_label', 'meta_labeling', 'calculate_label_statistics',
    'PurgedKFold', 'CombinatorialPurgedKFold', 'calculate_sample_weights',
    'ADWIN', 'SPRT', 'DriftDetector',
    'FeatureContract', 'FeatureContractRegistry'
]