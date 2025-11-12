"""
Inducement-Distribution Pattern (IDP) Strategy.

Complex 3-phase pattern identifying institutional manipulation
and subsequent directional moves.
"""

import pandas as pd
import numpy as np
from typing import Dict, Optional, List
from datetime import datetime
import logging

from strategies.strategy_base import StrategyBase, Signal
from features.delta_volume import (
    classify_trades,
    identify_idp_pattern,
    IDPPhase
)

logger = logging.getLogger(__name__)

class IDPInducement(StrategyBase):
    """IDP strategy detecting institutional stop hunts."""
    
    def __init__(self, params: Dict):
        super().__init__(params)
        
        self.penetration_pips_min = params.get('penetration_pips_min', 5)
        self.penetration_pips_max = params.get('penetration_pips_max', 20)
        self.volume_multiplier = params.get('volume_multiplier', 2.5)
        self.distribution_range_bars_min = params.get('distribution_range_bars_min', 3)
        self.distribution_range_bars_max = params.get('distribution_range_bars_max', 8)
        self.displacement_velocity_pips_per_minute = params.get('displacement_velocity_pips_per_minute', 7)
        self.stop_loss_beyond_inducement = params.get('stop_loss_beyond_inducement', True)
        self.take_profit_r_multiple = params.get('take_profit_r_multiple', 3.0)
        
        self.active_patterns: List[Dict] = []
        self.completed_patterns: List[Dict] = []
        self.logger = logging.getLogger(self.__class__.__name__)
        
        logger.info(f"IDP Inducement initialized: penetration={self.penetration_pips_min}-"
                   f"{self.penetration_pips_max} pips")
    
    def _identify_key_levels(self, data: pd.DataFrame) -> List[float]:
        """Identify key levels for potential sweeps."""
        levels = []
        
        try:
            lookback = min(100, len(data))
            recent_data = data.tail(lookback)
            
            for i in range(10, len(recent_data) - 10):
                if (recent_data.iloc[i]['high'] > recent_data.iloc[i-5:i]['high'].max() and
                    recent_data.iloc[i]['high'] > recent_data.iloc[i+1:i+6]['high'].max()):
                    levels.append(recent_data.iloc[i]['high'])
                
                if (recent_data.iloc[i]['low'] < recent_data.iloc[i-5:i]['low'].min() and
                    recent_data.iloc[i]['low'] < recent_data.iloc[i+1:i+6]['low'].min()):
                    levels.append(recent_data.iloc[i]['low'])
            
            current_price = data.iloc[-1]['close']
            for i in range(-5, 6):
                round_level = round(current_price * 1000) / 1000 + (i * 0.0010)
                levels.append(round_level)
            
            levels = sorted(list(set(levels)))
            levels = [l for l in levels if abs(l - current_price) < 0.0050]
            
            return levels
            
        except Exception as e:
            logger.error(f"Level identification failed: {str(e)}")
            return []
    
    def evaluate(self, data: pd.DataFrame, features: Dict) -> Optional[Signal]:
        """Evaluate IDP pattern conditions."""
        try:
            if len(data) < 100:
                logger.debug(f"Insufficient data: {len(data)} bars")
                return None
            
            atr = features.get('atr')
            if atr is None or np.isnan(atr) or atr <= 0:
                logger.warning(f"Invalid ATR: {atr}")
                return None
            
            key_levels = self._identify_key_levels(data)
            
            if not key_levels:
                logger.debug("No key levels identified")
                return None
            
            pattern = identify_idp_pattern(
                data.tail(50),
                key_levels,
                atr,
                {
                    'penetration_pips_min': self.penetration_pips_min,
                    'penetration_pips_max': self.penetration_pips_max,
                    'distribution_range_bars_min': self.distribution_range_bars_min,
                    'distribution_range_bars_max': self.distribution_range_bars_max,
                    'displacement_velocity_pips_per_minute': self.displacement_velocity_pips_per_minute
                }
            )
            
            if pattern and pattern['confidence'] in ['HIGH', 'MEDIUM']:
                displacement_time = pattern['displacement']['timestamp']
                current_time = data.iloc[-1]['timestamp']
                
                time_diff = (current_time - displacement_time).seconds / 60
                
                if time_diff <= 3:
                    signal = self._create_idp_signal(pattern, data, atr, features)
                    
                    if signal:
                        self.completed_patterns.append(pattern)
                        return signal
            
            return None
            
        except Exception as e:
            logger.error(f"IDP evaluation failed: {str(e)}", exc_info=True)
            return None
    
    def _create_idp_signal(self, pattern: Dict, data: pd.DataFrame,
                          atr: float, features: Dict) -> Optional[Signal]:
        """Create signal from complete IDP pattern."""
        try:
            current_price = data.iloc[-1]['close']
            
            if pattern['displacement']['direction'] == 'UP':
                direction = "LONG"
                entry_price = current_price
                
                if self.stop_loss_beyond_inducement:
                    inducement_low = pattern['level_swept'] - (self.penetration_pips_max * 0.0001)
                    stop_loss = min(inducement_low, entry_price - 2 * atr)
                else:
                    stop_loss = entry_price - 1.5 * atr
                
                risk = entry_price - stop_loss
                take_profit = entry_price + (risk * self.take_profit_r_multiple)
                
            else:
                direction = "SHORT"
                entry_price = current_price
                
                if self.stop_loss_beyond_inducement:
                    inducement_high = pattern['level_swept'] + (self.penetration_pips_max * 0.0001)
                    stop_loss = max(inducement_high, entry_price + 2 * atr)
                else:
                    stop_loss = entry_price + 1.5 * atr
                
                risk = stop_loss - entry_price
                take_profit = entry_price - (risk * self.take_profit_r_multiple)
            
            actual_risk = abs(entry_price - stop_loss)
            actual_reward = abs(take_profit - entry_price)
            rr_ratio = actual_reward / actual_risk if actual_risk > 0 else 0
            
            if rr_ratio < 2.5:
                logger.debug(f"IDP signal rejected: R:R {rr_ratio:.2f} < 2.5")
                return None
            
            if pattern['confidence'] == 'HIGH':
                sizing_level = 4
            elif pattern['confidence'] == 'MEDIUM':
                sizing_level = 3
            else:
                sizing_level = 2
            
            signal = Signal(
                timestamp=datetime.now(),
                symbol=data.attrs.get('symbol', 'UNKNOWN'),
                strategy_name="IDP_Inducement",
                direction=direction,
                entry_price=entry_price,
                stop_loss=stop_loss,
                take_profit=take_profit,
                sizing_level=sizing_level,
                metadata={
                    'pattern_confidence': pattern['confidence'],
                    'inducement_level': float(pattern['level_swept']),
                    'inducement_type': pattern['inducement']['type'],
                    'inducement_penetration': float(pattern['inducement']['penetration_pips']),
                    'inducement_volume_spike': float(pattern['inducement']['volume_spike']),
                    'distribution_bars': pattern['distribution']['duration_bars'],
                    'distribution_type': pattern['distribution']['distribution_type'],
                    'distribution_compression': float(pattern['distribution']['compression_ratio']),
                    'displacement_velocity': float(pattern['displacement']['velocity_pips_per_min']),
                    'displacement_atr': float(pattern['displacement']['displacement_atr']),
                    'risk_reward_ratio': float(rr_ratio),
                    'rationale': f"Complete IDP pattern: {pattern['inducement']['type']} sweep of "
                               f"{pattern['level_swept']:.5f} with {pattern['confidence']} confidence."
                }
            )
            
            logger.info(f"IDP Signal: {direction} @ {entry_price:.5f}, "
                       f"confidence={pattern['confidence']}, R:R={rr_ratio:.2f}")
            
            return signal
            
        except Exception as e:
            logger.error(f"IDP signal creation failed: {str(e)}", exc_info=True)
            return None
