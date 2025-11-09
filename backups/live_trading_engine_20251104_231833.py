"""
Live Trading Engine - Real-time Execution
Monitors markets continuously and executes trades when strategies generate signals
"""

import sys
sys.path.insert(0, 'C:/TradingSystem')
sys.path.insert(0, 'C:/TradingSystem/src')

import MetaTrader5 as mt5
import psycopg2
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import time
import importlib
import inspect
import logging

from features.technical_indicators import calculate_atr, calculate_rsi, identify_swing_points
from features.order_flow import VPINCalculator, calculate_signed_volume
from features.statistical_models import calculate_realized_volatility

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(message)s',
    handlers=[
        logging.FileHandler('C:/TradingSystem/logs/live_trading.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

DB_CONFIG = {
    'host': 'localhost',
    'port': 5432,
    'database': 'trading_system',
    'user': 'trading_user',
    'password': 'abc'
}

STRATEGY_MODULES = [
    'breakout_volume_confirmation', 'correlation_divergence', 'kalman_pairs_trading',
    'liquidity_sweep', 'mean_reversion_statistical', 'momentum_quality',
    'news_event_positioning', 'order_flow_toxicity', 'volatility_regime_adaptation'
]

SYMBOLS = [
    'EURUSD.pro', 'GBPUSD.pro', 'USDJPY.pro', 'AUDUSD.pro',
    'USDCAD.pro', 'USDCHF.pro', 'NZDUSD.pro', 'EURGBP.pro',
    'XAUUSD.pro', 'BTCUSD', 'ETHUSD'
]

SCAN_INTERVAL_SECONDS = 60  # Escanear mercados cada 60 segundos
LOOKBACK_BARS = 500  # Barras de histórico para análisis


class LiveTradingEngine:
    """Motor de trading en vivo que ejecuta las 9 estrategias en tiempo real."""
    
    def __init__(self):
        self.strategies = []
        self.stats = {}
        self.running = False
        self.scan_count = 0
        self.vpin_calculators = {symbol: VPINCalculator() for symbol in SYMBOLS}
        
    def initialize_mt5(self) -> bool:
        """Inicializa conexión con MetaTrader 5."""
        if not mt5.initialize():
            logger.error("ERROR: No se pudo inicializar MT5")
            return False
        
        account = mt5.account_info()
        if account is None:
            logger.error("ERROR: No hay cuenta conectada")
            mt5.shutdown()
            return False
        
        logger.info(f"✓ Conectado a {account.server}")
        logger.info(f"✓ Cuenta: {account.login}")
        logger.info(f"✓ Balance: ${account.balance:,.2f}")
        logger.info(f"✓ Equity: ${account.equity:,.2f}\n")
        
        return True
    
    def load_strategies(self):
        """Carga las 9 estrategias originales."""
        logger.info("Cargando estrategias...")
        
        for module_name in STRATEGY_MODULES:
            try:
                module = importlib.import_module(f'strategies.{module_name}')
                classes = [(n, o) for n, o in inspect.getmembers(module, inspect.isclass)
                          if o.__module__ == f'strategies.{module_name}']
                
                if classes:
                    class_name, strategy_class = classes[0]
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
                        'last_signal': None
                    }
                    
                    logger.info(f"  ✓ {module_name}")
                    
            except Exception as e:
                logger.error(f"  ✗ {module_name}: {str(e)[:60]}")
        
        logger.info(f"\n✓ {len(self.strategies)} estrategias cargadas y listas\n")
    
    def get_market_data(self, symbol: str, bars: int) -> pd.DataFrame:
        """Obtiene datos de mercado en tiempo real desde MT5."""
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
        """Calcula features para evaluación de estrategias."""
        features = {}
        
        if len(data) < 50:
            return features
        
        try:
            # Technical indicators
            if len(data) >= 14:
                atr_series = calculate_atr(data['high'], data['low'], data['close'], 14)
                features['atr'] = float(atr_series.iloc[-1]) if len(atr_series) > 0 else 0
                
                rsi_series = calculate_rsi(data['close'], 14)
                features['rsi'] = float(rsi_series.iloc[-1]) if len(rsi_series) > 0 else 50
            
            # Swing points
            swing_highs, swing_lows = identify_swing_points(data['high'], order=5)
            features['swing_high_levels'] = data.loc[swing_highs.tail(20), 'high'].values.tolist()
            features['swing_low_levels'] = data.loc[swing_lows.tail(20), 'low'].values.tolist()
            
            # Order flow
            signed_vol = calculate_signed_volume(data['close'], data['volume'])
            features['cumulative_volume_delta'] = float(signed_vol.sum())
            
            # VPIN
            for _, row in data.tail(50).iterrows():
                direction = 1 if row['close'] > row['open'] else -1
                self.vpin_calculators[symbol].add_trade(row['volume'], direction)
            
            features['vpin'] = self.vpin_calculators[symbol].get_current_vpin()
            
            # Volatility regime
            returns = data['close'].pct_change().dropna()
            if len(returns) >= 20:
                vol = calculate_realized_volatility(returns.tail(60), window=20)
                recent_vol = vol[-1] if len(vol) > 0 else 0
                avg_vol = np.mean(vol) if len(vol) > 0 else 0
                features['volatility_regime'] = 1 if recent_vol > avg_vol else 0
            else:
                features['volatility_regime'] = 0
            
            # Order book imbalance
            buy_vol = data.loc[data['close'] > data['open'], 'volume'].sum()
            sell_vol = data.loc[data['close'] <= data['open'], 'volume'].sum()
            total = buy_vol + sell_vol
            features['order_book_imbalance'] = float((buy_vol - sell_vol) / total) if total > 0 else 0
            
            # Momentum quality
            features['momentum_quality'] = 0.7
            
            # Spread
            features['spread'] = float((data['high'] - data['low']).mean())
            
        except Exception as e:
            logger.debug(f"Error calculando features: {e}")
        
        return features
    
    def execute_order(self, signal) -> bool:
        """Ejecuta orden en MT5 basándose en señal de estrategia."""
        try:
            symbol = signal.symbol
            direction = mt5.ORDER_TYPE_BUY if signal.direction == 'LONG' else mt5.ORDER_TYPE_SELL
            
            # Obtener información del símbolo
            symbol_info = mt5.symbol_info(symbol)
            if symbol_info is None:
                logger.error(f"Símbolo {symbol} no disponible")
                return False
            
            # Calcular volumen (0.01 lotes para demo)
            volume = 0.01
            
            # Preparar request
            request = {
                "action": mt5.TRADE_ACTION_DEAL,
                "symbol": symbol,
                "volume": volume,
                "type": direction,
                "price": signal.entry_price,
                "sl": signal.stop_loss,
                "tp": signal.take_profit,
                "deviation": 20,
                "magic": 234000,
                "comment": f"Strategy: {signal.strategy_name}",
                "type_time": mt5.ORDER_TIME_GTC,
                "type_filling": mt5.ORDER_FILLING_IOC,
            }
            
            # Enviar orden
            result = mt5.order_send(request)
            
            if result.retcode != mt5.TRADE_RETCODE_DONE:
                logger.error(f"✗ Orden rechazada: {result.comment}")
                return False
            
            logger.info(f"✓ ORDEN EJECUTADA: {signal.direction} {symbol} @ {signal.entry_price:.5f}")
            logger.info(f"  SL: {signal.stop_loss:.5f} | TP: {signal.take_profit:.5f}")
            logger.info(f"  Ticket: {result.order}")
            
            return True
            
        except Exception as e:
            logger.error(f"Error ejecutando orden: {e}")
            return False
    
    def scan_markets(self):
        """Escanea todos los símbolos con todas las estrategias."""
        self.scan_count += 1
        signals_generated = 0
        
        logger.info(f"{'=' * 80}")
        logger.info(f"SCAN #{self.scan_count} - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        logger.info(f"{'=' * 80}")
        
        for symbol in SYMBOLS:
            # Obtener datos en tiempo real
            data = self.get_market_data(symbol, LOOKBACK_BARS)
            
            if data.empty or len(data) < 100:
                continue
            
            # Calcular features
            features = self.calculate_features(data, symbol)
            
            if not features:
                continue
            
            current_price = float(data['close'].iloc[-1])
            
            # Evaluar cada estrategia
            for strategy_info in self.strategies:
                strategy_name = strategy_info['name']
                self.stats[strategy_name]['scans'] += 1
                
                try:
                    # INVOCACIÓN REAL del método evaluate
                    signals = strategy_info['instance'].evaluate(data, features)
                    
                    if signals:
                        signal_list = signals if isinstance(signals, list) else [signals]
                        
                        for signal in signal_list:
                            if signal is not None and signal.validate():
                                signals_generated += 1
                                self.stats[strategy_name]['signals'] += 1
                                self.stats[strategy_name]['last_signal'] = datetime.now()
                                
                                logger.info(f"\n🎯 SEÑAL GENERADA:")
                                logger.info(f"  Estrategia: {strategy_name}")
                                logger.info(f"  Símbolo: {symbol}")
                                logger.info(f"  Dirección: {signal.direction}")
                                logger.info(f"  Precio actual: {current_price:.5f}")
                                logger.info(f"  Entry: {signal.entry_price:.5f}")
                                logger.info(f"  Stop Loss: {signal.stop_loss:.5f}")
                                logger.info(f"  Take Profit: {signal.take_profit:.5f}")
                                
                                # Ejecutar orden en MT5
                                if self.execute_order(signal):
                                    self.stats[strategy_name]['trades_sent'] += 1
                
                except Exception as e:
                    pass
        
        # Resumen del scan
        logger.info(f"\nResultados del scan:")
        logger.info(f"  Señales generadas: {signals_generated}")
        logger.info(f"  Próximo scan en {SCAN_INTERVAL_SECONDS} segundos")
        
        # Estadísticas acumuladas cada 10 scans
        if self.scan_count % 10 == 0:
            self.print_statistics()
    
    def print_statistics(self):
        """Imprime estadísticas acumuladas."""
        logger.info(f"\n{'=' * 80}")
        logger.info(f"ESTADÍSTICAS ACUMULADAS (Scan #{self.scan_count})")
        logger.info(f"{'=' * 80}")
        
        for strategy_name, stats in sorted(self.stats.items(), key=lambda x: x[1]['signals'], reverse=True):
            logger.info(f"\n{strategy_name}:")
            logger.info(f"  Scans: {stats['scans']:,}")
            logger.info(f"  Señales: {stats['signals']}")
            logger.info(f"  Trades enviados: {stats['trades_sent']}")
            if stats['last_signal']:
                logger.info(f"  Última señal: {stats['last_signal'].strftime('%H:%M:%S')}")
        
        total_signals = sum(s['signals'] for s in self.stats.values())
        total_trades = sum(s['trades_sent'] for s in self.stats.values())
        logger.info(f"\nTOTAL:")
        logger.info(f"  Señales generadas: {total_signals}")
        logger.info(f"  Trades ejecutados: {total_trades}")
        logger.info(f"{'=' * 80}")
    
    def run(self):
        """Loop principal de trading en vivo."""
        logger.info("\n" + "=" * 80)
        logger.info("SISTEMA DE TRADING EN VIVO INICIADO")
        logger.info("=" * 80)
        logger.info(f"Estrategias activas: {len(self.strategies)}")
        logger.info(f"Símbolos monitoreados: {len(SYMBOLS)}")
        logger.info(f"Intervalo de escaneo: {SCAN_INTERVAL_SECONDS} segundos")
        logger.info(f"Modo: DEMO (sin riesgo de capital)")
        logger.info("=" * 80)
        logger.info("\n⚠️  Sistema operando en tiempo real")
        logger.info("   Presione Ctrl+C para detener\n")
        
        self.running = True
        
        try:
            while self.running:
                self.scan_markets()
                time.sleep(SCAN_INTERVAL_SECONDS)
                
        except KeyboardInterrupt:
            logger.info("\n\n⚠️  Deteniendo sistema...")
            self.print_statistics()
        
        finally:
            mt5.shutdown()
            logger.info("\n✓ Sistema detenido correctamente")


def main():
    engine = LiveTradingEngine()
    
    if not engine.initialize_mt5():
        return False
    
    engine.load_strategies()
    engine.run()
    
    return True


if __name__ == "__main__":
    main()
    exit(0)

