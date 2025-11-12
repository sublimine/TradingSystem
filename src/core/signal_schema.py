"""
Signal Schema Institucional - Versión Corregida
Con metadata explícito y todas las claves documentadas.
"""

from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Dict, Optional, Any
import logging

logger = logging.getLogger(__name__)


@dataclass
class InstitutionalSignal:
    """
    Schema canónico para señales institucionales.
    
    CORRECCIONES vs versión previa:
    - metadata ahora es campo explícito con factory
    - Claves esperadas en metadata documentadas
    - Método to_dict() para serialización
    """
    
    # ===== IDENTIFICACIÓN =====
    instrument: str
    timestamp: datetime
    horizon: str  # 'scalp', 'intraday', 'swing'
    strategy_id: str
    strategy_version: str
    
    # ===== INTENCIÓN DIRECCIONAL =====
    direction: int  # +1 LONG, -1 SHORT
    confidence: float  # [0, 1]
    
    # ===== CARACTERÍSTICAS TEMPORALES =====
    expected_half_life_seconds: int
    ttl_milliseconds: int
    
    # ===== PARÁMETROS DE RIESGO =====
    entry_price: float
    stop_distance_points: float
    target_profile: Dict[str, float] = field(default_factory=dict)
    
    # ===== SENSIBILIDAD A RÉGIMEN =====
    regime_sensitivity: Dict[str, float] = field(default_factory=dict)
    
    # ===== MÉTRICAS DE CALIDAD =====
    quality_metrics: Dict[str, float] = field(default_factory=dict)
    
    # ===== METADATA ADICIONAL =====
    metadata: Dict[str, Any] = field(default_factory=dict)
    """
    Claves esperadas en metadata (documentación):
    
    OBLIGATORIAS:
    - risk_reward_ratio: float - Ratio R:R de la señal
    - signal_id: str - ID único de la señal (ULID)
    - data_slice_hash: str - Hash del slice de datos usado
    
    OPCIONALES:
    - execution_style: str - 'aggressive' o 'passive'
    - feature_hash: str - Hash de features usados (para colinealidad)
    - alpha_source: str - Descripción del alpha
    - conviction_level: str - 'high', 'medium', 'low'
    - hedge_intent: bool - Si es hedge intencional
    """
    
    def is_expired(self) -> bool:
        """Verifica si señal expiró por TTL."""
        age_ms = (datetime.now() - self.timestamp).total_seconds() * 1000
        return age_ms > self.ttl_milliseconds
    
    def calculate_regime_weight(self, regime_probs: Dict[str, float]) -> float:
        """
        Calcula peso ajustado por régimen.
        Formula: weight = confidence × Σ(p_regime × sensitivity_regime)
        """
        regime_weight = sum(
            regime_probs.get(regime, 0) * self.regime_sensitivity.get(regime, 0)
            for regime in ['trend', 'range', 'shock']
        )
        return self.confidence * regime_weight
    
    def to_dict(self) -> Dict:
        """Serializa a dict para ledger."""
        return asdict(self)
    
    def __str__(self) -> str:
        direction_str = "LONG" if self.direction > 0 else "SHORT"
        return (
            f"InstitutionalSignal({self.strategy_id} → {self.instrument} {direction_str} "
            f"conf={self.confidence:.2f} hl={self.expected_half_life_seconds}s "
            f"signal_id={self.metadata.get('signal_id', 'NONE')})"
        )
