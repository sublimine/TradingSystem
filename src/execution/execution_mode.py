"""
Execution Mode Framework - MANDATO 21

Defines execution modes for the trading system:
- RESEARCH: Backtesting and calibration (historical data)
- PAPER: Demo/paper trading (simulated execution, no real orders)
- LIVE: Live trading (real broker, real money)

Author: SUBLIMINE Institutional Trading System
Date: 2025-11-14
Mandato: MANDATO 21 - Paper Trading Institucional
"""

from enum import Enum
import logging

logger = logging.getLogger(__name__)


class ExecutionMode(Enum):
    """
    Trading system execution modes.

    RESEARCH: Historical backtesting and calibration
        - Uses historical data (CSV, database)
        - No connection to broker
        - No real or simulated execution
        - Used for MANDATO 17-19 (backtest, calibration)

    PAPER: Paper/demo trading
        - Uses live or simulated market feed
        - Simulated execution (NO real broker orders)
        - Full risk management and reporting active
        - Same logic as LIVE but with virtual fills
        - ZERO risk of real money loss

    LIVE: Live production trading
        - Uses live market feed
        - Real broker execution
        - Real money at risk
        - Requires explicit confirmation
    """

    RESEARCH = "research"
    PAPER = "paper"
    LIVE = "live"

    def is_paper(self) -> bool:
        """Check if mode is PAPER."""
        return self == ExecutionMode.PAPER

    def is_live(self) -> bool:
        """Check if mode is LIVE."""
        return self == ExecutionMode.LIVE

    def is_research(self) -> bool:
        """Check if mode is RESEARCH."""
        return self == ExecutionMode.RESEARCH

    def allows_real_execution(self) -> bool:
        """Check if mode allows real broker execution."""
        return self == ExecutionMode.LIVE

    def requires_broker_connection(self) -> bool:
        """Check if mode requires broker connection (MT5, etc.)."""
        # PAPER can use MT5 demo for data feed
        # LIVE must use MT5 real
        return self in [ExecutionMode.PAPER, ExecutionMode.LIVE]

    def __str__(self) -> str:
        return self.value.upper()

    def __repr__(self) -> str:
        return f"ExecutionMode.{self.name}"


def parse_execution_mode(mode_str: str) -> ExecutionMode:
    """
    Parse execution mode from string.

    Args:
        mode_str: Mode string ('research', 'paper', 'live')

    Returns:
        ExecutionMode enum

    Raises:
        ValueError: If mode string is invalid
    """
    mode_str = mode_str.lower().strip()

    try:
        return ExecutionMode(mode_str)
    except ValueError:
        valid_modes = [m.value for m in ExecutionMode]
        raise ValueError(
            f"Invalid execution mode: '{mode_str}'. "
            f"Valid modes: {valid_modes}"
        )


def validate_execution_mode_config(mode: ExecutionMode, config: dict) -> bool:
    """
    Validate that config is compatible with execution mode.

    Args:
        mode: Execution mode
        config: System configuration dict

    Returns:
        True if valid, raises ValueError if invalid

    Raises:
        ValueError: If config is incompatible with mode
    """
    # LIVE mode validations
    if mode == ExecutionMode.LIVE:
        # Require explicit capital specification
        if 'capital' not in config or config.get('capital', 0) <= 0:
            raise ValueError(
                "LIVE mode requires 'capital' > 0 in config"
            )

        # Warn if risk limits are too aggressive
        max_risk = config.get('risk', {}).get('max_risk_per_trade', 0)
        if max_risk > 0.02:
            logger.warning(
                f"⚠️  LIVE mode with high risk per trade: {max_risk:.2%}"
            )

    # PAPER mode validations
    if mode == ExecutionMode.PAPER:
        # Ensure paper execution is enabled
        execution_config = config.get('execution', {})
        if execution_config.get('force_real_execution', False):
            raise ValueError(
                "PAPER mode incompatible with 'force_real_execution=true'"
            )

    return True


# Default execution mode (if not specified)
DEFAULT_EXECUTION_MODE = ExecutionMode.PAPER


def get_execution_mode_from_config(config: dict) -> ExecutionMode:
    """
    Get execution mode from config dict.

    Args:
        config: System configuration dict

    Returns:
        ExecutionMode enum
    """
    mode_str = config.get('execution_mode', DEFAULT_EXECUTION_MODE.value)
    return parse_execution_mode(mode_str)
