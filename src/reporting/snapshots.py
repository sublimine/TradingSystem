#!/usr/bin/env python3
"""
Periodic Snapshots - Position & Risk State Capture

Captura snapshots periódicos del estado del sistema:
- Posiciones activas + P&L unrealized
- Métricas de riesgo (exposure, drawdown, límites)
- Estado del circuit breaker
- Correlaciones

Mandato: MANDATO 13 - Reporting Hooks
Fecha: 2025-11-14

Uso:
    from src.reporting.snapshots import capture_position_snapshot, capture_risk_snapshot

    # Capturar snapshot de posiciones
    snapshot = capture_position_snapshot(position_manager, market_data)

    # Capturar snapshot de riesgo
    risk_snapshot = capture_risk_snapshot(risk_manager, position_manager)
"""

import logging
from datetime import datetime
from typing import Dict, List, Optional, Any
import pandas as pd

logger = logging.getLogger(__name__)


def capture_position_snapshot(
    position_manager,
    market_data: Dict[str, pd.DataFrame],
    timestamp: Optional[datetime] = None
) -> Dict[str, Any]:
    """
    Captura snapshot del estado de posiciones.

    Args:
        position_manager: MarketStructurePositionManager instance
        market_data: Current market data dict {symbol: DataFrame}
        timestamp: Snapshot timestamp (default: now)

    Returns:
        Position snapshot dict con todas las posiciones activas
    """
    if timestamp is None:
        timestamp = datetime.now()

    try:
        active_positions = position_manager.get_active_positions()

        positions_data = []
        total_unrealized_r = 0.0
        total_exposure_pct = 0.0

        for position_id, tracker in active_positions.items():
            symbol = tracker.symbol

            # Get current price
            current_price = None
            if symbol in market_data and not market_data[symbol].empty:
                current_price = market_data[symbol].iloc[-1]['close']
            else:
                logger.warning(f"No market data for {symbol} in snapshot")
                continue

            # Calculate current metrics
            unrealized_r = tracker.get_unrealized_r_multiple(current_price)

            # Calculate unrealized P&L in pips
            if tracker.direction == 'LONG':
                unrealized_pips = current_price - tracker.entry_price
            else:
                unrealized_pips = tracker.entry_price - current_price

            position_info = {
                'position_id': position_id,
                'symbol': symbol,
                'strategy_id': tracker.strategy,
                'direction': tracker.direction,
                'entry_price': tracker.entry_price,
                'current_price': current_price,
                'stop_loss': tracker.current_stop,
                'take_profit': tracker.current_target,
                'lot_size': tracker.lot_size,
                'remaining_lots': tracker.remaining_lots,
                'unrealized_r': unrealized_r,
                'unrealized_pips': unrealized_pips,
                'mfe': tracker.max_favorable_excursion,
                'mae': tracker.max_adverse_excursion,
                'is_risk_free': tracker.is_risk_free,
                'opened_at': tracker.opened_at,
                'duration_minutes': (timestamp - tracker.opened_at).total_seconds() / 60.0,
                'partial_exits': len(tracker.partial_exits),
            }

            positions_data.append(position_info)
            total_unrealized_r += unrealized_r
            # Approximate exposure (simplified)
            total_exposure_pct += (tracker.remaining_lots * 0.01)  # Rough estimate

        snapshot = {
            'timestamp': timestamp,
            'snapshot_type': 'POSITION',
            'num_positions': len(positions_data),
            'positions': positions_data,
            'total_unrealized_r': total_unrealized_r,
            'total_exposure_pct': total_exposure_pct,
            'symbols': list(set(p['symbol'] for p in positions_data)),
        }

        logger.debug(f"Position snapshot captured: {len(positions_data)} positions, {total_unrealized_r:.2f}R unrealized")

        return snapshot

    except Exception as e:
        logger.error(f"Failed to capture position snapshot: {e}")
        return {
            'timestamp': timestamp,
            'snapshot_type': 'POSITION',
            'num_positions': 0,
            'positions': [],
            'error': str(e)
        }


def capture_risk_snapshot(
    risk_manager,
    position_manager,
    timestamp: Optional[datetime] = None
) -> Dict[str, Any]:
    """
    Captura snapshot del estado de riesgo.

    Args:
        risk_manager: InstitutionalRiskManager instance
        position_manager: MarketStructurePositionManager instance
        timestamp: Snapshot timestamp (default: now)

    Returns:
        Risk snapshot dict con métricas de riesgo
    """
    if timestamp is None:
        timestamp = datetime.now()

    try:
        # Get risk manager stats
        stats = risk_manager.get_statistics()

        # Circuit breaker status
        can_trade, cb_reason = risk_manager.check_circuit_breaker()
        cb_stats = stats.get('circuit_breaker', {})

        # Exposure metrics
        exposure_stats = stats.get('exposure', {})

        # Position metrics
        active_positions = position_manager.get_active_positions()
        risk_free_count = sum(1 for t in active_positions.values() if t.is_risk_free)

        snapshot = {
            'timestamp': timestamp,
            'snapshot_type': 'RISK',

            # Circuit Breaker
            'circuit_breaker_status': 'OPEN' if not can_trade else 'CLOSED',
            'circuit_breaker_reason': cb_reason if not can_trade else None,
            'consecutive_losses': cb_stats.get('consecutive_losses', 0),
            'loss_probability_z': cb_stats.get('loss_probability_z', 0.0),
            'daily_dd_pct': cb_stats.get('daily_dd_pct', 0.0),

            # Drawdown
            'current_equity': stats['current_equity'],
            'peak_equity': stats['peak_equity'],
            'current_drawdown_pct': stats['current_drawdown_pct'],
            'max_drawdown_pct': stats['max_drawdown_pct'],

            # Exposure
            'total_exposure_pct': exposure_stats.get('total_exposure_pct', 0.0),
            'max_exposure_allowed': exposure_stats.get('max_exposure_allowed', 6.0),
            'exposure_utilization': exposure_stats.get('exposure_utilization_pct', 0.0),

            # Positions
            'active_positions': len(active_positions),
            'max_positions_allowed': stats.get('max_positions', 5),
            'risk_free_positions': risk_free_count,

            # Daily P&L
            'daily_pnl_pct': stats.get('daily_pnl_pct', 0.0),
            'daily_pnl_r': stats.get('daily_pnl_r', 0.0),

            # Limits
            'approaching_limits': []
        }

        # Check if approaching limits
        if snapshot['exposure_utilization'] > 80:
            snapshot['approaching_limits'].append('EXPOSURE_HIGH')

        if snapshot['current_drawdown_pct'] > (snapshot['max_drawdown_pct'] * 0.8):
            snapshot['approaching_limits'].append('DRAWDOWN_HIGH')

        if len(active_positions) >= stats.get('max_positions', 5):
            snapshot['approaching_limits'].append('MAX_POSITIONS')

        logger.debug(
            f"Risk snapshot captured: "
            f"CB={'OPEN' if not can_trade else 'CLOSED'}, "
            f"DD={snapshot['current_drawdown_pct']:.2f}%, "
            f"Exposure={snapshot['total_exposure_pct']:.2f}%"
        )

        return snapshot

    except Exception as e:
        logger.error(f"Failed to capture risk snapshot: {e}")
        return {
            'timestamp': timestamp,
            'snapshot_type': 'RISK',
            'error': str(e)
        }


def save_position_snapshot_to_db(snapshot: Dict, db) -> bool:
    """
    Guarda position snapshot a la base de datos.

    Transforma el snapshot en formato de filas individuales para la DB.

    Args:
        snapshot: Position snapshot dict (from capture_position_snapshot)
        db: ReportingDatabase instance

    Returns:
        True if saved successfully (or fallback)
    """
    try:
        if 'error' in snapshot:
            logger.error(f"Cannot save snapshot with error: {snapshot['error']}")
            return False

        timestamp = snapshot['timestamp']
        positions = snapshot.get('positions', [])

        if not positions:
            logger.debug("No positions to save in snapshot")
            return True

        # Convert each position to DB row format
        success_count = 0
        for pos in positions:
            db_row = {
                'timestamp': timestamp,
                'symbol': pos['symbol'],
                'strategy_id': pos['strategy_id'],
                'trade_id': pos['position_id'],
                'direction': pos['direction'],
                'quantity': pos['remaining_lots'],
                'entry_price': pos['entry_price'],
                'current_price': pos['current_price'],
                'unrealized_pnl': pos['unrealized_r'],  # Using R multiple as PnL metric
                'risk_allocated_pct': 0.0,  # TODO: Get from position if available
                'stop_loss': pos['stop_loss'],
                'take_profit': pos['take_profit'],
                'asset_class': pos['symbol'][:3] if len(pos['symbol']) >= 6 else 'FX',  # Rough classification
                'region': 'GLOBAL',  # TODO: Map symbol to region
                'risk_cluster': pos['strategy_id']  # Use strategy as risk cluster
            }

            if db.insert_position_snapshot(db_row):
                success_count += 1

        logger.debug(f"Saved {success_count}/{len(positions)} position snapshots to DB")
        return success_count > 0

    except Exception as e:
        logger.error(f"Failed to save position snapshot to DB: {e}")
        return False


def save_risk_snapshot_to_db(snapshot: Dict, db) -> bool:
    """
    Guarda risk snapshot a la base de datos.

    Args:
        snapshot: Risk snapshot dict (from capture_risk_snapshot)
        db: ReportingDatabase instance

    Returns:
        True if saved successfully (or fallback)
    """
    try:
        if 'error' in snapshot:
            logger.error(f"Cannot save snapshot with error: {snapshot['error']}")
            return False

        # Transform snapshot to DB format
        db_row = {
            'timestamp': snapshot['timestamp'],
            'total_risk_used_pct': snapshot.get('total_exposure_pct', 0.0),
            'total_risk_available_pct': snapshot.get('max_exposure_allowed', 6.0) - snapshot.get('total_exposure_pct', 0.0),
            'max_risk_allowed_pct': snapshot.get('max_exposure_allowed', 6.0),
            'risk_by_asset_class': {},  # TODO: Breakdown by asset class
            'risk_by_region': {},  # TODO: Breakdown by region
            'risk_by_strategy': {},  # TODO: Breakdown by strategy
            'risk_by_cluster': {},  # TODO: Breakdown by cluster
            'symbols_at_limit': [],  # TODO: Track symbols at limit
            'strategies_at_limit': [],  # TODO: Track strategies at limit
            'clusters_at_limit': [],  # TODO: Track clusters at limit
            'portfolio_correlation_avg': 0.0,  # TODO: Calculate correlation
            'herfindahl_index': 0.0,  # TODO: Calculate HHI
            'rejections_last_hour': 0,  # TODO: Track rejections
            'circuit_breaker_active': snapshot.get('circuit_breaker_status') == 'OPEN'
        }

        success = db.insert_risk_snapshot(db_row)

        if success:
            logger.debug("Risk snapshot saved to DB")
        else:
            logger.warning("Risk snapshot fallback to file")

        return success

    except Exception as e:
        logger.error(f"Failed to save risk snapshot to DB: {e}")
        return False


class SnapshotScheduler:
    """
    Scheduler for periodic snapshots.

    Maneja el timing de snapshots periódicos sin bloquear el trading loop.
    """

    def __init__(self, interval_minutes: int = 15):
        """
        Args:
            interval_minutes: Intervalo entre snapshots (default: 15 min)
        """
        self.interval_minutes = interval_minutes
        self.last_snapshot_time: Optional[datetime] = None

        logger.info(f"SnapshotScheduler initialized (interval: {interval_minutes} min)")

    def should_capture(self, current_time: Optional[datetime] = None) -> bool:
        """
        Determina si es momento de capturar snapshot.

        Args:
            current_time: Tiempo actual (default: now)

        Returns:
            True si debe capturar snapshot
        """
        if current_time is None:
            current_time = datetime.now()

        # First snapshot
        if self.last_snapshot_time is None:
            return True

        # Check interval
        elapsed_minutes = (current_time - self.last_snapshot_time).total_seconds() / 60.0

        return elapsed_minutes >= self.interval_minutes

    def mark_captured(self, capture_time: Optional[datetime] = None):
        """
        Marca que se capturó un snapshot.

        Args:
            capture_time: Tiempo de captura (default: now)
        """
        if capture_time is None:
            capture_time = datetime.now()

        self.last_snapshot_time = capture_time
        logger.debug(f"Snapshot marked as captured at {capture_time}")

    def reset(self):
        """Reset scheduler."""
        self.last_snapshot_time = None
        logger.info("SnapshotScheduler reset")
