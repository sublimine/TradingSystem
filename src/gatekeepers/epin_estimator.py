"""
ePIN/VPIN Estimator - Probability of Informed Trading

Implementa estimación de probabilidad de que haya traders informados
operando activamente en el mercado.

ePIN es versión simplificada de PIN que no requiere MLE complejo.
VPIN usa volume buckets para estimar toxicidad del flujo.

Cuando PIN/VPIN es alto, indica:
- Presencia de informed traders con información superior
- Alto riesgo de adverse selection
- Momento peligroso para proveer liquidez

Referencias:
- Easley et al. (2012): "Flow Toxicity and Liquidity in a High Frequency World"
- Easley, O'Hara & Kiefer (1996): "Informed Trading"
- Andersen & Bondarenko (2014): "VPIN and the Flash Crash"

Author: Sistema de Trading Institucional  
Date: 2025-11-06
Version: 1.0
"""

import numpy as np
import pandas as pd
from typing import Optional, Dict, List
from collections import deque
import logging


class ePINEstimator:
    """
    Estimador de Probability of Informed Trading.
    
    Combina dos métodos:
    1. ePIN: Estimación simple basada en imbalance rolling
    2. VPIN: Volume-synchronized probability usando buckets
    
    Ambos producen valor entre 0 y 1:
    - 0.0 = Sin informed trading (seguro)
    - 0.5 = Neutral
    - 0.7+ = Alto informed trading (peligroso)
    - 0.85+ = Crítico (detener trading)
    """
    
    def __init__(self,
                 volume_buckets: int = 50,
                 bucket_size: float = 10000.0,
                 epin_window: int = 100):
        """
        Inicializa el estimador.
        
        Args:
            volume_buckets: Número de buckets para VPIN (default: 50)
            bucket_size: Volumen target por bucket (default: 10000)
            epin_window: Ventana para ePIN simple (default: 100)
        """
        self.volume_buckets = volume_buckets
        self.bucket_size = bucket_size
        self.epin_window = epin_window
        
        # Buckets para VPIN
        self.buy_volumes = deque(maxlen=volume_buckets)
        self.sell_volumes = deque(maxlen=volume_buckets)
        
        # Bucket actual acumulándose
        self.current_bucket_buy = 0.0
        self.current_bucket_sell = 0.0
        self.current_bucket_total = 0.0
        
        # Para ePIN simple
        self.trade_directions = deque(maxlen=epin_window)
        
        # Valores actuales
        self.current_vpin = None
        self.current_epin = None
        
        self.logger = logging.getLogger(self.__class__.__name__)
        
        self.logger.info(
            f"ePIN/VPIN Estimator inicializado: "
            f"buckets={volume_buckets}, bucket_size={bucket_size}, epin_window={epin_window}"
        )
    
    def classify_trade(self, 
                      price: float, 
                      prev_mid: float) -> int:
        """
        Clasifica trade como compra o venta usando tick rule.
        
        Args:
            price: Precio de transacción
            prev_mid: Mid-price previo
            
        Returns:
            +1 para compra, -1 para venta
        """
        if price >= prev_mid:
            return 1  # Buy
        else:
            return -1  # Sell
    
    def update(self,
               price: float,
               volume: float,
               prev_mid: float) -> None:
        """
        Actualiza estimadores con nuevo trade.
        
        Args:
            price: Precio de transacción
            volume: Volumen del trade
            prev_mid: Mid-price antes de este trade
        """
        # Clasificar dirección
        direction = self.classify_trade(price, prev_mid)
        
        # Actualizar ePIN simple
        self.trade_directions.append(direction)
        self._update_epin()
        
        # Actualizar VPIN con volume buckets
        if direction == 1:
            # Buy
            self.current_bucket_buy += volume
        else:
            # Sell
            self.current_bucket_sell += volume
        
        self.current_bucket_total += volume
        
        # Si bucket está lleno, cerrar y crear nuevo
        if self.current_bucket_total >= self.bucket_size:
            self.buy_volumes.append(self.current_bucket_buy)
            self.sell_volumes.append(self.current_bucket_sell)
            
            # Reset bucket
            self.current_bucket_buy = 0.0
            self.current_bucket_sell = 0.0
            self.current_bucket_total = 0.0
            
            # Recalcular VPIN
            self._update_vpin()
    
    def _update_epin(self) -> None:
        """
        Actualiza ePIN usando formula simplificada.
        
        ePIN = |Buys - Sells| / Total Trades
        
        Aproximación simple del PIN completo que no requiere MLE.
        """
        if len(self.trade_directions) < 20:
            return
        
        directions = np.array(self.trade_directions)
        
        n_buys = np.sum(directions == 1)
        n_sells = np.sum(directions == -1)
        n_total = len(directions)
        
        # ePIN = order imbalance absoluto
        self.current_epin = abs(n_buys - n_sells) / n_total
        
        self.logger.debug(f"ePIN actualizado: {self.current_epin:.4f}")
    
    def _update_vpin(self) -> None:
        """
        Actualiza VPIN usando volume buckets.
        
        VPIN = Σ|V_buy - V_sell| / Σ(V_buy + V_sell)
        
        Mide fracción de volumen que es order flow tóxico.
        """
        if len(self.buy_volumes) < 10:
            return
        
        buy_vols = np.array(self.buy_volumes)
        sell_vols = np.array(self.sell_volumes)
        
        # Order flow imbalance por bucket
        imbalances = np.abs(buy_vols - sell_vols)
        
        # Total volume
        total_volume = np.sum(buy_vols + sell_vols)
        
        if total_volume > 0:
            self.current_vpin = np.sum(imbalances) / total_volume
            
            self.logger.debug(f"VPIN actualizado: {self.current_vpin:.4f}")
    
    def get_pin(self) -> Optional[float]:
        """
        Retorna mejor estimado actual de PIN.
        
        Usa promedio de ePIN y VPIN si ambos disponibles,
        o el que esté disponible.
        
        Returns:
            PIN estimado entre 0 y 1, o None si no hay datos
        """
        if self.current_epin is not None and self.current_vpin is not None:
            # Promedio ponderado (VPIN más confiable, peso 0.6)
            return 0.4 * self.current_epin + 0.6 * self.current_vpin
        elif self.current_vpin is not None:
            return self.current_vpin
        elif self.current_epin is not None:
            return self.current_epin
        else:
            return None
    
    def should_halt_trading(self, halt_threshold: float = 0.85) -> bool:
        """
        Determina si se debe detener trading basándose en PIN.
        
        Args:
            halt_threshold: PIN threshold para halt (default: 0.85)
            
        Returns:
            True si PIN indica halt
        """
        pin = self.get_pin()
        
        if pin is None:
            return False
        
        should_halt = pin > halt_threshold
        
        if should_halt:
            self.logger.warning(
                f"HALT RECOMENDADO: PIN = {pin:.4f} > {halt_threshold}. "
                f"Alta probabilidad de informed trading."
            )
        
        return should_halt
    
    def should_reduce_sizing(self, reduce_threshold: float = 0.70) -> bool:
        """
        Determina si se debe reducir sizing basándose en PIN.
        
        Args:
            reduce_threshold: PIN threshold para reducción (default: 0.70)
            
        Returns:
            True si PIN indica reducir sizing
        """
        pin = self.get_pin()
        
        if pin is None:
            return False
        
        should_reduce = pin > reduce_threshold
        
        if should_reduce:
            self.logger.info(
                f"REDUCIR SIZING: PIN = {pin:.4f} > {reduce_threshold}. "
                f"Informed trading detectado."
            )
        
        return should_reduce
    
    def get_sizing_multiplier(self,
                             reduce_threshold: float = 0.70,
                             halt_threshold: float = 0.85) -> float:
        """
        Retorna multiplicador de sizing basado en PIN.
        
        Args:
            reduce_threshold: PIN que comienza reducción
            halt_threshold: PIN que causa halt
            
        Returns:
            Multiplicador entre 0.0 y 1.0
        """
        pin = self.get_pin()
        
        if pin is None:
            return 1.0
        
        if pin > halt_threshold:
            return 0.0  # Halt
        
        if pin < reduce_threshold:
            return 1.0  # Normal
        
        # Reducción gradual entre thresholds
        reduction_factor = (halt_threshold - pin) / (halt_threshold - reduce_threshold)
        return 0.6 * reduction_factor
    
    def get_status_report(self) -> Dict:
        """
        Retorna reporte completo del estado actual.
        
        Returns:
            Dict con métricas relevantes
        """
        return {
            'pin_combined': self.get_pin(),
            'epin': self.current_epin,
            'vpin': self.current_vpin,
            'sizing_multiplier': self.get_sizing_multiplier(),
            'should_reduce_sizing': self.should_reduce_sizing(),
            'should_halt': self.should_halt_trading(),
            'buckets_filled': len(self.buy_volumes),
            'trades_in_epin_window': len(self.trade_directions)
        }
