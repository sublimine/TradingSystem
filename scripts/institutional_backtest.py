"""
Institutional-Grade Backtesting Engine
Complete pipeline: Feature Generation → Strategy Evaluation → Performance Analysis
"""

import sys
sys.path.insert(0, 'C:/TradingSystem')
sys.path.insert(0, 'C:/TradingSystem/src')

import psycopg2
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import importlib
import logging
from typing import Dict, List, Tuple

# Import feature calculation modules
from features.technical_indicators import (
    calculate_atr, calculate_rsi, calculate_adx,
    identify_swing_points, calculate_ema, calculate_sma
)
from features.microstructure import (
    calculate_spread, calculate_order_book_imbalance,
    calculate_microprice
)
from features.order_flow import (
    VPINCalculator, calculate_signed_volume,
    calculate_cumulative_volume_delta
)
from features.ofi import calculate_ofi  # INSTITUTIONAL: Order Flow Imbalance
from features.statistical_models import (
    calculate_realized_volatility, VolatilityHMM
)
from features.derived_features import (
    calculate_momentum_quality, calculate_volume_price_correlation,
    detect_price_volume_divergence
)

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

DB_CONFIG = {
    'host': 'localhost',
    'port': 5432,
    'database': 'trading_system',
    'user': 'trading_user',
    'password': 'abc'
}

INITIAL_CAPITAL = 10000.0
SLIPPAGE_PIPS = 1.0


class FeatureGenerator:
    """
    Generates comprehensive feature set for strategy evaluation.
    
    Coordinates calculation of technical indicators, microstructure metrics,
    order flow analysis, statistical models, and derived features.
    """
    
    def __init__(self):
        self.vpin_calculator = VPINCalculator(bucket_size=50000, num_buckets=50)
        self.volatility_hmm = VolatilityHMM(random_seed=42)
        self.hmm_fitted = False
        
    def generate_features(self, market_data: pd.DataFrame) -> Dict:
        """
        Generate complete feature set from market data.
        
        Args:
            market_data: DataFrame with OHLCV data
            
        Returns:
            Dictionary containing all calculated features
        """
        if len(market_data) < 100:
            return {}
        
        features = {}
        
        # Technical Indicators
        features['atr'] = calculate_atr(
            market_data['high'], 
            market_data['low'], 
            market_data['close'], 
            period=14
        ).iloc[-1] if len(market_data) >= 14 else 0
        
        features['rsi'] = calculate_rsi(
            market_data['close'], 
            period=14
        ).iloc[-1] if len(market_data) >= 15 else 50
        
        features['adx'] = calculate_adx(
            market_data['high'],
            market_data['low'],
            market_data['close'],
            period=14
        ).iloc[-1] if len(market_data) >= 28 else 20
        
        # Swing Points
        swing_highs, swing_lows = identify_swing_points(market_data['high'], order=5)
        recent_swing_highs = market_data.loc[swing_highs.tail(50), 'high'].values
        recent_swing_lows = market_data.loc[swing_lows.tail(50), 'low'].values
        
        features['swing_high_levels'] = recent_swing_highs.tolist()
        features['swing_low_levels'] = recent_swing_lows.tolist()
        
        # Moving Averages
        features['ema_20'] = calculate_ema(market_data['close'], 20).iloc[-1] if len(market_data) >= 20 else market_data['close'].iloc[-1]
        features['sma_50'] = calculate_sma(market_data['close'], 50).iloc[-1] if len(market_data) >= 50 else market_data['close'].iloc[-1]
        
        # Order Flow Metrics - INSTITUTIONAL
        signed_volumes = calculate_signed_volume(market_data['close'], market_data['volume'])
        cvd = calculate_cumulative_volume_delta(signed_volumes, window=20)
        features['cvd'] = cvd.iloc[-1] if len(cvd) > 0 else 0  # CVD for strategies
        features['cumulative_volume_delta'] = features['cvd']  # Alias for backward compatibility

        # OFI (Order Flow Imbalance) - INSTITUTIONAL
        ofi_series = calculate_ofi(market_data, window_size=20)
        features['ofi'] = ofi_series.iloc[-1] if len(ofi_series) > 0 else 0.0
        
        # VPIN Calculation (simplified for daily data)
        for _, row in market_data.tail(100).iterrows():
            trade_direction = 1 if row['close'] > row['open'] else -1
            vpin_value = self.vpin_calculator.add_trade(row['volume'], trade_direction)
            
        features['vpin'] = self.vpin_calculator.get_current_vpin()
        
        # Volatility Regime Detection
        returns = market_data['close'].pct_change().dropna()
        realized_vol = calculate_realized_volatility(returns.tail(60), window=20)
        
        if len(realized_vol) >= 20 and not self.hmm_fitted:
            try:
                clean_vol = realized_vol[~np.isnan(realized_vol)]
                if len(clean_vol) >= 20:
                    self.volatility_hmm.fit(clean_vol)
                    self.hmm_fitted = True
            except:
                pass
        
        if self.hmm_fitted and len(realized_vol) > 0:
            recent_vol = realized_vol[~np.isnan(realized_vol)].tail(10)
            if len(recent_vol) > 0:
                state_probs = self.volatility_hmm.predict_state(recent_vol)
                features['volatility_regime'] = 1 if state_probs[1] > 0.5 else 0
        else:
            features['volatility_regime'] = 0
        
        # Derived Features
        price_momentum = returns.iloc[-20:].mean() if len(returns) >= 20 else 0
        volume_momentum = market_data['volume'].pct_change().iloc[-20:].mean() if len(market_data) >= 21 else 0
        
        features['momentum_quality'] = calculate_momentum_quality(
            price_momentum,
            volume_momentum,
            features['vpin'],
            vpin_threshold=0.65
        )
        
        volume_price_corr = calculate_volume_price_correlation(
            market_data['close'],
            market_data['volume'],
            window=20
        )
        features['volume_price_correlation'] = volume_price_corr.iloc[-1] if len(volume_price_corr) > 0 else 0
        
        price_volume_div = detect_price_volume_divergence(
            market_data['close'],
            market_data['volume'],
            lookback=20
        )
        features['price_volume_divergence'] = price_volume_div.iloc[-1] if len(price_volume_div) > 0 else 0
        
        # Order Book Imbalance (simulated from volume analysis)
        buy_volume = market_data.loc[market_data['close'] > market_data['open'], 'volume'].sum()
        sell_volume = market_data.loc[market_data['close'] <= market_data['open'], 'volume'].sum()
        features['order_book_imbalance'] = calculate_order_book_imbalance(buy_volume, sell_volume)
        
        # Spread metrics (estimated from OHLC)
        typical_spread = (market_data['high'] - market_data['low']).mean()
        features['spread'] = typical_spread
        features['normalized_spread'] = typical_spread / features['atr'] if features['atr'] > 0 else 0
        
        return features


class InstitutionalBacktestEngine:
    """
    Production-grade backtesting engine with complete feature pipeline.
    """
    
    def __init__(self, strategy_configs: Dict, initial_capital: float):
        self.strategy_configs = strategy_configs
        self.initial_capital = initial_capital
        self.current_capital = initial_capital
        self.equity_peak = initial_capital
        
        self.feature_generator = FeatureGenerator()
        self.strategies = {}
        self.trades = []
        self.daily_equity = []
        self.strategy_stats = {}
        
    def load_strategies(self):
        """Load and instantiate all configured strategies."""
        logger.info("Loading strategy modules...")
        
        for strategy_name, config in self.strategy_configs.items():
            try:
                module = importlib.import_module(config['module'])
                strategy_class = getattr(module, config['class'])
                
                strategy_instance = strategy_class(config['params'])
                self.strategies[strategy_name] = strategy_instance
                
                self.strategy_stats[strategy_name] = {
                    'signals_generated': 0,
                    'trades_executed': 0,
                    'trades_won': 0,
                    'total_pnl': 0.0
                }
                
                logger.info(f"✓ Loaded: {strategy_name}")
                
            except Exception as e:
                logger.error(f"✗ Failed to load {strategy_name}: {e}")
        
        logger.info(f"Successfully loaded {len(self.strategies)} strategies\n")
    
    def run_backtest(self):
        """Execute comprehensive backtest with full feature pipeline."""
        logger.info("=" * 80)
        logger.info("INSTITUTIONAL-GRADE BACKTESTING ENGINE")
        logger.info("=" * 80)
        logger.info(f"Initial Capital: ${self.initial_capital:,.2f}")
        logger.info(f"Strategies: {len(self.strategies)}")
        logger.info("Feature Pipeline: Active")
        logger.info("=" * 80)
        
        conn = psycopg2.connect(**DB_CONFIG)
        
        # Load all available historical data
        all_data = pd.read_sql_query("""
            SELECT symbol, time, open, high, low, close, tick_volume as volume
            FROM market_data
            WHERE symbol IN ('EURUSD.pro', 'GBPUSD.pro', 'USDJPY.pro', 'AUDUSD.pro',
                           'USDCAD.pro', 'USDCHF.pro', 'NZDUSD.pro', 'EURGBP.pro',
                           'XAUUSD.pro', 'BTCUSD', 'ETHUSD')
            ORDER BY time
        """, conn)
        
        conn.close()
        
        if all_data.empty:
            logger.error("No historical data available")
            return False
        
        dates = sorted(all_data['time'].unique())
        symbols = all_data['symbol'].unique()
        
        logger.info(f"\nData Coverage:")
        logger.info(f"  Period: {dates[0].date()} to {dates[-1].date()}")
        logger.info(f"  Trading Days: {len(dates)}")
        logger.info(f"  Symbols: {len(symbols)}")
        logger.info(f"  Total Bars: {len(all_data):,}\n")
        
        logger.info("Backtesting Process:")
        logger.info("  1. Feature Generation (Technical + Microstructure + Order Flow)")
        logger.info("  2. Strategy Evaluation via evaluate() methods")
        logger.info("  3. Signal Processing and Trade Execution")
        logger.info("  4. Performance Tracking and Risk Management\n")
        
        # Minimum lookback for feature generation
        min_lookback = 100
        
        for i, date in enumerate(dates):
            if i < min_lookback:
                continue
            
            historical_data = all_data[all_data['time'] <= date]
            current_day_data = all_data[all_data['time'] == date]
            
            # Update open trades
            self._update_open_trades(date, current_day_data)
            
            # Calculate current equity
            current_equity = self._calculate_current_equity(current_day_data)
            
            if current_equity > self.equity_peak:
                self.equity_peak = current_equity
            
            self.daily_equity.append({
                'date': date,
                'equity': current_equity,
                'peak': self.equity_peak
            })
            
            # Process each symbol
            for symbol in symbols:
                symbol_history = historical_data[historical_data['symbol'] == symbol].copy()
                
                if len(symbol_history) < min_lookback:
                    continue
                
                # Generate features for this symbol
                try:
                    features = self.feature_generator.generate_features(symbol_history)
                    
                    if not features:
                        continue
                    
                    # Evaluate each strategy
                    for strategy_name, strategy in self.strategies.items():
                        try:
                            signals = strategy.evaluate(symbol_history, features)
                            
                            if signals:
                                for signal in signals:
                                    self.strategy_stats[strategy_name]['signals_generated'] += 1
                                    self._execute_trade(signal, strategy_name, date)
                                    
                        except Exception as e:
                            pass
                            
                except Exception as e:
                    pass
            
            # Progress reporting
            if (i + 1) % 50 == 0:
                progress = (i + 1) / len(dates) * 100
                open_trades = len([t for t in self.trades if t['status'] == 'open'])
                logger.info(f"Progress: {progress:.1f}% | Equity: ${current_equity:,.2f} | Open: {open_trades}")
        
        logger.info("\nBacktest execution completed")
        return True
    
    def _execute_trade(self, signal, strategy_name: str, entry_date: datetime):
        """Execute trade from strategy signal."""
        volume = 1.0
        
        pip_multiplier = 10000 if 'JPY' not in signal.symbol else 100
        slippage_price = SLIPPAGE_PIPS / pip_multiplier
        
        entry_price = signal.entry_price
        if signal.direction == 'LONG':
            entry_price += slippage_price
        else:
            entry_price -= slippage_price
        
        trade = {
            'entry_date': entry_date,
            'symbol': signal.symbol,
            'strategy': strategy_name,
            'direction': signal.direction,
            'entry_price': entry_price,
            'stop_loss': signal.stop_loss,
            'take_profit': signal.take_profit,
            'volume': volume,
            'status': 'open',
            'metadata': signal.metadata if hasattr(signal, 'metadata') else {}
        }
        
        self.trades.append(trade)
        self.strategy_stats[strategy_name]['trades_executed'] += 1
    
    def _update_open_trades(self, date: datetime, market_data: pd.DataFrame):
        """Update open trades and close if stops/targets hit."""
        for trade in self.trades:
            if trade['status'] != 'open':
                continue
            
            symbol_data = market_data[market_data['symbol'] == trade['symbol']]
            if len(symbol_data) == 0:
                continue
            
            current_bar = symbol_data.iloc[-1]
            current_high = float(current_bar['high'])
            current_low = float(current_bar['low'])
            
            trade_closed = False
            exit_price = None
            
            if trade['direction'] == 'LONG':
                if current_low <= trade['stop_loss']:
                    exit_price = trade['stop_loss']
                    trade_closed = True
                elif current_high >= trade['take_profit']:
                    exit_price = trade['take_profit']
                    trade_closed = True
            else:
                if current_high >= trade['stop_loss']:
                    exit_price = trade['stop_loss']
                    trade_closed = True
                elif current_low <= trade['take_profit']:
                    exit_price = trade['take_profit']
                    trade_closed = True
            
            if trade_closed:
                if trade['direction'] == 'LONG':
                    profit = (exit_price - trade['entry_price']) * trade['volume']
                else:
                    profit = (trade['entry_price'] - exit_price) * trade['volume']
                
                trade['exit_date'] = date
                trade['exit_price'] = exit_price
                trade['profit'] = profit
                trade['status'] = 'closed'
                
                self.current_capital += profit
                
                self.strategy_stats[trade['strategy']]['total_pnl'] += profit
                if profit > 0:
                    self.strategy_stats[trade['strategy']]['trades_won'] += 1
    
    def _calculate_current_equity(self, market_data: pd.DataFrame) -> float:
        """Calculate current equity including unrealized PnL."""
        equity = self.current_capital
        
        for trade in self.trades:
            if trade['status'] != 'open':
                continue
            
            symbol_data = market_data[market_data['symbol'] == trade['symbol']]
            if len(symbol_data) == 0:
                continue
            
            current_price = float(symbol_data.iloc[-1]['close'])
            
            if trade['direction'] == 'LONG':
                unrealized_pnl = (current_price - trade['entry_price']) * trade['volume']
            else:
                unrealized_pnl = (trade['entry_price'] - current_price) * trade['volume']
            
            equity += unrealized_pnl
        
        return equity
    
    def generate_performance_report(self):
        """Generate comprehensive performance metrics."""
        if not self.daily_equity:
            logger.error("No equity data available")
            return
        
        equity_series = pd.DataFrame(self.daily_equity)
        equity_series['returns'] = equity_series['equity'].pct_change()
        
        final_equity = equity_series['equity'].iloc[-1]
        total_return = (final_equity - self.initial_capital) / self.initial_capital
        
        equity_series['drawdown'] = (equity_series['peak'] - equity_series['equity']) / equity_series['peak']
        max_drawdown = equity_series['drawdown'].max()
        
        returns = equity_series['returns'].dropna()
        sharpe_ratio = np.sqrt(252) * returns.mean() / returns.std() if returns.std() > 0 else 0
        
        downside_returns = returns[returns < 0]
        sortino_ratio = np.sqrt(252) * returns.mean() / downside_returns.std() if len(downside_returns) > 0 and downside_returns.std() > 0 else 0
        
        calmar_ratio = (total_return * 100) / max_drawdown if max_drawdown > 0 else 0
        
        closed_trades = [t for t in self.trades if t['status'] == 'closed']
        winning_trades = [t for t in closed_trades if t['profit'] > 0]
        losing_trades = [t for t in closed_trades if t['profit'] <= 0]
        
        win_rate = len(winning_trades) / len(closed_trades) if closed_trades else 0
        avg_win = np.mean([t['profit'] for t in winning_trades]) if winning_trades else 0
        avg_loss = abs(np.mean([t['profit'] for t in losing_trades])) if losing_trades else 0
        profit_factor = (avg_win * len(winning_trades)) / (avg_loss * len(losing_trades)) if losing_trades else 0
        
        expectancy = (win_rate * avg_win) - ((1 - win_rate) * avg_loss)
        
        logger.info("\n" + "=" * 80)
        logger.info("INSTITUTIONAL PERFORMANCE REPORT")
        logger.info("=" * 80)
        logger.info(f"Initial Capital: ${self.initial_capital:,.2f}")
        logger.info(f"Final Equity: ${final_equity:,.2f}")
        logger.info(f"Total Return: {total_return * 100:.2f}%")
        logger.info(f"Max Drawdown: {max_drawdown * 100:.2f}%")
        logger.info(f"\nRisk-Adjusted Metrics:")
        logger.info(f"  Sharpe Ratio: {sharpe_ratio:.2f}")
        logger.info(f"  Sortino Ratio: {sortino_ratio:.2f}")
        logger.info(f"  Calmar Ratio: {calmar_ratio:.2f}")
        
        logger.info(f"\nTrading Statistics:")
        logger.info(f"  Total Trades: {len(closed_trades)}")
        logger.info(f"  Winning Trades: {len(winning_trades)}")
        logger.info(f"  Losing Trades: {len(losing_trades)}")
        logger.info(f"  Win Rate: {win_rate * 100:.1f}%")
        logger.info(f"  Average Win: ${avg_win:.2f}")
        logger.info(f"  Average Loss: ${avg_loss:.2f}")
        logger.info(f"  Profit Factor: {profit_factor:.2f}")
        logger.info(f"  Expectancy: ${expectancy:.2f}")
        
        logger.info(f"\nPer-Strategy Performance:")
        
        sorted_strategies = sorted(
            self.strategy_stats.items(),
            key=lambda x: x[1]['total_pnl'],
            reverse=True
        )
        
        for strategy_name, stats in sorted_strategies:
            win_rate_str = f"{stats['trades_won'] / stats['trades_executed'] * 100:.1f}%" if stats['trades_executed'] > 0 else "N/A"
            
            logger.info(f"\n  {strategy_name}:")
            logger.info(f"    Signals Generated: {stats['signals_generated']}")
            logger.info(f"    Trades Executed: {stats['trades_executed']}")
            logger.info(f"    Winning Trades: {stats['trades_won']}")
            logger.info(f"    Win Rate: {win_rate_str}")
            logger.info(f"    Total P/L: ${stats['total_pnl']:.2f}")
        
        logger.info("\n" + "=" * 80)


def main():
    """Execute institutional-grade backtesting."""
    
    strategy_configs = {
        'liquidity_sweep': {
            'module': 'strategies.liquidity_sweep',
            'class': 'LiquiditySweepStrategy',
            'params': {
                'enabled': True,
                'lookback_periods': [1440, 2880, 4320],
                'proximity_threshold': 10,
                'penetration_min': 3,
                'penetration_max': 15,
                'volume_threshold_multiplier': 2.0,
                'reversal_velocity_min': 5.0,
                'imbalance_threshold': 0.3,
                'vpin_threshold': 0.65,
                'min_confirmation_score': 4
            }
        }
    }
    
    engine = InstitutionalBacktestEngine(strategy_configs, INITIAL_CAPITAL)
    engine.load_strategies()
    
    if engine.run_backtest():
        engine.generate_performance_report()
    
    return True


if __name__ == "__main__":
    main()
    exit(0)
