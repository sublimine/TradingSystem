"""
MicrostructureEngine - MANDATO 24

Motor centralizado de cálculo de features de microestructura.

Responsibilities:
- Calcular OFI (Order Flow Imbalance)
- Calcular CVD (Cumulative Volume Delta)
- Calcular VPIN (Volume-Synchronized Probability of Informed Trading)
- Parsear L2 orderbook (si disponible)
- Mantener estado (VPIN buckets, CVD acumulado)
- Proveer features consistentes a todas las estrategias

Author: SUBLIMINE Institutional Trading System
Date: 2025-11-15
Version: 1.0
"""

import logging
from typing import Dict, Optional
import pandas as pd
from dataclasses import dataclass, field

# Import existing feature calculation functions
try:
    from src.features.order_flow import (
        VPINCalculator,
        calculate_ofi,
        calculate_signed_volume
    )
    HAS_ORDER_FLOW = True
except ImportError:
    HAS_ORDER_FLOW = False

try:
    from src.features.orderbook_l2 import (
        OrderBookSnapshot,
        parse_l2_snapshot
    )
    HAS_L2 = True
except ImportError:
    HAS_L2 = False

logger = logging.getLogger(__name__)


@dataclass
class MicrostructureFeatures:
    """
    Container para features de microestructura de un símbolo.

    Attributes:
        ofi: Order Flow Imbalance (-inf to +inf, typical range -10 to +10)
        cvd: Cumulative Volume Delta (running sum)
        vpin: VPIN (0 to 1, probability of informed trading)
        atr: Average True Range (para referencia, NO sizing)
        l2_snapshot: Level 2 orderbook snapshot (si disponible)
        imbalance: Bid/Ask volume imbalance (-1 to +1)
        spread: Spread en pips/points
        microprice: Volume-weighted mid price
    """
    ofi: float = 0.0
    cvd: float = 0.0
    vpin: float = 0.5  # Neutral default
    atr: float = 0.0001  # Small default
    l2_snapshot: Optional[object] = None  # OrderBookSnapshot
    imbalance: float = 0.0
    spread: float = 0.0
    microprice: float = 0.0


class MicrostructureEngine:
    """
    Motor centralizado de cálculo de features de microestructura.

    Mantiene estado por símbolo (VPIN buckets, CVD accumulator) y calcula
    todas las features necesarias para estrategias institucionales.

    Usage:
        engine = MicrostructureEngine(config)
        features = engine.calculate_features(symbol, market_data, l2_data)
        features_dict = engine.get_features_dict(features)

    Example:
        >>> engine = MicrostructureEngine({'features': {'ofi_lookback': 20}})
        >>> df = pd.DataFrame({'close': [...], 'volume': [...]})
        >>> features = engine.calculate_features('EURUSD', df)
        >>> print(f"VPIN: {features.vpin}, OFI: {features.ofi}")
    """

    def __init__(self, config: Dict):
        """
        Inicializa MicrostructureEngine.

        Args:
            config: System config dict con parámetros:
                - features.ofi_lookback: Lookback window para OFI (default 20)
                - features.vpin.bucket_size: VPIN bucket size (default 50000)
                - features.vpin.num_buckets: Número de buckets VPIN (default 50)
        """
        self.config = config

        # VPIN calculators (uno por símbolo)
        self.vpin_calculators: Dict[str, object] = {}  # VPINCalculator instances

        # CVD accumulators (running sum por símbolo)
        self.cvd_accumulators: Dict[str, float] = {}

        # OFI lookback window (default 20 bars)
        features_config = config.get('features', {})
        self.ofi_lookback = features_config.get('ofi_lookback', 20)

        # VPIN config
        vpin_config = features_config.get('vpin', {})
        self.vpin_bucket_size = vpin_config.get('bucket_size', 50000)
        self.vpin_num_buckets = vpin_config.get('num_buckets', 50)

        # Track if external modules available
        self.has_order_flow = HAS_ORDER_FLOW
        self.has_l2 = HAS_L2

        logger.info(
            f"MicrostructureEngine initialized "
            f"(OFI lookback={self.ofi_lookback}, "
            f"VPIN buckets={self.vpin_num_buckets}, "
            f"order_flow={self.has_order_flow}, L2={self.has_l2})"
        )

    def calculate_features(
        self,
        symbol: str,
        market_data: pd.DataFrame,
        l2_data: Optional[any] = None
    ) -> MicrostructureFeatures:
        """
        Calcula TODAS las features de microestructura para un símbolo.

        Args:
            symbol: Symbol to calculate features for (e.g. 'EURUSD')
            market_data: OHLCV DataFrame (debe tener al menos 2 rows)
                Required columns: open, high, low, close, volume
            l2_data: Level 2 orderbook data (optional, from MT5's market_book_get)

        Returns:
            MicrostructureFeatures con todas las features calculadas

        Note:
            Si data insuficiente o módulos no disponibles, retorna defaults.
        """
        features = MicrostructureFeatures()

        # Validar data
        if market_data is None or market_data.empty:
            logger.warning(f"{symbol}: No market data, returning defaults")
            return features

        if len(market_data) < 2:
            logger.debug(f"{symbol}: Insufficient data ({len(market_data)} bars)")
            return features

        # === OFI (Order Flow Imbalance) ===
        if self.has_order_flow:
            features.ofi = self._calculate_ofi(symbol, market_data)

        # === CVD (Cumulative Volume Delta) ===
        if self.has_order_flow:
            features.cvd = self._calculate_cvd(symbol, market_data)

        # === VPIN ===
        if self.has_order_flow:
            features.vpin = self._calculate_vpin(symbol, market_data)

        # === ATR (para referencia solamente, NO sizing) ===
        features.atr = self._calculate_atr(market_data)

        # === L2 Snapshot (si disponible) ===
        if l2_data is not None and self.has_l2:
            l2_snapshot = parse_l2_snapshot(l2_data)
            if l2_snapshot:
                features.l2_snapshot = l2_snapshot
                features.imbalance = l2_snapshot.imbalance
                features.spread = l2_snapshot.spread
                # Microprice: volume-weighted mid
                # For simplicity, use mid_price (could enhance)
                features.microprice = l2_snapshot.mid_price

        return features

    def _calculate_ofi(self, symbol: str, market_data: pd.DataFrame) -> float:
        """
        Calcula Order Flow Imbalance.

        OFI mide presión neta de compra/venta en el mercado.

        Args:
            symbol: Symbol name
            market_data: OHLCV DataFrame

        Returns:
            OFI value (típicamente -10 a +10, pero sin bound)
        """
        try:
            # Get lookback window
            lookback_data = market_data.tail(self.ofi_lookback)

            if len(lookback_data) < 2:
                return 0.0

            # Calculate OFI
            ofi = calculate_ofi(
                lookback_data['close'],
                lookback_data['volume']
            )

            return float(ofi) if ofi is not None else 0.0

        except Exception as e:
            logger.debug(f"{symbol}: OFI calculation error: {e}")
            return 0.0

    def _calculate_cvd(self, symbol: str, market_data: pd.DataFrame) -> float:
        """
        Calcula Cumulative Volume Delta.

        CVD = running sum of signed volume (buy volume - sell volume).
        Mantiene estado en self.cvd_accumulators.

        Args:
            symbol: Symbol name
            market_data: OHLCV DataFrame

        Returns:
            CVD value (running sum desde inicio del engine)
        """
        try:
            # Initialize accumulator if first time
            if symbol not in self.cvd_accumulators:
                self.cvd_accumulators[symbol] = 0.0

            # Get latest bar
            latest_bar = market_data.iloc[-1]

            # Get previous close (for signed volume)
            if len(market_data) >= 2:
                prev_close = market_data.iloc[-2]['close']
            else:
                # First bar, assume neutral
                return self.cvd_accumulators[symbol]

            # Calculate signed volume
            signed_vol = calculate_signed_volume(
                latest_bar['close'],
                prev_close,
                latest_bar['volume']
            )

            # Accumulate
            self.cvd_accumulators[symbol] += signed_vol

            return self.cvd_accumulators[symbol]

        except Exception as e:
            logger.debug(f"{symbol}: CVD calculation error: {e}")
            return self.cvd_accumulators.get(symbol, 0.0)

    def _calculate_vpin(self, symbol: str, market_data: pd.DataFrame) -> float:
        """
        Calcula VPIN (Volume-Synchronized Probability of Informed Trading).

        VPIN usa bucket-based accumulation de volume para detectar toxicidad.
        Valores altos (>0.75) indican alta probabilidad de informed trading.

        Args:
            symbol: Symbol name
            market_data: OHLCV DataFrame

        Returns:
            VPIN value (0 to 1)
        """
        try:
            # Initialize VPIN calculator if first time
            if symbol not in self.vpin_calculators:
                self.vpin_calculators[symbol] = VPINCalculator(
                    bucket_size=self.vpin_bucket_size,
                    num_buckets=self.vpin_num_buckets
                )

            calculator = self.vpin_calculators[symbol]

            # Get latest bar
            latest_bar = market_data.iloc[-1]

            # Get previous close
            if len(market_data) >= 2:
                prev_close = market_data.iloc[-2]['close']
            else:
                return 0.5  # Neutral default

            # Calculate trade direction
            signed_vol = calculate_signed_volume(
                latest_bar['close'],
                prev_close,
                latest_bar['volume']
            )

            trade_direction = 1 if signed_vol > 0 else -1 if signed_vol < 0 else 0

            # Add trade to VPIN calculator
            vpin_value = calculator.add_trade(
                latest_bar['volume'],
                trade_direction
            )

            # Return latest VPIN (or 0.5 if bucket not filled yet)
            if vpin_value is not None:
                return float(vpin_value)
            else:
                return 0.5

        except Exception as e:
            logger.debug(f"{symbol}: VPIN calculation error: {e}")
            return 0.5

    def _calculate_atr(
        self,
        market_data: pd.DataFrame,
        period: int = 14
    ) -> float:
        """
        Calcula ATR (Average True Range).

        NOTA: Solo para referencia/features. NO se usa para position sizing
        (NON-NEGOTIABLE: sizing es % fijo de capital).

        Args:
            market_data: OHLCV DataFrame
            period: ATR period (default 14)

        Returns:
            ATR value (en price units)
        """
        try:
            if len(market_data) < period:
                return 0.0001  # Default pequeño

            # Calculate True Range
            high = market_data['high']
            low = market_data['low']
            close_prev = market_data['close'].shift(1)

            tr1 = high - low
            tr2 = abs(high - close_prev)
            tr3 = abs(low - close_prev)

            tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)

            # ATR = SMA(TR, period)
            atr = tr.rolling(window=period).mean().iloc[-1]

            return float(atr) if not pd.isna(atr) else 0.0001

        except Exception as e:
            logger.debug(f"ATR calculation error: {e}")
            return 0.0001

    def get_features_dict(self, features: MicrostructureFeatures) -> Dict:
        """
        Convierte MicrostructureFeatures a dict para pasar a estrategias.

        Args:
            features: MicrostructureFeatures instance

        Returns:
            Dict con keys: ofi, cvd, vpin, atr, l2_snapshot, imbalance, spread, microprice

        Example:
            >>> features = engine.calculate_features('EURUSD', df)
            >>> features_dict = engine.get_features_dict(features)
            >>> print(features_dict['vpin'])
            0.78
        """
        return {
            'ofi': features.ofi,
            'cvd': features.cvd,
            'vpin': features.vpin,
            'atr': features.atr,
            'l2_snapshot': features.l2_snapshot,
            'imbalance': features.imbalance,
            'spread': features.spread,
            'microprice': features.microprice
        }

    def reset_symbol(self, symbol: str):
        """
        Reset state para un símbolo (útil para testing o re-inicialización).

        Borra VPIN calculator y CVD accumulator para el símbolo.

        Args:
            symbol: Symbol to reset
        """
        if symbol in self.vpin_calculators:
            del self.vpin_calculators[symbol]

        if symbol in self.cvd_accumulators:
            del self.cvd_accumulators[symbol]

        logger.debug(f"Reset microstructure state for {symbol}")

    def reset_all(self):
        """
        Reset TODOS los símbolos (útil para iniciar nueva sesión).
        """
        self.vpin_calculators.clear()
        self.cvd_accumulators.clear()

        logger.info("Reset all microstructure state")

    def get_symbols(self) -> list:
        """
        Retorna lista de símbolos con estado activo.

        Returns:
            Lista de símbolos que tienen calculators o accumulators activos
        """
        symbols = set()
        symbols.update(self.vpin_calculators.keys())
        symbols.update(self.cvd_accumulators.keys())

        return sorted(list(symbols))

    def get_status(self, symbol: str) -> Dict:
        """
        Retorna status/debug info para un símbolo.

        Args:
            symbol: Symbol name

        Returns:
            Dict con status info
        """
        return {
            'symbol': symbol,
            'has_vpin_calculator': symbol in self.vpin_calculators,
            'has_cvd_accumulator': symbol in self.cvd_accumulators,
            'cvd_value': self.cvd_accumulators.get(symbol, 0.0),
            'order_flow_available': self.has_order_flow,
            'l2_available': self.has_l2
        }
