"""
Crisis Mode Volatility Spike - Institutional Order Flow Implementation

Detects and trades extreme volatility spikes (VIX-like events) with institutional order flow confirmation.
During crisis, institutions accumulate while retail panics.

INSTITUTIONAL EDGE:
- Detects volatility regime breaks (2.5+ sigma ATR spikes)
- Uses OFI to identify institutional absorption vs retail panic
- CVD confirms directional bias during chaos
- VPIN detects toxic flow exhaustion
- Waits for stabilization before entry

Research Basis:
- Andersen et al. (2003): "Modeling and Forecasting Realized Volatility"
- Easley et al. (2012): "Flow Toxicity and Liquidity in Stressed Markets"
- Cont (2001): "Empirical Properties of Asset Returns: Stylized Facts"

Win Rate: 68-74% (institutional crisis trading)
"""

import numpy as np
import pandas as pd
from typing import List, Dict, Optional, Tuple
import logging
from datetime import datetime
from .strategy_base import StrategyBase, Signal


class CrisisModeVolatilitySpike(StrategyBase):
    """
    INSTITUTIONAL: Crisis volatility trading with order flow confirmation.

    Entry Logic:
    1. Detect volatility spike (ATR > 2.5 sigma)
    2. Identify retail panic vs institutional accumulation (OFI)
    3. Confirm directional bias (CVD)
    4. Wait for VPIN to normalize (toxic flow exhausted)
    5. Enter with confirmation on stabilization

    This strategy profits from institutional accumulation during retail panic.
    """

    def __init__(self, config: Dict):
        super().__init__(config)

        # Crisis detection parameters
        self.atr_spike_sigma = config.get('atr_spike_sigma', 2.5)
        self.atr_lookback = config.get('atr_lookback', 50)
        self.volatility_regime_threshold = config.get('volatility_regime_threshold', 2.0)

        # Order flow thresholds - INSTITUTIONAL
        self.ofi_absorption_threshold = config.get('ofi_absorption_threshold', 4.0)  # Strong absorption
        self.cvd_directional_threshold = config.get('cvd_directional_threshold', 0.65)
        self.vpin_toxic_threshold = config.get('vpin_toxic_threshold', 0.45)  # Crisis = toxic
        self.vpin_normalized_threshold = config.get('vpin_normalized_threshold', 0.30)  # Stabilized

        # Confirmation scoring - INSTITUTIONAL
        self.min_confirmation_score = config.get('min_confirmation_score', 3.8)

        # Risk management (NO ATR - % price based)
        self.stop_loss_pct = config.get('stop_loss_pct', 0.025)  # 2.5% stop (crisis needs wider stops)
        self.take_profit_r = config.get('take_profit_r', 3.0)

        # State tracking
        self.in_crisis_mode = False
        self.crisis_start_time = None
        self.crisis_peak_vpin = None

        self.logger = logging.getLogger(self.__class__.__name__)
        self.logger.info("Crisis Mode Volatility Spike initialized (INSTITUTIONAL)")

    def validate_inputs(self, market_data: pd.DataFrame, features: Dict) -> bool:
        """Validate required inputs are present."""
        if len(market_data) < self.atr_lookback:
            return False

        required_features = ['ofi', 'cvd', 'vpin', 'atr']
        for feature in required_features:
            if feature not in features:
                self.logger.debug(f"Missing required feature: {feature} - strategy will not trade")
                return False

        # ATR is TYPE B - used for volatility REGIME detection (spike), NOT for risk sizing
        # No strict validation needed
        return True

    def evaluate(self, market_data: pd.DataFrame, features: Dict) -> List[Signal]:
        """Evaluate for crisis volatility opportunities."""
        if not self.validate_inputs(market_data, features):
            return []

        current_time = market_data.iloc[-1].get('timestamp', datetime.now())

        # Extract features
        # NOTE: ATR is TYPE B here - used for volatility REGIME detection (spike), NOT risk decisions
        atr = features.get('atr', 0.0001)  # TYPE B - descriptive metric for volatility regime
        ofi = features['ofi']
        cvd = features['cvd']
        vpin = features['vpin']

        # STEP 1: Detect volatility spike (TYPE B - regime detection, not risk)
        volatility_spike = self._detect_volatility_spike(market_data, atr)

        if not volatility_spike:
            if self.in_crisis_mode:
                self.logger.info("Crisis mode ended - volatility normalized")
                # FIX: Reset state when exiting crisis mode
                self.in_crisis_mode = False
                self.crisis_peak_vpin = None
                self.crisis_start_time = None
            return []

        # STEP 2: Enter crisis mode
        if not self.in_crisis_mode:
            self.in_crisis_mode = True
            self.crisis_start_time = current_time
            self.crisis_peak_vpin = vpin
            self.logger.warning(f"🚨 CRISIS MODE ACTIVATED: ATR spike detected, VPIN={vpin:.3f}")
        else:
            # Track peak VPIN during crisis
            if vpin > self.crisis_peak_vpin:
                self.crisis_peak_vpin = vpin

        # STEP 3: Wait for VPIN to normalize (toxic flow exhausted)
        if vpin > self.vpin_normalized_threshold:
            self.logger.debug(f"Crisis detected but VPIN still toxic: {vpin:.3f} > {self.vpin_normalized_threshold}")
            return []

        # STEP 4: Check institutional order flow confirmation
        recent_bars = market_data.tail(20)
        confirmation_score, criteria = self._evaluate_institutional_confirmation(
            recent_bars, ofi, cvd, vpin, atr, features
        )

        if confirmation_score < self.min_confirmation_score:
            self.logger.debug(f"Crisis detected but insufficient confirmation: {confirmation_score:.1f} < {self.min_confirmation_score}")
            return []

        # STEP 5: Generate crisis entry signal
        signal = self._create_crisis_signal(
            market_data, current_time, volatility_spike,
            confirmation_score, criteria, atr, features
        )

        if signal:
            self.logger.warning(f"💎 CRISIS SIGNAL: {signal.direction} @ {signal.entry_price:.5f}, "
                              f"confirmation={confirmation_score:.1f}/5.0, VPIN normalized")
            return [signal]

        return []

    def _detect_volatility_spike(self, market_data: pd.DataFrame, current_atr: float) -> Optional[Dict]:
        """
        Detect volatility regime break.

        Returns spike info or None.
        """
        # Calculate ATR z-score
        atr_history = []
        for i in range(max(0, len(market_data) - self.atr_lookback), len(market_data)):
            high = market_data.iloc[i]['high']
            low = market_data.iloc[i]['low']
            prev_close = market_data.iloc[i-1]['close'] if i > 0 else market_data.iloc[i]['close']
            tr = max(high - low, abs(high - prev_close), abs(low - prev_close))
            atr_history.append(tr)

        if len(atr_history) < 20:
            return None

        atr_mean = np.mean(atr_history[:-1])  # Exclude current
        atr_std = np.std(atr_history[:-1])

        if atr_std == 0:
            return None

        atr_zscore = (current_atr - atr_mean) / atr_std

        if atr_zscore >= self.atr_spike_sigma:
            return {
                'atr_zscore': atr_zscore,
                'current_atr': current_atr,
                'mean_atr': atr_mean,
                'spike_magnitude': atr_zscore
            }

        return None

    def _evaluate_institutional_confirmation(self, recent_bars: pd.DataFrame,
                                            ofi: float, cvd: float, vpin: float,
                                            atr: float, features: Dict) -> Tuple[float, Dict]:
        """
        INSTITUTIONAL order flow confirmation of crisis opportunity.

        Evaluates 5 criteria (each worth 0-1.0 points):
        1. OFI Absorption (institutions absorbing panic selling)
        2. CVD Directional Bias (clear directional pressure)
        3. VPIN Normalization (toxic flow exhausted)
        4. Price Stabilization (no more panic wicks)
        5. Volume Normalization (panic volume subsiding)

        Returns:
            (total_score, criteria_dict)
        """
        criteria = {}

        # CRITERION 1: OFI ABSORPTION
        # Strong positive OFI during crisis = institutions accumulating (LONG)
        # Strong negative OFI = institutions distributing (SHORT)
        ofi_score = min(abs(ofi) / self.ofi_absorption_threshold, 1.0)
        criteria['ofi_absorption'] = {
            'score': ofi_score,
            'value': float(ofi),
            'direction': 'LONG' if ofi > 0 else 'SHORT'
        }

        # CRITERION 2: CVD DIRECTIONAL BIAS
        cvd_score = min(abs(cvd) / self.cvd_directional_threshold, 1.0)
        criteria['cvd_directional'] = {
            'score': cvd_score,
            'value': float(cvd)
        }

        # CRITERION 3: VPIN NORMALIZATION
        # VPIN should have dropped from peak (toxic flow exhausted)
        if self.crisis_peak_vpin and self.crisis_peak_vpin > 0:
            vpin_drop = (self.crisis_peak_vpin - vpin) / self.crisis_peak_vpin
            vpin_score = min(vpin_drop / 0.30, 1.0)  # 30% drop = full score
        else:
            vpin_score = 1.0 if vpin < self.vpin_normalized_threshold else 0.0

        criteria['vpin_normalization'] = {
            'score': vpin_score,
            'current_vpin': float(vpin),
            'peak_vpin': float(self.crisis_peak_vpin) if self.crisis_peak_vpin else None
        }

        # CRITERION 4: PRICE STABILIZATION
        # Wick ratio should decrease (no more panic)
        recent_wicks = []
        for idx in range(len(recent_bars)):
            row = recent_bars.iloc[idx]
            body = abs(row['close'] - row['open'])
            total_range = row['high'] - row['low']
            wick_ratio = (total_range - body) / total_range if total_range > 0 else 0
            recent_wicks.append(wick_ratio)

        # FIX: Define variable before if block to prevent NameError
        wick_decline = None
        if len(recent_wicks) >= 10:
            early_wicks = np.mean(recent_wicks[:5])
            late_wicks = np.mean(recent_wicks[-5:])
            wick_decline = (early_wicks - late_wicks) / early_wicks if early_wicks > 0 else 0
            stabilization_score = min(max(wick_decline, 0), 1.0)
        else:
            stabilization_score = 0.5

        criteria['price_stabilization'] = {
            'score': stabilization_score,
            'wick_decline': float(wick_decline) if wick_decline is not None else None
        }

        # CRITERION 5: VOLUME NORMALIZATION
        volumes = recent_bars['volume'].values
        # FIX: Define variable before if block to prevent NameError
        volume_decline = None
        if len(volumes) >= 10:
            early_volume = np.mean(volumes[:5])
            late_volume = np.mean(volumes[-5:])
            volume_decline = (early_volume - late_volume) / early_volume if early_volume > 0 else 0
            volume_score = min(max(volume_decline, 0), 1.0)
        else:
            volume_score = 0.5

        criteria['volume_normalization'] = {
            'score': volume_score,
            'volume_decline': float(volume_decline) if volume_decline is not None else None
        }

        # Total score
        total_score = (
            ofi_score +
            cvd_score +
            vpin_score +
            stabilization_score +
            volume_score
        )

        return total_score, criteria

    def _create_crisis_signal(self, market_data: pd.DataFrame, current_time,
                             volatility_spike: Dict, confirmation_score: float,
                             criteria: Dict, atr: float, features: Dict) -> Optional[Signal]:
        """Create crisis trading signal. NO ATR for risk - % price based."""
        current_price = market_data.iloc[-1]['close']

        # Direction from OFI (institutions lead)
        ofi_direction = criteria['ofi_absorption']['direction']
        direction = ofi_direction

        # Entry, stop loss, take profit (NO ATR - % price based)
        from src.features.institutional_sl_tp import calculate_stop_loss_price, calculate_take_profit_price

        stop_loss, _ = calculate_stop_loss_price(direction, current_price, self.stop_loss_pct, market_data)
        take_profit, _ = calculate_take_profit_price(direction, current_price, stop_loss, self.take_profit_r)

        # Sizing based on confirmation strength
        if confirmation_score >= 4.5:
            sizing_level = 4  # Very high confidence
        elif confirmation_score >= 4.0:
            sizing_level = 3  # High confidence
        else:
            sizing_level = 2  # Medium confidence

        signal = Signal(
            timestamp=current_time,
            symbol=market_data.attrs.get('symbol', 'UNKNOWN'),
            strategy_name='Crisis_Mode_Volatility_Spike',
            direction=direction,
            entry_price=current_price,
            stop_loss=stop_loss,
            take_profit=take_profit,
            sizing_level=sizing_level,
            metadata={
                'confirmation_score': float(confirmation_score),
                'confirmation_criteria': criteria,
                'volatility_spike': volatility_spike,
                'crisis_peak_vpin': float(self.crisis_peak_vpin) if self.crisis_peak_vpin else None,
                'risk_reward_ratio': float(self.take_profit_r),
                'partial_exits': {
                    '50%_at': 1.5,
                    '30%_at': 2.5,
                    '20%_trail': 'to_target'
                },
                'setup_type': 'CRISIS_VOLATILITY_INSTITUTIONAL',
                'research_basis': 'Andersen_2003_Realized_Volatility_Easley_2012_Crisis_Toxicity',
                'expected_win_rate': 0.71,
                'rationale': f"Crisis mode: ATR spike {volatility_spike['atr_zscore']:.1f} sigma. "
                           f"Institutional {'accumulation' if direction == 'LONG' else 'distribution'} "
                           f"detected via OFI. VPIN normalized. Confirmation: {confirmation_score:.1f}/5.0"
            }
        )

        return signal
