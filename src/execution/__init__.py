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

# MANDATO 21: Execution mode framework
from .execution_mode import (
    ExecutionMode,
    parse_execution_mode,
    validate_execution_mode_config,
    get_execution_mode_from_config,
    DEFAULT_EXECUTION_MODE
)
from .execution_adapter import (
    ExecutionAdapter,
    ExecutionOrder,
    Position,
    AccountInfo
)
from .paper_execution_adapter import PaperExecutionAdapter
from .live_execution_adapter import LiveExecutionAdapter

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
    # MANDATO 21: Execution modes and adapters
    'ExecutionMode',
    'parse_execution_mode',
    'validate_execution_mode_config',
    'get_execution_mode_from_config',
    'DEFAULT_EXECUTION_MODE',
    'ExecutionAdapter',
    'ExecutionOrder',
    'Position',
    'AccountInfo',
    'PaperExecutionAdapter',
    'LiveExecutionAdapter'
]