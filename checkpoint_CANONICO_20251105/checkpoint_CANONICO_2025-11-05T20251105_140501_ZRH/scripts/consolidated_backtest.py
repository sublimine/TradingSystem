"""
Consolidated Backtesting Framework for Original Nine Strategies
Evaluates complete portfolio over available historical data
"""

import sys
import os
sys.path.insert(0, 'C:/TradingSystem')
sys.path.insert(0, 'C:/TradingSystem/src')

import psycopg2
import pandas as pd
import numpy as np
from datetime import datetime
import importlib
import logging

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

STRATEGY_MODULES = [
    'breakout_volume_confirmation',
    'correlation_divergence',
    'kalman_pairs_trading',
    'liquidity_sweep',
    'mean_reversion_statistical',
    'momentum_quality',
    'news_event_positioning',
    'order_flow_toxicity',
    'volatility_regime_adaptation'
]


def load_strategies():
    """Dynamically load all nine original strategies."""
    strategies = []
    
    for module_name in STRATEGY_MODULES:
        try:
            module = importlib.import_module(f'strategies.{module_name}')
            
            class_name = ''.join(word.capitalize() for word in module_name.split('_'))
            
            if hasattr(module, class_name):
                strategy_class = getattr(module, class_name)
                
                config = {
                    'enabled': True,
                    'symbols': [
                        'EURUSD.pro', 'GBPUSD.pro', 'USDJPY.pro', 'AUDUSD.pro',
                        'USDCAD.pro', 'USDCHF.pro', 'NZDUSD.pro', 'EURGBP.pro',
                        'XAUUSD.pro', 'BTCUSD', 'ETHUSD'
                    ]
                }
                
                try:
                    strategy = strategy_class(config)
                    strategies.append(strategy)
                    logger.info(f"✓ Loaded: {strategy.strategy_name}")
                except Exception as e:
                    logger.error(f"✗ Failed to instantiate {class_name}: {e}")
            else:
                logger.warning(f"Class {class_name} not found in {module_name}")
                
        except Exception as e:
            logger.error(f"✗ Failed to load module {module_name}: {e}")
    
    return strategies


class ConsolidatedBacktestEngine:
    """Backtesting engine evaluating all nine strategies together."""
    
    def __init__(self, strategies, initial_capital):
        self.strategies = strategies
        self.initial_capital = initial_capital
        self.current_capital = initial_capital
        self.equity_peak = initial_capital
        
        self.trades = []
        self.daily_equity = []
        self.strategy_stats = {s.strategy_name: {
            'signals_generated': 0,
            'trades_executed': 0,
            'trades_won': 0,
            'total_pnl': 0.0
        } for s in strategies}
        
    def run_backtest(self):
        """Execute consolidated backtest over all available historical data."""
        logger.info("=" * 80)
        logger.info("CONSOLIDATED BACKTEST: 9 ORIGINAL STRATEGIES")
        logger.info("=" * 80)
        
        conn = psycopg2.connect(**DB_CONFIG)
        
        all_data = pd.read_sql_query("""
            SELECT symbol, time, open, high, low, close
            FROM market_data
            ORDER BY time
        """, conn)
        
        conn.close()
        
        if all_data.empty:
            logger.error("No historical data available in database")
            return False
        
        dates = sorted(all_data['time'].unique())
        
        logger.info(f"Period: {dates[0].date()} to {dates[-1].date()}")
        logger.info(f"Trading days: {len(dates)}")
        logger.info(f"Strategies: {len(self.strategies)}")
        logger.info(f"Initial capital: ${self.initial_capital:,.2f}\n")
        
        max_lookback = max(s.get_required_lookback_bars() for s in self.strategies)
        
        for i, date in enumerate(dates):
            if i < max_lookback:
                continue
            
            historical_data = all_data[all_data['time'] <= date]
            current_day_data = all_data[all_data['time'] == date]
            
            self._update_open_trades(date, current_day_data)
            
            current_equity = self._calculate_current_equity(current_day_data)
            
            if current_equity > self.equity_peak:
                self.equity_peak = current_equity
            
            self.daily_equity.append({
                'date': date,
                'equity': current_equity,
                'peak': self.equity_peak
            })
            
            for strategy in self.strategies:
                if not strategy.enabled:
                    continue
                
                for symbol in strategy.get_applicable_symbols():
                    try:
                        symbol_history = historical_data[historical_data['symbol'] == symbol]
                        
                        if len(symbol_history) < strategy.get_required_lookback_bars():
                            continue
                        
                        signal = strategy.analyze_market(symbol, symbol_history, date)
                        
                        if signal is not None:
                            self.strategy_stats[strategy.strategy_name]['signals_generated'] += 1
                            self._execute_trade(signal, date)
                            
                    except Exception as e:
                        pass
            
            if (i + 1) % 100 == 0:
                progress = (i + 1) / len(dates) * 100
                open_trades = len([t for t in self.trades if t['status'] == 'open'])
                logger.info(f"Progress: {progress:.1f}% - Equity: ${current_equity:,.2f} - Open: {open_trades}")
        
        logger.info("\nBacktest execution completed")
        return True
    
    def _execute_trade(self, signal, entry_date):
        """Execute trade from signal."""
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
            'strategy': signal.strategy_name,
            'direction': signal.direction,
            'entry_price': entry_price,
            'stop_loss': signal.stop_loss,
            'take_profit': signal.take_profit,
            'volume': volume,
            'status': 'open'
        }
        
        self.trades.append(trade)
        self.strategy_stats[signal.strategy_name]['trades_executed'] += 1
    
    def _update_open_trades(self, date, market_data):
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
    
    def _calculate_current_equity(self, market_data):
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
    
    def generate_report(self):
        """Generate comprehensive performance report."""
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
        
        closed_trades = [t for t in self.trades if t['status'] == 'closed']
        winning_trades = [t for t in closed_trades if t['profit'] > 0]
        losing_trades = [t for t in closed_trades if t['profit'] <= 0]
        
        win_rate = len(winning_trades) / len(closed_trades) if closed_trades else 0
        avg_win = np.mean([t['profit'] for t in winning_trades]) if winning_trades else 0
        avg_loss = abs(np.mean([t['profit'] for t in losing_trades])) if losing_trades else 0
        profit_factor = (avg_win * len(winning_trades)) / (avg_loss * len(losing_trades)) if losing_trades else 0
        
        logger.info("\n" + "=" * 80)
        logger.info("CONSOLIDATED PORTFOLIO RESULTS")
        logger.info("=" * 80)
        logger.info(f"Initial Capital: ${self.initial_capital:,.2f}")
        logger.info(f"Final Equity: ${final_equity:,.2f}")
        logger.info(f"Total Return: {total_return * 100:.2f}%")
        logger.info(f"Max Drawdown: {max_drawdown * 100:.2f}%")
        logger.info(f"Sharpe Ratio: {sharpe_ratio:.2f}")
        
        logger.info(f"\nAggregate Trading Statistics:")
        logger.info(f"  Total Trades: {len(closed_trades)}")
        logger.info(f"  Winning Trades: {len(winning_trades)}")
        logger.info(f"  Losing Trades: {len(losing_trades)}")
        logger.info(f"  Win Rate: {win_rate * 100:.1f}%")
        logger.info(f"  Average Win: ${avg_win:.2f}")
        logger.info(f"  Average Loss: ${avg_loss:.2f}")
        logger.info(f"  Profit Factor: {profit_factor:.2f}")
        
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
    """Execute consolidated backtesting of nine original strategies."""
    
    logger.info("Loading nine original strategies...")
    strategies = load_strategies()
    
    if not strategies:
        logger.error("No strategies loaded successfully")
        return False
    
    logger.info(f"\nSuccessfully loaded {len(strategies)} strategies\n")
    
    engine = ConsolidatedBacktestEngine(strategies, INITIAL_CAPITAL)
    
    if not engine.run_backtest():
        return False
    
    engine.generate_report()
    
    return True


if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
