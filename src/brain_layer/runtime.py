"""
Brain Layer Runtime

MANDATO 14: BrainPolicyStore para consultas de políticas en tiempo real.

Responsabilidades:
- Cargar policies desde DB/YAML al inicio
- Exponer API thread-safe
- Cache en memoria con TTL
"""

import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional
from threading import RLock
import yaml

from .models import BrainPolicy

logger = logging.getLogger(__name__)


class BrainPolicyStore:
    """
    Store de políticas del Brain para runtime.

    Carga policies desde DB/YAML y expone API thread-safe para consultas.
    """

    def __init__(self, yaml_path: Optional[str] = None, db=None):
        """
        Inicializar store.

        Args:
            yaml_path: Path a brain_policies.yaml (opcional)
            db: ReportingDatabase instance (opcional, para cargar desde DB)
        """
        self._policies: Dict[str, BrainPolicy] = {}
        self._lock = RLock()  # Thread-safe
        self._yaml_path = yaml_path or (
            Path(__file__).parent.parent.parent / "config" / "brain_policies.yaml"
        )
        self._db = db

        self.reload_policies()

    def reload_policies(self) -> int:
        """
        Recargar políticas desde YAML/DB.

        Returns:
            Número de policies cargadas
        """
        with self._lock:
            # Intentar cargar desde YAML primero
            count = self._load_from_yaml()

            if count == 0:
                logger.warning("No policies loaded from YAML, usando defaults")
                self._policies = {}

            logger.info(f"BrainPolicyStore: {count} policies cargadas")
            return count

    def _load_from_yaml(self) -> int:
        """
        Cargar policies desde YAML.

        Returns:
            Número de policies cargadas
        """
        path = Path(self._yaml_path)

        if not path.exists():
            logger.warning(f"brain_policies.yaml no encontrado: {path}")
            return 0

        try:
            with open(path, 'r') as f:
                data = yaml.safe_load(f)

            policies_data = data.get('policies', {})

            for strategy_id, policy_dict in policies_data.items():
                try:
                    policy = BrainPolicy.from_dict(policy_dict)

                    # Verificar vigencia
                    if not policy.is_valid():
                        logger.warning(f"Policy expirada: {strategy_id}")
                        continue

                    self._policies[strategy_id] = policy

                except Exception as e:
                    logger.error(f"Error parseando policy {strategy_id}: {e}")

            logger.info(f"Loaded {len(self._policies)} policies from YAML")
            return len(self._policies)

        except Exception as e:
            logger.error(f"Error cargando YAML: {e}")
            return 0

    def get_policy(self, strategy_id: str) -> Optional[BrainPolicy]:
        """
        Obtener policy de una estrategia.

        Args:
            strategy_id: ID de estrategia

        Returns:
            BrainPolicy o None si no existe
        """
        with self._lock:
            policy = self._policies.get(strategy_id)

            if policy and not policy.is_valid():
                logger.warning(f"Policy expirada: {strategy_id}")
                return None

            return policy

    def get_state(self, strategy_id: str) -> str:
        """
        Obtener estado de una estrategia.

        Args:
            strategy_id: ID de estrategia

        Returns:
            Estado (PRODUCTION/PILOT/DEGRADED/RETIRED) o 'PILOT' si no hay policy
        """
        policy = self.get_policy(strategy_id)
        return policy.state_suggested if policy else 'PILOT'

    def get_weight(self, strategy_id: str) -> float:
        """
        Obtener peso recomendado de una estrategia.

        Args:
            strategy_id: ID de estrategia

        Returns:
            Peso 0.0–1.0 (default 0.5 si no hay policy)
        """
        policy = self.get_policy(strategy_id)
        return policy.weight_recommendation if policy else 0.5

    def get_effective_quality_threshold(self, strategy_id: str,
                                       regime: str = 'NORMAL',
                                       base: float = 0.60) -> float:
        """
        Obtener threshold efectivo de QualityScore.

        Args:
            strategy_id: ID de estrategia
            regime: Régimen de mercado
            base: Threshold base (default 0.60)

        Returns:
            Threshold efectivo
        """
        policy = self.get_policy(strategy_id)

        if not policy:
            return base

        return policy.get_effective_threshold(regime, base)

    def is_enabled_in_regime(self, strategy_id: str, regime: str = 'NORMAL') -> bool:
        """
        Verificar si estrategia está habilitada en un régimen.

        Args:
            strategy_id: ID de estrategia
            regime: Régimen de mercado

        Returns:
            True si habilitada (default True si no hay policy)
        """
        policy = self.get_policy(strategy_id)

        if not policy:
            return True

        return policy.is_enabled_in_regime(regime)

    def get_all_policies(self) -> Dict[str, BrainPolicy]:
        """
        Obtener todas las policies activas.

        Returns:
            Dict {strategy_id: BrainPolicy}
        """
        with self._lock:
            return {
                sid: policy
                for sid, policy in self._policies.items()
                if policy.is_valid()
            }

    def get_statistics(self) -> Dict:
        """
        Obtener estadísticas del store.

        Returns:
            Dict con stats
        """
        with self._lock:
            policies = self.get_all_policies()

            state_counts = {}
            for policy in policies.values():
                state = policy.state_suggested
                state_counts[state] = state_counts.get(state, 0) + 1

            return {
                'total_policies': len(policies),
                'states': state_counts,
                'yaml_path': str(self._yaml_path),
                'last_load': datetime.now().isoformat()
            }
