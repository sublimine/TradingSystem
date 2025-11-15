"""
Metrics Exporter - MANDATO 26

Generates JSON snapshots of key system metrics for monitoring/alerting.

Usage:
    from src.monitoring.metrics_exporter import MetricsExporter

    exporter = MetricsExporter(capital=10000)
    snapshot = exporter.export_snapshot()

Author: SUBLIMINE SRE Team
Date: 2025-11-15
Mandate: M26 - Production Hardening
"""

import json
from datetime import datetime
from typing import Dict, List, Optional, Any
from pathlib import Path
from dataclasses import dataclass, asdict
import logging

logger = logging.getLogger(__name__)


@dataclass
class KillSwitchMetrics:
    """Kill Switch status metrics."""
    state: str
    reason: Optional[str]
    blocked_since: Optional[str]
    total_blocks: int


@dataclass
class PositionMetrics:
    """Position and exposure metrics."""
    open_positions: int
    total_exposure_pct: float
    max_exposure_pct: float
    positions_by_symbol: Dict[str, float]  # symbol -> exposure %


@dataclass
class PnLMetrics:
    """P&L and performance metrics."""
    daily_pnl: float
    daily_pnl_pct: float
    current_drawdown: float
    max_drawdown: float
    total_trades_today: int
    winning_trades: int
    losing_trades: int


@dataclass
class SignalMetrics:
    """Signal quality and reject metrics."""
    signals_generated: int
    signals_rejected: int
    reject_rate_pct: float
    avg_signal_quality: float
    signals_by_strategy: Dict[str, int]


@dataclass
class MicrostructureMetrics:
    """Aggregated microstructure metrics."""
    symbols: List[str]
    avg_vpin: float
    avg_ofi: float
    avg_cvd: float
    extreme_vpin_count: int  # VPIN > 0.7


@dataclass
class SystemMetrics:
    """Complete system health snapshot."""
    timestamp: str
    mode: str  # RESEARCH, PAPER, LIVE
    uptime_seconds: float
    kill_switch: KillSwitchMetrics
    positions: PositionMetrics
    pnl: PnLMetrics
    signals: SignalMetrics
    microstructure: MicrostructureMetrics
    alerts: List[str]  # Active alerts/warnings


class MetricsExporter:
    """
    Exports system metrics to JSON snapshots.

    Designed for lightweight monitoring without full observability stack.
    """

    def __init__(self, capital: float = 10000.0):
        """
        Initialize metrics exporter.

        Args:
            capital: Initial/current capital for % calculations
        """
        self.capital = capital
        self.start_time = datetime.now()

    def export_snapshot(
        self,
        kill_switch_status: Optional[Dict] = None,
        position_manager: Optional[Any] = None,
        trade_history: Optional[List] = None,
        signal_history: Optional[List] = None,
        microstructure_engine: Optional[Any] = None,
        mode: str = "UNKNOWN"
    ) -> Dict:
        """
        Generate complete metrics snapshot.

        Args:
            kill_switch_status: KillSwitch status dict
            position_manager: PositionManager instance
            trade_history: List of completed trades
            signal_history: List of generated signals
            microstructure_engine: MicrostructureEngine instance
            mode: Trading mode (RESEARCH/PAPER/LIVE)

        Returns:
            Dict with complete metrics snapshot
        """
        snapshot = SystemMetrics(
            timestamp=datetime.now().isoformat(),
            mode=mode,
            uptime_seconds=(datetime.now() - self.start_time).total_seconds(),
            kill_switch=self._collect_kill_switch_metrics(kill_switch_status),
            positions=self._collect_position_metrics(position_manager),
            pnl=self._collect_pnl_metrics(trade_history),
            signals=self._collect_signal_metrics(signal_history),
            microstructure=self._collect_microstructure_metrics(microstructure_engine),
            alerts=self._generate_alerts(
                kill_switch_status,
                position_manager,
                trade_history,
                signal_history
            )
        )

        return asdict(snapshot)

    def _collect_kill_switch_metrics(self, kill_switch_status: Optional[Dict]) -> KillSwitchMetrics:
        """Collect Kill Switch metrics."""
        if not kill_switch_status:
            return KillSwitchMetrics(
                state="UNKNOWN",
                reason=None,
                blocked_since=None,
                total_blocks=0
            )

        return KillSwitchMetrics(
            state=kill_switch_status.get('state', 'UNKNOWN'),
            reason=kill_switch_status.get('reason'),
            blocked_since=kill_switch_status.get('blocked_since'),
            total_blocks=kill_switch_status.get('total_blocks', 0)
        )

    def _collect_position_metrics(self, position_manager: Optional[Any]) -> PositionMetrics:
        """Collect position and exposure metrics."""
        if not position_manager:
            return PositionMetrics(
                open_positions=0,
                total_exposure_pct=0.0,
                max_exposure_pct=0.0,
                positions_by_symbol={}
            )

        try:
            positions = getattr(position_manager, 'positions', {})
            total_exposure = 0.0
            positions_by_symbol = {}

            for symbol, position in positions.items():
                exposure_pct = (abs(position.get('value', 0)) / self.capital) * 100
                positions_by_symbol[symbol] = round(exposure_pct, 2)
                total_exposure += exposure_pct

            max_exposure = max(positions_by_symbol.values()) if positions_by_symbol else 0.0

            return PositionMetrics(
                open_positions=len(positions),
                total_exposure_pct=round(total_exposure, 2),
                max_exposure_pct=round(max_exposure, 2),
                positions_by_symbol=positions_by_symbol
            )
        except Exception as e:
            logger.warning(f"Error collecting position metrics: {e}")
            return PositionMetrics(
                open_positions=0,
                total_exposure_pct=0.0,
                max_exposure_pct=0.0,
                positions_by_symbol={}
            )

    def _collect_pnl_metrics(self, trade_history: Optional[List]) -> PnLMetrics:
        """Collect P&L metrics."""
        if not trade_history:
            return PnLMetrics(
                daily_pnl=0.0,
                daily_pnl_pct=0.0,
                current_drawdown=0.0,
                max_drawdown=0.0,
                total_trades_today=0,
                winning_trades=0,
                losing_trades=0
            )

        try:
            # Filter today's trades
            today = datetime.now().date()
            today_trades = [
                t for t in trade_history
                if hasattr(t, 'timestamp') and t.timestamp.date() == today
            ]

            # Calculate daily P&L
            daily_pnl = sum(t.pnl for t in today_trades if hasattr(t, 'pnl'))
            daily_pnl_pct = (daily_pnl / self.capital) * 100 if self.capital > 0 else 0.0

            # Calculate drawdown
            cumulative_pnl = [t.cumulative_pnl for t in trade_history if hasattr(t, 'cumulative_pnl')]
            if cumulative_pnl:
                peak = max(cumulative_pnl)
                current = cumulative_pnl[-1]
                current_drawdown = peak - current
                max_drawdown = max(peak - pnl for pnl in cumulative_pnl)
            else:
                current_drawdown = 0.0
                max_drawdown = 0.0

            # Win/loss counts
            winning = sum(1 for t in today_trades if hasattr(t, 'pnl') and t.pnl > 0)
            losing = sum(1 for t in today_trades if hasattr(t, 'pnl') and t.pnl < 0)

            return PnLMetrics(
                daily_pnl=round(daily_pnl, 2),
                daily_pnl_pct=round(daily_pnl_pct, 2),
                current_drawdown=round(current_drawdown, 2),
                max_drawdown=round(max_drawdown, 2),
                total_trades_today=len(today_trades),
                winning_trades=winning,
                losing_trades=losing
            )
        except Exception as e:
            logger.warning(f"Error collecting P&L metrics: {e}")
            return PnLMetrics(
                daily_pnl=0.0,
                daily_pnl_pct=0.0,
                current_drawdown=0.0,
                max_drawdown=0.0,
                total_trades_today=0,
                winning_trades=0,
                losing_trades=0
            )

    def _collect_signal_metrics(self, signal_history: Optional[List]) -> SignalMetrics:
        """Collect signal quality and reject metrics."""
        if not signal_history:
            return SignalMetrics(
                signals_generated=0,
                signals_rejected=0,
                reject_rate_pct=0.0,
                avg_signal_quality=0.0,
                signals_by_strategy={}
            )

        try:
            # Filter last 100 signals
            recent_signals = signal_history[-100:] if len(signal_history) > 100 else signal_history

            total = len(recent_signals)
            rejected = sum(1 for s in recent_signals if getattr(s, 'rejected', False))
            reject_rate = (rejected / total * 100) if total > 0 else 0.0

            # Average quality score
            quality_scores = [
                s.metadata.get('confirmation_score', 0)
                for s in recent_signals
                if hasattr(s, 'metadata') and 'confirmation_score' in s.metadata
            ]
            avg_quality = sum(quality_scores) / len(quality_scores) if quality_scores else 0.0

            # Count by strategy
            signals_by_strategy = {}
            for s in recent_signals:
                strategy = getattr(s, 'strategy_name', 'UNKNOWN')
                signals_by_strategy[strategy] = signals_by_strategy.get(strategy, 0) + 1

            return SignalMetrics(
                signals_generated=total,
                signals_rejected=rejected,
                reject_rate_pct=round(reject_rate, 2),
                avg_signal_quality=round(avg_quality, 2),
                signals_by_strategy=signals_by_strategy
            )
        except Exception as e:
            logger.warning(f"Error collecting signal metrics: {e}")
            return SignalMetrics(
                signals_generated=0,
                signals_rejected=0,
                reject_rate_pct=0.0,
                avg_signal_quality=0.0,
                signals_by_strategy={}
            )

    def _collect_microstructure_metrics(self, microstructure_engine: Optional[Any]) -> MicrostructureMetrics:
        """Collect aggregated microstructure metrics."""
        if not microstructure_engine:
            return MicrostructureMetrics(
                symbols=[],
                avg_vpin=0.0,
                avg_ofi=0.0,
                avg_cvd=0.0,
                extreme_vpin_count=0
            )

        try:
            # Get features for all symbols
            features_cache = getattr(microstructure_engine, 'features_cache', {})

            if not features_cache:
                return MicrostructureMetrics(
                    symbols=[],
                    avg_vpin=0.0,
                    avg_ofi=0.0,
                    avg_cvd=0.0,
                    extreme_vpin_count=0
                )

            symbols = list(features_cache.keys())
            vpins = []
            ofis = []
            cvds = []
            extreme_vpin_count = 0

            for symbol, features in features_cache.items():
                if hasattr(features, 'vpin'):
                    vpins.append(features.vpin)
                    if features.vpin > 0.7:
                        extreme_vpin_count += 1
                if hasattr(features, 'ofi'):
                    ofis.append(features.ofi)
                if hasattr(features, 'cvd'):
                    cvds.append(features.cvd)

            return MicrostructureMetrics(
                symbols=symbols,
                avg_vpin=round(sum(vpins) / len(vpins), 3) if vpins else 0.0,
                avg_ofi=round(sum(ofis) / len(ofis), 3) if ofis else 0.0,
                avg_cvd=round(sum(cvds) / len(cvds), 1) if cvds else 0.0,
                extreme_vpin_count=extreme_vpin_count
            )
        except Exception as e:
            logger.warning(f"Error collecting microstructure metrics: {e}")
            return MicrostructureMetrics(
                symbols=[],
                avg_vpin=0.0,
                avg_ofi=0.0,
                avg_cvd=0.0,
                extreme_vpin_count=0
            )

    def _generate_alerts(
        self,
        kill_switch_status: Optional[Dict],
        position_manager: Optional[Any],
        trade_history: Optional[List],
        signal_history: Optional[List]
    ) -> List[str]:
        """Generate active alerts based on thresholds."""
        alerts = []

        # Kill Switch alert
        if kill_switch_status and kill_switch_status.get('state') == 'BLOCKED':
            alerts.append(f"🚨 KILL SWITCH BLOCKED: {kill_switch_status.get('reason', 'Unknown')}")

        # Position exposure alert
        if position_manager:
            try:
                positions = getattr(position_manager, 'positions', {})
                total_exposure = sum(
                    abs(p.get('value', 0)) / self.capital * 100
                    for p in positions.values()
                )
                if total_exposure > 200:  # >200% exposure
                    alerts.append(f"⚠️ HIGH EXPOSURE: {total_exposure:.1f}% (threshold: 200%)")
            except:
                pass

        # Daily loss alert
        if trade_history:
            try:
                today = datetime.now().date()
                today_trades = [
                    t for t in trade_history
                    if hasattr(t, 'timestamp') and t.timestamp.date() == today
                ]
                daily_pnl = sum(t.pnl for t in today_trades if hasattr(t, 'pnl'))
                daily_loss_pct = abs(daily_pnl / self.capital * 100) if daily_pnl < 0 else 0

                if daily_loss_pct > 2:  # >2% daily loss
                    alerts.append(f"⚠️ DAILY LOSS: -{daily_loss_pct:.1f}% (threshold: -2%)")
            except:
                pass

        # Reject rate alert
        if signal_history:
            try:
                recent = signal_history[-100:] if len(signal_history) > 100 else signal_history
                rejected = sum(1 for s in recent if getattr(s, 'rejected', False))
                reject_rate = (rejected / len(recent) * 100) if recent else 0

                if reject_rate > 50:  # >50% reject rate
                    alerts.append(f"⚠️ HIGH REJECT RATE: {reject_rate:.1f}% (threshold: 50%)")
            except:
                pass

        # Extreme VPIN alert
        try:
            # This would need microstructure_engine passed in, simplifying for now
            pass
        except:
            pass

        return alerts

    def save_snapshot(self, snapshot: Dict, filepath: Optional[Path] = None) -> Path:
        """
        Save snapshot to JSON file.

        Args:
            snapshot: Metrics snapshot dict
            filepath: Optional custom filepath

        Returns:
            Path to saved file
        """
        if filepath is None:
            reports_dir = Path('reports/health')
            reports_dir.mkdir(parents=True, exist_ok=True)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filepath = reports_dir / f"metrics_snapshot_{timestamp}.json"

        with open(filepath, 'w') as f:
            json.dump(snapshot, f, indent=2)

        logger.info(f"Metrics snapshot saved: {filepath}")
        return filepath
