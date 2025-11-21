"""
Delta volume and trade classification module for IDP pattern detection.

Based on:
- Kyle, A.S. (1985). "Continuous Auctions and Insider Trading."
- Admati & Pfleiderer (1988). "A Theory of Intraday Patterns."
"""

import pandas as pd
import numpy as np
from typing import Dict, Tuple, Optional, List
from dataclasses import dataclass
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

@dataclass
class IDPPhase:
    """Represents a phase in the Inducement-Distribution Pattern."""
    phase_type: str
    start_timestamp: datetime
    end_timestamp: Optional[datetime]
    start_price: float
    end_price: Optional[float]
    volume_profile: Dict[str, float]
    characteristics: Dict[str, any]
    is_complete: bool = False
    
    @property
    def duration_bars(self) -> int:
        if self.end_timestamp and self.start_timestamp:
            return int((self.end_timestamp - self.start_timestamp).seconds / 60)
        return 0
    
    @property
    def price_movement(self) -> float:
        if self.end_price:
            return self.end_price - self.start_price
        return 0.0

def classify_trades(data: pd.DataFrame) -> pd.DataFrame:
    """Classify trades using Lee-Ready algorithm."""
    try:
        reference_price = (data['open'] + data['high'] + data['low']) / 3
        trade_signs = np.where(data['close'] > reference_price, 1, -1)
        
        exact_matches = data['close'] == reference_price
        if exact_matches.any():
            price_changes = data['close'].diff()
            trade_signs[exact_matches] = np.sign(price_changes[exact_matches])
        
        data['trade_sign'] = trade_signs
        data['buy_volume'] = data['tick_volume'].where(data['trade_sign'] > 0, 0)
        data['sell_volume'] = data['tick_volume'].where(data['trade_sign'] < 0, 0)
        data['delta_volume'] = data['buy_volume'] - data['sell_volume']
        data['cumulative_delta'] = data['delta_volume'].cumsum()
        
        return data
    except Exception as e:
        logger.error(f"Trade classification failed: {str(e)}", exc_info=True)
        return data

def detect_sweep(data: pd.DataFrame, level: float, level_type: str,
                penetration_min: float = 5, penetration_max: float = 20,
                pip_value: float = 0.0001) -> Optional[Dict]:
    """Detect level sweep for inducement phase."""
    try:
        for i in range(len(data) - 1):
            bar = data.iloc[i]
            
            if bar['high'] > level:
                penetration = (bar['high'] - level) / pip_value
                if penetration_min <= penetration <= penetration_max:
                    if bar['close'] < level or data.iloc[i + 1]['close'] < level:
                        volume_spike = bar['tick_volume'] / data['tick_volume'].mean()
                        if volume_spike >= 2.5:
                            return {
                                'type': 'UPWARD',
                                'timestamp': bar['timestamp'],
                                'level': level,
                                'penetration_pips': penetration,
                                'volume_spike': volume_spike,
                                'delta_volume': bar.get('delta_volume', 0),
                                'recovered': bar['close'] < level
                            }
            
            elif bar['low'] < level:
                penetration = (level - bar['low']) / pip_value
                if penetration_min <= penetration <= penetration_max:
                    if bar['close'] > level or data.iloc[i + 1]['close'] > level:
                        volume_spike = bar['tick_volume'] / data['tick_volume'].mean()
                        if volume_spike >= 2.5:
                            return {
                                'type': 'DOWNWARD',
                                'timestamp': bar['timestamp'],
                                'level': level,
                                'penetration_pips': penetration,
                                'volume_spike': volume_spike,
                                'delta_volume': bar.get('delta_volume', 0),
                                'recovered': bar['close'] > level
                            }
        return None
    except Exception as e:
        logger.error(f"Sweep detection failed: {str(e)}")
        return None

def detect_distribution_phase(data: pd.DataFrame, start_idx: int,
                             min_bars: int = 3, max_bars: int = 8) -> Optional[Dict]:
    """Detect distribution phase after inducement."""
    try:
        if start_idx + max_bars > len(data):
            return None
        
        for window_size in range(min_bars, min(max_bars + 1, len(data) - start_idx)):
            distribution_data = data.iloc[start_idx:start_idx + window_size]
            ranges = distribution_data['high'] - distribution_data['low']
            avg_range = ranges.mean()
            prior_avg_range = (data.iloc[max(0, start_idx - 20):start_idx]['high'] - 
                             data.iloc[max(0, start_idx - 20):start_idx]['low']).mean()
            
            if avg_range < prior_avg_range * 0.7:
                total_delta = distribution_data['delta_volume'].sum()
                price_change = distribution_data.iloc[-1]['close'] - distribution_data.iloc[0]['close']
                
                if abs(total_delta) > distribution_data['tick_volume'].sum() * 0.3:
                    if abs(price_change) < avg_range * 2:
                        return {
                            'start_idx': start_idx,
                            'end_idx': start_idx + window_size - 1,
                            'duration_bars': window_size,
                            'avg_range': avg_range,
                            'compression_ratio': avg_range / prior_avg_range,
                            'total_delta': total_delta,
                            'price_change': price_change,
                            'absorption_detected': True,
                            'distribution_type': 'ACCUMULATION' if total_delta > 0 else 'DISTRIBUTION'
                        }
        return None
    except Exception as e:
        logger.error(f"Distribution detection failed: {str(e)}")
        return None

def detect_displacement_phase(data: pd.DataFrame, start_idx: int,
                             min_velocity_pips_per_min: float = 7,
                             min_displacement_atr: float = 1.5,
                             indicador de rango: float = None, pip_value: float = 0.0001) -> Optional[Dict]:
    """
    Detect displacement phase in IDP pattern.

    âš ï¸ indicador de rango USAGE: TYPE B - DESCRIPTIVE METRIC ONLY âš ï¸
    indicador de rango is used here for DISPLACEMENT DETECTION (pattern identification), NOT risk sizing.
    displacement_atr ratio measures displacement strength relative to normal volatility.
    This is a legitimate use case per PLAN OMEGA.

    Args:
        data: OHLCV DataFrame
        start_idx: Starting index for detection
        min_velocity_pips_per_min: Minimum velocity in pips/minute (default: 7)
        min_displacement_atr: Minimum displacement/indicador de rango ratio (default: 1.5)
        indicador de rango: Average True Range for normalization (TYPE B - descriptive metric only)
        pip_value: Pip value for conversion (default: 0.0001)

    Returns:
        Dict with displacement info if detected, None otherwise
    """
    try:
        if start_idx >= len(data) - 1:
            return None
        
        for i in range(start_idx, min(start_idx + 5, len(data))):
            bar = data.iloc[i]
            bar_move = abs(bar['close'] - bar['open'])
            bar_velocity_pips = (bar_move / pip_value)
            
            if bar_velocity_pips >= min_velocity_pips_per_min:
                if i + 1 < len(data):
                    next_bar = data.iloc[i + 1]
                    if ((bar['close'] > bar['open'] and next_bar['close'] > bar['close']) or
                        (bar['close'] < bar['open'] and next_bar['close'] < bar['close'])):
                        
                        if indicador de rango and indicador de rango > 0:
                            displacement_atr = bar_move / indicador de rango
                            if displacement_atr >= min_displacement_atr:
                                return {
                                    'timestamp': bar['timestamp'],
                                    'bar_idx': i,
                                    'direction': 'UP' if bar['close'] > bar['open'] else 'DOWN',
                                    'velocity_pips_per_min': bar_velocity_pips,
                                    'displacement_atr': displacement_atr,
                                    'bar_move': bar_move,
                                    'volume': bar['tick_volume'],
                                    'continuation_confirmed': True
                                }
        return None
    except Exception as e:
        logger.error(f"Displacement detection failed: {str(e)}")
        return None

def identify_idp_pattern(data: pd.DataFrame, levels: List[float],
                        indicador de rango: float, params: Dict) -> Optional[Dict]:
    """
    Identify complete 3-phase IDP (Inducement-Distribution-Placement) pattern.

    âš ï¸ indicador de rango USAGE: TYPE B - DESCRIPTIVE METRIC ONLY âš ï¸
    indicador de rango is used for DISPLACEMENT DETECTION (pattern identification), NOT risk sizing.
    Passed to detect_displacement_phase() for displacement strength normalization.
    This is a legitimate use case per PLAN OMEGA.

    Args:
        data: OHLCV DataFrame
        levels: List of price levels to check for sweeps
        indicador de rango: Average True Range for normalization (TYPE B - descriptive metric only)
        params: Dict with detection parameters

    Returns:
        Dict with complete IDP pattern if detected, None otherwise
    """
    try:
        data = classify_trades(data.copy())
        
        for level in levels:
            sweep = detect_sweep(
                data.tail(20), level, 'swing',
                params.get('penetration_pips_min', 5),
                params.get('penetration_pips_max', 20)
            )
            
            if sweep:
                sweep_idx = data[data['timestamp'] == sweep['timestamp']].index[0]
                distribution = detect_distribution_phase(
                    data, sweep_idx + 1,
                    params.get('distribution_range_bars_min', 3),
                    params.get('distribution_range_bars_max', 8)
                )
                
                if distribution:
                    displacement = detect_displacement_phase(
                        data, distribution['end_idx'] + 1,
                        params.get('displacement_velocity_pips_per_minute', 7),
                        1.5, indicador de rango
                    )
                    
                    if displacement:
                        return {
                            'pattern_type': 'IDP',
                            'inducement': sweep,
                            'distribution': distribution,
                            'displacement': displacement,
                            'expected_direction': displacement['direction'],
                            'level_swept': level,
                            'confidence': calculate_idp_confidence(sweep, distribution, displacement)
                        }
        return None
    except Exception as e:
        logger.error(f"IDP pattern identification failed: {str(e)}")
        return None

def calculate_idp_confidence(sweep: Dict, distribution: Dict, displacement: Dict) -> str:
    """Calculate IDP pattern confidence."""
    score = 0
    
    if sweep['volume_spike'] > 3.0:
        score += 2
    elif sweep['volume_spike'] > 2.5:
        score += 1
    
    if distribution['compression_ratio'] < 0.5:
        score += 2
    elif distribution['compression_ratio'] < 0.7:
        score += 1
    
    if distribution['absorption_detected']:
        score += 2
    
    if displacement['velocity_pips_per_min'] > 10:
        score += 2
    elif displacement['velocity_pips_per_min'] > 7:
        score += 1
    
    if displacement['displacement_atr'] > 2.0:
        score += 2
    elif displacement['displacement_atr'] > 1.5:
        score += 1
    
    if score >= 8:
        return 'HIGH'
    elif score >= 5:
        return 'MEDIUM'
    else:
        return 'LOW'
