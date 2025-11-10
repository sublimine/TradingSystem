"""
Spread Monitor - Transaction Cost Surveillance

Monitorea el spread efectivo en tiempo real para detectar condiciones
de mercado donde los costos de transacción son prohibitivos.

El spread es el termómetro del mercado:
- Spread normal: Mercado líquido, tradeable
- Spread 2-3x normal: Caution, costos elevados
- Spread 5x+ normal: Halt, mercado ilíquido o en stress

Durante eventos extremos (NFP, flash crash), el spread puede explotar
a 10-20x su nivel normal, haciendo que cualquier trade sea ruinoso.

Referencias:
- Roll, R. (1984): "A Simple Implicit Measure of the Effective Bid-Ask Spread"
- Stoll, H. (1989): "Inferring the Components of the Bid-Ask Spread"
- Glosten & Harris (1988): "Estimating the Components of the Bid-Ask Spread"

Author: Sistema de Trading Institucional
Date: 2025-11-06
Version: 1.0
"""

import numpy as np
import pandas as pd
from typing import Optional, Dict, Tuple
from collections import deque
import logging


class SpreadMonitor:
    """
    Monitor de spread efectivo con detección de anomalías.
    
    Trackea el spread en tiempo real y detecta cuando se amplía
    desproporcionadamente, indicando stress de liquidez.
    
    El spread efectivo se calcula como:
    Effective Spread = 2 * |Trade Price - Mid Price|
    
    En FX, spread típico es 0.5-2 pips en condiciones normales.
    Durante stress, puede llegar a 10+ pips.
    """
    
    def __init__(self,
                 window_size: int = 100,
                 historical_window: int = 1000):
        """
        Inicializa el monitor de spread.
        
        Args:
            window_size: Ventana para calcular spread promedio (default: 100)
            historical_window: Ventana para estadísticas históricas (default: 1000)
        """
        self.window_size = window_size
        self.historical_window = historical_window
        
        # Buffer de spreads observados
        self.spreads = deque(maxlen=window_size)
        
        # Historia de spreads para estadísticas
        self.spread_history = deque(maxlen=historical_window)
        
        # Spread actual
        self.current_spread = None
        
        self.logger = logging.getLogger(self.__class__.__name__)
        
        self.logger.info(
            f"Spread Monitor inicializado: "
            f"window={window_size}, historical={historical_window}"
        )
    
    def calculate_quoted_spread(self,
                                bid: float,
                                ask: float,
                                mid: float) -> float:
        """
        Calcula quoted spread (spread del libro).
        
        Args:
            bid: Precio bid
            ask: Precio ask
            mid: Mid price
            
        Returns:
            Quoted spread en basis points
        """
        spread = ask - bid
        spread_bp = (spread / mid) * 10000
        return spread_bp
    
    def calculate_effective_spread(self,
                                   trade_price: float,
                                   mid_price: float,
                                   direction: int) -> float:
        """
        Calcula effective spread (costo real de transacción).
        
        Effective Spread = 2 * |Trade Price - Mid Price|
        
        Multiplicamos por 2 porque el spread es el costo round-trip
        (comprar y vender).
        
        Args:
            trade_price: Precio de la transacción
            mid_price: Mid price en momento de transacción
            direction: +1 para compra, -1 para venta
            
        Returns:
            Effective spread en basis points
        """
        # Para compra: trade_price debería estar en/sobre mid
        # Para venta: trade_price debería estar en/bajo mid
        deviation = abs(trade_price - mid_price)
        effective_spread = 2 * deviation
        
        # Convertir a basis points
        spread_bp = (effective_spread / mid_price) * 10000
        
        return spread_bp
    
    def update_quoted(self,
                     bid: float,
                     ask: float) -> None:
        """
        Actualiza monitor con quoted spread del libro.
        
        Args:
            bid: Precio bid actual
            ask: Precio ask actual
        """
        mid = (bid + ask) / 2
        spread_bp = self.calculate_quoted_spread(bid, ask, mid)
        
        self.spreads.append(spread_bp)
        self.spread_history.append(spread_bp)
        self.current_spread = spread_bp
        
        self.logger.debug(f"Quoted spread actualizado: {spread_bp:.2f} bp")
    
    def update_effective(self,
                        trade_price: float,
                        mid_price: float,
                        direction: int) -> None:
        """
        Actualiza monitor con effective spread observado.
        
        Args:
            trade_price: Precio de transacción
            mid_price: Mid price en ese momento
            direction: Dirección del trade (+1 compra, -1 venta)
        """
        spread_bp = self.calculate_effective_spread(
            trade_price, mid_price, direction
        )
        
        self.spreads.append(spread_bp)
        self.spread_history.append(spread_bp)
        self.current_spread = spread_bp
        
        self.logger.debug(f"Effective spread actualizado: {spread_bp:.2f} bp")
    
    def get_current_spread(self) -> Optional[float]:
        """
        Retorna el spread actual.
        
        Returns:
            Spread actual en basis points, o None si no hay datos
        """
        return self.current_spread
    
    def get_mean_spread(self) -> Optional[float]:
        """
        Retorna el spread promedio en ventana actual.
        
        Returns:
            Spread promedio en basis points, o None si no hay suficientes datos
        """
        if len(self.spreads) < 10:
            return None
        
        return np.mean(self.spreads)
    
    def get_median_spread(self) -> Optional[float]:
        """
        Retorna la mediana del spread en ventana actual.
        
        La mediana es más robusta a outliers que la media.
        
        Returns:
            Mediana del spread en basis points
        """
        if len(self.spreads) < 10:
            return None
        
        return np.median(self.spreads)
    
    def get_spread_std(self) -> Optional[float]:
        """
        Retorna la desviación estándar del spread.
        
        Returns:
            Desviación estándar en basis points
        """
        if len(self.spreads) < 10:
            return None
        
        return np.std(self.spreads)
    
    def get_spread_ratio(self) -> Optional[float]:
        """
        Retorna el ratio del spread actual sobre la mediana histórica.
        
        Este ratio es la métrica clave para decisiones:
        - Ratio < 1.0: Spread comprimido (bueno)
        - Ratio ~ 1.0: Spread normal
        - Ratio 2-3x: Spread elevado (caution)
        - Ratio 5x+: Spread crítico (halt)
        
        Returns:
            Current_spread / Median_spread, o None si no hay datos
        """
        if self.current_spread is None:
            return None
        
        median = self.get_median_spread()
        
        if median is None or median == 0:
            return None
        
        return self.current_spread / median
    
    def should_halt_trading(self, halt_threshold: float = 5.0) -> bool:
        """
        Determina si se debe detener trading basándose en spread.
        
        Args:
            halt_threshold: Ratio sobre mediana que dispara halt (default: 5.0)
            
        Returns:
            True si spread indica halt
        """
        ratio = self.get_spread_ratio()
        
        if ratio is None:
            return False
        
        should_halt = ratio > halt_threshold
        
        if should_halt:
            current = self.get_current_spread()
            median = self.get_median_spread()
            self.logger.warning(
                f"HALT RECOMENDADO: Spread = {current:.2f} bp "
                f"({ratio:.2f}x mediana de {median:.2f} bp). "
                f"Threshold: {halt_threshold}x. "
                f"Costos de transacción prohibitivos."
            )
        
        return should_halt
    
    def should_reduce_sizing(self, reduce_threshold: float = 2.0) -> bool:
        """
        Determina si se debe reducir sizing basándose en spread.
        
        Args:
            reduce_threshold: Ratio que dispara reducción (default: 2.0)
            
        Returns:
            True si spread indica reducir sizing
        """
        ratio = self.get_spread_ratio()
        
        if ratio is None:
            return False
        
        should_reduce = ratio > reduce_threshold
        
        if should_reduce:
            current = self.get_current_spread()
            median = self.get_median_spread()
            self.logger.info(
                f"REDUCIR SIZING: Spread = {current:.2f} bp "
                f"({ratio:.2f}x mediana de {median:.2f} bp). "
                f"Costos de transacción elevados."
            )
        
        return should_reduce
    
    def get_sizing_multiplier(self,
                             reduce_threshold: float = 2.0,
                             halt_threshold: float = 5.0) -> float:
        """
        Retorna multiplicador de sizing basado en spread.
        
        Args:
            reduce_threshold: Ratio que comienza reducción
            halt_threshold: Ratio que causa halt
            
        Returns:
            Multiplicador entre 0.0 y 1.2:
            - 1.2 si spread < 0.8x mediana (spread comprimido)
            - 1.0 si spread ~ 1.0x mediana (normal)
            - 0.6 si spread ~ 2.0x mediana (elevado)
            - 0.0 si spread > 5.0x mediana (halt)
        """
        ratio = self.get_spread_ratio()
        
        if ratio is None:
            return 1.0
        
        if ratio > halt_threshold:
            return 0.0  # Halt
        
        if ratio < 0.8:
            return 1.2  # Spread comprimido, aumentar sizing
        
        if ratio < reduce_threshold:
            return 1.0  # Normal
        
        # Reducción gradual entre reduce_threshold y halt_threshold
        reduction_factor = (halt_threshold - ratio) / (halt_threshold - reduce_threshold)
        return 0.6 * reduction_factor
    
    def get_status_report(self) -> Dict:
        """
        Retorna reporte completo del estado actual.
        
        Returns:
            Dict con todas las métricas relevantes
        """
        return {
            'spread_current': self.current_spread,
            'spread_mean': self.get_mean_spread(),
            'spread_median': self.get_median_spread(),
            'spread_std': self.get_spread_std(),
            'spread_ratio': self.get_spread_ratio(),
            'sizing_multiplier': self.get_sizing_multiplier(),
            'should_reduce_sizing': self.should_reduce_sizing(),
            'should_halt': self.should_halt_trading(),
            'spreads_in_buffer': len(self.spreads),
            'historical_samples': len(self.spread_history)
        }
