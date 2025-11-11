"""
Institutional Live Trading Engine - Complete Integration

Integrates all institutional components:
- Multi-Timeframe Data Manager
- Institutional Risk Manager (statistical circuit breakers)
- Market Structure Position Manager
- Regime Detector
- Brain Layer (signal arbitration and portfolio orchestration)

This is NOT a simple signal executor. This is an institutional algorithm
with portfolio-level thinking, regime adaptation, and advanced risk management.
"""

import os
import sys
from pathlib import Path
import yaml

# Determinar BASE_DIR dinámicamente
BASE_DIR = Path(__file__).parent.parent.resolve()
sys.path.insert(0, str(BASE_DIR))
sys.path.insert(0, str(BASE_DIR / 'src'))

# Logging robusto
import logging
from logging.handlers import RotatingFileHandler

log_dir = BASE_DIR / 'logs'
log_dir.mkdir(exist_ok=True)
log_file = log_dir / 'institutional_trading.log'

try:
    file_handler = RotatingFileHandler(
        str(log_file),
        maxBytes=10*1024*1024,  # 10MB
        backupCount=5,
        encoding='utf-8'
    )
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
    handlers = [file_handler, logging.StreamHandler()]
except Exception as e:
    print(f"WARNING: Could not create log file, using console only: {e}")
    handlers = [logging.StreamHandler()]

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=handlers
)
logger = logging.getLogger(__name__)

# Critical imports
import pandas as pd
import numpy as np
import MetaTrader5 as mt5
import importlib
import inspect
from datetime import datetime
import time
import warnings
warnings.filterwarnings("ignore", category=RuntimeWarning)

# Institutional core components
from core import (
    MultiTimeframeDataManager,
    InstitutionalRiskManager,
    MarketStructurePositionManager,
    RegimeDetector,
    InstitutionalBrain,
)

# Strategy whitelist - 14 institutional strategies
STRATEGY_WHITELIST = [
    'mean_reversion_statistical',
    'liquidity_sweep',
    'momentum_quality',
    'order_block_institutional',
    'kalman_pairs_trading',
    'correlation_divergence',
    'volatility_regime_adaptation',
    'breakout_volume_confirmation',
    'fvg_institutional',
    'htf_ltf_liquidity',
    'iceberg_detection',
    'idp_inducement_distribution',
    'ofi_refinement',
    'order_flow_toxicity',  # Filter only
]

SYMBOLS = [
    'EURUSD.pro', 'GBPUSD.pro', 'USDJPY.pro', 'AUDUSD.pro',
    'USDCAD.pro', 'USDCHF.pro', 'NZDUSD.pro', 'EURGBP.pro',
    'XAUUSD.pro', 'BTCUSD', 'ETHUSD'
]

SCAN_INTERVAL_SECONDS = 60


def load_configs():
    """Load all configuration files."""
    configs = {}

    # Strategy configuration
    strategy_config_path = BASE_DIR / 'config' / 'strategies_institutional.yaml'
    if strategy_config_path.exists():
        with open(strategy_config_path, 'r', encoding='utf-8') as f:
            configs['strategies'] = yaml.safe_load(f)
            logger.info(f"Loaded strategy config: {len(configs['strategies'])} strategies")
    else:
        configs['strategies'] = {}
        logger.warning("Strategy config not found, using defaults")

    # Risk management configuration
    configs['risk'] = {
        'base_risk_per_trade': 0.5,
        'min_risk_per_trade': 0.33,
        'max_risk_per_trade': 1.0,
        'min_quality_score': 0.60,
        'max_total_exposure': 6.0,
        'max_correlated_exposure': 5.0,
        'max_per_symbol_exposure': 2.0,
        'max_per_strategy_exposure': 3.0,
        'max_daily_loss': 3.0,
        'max_drawdown': 15.0,
        'circuit_breaker_z_score': 2.5,
        'circuit_breaker_lookback': 30,
        'circuit_cooldown_minutes': 120,
    }

    # Position management configuration
    configs['position'] = {
        'min_r_for_breakeven': 1.5,
        'min_r_for_trailing': 2.0,
        'min_r_for_partial': 2.5,
        'partial_exit_pct': 0.50,
        'structure_proximity_atr': 0.5,
        'update_interval_bars': 1,
    }

    # Regime detection configuration
    configs['regime'] = {
        'regime_lookback': 30,
        'min_regime_confidence': 0.60,
        'trend_adx_threshold': 25,
        'strong_trend_adx': 35,
        'ranging_adx_max': 20,
        'low_vol_percentile': 30,
        'high_vol_percentile': 70,
    }

    # Brain configuration
    configs['brain'] = {
        'min_arbitration_score': 0.65,
        'max_positions_per_symbol': 2,
        'max_total_positions': 8,
        'max_correlated_positions': 4,
    }

    return configs


class InstitutionalTradingEngine:
    """
    Institutional trading engine with complete architecture.

    Components:
    - Multi-Timeframe Data Manager: D1/H4/H1/M30/M15/M5/M1 data
    - Risk Manager: Statistical circuit breakers, dynamic sizing
    - Position Manager: Market structure-based stops
    - Regime Detector: Market regime classification
    - Brain: Signal arbitration and portfolio orchestration
    """

    def __init__(self):
        """Initialize institutional trading engine."""
        logger.info("=" * 100)
        logger.info("INSTITUTIONAL TRADING ENGINE - INITIALIZATION")
        logger.info("=" * 100)

        # Load configurations
        self.configs = load_configs()

        # Strategy instances
        self.strategies = []
        self.stats = {}

        # Core institutional components (initialized after MT5 connection)
        self.mtf_manager = None
        self.risk_manager = None
        self.position_manager = None
        self.regime_detector = None
        self.brain = None

        # Execution tracking
        self.scan_count = 0
        self.running = False

        # Position tracking for MT5 integration
        self.active_mt5_positions = {}

        logger.info("Engine initialized (components pending MT5 connection)")

    def initialize_mt5(self) -> bool:
        """Initialize MetaTrader 5 connection."""
        if not mt5.initialize():
            logger.error("ERROR: Could not initialize MT5")
            return False

        account = mt5.account_info()
        if account is None:
            logger.error("ERROR: No account connected")
            mt5.shutdown()
            return False

        logger.info(f"✓ Connected to {account.server}")
        logger.info(f"✓ Account: {account.login}")
        logger.info(f"✓ Balance: ${account.balance:,.2f}")
        logger.info(f"✓ Equity: ${account.equity:,.2f}")

        # Initialize institutional components NOW that we have account info
        self._initialize_institutional_components(account.balance)

        return True

    def _initialize_institutional_components(self, initial_balance: float):
        """Initialize all institutional core components."""
        logger.info("\nInitializing institutional components...")

        # 1. Multi-Timeframe Data Manager
        self.mtf_manager = MultiTimeframeDataManager(SYMBOLS)
        logger.info("✓ MTF Data Manager initialized")

        # 2. Risk Manager
        risk_config = self.configs['risk'].copy()
        risk_config['initial_balance'] = initial_balance
        self.risk_manager = InstitutionalRiskManager(risk_config)
        logger.info("✓ Risk Manager initialized (statistical circuit breakers)")

        # 3. Position Manager
        self.position_manager = MarketStructurePositionManager(
            self.configs['position'],
            self.mtf_manager
        )
        logger.info("✓ Position Manager initialized (market structure-based)")

        # 4. Regime Detector
        self.regime_detector = RegimeDetector(self.configs['regime'])
        logger.info("✓ Regime Detector initialized")

        # 5. Brain Layer
        self.brain = InstitutionalBrain(
            self.configs['brain'],
            self.risk_manager,
            self.position_manager,
            self.regime_detector,
            self.mtf_manager
        )
        logger.info("✓ Brain Layer initialized (advanced orchestration)")

        logger.info("\n✓ ALL INSTITUTIONAL COMPONENTS READY\n")

    def load_strategies(self):
        """Load institutional strategies."""
        logger.info("Loading institutional strategies...")

        strategy_configs = self.configs['strategies']
        loaded_count = 0
        error_count = 0

        for module_name in STRATEGY_WHITELIST:
            try:
                module = importlib.import_module(f'strategies.{module_name}')
                classes = [(n, o) for n, o in inspect.getmembers(module, inspect.isclass)
                          if o.__module__ == f'strategies.{module_name}']

                if classes:
                    class_name, strategy_class = classes[0]

                    if not hasattr(strategy_class, 'evaluate'):
                        logger.error(f"  ERROR {module_name}: No evaluate method")
                        error_count += 1
                        continue

                    # Get strategy-specific config
                    strategy_config = strategy_configs.get(module_name, {})
                    strategy_config['enabled'] = strategy_config.get('enabled', True)
                    strategy_config['symbols'] = SYMBOLS

                    instance = strategy_class(strategy_config)

                    self.strategies.append({
                        'name': module_name,
                        'instance': instance,
                        'class': class_name
                    })

                    self.stats[module_name] = {
                        'signals_generated': 0,
                        'signals_approved': 0,
                        'signals_rejected': 0,
                        'trades_executed': 0,
                        'errors': 0
                    }

                    logger.info(f"  ✓ {module_name}")
                    loaded_count += 1

                else:
                    logger.error(f"  ERROR {module_name}: Class not found")
                    error_count += 1

            except Exception as e:
                logger.error(f"  ERROR {module_name}: {str(e)[:80]}")
                error_count += 1

        logger.info(f"\n✓ Strategies loaded: {loaded_count}/{len(STRATEGY_WHITELIST)}")
        if error_count > 0:
            logger.warning(f"⚠ Load errors: {error_count}")

    def update_mtf_data(self):
        """Update multi-timeframe data for all symbols."""
        for symbol in SYMBOLS:
            try:
                self.mtf_manager.update_all_timeframes(symbol)
            except Exception as e:
                logger.error(f"Error updating MTF data for {symbol}: {e}")

    def calculate_features(self, symbol: str) -> Dict:
        """
        Calculate features for symbol using MTF data.

        Args:
            symbol: Symbol to calculate features for

        Returns:
            Features dictionary
        """
        features = {}

        try:
            # Get M1 data for microstructure features
            m1_data = self.mtf_manager.get_data(symbol, 'M1')

            if m1_data.empty or len(m1_data) < 50:
                # Return minimal features
                return {
                    'atr': 0.0001,
                    'rsi': 50.0,
                    'vpin': 0.5,
                    'adx': 0.0,
                    'order_flow_imbalance': 0.0,
                }

            # ATR
            if 'atr' in m1_data.columns:
                features['atr'] = float(m1_data['atr'].iloc[-1])
            else:
                features['atr'] = 0.0001

            # RSI
            close = m1_data['close']
            delta = close.diff()
            gain = delta.where(delta > 0, 0).rolling(14).mean()
            loss = -delta.where(delta < 0, 0).rolling(14).mean()
            rs = gain / loss
            rsi = 100 - (100 / (1 + rs))
            features['rsi'] = float(rsi.iloc[-1]) if not rsi.empty else 50.0

            # VPIN (order flow toxicity)
            buy_volume = m1_data.loc[m1_data['close'] > m1_data['close'].shift(1), 'volume'].sum()
            sell_volume = m1_data.loc[m1_data['close'] <= m1_data['close'].shift(1), 'volume'].sum()
            total_volume = buy_volume + sell_volume

            if total_volume > 0:
                imbalance = abs(buy_volume - sell_volume) / total_volume
                features['vpin'] = float(imbalance)
            else:
                features['vpin'] = 0.5

            # Order flow imbalance (signed)
            features['order_flow_imbalance'] = float((buy_volume - sell_volume) / total_volume) if total_volume > 0 else 0.0

            # ADX (simplified)
            high = m1_data['high']
            low = m1_data['low']
            close = m1_data['close']

            plus_dm = high.diff()
            minus_dm = -low.diff()
            plus_dm[plus_dm < 0] = 0
            minus_dm[minus_dm < 0] = 0

            atr = m1_data['atr'] if 'atr' in m1_data.columns else (high - low).rolling(14).mean()
            plus_di = 100 * (plus_dm.rolling(14).mean() / atr)
            minus_di = 100 * (minus_dm.rolling(14).mean() / atr)

            dx = 100 * abs(plus_di - minus_di) / (plus_di + minus_di)
            adx = dx.rolling(14).mean()

            features['adx'] = float(adx.iloc[-1]) if not adx.empty else 0.0

            # MTF confluence
            mtf_trends = self.mtf_manager.calculate_mtf_trend(symbol)
            features['mtf_trends'] = mtf_trends

            # Structure data
            structure = self.mtf_manager.get_structure(symbol, 'M15')
            features['structure'] = structure

        except Exception as e:
            logger.error(f"Error calculating features for {symbol}: {e}")
            features = {
                'atr': 0.0001,
                'rsi': 50.0,
                'vpin': 0.5,
                'adx': 0.0,
                'order_flow_imbalance': 0.0,
            }

        return features

    def collect_signals(self) -> List[Dict]:
        """
        Collect signals from all strategies.

        Returns:
            List of raw signals
        """
        all_signals = []

        for symbol in SYMBOLS:
            # Get data and features
            market_data = self.mtf_manager.get_data(symbol, 'M1')

            if market_data.empty or len(market_data) < 100:
                continue

            features = self.calculate_features(symbol)

            if not features:
                continue

            # Evaluate each strategy
            for strategy_info in self.strategies:
                strategy_name = strategy_info['name']

                try:
                    signals = strategy_info['instance'].evaluate(market_data, features)

                    if signals:
                        signal_list = signals if isinstance(signals, list) else [signals]

                        for signal in signal_list:
                            if signal is not None and hasattr(signal, 'validate') and signal.validate():
                                # Convert to dict format for Brain
                                signal_dict = {
                                    'timestamp': datetime.now(),
                                    'symbol': signal.symbol,
                                    'strategy_name': strategy_name,
                                    'direction': signal.direction,
                                    'entry_price': signal.entry_price,
                                    'stop_loss': signal.stop_loss,
                                    'take_profit': signal.take_profit,
                                    'metadata': getattr(signal, 'metadata', {}),
                                }

                                all_signals.append(signal_dict)
                                self.stats[strategy_name]['signals_generated'] += 1

                except Exception as e:
                    self.stats[strategy_name]['errors'] += 1
                    logger.error(f"Error evaluating {strategy_name}: {e}")

        return all_signals

    def execute_order(self, execution_order: Dict) -> bool:
        """
        Execute approved order from Brain.

        Args:
            execution_order: Execution order from Brain

        Returns:
            Success boolean
        """
        try:
            symbol = execution_order['symbol']
            direction_str = execution_order['direction']
            lot_size = execution_order['lot_size']

            direction = mt5.ORDER_TYPE_BUY if direction_str == 'LONG' else mt5.ORDER_TYPE_SELL

            symbol_info = mt5.symbol_info(symbol)
            if symbol_info is None:
                logger.error(f"ERROR: Symbol {symbol} not available")
                return False

            tick = mt5.symbol_info_tick(symbol)
            if tick is None:
                logger.error(f"ERROR: No tick for {symbol}")
                return False

            price = tick.ask if direction == mt5.ORDER_TYPE_BUY else tick.bid

            # Validate lot size
            lot_size = max(symbol_info.volume_min, lot_size)
            lot_size = min(symbol_info.volume_max, lot_size)
            lot_size = round(lot_size, 2)

            request = {
                "action": mt5.TRADE_ACTION_DEAL,
                "symbol": symbol,
                "volume": lot_size,
                "type": direction,
                "price": price,
                "sl": execution_order['stop_loss'],
                "tp": execution_order['take_profit'],
                "deviation": 20,
                "magic": 234000,
                "comment": f"{execution_order['strategy'][:15]}",
                "type_time": mt5.ORDER_TIME_GTC,
                "type_filling": mt5.ORDER_FILLING_FOK,
            }

            result = mt5.order_send(request)

            if result is None:
                error = mt5.last_error()
                logger.error(f"ERROR: order_send returned None - {error}")
                return False

            if result.retcode != mt5.TRADE_RETCODE_DONE:
                logger.error(f"ERROR: Order rejected - {result.comment}")
                return False

            # Register position in components
            position_id = f"{symbol}_{result.order}_{int(datetime.now().timestamp())}"

            self.risk_manager.register_position(
                position_id,
                execution_order['signal'],
                lot_size,
                execution_order['risk_pct']
            )

            self.position_manager.add_position(
                position_id,
                execution_order['signal'],
                lot_size
            )

            self.brain.orchestrator.register_position(
                position_id,
                execution_order['signal'],
                lot_size
            )

            self.active_mt5_positions[position_id] = {
                'ticket': result.order,
                'symbol': symbol,
                'direction': direction_str,
                'lot_size': lot_size,
            }

            logger.info(f"✓ ORDER EXECUTED: {direction_str} {symbol} {lot_size:.2f} lots @ {price:.5f}")
            logger.info(f"  SL: {execution_order['stop_loss']:.5f} | TP: {execution_order['take_profit']:.5f}")
            logger.info(f"  Quality: {execution_order['quality_score']:.3f} | Risk: {execution_order['risk_pct']:.2f}%")
            logger.info(f"  Regime: {execution_order['regime']}")

            return True

        except Exception as e:
            logger.error(f"ERROR executing order: {e}")
            return False

    def update_positions(self):
        """Update all active positions through position manager."""
        # Collect current market data
        market_data = {}

        for symbol in SYMBOLS:
            data = self.mtf_manager.get_data(symbol, 'M1')
            if not data.empty:
                market_data[symbol] = data

        # Update positions
        self.brain.update_positions(market_data)

    def scan_markets(self):
        """Execute one market scan cycle - institutional orchestration."""
        self.scan_count += 1

        logger.info("=" * 100)
        logger.info(f"INSTITUTIONAL SCAN #{self.scan_count} - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        logger.info("=" * 100)

        # 1. Update multi-timeframe data
        logger.info("Updating MTF data...")
        self.update_mtf_data()

        # 2. Update positions (trailing stops, partials, etc.)
        logger.info("Updating positions...")
        self.update_positions()

        # 3. Collect signals from all strategies
        logger.info("Collecting signals from strategies...")
        raw_signals = self.collect_signals()

        logger.info(f"✓ Collected {len(raw_signals)} raw signals")

        if not raw_signals:
            logger.info("No signals generated this scan")
            return

        # 4. Prepare market data for Brain
        market_data = {}
        features = {}

        for symbol in SYMBOLS:
            data = self.mtf_manager.get_data(symbol, 'M1')
            if not data.empty:
                market_data[symbol] = data
                features[symbol] = self.calculate_features(symbol)

        # 5. Process signals through Brain (institutional orchestration)
        logger.info("Processing signals through Brain Layer...")
        approved_orders = self.brain.process_signals(raw_signals, market_data, features)

        logger.info(f"✓ Brain approved {len(approved_orders)} signals")

        # Update stats
        for strategy_name in self.stats:
            strategy_signals = [s for s in raw_signals if s['strategy_name'] == strategy_name]
            strategy_approved = [o for o in approved_orders if o['strategy'] == strategy_name]

            self.stats[strategy_name]['signals_approved'] += len(strategy_approved)
            self.stats[strategy_name]['signals_rejected'] += (len(strategy_signals) - len(strategy_approved))

        # 6. Execute approved orders
        for order in approved_orders:
            if self.execute_order(order):
                self.stats[order['strategy']]['trades_executed'] += 1

        # 7. Print statistics every 10 scans
        if self.scan_count % 10 == 0:
            self.print_statistics()

    def print_statistics(self):
        """Print comprehensive statistics."""
        logger.info("\n" + "=" * 100)
        logger.info(f"INSTITUTIONAL STATISTICS - Scan #{self.scan_count}")
        logger.info("=" * 100)

        # Strategy statistics
        logger.info("\nSTRATEGY PERFORMANCE:")
        for strategy_name, stats in sorted(self.stats.items()):
            generated = stats['signals_generated']
            approved = stats['signals_approved']
            rejected = stats['signals_rejected']
            executed = stats['trades_executed']
            approval_rate = (approved / generated * 100) if generated > 0 else 0

            logger.info(f"\n{strategy_name}:")
            logger.info(f"  Signals Generated: {generated}")
            logger.info(f"  Signals Approved:  {approved} ({approval_rate:.1f}%)")
            logger.info(f"  Signals Rejected:  {rejected}")
            logger.info(f"  Trades Executed:   {executed}")

        # Brain statistics
        logger.info("\nBRAIN STATISTICS:")
        brain_stats = self.brain.get_statistics()
        logger.info(f"  Total Signals Received: {brain_stats['total_signals_received']}")
        logger.info(f"  Total Approved: {brain_stats['total_signals_approved']}")
        logger.info(f"  Total Rejected: {brain_stats['total_signals_rejected']}")
        logger.info(f"  Approval Rate: {brain_stats['approval_rate_pct']:.1f}%")

        # Risk Manager statistics
        logger.info("\nRISK MANAGER:")
        risk_stats = brain_stats['risk_manager']
        logger.info(f"  Current Equity: ${risk_stats['current_equity']:,.2f}")
        logger.info(f"  Drawdown: {risk_stats['current_drawdown_pct']:.2f}%")
        logger.info(f"  Daily P&L: {risk_stats['daily_pnl_pct']:.2f}%")
        logger.info(f"  Active Positions: {risk_stats['active_positions']}")
        logger.info(f"  Total Exposure: {risk_stats['total_exposure_pct']:.2f}%")

        # Circuit Breaker
        cb_stats = risk_stats['circuit_breaker']
        logger.info(f"\nCIRCUIT BREAKER: {cb_stats['status']}")
        if cb_stats['status'] == 'OPEN':
            logger.warning(f"  ⚠ Remaining Cooldown: {cb_stats['remaining_cooldown_min']:.1f} min")

        # Position Manager
        logger.info("\nPOSITION MANAGER:")
        pos_stats = brain_stats['position_manager']
        logger.info(f"  Active Positions: {pos_stats['active_positions']}")
        logger.info(f"  Risk-Free Positions: {pos_stats['risk_free_positions']}")

        # Regime
        logger.info("\nREGIME:")
        regime_stats = brain_stats['regime']
        logger.info(f"  Current: {regime_stats['current_regime']}")
        logger.info(f"  Confidence: {regime_stats['confidence']:.2f}")
        logger.info(f"  Duration: {regime_stats['duration_bars']} bars")

        logger.info("\n" + "=" * 100)

    def run(self):
        """Run institutional trading engine."""
        logger.info("\n" + "=" * 100)
        logger.info("INSTITUTIONAL TRADING ENGINE - LIVE")
        logger.info("=" * 100)
        logger.info(f"Strategies: {len(self.strategies)}")
        logger.info(f"Symbols: {len(SYMBOLS)}")
        logger.info(f"Scan Interval: {SCAN_INTERVAL_SECONDS}s")
        logger.info(f"Mode: INSTITUTIONAL (Brain Layer Active)")
        logger.info("=" * 100)

        self.running = True

        try:
            while self.running:
                self.scan_markets()
                time.sleep(SCAN_INTERVAL_SECONDS)

        except KeyboardInterrupt:
            logger.info("\n\nStopping engine...")
            self.print_statistics()

        finally:
            mt5.shutdown()
            logger.info("\n✓ Engine stopped")


def main():
    """Main entry point."""
    engine = InstitutionalTradingEngine()

    if not engine.initialize_mt5():
        return False

    engine.load_strategies()
    engine.run()

    return True


if __name__ == "__main__":
    main()
