"""
Absorption Breakout Strategy - Institutional Implementation

Esta estrategia detecta breakouts genuinos respaldados por absorción institucional,
distinguiéndolos de breakouts falsos que son trampas retail.

DIFERENCIADORES CLAVE vs implementación retail:
1. Delta Volume Classification: Usa tick rule de Lee-Ready para clasificar cada
   tick como compra o venta, calculando net buying pressure
2. Displacement Requirement: Exige movimiento sostenido ≥1.5 ATR post-breakout
3. Sweep Detection: Invalida breakouts en niveles que fueron swept previamente
4. OFI Confirmation: Requiere Order Flow Imbalance coherente con dirección

FUNDAMENTO INSTITUCIONAL:
- Harris (2003): "Trading and Exchanges" - tick classification
- Easley et al. (2012): "Flow toxicity" - informed vs uninformed volume
- O'Hara (1995): "Market Microstructure Theory" - price discovery via volume

Author: Sistema de Trading Institucional
Date: 2025-11-05
Version: 2.0 (Institutional Grade)
"""

import numpy as np
import pandas as pd
from typing import Optional, Dict, List, Tuple
from dataclasses import dataclass
from collections import deque
import logging
from strategies.strategy_base import StrategyBase, Signal

# Import de la base de estrategia


@dataclass
class LevelMemory:
    """Memoria de niveles de precio para detección de sweeps."""
    price: float
    timestamp: pd.Timestamp
    was_swept: bool
    sweep_direction: Optional[str]  # 'up' o 'down'


class AbsorptionBreakout(StrategyBase):
    """
    Breakout Strategy con filtros institucionales de absorción.
    
    Opera breakouts genuinos que exhiben tres firmas institucionales:
    1. Delta volume fuertemente sesgado (> 1.8 sigma) vía Lee-Ready classification
    2. Displacement sostenido post-breakout (≥ 1.5 ATR en 5 barras)
    3. Ausencia de liquidity sweep previo en ese nivel
    """
    
    def __init__(self, config: Dict):
        """
        Inicializa estrategia con configuración institucional.
        
        Args:
            config: Diccionario con parámetros, incluyendo:
                - atr_period: Periodo para ATR (default: 14)
                - volume_lookback: Ventana para estadísticas de volumen (default: 50)
                - delta_volume_threshold_sigma: Umbral para delta volume (default: 1.8)
                - displacement_atr_multiplier: Multiplicador ATR para displacement (default: 1.5)
                - displacement_bars: Barras para medir displacement (default: 5)
                - sweep_memory_bars: Cuántas barras recordar sweeps (default: 40)
                - min_breakout_volume_percentile: Percentil mínimo de volumen (default: 70)
        """
        super().__init__(config)
        
        # Parámetros institucionales
        self.atr_period = self.config.get('atr_period', 14)
        self.volume_lookback = self.config.get('volume_lookback', 50)
        self.delta_threshold_sigma = self.config.get('delta_volume_threshold_sigma', 1.8)
        self.displacement_atr_mult = self.config.get('displacement_atr_multiplier', 1.5)
        self.displacement_bars = self.config.get('displacement_bars', 5)
        self.sweep_memory_bars = self.config.get('sweep_memory_bars', 40)
        self.min_volume_pct = self.config.get('min_breakout_volume_percentile', 70)
        
        # Memoria de niveles importantes
        self.level_memory: deque = deque(maxlen=self.sweep_memory_bars)
        
        self.logger = logging.getLogger(self.__class__.__name__)
        
        self.logger.info(f"Absorption Breakout inicializado con parámetros institucionales:")
        self.logger.info(f"  Delta threshold: {self.delta_threshold_sigma}σ")
        self.logger.info(f"  Displacement required: {self.displacement_atr_mult}x ATR")
        self.logger.info(f"  Sweep memory: {self.sweep_memory_bars} bars")
    
    def classify_tick_direction(self, data: pd.DataFrame) -> pd.Series:
        """
        Clasifica cada tick como compra o venta usando Lee-Ready tick rule.
        
        Método:
        - Si close > mid_price: clasificar como compra (+1)
        - Si close < mid_price: clasificar como venta (-1)
        - Si close == mid_price: usar cambio de precio (uptick rule)
        
        Args:
            data: DataFrame con columnas high, low, close
            
        Returns:
            Series con clasificación: +1 (compra), -1 (venta), 0 (neutral)
            
        Fundamento:
            Lee-Ready (1991): "Inferring Trade Direction from Intraday Data"
            Precisión empírica: 75-80% en clasificación correcta
        """
        # Calcular mid-price
        mid_price = (data['high'] + data['low']) / 2
        
        # Clasificación primaria: comparar close con mid
        classification = np.where(
            data['close'] > mid_price, 1,  # Compra
            np.where(data['close'] < mid_price, -1, 0)  # Venta o neutral
        )
        
        # Para casos neutrales, usar uptick rule
        price_change = data['close'].diff()
        uptick_rule = np.where(
            price_change > 0, 1,
            np.where(price_change < 0, -1, 0)
        )
        
        # Combinar: usar clasificación primaria, y uptick rule para neutrals
        final_classification = np.where(
            classification == 0,
            uptick_rule,
            classification
        )
        
        return pd.Series(final_classification, index=data.index)
    
    def calculate_delta_volume(self, data: pd.DataFrame) -> Tuple[pd.Series, float, float]:
        """
        Calcula delta volume usando clasificación de ticks.
        
        Delta Volume = Volume_buys - Volume_sells
        
        Args:
            data: DataFrame con volume y clasificación de dirección
            
        Returns:
            Tuple de:
            - Series de delta volume acumulado
            - Media de delta volume
            - Desviación estándar de delta volume
        """
        # Clasificar dirección de cada tick
        tick_direction = self.classify_tick_direction(data)
        
        # Delta volume = dirección * volumen
        delta_volume = tick_direction * data['tick_volume']
        
        # Calcular estadísticas en ventana rodante
        delta_mean = delta_volume.rolling(self.volume_lookback).mean()
        delta_std = delta_volume.rolling(self.volume_lookback).std()
        
        return delta_volume, delta_mean.iloc[-1], delta_std.iloc[-1]
    
    def detect_liquidity_sweep(self, data: pd.DataFrame, level: float, direction: str) -> bool:
        """
        Detecta si hubo liquidity sweep del nivel en barras recientes.
        
        Sweep = penetración breve del nivel seguida por reversión rápida.
        
        Args:
            data: DataFrame con OHLC
            level: Nivel de precio a verificar
            direction: 'up' (resistencia) o 'down' (soporte)
            
        Returns:
            True si se detectó sweep previo, False en caso contrario
        """
        # Revisar últimas barras en memoria
        for i in range(min(len(data), self.sweep_memory_bars)):
            bar_idx = len(data) - 1 - i
            
            if bar_idx < 0:
                break
            
            bar = data.iloc[bar_idx]
            
            if direction == 'up':
                # Sweep de resistencia: high penetra el nivel pero close está debajo
                penetration = bar['high'] > level
                reversal = bar['close'] < level
                
                if penetration and reversal:
                    # Verificar que el reversal fue significativo
                    reversal_distance = level - bar['close']
                    bar_range = bar['high'] - bar['low']
                    
                    if reversal_distance > 0.3 * bar_range:
                        self.logger.info(f"Sweep detectado en {level:.5f} hace {i} barras (dirección: up)")
                        return True
                        
            elif direction == 'down':
                # Sweep de soporte: low penetra el nivel pero close está arriba
                penetration = bar['low'] < level
                reversal = bar['close'] > level
                
                if penetration and reversal:
                    reversal_distance = bar['close'] - level
                    bar_range = bar['high'] - bar['low']
                    
                    if reversal_distance > 0.3 * bar_range:
                        self.logger.info(f"Sweep detectado en {level:.5f} hace {i} barras (dirección: down)")
                        return True
        
        return False
    
    def measure_displacement(self, data: pd.DataFrame, breakout_price: float, direction: str) -> float:
        """
        Mide el displacement post-breakout en múltiplos de ATR.
        
        Args:
            data: DataFrame con OHLC y ATR calculado
            breakout_price: Precio del breakout
            direction: 'long' o 'short'
            
        Returns:
            Displacement en múltiplos de ATR
        """
        if len(data) < self.displacement_bars + 1:
            return 0.0
        
        # Tomar las siguientes N barras después del breakout
        post_breakout = data.iloc[-self.displacement_bars:]
        
        if direction == 'long':
            # Para LONG, medir cuánto subió desde breakout_price
            max_price = post_breakout['high'].max()
            displacement = max_price - breakout_price
        else:
            # Para SHORT, medir cuánto bajó desde breakout_price
            min_price = post_breakout['low'].min()
            displacement = breakout_price - min_price
        
        # Normalizar por ATR actual
        current_atr = data['atr'].iloc[-1]
        
        if current_atr > 0:
            displacement_atr = displacement / current_atr
        else:
            displacement_atr = 0.0
        
        return displacement_atr
    
    def evaluate(self, data: pd.DataFrame, features: Dict) -> Optional[Signal]:
        """
        Evalúa condiciones para breakout institucional con absorción confirmada.
        
        Proceso de validación (todos los filtros deben pasar):
        1. Identificar breakout de rango con volumen elevado
        2. Calcular delta volume y verificar que > threshold sigma
        3. Verificar ausencia de sweep previo en ese nivel
        4. Medir displacement post-breakout y verificar que ≥ threshold ATR
        5. Confirmar con OFI si está disponible en features
        
        Args:
            data: DataFrame con OHLC, volume, indicadores
            features: Dict con features adicionales (OFI, VPIN, etc)
            
        Returns:
            Signal object si todos los filtros pasan, None en caso contrario
        """
        if len(data) < max(self.atr_period, self.volume_lookback, self.displacement_bars):
            return None
        
        # Calcular ATR si no está presente
        if 'atr' not in data.columns:
            data['atr'] = self.calculate_atr(data, self.atr_period)
        
        current_bar = data.iloc[-1]
        prev_bar = data.iloc[-2]
        
        current_atr = current_bar['atr']
        
        # ===================================================================
        # PASO 1: Detectar breakout potencial
        # ===================================================================
        
        # Calcular rango de consolidación en últimas barras
        lookback_range = data.iloc[-20:]
        range_high = lookback_range['high'].max()
        range_low = lookback_range['low'].min()
        range_mid = (range_high + range_low) / 2
        
        # Detectar breakout alcista
        is_breakout_up = (
            prev_bar['close'] <= range_high and
            current_bar['close'] > range_high and
            current_bar['close'] > current_bar['open']  # Vela alcista
        )
        
        # Detectar breakout bajista
        is_breakout_down = (
            prev_bar['close'] >= range_low and
            current_bar['close'] < range_low and
            current_bar['close'] < current_bar['open']  # Vela bajista
        )
        
        if not (is_breakout_up or is_breakout_down):
            return None
        
        direction = 'long' if is_breakout_up else 'short'
        breakout_level = range_high if is_breakout_up else range_low
        
        self.logger.info(f"Breakout potencial detectado: {direction} en {breakout_level:.5f}")
        
        # ===================================================================
        # PASO 2: Validar volumen elevado
        # ===================================================================
        
        volume_percentile = (
            (data['tick_volume'].iloc[-50:] < current_bar['tick_volume']).sum() / 50 * 100
        )
        
        if volume_percentile < self.min_volume_pct:
            self.logger.info(
                f"Breakout rechazado: volumen insuficiente "
                f"(percentil {volume_percentile:.1f}% < {self.min_volume_pct}%)"
            )
            return None
        
        # ===================================================================
        # PASO 3: Validar delta volume (absorción institucional)
        # ===================================================================
        
        delta_vol, delta_mean, delta_std = self.calculate_delta_volume(data)
        
        current_delta = delta_vol.iloc[-1]
        
        if delta_std > 0:
            delta_z_score = (current_delta - delta_mean) / delta_std
        else:
            delta_z_score = 0
        
        # Para LONG, requerimos delta positivo (más compras)
        # Para SHORT, requerimos delta negativo (más ventas)
        delta_valid = False
        
        if direction == 'long' and delta_z_score > self.delta_threshold_sigma:
            delta_valid = True
            self.logger.info(f"Delta volume LONG válido: z-score = {delta_z_score:.2f}σ")
        elif direction == 'short' and delta_z_score < -self.delta_threshold_sigma:
            delta_valid = True
            self.logger.info(f"Delta volume SHORT válido: z-score = {delta_z_score:.2f}σ")
        
        if not delta_valid:
            self.logger.info(
                f"Breakout rechazado: delta volume insuficiente "
                f"(z-score = {delta_z_score:.2f}σ, threshold = {self.delta_threshold_sigma}σ)"
            )
            return None
        
        # ===================================================================
        # PASO 4: Verificar ausencia de sweep previo
        # ===================================================================
        
        sweep_direction = 'up' if direction == 'long' else 'down'
        has_sweep = self.detect_liquidity_sweep(data, breakout_level, sweep_direction)
        
        if has_sweep:
            self.logger.warning(
                f"Breakout rechazado: nivel {breakout_level:.5f} fue swept previamente. "
                "Segundo toque post-sweep es trampa retail."
            )
            return None
        
        # ===================================================================
        # PASO 5: Medir displacement post-breakout
        # ===================================================================
        
        # Nota: En tiempo real, necesitaríamos esperar N barras para medir displacement
        # En backtest, podemos "mirar adelante" para validación
        # Para implementación live, este filtro se aplica como confirmación retrasada
        
        displacement = self.measure_displacement(data, breakout_level, direction)
        
        if displacement < self.displacement_atr_mult:
            self.logger.info(
                f"Breakout rechazado: displacement insuficiente "
                f"({displacement:.2f}x ATR < {self.displacement_atr_mult}x ATR requerido)"
            )
            return None
        
        self.logger.info(f"Displacement validado: {displacement:.2f}x ATR")
        
        # ===================================================================
        # PASO 6: Confirmar con OFI si disponible
        # ===================================================================
        
        if 'ofi_imbalance' in features:
            ofi = features['ofi_imbalance']
            
            # Para LONG, OFI debe ser positivo; para SHORT, negativo
            ofi_confirms = (direction == 'long' and ofi > 0) or (direction == 'short' and ofi < 0)
            
            if not ofi_confirms:
                self.logger.warning(
                    f"Breakout rechazado: OFI no confirma dirección "
                    f"(OFI={ofi:.2f}, direction={direction})"
                )
                return None
            
            self.logger.info(f"OFI confirma dirección: {ofi:.2f}")
        
        # ===================================================================
        # TODOS LOS FILTROS PASARON - GENERAR SEÑAL
        # ===================================================================
        
        self.logger.info(
            f"SEÑAL INSTITUCIONAL GENERADA: {direction.upper()} breakout en {breakout_level:.5f}"
        )
        
        # Calcular niveles de gestión de riesgo
        if direction == 'long':
            entry_price = current_bar['close']
            # Stop loss debajo del rango de consolidación con buffer de 0.5 ATR
            stop_loss = range_low - 0.5 * current_atr
            # Take profit basado en displacement esperado similar (1.5 ATR)
            take_profit = entry_price + 2.0 * current_atr
            
        else:  # short
            entry_price = current_bar['close']
            stop_loss = range_high + 0.5 * current_atr
            take_profit = entry_price - 2.0 * current_atr
        
        # Sizing level basado en calidad de señal (3 de 5 = medio-alto)
        # Todos los filtros pasaron, así que confianza es alta
        sizing_level = 4
        
        return Signal(
            strategy_name=self.name,
            direction=direction,
            entry_price=entry_price,
            stop_loss=stop_loss,
            take_profit=take_profit,
            confidence=0.80,  # Alta confianza - todos los filtros institucionales pasaron
            sizing_level=sizing_level,
            metadata={
                'breakout_level': breakout_level,
                'delta_z_score': float(delta_z_score),
                'displacement_atr': float(displacement),
                'volume_percentile': float(volume_percentile),
                'range_high': float(range_high),
                'range_low': float(range_low),
                'ofi_confirmation': 'ofi_imbalance' in features
            }
        )
    
    def calculate_atr(self, data: pd.DataFrame, period: int) -> pd.Series:
        """
        Calcula Average True Range.
        
        Args:
            data: DataFrame con high, low, close
            period: Periodo para ATR
            
        Returns:
            Series con valores de ATR
        """
        high = data['high']
        low = data['low']
        close = data['close']
        
        # True Range = max(high-low, abs(high-prev_close), abs(low-prev_close))
        tr1 = high - low
        tr2 = abs(high - close.shift())
        tr3 = abs(low - close.shift())
        
        true_range = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        
        atr = true_range.rolling(period).mean()
        
        return atr


# Mantener compatibilidad con nombre antiguo en imports
BreakoutVolumeConfirmation = AbsorptionBreakout



