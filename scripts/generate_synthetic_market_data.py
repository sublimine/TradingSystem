#!/usr/bin/env python3
"""
MANDATO 19 - Synthetic Data Generator (DEMO ONLY)

Genera datos sintéticos REALISTAS para validar pipeline de calibración.

⚠️  ADVERTENCIA: Estos datos son SINTÉTICOS, NO reales.
⚠️  Solo para testing/demo del pipeline.
⚠️  NO usar para decisiones de trading reales.

Uso:
    python scripts/generate_synthetic_market_data.py

Autor: SUBLIMINE Institutional Trading System
Fecha: 2025-11-14
Mandato: MANDATO 19 - BLOQUEADO POR FALTA DE DATOS REALES
"""

import sys
import os
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s'
)
logger = logging.getLogger(__name__)


class SyntheticMarketDataGenerator:
    """
    Generador de datos sintéticos realistas.

    Simula:
    - Movimiento browniano geométrico (GBM)
    - Volatilidad estocástica
    - Microstructure noise
    - Spreads realistas
    - Volumen variable
    """

    def __init__(self, seed: int = 42):
        """
        Args:
            seed: Random seed para reproducibilidad
        """
        self.seed = seed
        np.random.seed(seed)

    def generate_ohlcv(self, symbol: str, start_date: datetime, end_date: datetime,
                       timeframe: str = "M15", base_price: float = 1.0) -> pd.DataFrame:
        """
        Generar datos OHLCV sintéticos realistas.

        Args:
            symbol: Símbolo (ej: EURUSD, XAUUSD)
            start_date: Fecha inicio
            end_date: Fecha fin
            timeframe: Timeframe ('M1', 'M5', 'M15', 'H1', 'H4', 'D1')
            base_price: Precio base inicial

        Returns:
            DataFrame con columnas [open, high, low, close, volume]
        """
        logger.info(f"Generating synthetic data for {symbol} {timeframe}: {start_date} to {end_date}")

        # Mapear timeframe a minutos
        tf_minutes = {
            'M1': 1,
            'M5': 5,
            'M15': 15,
            'M30': 30,
            'H1': 60,
            'H4': 240,
            'D1': 1440
        }

        if timeframe not in tf_minutes:
            raise ValueError(f"Invalid timeframe: {timeframe}")

        minutes = tf_minutes[timeframe]

        # Generar timestamps
        timestamps = pd.date_range(start=start_date, end=end_date, freq=f'{minutes}T')
        n_bars = len(timestamps)

        # Parámetros realistas por tipo de símbolo
        if 'USD' in symbol or 'EUR' in symbol or 'GBP' in symbol:
            # FX
            volatility = 0.10  # 10% anual
            drift = 0.0  # Sin drift neto (FX oscila)
            spread_bps = 0.5
        elif 'XAU' in symbol or 'GOLD' in symbol:
            # Gold
            volatility = 0.15
            drift = 0.02
            spread_bps = 3.0
        elif 'US500' in symbol or 'NAS' in symbol:
            # Índices
            volatility = 0.20
            drift = 0.08
            spread_bps = 2.0
        elif 'BTC' in symbol:
            # Crypto
            volatility = 0.60
            drift = 0.10
            spread_bps = 10.0
        else:
            # Default
            volatility = 0.15
            drift = 0.0
            spread_bps = 1.0

        # Ajustar volatilidad para timeframe (scaling)
        # Volatilidad crece con sqrt(time)
        vol_scaled = volatility * np.sqrt(minutes / (252 * 1440))  # Annualized to bar

        # Generar returns usando GBM (Geometric Brownian Motion)
        dt = minutes / (252 * 1440)  # Fraction of year
        returns = np.random.normal(drift * dt, vol_scaled, n_bars)

        # Generar precios close usando GBM
        prices = np.zeros(n_bars)
        prices[0] = base_price

        for i in range(1, n_bars):
            prices[i] = prices[i-1] * np.exp(returns[i])

        # Generar OHLC desde close
        # High: close + ruido positivo
        # Low: close - ruido positivo
        # Open: close anterior + pequeño gap

        ohlc_noise = vol_scaled * 0.3  # 30% de volatilidad para rangos intrabar

        opens = np.zeros(n_bars)
        highs = np.zeros(n_bars)
        lows = np.zeros(n_bars)
        closes = prices.copy()

        opens[0] = base_price
        for i in range(1, n_bars):
            # Open = close anterior + gap pequeño
            gap = np.random.normal(0, vol_scaled * 0.1) * closes[i-1]
            opens[i] = closes[i-1] + gap

        # High/Low con microstructure noise
        for i in range(n_bars):
            bar_range = abs(np.random.normal(0, ohlc_noise)) * closes[i]

            # High: max(open, close) + extra
            highs[i] = max(opens[i], closes[i]) + abs(np.random.normal(0, bar_range * 0.5))

            # Low: min(open, close) - extra
            lows[i] = min(opens[i], closes[i]) - abs(np.random.normal(0, bar_range * 0.5))

            # Asegurar High >= Low
            if lows[i] > highs[i]:
                lows[i], highs[i] = highs[i], lows[i]

        # Generar volumen (lognormal distribution, realista)
        # Mayor volumen en movimientos grandes
        volume_base = 1000
        price_changes = np.abs(np.diff(closes, prepend=closes[0]))
        price_changes_normalized = price_changes / np.mean(price_changes)

        volumes = np.random.lognormal(mean=np.log(volume_base), sigma=0.5, size=n_bars)
        volumes = volumes * (1 + price_changes_normalized)  # Más volumen en movimientos grandes
        volumes = volumes.astype(int)

        # Crear DataFrame
        df = pd.DataFrame({
            'open': opens,
            'high': highs,
            'low': lows,
            'close': closes,
            'volume': volumes
        }, index=timestamps)

        # Asegurar UTC
        df.index = df.index.tz_localize('UTC')

        logger.info(f"Generated {len(df)} synthetic bars for {symbol}")
        logger.info(f"  Price range: {df['close'].min():.5f} to {df['close'].max():.5f}")
        logger.info(f"  Avg volume: {df['volume'].mean():.0f}")

        return df

    def save_to_csv(self, df: pd.DataFrame, symbol: str, timeframe: str, output_dir: str = "data/historical"):
        """
        Guardar datos sintéticos a CSV.

        Args:
            df: DataFrame OHLCV
            symbol: Símbolo
            timeframe: Timeframe
            output_dir: Directorio de salida
        """
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        filename = f"{symbol}_{timeframe}_SYNTHETIC.csv"
        filepath = output_path / filename

        # Guardar con timestamp column
        df_export = df.copy()
        df_export.index.name = 'timestamp'

        df_export.to_csv(filepath)

        logger.info(f"Saved synthetic data to {filepath}")

        # Crear archivo README para advertir
        readme_path = output_path / "README_SYNTHETIC.txt"
        with open(readme_path, 'w') as f:
            f.write("""
⚠️  ADVERTENCIA: DATOS SINTÉTICOS - NO REALES ⚠️

Los archivos CSV con sufijo '_SYNTHETIC.csv' contienen datos generados
artificialmente para testing del pipeline de calibración.

ESTOS DATOS SON SINTÉTICOS Y NO REFLEJAN MERCADO REAL.

NO usar para:
- Decisiones de trading reales
- Paper trading
- Backtesting de producción

Uso válido:
- Testing de pipeline de calibración
- Validación de scripts
- Desarrollo y debugging

Para ejecutar calibración REAL:
1. Obtener datos históricos reales (MT5 o CSV reales)
2. Colocar en data/historical/ (sin sufijo _SYNTHETIC)
3. Ejecutar run_calibration_sweep.py con datos reales

Generado por: scripts/generate_synthetic_market_data.py
Fecha: 2025-11-14
Mandato: MANDATO 19 - BLOQUEADO POR FALTA DE DATOS REALES
""")

        logger.info(f"Created README warning: {readme_path}")


def main():
    """Generar datos sintéticos para MANDATO 19 demo."""
    logger.info("="*80)
    logger.info("MANDATO 19 - SYNTHETIC DATA GENERATOR (DEMO ONLY)")
    logger.info("="*80)
    logger.info("⚠️  WARNING: Generating SYNTHETIC data for pipeline testing")
    logger.info("⚠️  NOT real market data - DO NOT use for real trading decisions")
    logger.info("="*80)

    generator = SyntheticMarketDataGenerator(seed=42)

    # Períodos según MANDATO 18R config
    calib_start = datetime(2023, 1, 1)
    calib_end = datetime(2024, 6, 30)
    holdout_start = datetime(2024, 7, 1)
    holdout_end = datetime(2024, 12, 31)

    # Combinar para un dataset continuo
    full_start = calib_start
    full_end = holdout_end

    # Símbolos para MANDATO 19 (mínimo 3)
    symbols_config = [
        ('EURUSD.pro', 1.08, 'M15'),
        ('XAUUSD.pro', 2000.0, 'M15'),
        ('US500.pro', 4500.0, 'M15'),
    ]

    for symbol, base_price, timeframe in symbols_config:
        logger.info(f"\nGenerating {symbol} {timeframe}...")

        df = generator.generate_ohlcv(
            symbol=symbol,
            start_date=full_start,
            end_date=full_end,
            timeframe=timeframe,
            base_price=base_price
        )

        generator.save_to_csv(df, symbol, timeframe)

    logger.info("\n" + "="*80)
    logger.info("✅ Synthetic data generation completed")
    logger.info("="*80)
    logger.info(f"Files created in data/historical/")
    logger.info("Files: *_SYNTHETIC.csv (NOT REAL DATA)")
    logger.info("\nNext steps:")
    logger.info("1. Review README_SYNTHETIC.txt")
    logger.info("2. Run calibration pipeline with synthetic data (DEMO only)")
    logger.info("3. Replace with REAL data when available")
    logger.info("="*80)


if __name__ == '__main__':
    main()
