"""
Position Sizer - Calculador de tamanos de posicion institucional
"""

import logging
from typing import Dict, Optional
from dataclasses import dataclass
import numpy as np

from core.signal_schema import InstitutionalSignal

logger = logging.getLogger(__name__)


@dataclass
class PositionSize:
    """Resultado del calculo de sizing."""
    capital_fraction: float
    capital_amount: float
    reasoning: str
    kelly_fraction: float
    adjusted_fraction: float
    budget_constrained: bool


class PositionSizer:
    """Calculador de tamanos de posicion basado en Kelly Criterion ajustado."""
    
    def __init__(self,
                 total_capital: float,
                 kelly_fraction: float = 0.25,
                 min_position_pct: float = 0.002,
                 max_position_pct: float = 0.05,
                 shock_regime_multiplier: float = 0.50):
        
        self.total_capital = total_capital
        self.kelly_fraction = kelly_fraction
        self.min_position_pct = min_position_pct
        self.max_position_pct = max_position_pct
        self.shock_regime_multiplier = shock_regime_multiplier
        
        logger.info(
            f"PositionSizer inicializado: kelly_frac={kelly_fraction}, "
            f"caps=[{min_position_pct:.2%}, {max_position_pct:.2%}]"
        )
    
    def calculate_size(self,
                       signal: 'InstitutionalSignal',
                       regime_probs: Dict[str, float],
                       available_capital_fraction: float = 1.0,
                       historical_stats: Optional[Dict] = None) -> PositionSize:
        
        reasoning_parts = []
        
        kelly_optimal = self._calculate_kelly(signal, historical_stats)
        reasoning_parts.append(f"Kelly optimo: {kelly_optimal:.4f}")
        
        kelly_adjusted = kelly_optimal * self.kelly_fraction
        reasoning_parts.append(f"Kelly ajustado ({self.kelly_fraction:.0%}): {kelly_adjusted:.4f}")
        
        confidence_multiplier = self._get_confidence_multiplier(signal.confidence)
        size_after_confidence = kelly_adjusted * confidence_multiplier
        reasoning_parts.append(f"Ajuste confianza ({confidence_multiplier:.2f}x): {size_after_confidence:.4f}")
        
        regime_multiplier = self._get_regime_multiplier(regime_probs, signal)
        size_after_regime = size_after_confidence * regime_multiplier
        reasoning_parts.append(f"Ajuste regimen ({regime_multiplier:.2f}x): {size_after_regime:.4f}")
        
        size_capped = np.clip(size_after_regime, self.min_position_pct, self.max_position_pct)
        if size_capped != size_after_regime:
            reasoning_parts.append(f"Aplicado cap: {size_capped:.4f}")
        
        budget_constrained = False
        
        if size_capped > available_capital_fraction:
            size_final = available_capital_fraction
            budget_constrained = True
            reasoning_parts.append(f"Limitado por budget: {size_final:.4f}")
        else:
            size_final = size_capped
        
        capital_amount = size_final * self.total_capital
        
        reasoning = " -> ".join(reasoning_parts)
        
        logger.info(
            f"SIZING_CALCULATED: {signal.strategy_id} {signal.instrument} "
            f"size={size_final:.4f} (${capital_amount:,.2f})"
        )
        
        return PositionSize(
            capital_fraction=size_final,
            capital_amount=capital_amount,
            reasoning=reasoning,
            kelly_fraction=kelly_optimal,
            adjusted_fraction=size_capped,
            budget_constrained=budget_constrained
        )
    
    def _calculate_kelly(self, signal: 'InstitutionalSignal', 
                        historical_stats: Optional[Dict]) -> float:
        
        if historical_stats and historical_stats.get('trades', 0) > 30:
            win_rate = historical_stats['wins'] / historical_stats['trades']
            avg_win = historical_stats.get('avg_win_r', 2.0)
            avg_loss = abs(historical_stats.get('avg_loss_r', -1.0))

            # P1-010: Usar max() para mínimo razonable en lugar de check exacto
            avg_loss = max(avg_loss, 0.1)  # Mínimo razonable para evitar b gigante

            b = avg_win / avg_loss
        else:
            primary_target = list(signal.target_profile.values())[0] if signal.target_profile else 2.0
            b = primary_target
            win_rate = 0.50 + (signal.confidence - 0.50) * 0.20

        # P1-010: Validar b > 0 para evitar división por cero
        if b <= 0:
            return 0.0

        p = win_rate
        q = 1 - p

        kelly = (p * b - q) / b

        return max(0.0, kelly)
    
    def _get_confidence_multiplier(self, confidence: float) -> float:
        if confidence >= 0.90:
            return 1.2
        elif confidence >= 0.70:
            return 1.0
        elif confidence >= 0.50:
            return 0.8
        else:
            return 0.6
    
    def _get_regime_multiplier(self, regime_probs: Dict[str, float],
                               signal: 'InstitutionalSignal') -> float:
        
        dominant_regime = max(regime_probs, key=regime_probs.get)
        regime_prob = regime_probs[dominant_regime]
        
        if dominant_regime == 'shock' and regime_prob > 0.40:
            return self.shock_regime_multiplier
        
        strategy_sensitivity = signal.regime_sensitivity.get(dominant_regime, 0.5)
        
        if strategy_sensitivity >= 0.7:
            return 1.1
        elif strategy_sensitivity >= 0.5:
            return 1.0
        else:
            return 0.8
