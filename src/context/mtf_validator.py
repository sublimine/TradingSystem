"""
MTF Context Validator - Medium Timeframe Context Validation

Valida contexto táctico en M15/M5:
- Swing structure alineada con HTF
- Zonas de supply/demand (POIs - Points of Interest)
- Validación de entry zones

MTF valida que la zona operativa sea consistente con HTF bias.
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Optional
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class MTFContextValidator:
    """
    Valida contexto en timeframes medios (M15, M5).

    Verifica:
    - Alineación de swings con HTF
    - Identificación de POIs (order blocks, FVGs, demand/supply zones)
    - Validez de zona de entrada
    """

    def __init__(self, config: Dict):
        """
        Inicializar validador MTF.

        Args:
            config: {
                'poi_lookback': int - Velas para detectar POIs (default: 20),
                'min_poi_size': float - Tamaño mínimo de POI en pips (default: 5),
                'confluence_threshold': float - Threshold para confluencia (default: 0.5)
            }
        """
        self.poi_lookback = config.get('poi_lookback', 20)
        self.min_poi_size = config.get('min_poi_size', 5)
        self.confluence_threshold = config.get('confluence_threshold', 0.5)

        # Cache de POIs por símbolo
        self.poi_cache = {}

        logger.info(f"MTFContextValidator initialized: poi_lookback={self.poi_lookback}")

    def validate_context(self, symbol: str, ohlcv: pd.DataFrame,
                        htf_bias: int, current_price: float) -> Dict:
        """
        Valida contexto MTF contra HTF bias.

        Args:
            symbol: Símbolo
            ohlcv: DataFrame MTF (M15 o M5)
            htf_bias: 1 (bullish), -1 (bearish), 0 (range)
            current_price: Precio actual

        Returns:
            {
                'mtf_alignment': float [0-1],  # Alineación con HTF
                'pois': List[Dict],  # POIs identificados
                'nearest_poi': Dict,  # POI más cercano
                'poi_distance_normalized': float,  # Distancia normalizada al POI
                'context_valid': bool  # ¿Contexto válido para operar?
            }
        """
        if len(ohlcv) < 30:
            logger.warning(f"{symbol}: Insufficient MTF data ({len(ohlcv)} bars)")
            return self._default_context()

        # 1. Detectar POIs (order blocks / zonas clave)
        pois = self._detect_pois(ohlcv, htf_bias)

        # 2. Encontrar POI más cercano
        nearest_poi = self._find_nearest_poi(pois, current_price)

        # 3. Calcular alineación MTF con HTF
        mtf_alignment = self._calculate_alignment(ohlcv, htf_bias)

        # 4. Calcular distancia normalizada al POI
        poi_distance_normalized = 0.5
        if nearest_poi:
            poi_size = abs(nearest_poi['high'] - nearest_poi['low'])
            distance = abs(current_price - nearest_poi['price'])
            poi_distance_normalized = min(distance / (poi_size + 1e-8), 1.0)

        # 5. Validar contexto
        context_valid = (
            mtf_alignment >= self.confluence_threshold and
            poi_distance_normalized <= 0.5  # Cerca de POI
        )

        context = {
            'mtf_alignment': round(mtf_alignment, 4),
            'pois': pois,
            'nearest_poi': nearest_poi,
            'poi_distance_normalized': round(poi_distance_normalized, 4),
            'context_valid': context_valid
        }

        self.poi_cache[symbol] = context
        return context

    def _detect_pois(self, ohlcv: pd.DataFrame, htf_bias: int) -> List[Dict]:
        """
        Detecta POIs (order blocks, demand/supply zones).

        POI = Vela con:
        - Movimiento fuerte (body > 50% del rango)
        - Seguida de reacción en dirección opuesta
        - Alineada con HTF bias

        Returns:
            Lista de POIs [{type, price, high, low, timestamp}, ...]
        """
        pois = []
        n = len(ohlcv)

        for i in range(self.poi_lookback, n - 2):
            open_price = ohlcv['open'].iloc[i]
            close_price = ohlcv['close'].iloc[i]
            high = ohlcv['high'].iloc[i]
            low = ohlcv['low'].iloc[i]

            body = abs(close_price - open_price)
            full_range = high - low

            # Vela con body fuerte
            if full_range > 0 and body / full_range > 0.5:
                # Bullish order block (para compras)
                if close_price > open_price and (htf_bias >= 0):
                    pois.append({
                        'type': 'DEMAND',
                        'price': (open_price + low) / 2,  # Mitad del bloque
                        'high': close_price,
                        'low': low,
                        'timestamp': ohlcv.index[i]
                    })

                # Bearish order block (para ventas)
                elif close_price < open_price and (htf_bias <= 0):
                    pois.append({
                        'type': 'SUPPLY',
                        'price': (open_price + high) / 2,
                        'high': high,
                        'low': close_price,
                        'timestamp': ohlcv.index[i]
                    })

        # Retornar últimos N POIs
        return pois[-10:] if pois else []

    def _find_nearest_poi(self, pois: List[Dict], current_price: float) -> Optional[Dict]:
        """Encuentra POI más cercano al precio actual."""
        if not pois:
            return None

        nearest = min(pois, key=lambda poi: abs(poi['price'] - current_price))
        return nearest

    def _calculate_alignment(self, ohlcv: pd.DataFrame, htf_bias: int) -> float:
        """
        Calcula alineación de MTF con HTF bias.

        Verifica si swings recientes en MTF son consistentes con HTF.

        Returns:
            Alignment score [0-1]
        """
        if htf_bias == 0:
            return 0.5  # Neutral en rango

        recent_bars = ohlcv.tail(10)
        closes = recent_bars['close'].values

        # Tendencia MTF (simple: pendiente de closes)
        if len(closes) >= 5:
            x = np.arange(len(closes))
            slope = np.polyfit(x, closes, 1)[0]

            # Normalizar slope a [0-1]
            slope_normalized = np.tanh(slope * 100)  # Escalar para sensibilidad

            # Si HTF bullish y MTF slope positiva → alta alineación
            # Si HTF bearish y MTF slope negativa → alta alineación
            if htf_bias == 1:
                alignment = (slope_normalized + 1) / 2  # Mapear [-1,1] a [0,1]
            elif htf_bias == -1:
                alignment = (1 - slope_normalized) / 2  # Invertir para bearish
            else:
                alignment = 0.5

            return np.clip(alignment, 0.0, 1.0)

        return 0.5

    def get_nearest_poi_distance(self, symbol: str, current_price: float) -> float:
        """
        Obtiene distancia normalizada al POI más cercano.

        Returns:
            Distancia [0-1], 0 = en POI, 1 = muy lejos
        """
        if symbol not in self.poi_cache:
            return 0.5

        return self.poi_cache[symbol].get('poi_distance_normalized', 0.5)

    def _default_context(self) -> Dict:
        """Contexto por defecto cuando no hay datos."""
        return {
            'mtf_alignment': 0.5,
            'pois': [],
            'nearest_poi': None,
            'poi_distance_normalized': 0.5,
            'context_valid': False
        }
