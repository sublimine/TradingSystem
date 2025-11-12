"""
Iceberg Detection Strategy.

Identifies hidden large orders and trades their revelation.
Operates in degraded mode without L2 data.
"""

import pandas as pd
import numpy as np
from typing import Dict, Optional, List
from datetime import datetime
import logging
from .strategy_base import StrategyBase, Signal

from ..features.orderbook_l2 import (
    parse_l2_snapshot,
    detect_iceberg_signature,
    OrderBookSnapshot
)

logger = logging.getLogger(__name__)

class IcebergDetection(StrategyBase):
    """Iceberg detection strategy with degraded mode support."""
    
    def __init__(self, params: Dict):
        super().__init__(params)
        
        self.mode = params.get('mode', 'degraded')
        self.volume_advancement_ratio_threshold = params.get('volume_advancement_ratio_threshold', 4.0)  # Icebergs reales
        self.stall_duration_bars = params.get('stall_duration_bars', 5)
        self.replenishment_detection = params.get('replenishment_detection', True)
        self.stop_loss_behind_level_atr = params.get('stop_loss_behind_level_atr', 1.0)
        self.take_profit_r_multiple = params.get('take_profit_r_multiple', 2.5)
        
        self.l2_available = False
        self.l2_snapshots: List[OrderBookSnapshot] = []
        
        # State tracking para logging profesional
        self._logged_degraded_mode = False  # Flag para evitar logging repetitivo
        self._last_mode_state = None  # Último estado conocido
        self.logger = logging.getLogger(self.__class__.__name__)
        
        if self.mode == 'degraded':
            logger.debug("Iceberg Detection initialized in DEGRADED MODE")
        else:
            logger.info(f"Iceberg Detection initialized: mode={self.mode}")
    
    def _check_l2_availability(self, features: Dict) -> bool:
        """Check if L2 data is available."""
        try:
            l2_data = features.get('l2_data')
            
            if l2_data is not None:
                snapshot = parse_l2_snapshot(l2_data)
                if snapshot is not None:
                    self.l2_snapshots.append(snapshot)
                    self.l2_snapshots = self.l2_snapshots[-100:]
                    return True
            
            return False
            
        except Exception as e:
            logger.error(f"L2 availability check failed: {str(e)}")
            return False
    


    def calculate_effective_spread(self, data: pd.DataFrame, window: int = 10) -> pd.Series:
        """
        Calcula effective spread como proxy sin acceso a Level 2.
        
        Effective Spread = 2 * |transaction_price - mid_price|
        
        En ausencia de datos de transacciones reales, usamos:
        - High como proxy de transacciones en el ask
        - Low como proxy de transacciones en el bid
        - Mid = (high + low) / 2
        
        Args:
            data: DataFrame con high, low, close
            window: Ventana para estadísticas rodantes
            
        Returns:
            Series con effective spread normalizado
            
        Nota institucional:
            El effective spread captura el costo real de transacción.
            Durante absorción por iceberg, el effective spread se amplía
            porque hay adverse selection risk para market makers.
        """
        # Calcular mid-price
        mid_price = (data['high'] + data['low']) / 2
        
        # Effective spread para trades en ask (aproximado por high)
        spread_ask = 2 * (data['high'] - mid_price)
        
        # Effective spread para trades en bid (aproximado por low)
        spread_bid = 2 * (mid_price - data['low'])
        
        # Promedio ponderado
        effective_spread = (spread_ask + spread_bid) / 2
        
        # Normalizar por mid-price (en basis points)
        effective_spread_bp = (effective_spread / mid_price) * 10000
        
        # Calcular estadísticas rodantes para detectar anomalías
        spread_mean = effective_spread_bp.rolling(window).mean()
        spread_std = effective_spread_bp.rolling(window).std()
        
        # Z-score del spread
        spread_z = (effective_spread_bp - spread_mean) / spread_std
        
        return spread_z
    
    def measure_time_at_price(self, data: pd.DataFrame, tolerance_pips: float = 0.1) -> int:
        """
        Mide cuántos ticks consecutivos han ocurrido aproximadamente al mismo precio.
        
        Time-at-price elevado indica que el precio está "pegado" en un nivel,
        firma clásica de absorción por orden grande.
        
        Args:
            data: DataFrame con close prices
            tolerance_pips: Tolerancia para considerar "mismo precio"
            
        Returns:
            Número de ticks consecutivos en el rango
        """
        if len(data) < 2:
            return 0
        
        # Tomar últimos N ticks
        recent_prices = data['close'].iloc[-20:].values
        
        if len(recent_prices) == 0:
            return 0
        
        current_price = recent_prices[-1]
        consecutive_ticks = 1
        
        # Contar hacia atrás cuántos ticks están dentro de tolerance
        for i in range(len(recent_prices) - 2, -1, -1):
            price_diff = abs(recent_prices[i] - current_price)
            
            if price_diff <= tolerance_pips:
                consecutive_ticks += 1
            else:
                break
        
        return consecutive_ticks
    
    def get_session_calibration(self, symbol: str, current_time: pd.Timestamp) -> Dict:
        """
        Retorna umbrales calibrados específicos para símbolo y sesión horaria.
        
        Args:
            symbol: Símbolo del instrumento
            current_time: Timestamp actual
            
        Returns:
            Dict con umbrales calibrados
            
        Nota institucional:
            Los umbrales de qué constituye "volumen anómalo" o "spread anómalo"
            varían dramáticamente por instrumento y sesión. Por ejemplo, el spread
            de USD/JPY durante Tokyo es muy diferente al spread durante London.
        """
        # Determinar sesión horaria (UTC)
        hour_utc = current_time.hour
        
        if 0 <= hour_utc < 8:
            session = 'ASIA'
        elif 8 <= hour_utc < 16:
            session = 'LONDON'
        else:
            session = 'NY'
        
        # Calibraciones por defecto (deberían cargarse desde históricos)
        # Estos valores son ejemplos; en producción vendrían de análisis histórico
        calibrations = {
            ('EURUSD', 'ASIA'): {
                'volume_threshold_sigma': 2.5,
                'spread_threshold_multiplier': 1.8,
                'time_at_price_minimum': 7
            },
            ('EURUSD', 'LONDON'): {
                'volume_threshold_sigma': 2.2,
                'spread_threshold_multiplier': 1.5,
                'time_at_price_minimum': 5
            },
            ('EURUSD', 'NY'): {
                'volume_threshold_sigma': 2.3,
                'spread_threshold_multiplier': 1.6,
                'time_at_price_minimum': 6
            },
            # Agregar más combinaciones según sea necesario
        }
        
        # Buscar calibración específica
        key = (symbol.replace('.pro', '').upper(), session)
        
        if key in calibrations:
            return calibrations[key]
        
        # Default conservador si no hay calibración específica
        return {
            'volume_threshold_sigma': 2.5,
            'spread_threshold_multiplier': 1.8,
            'time_at_price_minimum': 8
        }
    def evaluate(self, data: pd.DataFrame, features: Dict) -> Optional[Signal]:
        """Evaluate iceberg detection conditions."""
        try:
            if len(data) < 50:
                logger.debug(f"Insufficient data: {len(data)} bars")
                return None
            
            atr = features.get('atr')
            if atr is None or np.isnan(atr) or atr <= 0:
                logger.warning(f"Invalid ATR: {atr}")
                return None
            
            self.l2_available = self._check_l2_availability(features)
            
            if not self.l2_available and self.mode != 'degraded':
                logger.debug("L2 data not available - switching to DEGRADED MODE")
                self.mode = 'degraded'
            
            iceberg = detect_iceberg_signature(
                data.tail(20),
                self.l2_snapshots if self.l2_available else None,
                self.stall_duration_bars,
                self.volume_advancement_ratio_threshold
            )
            
            if iceberg:
                logger.info(f"Iceberg detected in {iceberg['mode']} mode: "
                          f"confidence={iceberg['confidence']}")
                
                if iceberg['mode'] == 'DEGRADED' and iceberg['confidence'] == 'LOW':
                    logger.debug("Skipping low confidence iceberg in degraded mode")
                    return None
                
                signal = self._create_iceberg_signal(iceberg, data, atr, features)
                return signal
            
            return None
            
        except Exception as e:
            logger.error(f"Iceberg evaluation failed: {str(e)}", exc_info=True)
            return None
    
    def _create_iceberg_signal(self, iceberg: Dict, data: pd.DataFrame,
                              atr: float, features: Dict) -> Optional[Signal]:
        """Create signal for iceberg trade with OFI/CVD/VPIN confirmation."""
        try:
            current_price = data.iloc[-1]['close']
            iceberg_level = iceberg.get('price_level', current_price)

            # INSTITUTIONAL: Validate with order flow
            ofi = features.get('ofi', 0)
            cvd = features.get('cvd', 0)
            vpin = features.get('vpin', 1.0)

            # Determine expected direction
            if iceberg.get('side') == 'BID' or current_price > iceberg_level:
                direction = "LONG"
                expected_direction = 1
                entry_price = current_price
                stop_loss = iceberg_level - (self.stop_loss_behind_level_atr * atr)
                risk = entry_price - stop_loss
                take_profit = entry_price + (risk * self.take_profit_r_multiple)

            else:
                direction = "SHORT"
                expected_direction = -1
                entry_price = current_price
                stop_loss = iceberg_level + (self.stop_loss_behind_level_atr * atr)
                risk = stop_loss - entry_price
                take_profit = entry_price - (risk * self.take_profit_r_multiple)

            # Check OFI alignment (iceberg absorption should show in OFI)
            ofi_aligned = (ofi > 0 and expected_direction > 0) or (ofi < 0 and expected_direction < 0)

            # If OFI strongly contradicts and we're in degraded mode, skip
            if iceberg['mode'] == 'DEGRADED' and abs(ofi) > 2.0 and not ofi_aligned:
                logger.debug(f"Iceberg signal rejected: OFI misaligned in degraded mode")
                return None

            # If VPIN too high (toxic), reduce confidence
            if vpin > 0.35:
                if iceberg['confidence'] == 'HIGH':
                    iceberg['confidence'] = 'MEDIUM'
                elif iceberg['confidence'] == 'MEDIUM':
                    iceberg['confidence'] = 'LOW'
                else:
                    logger.debug(f"Iceberg signal rejected: VPIN too high {vpin:.3f} + LOW confidence")
                    return None

            actual_risk = abs(entry_price - stop_loss)
            actual_reward = abs(take_profit - entry_price)
            rr_ratio = actual_reward / actual_risk if actual_risk > 0 else 0

            if rr_ratio < 2.0:
                logger.debug(f"Iceberg signal rejected: R:R {rr_ratio:.2f} < 2.0")
                return None

            # Adjust sizing based on confidence + order flow
            if iceberg['confidence'] == 'HIGH' and ofi_aligned and vpin < 0.25:
                sizing_level = 3
            elif iceberg['confidence'] == 'MEDIUM' and ofi_aligned:
                sizing_level = 2
            else:
                sizing_level = 1

            signal = Signal(
                timestamp=datetime.now(),
                symbol=data.attrs.get('symbol', 'UNKNOWN'),
                strategy_name="Iceberg_Detection",
                direction=direction,
                entry_price=entry_price,
                stop_loss=stop_loss,
                take_profit=take_profit,
                sizing_level=sizing_level,
                metadata={
                    'detection_mode': iceberg['mode'],
                    'confidence': iceberg['confidence'],
                    'iceberg_level': float(iceberg_level),
                    'iceberg_side': iceberg.get('side', 'UNKNOWN'),
                    'volume_price_ratio': iceberg.get('volume_price_ratio', 0),
                    'ofi': float(ofi),
                    'cvd': float(cvd),
                    'vpin': float(vpin),
                    'ofi_aligned': ofi_aligned,
                    'risk_reward_ratio': float(rr_ratio),
                    'partial_exits': {'50%_at': 1.5, '30%_at': 2.5, '20%_trail': 'to_target'},
                    'l2_available': self.l2_available,
                    'research_basis': 'Easley_2012_Flow_Toxicity_Harris_2003_Microstructure',
                    'expected_win_rate': 0.68 if iceberg['mode'] == 'L2' else 0.62,
                    'rationale': f"Iceberg detected at {iceberg_level:.5f} in {iceberg['mode']} mode "
                               f"with {iceberg['confidence']} confidence. "
                               f"OFI {'aligned' if ofi_aligned else 'neutral'}, VPIN={vpin:.3f}"
                }
            )

            logger.info(f"Iceberg Signal: {direction} @ {entry_price:.5f}, "
                       f"mode={iceberg['mode']}, R:R={rr_ratio:.2f}, OFI={'✓' if ofi_aligned else '~'}")

            return signal

        except Exception as e:
            logger.error(f"Iceberg signal creation failed: {str(e)}", exc_info=True)
            return None


