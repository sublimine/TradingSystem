"""
Liquidity Sweep Detection Strategy

Identifies instances where price briefly penetrates technical levels with anomalous
volume before reversing, indicating institutional absorption of retail stop orders.
"""

import numpy as np
import pandas as pd
from typing import List, Dict, Optional, Tuple
from datetime import datetime, timedelta

from .strategy_base import StrategyBase, Signal


class LiquiditySweepStrategy(StrategyBase):
    """
    Strategy that detects liquidity sweeps at critical technical levels.
    
    Entry occurs after confirming sweep characteristics including penetration depth,
    volume anomaly, reversal velocity, order book imbalance, and order flow toxicity.
    """
    
    def __init__(self, config: Dict):
        """
        Initialize liquidity sweep strategy.
        
        Required config parameters:
            - lookback_periods: List of periods for swing point identification [24h, 48h, 72h]
            - proximity_threshold: Distance to level to activate monitoring (pips)
            - penetration_min: Minimum penetration beyond level (pips)
            - penetration_max: Maximum penetration beyond level (pips)
            - volume_threshold_multiplier: Volume must exceed this multiple of average
            - reversal_velocity_min: Minimum speed of price return (pips/minute)
            - imbalance_threshold: Minimum order book imbalance during sweep
            - vpin_threshold: Minimum VPIN level indicating toxic flow
            - min_confirmation_score: Minimum total confirmation score (0-5)
        """
        super().__init__(config)
        
        self.lookback_periods = config.get('lookback_periods', [1440, 2880, 4320])
        self.proximity_threshold = config.get('proximity_threshold', 10)
        self.penetration_min = config.get('penetration_min', 3)
        self.penetration_max = config.get('penetration_max', 15)
        self.volume_threshold = config.get('volume_threshold_multiplier', 2.0)
        self.reversal_velocity_min = config.get('reversal_velocity_min', 5.0)
        self.imbalance_threshold = config.get('imbalance_threshold', 0.3)
        self.vpin_threshold = config.get('vpin_threshold', 0.65)
        self.min_confirmation_score = config.get('min_confirmation_score', 4)
        
        self.identified_levels = {}
        self.active_monitors = {}
        
    def evaluate(self, market_data: pd.DataFrame, features: Dict) -> List[Signal]:
        """
        Evaluate market for liquidity sweep opportunities.
        
        Args:
            market_data: Recent OHLCV data with at least 72 hours of history
            features: Pre-calculated features including swing points, VPIN, imbalances
            
        Returns:
            List of signals generated (may be empty)
        """
        if not self.validate_inputs(market_data, features):
            return []
        
        signals = []
        symbol = market_data['symbol'].iloc[-1] if 'symbol' in market_data.columns else 'UNKNOWN'
        
        self._update_critical_levels(market_data, features)
        
        current_price = market_data['close'].iloc[-1]
        current_time = market_data['time'].iloc[-1]
        
        self._update_monitors(symbol, current_price, current_time)
        
        recent_bars = market_data.tail(10)
        for level_price, level_info in self.identified_levels.get(symbol, {}).items():
            if self._check_level_penetration(recent_bars, level_price, level_info['type']):
                
                confirmation_score, criteria_scores = self._evaluate_sweep_criteria(
                    recent_bars, level_price, level_info, features
                )
                
                if confirmation_score >= self.min_confirmation_score:
                    signal = self._generate_signal(
                        symbol, current_time, level_price, level_info,
                        confirmation_score, criteria_scores, market_data
                    )
                    if signal:
                        signals.append(signal)
        
        return signals
    
    def _update_critical_levels(self, market_data: pd.DataFrame, features: Dict):
        """Identify and update critical technical levels from swing points."""
        symbol = market_data['symbol'].iloc[-1] if 'symbol' in market_data.columns else 'UNKNOWN'
        
        if symbol not in self.identified_levels:
            self.identified_levels[symbol] = {}
        
        for period_minutes in self.lookback_periods:
            if len(market_data) < period_minutes:
                continue
            
            period_data = market_data.tail(period_minutes).copy()
            
            highs = period_data['high'].values
            swing_high_indices = []
            for i in range(2, len(highs) - 2):
                if highs[i] == max(highs[i-2:i+3]):
                    swing_high_indices.append(i)
            
            lows = period_data['low'].values
            swing_low_indices = []
            for i in range(2, len(lows) - 2):
                if lows[i] == min(lows[i-2:i+3]):
                    swing_low_indices.append(i)
            
            for idx in swing_high_indices[-5:]:
                level_price = round(highs[idx], 5)
                self.identified_levels[symbol][level_price] = {
                    'type': 'resistance',
                    'period': period_minutes,
                    'touches': 1,
                    'last_updated': datetime.now()
                }
            
            for idx in swing_low_indices[-5:]:
                level_price = round(lows[idx], 5)
                self.identified_levels[symbol][level_price] = {
                    'type': 'support',
                    'period': period_minutes,
                    'touches': 1,
                    'last_updated': datetime.now()
                }
    
    def _update_monitors(self, symbol: str, current_price: float, current_time: datetime):
        """Update monitoring status for levels approaching current price."""
        if symbol not in self.active_monitors:
            self.active_monitors[symbol] = {}
        
        for level_price, level_info in self.identified_levels.get(symbol, {}).items():
            distance_pips = abs(current_price - level_price) * 10000
            
            if distance_pips <= self.proximity_threshold:
                if level_price not in self.active_monitors[symbol]:
                    self.active_monitors[symbol][level_price] = {
                        'activated': current_time,
                        'snapshots': []
                    }
    
    def _check_level_penetration(self, recent_bars: pd.DataFrame, 
                                 level_price: float, level_type: str) -> bool:
        """Check if price has penetrated the specified level."""
        if level_type == 'support':
            penetration = recent_bars['low'].min() < level_price
            reversal = recent_bars['close'].iloc[-1] >= level_price
        else:
            penetration = recent_bars['high'].max() > level_price
            reversal = recent_bars['close'].iloc[-1] <= level_price
        
        return penetration and reversal
    
    def _evaluate_sweep_criteria(self, recent_bars: pd.DataFrame, level_price: float,
                                 level_info: Dict, features: Dict) -> Tuple[int, Dict]:
        """
        Evaluate five confirmation criteria for liquidity sweep.
        
        Returns tuple of (total_score, individual_criteria_scores)
        """
        criteria_scores = {
            'penetration_depth': 0,
            'volume_anomaly': 0,
            'reversal_velocity': 0,
            'order_book_imbalance': 0,
            'vpin_toxicity': 0
        }
        
        if level_info['type'] == 'support':
            penetration_depth = (level_price - recent_bars['low'].min()) * 10000
        else:
            penetration_depth = (recent_bars['high'].max() - level_price) * 10000
        
        if self.penetration_min <= penetration_depth <= self.penetration_max:
            criteria_scores['penetration_depth'] = 1
        
        sweep_bar_idx = recent_bars['low'].idxmin() if level_info['type'] == 'support' else recent_bars['high'].idxmax()
        sweep_volume = recent_bars.loc[sweep_bar_idx, 'volume']
        avg_volume = recent_bars['volume'].mean()
        
        if sweep_volume >= avg_volume * self.volume_threshold:
            criteria_scores['volume_anomaly'] = 1
        
        bars_since_sweep = len(recent_bars) - list(recent_bars.index).index(sweep_bar_idx) - 1
        if bars_since_sweep > 0:
            price_reversal = abs(recent_bars['close'].iloc[-1] - recent_bars.loc[sweep_bar_idx, 'close']) * 10000
            reversal_velocity = price_reversal / bars_since_sweep
            
            if reversal_velocity >= self.reversal_velocity_min:
                criteria_scores['reversal_velocity'] = 1
        
        if 'order_book_imbalance' in features:
            current_imbalance = features['order_book_imbalance']
            expected_direction = -1 if level_info['type'] == 'support' else 1
            
            if abs(current_imbalance) >= self.imbalance_threshold and np.sign(current_imbalance) == expected_direction:
                criteria_scores['order_book_imbalance'] = 1
        
        if 'vpin' in features:
            current_vpin = features['vpin']
            if current_vpin >= self.vpin_threshold:
                criteria_scores['vpin_toxicity'] = 1
        
        total_score = sum(criteria_scores.values())
        
        return total_score, criteria_scores
    
    def _generate_signal(self, symbol: str, timestamp: datetime, level_price: float,
                        level_info: Dict, confirmation_score: int, criteria_scores: Dict,
                        market_data: pd.DataFrame) -> Optional[Signal]:
        """Generate trading signal after successful sweep detection."""
        current_price = market_data['close'].iloc[-1]
        
        recent_highs = market_data['high'].tail(14)
        recent_lows = market_data['low'].tail(14)
        atr_value = (recent_highs - recent_lows).mean()
        
        if level_info['type'] == 'support':
            direction = 'LONG'
            entry_price = current_price
            stop_loss = level_price - (atr_value * 1.5)
            take_profit = current_price + (abs(current_price - stop_loss) * 3.0)
        else:
            direction = 'SHORT'
            entry_price = current_price
            stop_loss = level_price + (atr_value * 1.5)
            take_profit = current_price - (abs(stop_loss - current_price) * 3.0)
        
        sizing_level = 4 if confirmation_score == 5 else 3
        
        metadata = {
            'level_price': float(level_price),
            'level_type': level_info['type'],
            'confirmation_score': confirmation_score,
            'criteria_scores': criteria_scores,
            'atr': float(atr_value),
            'strategy_version': '1.0'
        }
        
        signal = Signal(
            timestamp=timestamp,
            symbol=symbol,
            strategy_name=self.name,
            direction=direction,
            entry_price=float(entry_price),
            stop_loss=float(stop_loss),
            take_profit=float(take_profit),
            sizing_level=sizing_level,
            metadata=metadata
        )
        
        return signal