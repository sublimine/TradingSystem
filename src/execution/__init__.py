"""Execution modules for market connectivity and order management."""
from .data_validator import DataValidator, ValidationResult, ValidationSeverity
from .data_sources import (
    MultiSourceDataManager, DataSource, PostgreSQLSource, MT5Source,
    SourceStatus, SourceHealth
)
from .broker_client import (
    BrokerClient, Order, OrderType, OrderSide, OrderStatus, RejectReason
)
from .lp_analytics import LPAnalytics, LPMetrics
from .tca_engine import TCAEngine, TCAPreTrade, TCAAtTrade, TCAPostTrade
from .circuit_breakers import CircuitBreakerManager, BreakerType, BreakerConfig
from .venue_simulator import VenueSimulator
from .capacity_model import CapacityModel

# MANDATO 23: Live Execution & Kill Switch
from .execution_mode import ExecutionMode
from .execution_adapter import ExecutionAdapter, AccountInfo, Position, OrderResult
from .paper_execution_adapter import PaperExecutionAdapter
from .live_execution_adapter import LiveExecutionAdapter
from .kill_switch import KillSwitch, KillSwitchState, KillSwitchStatus

__all__ = [
    'DataValidator', 'ValidationResult', 'ValidationSeverity',
    'MultiSourceDataManager', 'DataSource', 'PostgreSQLSource', 'MT5Source',
    'SourceStatus', 'SourceHealth',
    'BrokerClient', 'Order', 'OrderType', 'OrderSide', 'OrderStatus', 'RejectReason',
    'LPAnalytics', 'LPMetrics',
    'TCAEngine', 'TCAPreTrade', 'TCAAtTrade', 'TCAPostTrade',
    'CircuitBreakerManager', 'BreakerType', 'BreakerConfig',
    'VenueSimulator',
    'CapacityModel',
    # MANDATO 23
    'ExecutionMode',
    'ExecutionAdapter', 'AccountInfo', 'Position', 'OrderResult',
    'PaperExecutionAdapter',
    'LiveExecutionAdapter',
    'KillSwitch', 'KillSwitchState', 'KillSwitchStatus'
]