"""
MANDATO 20 - MT5 Data Client Institucional

Cliente para descarga de históricos REALES desde MetaTrader 5.

Features:
- Reutiliza MT5Connector existente (reconexión automática)
- Descarga OHLCV con validación institucional
- Manejo de errores robusto
- Logging detallado
- NO guarda credenciales en código

NON-NEGOTIABLES:
- Credenciales SOLO desde ENV vars o config externo
- TODO etiquetado como REAL (no sintético)
- Validación de datos (NaNs, outliers, gaps)
- Backward compatible (no romper nada existente)

Autor: SUBLIMINE Institutional Trading System
Fecha: 2025-11-14
Mandato: MANDATO 20
"""

import os
import logging
from datetime import datetime, timedelta
from typing import Dict, Optional, Tuple
from pathlib import Path

import pandas as pd
import numpy as np

try:
    import MetaTrader5 as mt5
    MT5_AVAILABLE = True
except ModuleNotFoundError:
    MT5_AVAILABLE = False
    mt5 = None

# Reutilizar MT5Connector existente (MANDATO anterior)
from src.mt5_connector import MT5Connector

logger = logging.getLogger(__name__)


class MT5DataClient:
    """
    Cliente institucional para descarga de históricos desde MT5.

    Reutiliza MT5Connector existente + agrega funcionalidad de descarga.
    """

    def __init__(self, connector: Optional[MT5Connector] = None):
        """
        Args:
            connector: Instancia de MT5Connector (opcional, se crea si no se provee)
        """
        if not MT5_AVAILABLE:
            logger.critical("MANDATO 20 - MT5 NOT AVAILABLE: MetaTrader5 module not installed")
            logger.critical("Install with: pip install MetaTrader5")
            logger.critical("This client will NOT work until MT5 is available")
            self.available = False
            return

        self.available = True
        self.connector = connector if connector else MT5Connector()

        # Mapeo timeframe string → MT5 constant
        self.timeframe_map = {
            'M1': mt5.TIMEFRAME_M1,
            'M5': mt5.TIMEFRAME_M5,
            'M15': mt5.TIMEFRAME_M15,
            'M30': mt5.TIMEFRAME_M30,
            'H1': mt5.TIMEFRAME_H1,
            'H4': mt5.TIMEFRAME_H4,
            'D1': mt5.TIMEFRAME_D1,
            'W1': mt5.TIMEFRAME_W1,
            'MN1': mt5.TIMEFRAME_MN1,
        }

        logger.info("MT5DataClient initialized (REAL data mode)")

    def check_connection(self) -> bool:
        """
        Verificar si hay conexión activa a MT5.

        Returns:
            True si conectado, False si no
        """
        if not self.available:
            logger.error("MT5 not available - cannot check connection")
            return False

        logger.info("Checking MT5 connection...")

        if self.connector.ensure_connected():
            account = mt5.account_info()
            if account:
                logger.info(f"✅ MT5 connected: {account.server} | Login: {account.login}")
                logger.info(f"   Balance: {account.balance} {account.currency}")
                logger.info(f"   Leverage: 1:{account.leverage}")
                return True

        logger.error("❌ MT5 connection failed")
        return False

    def download_ohlcv(self, symbol: str, timeframe: str,
                       start_date: datetime, end_date: datetime) -> pd.DataFrame:
        """
        Descargar datos OHLCV REALES desde MT5.

        Args:
            symbol: Símbolo MT5 (ej: 'EURUSD', 'XAUUSD', 'US500')
            timeframe: Timeframe ('M1', 'M5', 'M15', 'H1', 'H4', 'D1')
            start_date: Fecha inicio (datetime)
            end_date: Fecha fin (datetime)

        Returns:
            DataFrame con columnas [open, high, low, close, volume] + DatetimeIndex UTC

        Raises:
            RuntimeError: Si MT5 no disponible o error en descarga
            ValueError: Si timeframe inválido o símbolo no existe
        """
        if not self.available:
            raise RuntimeError("MT5 not available - cannot download data")

        if timeframe not in self.timeframe_map:
            raise ValueError(f"Invalid timeframe: {timeframe}. Valid: {list(self.timeframe_map.keys())}")

        logger.info(f"Downloading REAL data: {symbol} {timeframe} from {start_date} to {end_date}")

        # Asegurar conexión
        if not self.connector.ensure_connected():
            raise RuntimeError("Failed to connect to MT5")

        # Obtener datos
        mt5_timeframe = self.timeframe_map[timeframe]

        try:
            rates = mt5.copy_rates_range(symbol, mt5_timeframe, start_date, end_date)
        except Exception as e:
            raise RuntimeError(f"MT5 copy_rates_range failed: {e}")

        if rates is None or len(rates) == 0:
            # Verificar si el símbolo existe
            symbol_info = mt5.symbol_info(symbol)
            if symbol_info is None:
                raise ValueError(f"Symbol '{symbol}' does not exist on MT5 server")

            raise RuntimeError(f"No data returned from MT5 for {symbol} {timeframe} (dates may be invalid)")

        # Convertir a DataFrame
        df = pd.DataFrame(rates)

        # Convertir timestamp
        df['time'] = pd.to_datetime(df['time'], unit='s')
        df.set_index('time', inplace=True)
        df.index = df.index.tz_localize('UTC')

        # Renombrar columnas a formato estándar
        df.rename(columns={'tick_volume': 'volume'}, inplace=True)

        # Seleccionar solo OHLCV
        df = df[['open', 'high', 'low', 'close', 'volume']].copy()

        # Validar datos
        df = self._validate_data(df, symbol, timeframe)

        logger.info(f"✅ Downloaded {len(df)} REAL bars for {symbol} {timeframe}")
        logger.info(f"   Date range: {df.index[0]} to {df.index[-1]}")
        logger.info(f"   Price range: {df['close'].min():.5f} to {df['close'].max():.5f}")

        return df

    def _validate_data(self, df: pd.DataFrame, symbol: str, timeframe: str) -> pd.DataFrame:
        """
        Validar calidad de datos OHLCV.

        Checks:
        - NaNs
        - High >= Low
        - Open/Close entre High/Low
        - Volume >= 0
        - Outliers extremos

        Args:
            df: DataFrame OHLCV
            symbol: Símbolo (para logging)
            timeframe: Timeframe (para logging)

        Returns:
            DataFrame validado (con filas problemáticas removidas o corregidas)
        """
        logger.info(f"Validating data quality for {symbol} {timeframe}...")

        initial_len = len(df)

        # Check 1: NaNs
        nans_before = df.isnull().sum().sum()
        if nans_before > 0:
            logger.warning(f"  Found {nans_before} NaN values - dropping rows with NaNs")
            df = df.dropna()

        # Check 2: High >= Low
        invalid_hl = df[df['high'] < df['low']]
        if len(invalid_hl) > 0:
            logger.warning(f"  Found {len(invalid_hl)} bars where High < Low - correcting")
            # Swap high/low
            mask = df['high'] < df['low']
            df.loc[mask, ['high', 'low']] = df.loc[mask, ['low', 'high']].values

        # Check 3: Open/Close entre High/Low
        invalid_oc = df[(df['open'] > df['high']) | (df['open'] < df['low']) |
                        (df['close'] > df['high']) | (df['close'] < df['low'])]
        if len(invalid_oc) > 0:
            logger.warning(f"  Found {len(invalid_oc)} bars with Open/Close outside High/Low range")
            logger.warning(f"  Dropping these {len(invalid_oc)} invalid bars")
            df = df.drop(invalid_oc.index)

        # Check 4: Volume >= 0
        negative_vol = df[df['volume'] < 0]
        if len(negative_vol) > 0:
            logger.warning(f"  Found {len(negative_vol)} bars with negative volume - setting to 0")
            df.loc[df['volume'] < 0, 'volume'] = 0

        # Check 5: Outliers extremos (precio cambia >50% en una barra)
        price_change_pct = df['close'].pct_change().abs()
        outliers = df[price_change_pct > 0.50]
        if len(outliers) > 0:
            logger.warning(f"  Found {len(outliers)} potential outlier bars (>50% price change)")
            logger.warning(f"  Review manually - NOT auto-removing (could be real flash crash)")

        # Check 6: Gaps en datos (detectar si faltan barras)
        expected_bars = self._estimate_expected_bars(df.index[0], df.index[-1], timeframe)
        actual_bars = len(df)
        missing_pct = (expected_bars - actual_bars) / expected_bars * 100 if expected_bars > 0 else 0

        if missing_pct > 10:
            logger.warning(f"  Data appears incomplete: expected ~{expected_bars} bars, got {actual_bars}")
            logger.warning(f"  Missing ~{missing_pct:.1f}% of data (weekends/holidays may account for some)")

        final_len = len(df)
        removed = initial_len - final_len

        if removed > 0:
            logger.warning(f"  Validation removed {removed} invalid bars ({removed/initial_len*100:.2f}%)")
        else:
            logger.info(f"  ✅ Data quality OK - no issues found")

        return df

    def _estimate_expected_bars(self, start: pd.Timestamp, end: pd.Timestamp, timeframe: str) -> int:
        """Estimar número esperado de barras (aprox, sin contar weekends exactos)."""
        tf_minutes = {
            'M1': 1, 'M5': 5, 'M15': 15, 'M30': 30,
            'H1': 60, 'H4': 240, 'D1': 1440, 'W1': 10080, 'MN1': 43200
        }

        if timeframe not in tf_minutes:
            return 0

        total_minutes = (end - start).total_seconds() / 60
        bars_per_minute = 1 / tf_minutes[timeframe]

        # Rough estimate (incluye weekends, holidays - no perfecto)
        estimated = int(total_minutes * bars_per_minute)

        # Factor weekends (aprox 5/7 de semana es trading para FX, menos para índices)
        estimated = int(estimated * 0.7)  # Conservative

        return estimated

    def save_to_csv(self, df: pd.DataFrame, symbol: str, timeframe: str,
                    output_dir: str = "data/historical/REAL") -> Path:
        """
        Guardar datos REALES a CSV con naming institucional.

        Args:
            df: DataFrame OHLCV
            symbol: Símbolo
            timeframe: Timeframe
            output_dir: Directorio de salida

        Returns:
            Path al archivo CSV creado
        """
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        # Naming institucional: REAL_{SYMBOL}_{TF}.csv
        filename = f"REAL_{symbol}_{timeframe}.csv"
        filepath = output_path / filename

        # Exportar con timestamp column
        df_export = df.copy()
        df_export.index.name = 'timestamp'

        df_export.to_csv(filepath)

        logger.info(f"✅ Saved REAL data to: {filepath}")
        logger.info(f"   {len(df)} bars, {df.index[0]} to {df.index[-1]}")

        return filepath

    def disconnect(self):
        """Desconectar de MT5 limpiamente."""
        if self.available and self.connector:
            self.connector.disconnect()
            logger.info("MT5 disconnected")
