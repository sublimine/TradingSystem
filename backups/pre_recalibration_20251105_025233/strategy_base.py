"""
Strategy Base Class - Foundation for Trading Strategy Integration
Defines required interface for all trading strategies
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Optional
from datetime import datetime
import pandas as pd
from dataclasses import dataclass


@dataclass
class Signal:
    """Trading signal with complete information for risk management."""
    timestamp: datetime
    symbol: str
    strategy_name: str
    direction: str
    entry_price: float
    stop_loss: float
    take_profit: float
    sizing_level: int
    metadata: Dict

    def validate(self) -> bool:
        """Validate signal has required fields with sensible values."""
        if self.direction not in ['LONG', 'SHORT']:
            return False

        if self.sizing_level < 1 or self.sizing_level > 5:
            return False

        if self.direction == 'LONG':
            if self.stop_loss >= self.entry_price:
                return False
            if self.take_profit <= self.entry_price:
                return False
        else:
            if self.stop_loss <= self.entry_price:
                return False
            if self.take_profit >= self.entry_price:
                return False

        return True


class StrategyBase(ABC):
    """
    Abstract base class for trading strategies.

    Supports two implementation patterns:
    1. Legacy pattern: implement analyze_market() and get_required_lookback_bars()
    2. Current pattern: implement evaluate() which receives pre-calculated features
    """

    def __init__(self, config: Dict):
        """
        Initialize strategy with configuration.

        Args:
            config: Dictionary containing strategy parameters
        """
        self.name = self.__class__.__name__
        self.config = config
        self.enabled = config.get('enabled', True)

    def analyze_market(self, symbol: str, historical_data: pd.DataFrame,
                      current_time: datetime) -> Optional[Signal]:
        """
        Analyze market conditions and generate signal if setup identified.
        
        Default implementation returns None. Strategies using evaluate() pattern
        do not need to override this method.

        Args:
            symbol: Symbol to analyze
            historical_data: DataFrame with OHLC data up to current_time
            current_time: Current timestamp in backtest or live trading

        Returns:
            Signal object if setup identified, None otherwise
        """
        return None

    def get_required_lookback_bars(self) -> int:
        """
        Return number of historical bars required for analysis.
        
        Default implementation returns 100 bars. Strategies should override
        if they require different lookback period.

        Returns:
            Minimum number of bars needed for indicators and logic
        """
        return 100

    def get_applicable_symbols(self) -> List[str]:
        """
        Return list of symbols this strategy trades.

        Default implementation returns all symbols from config.
        Override if strategy has specific symbol requirements.
        """
        return self.config.get('symbols', [])

    def should_generate_signals(self, market_conditions: Dict) -> bool:
        """
        Determine if strategy should generate signals given market conditions.

        Allows strategy to pause during unfavorable environments.
        Default implementation always returns True.

        Args:
            market_conditions: Dictionary with market state information

        Returns:
            True if strategy should generate signals, False to pause
        """
        return self.enabled

    def get_strategy_info(self) -> Dict:
        """
        Return dictionary with strategy information for reporting.

        Returns:
            Dictionary with name, description, parameters, etc.
        """
        return {
            'name': self.name,
            'enabled': self.enabled,
            'symbols': self.get_applicable_symbols(),
            'lookback_bars': self.get_required_lookback_bars()
        }
    
    def validate_inputs(self, market_data: pd.DataFrame, features: Dict) -> bool:
        """
        Validate that required inputs are present for strategy evaluation.
        
        Args:
            market_data: DataFrame with OHLC data
            features: Dictionary of calculated features
            
        Returns:
            True if inputs are valid, False otherwise
        """
        if market_data is None or len(market_data) == 0:
            return False
        
        required_columns = ['open', 'high', 'low', 'close', 'volume']
        if not all(col in market_data.columns for col in required_columns):
            return False
        
        return True
