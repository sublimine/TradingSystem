"""
Execution modules for market connectivity and order management.

PLAN OMEGA FASE 3.2: Added ExecutionMode + Adapters
"""
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

# PLAN OMEGA FASE 3.2: ExecutionMode + Adapters
from .execution_mode import ExecutionMode, ExecutionConfig
from .broker_adapter import BrokerAdapter, Order as BrokerOrder, Position
from .paper_broker import PaperBrokerAdapter
from .live_broker import LiveBrokerAdapter
from .execution_manager import ExecutionManager

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
    # PLAN OMEGA FASE 3.2
    'ExecutionMode', 'ExecutionConfig',
    'BrokerAdapter', 'BrokerOrder', 'Position',
    'PaperBrokerAdapter', 'LiveBrokerAdapter',
    'ExecutionManager',
]