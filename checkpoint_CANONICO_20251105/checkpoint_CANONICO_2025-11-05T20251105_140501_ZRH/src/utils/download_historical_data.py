# -*- coding: utf-8 -*-
import sys
import yaml
import logging
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Optional, Tuple

import MetaTrader5 as mt5
import pandas as pd
import psycopg2
from psycopg2.extras import execute_batch

PROJECT_ROOT = Path(__file__).parent.parent.parent
CONFIG_PATH = PROJECT_ROOT / "config" / "production" / "config.yaml"
LOG_DIR = PROJECT_ROOT / "logs" / "data_capture"
LOG_DIR.mkdir(parents=True, exist_ok=True)

log_file = LOG_DIR / f"download_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file, encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)


def load_config():
    try:
        with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        logger.info("Configuration loaded successfully")
        return config
    except Exception as e:
        logger.error(f"Failed to load configuration: {e}")
        sys.exit(1)


def initialize_mt5(config):
    try:
        logger.info("Connecting to MT5...")
        
        if not mt5.initialize():
            error = mt5.last_error()
            logger.error(f"MT5 initialization failed: {error}")
            return False
        
        terminal_info = mt5.terminal_info()
        if terminal_info is None:
            logger.error("Cannot access MT5 terminal information")
            mt5.shutdown()
            return False
        
        if not terminal_info.connected:
            logger.error("MT5 is not connected to trade server")
            mt5.shutdown()
            return False
        
        account_info = mt5.account_info()
        if account_info is None:
            logger.error("Cannot access account information")
            mt5.shutdown()
            return False
        
        logger.info("=" * 60)
        logger.info("MT5 CONNECTION SUCCESSFUL")
        logger.info(f"Account Number: {account_info.login}")
        logger.info(f"Server: {account_info.server}")
        logger.info(f"Balance: {account_info.balance:.2f} {account_info.currency}")
        logger.info(f"Leverage: 1:{account_info.leverage}")
        logger.info(f"Company: {account_info.company}")
        logger.info("=" * 60)
        
        return True
        
    except Exception as e:
        logger.error(f"Unexpected error during MT5 initialization: {e}")
        return False


def get_db_connection(config):
    try:
        conn = psycopg2.connect(
            host=config['database']['host'],
            port=config['database']['port'],
            database=config['database']['name'],
            user=config['database']['user'],
            password=config['database']['password']
        )
        logger.info("Database connection established")
        return conn
    except Exception as e:
        logger.error(f"Database connection failed: {e}")
        sys.exit(1)


def get_last_timestamp(conn, symbol):
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                "SELECT MAX(time) FROM market_data WHERE symbol = %s AND timeframe = 'M1'",
                (symbol,)
            )
            result = cursor.fetchone()[0]
            if result:
                logger.info(f"{symbol}: Found existing data up to {result}")
            return result
    except Exception as e:
        logger.warning(f"Error checking existing data for {symbol}: {e}")
        return None


def download_symbol_bars(symbol, start_date, end_date):
    try:
        rates = mt5.copy_rates_range(symbol, mt5.TIMEFRAME_M1, start_date, end_date)
        
        if rates is None or len(rates) == 0:
            logger.warning(f"{symbol}: No data returned from MT5")
            return None
        
        df = pd.DataFrame(rates)
        df['time'] = pd.to_datetime(df['time'], unit='s')
        df['symbol'] = symbol
        df['timeframe'] = 'M1'
        
        logger.info(f"{symbol}: Downloaded {len(df):,} bars")
        return df
        
    except Exception as e:
        logger.error(f"{symbol}: Download error - {e}")
        return None


def validate_data(df, symbol):
    issues = []
    
    if df['time'].isnull().any():
        issues.append("Null timestamps detected")
    
    if df['time'].duplicated().any():
        count = df['time'].duplicated().sum()
        issues.append(f"{count} duplicate timestamps")
    
    for col in ['open', 'high', 'low', 'close']:
        if (df[col] <= 0).any():
            issues.append(f"Invalid {col} prices")
    
    invalid_ohlc = df[
        (df['high'] < df['low']) |
        (df['high'] < df['open']) |
        (df['high'] < df['close']) |
        (df['low'] > df['open']) |
        (df['low'] > df['close'])
    ]
    if len(invalid_ohlc) > 0:
        issues.append(f"{len(invalid_ohlc)} bars with invalid OHLC")
    
    return len(issues) == 0, issues


def insert_data_batch(conn, df):
    try:
        with conn.cursor() as cursor:
            insert_query = """
                INSERT INTO market_data 
                (time, symbol, timeframe, open, high, low, close, tick_volume, spread, real_volume)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (time, symbol, timeframe) DO NOTHING
            """
            
            data_tuples = [
                (
                    row['time'],
                    row['symbol'],
                    row['timeframe'],
                    float(row['open']),
                    float(row['high']),
                    float(row['low']),
                    float(row['close']),
                    int(row['tick_volume']),
                    int(row['spread']),
                    int(row['real_volume'])
                )
                for _, row in df.iterrows()
            ]
            
            execute_batch(cursor, insert_query, data_tuples, page_size=1000)
            conn.commit()
            
            logger.info(f"Inserted {len(data_tuples):,} bars into database")
            
    except Exception as e:
        logger.error(f"Insert error: {e}")
        conn.rollback()
        raise


def download_symbol(conn, symbol):
    logger.info(f"\n{'='*60}")
    logger.info(f"Processing: {symbol}")
    logger.info(f"{'='*60}")
    
    last_timestamp = get_last_timestamp(conn, symbol)
    
    if last_timestamp:
        start_date = last_timestamp + timedelta(minutes=1)
        logger.info(f"{symbol}: Resuming from {start_date}")
    else:
        start_date = datetime(2025, 9, 1, 0, 0, 0)
        logger.info(f"{symbol}: Starting fresh from {start_date}")
    
    end_date = datetime(2025, 11, 1, 0, 0, 0)
    
    if start_date >= end_date:
        logger.info(f"{symbol}: Already up to date")
        return True
    
    df = download_symbol_bars(symbol, start_date, end_date)
    
    if df is None or len(df) == 0:
        logger.warning(f"{symbol}: No new data available")
        return False
    
    is_valid, issues = validate_data(df, symbol)
    if not is_valid:
        logger.warning(f"{symbol}: Validation issues - {'; '.join(issues)}")
    
    insert_data_batch(conn, df)
    
    return True


def get_all_symbols(config):
    symbols = []
    symbols.extend(config['universe']['forex_majors'])
    symbols.extend(config['universe']['forex_jpy_crosses'])
    symbols.extend(config['universe']['commodities'])
    symbols.extend(config['universe']['crypto'])
    return symbols


def main():
    logger.info("\n" + "="*80)
    logger.info("HISTORICAL DATA DOWNLOAD SESSION STARTED")
    logger.info("="*80 + "\n")
    
    config = load_config()
    
    if not initialize_mt5(config):
        logger.error("Cannot proceed without MT5 connection")
        sys.exit(1)
    
    conn = get_db_connection(config)
    
    symbols = get_all_symbols(config)
    logger.info(f"Total symbols to process: {len(symbols)}")
    logger.info(f"Symbols: {', '.join(symbols)}\n")
    
    successful = 0
    failed = 0
    
    for symbol in symbols:
        try:
            if download_symbol(conn, symbol):
                successful += 1
            else:
                failed += 1
        except Exception as e:
            logger.error(f"{symbol}: Unexpected error - {e}")
            failed += 1
    
    conn.close()
    mt5.shutdown()
    
    logger.info("\n" + "="*80)
    logger.info(f"DOWNLOAD SESSION COMPLETED")
    logger.info(f"Successful: {successful}/{len(symbols)}")
    logger.info(f"Failed: {failed}/{len(symbols)}")
    logger.info("="*80)


if __name__ == "__main__":
    main()