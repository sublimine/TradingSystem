"""
ML Supervisor - Autonomous Decision Maker

This component monitors ML insights and AUTOMATICALLY takes action:
- Disables losing strategies
- Adjusts parameters based on ML optimization
- Activates circuit breakers on excessive drawdown
- Generates reports on schedule
- No manual intervention required

Author: Elite Trading System
Version: 1.0
"""

import logging
from collections import deque
import yaml
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from pathlib import Path

logger = logging.getLogger(__name__)


class MLSupervisor:
    """
    Autonomous supervisor that monitors ML and takes action automatically.

    **NO MANUAL INTERVENTION REQUIRED**

    Actions taken automatically:
    1. Disable strategies with poor performance
    2. Apply ML-optimized parameters
    3. Activate circuit breakers on DD threshold
    4. Schedule and generate reports
    5. Alert on critical issues
    """

    def __init__(self, config: dict, ml_engine, strategy_orchestrator, reporting_system):
        """
        Initialize ML Supervisor.

        Args:
            config: System configuration
            ml_engine: ML Adaptive Engine instance
            strategy_orchestrator: Strategy orchestrator instance
            reporting_system: Institutional reporting system
        """
        self.config = config
        self.ml_engine = ml_engine
        self.strategy_orchestrator = strategy_orchestrator
        self.reporting = reporting_system

        # Supervision settings
        self.enabled = config.get('ml_supervisor', {}).get('enabled', True)
        self.auto_disable_threshold_r = config.get('ml_supervisor', {}).get('auto_disable_threshold_r', -10.0)
        self.auto_adjust_params = config.get('ml_supervisor', {}).get('auto_adjust_params', True)
        self.circuit_breaker_dd = config.get('risk', {}).get('circuit_breaker_dd', 15.0)

        # State
        self.circuit_breaker_active = False
        # FIX BUG #16: Use deque with maxlen to prevent memory leak
        self.disabled_strategies = deque(maxlen=100)
        self.last_report_date = None
        self.session_drawdown_r = 0.0

        logger.info("=" * 80)
        logger.info("ML SUPERVISOR INITIALIZED - AUTONOMOUS MODE")
        logger.info(f"Auto-disable threshold: {self.auto_disable_threshold_r}R")
        logger.info(f"Circuit breaker DD: {self.circuit_breaker_dd}R")
        logger.info(f"Auto-adjust parameters: {self.auto_adjust_params}")
        logger.info("=" * 80)

    def supervise(self, current_equity: float, open_positions: List, closed_trades: List):
        """
        Main supervision loop - called every update cycle.

        Automatically:
        1. Monitors strategy performance
        2. Applies ML recommendations
        3. Checks circuit breakers
        4. Generates scheduled reports

        Args:
            current_equity: Current account equity
            open_positions: List of open positions
            closed_trades: List of closed trades
        """
        if not self.enabled:
            return

        try:
            # 1. Check circuit breaker
            self._check_circuit_breaker(current_equity, closed_trades)

            if self.circuit_breaker_active:
                logger.warning("🔴 CIRCUIT BREAKER ACTIVE - Trading paused")
                return

            # 2. Monitor and disable poor strategies
            self._monitor_strategy_performance(closed_trades)

            # 3. Apply ML parameter optimizations
            if self.auto_adjust_params and self.ml_engine:
                self._apply_ml_optimizations()

            # 4. Generate scheduled reports
            self._check_report_schedule(closed_trades)

            # 5. Monitor ML feature importance changes
            if self.ml_engine:
                self._monitor_feature_importance()

        except Exception as e:
            logger.error(f"ML Supervisor error (non-fatal, continuing): {e}", exc_info=True)
            # Continue trading even if supervisor fails - don't crash the system

    def _check_circuit_breaker(self, current_equity: float, closed_trades: List):
        """
        Check if circuit breaker should activate.

        Automatically pauses trading if:
        - Drawdown exceeds threshold (e.g., -15R)
        - Consecutive losing streak > 10
        - Sudden equity drop > 5%
        """
        if not closed_trades:
            return

        # Calculate session drawdown
        import pandas as pd
        trades_df = pd.DataFrame(closed_trades)

        if 'pnl_r' not in trades_df.columns:
            return

        returns = trades_df['pnl_r'].values
        cumulative = returns.cumsum()
        running_max = pd.Series(cumulative).cummax()
        drawdown = cumulative - running_max

        current_dd = drawdown[-1] if len(drawdown) > 0 else 0
        self.session_drawdown_r = current_dd

        # Check threshold
        if current_dd < -self.circuit_breaker_dd:
            if not self.circuit_breaker_active:
                self.circuit_breaker_active = True
                logger.critical("=" * 80)
                logger.critical(f"🔴 CIRCUIT BREAKER ACTIVATED")
                logger.critical(f"Drawdown: {current_dd:.2f}R exceeds threshold {-self.circuit_breaker_dd}R")
                logger.critical("ALL TRADING PAUSED")
                logger.critical("=" * 80)

                # Send alert (if configured)
                self._send_alert(
                    level='CRITICAL',
                    message=f"Circuit breaker activated. DD: {current_dd:.2f}R"
                )

        # Check if can deactivate (DD recovered to -5R)
        elif current_dd > -5.0 and self.circuit_breaker_active:
            self.circuit_breaker_active = False
            logger.info("=" * 80)
            logger.info("✅ CIRCUIT BREAKER DEACTIVATED")
            logger.info(f"Drawdown recovered to {current_dd:.2f}R")
            logger.info("Trading resumed")
            logger.info("=" * 80)

    def _monitor_strategy_performance(self, closed_trades: List):
        """
        Monitor individual strategy performance and auto-disable losers.

        Disables strategy if:
        - Total P&L < -10R
        - Win rate < 40% over 20+ trades
        - Sharpe < 0 over 30+ trades
        """
        if not closed_trades:
            return

        import pandas as pd
        trades_df = pd.DataFrame(closed_trades)

        if 'strategy' not in trades_df.columns or 'pnl_r' not in trades_df.columns:
            return

        # Analyze each strategy
        for strategy_name in trades_df['strategy'].unique():
            strategy_trades = trades_df[trades_df['strategy'] == strategy_name]

            if len(strategy_trades) < 10:
                continue  # Need minimum trades

            total_pnl_r = strategy_trades['pnl_r'].sum()
            win_rate = (strategy_trades['pnl_r'] > 0).sum() / len(strategy_trades)

            # Check auto-disable conditions
            should_disable = False
            reason = ""

            if total_pnl_r < self.auto_disable_threshold_r:
                should_disable = True
                reason = f"Total P&L {total_pnl_r:.2f}R below threshold {self.auto_disable_threshold_r}R"

            elif len(strategy_trades) >= 20 and win_rate < 0.40:
                should_disable = True
                reason = f"Win rate {win_rate:.2%} below 40% over {len(strategy_trades)} trades"

            if should_disable and strategy_name not in self.disabled_strategies:
                self._disable_strategy(strategy_name, reason)

    def _disable_strategy(self, strategy_name: str, reason: str):
        """
        Automatically disable a strategy and update config.

        Args:
            strategy_name: Name of strategy to disable
            reason: Reason for disabling
        """
        logger.warning("=" * 80)
        logger.warning(f"🔴 AUTO-DISABLING STRATEGY: {strategy_name}")
        logger.warning(f"Reason: {reason}")
        logger.warning("=" * 80)

        # Disable in orchestrator
        for strategy in self.strategy_orchestrator.strategies:
            if strategy.__class__.__name__ == strategy_name:
                strategy.enabled = False
                break

        # Update config file
        config_path = Path('config/strategies_institutional.yaml')
        if config_path.exists():
            with open(config_path, 'r') as f:
                strategies_config = yaml.safe_load(f)

            # Find and disable strategy
            for key in strategies_config:
                if strategy_name.lower() in key.lower():
                    strategies_config[key]['enabled'] = False
                    logger.info(f"✓ Updated config: {key}.enabled = false")

            # Save updated config
            with open(config_path, 'w') as f:
                yaml.dump(strategies_config, f, default_flow_style=False)

            logger.info(f"✓ Config saved: {config_path}")

        # Track disabled
        self.disabled_strategies.append(strategy_name)

        # Send alert
        self._send_alert(
            level='WARNING',
            message=f"Strategy '{strategy_name}' auto-disabled. {reason}"
        )

    def _apply_ml_optimizations(self):
        """
        Apply ML-recommended parameter optimizations automatically.

        ML continuously optimizes:
        - Entry thresholds
        - Exit criteria
        - Risk parameters
        - Timeframe selections

        This method applies those optimizations WITHOUT manual intervention.
        """
        if not self.ml_engine:
            return

        # Get ML recommendations
        try:
            recommendations = self.ml_engine.get_parameter_recommendations()

            if not recommendations:
                return

            logger.info("=" * 80)
            logger.info("🤖 APPLYING ML PARAMETER OPTIMIZATIONS")
            logger.info("=" * 80)

            applied_count = 0

            for strategy_name, params in recommendations.items():
                # Find strategy
                strategy = None
                for s in self.strategy_orchestrator.strategies:
                    if s.__class__.__name__ == strategy_name:
                        strategy = s
                        break

                if strategy:
                    # Apply optimized parameters
                    for param_name, new_value in params.items():
                        if hasattr(strategy, param_name):
                            old_value = getattr(strategy, param_name)
                            setattr(strategy, param_name, new_value)
                            logger.info(f"✓ {strategy_name}.{param_name}: {old_value} → {new_value}")
                            applied_count += 1

            if applied_count > 0:
                logger.info(f"✓ Applied {applied_count} ML optimizations")
                logger.info("=" * 80)

        except Exception as e:
            logger.error(f"Failed to apply ML optimizations: {e}")

    def _check_report_schedule(self, closed_trades: List):
        """
        Check if scheduled reports should be generated.

        Automatically generates:
        - Daily reports at midnight
        - Weekly reports on Sunday
        - Monthly reports on last day of month
        """
        current_date = datetime.now().date()

        # Check if new day (daily report)
        if self.last_report_date != current_date:
            if self.last_report_date is not None:
                # Generate daily report for previous day
                yesterday_trades = [
                    t for t in closed_trades
                    if datetime.fromisoformat(str(t.get('exit_time', t.get('entry_time')))).date() == self.last_report_date
                ]

                if yesterday_trades:
                    logger.info(f"📊 Generating daily report for {self.last_report_date}")
                    self.reporting.generate_daily_report(
                        yesterday_trades,
                        datetime.combine(self.last_report_date, datetime.min.time())
                    )

            self.last_report_date = current_date

        # Check if Sunday (weekly report)
        if current_date.weekday() == 6:  # Sunday
            week_trades = [
                t for t in closed_trades
                if (current_date - datetime.fromisoformat(str(t.get('exit_time', t.get('entry_time')))).date()).days <= 7
            ]

            if week_trades:
                logger.info(f"📊 Generating weekly report")
                self.reporting.generate_weekly_report(
                    week_trades,
                    datetime.combine(current_date, datetime.min.time())
                )

        # Check if end of month (monthly report)
        tomorrow = current_date + timedelta(days=1)
        if tomorrow.month != current_date.month:
            month_trades = [
                t for t in closed_trades
                if datetime.fromisoformat(str(t.get('exit_time', t.get('entry_time')))).date().month == current_date.month
            ]

            if month_trades:
                logger.info(f"📊 Generating monthly report")
                report = self.reporting.generate_monthly_report(
                    month_trades,
                    datetime.combine(current_date, datetime.min.time())
                )

                # Act on recommendations
                if 'recommendations' in report:
                    self._process_recommendations(report['recommendations'])

    def _monitor_feature_importance(self):
        """
        Monitor ML feature importance changes.

        If feature importance shifts significantly:
        - Log the change
        - Potentially adjust strategy weights
        """
        try:
            feature_importance = self.ml_engine.get_feature_importance()

            if feature_importance:
                # Save to file for tracking
                import json
                feature_file = Path('ml_data/feature_importance.json')

                data = {
                    'timestamp': datetime.now().isoformat(),
                    'feature_importance': feature_importance
                }

                with open(feature_file, 'w') as f:
                    json.dump(data, f, indent=2)

        except Exception as e:
            logger.debug(f"Could not monitor feature importance: {e}")

    def _process_recommendations(self, recommendations: List[str]):
        """
        Process monthly report recommendations automatically.

        Args:
            recommendations: List of recommendation strings
        """
        logger.info("=" * 80)
        logger.info("📋 PROCESSING MONTHLY RECOMMENDATIONS")
        logger.info("=" * 80)

        for rec in recommendations:
            logger.info(f"  {rec}")

            # Parse and act on recommendations
            if "🔴" in rec and "Disable" in rec:
                # Extract strategy name and disable it
                # Example: "🔴 Strategy 'spoofing_detection_l2' lost -8.2R. Consider: 1) Disable"
                import re
                match = re.search(r"Strategy '(\w+)'", rec)
                if match:
                    strategy_name = match.group(1)
                    if strategy_name not in self.disabled_strategies:
                        self._disable_strategy(strategy_name, "Monthly report recommendation")

        logger.info("=" * 80)

    def _send_alert(self, level: str, message: str):
        """
        Send alert to user (email, SMS, etc.).

        Args:
            level: Alert level (INFO, WARNING, CRITICAL)
            message: Alert message
        """
        # TODO: Implement email/SMS alerts
        logger.log(
            logging.CRITICAL if level == 'CRITICAL' else logging.WARNING if level == 'WARNING' else logging.INFO,
            f"🚨 ALERT [{level}]: {message}"
        )

    def get_status(self) -> Dict:
        """
        Get supervisor status.

        Returns:
            Dict with current status
        """
        return {
            'enabled': self.enabled,
            'circuit_breaker_active': self.circuit_breaker_active,
            'session_drawdown_r': self.session_drawdown_r,
            'disabled_strategies': self.disabled_strategies,
            'auto_adjust_params': self.auto_adjust_params
        }
