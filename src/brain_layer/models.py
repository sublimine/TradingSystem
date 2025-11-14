"""
Brain Layer Data Models

Estructuras de datos para políticas del Brain-layer.
MANDATO 14 - NO machine learning, solo estructuras documentadas.
"""

from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from typing import Dict, Optional, Literal
import json


@dataclass
class RegimeConfig:
    """
    Configuración de estrategia para un régimen específico.

    Permite habilitar/deshabilitar y ajustar pesos por régimen de mercado.
    """
    enabled: bool = True                    # Activar en este régimen
    weight_factor: float = 1.0              # Multiplicador de peso (0.5–1.5)
    quality_adjustment: float = 0.0         # Ajuste adicional de threshold

    def __post_init__(self):
        """Validar rangos."""
        assert 0.0 <= self.weight_factor <= 2.0, "weight_factor debe estar en [0, 2]"
        assert -0.15 <= self.quality_adjustment <= 0.15, "quality_adjustment debe estar en [-0.15, +0.15]"


@dataclass
class PolicyMetadata:
    """
    Metadata de decisión para una BrainPolicy.

    Documenta el razonamiento y confianza detrás de una policy.
    """
    reason_summary: str                     # Motivo resumido
    confidence_score: float                 # 0–1, confianza en la recomendación
    triggering_metrics: Dict[str, float]    # Métricas que justifican cambios
    previous_state: Optional[str] = None    # Estado anterior (si cambió)
    lookback_days: int = 90                 # Ventana de análisis usada

    def __post_init__(self):
        """Validar rangos."""
        assert 0.0 <= self.confidence_score <= 1.0, "confidence_score debe estar en [0, 1]"
        assert self.lookback_days > 0, "lookback_days debe ser > 0"


@dataclass
class BrainPolicy:
    """
    Política del Brain-layer para una estrategia.

    Define estado operativo, peso, threshold de calidad y config por régimen.
    Generada OFFLINE por el trainer, consumida en RUNTIME.
    """
    strategy_id: str

    # Estado operativo recomendado
    state_suggested: Literal['PRODUCTION', 'PILOT', 'DEGRADED', 'RETIRED']

    # Peso relativo en cluster (0.0–1.0)
    weight_recommendation: float

    # Ajuste de threshold de QualityScore (-0.15 a +0.15)
    quality_threshold_adjustment: float

    # Configuración por régimen
    regime_overrides: Dict[str, RegimeConfig] = field(default_factory=dict)

    # Metadata de decisión
    metadata: PolicyMetadata = field(default_factory=lambda: PolicyMetadata(
        reason_summary="Default policy",
        confidence_score=0.5,
        triggering_metrics={}
    ))

    # Timestamps
    created_at: datetime = field(default_factory=datetime.now)
    valid_until: datetime = field(default_factory=lambda: datetime.now() + timedelta(days=7))

    def __post_init__(self):
        """Validar constraints institucionales."""
        assert self.state_suggested in {'PRODUCTION', 'PILOT', 'DEGRADED', 'RETIRED'}, \
            f"state_suggested inválido: {self.state_suggested}"

        assert 0.0 <= self.weight_recommendation <= 1.0, \
            f"weight_recommendation debe estar en [0, 1]: {self.weight_recommendation}"

        assert -0.15 <= self.quality_threshold_adjustment <= 0.15, \
            f"quality_threshold_adjustment debe estar en [-0.15, +0.15]: {self.quality_threshold_adjustment}"

        assert self.valid_until > self.created_at, \
            "valid_until debe ser posterior a created_at"

    def to_dict(self) -> dict:
        """Convertir a diccionario (para serialización)."""
        data = asdict(self)

        # Convertir datetime a ISO string
        data['created_at'] = self.created_at.isoformat()
        data['valid_until'] = self.valid_until.isoformat()

        # Convertir RegimeConfig a dict
        data['regime_overrides'] = {
            regime: asdict(config)
            for regime, config in self.regime_overrides.items()
        }

        return data

    def to_json(self) -> str:
        """Serializar a JSON."""
        return json.dumps(self.to_dict(), indent=2)

    @classmethod
    def from_dict(cls, data: dict) -> 'BrainPolicy':
        """Crear BrainPolicy desde diccionario."""
        # Parsear datetimes
        if isinstance(data.get('created_at'), str):
            data['created_at'] = datetime.fromisoformat(data['created_at'])
        if isinstance(data.get('valid_until'), str):
            data['valid_until'] = datetime.fromisoformat(data['valid_until'])

        # Parsear RegimeConfig
        if 'regime_overrides' in data:
            data['regime_overrides'] = {
                regime: RegimeConfig(**config)
                for regime, config in data['regime_overrides'].items()
            }

        # Parsear PolicyMetadata
        if 'metadata' in data and isinstance(data['metadata'], dict):
            data['metadata'] = PolicyMetadata(**data['metadata'])

        return cls(**data)

    def is_valid(self) -> bool:
        """Verificar si la policy está vigente."""
        return datetime.now() < self.valid_until

    def get_effective_threshold(self, regime: str = 'NORMAL', base: float = 0.60) -> float:
        """
        Calcular threshold efectivo para un régimen dado.

        Args:
            regime: Régimen de mercado
            base: Threshold base institucional (default 0.60)

        Returns:
            Threshold efectivo
        """
        effective = base + self.quality_threshold_adjustment

        # Aplicar ajuste de régimen si existe
        if regime in self.regime_overrides:
            effective += self.regime_overrides[regime].quality_adjustment

        # Limitar a rango razonable [0.40, 0.90]
        return max(0.40, min(0.90, effective))

    def is_enabled_in_regime(self, regime: str = 'NORMAL') -> bool:
        """
        Verificar si la estrategia está habilitada en un régimen dado.

        Args:
            regime: Régimen de mercado

        Returns:
            True si habilitada
        """
        if self.state_suggested == 'RETIRED':
            return False

        if regime in self.regime_overrides:
            return self.regime_overrides[regime].enabled

        return True  # Por defecto habilitada


@dataclass
class StrategyMetrics:
    """
    Métricas calculadas para una estrategia (usado en offline_trainer).
    """
    strategy_id: str

    # Performance metrics
    sharpe_30d: float = 0.0
    sharpe_90d: float = 0.0
    sortino_30d: float = 0.0
    sortino_90d: float = 0.0
    calmar_90d: float = 0.0

    max_drawdown_pct: float = 0.0
    hit_rate: float = 0.0
    avg_winner: float = 0.0
    avg_loser: float = 0.0
    expectancy: float = 0.0

    # Trade stats
    total_trades: int = 0
    total_trades_30d: int = 0

    # Regime breakdown
    pnl_by_regime: Dict[str, float] = field(default_factory=dict)

    # Quality analysis
    quality_correlation: float = 0.0  # Corr(QS, R)
    rejection_rate: float = 0.0

    # Cluster contribution
    cluster_pnl_contribution: float = 0.0
    crowding_score: float = 0.0

    # Estado actual
    current_state: str = 'PILOT'
