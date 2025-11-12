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

def parse_l2_snapshot(l2_data) -> Optional[OrderBookSnapshot]:
    """
    Parse Level 2 orderbook data from MT5.

    Args:
        l2_data: Tuple of BookInfo entries from mt5.market_book_get()
                 Each entry has: type (0=bid, 1=ask), price, volume, volume_dbl

    Returns:
        OrderBookSnapshot with parsed bid/ask levels, or None if unavailable

    Research: Biais, Hillion & Spatt (1995), Hautsch & Huang (2012)
    """
    try:
        if l2_data is None or len(l2_data) == 0:
            logger.debug("No L2 data available - operating in degraded mode")
            return None

        # Separate bids and asks
        bids = []
        asks = []

        for entry in l2_data:
            # entry.type: 0 = ORDER_TYPE_BUY (bid), 1 = ORDER_TYPE_SELL (ask)
            price = float(entry.price)
            volume = float(entry.volume_dbl)  # Use precise double value

            if entry.type == 0:  # Bid
                bids.append((price, volume))
            else:  # Ask (type == 1)
                asks.append((price, volume))

        # Sort: bids descending (best bid first), asks ascending (best ask first)
        bids.sort(reverse=True, key=lambda x: x[0])
        asks.sort(key=lambda x: x[0])

        if not bids or not asks:
            logger.warning("L2 data incomplete: missing bids or asks")
            return None

        # Calculate metrics
        best_bid = bids[0][0]
        best_ask = asks[0][0]
        mid_price = (best_bid + best_ask) / 2.0
        spread = best_ask - best_bid

        total_bid_volume = sum(vol for _, vol in bids)
        total_ask_volume = sum(vol for _, vol in asks)

        # Imbalance: positive = more bid pressure, negative = more ask pressure
        if total_bid_volume + total_ask_volume > 0:
            imbalance = (total_bid_volume - total_ask_volume) / (total_bid_volume + total_ask_volume)
        else:
            imbalance = 0.0

        snapshot = OrderBookSnapshot(
            timestamp=datetime.now(),
            bids=bids,
            asks=asks,
            mid_price=mid_price,
            spread=spread,
            total_bid_volume=total_bid_volume,
            total_ask_volume=total_ask_volume,
            imbalance=imbalance
        )

        logger.debug(f"L2 snapshot parsed: {len(bids)} bids, {len(asks)} asks, "
                    f"spread={spread:.5f}, imbalance={imbalance:.3f}")

        return snapshot

    except Exception as e:
        logger.error(f"L2 parsing failed: {str(e)}", exc_info=True)
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