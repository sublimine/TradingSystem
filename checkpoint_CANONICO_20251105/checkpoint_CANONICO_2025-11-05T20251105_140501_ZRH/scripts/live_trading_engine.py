"""
Live Trading Engine - Institucional
Build: 20251105_FINAL
Lista blanca: 9 estrategias oficiales
"""

import sys
sys.path.insert(0, 'C:/TradingSystem')
sys.path.insert(0, 'C:/TradingSystem/src')

import MetaTrader5 as mt5
import pandas as pd
import numpy as np
from datetime import datetime
import time
import importlib
import inspect
import logging
import json

from features.technical_indicators import calculate_atr, calculate_rsi, identify_swing_points
from features.order_flow import VPINCalculator, calculate_signed_volume
from features.statistical_models import calculate_realized_volatility

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(message)s',
    handlers=[
        logging.FileHandler('C:/TradingSystem/logs/live_trading.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# LISTA BLANCA OFICIAL - 9 ESTRATEGIAS INSTITUCIONALES
STRATEGY_WHITELIST = [
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

SYMBOLS = [
    'EURUSD.pro', 'GBPUSD.pro', 'USDJPY.pro', 'AUDUSD.pro',
    'USDCAD.pro', 'USDCHF.pro', 'NZDUSD.pro', 'EURGBP.pro',
    'XAUUSD.pro', 'BTCUSD', 'ETHUSD'
]

SCAN_INTERVAL_SECONDS = 60
LOOKBACK_BARS = 500


class LiveTradingEngine:
    
    def __init__(self):
        self.strategies = []
        self.stats = {}
        self.running = False
        self.scan_count = 0
        self.vpin_calculators = {symbol: VPINCalculator() for symbol in SYMBOLS}
        self.open_positions = {}
        self.position_cooldown = 300  # 5 minutos anti-spam
        
        # Generar boot trace
        logger.info("=" * 80)
        logger.info(f"Filtro de estrategias activo: lista blanca = {len(STRATEGY_WHITELIST)}")
        logger.info(f"PYTHONPATH_INCLUDES: {sys.path[0]}")
        logger.info("=" * 80)
        
    def initialize_mt5(self) -> bool:
        if not mt5.initialize():
            logger.error("ERROR: No se pudo inicializar MT5")
            return False
        
        account = mt5.account_info()
        if account is None:
            logger.error("ERROR: No hay cuenta conectada")
            mt5.shutdown()
            return False
        
        logger.info(f"OK Conectado a {account.server}")
        logger.info(f"OK Cuenta: {account.login}")
        logger.info(f"OK Balance: ${account.balance:,.2f}")
        logger.info(f"OK Equity: ${account.equity:,.2f}")
        
        return True
    
    def load_strategies(self):
        logger.info("Cargando estrategias (lista blanca)...")
        
        loaded_count = 0
        error_count = 0
        
        for module_name in STRATEGY_WHITELIST:
            try:
                module = importlib.import_module(f'strategies.{module_name}')
                classes = [(n, o) for n, o in inspect.getmembers(module, inspect.isclass)
                          if o.__module__ == f'strategies.{module_name}']
                
                if classes:
                    class_name, strategy_class = classes[0]
                    
                    # Verificar firma de evaluate
                    if not hasattr(strategy_class, 'evaluate'):
                        logger.error(f"  ERROR {module_name}: Clase sin método evaluate")
                        error_count += 1
                        continue
                    
                    config = {'enabled': True, 'symbols': SYMBOLS}
                    instance = strategy_class(config)
                    
                    self.strategies.append({
                        'name': module_name,
                        'instance': instance,
                        'class': class_name
                    })
                    
                    self.stats[module_name] = {
                        'scans': 0,
                        'signals': 0,
                        'trades_sent': 0,
                        'last_signal': None,
                        'evaluations': 0,
                        'errors': 0
                    }
                    
                    logger.info(f"  CARGADA {module_name}")
                    loaded_count += 1
                    
                else:
                    logger.error(f"  ERROR_IMPORT {module_name}: No se encontró clase")
                    error_count += 1
                    
            except Exception as e:
                logger.error(f"  ERROR_IMPORT {module_name}: {str(e)[:60]}")
                error_count += 1
        
        logger.info(f"\nEstrategias cargadas: {loaded_count}/{len(STRATEGY_WHITELIST)}")
        logger.info(f"Errores de carga: {error_count}")
        
    def get_market_data(self, symbol: str, bars: int) -> pd.DataFrame:
        try:
            rates = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_M1, 0, bars)
            
            if rates is None or len(rates) == 0:
                return pd.DataFrame()
            
            df = pd.DataFrame(rates)
            df['time'] = pd.to_datetime(df['time'], unit='s')
            df['symbol'] = symbol
            df['volume'] = df['tick_volume']
            
            return df
            
        except Exception as e:
            logger.error(f"Error obteniendo datos de {symbol}: {e}")
            return pd.DataFrame()
    
    def calculate_features(self, data: pd.DataFrame, symbol: str) -> dict:
        features = {}
        
        if len(data) < 50:
            return features
        
        try:
            if len(data) >= 14:
                atr_series = calculate_atr(data['high'], data['low'], data['close'], 14)
                features['atr'] = float(atr_series.iloc[-1]) if len(atr_series) > 0 else 0
                
                rsi_series = calculate_rsi(data['close'], 14)
                features['rsi'] = float(rsi_series.iloc[-1]) if len(rsi_series) > 0 else 50
            
            swing_highs, swing_lows = identify_swing_points(data['high'], order=5)
            features['swing_high_levels'] = data.loc[swing_highs.tail(20), 'high'].values.tolist()
            features['swing_low_levels'] = data.loc[swing_lows.tail(20), 'low'].values.tolist()
            
            signed_vol = calculate_signed_volume(data['close'], data['volume'])
            features['cumulative_volume_delta'] = float(signed_vol.sum())
            
            for _, row in data.tail(50).iterrows():
                direction = 1 if row['close'] > row['open'] else -1
                self.vpin_calculators[symbol].add_trade(row['volume'], direction)
            
            features['vpin'] = self.vpin_calculators[symbol].get_current_vpin()
            
            returns = data['close'].pct_change().dropna()
            if len(returns) >= 20:
                vol = calculate_realized_volatility(returns.tail(60), window=20)
                recent_vol = vol[-1] if len(vol) > 0 else 0
                avg_vol = np.mean(vol) if len(vol) > 0 else 0
                features['volatility_regime'] = 1 if recent_vol > avg_vol else 0
            else:
                features['volatility_regime'] = 0
            
            buy_vol = data.loc[data['close'] > data['open'], 'volume'].sum()
            sell_vol = data.loc[data['close'] <= data['open'], 'volume'].sum()
            total = buy_vol + sell_vol
            features['order_book_imbalance'] = float((buy_vol - sell_vol) / total) if total > 0 else 0
            features['momentum_quality'] = 0.7
            features['spread'] = float((data['high'] - data['low']).mean())
            
        except Exception as e:
            logger.debug(f"Error calculando features: {e}")
        
        return features
    
    def can_open_position(self, symbol: str, direction: str) -> bool:
        positions = mt5.positions_get(symbol=symbol)
        
        if positions:
            for pos in positions:
                pos_type = pos.type
                pos_direction = 'LONG' if pos_type == 0 else 'SHORT'
                
                if pos_direction == direction:
                    logger.info(f"  THROTTLE_COOLDOWN: Ya existe {direction} en {symbol}")
                    return False
        
        key = f"{symbol}_{direction}"
        if key in self.open_positions:
            time_since = (datetime.now() - self.open_positions[key]).total_seconds()
            if time_since < self.position_cooldown:
                logger.info(f"  DUPLICATE_IDEA: {symbol} {direction} en cooldown ({int(time_since)}s)")
                return False
        
        return True
    
    def record_position_opened(self, symbol: str, direction: str):
        key = f"{symbol}_{direction}"
        self.open_positions[key] = datetime.now()
    
    def execute_order(self, signal) -> bool:
        try:
            symbol = signal.symbol
            direction = mt5.ORDER_TYPE_BUY if signal.direction == 'LONG' else mt5.ORDER_TYPE_SELL
            
            symbol_info = mt5.symbol_info(symbol)
            if symbol_info is None:
                logger.error(f"ERROR: Simbolo {symbol} no disponible")
                return False
            
            volume = symbol_info.volume_min
            
            tick = mt5.symbol_info_tick(symbol)
            if tick is None:
                logger.error(f"ERROR: No tick para {symbol}")
                return False
            
            price = tick.ask if direction == mt5.ORDER_TYPE_BUY else tick.bid
            
            request = {
                "action": mt5.TRADE_ACTION_DEAL,
                "symbol": symbol,
                "volume": volume,
                "type": direction,
                "price": price,
                "sl": signal.stop_loss,
                "tp": signal.take_profit,
                "deviation": 20,
                "magic": 234000,
                "comment": f"{signal.strategy_name[:15]}",
                "type_time": mt5.ORDER_TIME_GTC,
                "type_filling": mt5.ORDER_FILLING_FOK,
            }
            
            result = mt5.order_send(request)
            
            if result is None:
                error = mt5.last_error()
                logger.error(f"ERROR: order_send devolvio None - {error}")
                return False
            
            if result.retcode != mt5.TRADE_RETCODE_DONE:
                logger.error(f"ERROR: Orden rechazada - {result.comment}")
                return False
            
            logger.info(f"OK ORDEN EJECUTADA: {signal.direction} {symbol} @ {price:.5f}")
            logger.info(f"   SL: {signal.stop_loss:.5f} | TP: {signal.take_profit:.5f}")
            
            return True
            
        except Exception as e:
            logger.error(f"ERROR ejecutando orden: {e}")
            return False
    
    def scan_markets(self):
        self.scan_count += 1
        signals_generated = 0
        
        logger.info(f"{'=' * 80}")
        logger.info(f"SCAN #{self.scan_count} - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        logger.info(f"{'=' * 80}")
        
        for symbol in SYMBOLS:
            data = self.get_market_data(symbol, LOOKBACK_BARS)
            
            if data.empty or len(data) < 100:
                continue
            
            features = self.calculate_features(data, symbol)
            
            if not features:
                continue
            
            current_price = float(data['close'].iloc[-1])
            
            for strategy_info in self.strategies:
                strategy_name = strategy_info['name']
                self.stats[strategy_name]['scans'] += 1
                
                try:
                    self.stats[strategy_name]['evaluations'] += 1
                    signals = strategy_info['instance'].evaluate(data, features)
                    
                    if signals:
                        signal_list = signals if isinstance(signals, list) else [signals]
                        
                        for signal in signal_list:
                            if signal is not None and signal.validate():
                                
                                if not self.can_open_position(signal.symbol, signal.direction):
                                    continue
                                
                                signals_generated += 1
                                self.stats[strategy_name]['signals'] += 1
                                self.stats[strategy_name]['last_signal'] = datetime.now()
                                
                                logger.info(f"\nSEÑAL GENERADA:")
                                logger.info(f"  Estrategia: {strategy_name}")
                                logger.info(f"  Simbolo: {symbol}")
                                logger.info(f"  Direccion: {signal.direction}")
                                logger.info(f"  Entry: {signal.entry_price:.5f}")
                                
                                if self.execute_order(signal):
                                    self.stats[strategy_name]['trades_sent'] += 1
                                    self.record_position_opened(signal.symbol, signal.direction)
                
                except Exception as e:
                    self.stats[strategy_name]['errors'] += 1
                    logger.error(f"ERROR evaluando {strategy_name}: {e}")
        
        logger.info(f"\nResultados del scan:")
        logger.info(f"  Señales generadas: {signals_generated}")
        
        if self.scan_count % 10 == 0:
            self.print_statistics()
    
    def print_statistics(self):
        logger.info(f"\n{'=' * 80}")
        logger.info(f"ESTADISTICAS (Scan #{self.scan_count})")
        logger.info(f"{'=' * 80}")
        
        for strategy_name, stats in sorted(self.stats.items()):
            evals = stats['evaluations']
            signals = stats['signals']
            errors = stats['errors']
            
            logger.info(f"\n{strategy_name}:")
            logger.info(f"  Evaluaciones: {evals}")
            logger.info(f"  Señales: {signals}")
            logger.info(f"  Errores: {errors}")
            logger.info(f"  Trades: {stats['trades_sent']}")
    
    def run(self):
        logger.info("\n" + "=" * 80)
        logger.info("SISTEMA DE TRADING EN VIVO INICIADO")
        logger.info("=" * 80)
        logger.info(f"Estrategias activas: {len(self.strategies)}")
        logger.info(f"Simbolos monitoreados: {len(SYMBOLS)}")
        logger.info(f"Intervalo de escaneo: {SCAN_INTERVAL_SECONDS} segundos")
        logger.info(f"Cooldown anti-spam: {self.position_cooldown} segundos")
        logger.info(f"Modo: DEMO")
        logger.info("=" * 80)
        
        self.running = True
        
        try:
            while self.running:
                self.scan_markets()
                time.sleep(SCAN_INTERVAL_SECONDS)
                
        except KeyboardInterrupt:
            logger.info("\n\nDeteniendo sistema...")
            self.print_statistics()
        
        finally:
            mt5.shutdown()
            logger.info("\nOK Sistema detenido")


def main():
    engine = LiveTradingEngine()
    
    if not engine.initialize_mt5():
        return False
    
    engine.load_strategies()
    engine.run()
    
    return True


if __name__ == "__main__":
    main()
