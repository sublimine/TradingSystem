"""
Backtest Data Loader - MANDATO 17

Carga datos históricos para backtest desde múltiples fuentes:
1. CSV files (formato estándar OHLCV)
2. MT5 connector (via MetaTrader 5)
3. Pickle cache (optimización)

Formato estándar:
- DatetimeIndex con timezone UTC
- Columns: [open, high, low, close, volume]
- Resampling a múltiples timeframes (M1, M5, M15, H1, H4, D1)
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from pathlib import Path
import logging
import pickle

logger = logging.getLogger(__name__)


class BacktestDataLoader:
    """
    Carga y gestiona datos históricos para backtest institucional.

    Features:
    - Multi-timeframe resampling (M1 → M5, M15, H1, H4, D1)
    - Cache para optimizar recargas
    - Validación de calidad de datos (gaps, outliers)
    - Soporte CSV y MT5
    """

    def __init__(self, data_dir: str = "data/historical", cache_dir: str = "data/cache"):
        """
        Inicializar data loader.

        Args:
            data_dir: Directorio con archivos CSV históricos
            cache_dir: Directorio para cache pickle
        """
        self.data_dir = Path(data_dir)
        self.cache_dir = Path(cache_dir)

        # Crear directorios si no existen
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        # Cache de datos cargados: {symbol: {timeframe: DataFrame}}
        self.data_cache: Dict[str, Dict[str, pd.DataFrame]] = {}

        logger.info(f"BacktestDataLoader initialized: data_dir={data_dir}, cache_dir={cache_dir}")

    def load_csv(self, symbol: str, csv_path: str, timeframe: str = "M1") -> pd.DataFrame:
        """
        Cargar datos desde CSV.

        Formato esperado:
        - Columna 'timestamp' o 'datetime' o DatetimeIndex
        - Columnas: open, high, low, close, volume

        Args:
            symbol: Símbolo
            csv_path: Ruta al archivo CSV
            timeframe: Timeframe de los datos ('M1', 'M5', 'H1', etc.)

        Returns:
            DataFrame con OHLCV + DatetimeIndex UTC
        """
        logger.info(f"Loading CSV: {symbol} {timeframe} from {csv_path}")

        # Leer CSV
        df = pd.read_csv(csv_path)

        # Detectar columna de timestamp
        time_col = None
        for col in ['timestamp', 'datetime', 'time', 'date']:
            if col in df.columns:
                time_col = col
                break

        if time_col:
            df[time_col] = pd.to_datetime(df[time_col])
            df.set_index(time_col, inplace=True)
        elif not isinstance(df.index, pd.DatetimeIndex):
            raise ValueError(f"CSV must have datetime column or DatetimeIndex: {csv_path}")

        # Asegurar que el índice sea DatetimeIndex con UTC
        if not isinstance(df.index, pd.DatetimeIndex):
            df.index = pd.to_datetime(df.index)

        if df.index.tz is None:
            df.index = df.index.tz_localize('UTC')

        # Validar columnas OHLCV (case-insensitive)
        required_cols = ['open', 'high', 'low', 'close', 'volume']
        df.columns = df.columns.str.lower()

        missing_cols = [col for col in required_cols if col not in df.columns]
        if missing_cols:
            # Intentar inferir columnas faltantes
            if 'volume' in missing_cols and 'tick_volume' in df.columns:
                df['volume'] = df['tick_volume']
                missing_cols.remove('volume')

        if missing_cols:
            raise ValueError(f"CSV missing required columns: {missing_cols}")

        # Seleccionar solo OHLCV
        df = df[required_cols].copy()

        # Validar calidad de datos
        df = self._validate_data_quality(df, symbol)

        # Ordenar por timestamp
        df.sort_index(inplace=True)

        logger.info(f"Loaded {len(df)} bars for {symbol} {timeframe}: {df.index[0]} to {df.index[-1]}")

        # Guardar en cache
        if symbol not in self.data_cache:
            self.data_cache[symbol] = {}
        self.data_cache[symbol][timeframe] = df

        return df

    def load_mt5(self, symbol: str, start_date: datetime, end_date: datetime,
                 timeframe: str = "M1", mt5_connector = None) -> pd.DataFrame:
        """
        Cargar datos desde MetaTrader 5.

        Args:
            symbol: Símbolo MT5
            start_date: Fecha inicio
            end_date: Fecha fin
            timeframe: Timeframe ('M1', 'M5', 'M15', 'H1', 'H4', 'D1')
            mt5_connector: Instancia de MT5Connector (opcional)

        Returns:
            DataFrame OHLCV
        """
        logger.info(f"Loading MT5: {symbol} {timeframe} from {start_date} to {end_date}")

        if mt5_connector is None:
            # Intentar importar MT5Connector
            try:
                from src.mt5_connector import MT5Connector
                mt5_connector = MT5Connector()
                mt5_connector.connect()
            except Exception as e:
                raise RuntimeError(f"MT5 connector not available: {e}")

        # Mapear timeframe string a MT5 constante
        import MetaTrader5 as mt5
        tf_map = {
            'M1': mt5.TIMEFRAME_M1,
            'M5': mt5.TIMEFRAME_M5,
            'M15': mt5.TIMEFRAME_M15,
            'M30': mt5.TIMEFRAME_M30,
            'H1': mt5.TIMEFRAME_H1,
            'H4': mt5.TIMEFRAME_H4,
            'D1': mt5.TIMEFRAME_D1,
        }

        if timeframe not in tf_map:
            raise ValueError(f"Invalid timeframe: {timeframe}")

        # Obtener datos
        rates = mt5.copy_rates_range(symbol, tf_map[timeframe], start_date, end_date)

        if rates is None or len(rates) == 0:
            raise ValueError(f"No data returned from MT5 for {symbol} {timeframe}")

        # Convertir a DataFrame
        df = pd.DataFrame(rates)
        df['time'] = pd.to_datetime(df['time'], unit='s')
        df.set_index('time', inplace=True)
        df.index = df.index.tz_localize('UTC')

        # Renombrar columnas
        df.rename(columns={'tick_volume': 'volume'}, inplace=True)

        # Seleccionar OHLCV
        df = df[['open', 'high', 'low', 'close', 'volume']].copy()

        # Validar calidad
        df = self._validate_data_quality(df, symbol)

        logger.info(f"Loaded {len(df)} bars from MT5 for {symbol} {timeframe}")

        # Guardar en cache
        if symbol not in self.data_cache:
            self.data_cache[symbol] = {}
        self.data_cache[symbol][timeframe] = df

        return df

    def resample_to_timeframe(self, df: pd.DataFrame, target_timeframe: str) -> pd.DataFrame:
        """
        Resample OHLCV data a otro timeframe.

        Args:
            df: DataFrame OHLCV original
            target_timeframe: Timeframe objetivo ('M5', 'M15', 'H1', 'H4', 'D1')

        Returns:
            DataFrame resampled
        """
        # Mapear timeframe a pandas frequency
        tf_map = {
            'M1': '1min',
            'M5': '5min',
            'M15': '15min',
            'M30': '30min',
            'H1': '1H',
            'H4': '4H',
            'D1': '1D',
        }

        if target_timeframe not in tf_map:
            raise ValueError(f"Invalid target timeframe: {target_timeframe}")

        freq = tf_map[target_timeframe]

        # Resample OHLCV
        resampled = df.resample(freq).agg({
            'open': 'first',
            'high': 'max',
            'low': 'min',
            'close': 'last',
            'volume': 'sum'
        })

        # Eliminar filas con NaN (períodos sin datos)
        resampled.dropna(inplace=True)

        logger.debug(f"Resampled to {target_timeframe}: {len(df)} → {len(resampled)} bars")

        return resampled

    def load_multi_timeframe(self, symbol: str, csv_path: str = None,
                            base_timeframe: str = "M1",
                            target_timeframes: List[str] = None) -> Dict[str, pd.DataFrame]:
        """
        Cargar datos en múltiples timeframes desde una fuente base.

        Args:
            symbol: Símbolo
            csv_path: Ruta CSV (si se usa CSV)
            base_timeframe: Timeframe base de los datos
            target_timeframes: Lista de timeframes objetivo (default: ['M5', 'M15', 'H1', 'H4', 'D1'])

        Returns:
            Dict {timeframe: DataFrame}
        """
        if target_timeframes is None:
            target_timeframes = ['M5', 'M15', 'H1', 'H4', 'D1']

        # Cargar datos base
        if csv_path:
            base_data = self.load_csv(symbol, csv_path, base_timeframe)
        elif symbol in self.data_cache and base_timeframe in self.data_cache[symbol]:
            base_data = self.data_cache[symbol][base_timeframe]
        else:
            raise ValueError(f"No data loaded for {symbol} {base_timeframe}")

        # Resample a cada timeframe objetivo
        multi_tf_data = {base_timeframe: base_data}

        for tf in target_timeframes:
            if tf == base_timeframe:
                continue

            resampled = self.resample_to_timeframe(base_data, tf)
            multi_tf_data[tf] = resampled

            # Guardar en cache
            if symbol not in self.data_cache:
                self.data_cache[symbol] = {}
            self.data_cache[symbol][tf] = resampled

        logger.info(f"Loaded multi-timeframe data for {symbol}: {list(multi_tf_data.keys())}")

        return multi_tf_data

    def _validate_data_quality(self, df: pd.DataFrame, symbol: str) -> pd.DataFrame:
        """
        Validar calidad de datos: gaps, outliers, valores negativos.

        Args:
            df: DataFrame OHLCV
            symbol: Símbolo (para logging)

        Returns:
            DataFrame limpio
        """
        initial_len = len(df)

        # 1. Eliminar duplicados
        df = df[~df.index.duplicated(keep='first')]

        # 2. Eliminar NaN
        df.dropna(inplace=True)

        # 3. Eliminar valores negativos o cero
        df = df[(df['open'] > 0) & (df['high'] > 0) & (df['low'] > 0) &
                (df['close'] > 0) & (df['volume'] >= 0)]

        # 4. Validar OHLC consistency: high >= low, high >= open, high >= close, low <= open, low <= close
        df = df[(df['high'] >= df['low']) &
                (df['high'] >= df['open']) &
                (df['high'] >= df['close']) &
                (df['low'] <= df['open']) &
                (df['low'] <= df['close'])]

        # 5. Detectar outliers (precio > 10x media móvil 100)
        if len(df) > 100:
            ma100 = df['close'].rolling(100).mean()
            outlier_threshold = 10.0
            outliers = (df['close'] > ma100 * outlier_threshold) | (df['close'] < ma100 / outlier_threshold)

            if outliers.sum() > 0:
                logger.warning(f"{symbol}: Removed {outliers.sum()} outlier bars")
                df = df[~outliers]

        removed = initial_len - len(df)
        if removed > 0:
            logger.warning(f"{symbol}: Data quality validation removed {removed}/{initial_len} bars "
                          f"({removed/initial_len*100:.1f}%)")

        return df

    def get_data(self, symbol: str, timeframe: str) -> Optional[pd.DataFrame]:
        """
        Obtener datos desde cache.

        Args:
            symbol: Símbolo
            timeframe: Timeframe

        Returns:
            DataFrame o None si no está en cache
        """
        if symbol in self.data_cache and timeframe in self.data_cache[symbol]:
            return self.data_cache[symbol][timeframe]
        return None

    def save_cache(self, cache_file: str = "backtest_data_cache.pkl"):
        """
        Guardar cache a disco (pickle) para recargas rápidas.

        Args:
            cache_file: Nombre del archivo cache
        """
        cache_path = self.cache_dir / cache_file

        try:
            with open(cache_path, 'wb') as f:
                pickle.dump(self.data_cache, f)

            logger.info(f"Cache saved to {cache_path}")
        except Exception as e:
            logger.error(f"Failed to save cache: {e}")

    def load_cache(self, cache_file: str = "backtest_data_cache.pkl"):
        """
        Cargar cache desde disco.

        Args:
            cache_file: Nombre del archivo cache
        """
        cache_path = self.cache_dir / cache_file

        if not cache_path.exists():
            logger.info(f"No cache file found: {cache_path}")
            return

        try:
            with open(cache_path, 'rb') as f:
                self.data_cache = pickle.load(f)

            symbols = len(self.data_cache)
            total_bars = sum(len(df) for symbol_data in self.data_cache.values()
                           for df in symbol_data.values())

            logger.info(f"Cache loaded from {cache_path}: {symbols} symbols, {total_bars} total bars")
        except Exception as e:
            logger.error(f"Failed to load cache: {e}")

    def get_date_range(self, symbol: str, timeframe: str) -> Optional[tuple]:
        """
        Obtener rango de fechas de datos cargados.

        Args:
            symbol: Símbolo
            timeframe: Timeframe

        Returns:
            (start_date, end_date) o None
        """
        df = self.get_data(symbol, timeframe)
        if df is None or df.empty:
            return None

        return (df.index[0], df.index[-1])
