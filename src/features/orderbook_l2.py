"""
Level 2 order book analysis module for iceberg detection.

Note: Operates in degraded mode when L2 data unavailable.

Based on:
- Biais, Hillion & Spatt (1995). "An Empirical Analysis of the Limit Order Book."
- Hautsch & Huang (2012). "The Market Impact of a Limit Order."
"""

import pandas as pd
import numpy as np
from typing import Dict, Optional, List, Tuple
from dataclasses import dataclass
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

@dataclass
class OrderBookSnapshot:
    """Represents L2 order book snapshot."""
    timestamp: datetime
    bids: List[Tuple[float, float]]
    asks: List[Tuple[float, float]]
    mid_price: float
    spread: float
    total_bid_volume: float
    total_ask_volume: float
    imbalance: float
    
    @property
    def best_bid(self) -> float:
        return self.bids[0][0] if self.bids else 0
    
    @property
    def best_ask(self) -> float:
        return self.asks[0][0] if self.asks else 0

def parse_l2_snapshot(l2_data: Optional[str]) -> Optional[OrderBookSnapshot]:
    """Parse L2 data if available."""
    try:
        if l2_data is None:
            logger.debug("No L2 data available - operating in degraded mode")
            return None
        
        logger.warning("L2 parsing not implemented - degraded mode active")
        return None
        
    except Exception as e:
        logger.error(f"L2 parsing failed: {str(e)}")
        return None

def detect_iceberg_signature(price_data: pd.DataFrame,
                            l2_snapshots: Optional[List[OrderBookSnapshot]] = None,
                            stall_duration_bars: int = 5,
                            volume_price_ratio_threshold: float = 15.0) -> Optional[Dict]:
    """Detect iceberg order signatures."""
    try:
        if l2_snapshots is None or len(l2_snapshots) == 0:
            logger.debug("Iceberg detection in DEGRADED MODE")
            
            for i in range(len(price_data) - stall_duration_bars):
                window = price_data.iloc[i:i + stall_duration_bars]
                
                price_range = window['high'].max() - window['low'].min()
                avg_range = (price_data['high'] - price_data['low']).mean()
                total_volume = window['tick_volume'].sum()
                avg_volume = price_data['tick_volume'].mean() * stall_duration_bars
                
                if price_range < avg_range * 0.3:
                    if total_volume > avg_volume * 2:
                        if price_range > 0:
                            vp_ratio = total_volume / (price_range * 10000)
                            
                            if vp_ratio >= volume_price_ratio_threshold:
                                return {
                                    'mode': 'DEGRADED',
                                    'confidence': 'LOW',
                                    'timestamp': window.iloc[0]['timestamp'],
                                    'price_level': window['close'].mean(),
                                    'stall_bars': stall_duration_bars,
                                    'volume_price_ratio': vp_ratio,
                                    'total_volume': total_volume,
                                    'price_range': price_range,
                                    'warning': 'Operating without L2 data'
                                }
            
            return None
            
        else:
            logger.info("Iceberg detection in FULL MODE with L2 data")
            
            for i, snapshot in enumerate(l2_snapshots[:-1]):
                next_snapshot = l2_snapshots[i + 1]
                
                for level_idx, (price, size) in enumerate(snapshot.bids[:5]):
                    matching_level = None
                    for next_price, next_size in next_snapshot.bids[:5]:
                        if abs(next_price - price) < 0.00001:
                            matching_level = (next_price, next_size)
                            break
                    
                    if matching_level:
                        if abs(matching_level[1] - size) < size * 0.1:
                            return {
                                'mode': 'FULL',
                                'confidence': 'HIGH',
                                'side': 'BID',
                                'price_level': price,
                                'detected_size': size,
                                'timestamp': snapshot.timestamp,
                                'replenishment_detected': True
                            }
                
                for level_idx, (price, size) in enumerate(snapshot.asks[:5]):
                    matching_level = None
                    for next_price, next_size in next_snapshot.asks[:5]:
                        if abs(next_price - price) < 0.00001:
                            matching_level = (next_price, next_size)
                            break
                    
                    if matching_level:
                        if abs(matching_level[1] - size) < size * 0.1:
                            return {
                                'mode': 'FULL',
                                'confidence': 'HIGH',
                                'side': 'ASK',
                                'price_level': price,
                                'detected_size': size,
                                'timestamp': snapshot.timestamp,
                                'replenishment_detected': True
                            }
            
            return None
            
    except Exception as e:
        logger.error(f"Iceberg detection failed: {str(e)}", exc_info=True)
        return None

def calculate_book_pressure(snapshot: OrderBookSnapshot,
                          depth_levels: int = 5) -> Tuple[float, float]:
    """Calculate bid/ask pressure from order book."""
    try:
        if snapshot is None:
            return 0.0, 0.0
        
        bid_pressure = 0.0
        ask_pressure = 0.0
        
        for i, (price, size) in enumerate(snapshot.bids[:depth_levels]):
            distance = abs(snapshot.mid_price - price)
            weight = 1.0 / (1.0 + distance * 1000)
            bid_pressure += size * weight
        
        for i, (price, size) in enumerate(snapshot.asks[:depth_levels]):
            distance = abs(price - snapshot.mid_price)
            weight = 1.0 / (1.0 + distance * 1000)
            ask_pressure += size * weight
        
        return bid_pressure, ask_pressure
        
    except Exception as e:
        logger.error(f"Book pressure calculation failed: {str(e)}")
        return 0.0, 0.0