"""
OFI Refinement Strategy - Institutional Implementation

Order Flow Imbalance (OFI) strategy based on microstructure analysis
of bid-ask volume dynamics to detect directional pressure.

FUNDAMENTO ACADÃ‰MICO:
- Cont, Kukanov & Stoikov (2014): "The Price Impact of Order Book Events"
  Journal of Financial Econometrics, 12(1), 47-88
- Cartea, Jaimungal & Penalva (2015): "Algorithmic and High-Frequency Trading"
  Cambridge University Press, Chapter 7
- Lee & Ready (1991): "Inferring Trade Direction from Intraday Data"
  Journal of Finance, 46(2), 733-746

DIFERENCIADORES INSTITUCIONALES:
1. Z-score threshold at 1.8Ïƒ for higher frequency signals (vs 2.5Ïƒ retail)
2. VPIN toxicity filter to avoid adverse selection (Easley et al., 2012)
3. Price-OFI coherence requirement to confirm genuine flow
4. Dynamic window adjustment based on market regime
"""

import logging
import numpy as np
import pandas as pd
from typing import Optional, Dict, Tuple
from collections import deque
from datetime import datetime, timedelta

from .strategy_base import StrategyBase, Signal

class OFIRefinement(StrategyBase):
    """
    Order Flow Imbalance strategy using bid-ask volume dynamics.
    
    Detects directional pressure from order book volume changes,
    filtered by VPIN toxicity and price coherence checks.
    """
    
    def __init__(self, config: Dict):
        """
        Initialize OFI Refinement strategy with institutional parameters.
        
        Args:
            config: Strategy configuration dictionary
        """
        super().__init__(config)
        
        # OFI calculation parameters
        self.window_ticks = config.get('window_ticks', 100)
        self.z_entry_threshold = config.get('z_entry_threshold', 1.8)
        self.lookback_periods = config.get('lookback_periods', 500)
        
        # Risk filters
        self.vpin_max_safe = config.get('vpin_max_safe', 0.35)
        self.price_coherence_required = config.get('price_coherence_required', True)
        self.min_data_points = config.get('min_data_points', 200)
        
        # Risk management - INSTITUTIONAL (NO ATR)
        self.stop_loss_pct = config.get('stop_loss_pct', 0.012)  # 1.2% stop
        self.take_profit_pct = config.get('take_profit_pct', 0.025)  # 2.5% target
        
        # State tracking
        # FIX BUG #12: Use deque with maxlen to prevent memory leak
        self.ofi_history = deque(maxlen=5000)
        self.last_signal_time = None
        self.signal_cooldown = timedelta(minutes=5)
        
        self.logger = logging.getLogger(self.__class__.__name__)
        self.logger.info(f"OFI Refinement initialized with threshold={self.z_entry_threshold}Ïƒ, "
                        f"window={self.window_ticks} ticks")
        self.name = 'ofi_refinement'
    
    def calculate_ofi(self, data: pd.DataFrame) -> pd.Series:
        """
        Calculate Order Flow Imbalance using bid-ask volume changes.
        
        OFI(t) = Î£[Î”bid_volume(t) - Î”ask_volume(t)]
        
        Uses tick rule classification when true bid-ask data unavailable:
        - If close > midpoint â†’ buy-initiated (ask volume)
        - If close < midpoint â†’ sell-initiated (bid volume)
        
        Args:
            data: DataFrame with OHLCV data
            
        Returns:
            Series of OFI values
        """
        if len(data) < self.window_ticks:
            self.logger.warning(f"Insufficient data for OFI calculation: {len(data)} < {self.window_ticks}")
            return pd.Series(index=data.index, dtype=float)
        
        # Calculate midpoint for tick classification (Lee-Ready method)
        midpoint = (data['high'] + data['low']) / 2
        
        # Classify trades: 1 for buy-initiated, -1 for sell-initiated
        trade_sign = np.where(data['close'] > midpoint, 1, 
                              np.where(data['close'] < midpoint, -1, 0))
        
        # Handle exact midpoint cases using tick rule
        at_midpoint = data['close'] == midpoint
        if at_midpoint.any():
            price_changes = data['close'].diff()
            trade_sign[at_midpoint] = np.sign(price_changes[at_midpoint])
        
        # Calculate signed volume (proxy for bid/ask volume changes)
        signed_volume = data['volume'] * trade_sign
        
        # Calculate OFI as rolling sum of signed volume
        ofi = pd.Series(signed_volume, index=data.index).rolling(
            window=self.window_ticks, min_periods=1
        ).sum()
        
        self.logger.debug(f"OFI calculated: mean={ofi.mean():.2f}, std={ofi.std():.2f}, "
                         f"last={ofi.iloc[-1]:.2f}")
        
        return ofi
    
    def calculate_ofi_zscore(self, ofi_series: pd.Series, window: int) -> float:
        """
        Normalize current OFI against historical distribution.
        
        Z-score = (OFI_current - Î¼_historical) / Ïƒ_historical
        
        Args:
            ofi_series: Series of OFI values
            window: Lookback window for statistics
            
        Returns:
            Z-score of current OFI
        """
        if len(ofi_series) < window:
            self.logger.warning(f"Insufficient OFI history for z-score: {len(ofi_series)} < {window}")
            return 0.0
        
        # Use all data except last value for statistics (avoid lookahead)
        historical_ofi = ofi_series.iloc[:-1].tail(window)
        current_ofi = ofi_series.iloc[-1]
        
        mean = historical_ofi.mean()
        std = historical_ofi.std()
        
        if std == 0 or np.isnan(std):
            self.logger.warning("OFI standard deviation is zero or NaN")
            return 0.0
        
        z_score = (current_ofi - mean) / std
        
        # Cap extreme values to avoid outlier trades
        z_score = np.clip(z_score, -4.0, 4.0)
        
        self.logger.debug(f"OFI Z-score: {z_score:.3f} (current={current_ofi:.2f}, "
                         f"mean={mean:.2f}, std={std:.2f})")
        
        return z_score
    
    def check_price_coherence(self, ofi: float, price_change: float) -> bool:
        """
        Verify OFI direction aligns with price movement.
        
        Coherence prevents false signals when OFI and price diverge,
        which often indicates absorption rather than directional flow.
        
        Args:
            ofi: Current OFI value
            price_change: Recent price change percentage
            
        Returns:
            True if OFI and price are coherent
        """
        # Both should have same sign for coherence
        coherent = (ofi > 0 and price_change > 0) or (ofi < 0 and price_change < 0)
        
        if not coherent:
            self.logger.info(f"OFI-price divergence detected: OFI={ofi:.2f}, "
                           f"price_change={price_change:.4f}%")
        
        return coherent
    
    # REMOVED: calculate_atr() - NO ATR in institutional system
    # Replaced with institutional_sl_tp module (% price + structure)
    
    def evaluate(self, data: pd.DataFrame, features: Dict) -> Optional[Signal]:
        """
        Evaluate OFI conditions and generate trading signal.
        
        Process:
        1. Calculate OFI from order flow
        2. Normalize to z-score against historical window
        3. Check if |z-score| > threshold (1.8Ïƒ)
        4. Verify VPIN < max_safe threshold (if available)
        5. Confirm price-OFI coherence
        6. Generate signal with ATR-based stops
        
        Args:
            data: DataFrame with OHLCV data
            features: Dict with pre-calculated features (may include VPIN)
            
        Returns:
            Signal object if conditions met, None otherwise
        """
        # Validate minimum data requirements
        if len(data) < self.min_data_points:
            self.logger.debug(f"Insufficient data: {len(data)} < {self.min_data_points}")
            return None
        
        # Check cooldown period
        if self.last_signal_time:
            time_since_signal = datetime.now() - self.last_signal_time
            if time_since_signal < self.signal_cooldown:
                self.logger.debug(f"Cooldown active: {time_since_signal.seconds}s < {self.signal_cooldown.seconds}s")
                return None
        
        # STEP 1: Calculate OFI
        ofi_series = self.calculate_ofi(data)
        if ofi_series.empty or ofi_series.isna().all():
            self.logger.warning("OFI calculation failed or returned empty")
            return None
        
        current_ofi = ofi_series.iloc[-1]
        
        # STEP 2: Calculate z-score
        z_score = self.calculate_ofi_zscore(ofi_series, self.lookback_periods)
        
        # STEP 3: Check threshold
        if abs(z_score) < self.z_entry_threshold:
            self.logger.debug(f"OFI z-score {z_score:.3f} below threshold {self.z_entry_threshold}")
            return None
        
        self.logger.info(f"OFI signal candidate: z-score={z_score:.3f}Ïƒ, OFI={current_ofi:.2f}")
        
        # STEP 4: Check VPIN if available
        vpin = features.get('vpin')
        if vpin is not None:
            if vpin > self.vpin_max_safe:
                self.logger.warning(f"VPIN {vpin:.3f} exceeds safe threshold {self.vpin_max_safe} - "
                                   "market too toxic")
                return None
            self.logger.info(f"VPIN check passed: {vpin:.3f} < {self.vpin_max_safe}")
        
        # STEP 5: Check price coherence
        price_change_pct = ((data['close'].iloc[-1] / data['close'].iloc[-20]) - 1) * 100
        
        if self.price_coherence_required:
            if not self.check_price_coherence(current_ofi, price_change_pct):
                self.logger.warning("Price-OFI coherence check failed")
                return None
        
        # STEP 6: Generate signal (INSTITUTIONAL - NO ATR)
        current_price = data['close'].iloc[-1]

        # Import institutional SL/TP module (NO ATR)
        from src.features.institutional_sl_tp import calculate_stop_loss_price, calculate_take_profit_price

        if z_score > 0:
            direction = 'LONG'
            # Use % price for SL/TP (from config: stop_loss_pct, take_profit_pct)
            stop_loss, _ = calculate_stop_loss_price(direction, current_price, self.stop_loss_pct, data)
            take_profit, _ = calculate_take_profit_price(direction, current_price, stop_loss, None, self.take_profit_pct)
        else:
            direction = 'SHORT'
            stop_loss, _ = calculate_stop_loss_price(direction, current_price, self.stop_loss_pct, data)
            take_profit, _ = calculate_take_profit_price(direction, current_price, stop_loss, None, self.take_profit_pct)
        
        # Calculate confidence based on z-score magnitude
        confidence = min(0.95, 0.65 + (abs(z_score) - self.z_entry_threshold) * 0.15)
        
        # Determine sizing level (1-5 based on signal strength)
        if abs(z_score) > 3.0:
            sizing_level = 5
        elif abs(z_score) > 2.5:
            sizing_level = 4
        elif abs(z_score) > 2.0:
            sizing_level = 3
        else:
            sizing_level = 2
        
        signal = Signal(
            strategy_name=self.name,
            direction=direction,
            entry_price=current_price,
            stop_loss=stop_loss,
            take_profit=take_profit,
            confidence=confidence,
            sizing_level=sizing_level,
            metadata={
                'ofi_value': float(current_ofi),
                'ofi_z_score': float(z_score),
                'vpin': float(vpin) if vpin else None,
                'price_change_20p': float(price_change_pct),
                'atr': float(atr),  # TYPE B - descriptive metric only
                'risk_reward_ratio': self.take_profit_pct / self.stop_loss_pct  # ~2.08 (2.5% / 1.2%)
            }
        )
        
        self.logger.info(f"Signal generated: {direction.upper()} @ {current_price:.5f}, "
                        f"SL={stop_loss:.5f}, TP={take_profit:.5f}, "
                        f"confidence={confidence:.2f}, size={sizing_level}")
        
        # Update state
        self.last_signal_time = datetime.now()
        self.ofi_history.append({'timestamp': datetime.now(), 'ofi': current_ofi, 'z_score': z_score})
        
        return signal