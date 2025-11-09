"""
Order Block Institutional Strategy.

Identifies institutional participation zones through displacement
and trades rejections at these levels.
"""

import pandas as pd
import numpy as np
from typing import Dict, Optional, List
from datetime import datetime, timedelta
import logging

from strategies.strategy_base import StrategyBase, Signal
from features.displacement import (
    detect_displacement, 
    validate_order_block_retest,
    calculate_footprint_direction,
    OrderBlock
)
from features.ofi import calculate_ofi

logger = logging.getLogger(__name__)

class OrderBlockInstitutional(StrategyBase):
    """Order Block strategy using institutional displacement criteria."""
    
    def __init__(self, params: Dict):
        super().__init__(params)
        
        self.volume_sigma_threshold = params.get('volume_sigma_threshold', 2.5)
        self.displacement_atr_multiplier = params.get('displacement_atr_multiplier', 2.0)
        self.no_retest_enforcement = params.get('no_retest_enforcement', True)
        self.buffer_atr = params.get('buffer_atr', 0.5)
        self.max_active_blocks = params.get('max_active_blocks', 5)
        self.block_expiry_hours = params.get('block_expiry_hours', 24)
        self.stop_loss_buffer_atr = params.get('stop_loss_buffer_atr', 0.75)
        self.take_profit_r_multiple = params.get('take_profit_r_multiple', [1.5, 3.0])
        self.require_ofi_confirmation = params.get('require_ofi_confirmation', True)
        self.require_footprint_confirmation = params.get('require_footprint_confirmation', True)
        
        self.active_blocks: List[OrderBlock] = []
        self.logger = logging.getLogger(self.__class__.__name__)
        
        logger.info(f"Order Block Institutional initialized: displacement={self.displacement_atr_multiplier}xATR")
    
    def evaluate(self, data: pd.DataFrame, features: Dict) -> Optional[Signal]:
        """Evaluate order block conditions."""
        try:
            if len(data) < 100:
                return None
            
            atr = features.get('atr')
            if atr is None or np.isnan(atr) or atr <= 0:
                return None
            
            new_blocks = detect_displacement(
                data, atr, self.displacement_atr_multiplier,
                self.volume_sigma_threshold
            )
            
            if new_blocks:
                existing_times = {b.timestamp for b in self.active_blocks}
                for block in new_blocks:
                    if block.timestamp not in existing_times:
                        self.active_blocks.append(block)
            
            current_time = data.iloc[-1]['timestamp']
            expiry_cutoff = current_time - timedelta(hours=self.block_expiry_hours)
            
            self.active_blocks = [b for b in self.active_blocks 
                                 if b.is_active and b.timestamp > expiry_cutoff]
            
            if len(self.active_blocks) > self.max_active_blocks:
                self.active_blocks.sort(key=lambda x: x.timestamp, reverse=True)
                self.active_blocks = self.active_blocks[:self.max_active_blocks]
            
            recent_data = data.tail(10)
            
            for block in self.active_blocks:
                if self.no_retest_enforcement and block.tested_count > 0:
                    continue
                
                is_retesting, shows_rejection = validate_order_block_retest(
                    block, recent_data, self.buffer_atr, atr
                )
                
                if is_retesting and shows_rejection:
                    confirmations_passed = True
                    ofi_direction = 0
                    
                    if self.require_ofi_confirmation:
                        ofi_raw = calculate_ofi(data)
                        if not ofi_raw.empty and not np.isnan(ofi_raw.iloc[-1]):
                            ofi_direction = np.sign(ofi_raw.iloc[-1])
                            
                            if block.block_type == 'BULLISH' and ofi_direction < 0:
                                confirmations_passed = False
                            elif block.block_type == 'BEARISH' and ofi_direction > 0:
                                confirmations_passed = False
                    
                    footprint_direction = 0
                    if self.require_footprint_confirmation and confirmations_passed:
                        footprint_direction = calculate_footprint_direction(recent_data)
                        
                        if block.block_type == 'BULLISH' and footprint_direction < -0.2:
                            confirmations_passed = False
                        elif block.block_type == 'BEARISH' and footprint_direction > 0.2:
                            confirmations_passed = False
                    
                    if confirmations_passed:
                        signal = self._create_order_block_signal(
                            block, data.iloc[-1]['close'], atr, data,
                            ofi_direction, footprint_direction
                        )
                        
                        if signal:
                            block.tested_count += 1
                            block.last_test_timestamp = current_time
                            return signal
            
            return None
            
        except Exception as e:
            logger.error(f"Order block evaluation failed: {str(e)}", exc_info=True)
            return None
    
    def _create_order_block_signal(self, block: OrderBlock, current_price: float,
                                  atr: float, data: pd.DataFrame,
                                  ofi_direction: float, footprint_direction: float) -> Optional[Signal]:
        """Create signal for order block rejection trade."""
        try:
            if block.block_type == 'BULLISH':
                direction = "LONG"
                entry_price = current_price
                stop_loss = block.zone_low - (self.stop_loss_buffer_atr * atr)
                risk = entry_price - stop_loss
                take_profit_1 = entry_price + (risk * self.take_profit_r_multiple[0])
                take_profit_2 = entry_price + (risk * self.take_profit_r_multiple[1])
                take_profit = take_profit_1
            else:
                direction = "SHORT"
                entry_price = current_price
                stop_loss = block.zone_high + (self.stop_loss_buffer_atr * atr)
                risk = stop_loss - entry_price
                take_profit_1 = entry_price - (risk * self.take_profit_r_multiple[0])
                take_profit_2 = entry_price - (risk * self.take_profit_r_multiple[1])
                take_profit = take_profit_1
            
            actual_risk = abs(entry_price - stop_loss)
            actual_reward = abs(take_profit - entry_price)
            rr_ratio = actual_reward / actual_risk if actual_risk > 0 else 0
            
            if rr_ratio < 1.5:
                return None
            
            if block.displacement_magnitude > 3.0 and block.volume_sigma > 3.5:
                sizing_level = 5
            elif block.displacement_magnitude > 2.5 and block.volume_sigma > 3.0:
                sizing_level = 4
            elif block.displacement_magnitude > 2.0 and block.volume_sigma > 2.5:
                sizing_level = 3
            else:
                sizing_level = 2
            
            signal = Signal(
                timestamp=datetime.now(),
                symbol=data.attrs.get('symbol', 'UNKNOWN'),
                strategy_name="OrderBlock_Institutional",
                direction=direction,
                entry_price=entry_price,
                stop_loss=stop_loss,
                take_profit=take_profit,
                sizing_level=sizing_level,
                metadata={
                    'block_type': block.block_type,
                    'zone_high': float(block.zone_high),
                    'zone_low': float(block.zone_low),
                    'displacement_atr': float(block.displacement_magnitude),
                    'volume_sigma': float(block.volume_sigma),
                    'tested_count': block.tested_count,
                    'ofi_direction': float(ofi_direction),
                    'footprint_direction': float(footprint_direction),
                    'risk_reward_ratio': float(rr_ratio),
                    'rationale': f"{block.block_type} order block showing rejection on first retest."
                }
            )
            
            return signal
            
        except Exception as e:
            logger.error(f"Order block signal creation failed: {str(e)}", exc_info=True)
            return None

