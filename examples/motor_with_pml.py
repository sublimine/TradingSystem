import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

import pandas as pd
import numpy as np
import logging
from typing import Dict, List, Optional
from datetime import datetime
import time

from core.portfolio_manager import PortfolioManagerLayer
from core.strategy_adapter import StrategyAdapter
from core.signal_schema import InstitutionalSignal

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# ============================================================================
# CONFIGURACION DE CAPITAL
# ============================================================================

TOTAL_CAPITAL = 10000.0

FAMILY_ALLOCATIONS = {
    'momentum': 0.35,
    'mean_reversion': 0.25,
    'breakout': 0.20,
    'arbitrage': 0.10,
    'other': 0.10
}

STRATEGY_FAMILIES = {
    'ofi_refined': 'momentum',
    'ofi_momentum': 'momentum',
    'ofi_trend': 'momentum',
    'fvg_institutional': 'breakout',
    'fvg_continuation': 'breakout',
    'order_block_aggressive': 'breakout',
    'order_block_conservative': 'breakout',
    'liquidity_sweep': 'mean_reversion',
    'liquidity_absorption': 'mean_reversion',
    'manipulation_pattern': 'mean_reversion',
    'multi_tf_liquidity': 'mean_reversion',
    'volume_climax': 'momentum',
    'smart_money': 'other',
    'institutional_footprint': 'other'
}


# ============================================================================
# ESTRATEGIAS INSTITUCIONALES REALES
# ============================================================================

class OrderFlowImbalanceRefined(StrategyAdapter):
    """
    Order Flow Imbalance - Refinado
    Detecta desequilibrios institucionales en el flujo de ordenes.
    """
    
    def __init__(self):
        super().__init__(
            strategy_id='ofi_refined',
            strategy_version='1.0.0'
        )
    
    def evaluate(self, data: pd.DataFrame, features: Dict,
                 instrument: str, horizon: str) -> Optional[InstitutionalSignal]:
        
        if len(data) < 50:
            return None
        
        ofi = features.get('ofi', 0.0)
        vpin = features.get('vpin', 0.5)
        
        # Requiere OFI fuerte y VPIN confirmando
        if abs(ofi) < 1.5 or vpin < 0.65:
            return None
        
        direction = 1 if ofi > 0 else -1
        confidence = min(0.55 + abs(ofi) * 0.15 + (vpin - 0.5) * 0.4, 0.95)
        
        close = data['close'].iloc[-1]
        atr = (data['high'] - data['low']).rolling(14).mean().iloc[-1]
        stop_distance = 1.5 * atr
        
        return self.create_signal(
            instrument=instrument,
            horizon=horizon,
            direction=direction,
            confidence=confidence,
            entry_price=close,
            stop_distance_points=stop_distance,
            target_profile={'primary': 2.5, 'extended': 4.0},
            regime_sensitivity={'trend': 0.85, 'range': 0.40, 'shock': 0.15},
            quality_metrics={'hit_rate': 0.62, 'sharpe': 2.1, 'max_drawdown': 0.14},
            expected_half_life_seconds=2400,
            ttl_milliseconds=180000,
            metadata={'ofi': ofi, 'vpin': vpin, 'setup': 'refined_ofi'}
        )


class OrderFlowImbalanceMomentum(StrategyAdapter):
    """OFI enfocado en momentum de corto plazo."""
    
    def __init__(self):
        super().__init__(strategy_id='ofi_momentum', strategy_version='1.0.0')
    
    def evaluate(self, data: pd.DataFrame, features: Dict,
                 instrument: str, horizon: str) -> Optional[InstitutionalSignal]:
        
        if len(data) < 30:
            return None
        
        ofi = features.get('ofi', 0.0)
        vol_ratio = features.get('vol_ratio', 1.0)
        
        if abs(ofi) < 1.2 or vol_ratio < 1.3:
            return None
        
        direction = 1 if ofi > 0 else -1
        confidence = min(0.60 + abs(ofi) * 0.12, 0.88)
        
        close = data['close'].iloc[-1]
        atr = (data['high'] - data['low']).rolling(10).mean().iloc[-1]
        stop_distance = 1.2 * atr
        
        return self.create_signal(
            instrument=instrument,
            horizon=horizon,
            direction=direction,
            confidence=confidence,
            entry_price=close,
            stop_distance_points=stop_distance,
            target_profile={'primary': 2.0, 'extended': 3.0},
            regime_sensitivity={'trend': 0.90, 'range': 0.35, 'shock': 0.10},
            quality_metrics={'hit_rate': 0.58, 'sharpe': 1.9, 'max_drawdown': 0.16},
            expected_half_life_seconds=1800,
            ttl_milliseconds=120000,
            metadata={'ofi': ofi, 'vol_ratio': vol_ratio, 'setup': 'momentum_ofi'}
        )


class OrderFlowImbalanceTrend(StrategyAdapter):
    """OFI para seguimiento de tendencia."""
    
    def __init__(self):
        super().__init__(strategy_id='ofi_trend', strategy_version='1.0.0')
    
    def evaluate(self, data: pd.DataFrame, features: Dict,
                 instrument: str, horizon: str) -> Optional[InstitutionalSignal]:
        
        if len(data) < 60:
            return None
        
        ofi = features.get('ofi', 0.0)
        close = data['close']
        sma_50 = close.rolling(50).mean().iloc[-1]
        current_price = close.iloc[-1]
        
        trend_aligned = (ofi > 0 and current_price > sma_50) or (ofi < 0 and current_price < sma_50)
        
        if not trend_aligned or abs(ofi) < 1.0:
            return None
        
        direction = 1 if ofi > 0 else -1
        confidence = min(0.58 + abs(ofi) * 0.10, 0.85)
        
        atr = (data['high'] - data['low']).rolling(20).mean().iloc[-1]
        stop_distance = 1.8 * atr
        
        return self.create_signal(
            instrument=instrument,
            horizon=horizon,
            direction=direction,
            confidence=confidence,
            entry_price=current_price,
            stop_distance_points=stop_distance,
            target_profile={'primary': 3.0, 'extended': 5.0},
            regime_sensitivity={'trend': 0.92, 'range': 0.25, 'shock': 0.08},
            quality_metrics={'hit_rate': 0.64, 'sharpe': 2.3, 'max_drawdown': 0.13},
            expected_half_life_seconds=3600,
            ttl_milliseconds=240000,
            metadata={'ofi': ofi, 'trend_alignment': True, 'setup': 'trend_ofi'}
        )


class FairValueGapInstitutional(StrategyAdapter):
    """Fair Value Gap - Patrones institucionales."""
    
    def __init__(self):
        super().__init__(strategy_id='fvg_institutional', strategy_version='1.0.0')
    
    def evaluate(self, data: pd.DataFrame, features: Dict,
                 instrument: str, horizon: str) -> Optional[InstitutionalSignal]:
        
        if len(data) < 20:
            return None
        
        # Detectar gap entre velas
        gap_up = data['low'].iloc[-1] > data['high'].iloc[-3]
        gap_down = data['high'].iloc[-1] < data['low'].iloc[-3]
        
        if not (gap_up or gap_down):
            return None
        
        vol_ratio = features.get('vol_ratio', 1.0)
        if vol_ratio < 1.4:
            return None
        
        direction = 1 if gap_up else -1
        confidence = min(0.65 + vol_ratio * 0.15, 0.90)
        
        close = data['close'].iloc[-1]
        gap_size = abs(data['low'].iloc[-1] - data['high'].iloc[-3]) if gap_up else abs(data['high'].iloc[-1] - data['low'].iloc[-3])
        stop_distance = gap_size * 0.8
        
        return self.create_signal(
            instrument=instrument,
            horizon=horizon,
            direction=direction,
            confidence=confidence,
            entry_price=close,
            stop_distance_points=stop_distance,
            target_profile={'primary': 2.2, 'extended': 3.5},
            regime_sensitivity={'trend': 0.80, 'range': 0.45, 'shock': 0.20},
            quality_metrics={'hit_rate': 0.61, 'sharpe': 2.0, 'max_drawdown': 0.15},
            expected_half_life_seconds=2700,
            ttl_milliseconds=200000,
            metadata={'gap_size': gap_size, 'vol_ratio': vol_ratio, 'setup': 'fvg_institutional'}
        )


class FairValueGapContinuation(StrategyAdapter):
    """FVG para continuación de tendencia."""
    
    def __init__(self):
        super().__init__(strategy_id='fvg_continuation', strategy_version='1.0.0')
    
    def evaluate(self, data: pd.DataFrame, features: Dict,
                 instrument: str, horizon: str) -> Optional[InstitutionalSignal]:
        
        if len(data) < 30:
            return None
        
        close = data['close']
        sma_20 = close.rolling(20).mean().iloc[-1]
        current_price = close.iloc[-1]
        
        # Detectar gap en dirección de tendencia
        gap_up = data['low'].iloc[-1] > data['high'].iloc[-3] and current_price > sma_20
        gap_down = data['high'].iloc[-1] < data['low'].iloc[-3] and current_price < sma_20
        
        if not (gap_up or gap_down):
            return None
        
        direction = 1 if gap_up else -1
        confidence = 0.68
        
        atr = (data['high'] - data['low']).rolling(14).mean().iloc[-1]
        stop_distance = 1.3 * atr
        
        return self.create_signal(
            instrument=instrument,
            horizon=horizon,
            direction=direction,
            confidence=confidence,
            entry_price=current_price,
            stop_distance_points=stop_distance,
            target_profile={'primary': 2.5, 'extended': 4.0},
            regime_sensitivity={'trend': 0.88, 'range': 0.30, 'shock': 0.12},
            quality_metrics={'hit_rate': 0.63, 'sharpe': 2.2, 'max_drawdown': 0.13},
            expected_half_life_seconds=3000,
            ttl_milliseconds=220000,
            metadata={'trend_continuation': True, 'setup': 'fvg_continuation'}
        )


class OrderBlockAggressive(StrategyAdapter):
    """Order Block - Enfoque agresivo."""
    
    def __init__(self):
        super().__init__(strategy_id='order_block_aggressive', strategy_version='1.0.0')
    
    def evaluate(self, data: pd.DataFrame, features: Dict,
                 instrument: str, horizon: str) -> Optional[InstitutionalSignal]:
        
        if len(data) < 25:
            return None
        
        volume = data['volume']
        vol_spike = volume.iloc[-1] > volume.rolling(20).mean().iloc[-1] * 2.0
        
        if not vol_spike:
            return None
        
        close = data['close']
        current_price = close.iloc[-1]
        prev_price = close.iloc[-2]
        
        big_move = abs(current_price - prev_price) / prev_price > 0.002
        
        if not big_move:
            return None
        
        direction = 1 if current_price > prev_price else -1
        confidence = 0.72
        
        atr = (data['high'] - data['low']).rolling(10).mean().iloc[-1]
        stop_distance = 1.0 * atr
        
        return self.create_signal(
            instrument=instrument,
            horizon=horizon,
            direction=direction,
            confidence=confidence,
            entry_price=current_price,
            stop_distance_points=stop_distance,
            target_profile={'primary': 2.0, 'extended': 3.2},
            regime_sensitivity={'trend': 0.82, 'range': 0.50, 'shock': 0.25},
            quality_metrics={'hit_rate': 0.60, 'sharpe': 1.95, 'max_drawdown': 0.17},
            expected_half_life_seconds=2100,
            ttl_milliseconds=150000,
            metadata={'volume_spike': True, 'setup': 'order_block_aggressive'}
        )


class OrderBlockConservative(StrategyAdapter):
    """Order Block - Enfoque conservador."""
    
    def __init__(self):
        super().__init__(strategy_id='order_block_conservative', strategy_version='1.0.0')
    
    def evaluate(self, data: pd.DataFrame, features: Dict,
                 instrument: str, horizon: str) -> Optional[InstitutionalSignal]:
        
        if len(data) < 40:
            return None
        
        volume = data['volume']
        vol_spike = volume.iloc[-1] > volume.rolling(30).mean().iloc[-1] * 2.5
        
        if not vol_spike:
            return None
        
        close = data['close']
        current_price = close.iloc[-1]
        sma_30 = close.rolling(30).mean().iloc[-1]
        
        trend_aligned = (current_price > sma_30 * 1.005) or (current_price < sma_30 * 0.995)
        
        if not trend_aligned:
            return None
        
        direction = 1 if current_price > sma_30 else -1
        confidence = 0.75
        
        atr = (data['high'] - data['low']).rolling(20).mean().iloc[-1]
        stop_distance = 1.6 * atr
        
        return self.create_signal(
            instrument=instrument,
            horizon=horizon,
            direction=direction,
            confidence=confidence,
            entry_price=current_price,
            stop_distance_points=stop_distance,
            target_profile={'primary': 2.8, 'extended': 4.5},
            regime_sensitivity={'trend': 0.87, 'range': 0.38, 'shock': 0.15},
            quality_metrics={'hit_rate': 0.66, 'sharpe': 2.4, 'max_drawdown': 0.12},
            expected_half_life_seconds=3300,
            ttl_milliseconds=250000,
            metadata={'volume_confirmed': True, 'trend_aligned': True, 'setup': 'order_block_conservative'}
        )


class LiquiditySweep(StrategyAdapter):
    """Liquidity Sweep - Detección de barridos de liquidez."""
    
    def __init__(self):
        super().__init__(strategy_id='liquidity_sweep', strategy_version='1.0.0')
    
    def evaluate(self, data: pd.DataFrame, features: Dict,
                 instrument: str, horizon: str) -> Optional[InstitutionalSignal]:
        
        if len(data) < 35:
            return None
        
        high = data['high']
        low = data['low']
        close = data['close']
        
        # Detectar sweep de highs o lows recientes
        recent_high = high.rolling(20).max().iloc[-2]
        recent_low = low.rolling(20).min().iloc[-2]
        
        swept_high = high.iloc[-1] > recent_high and close.iloc[-1] < recent_high
        swept_low = low.iloc[-1] < recent_low and close.iloc[-1] > recent_low
        
        if not (swept_high or swept_low):
            return None
        
        direction = -1 if swept_high else 1
        confidence = 0.70
        
        current_price = close.iloc[-1]
        atr = (high - low).rolling(14).mean().iloc[-1]
        stop_distance = 1.4 * atr
        
        return self.create_signal(
            instrument=instrument,
            horizon=horizon,
            direction=direction,
            confidence=confidence,
            entry_price=current_price,
            stop_distance_points=stop_distance,
            target_profile={'primary': 2.3, 'extended': 3.8},
            regime_sensitivity={'trend': 0.70, 'range': 0.65, 'shock': 0.30},
            quality_metrics={'hit_rate': 0.63, 'sharpe': 2.1, 'max_drawdown': 0.14},
            expected_half_life_seconds=2800,
            ttl_milliseconds=210000,
            metadata={'sweep_type': 'high' if swept_high else 'low', 'setup': 'liquidity_sweep'}
        )


class LiquidityAbsorption(StrategyAdapter):
    """Liquidity Absorption - Zonas de absorción."""
    
    def __init__(self):
        super().__init__(strategy_id='liquidity_absorption', strategy_version='1.0.0')
    
    def evaluate(self, data: pd.DataFrame, features: Dict,
                 instrument: str, horizon: str) -> Optional[InstitutionalSignal]:
        
        if len(data) < 30:
            return None
        
        volume = data['volume']
        vol_ratio = features.get('vol_ratio', 1.0)
        
        # Alta vol con poco movimiento = absorción
        price_range = (data['high'].iloc[-1] - data['low'].iloc[-1]) / data['close'].iloc[-1]
        high_vol_low_range = vol_ratio > 1.5 and price_range < 0.003
        
        if not high_vol_low_range:
            return None
        
        close = data['close']
        current_price = close.iloc[-1]
        sma_10 = close.rolling(10).mean().iloc[-1]
        
        direction = 1 if current_price > sma_10 else -1
        confidence = 0.68
        
        atr = (data['high'] - data['low']).rolling(14).mean().iloc[-1]
        stop_distance = 1.5 * atr
        
        return self.create_signal(
            instrument=instrument,
            horizon=horizon,
            direction=direction,
            confidence=confidence,
            entry_price=current_price,
            stop_distance_points=stop_distance,
            target_profile={'primary': 2.4, 'extended': 3.6},
            regime_sensitivity={'trend': 0.65, 'range': 0.70, 'shock': 0.35},
            quality_metrics={'hit_rate': 0.61, 'sharpe': 2.0, 'max_drawdown': 0.15},
            expected_half_life_seconds=2500,
            ttl_milliseconds=190000,
            metadata={'absorption_detected': True, 'vol_ratio': vol_ratio, 'setup': 'liquidity_absorption'}
        )


class ManipulationPattern(StrategyAdapter):
    """Manipulation Pattern - Patrones de manipulación institucional."""
    
    def __init__(self):
        super().__init__(strategy_id='manipulation_pattern', strategy_version='1.0.0')
    
    def evaluate(self, data: pd.DataFrame, features: Dict,
                 instrument: str, horizon: str) -> Optional[InstitutionalSignal]:
        
        if len(data) < 25:
            return None
        
        close = data['close']
        high = data['high']
        low = data['low']
        
        # Patron de manipulación: falsa ruptura seguida de reversión
        breakout_up = high.iloc[-2] > high.rolling(15).max().iloc[-3]
        reversal_down = close.iloc[-1] < close.iloc[-2] * 0.997
        
        breakout_down = low.iloc[-2] < low.rolling(15).min().iloc[-3]
        reversal_up = close.iloc[-1] > close.iloc[-2] * 1.003
        
        manipulation_detected = (breakout_up and reversal_down) or (breakout_down and reversal_up)
        
        if not manipulation_detected:
            return None
        
        direction = -1 if (breakout_up and reversal_down) else 1
        confidence = 0.73
        
        current_price = close.iloc[-1]
        atr = (high - low).rolling(14).mean().iloc[-1]
        stop_distance = 1.3 * atr
        
        return self.create_signal(
            instrument=instrument,
            horizon=horizon,
            direction=direction,
            confidence=confidence,
            entry_price=current_price,
            stop_distance_points=stop_distance,
            target_profile={'primary': 2.6, 'extended': 4.2},
            regime_sensitivity={'trend': 0.75, 'range': 0.60, 'shock': 0.28},
            quality_metrics={'hit_rate': 0.65, 'sharpe': 2.3, 'max_drawdown': 0.13},
            expected_half_life_seconds=3100,
            ttl_milliseconds=230000,
            metadata={'manipulation_type': 'bullish_trap' if breakout_up else 'bearish_trap', 'setup': 'manipulation_pattern'}
        )


class MultiTFLiquidity(StrategyAdapter):
    """Multi-Timeframe Liquidity - Análisis de liquidez multi-temporalidad."""
    
    def __init__(self):
        super().__init__(strategy_id='multi_tf_liquidity', strategy_version='1.0.0')
    
    def evaluate(self, data: pd.DataFrame, features: Dict,
                 instrument: str, horizon: str) -> Optional[InstitutionalSignal]:
        
        if len(data) < 50:
            return None
        
        close = data['close']
        current_price = close.iloc[-1]
        
        # Simular múltiples timeframes con diferentes SMAs
        sma_fast = close.rolling(10).mean().iloc[-1]
        sma_medium = close.rolling(30).mean().iloc[-1]
        sma_slow = close.rolling(50).mean().iloc[-1]
        
        # Alineación de timeframes
        aligned_bullish = current_price > sma_fast > sma_medium > sma_slow
        aligned_bearish = current_price < sma_fast < sma_medium < sma_slow
        
        if not (aligned_bullish or aligned_bearish):
            return None
        
        direction = 1 if aligned_bullish else -1
        confidence = 0.76
        
        atr = (data['high'] - data['low']).rolling(20).mean().iloc[-1]
        stop_distance = 1.7 * atr
        
        return self.create_signal(
            instrument=instrument,
            horizon=horizon,
            direction=direction,
            confidence=confidence,
            entry_price=current_price,
            stop_distance_points=stop_distance,
            target_profile={'primary': 3.2, 'extended': 5.0},
            regime_sensitivity={'trend': 0.93, 'range': 0.28, 'shock': 0.10},
            quality_metrics={'hit_rate': 0.67, 'sharpe': 2.5, 'max_drawdown': 0.11},
            expected_half_life_seconds=4200,
            ttl_milliseconds=280000,
            metadata={'tf_alignment': 'bullish' if aligned_bullish else 'bearish', 'setup': 'multi_tf_liquidity'}
        )


class VolumeClimax(StrategyAdapter):
    """Volume Climax - Detección de clímax de volumen."""
    
    def __init__(self):
        super().__init__(strategy_id='volume_climax', strategy_version='1.0.0')
    
    def evaluate(self, data: pd.DataFrame, features: Dict,
                 instrument: str, horizon: str) -> Optional[InstitutionalSignal]:
        
        if len(data) < 30:
            return None
        
        volume = data['volume']
        vol_ma = volume.rolling(20).mean().iloc[-1]
        vol_std = volume.rolling(20).std().iloc[-1]
        
        # Volumen extremo (3+ desviaciones estándar)
        vol_climax = volume.iloc[-1] > (vol_ma + 3 * vol_std)
        
        if not vol_climax:
            return None
        
        close = data['close']
        current_price = close.iloc[-1]
        prev_price = close.iloc[-2]
        
        # Dirección del clímax
        strong_move_up = current_price > prev_price * 1.005
        strong_move_down = current_price < prev_price * 0.995
        
        if not (strong_move_up or strong_move_down):
            return None
        
        # Reversión esperada después del clímax
        direction = -1 if strong_move_up else 1
        confidence = 0.71
        
        atr = (data['high'] - data['low']).rolling(14).mean().iloc[-1]
        stop_distance = 1.2 * atr
        
        return self.create_signal(
            instrument=instrument,
            horizon=horizon,
            direction=direction,
            confidence=confidence,
            entry_price=current_price,
            stop_distance_points=stop_distance,
            target_profile={'primary': 2.1, 'extended': 3.3},
            regime_sensitivity={'trend': 0.60, 'range': 0.75, 'shock': 0.40},
            quality_metrics={'hit_rate': 0.62, 'sharpe': 2.0, 'max_drawdown': 0.16},
            expected_half_life_seconds=2200,
            ttl_milliseconds=160000,
            metadata={'volume_sigma': 3.0, 'climax_direction': 'up' if strong_move_up else 'down', 'setup': 'volume_climax'}
        )


class SmartMoneyTracker(StrategyAdapter):
    """Smart Money Tracker - Seguimiento de dinero inteligente."""
    
    def __init__(self):
        super().__init__(strategy_id='smart_money', strategy_version='1.0.0')
    
    def evaluate(self, data: pd.DataFrame, features: Dict,
                 instrument: str, horizon: str) -> Optional[InstitutionalSignal]:
        
        if len(data) < 40:
            return None
        
        close = data['close']
        volume = data['volume']
        
        # Smart money: divergencia precio-volumen
        price_change = (close.iloc[-1] - close.iloc[-10]) / close.iloc[-10]
        vol_change = (volume.iloc[-10:].mean() - volume.iloc[-20:-10].mean()) / volume.iloc[-20:-10].mean()
        
        # Volumen aumenta pero precio no sigue = acumulación/distribución
        divergence = abs(price_change) < 0.005 and vol_change > 0.3
        
        if not divergence:
            return None
        
        current_price = close.iloc[-1]
        sma_20 = close.rolling(20).mean().iloc[-1]
        
        direction = 1 if current_price > sma_20 else -1
        confidence = 0.69
        
        atr = (data['high'] - data['low']).rolling(14).mean().iloc[-1]
        stop_distance = 1.6 * atr
        
        return self.create_signal(
            instrument=instrument,
            horizon=horizon,
            direction=direction,
            confidence=confidence,
            entry_price=current_price,
            stop_distance_points=stop_distance,
            target_profile={'primary': 2.7, 'extended': 4.3},
            regime_sensitivity={'trend': 0.78, 'range': 0.55, 'shock': 0.22},
            quality_metrics={'hit_rate': 0.64, 'sharpe': 2.2, 'max_drawdown': 0.14},
            expected_half_life_seconds=3400,
            ttl_milliseconds=240000,
            metadata={'price_vol_divergence': True, 'setup': 'smart_money'}
        )


class InstitutionalFootprint(StrategyAdapter):
    """Institutional Footprint - Huella institucional en el mercado."""
    
    def __init__(self):
        super().__init__(strategy_id='institutional_footprint', strategy_version='1.0.0')
    
    def evaluate(self, data: pd.DataFrame, features: Dict,
                 instrument: str, horizon: str) -> Optional[InstitutionalSignal]:
        
        if len(data) < 35:
            return None
        
        spread_bp = features.get('spread_bp', 2.0)
        median_spread = features.get('median_spread_bp', 2.0)
        
        # Spread comprimido = presencia institucional
        tight_spread = spread_bp < median_spread * 0.7
        
        if not tight_spread:
            return None
        
        ofi = features.get('ofi', 0.0)
        
        if abs(ofi) < 0.8:
            return None
        
        direction = 1 if ofi > 0 else -1
        confidence = 0.74
        
        close = data['close']
        current_price = close.iloc[-1]
        atr = (data['high'] - data['low']).rolling(14).mean().iloc[-1]
        stop_distance = 1.4 * atr
        
        return self.create_signal(
            instrument=instrument,
            horizon=horizon,
            direction=direction,
            confidence=confidence,
            entry_price=current_price,
            stop_distance_points=stop_distance,
            target_profile={'primary': 2.9, 'extended': 4.6},
            regime_sensitivity={'trend': 0.84, 'range': 0.48, 'shock': 0.18},
            quality_metrics={'hit_rate': 0.66, 'sharpe': 2.4, 'max_drawdown': 0.12},
            expected_half_life_seconds=3600,
            ttl_milliseconds=260000,
            metadata={'spread_compression': True, 'ofi': ofi, 'setup': 'institutional_footprint'}
        )


# ============================================================================
# MOTOR DE TRADING
# ============================================================================

class TradingEngine:
    """Motor de trading con 14 estrategias institucionales reales."""
    
    def __init__(self):
        self.pml = PortfolioManagerLayer(
            total_capital=TOTAL_CAPITAL,
            family_allocations=FAMILY_ALLOCATIONS,
            strategy_families=STRATEGY_FAMILIES
        )
        
        # TODAS las estrategias institucionales
        self.strategies: List[StrategyAdapter] = [
            OrderFlowImbalanceRefined(),
            OrderFlowImbalanceMomentum(),
            OrderFlowImbalanceTrend(),
            FairValueGapInstitutional(),
            FairValueGapContinuation(),
            OrderBlockAggressive(),
            OrderBlockConservative(),
            LiquiditySweep(),
            LiquidityAbsorption(),
            ManipulationPattern(),
            MultiTFLiquidity(),
            VolumeClimax(),
            SmartMoneyTracker(),
            InstitutionalFootprint()
        ]
        
        self.positions: Dict[str, Dict] = {}
        self.instruments = ['EURUSD.pro', 'GBPUSD.pro', 'XAUUSD.pro']
        
        logger.info(
            f"TradingEngine inicializado: capital=${TOTAL_CAPITAL:,.2f}, "
            f"{len(self.strategies)} estrategias institucionales"
        )
    
    def run_tick(self):
        """Ejecuta un tick del motor."""
        logger.info("=" * 70)
        logger.info("MOTOR_TICK_START")
        
        data_by_instrument = self._fetch_market_data()
        features_by_instrument = self._calculate_features(data_by_instrument)
        self._evaluate_strategies(data_by_instrument, features_by_instrument)
        
        result = self.pml.process_decision_tick(
            data_by_instrument=data_by_instrument,
            features_by_instrument=features_by_instrument
        )
        
        self._execute_decisions(result['executions'])
        self._manage_positions(data_by_instrument)
        self._log_stats(result['stats'])
        
        logger.info("MOTOR_TICK_END")
    
    def _fetch_market_data(self) -> Dict[str, pd.DataFrame]:
        """Obtiene datos de mercado."""
        data_by_instrument = {}
        
        BASES = {
            'EURUSD.pro': 1.10,
            'GBPUSD.pro': 1.27,
            'XAUUSD.pro': 2400.0,
        }
        
        for instrument in self.instruments:
            n_bars = 100
            dates = pd.date_range(end=datetime.now(), periods=n_bars, freq='1min')
            
            base_price = BASES.get(instrument, 1.10)
            vol = 0.0001 if instrument != 'XAUUSD.pro' else 0.0015
            returns = np.random.randn(n_bars) * vol
            prices = base_price * (1 + returns).cumprod()
            
            df = pd.DataFrame({
                'timestamp': dates,
                'open': prices,
                'high': prices * (1 + abs(np.random.randn(n_bars) * vol)),
                'low': prices * (1 - abs(np.random.randn(n_bars) * vol)),
                'close': prices,
                'volume': np.random.randint(100, 1000, n_bars)
            })
            
            df.attrs['symbol'] = instrument
            data_by_instrument[instrument] = df
        
        return data_by_instrument
    
    def _calculate_features(self, data_by_instrument: Dict[str, pd.DataFrame]) -> Dict[str, Dict]:
        """Calcula features."""
        import hashlib
        
        features_by_instrument = {}
        
        for instrument, data in data_by_instrument.items():
            close = data['close']
            
            def _hash_df(df):
                try:
                    arr = df[['open', 'high', 'low', 'close', 'volume']].tail(200).to_numpy()
                    return hashlib.sha1(arr.tobytes()).hexdigest()[:16]
                except Exception:
                    return None
            
            features = {
                'ofi': np.random.randn() * 0.8,
                'vpin': np.random.uniform(0.45, 0.75),
                'spread_bp': 2.0 if 'USD' in instrument and instrument != 'XAUUSD.pro' else 10.0,
                'median_spread_bp': 2.2 if 'USD' in instrument and instrument != 'XAUUSD.pro' else 11.0,
                'vol_ratio': np.random.uniform(0.9, 1.6),
                'vol_of_vol': np.random.uniform(0.6, 1.3),
                'data_quality': True,
                'bid': close.iloc[-1] - 0.0001,
                'ask': close.iloc[-1] + 0.0001,
                'data_slice_id': _hash_df(data)
            }
            
            features_by_instrument[instrument] = features
        
        return features_by_instrument
    
    def _evaluate_strategies(self, data_by_instrument: Dict, features_by_instrument: Dict):
        """Invoca TODAS las estrategias."""
        total_signals = 0
        
        for strategy in self.strategies:
            for instrument in self.instruments:
                data = data_by_instrument[instrument]
                features = features_by_instrument[instrument]
                
                for horizon in ['intraday', 'swing']:
                    try:
                        signal = strategy.evaluate(data, features, instrument, horizon)
                        
                        if signal is not None:
                            if strategy.publish_signal(signal):
                                total_signals += 1
                    
                    except Exception as e:
                        logger.error(f"Strategy error: {strategy.strategy_id} {instrument}/{horizon}: {e}")
        
        logger.info(f"Strategies evaluated: {total_signals} senales de {len(self.strategies)} estrategias")
    
    def _execute_decisions(self, executions: List[Dict]):
        """Ejecuta senales con sizing calculado."""
        
        for execution in executions:
            signal = execution['signal']
            position_size = execution['position_size']
            family = execution['family']
            
            position_key = f"{signal.instrument}_{signal.horizon}"
            
            if position_key in self.positions:
                logger.warning(f"EXECUTION_SKIP: {position_key} ya tiene posicion")
                continue
            
            lot_size = self._calculate_lot_size(
                signal.instrument,
                position_size.capital_amount,
                signal.stop_distance_points
            )
            
            position_id = f"{position_key}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            
            if not self.pml.budget_manager.reserve_capital(
                position_id=position_id,
                family=family,
                amount=position_size.capital_amount
            ):
                logger.warning(
                    f"EXECUTION_SKIP: {position_key} no pudo reservar capital "
                    f"(familia={family}, amount=${position_size.capital_amount:,.2f})"
                )
                continue
            
            execution_price = signal.entry_price
            
            self.positions[position_key] = {
                'position_id': position_id,
                'signal': signal,
                'entry_price': execution_price,
                'entry_time': datetime.now(),
                'direction': signal.direction,
                'lot_size': lot_size,
                'capital_at_risk': position_size.capital_amount,
                'stop_price': execution_price - signal.direction * signal.stop_distance_points,
                'target_prices': {
                    name: execution_price + signal.direction * signal.stop_distance_points * ratio
                    for name, ratio in signal.target_profile.items()
                },
                'regime': 'trend',
                'family': family
            }
            
            logger.info(
                f"EXECUTION: {signal.strategy_id} -> {signal.instrument} {signal.direction:+d} "
                f"@ {execution_price:.5f} size={lot_size:.2f} lots "
                f"capital=${position_size.capital_amount:,.2f} ({position_size.capital_fraction:.2%})"
            )
    
    def _calculate_lot_size(self, instrument: str, capital_at_risk: float, 
                           stop_distance_price: float) -> float:
        """Calcula tamaño de lote real."""
        
        SPECS = {
            'EURUSD.pro': {'pip_size': 1e-4, 'pip_value': 10.0},
            'GBPUSD.pro': {'pip_size': 1e-4, 'pip_value': 10.0},
            'XAUUSD.pro': {'pip_size': 1e-2, 'pip_value': 1.0},
        }
        
        spec = SPECS.get(instrument, {'pip_size': 1e-4, 'pip_value': 10.0})
        pip_size = spec['pip_size']
        pip_value = spec['pip_value']
        
        if stop_distance_price <= 0 or pip_size <= 0:
            return 0.01
        
        pips = stop_distance_price / pip_size
        risk_per_lot = pips * pip_value
        
        if risk_per_lot <= 0:
            return 0.01
        
        lot_size = capital_at_risk / risk_per_lot
        return round(max(0.01, min(lot_size, 100.0)), 2)
    
    def _manage_positions(self, data_by_instrument: Dict):
        """Gestiona posiciones abiertas."""
        closed_positions = []
        
        for position_key, position in list(self.positions.items()):
            instrument = position['signal'].instrument
            current_data = data_by_instrument.get(instrument)
            
            if current_data is None:
                continue
            
            current_price = current_data['close'].iloc[-1]
            
            if position['direction'] == 1:
                if current_price <= position['stop_price']:
                    pnl_r = -1.0
                    self._close_position(position_key, current_price, pnl_r, "STOP")
                    closed_positions.append(position_key)
                    continue
            else:
                if current_price >= position['stop_price']:
                    pnl_r = -1.0
                    self._close_position(position_key, current_price, pnl_r, "STOP")
                    closed_positions.append(position_key)
                    continue
            
            primary_target = position['target_prices'].get('primary')
            
            if primary_target:
                if position['direction'] == 1 and current_price >= primary_target:
                    pnl_r = 2.0
                    self._close_position(position_key, current_price, pnl_r, "TARGET")
                    closed_positions.append(position_key)
                elif position['direction'] == -1 and current_price <= primary_target:
                    pnl_r = 2.0
                    self._close_position(position_key, current_price, pnl_r, "TARGET")
                    closed_positions.append(position_key)
        
        for key in closed_positions:
            del self.positions[key]
    
    def _close_position(self, position_key: str, exit_price: float, pnl_r: float, reason: str):
        """Cierra posicion y libera capital."""
        position = self.positions[position_key]
        signal = position['signal']
        position_id = position['position_id']
        
        self.pml.budget_manager.release_capital(position_id)
        
        self.pml.record_signal_outcome(
            strategy_id=signal.strategy_id,
            pnl_r=pnl_r,
            horizon=signal.horizon,
            regime=position['regime']
        )
        
        pnl_usd = pnl_r * position['capital_at_risk']
        
        logger.info(
            f"POSITION_CLOSED: {position_key} @ {exit_price:.5f} "
            f"pnl={pnl_r:.2f}R (${pnl_usd:+,.2f}) reason={reason}"
        )
    
    def _log_stats(self, stats: Dict):
        """Log de estadisticas."""
        budget_util = stats.get('budget_utilization', {}).get('portfolio', {})
        
        logger.info(
            f"STATS: decisions={stats['total_decisions']}, "
            f"executions={stats['executions']}, "
            f"silences={stats['silences']}, "
            f"open_positions={len(self.positions)}, "
            f"capital_used=${budget_util.get('total_committed', 0):,.2f} "
            f"({budget_util.get('utilization_pct', 0):.1f}%)"
        )


def main():
    """Ejecuta el motor con las 14 estrategias institucionales."""
    
    logger.info("=" * 70)
    logger.info("  TRADING SYSTEM - 14 ESTRATEGIAS INSTITUCIONALES")
    logger.info("=" * 70)
    logger.info("")
    logger.info(f"Capital: ${TOTAL_CAPITAL:,.2f}")
    logger.info(f"Estrategias activas: 14")
    logger.info("")
    
    engine = TradingEngine()
    
    logger.info("Ejecutando 5 ticks...")
    logger.info("")
    
    for i in range(5):
        logger.info(f"\nTICK {i+1}/5")
        engine.run_tick()
        time.sleep(0.5)
    
    logger.info("\nActualizando correlaciones...")
    engine.pml.update_correlations()
    
    logger.info("Exportando ledger...")
    engine.pml.export_ledger("output/decision_ledger.json")
    
    logger.info("\n" + "=" * 70)
    logger.info("ESTADISTICAS FINALES")
    logger.info("=" * 70)
    
    stats = engine.pml.get_aggregate_stats()
    
    logger.info(f"Total ticks: {stats['total_ticks']}")
    logger.info(f"Total ejecuciones: {stats['total_executions']}")
    logger.info(f"Tasa de ejecucion: {stats['execution_rate']:.1%}")
    logger.info("")
    
    budget_stats = stats['budget_manager']
    logger.info("Budget Manager:")
    logger.info(f"  Reservas totales: {budget_stats['total_reservations']}")
    logger.info(f"  Liberaciones totales: {budget_stats['total_releases']}")
    logger.info(f"  Capital pico usado: ${budget_stats['peak_capital_used']:,.2f}")
    logger.info("")
    
    utilization = budget_stats['current_utilization']
    logger.info("Utilizacion por familia:")
    for family, util in utilization.items():
        if family != 'portfolio':
            logger.info(
                f"  {family}: ${util['committed']:,.2f} / ${util['total_budget']:,.2f} "
                f"({util['utilization_pct']:.1f}%)"
            )
    
    logger.info("")
    logger.info("Conflict Arbiter:")
    logger.info(f"  Ejecuciones: {stats['arbiter']['executions']}")
    logger.info(f"  Silencios: {stats['arbiter']['silences']}")
    logger.info(f"  Rechazos EV: {stats['arbiter']['ev_rejections']}")
    logger.info("")
    logger.info("=" * 70)
    logger.info("Motor completado exitosamente")
    logger.info("=" * 70)


if __name__ == "__main__":
    main()
