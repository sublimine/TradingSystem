"""
Kyle's Lambda Estimator - Market Impact Measurement

Implementa el modelo de Kyle (1985) para estimar lambda, que mide cuánto
se mueve el precio por unidad de volumen traded.

Lambda = ΔPrice / SignedVolume

Cuando lambda es alto, indica:
- Mercado poco profundo (baja liquidez)
- Presencia de informed traders moviendo precio agresivamente
- Alto costo de impacto por ejecutar órdenes

Referencias:
- Kyle, A. S. (1985). "Continuous Auctions and Insider Trading"
- Hasbrouck, J. (2007). "Empirical Market Microstructure"
- Glosten, L. & Harris, L. (1988). "Estimating the Components of the Bid-Ask Spread"

Author: Sistema de Trading Institucional
Date: 2025-11-06
Version: 1.0
"""

import numpy as np
import pandas as pd
from typing import Optional, Tuple, Dict
from collections import deque
import logging


class KylesLambdaEstimator:
    """
    Estimador de Kyle's Lambda usando regresión recursiva.
    
    Lambda mide el impacto de mercado: cuánto se mueve el precio
    por cada unidad de volumen traded en una dirección.
    
    Método de estimación:
    - Regresión OLS: ΔPrice ~ Lambda * SignedVolume
    - Ventana rodante de N trades (default: 100)
    - Actualización recursiva cada K trades (default: 10)
    """
    
    def __init__(self,
                 estimation_window: int = 100,
                 update_frequency: int = 10,
                 historical_window: int = 1000,
                 warm_up_threshold: int = 100,
                 warm_up_absolute_lambda: float = 0.05):
        """
        Inicializa el estimador.

        Args:
            estimation_window: Número de trades para regresión (default: 100)
            update_frequency: Cada cuántos trades actualizar (default: 10)
            historical_window: Ventana para estadísticas históricas (default: 1000)
            warm_up_threshold: Mínimo de trades antes de usar ratios (default: 100)
            warm_up_absolute_lambda: Threshold absoluto durante warm-up (default: 0.05)
        """
        self.estimation_window = estimation_window
        self.update_frequency = update_frequency
        self.historical_window = historical_window

        # CR12 FIX: Agregar warm-up phase para prevenir false negatives
        self.warm_up_threshold = warm_up_threshold
        self.warm_up_absolute_lambda = warm_up_absolute_lambda
        self.trades_observed = 0

        # Buffers para datos
        self.price_changes = deque(maxlen=estimation_window)
        self.signed_volumes = deque(maxlen=estimation_window)

        # Historia de lambdas estimados
        self.lambda_history = deque(maxlen=historical_window)

        # Lambda actual
        self.current_lambda = None
        self.lambda_stderr = None

        # Contador de trades desde última actualización
        self.trades_since_update = 0

        self.logger = logging.getLogger(self.__class__.__name__)

        self.logger.info(
            f"Kyle's Lambda Estimator inicializado: "
            f"window={estimation_window}, update_freq={update_frequency}, "
            f"warm_up_threshold={warm_up_threshold}, "
            f"warm_up_absolute_lambda={warm_up_absolute_lambda}"
        )
    
    def classify_trade_direction(self, 
                                  price: float, 
                                  prev_mid: float) -> int:
        """
        Clasifica la dirección del trade usando tick rule.
        
        Args:
            price: Precio de la transacción
            prev_mid: Mid-price previo
            
        Returns:
            +1 si es compra, -1 si es venta, 0 si neutral
        """
        if price > prev_mid:
            return 1  # Buy
        elif price < prev_mid:
            return -1  # Sell
        else:
            return 0  # Neutral (usar cambio de precio como fallback)
    
    def update(self, 
               current_price: float, 
               prev_price: float,
               volume: float,
               mid_price: float,
               prev_mid: float) -> None:
        """
        Actualiza el estimador con un nuevo trade.
        
        Args:
            current_price: Precio actual de transacción
            prev_price: Precio previo
            volume: Volumen del trade
            mid_price: Mid-price actual
            prev_mid: Mid-price previo
        """
        # Calcular cambio de precio
        price_change = current_price - prev_price
        
        # Clasificar dirección del trade
        trade_direction = self.classify_trade_direction(current_price, prev_mid)
        
        # Si no podemos clasificar con mid-price, usar cambio de precio
        if trade_direction == 0:
            trade_direction = 1 if price_change > 0 else -1 if price_change < 0 else 0
        
        # Signed volume = dirección * volumen
        signed_volume = trade_direction * volume
        
        # Agregar a buffers
        self.price_changes.append(price_change)
        self.signed_volumes.append(signed_volume)

        # Incrementar contadores
        self.trades_since_update += 1
        # CR12 FIX: Incrementar contador para warm-up phase
        self.trades_observed += 1

        # Re-estimar lambda si es momento de actualizar
        if self.trades_since_update >= self.update_frequency:
            self._estimate_lambda()
            self.trades_since_update = 0
    
    def _estimate_lambda(self) -> None:
        """
        Estima lambda usando regresión OLS en ventana actual.
        
        Modelo: ΔPrice = λ * SignedVolume + ε
        
        Lambda se estima como: λ = Cov(ΔP, SV) / Var(SV)
        """
        if len(self.price_changes) < 30:
            # Necesitamos mínimo 30 observaciones para estimación robusta
            return
        
        # Convertir a arrays numpy
        delta_prices = np.array(self.price_changes)
        signed_vols = np.array(self.signed_volumes)
        
        # Remover observaciones con volumen cero (evitar división por cero)
        nonzero_mask = signed_vols != 0
        delta_prices = delta_prices[nonzero_mask]
        signed_vols = signed_vols[nonzero_mask]
        
        if len(signed_vols) < 10:
            return
        
        # Calcular lambda = Cov(ΔP, SV) / Var(SV)
        covariance = np.cov(delta_prices, signed_vols)[0, 1]
        variance_sv = np.var(signed_vols)
        
        if variance_sv > 1e-10:  # Evitar división por valores muy pequeños
            lambda_estimate = covariance / variance_sv
            
            # Calcular error estándar
            residuals = delta_prices - lambda_estimate * signed_vols
            mse = np.mean(residuals ** 2)
            stderr = np.sqrt(mse / variance_sv)
            
            # Guardar estimados
            self.current_lambda = lambda_estimate
            self.lambda_stderr = stderr
            
            # Agregar a historia
            self.lambda_history.append(lambda_estimate)
            
            self.logger.debug(
                f"Lambda actualizado: {lambda_estimate:.6f} (stderr: {stderr:.6f})"
            )
    
    def get_lambda(self) -> Optional[float]:
        """
        Retorna el lambda actual estimado.
        
        Returns:
            Lambda actual, o None si no hay suficientes datos
        """
        return self.current_lambda
    
    def get_historical_mean(self) -> Optional[float]:
        """
        Retorna la media histórica de lambda.
        
        Returns:
            Media de lambda en ventana histórica, o None si insuficiente historia
        """
        if len(self.lambda_history) < 50:
            return None
        
        return np.mean(self.lambda_history)
    
    def get_historical_std(self) -> Optional[float]:
        """
        Retorna la desviación estándar histórica de lambda.
        
        Returns:
            Std de lambda en ventana histórica, o None si insuficiente historia
        """
        if len(self.lambda_history) < 50:
            return None
        
        return np.std(self.lambda_history)
    
    def get_lambda_ratio(self) -> Optional[float]:
        """
        Retorna el ratio de lambda actual sobre su media histórica.
        
        Este ratio es la métrica clave para decisiones:
        - Ratio < 0.5: Liquidez excelente, aumentar sizing
        - Ratio ~ 1.0: Liquidez normal
        - Ratio > 2.0: Liquidez degradada, reducir sizing
        - Ratio > 3.0: Liquidez crítica, detener trading
        
        Returns:
            Lambda_actual / Lambda_histórico, o None si no hay suficiente data
        """
        if self.current_lambda is None:
            return None
        
        historical_mean = self.get_historical_mean()
        
        if historical_mean is None or historical_mean == 0:
            return None
        
        return abs(self.current_lambda) / abs(historical_mean)
    
    def should_halt_trading(self, halt_threshold: float = 3.0) -> bool:
        """
        Determina si se debe detener el trading basándose en lambda.

        Args:
            halt_threshold: Ratio sobre media histórica que dispara halt (default: 3.0)

        Returns:
            True si lambda indica que se debe detener trading
        """
        # CR12 FIX: Durante warm-up, usar threshold absoluto en lugar de ratio
        if self.trades_observed < self.warm_up_threshold:
            if self.current_lambda is None:
                # Sin datos → conservador: halt trading
                self.logger.warning(
                    f"HALT WARM-UP: Sin datos de lambda (trades={self.trades_observed}/{self.warm_up_threshold}). "
                    f"Conservador: bloquear trading hasta warm-up completo."
                )
                return True

            # Usar threshold absoluto durante warm-up
            should_halt = self.current_lambda > self.warm_up_absolute_lambda

            if should_halt:
                self.logger.warning(
                    f"HALT WARM-UP: Lambda = {self.current_lambda:.4f} > "
                    f"{self.warm_up_absolute_lambda:.4f} (threshold absoluto). "
                    f"Trades observados: {self.trades_observed}/{self.warm_up_threshold}."
                )

            return should_halt

        # Post-warm-up: usar ratio sobre media histórica
        ratio = self.get_lambda_ratio()

        if ratio is None:
            # CR12 FIX: Si no hay datos post-warm-up, ser conservador
            self.logger.warning("HALT: Sin datos válidos para calcular ratio de lambda. Conservador: bloquear trading.")
            return True

        should_halt = ratio > halt_threshold

        if should_halt:
            self.logger.warning(
                f"HALT RECOMENDADO: Lambda ratio = {ratio:.2f}x (threshold: {halt_threshold}x). "
                f"Liquidez críticamente degradada."
            )

        return should_halt
    
    def should_reduce_sizing(self, reduce_threshold: float = 2.0) -> bool:
        """
        Determina si se debe reducir sizing basándose en lambda.

        Args:
            reduce_threshold: Ratio que dispara reducción de sizing (default: 2.0)

        Returns:
            True si lambda indica que se debe reducir sizing
        """
        # CR12 FIX: Durante warm-up, usar threshold absoluto más conservador
        if self.trades_observed < self.warm_up_threshold:
            if self.current_lambda is None:
                # Sin datos → conservador: reducir sizing
                return True

            # Usar threshold absoluto más bajo para reducción (60% del halt threshold)
            reduce_absolute_threshold = self.warm_up_absolute_lambda * 0.6
            should_reduce = self.current_lambda > reduce_absolute_threshold

            if should_reduce:
                self.logger.info(
                    f"REDUCIR SIZING WARM-UP: Lambda = {self.current_lambda:.4f} > "
                    f"{reduce_absolute_threshold:.4f} (threshold absoluto). "
                    f"Trades observados: {self.trades_observed}/{self.warm_up_threshold}."
                )

            return should_reduce

        # Post-warm-up: usar ratio sobre media histórica
        ratio = self.get_lambda_ratio()

        if ratio is None:
            # CR12 FIX: Si no hay datos post-warm-up, conservador: reducir sizing
            return True

        should_reduce = ratio > reduce_threshold

        if should_reduce:
            self.logger.info(
                f"REDUCIR SIZING: Lambda ratio = {ratio:.2f}x (threshold: {reduce_threshold}x). "
                f"Liquidez degradada."
            )

        return should_reduce
    
    def get_sizing_multiplier(self, 
                             reduce_threshold: float = 2.0,
                             halt_threshold: float = 3.0) -> float:
        """
        Retorna multiplicador de sizing basado en lambda actual.
        
        Args:
            reduce_threshold: Ratio que comienza reducción gradual
            halt_threshold: Ratio que causa halt completo
            
        Returns:
            Multiplicador entre 0.0 y 1.2:
            - 1.2 si lambda < 0.5x (liquidez excelente)
            - 1.0 si lambda ~ 1.0x (liquidez normal)
            - 0.6 si lambda ~ 2.0x (liquidez degradada)
            - 0.0 si lambda > 3.0x (halt)
        """
        ratio = self.get_lambda_ratio()
        
        if ratio is None:
            return 1.0  # Default si no hay datos
        
        if ratio > halt_threshold:
            return 0.0  # Halt completo
        
        if ratio < 0.5:
            return 1.2  # Aumentar sizing en liquidez excelente
        
        if ratio < reduce_threshold:
            return 1.0  # Sizing normal
        
        # Reducción gradual entre reduce_threshold y halt_threshold
        # Linear interpolation
        reduction_factor = (halt_threshold - ratio) / (halt_threshold - reduce_threshold)
        return 0.6 * reduction_factor
    
    def get_status_report(self) -> Dict:
        """
        Retorna reporte completo del estado actual.
        
        Returns:
            Dict con todas las métricas relevantes
        """
        return {
            'lambda_current': self.current_lambda,
            'lambda_stderr': self.lambda_stderr,
            'lambda_historical_mean': self.get_historical_mean(),
            'lambda_historical_std': self.get_historical_std(),
            'lambda_ratio': self.get_lambda_ratio(),
            'sizing_multiplier': self.get_sizing_multiplier(),
            'should_reduce_sizing': self.should_reduce_sizing(),
            'should_halt': self.should_halt_trading(),
            'trades_in_buffer': len(self.price_changes),
            'historical_samples': len(self.lambda_history)
        }
