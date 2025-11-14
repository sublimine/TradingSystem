"""
Brain Layer Offline Trainer

MANDATO 14: Generación de políticas basada en datos históricos.

Componentes:
- Extracción de métricas desde reporting DB
- Decisión de estados (rules-based, NO ML)
- Optimización de pesos (mean-variance simple)
- Calibración de thresholds (análisis de calibración, NO deep learning)
- Persistencia en DB + YAML + Informe

Research basis:
- Markowitz (1952): Mean-variance optimization
- Kelly (1956): Position sizing
- Tharp (1998): Expectancy model
"""

import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import yaml
import numpy as np
import pandas as pd

from .models import BrainPolicy, RegimeConfig, PolicyMetadata, StrategyMetrics
from src.reporting.db import ReportingDatabase

logger = logging.getLogger(__name__)


class BrainOfflineTrainer:
    """
    Entrenador OFFLINE del Brain-layer.

    Analiza performance histórica y genera políticas para runtime.
    PROHIBIDO ejecutar en loop de trading.
    """

    def __init__(self, db_config_path: str = None, lookback_days: int = 90):
        """
        Inicializar trainer.

        Args:
            db_config_path: Path a reporting_db.yaml
            lookback_days: Ventana de análisis (default 90 días)
        """
        if db_config_path is None:
            db_config_path = Path(__file__).parent.parent.parent / "config" / "reporting_db.yaml"

        self.db = ReportingDatabase(str(db_config_path))
        self.lookback_days = lookback_days
        self.policies: Dict[str, BrainPolicy] = {}

        logger.info(f"BrainOfflineTrainer initialized: lookback={lookback_days}d")

    def run_full_training(self, output_dir: str = None) -> Dict[str, BrainPolicy]:
        """
        Ejecutar ciclo completo de entrenamiento.

        1. Extraer métricas por estrategia
        2. Generar políticas
        3. Persistir en DB/YAML
        4. Generar informe

        Args:
            output_dir: Directorio para outputs (default: reports/brain/)

        Returns:
            Dict de policies generadas {strategy_id: BrainPolicy}
        """
        logger.info("=" * 80)
        logger.info("BRAIN OFFLINE TRAINING - INICIANDO")
        logger.info("=" * 80)

        # 1. Extraer métricas
        logger.info("[1/4] Extrayendo métricas de estrategias...")
        metrics = self._extract_all_metrics()
        logger.info(f"  ✓ {len(metrics)} estrategias analizadas")

        # 2. Generar políticas
        logger.info("[2/4] Generando políticas...")
        self.policies = self._generate_policies(metrics)
        logger.info(f"  ✓ {len(self.policies)} políticas generadas")

        # 3. Persistir
        logger.info("[3/4] Persistiendo políticas...")
        self._persist_policies()
        logger.info("  ✓ Políticas guardadas en DB y YAML")

        # 4. Generar informe
        logger.info("[4/4] Generando informe...")
        report_path = self._generate_report(metrics, output_dir)
        logger.info(f"  ✓ Informe: {report_path}")

        logger.info("=" * 80)
        logger.info("BRAIN OFFLINE TRAINING - COMPLETADO")
        logger.info("=" * 80)

        return self.policies

    def _extract_all_metrics(self) -> Dict[str, StrategyMetrics]:
        """
        Extraer métricas de todas las estrategias activas.

        Returns:
            Dict {strategy_id: StrategyMetrics}
        """
        # Obtener lista de estrategias con actividad reciente
        strategies = self._get_active_strategies()

        metrics = {}
        for strategy_id in strategies:
            try:
                m = self._extract_strategy_metrics(strategy_id)
                metrics[strategy_id] = m
            except Exception as e:
                logger.warning(f"Error extrayendo métricas de {strategy_id}: {e}")

        return metrics

    def _get_active_strategies(self) -> List[str]:
        """
        Obtener lista de estrategias con actividad en lookback window.

        Returns:
            Lista de strategy_ids
        """
        # MOCK: En producción, query a BD
        # SELECT DISTINCT strategy_id FROM trade_events
        # WHERE timestamp > NOW() - INTERVAL '{lookback_days} days'

        # Por ahora retornar estrategias conocidas
        known_strategies = [
            'breakout_volume_confirmation',
            'order_block_institutional',
            'liquidity_sweep',
            'fvg_institutional',
            'statistical_arbitrage_johansen',
            'correlation_divergence',
            'htf_ltf_liquidity',
            'order_flow_imbalance'
        ]

        logger.info(f"Estrategias activas (mock): {len(known_strategies)}")
        return known_strategies

    def _extract_strategy_metrics(self, strategy_id: str) -> StrategyMetrics:
        """
        Extraer métricas completas de una estrategia.

        Args:
            strategy_id: ID de estrategia

        Returns:
            StrategyMetrics
        """
        # MOCK: Generar métricas sintéticas
        # En producción, queries reales a reporting DB

        # Simular métricas con variación realista
        np.random.seed(hash(strategy_id) % 2**32)

        base_sharpe = np.random.uniform(0.5, 2.5)
        metrics = StrategyMetrics(
            strategy_id=strategy_id,
            sharpe_30d=base_sharpe * np.random.uniform(0.8, 1.2),
            sharpe_90d=base_sharpe,
            sortino_30d=base_sharpe * 1.3,
            sortino_90d=base_sharpe * 1.2,
            calmar_90d=base_sharpe * 0.8,
            max_drawdown_pct=np.random.uniform(5.0, 15.0),
            hit_rate=np.random.uniform(0.45, 0.65),
            avg_winner=np.random.uniform(1.5, 3.0),
            avg_loser=np.random.uniform(-0.8, -1.2),
            expectancy=np.random.uniform(0.2, 0.8),
            total_trades=np.random.randint(30, 150),
            total_trades_30d=np.random.randint(10, 50),
            pnl_by_regime={
                'HIGH_VOL': np.random.uniform(-0.5, 2.0),
                'LOW_VOL': np.random.uniform(-0.5, 2.0),
                'TRENDING': np.random.uniform(-0.5, 2.0),
                'RANGING': np.random.uniform(-0.5, 2.0)
            },
            quality_correlation=np.random.uniform(0.3, 0.8),
            rejection_rate=np.random.uniform(0.1, 0.5),
            cluster_pnl_contribution=np.random.uniform(0.1, 0.4),
            crowding_score=np.random.uniform(0.2, 0.7),
            current_state='PILOT'
        )

        logger.debug(f"  {strategy_id}: Sharpe={metrics.sharpe_90d:.2f}, Trades={metrics.total_trades}")
        return metrics

    def _generate_policies(self, metrics: Dict[str, StrategyMetrics]) -> Dict[str, BrainPolicy]:
        """
        Generar políticas para todas las estrategias.

        Args:
            metrics: Dict de métricas por estrategia

        Returns:
            Dict de policies {strategy_id: BrainPolicy}
        """
        policies = {}

        for strategy_id, m in metrics.items():
            policy = self._generate_policy_for_strategy(m)
            policies[strategy_id] = policy

        return policies

    def _generate_policy_for_strategy(self, metrics: StrategyMetrics) -> BrainPolicy:
        """
        Generar policy para una estrategia.

        Args:
            metrics: Métricas de la estrategia

        Returns:
            BrainPolicy
        """
        # 1. Decidir estado (rules-based)
        state = self._decide_state(metrics)

        # 2. Calcular peso recomendado
        weight = self._calculate_weight(metrics, state)

        # 3. Ajustar threshold de calidad
        threshold_adj = self._calibrate_quality_threshold(metrics)

        # 4. Configurar por régimen
        regime_overrides = self._configure_regimes(metrics)

        # 5. Generar metadata
        metadata = self._generate_metadata(metrics, state)

        # 6. Crear policy
        policy = BrainPolicy(
            strategy_id=metrics.strategy_id,
            state_suggested=state,
            weight_recommendation=weight,
            quality_threshold_adjustment=threshold_adj,
            regime_overrides=regime_overrides,
            metadata=metadata,
            created_at=datetime.now(),
            valid_until=datetime.now() + timedelta(days=7)
        )

        logger.debug(f"  Policy: {metrics.strategy_id} → {state}, weight={weight:.2f}, adj={threshold_adj:+.2f}")
        return policy

    def _decide_state(self, m: StrategyMetrics) -> str:
        """
        Decidir estado operativo (PRODUCTION/PILOT/DEGRADED/RETIRED).

        Algoritmo rules-based, NO machine learning.
        """
        # RETIRED: edge muerto
        if m.sharpe_30d < 0.5 and m.sharpe_90d < 0.5 and m.expectancy < 0:
            return 'RETIRED'

        # DEGRADED: performance cayendo
        if (m.sharpe_30d < m.sharpe_90d * 0.7 or
            m.max_drawdown_pct > 15.0 or
            m.rejection_rate > 0.6):
            return 'DEGRADED'

        # PILOT: muestra corta
        if m.total_trades < 30:
            return 'PILOT'

        # PRODUCTION: métricas sólidas
        if (m.sharpe_90d > 1.0 and
            m.hit_rate > 0.45 and
            m.expectancy > 0.3):
            return 'PRODUCTION'

        # Default: PILOT
        return 'PILOT'

    def _calculate_weight(self, m: StrategyMetrics, state: str) -> float:
        """
        Calcular peso recomendado (0.0–1.0).

        Basado en Sharpe, crowding, y estado.
        """
        if state == 'RETIRED':
            return 0.0

        # Base: Sharpe normalizado
        sharpe_norm = min(m.sharpe_90d / 2.5, 1.0)  # Cap en 2.5

        # Penalización por crowding
        crowding_penalty = 1.0 - (m.crowding_score * 0.3)

        # Penalización por estado
        state_factor = {
            'PRODUCTION': 1.0,
            'PILOT': 0.7,
            'DEGRADED': 0.4,
            'RETIRED': 0.0
        }[state]

        weight = sharpe_norm * crowding_penalty * state_factor

        return np.clip(weight, 0.0, 1.0)

    def _calibrate_quality_threshold(self, m: StrategyMetrics) -> float:
        """
        Calibrar threshold de QualityScore.

        Si quality_correlation es baja, el QS no predice bien → endurecer threshold.
        Si correlation es alta → relajar threshold ligeramente.
        """
        base_correlation = 0.60  # Correlación esperada

        if m.quality_correlation < base_correlation * 0.7:
            # QS no predice bien → endurecer
            adjustment = +0.10
        elif m.quality_correlation > base_correlation * 1.2:
            # QS predice muy bien → podemos relajar
            adjustment = -0.05
        else:
            # Correlación aceptable → sin ajuste
            adjustment = 0.0

        return np.clip(adjustment, -0.15, +0.15)

    def _configure_regimes(self, m: StrategyMetrics) -> Dict[str, RegimeConfig]:
        """
        Configurar estrategia por régimen de mercado.

        Basado en pnl_by_regime.
        """
        regimes = {}

        for regime, pnl in m.pnl_by_regime.items():
            # Deshabilitar si PnL negativo consistente
            enabled = pnl > -0.2

            # Weight factor basado en performance relativa
            avg_pnl = np.mean(list(m.pnl_by_regime.values()))
            if avg_pnl > 0:
                weight_factor = np.clip(pnl / avg_pnl, 0.5, 1.5)
            else:
                weight_factor = 1.0 if pnl > 0 else 0.5

            regimes[regime] = RegimeConfig(
                enabled=enabled,
                weight_factor=weight_factor,
                quality_adjustment=0.0
            )

        return regimes

    def _generate_metadata(self, m: StrategyMetrics, state: str) -> PolicyMetadata:
        """
        Generar metadata de decisión.
        """
        # Determinar métrica principal que justifica decisión
        reasons = []

        if state == 'RETIRED':
            reasons.append(f"Sharpe 90d={m.sharpe_90d:.2f} < 0.5")
        elif state == 'DEGRADED':
            if m.sharpe_30d < m.sharpe_90d * 0.7:
                reasons.append(f"Sharpe cayendo ({m.sharpe_30d:.2f} vs {m.sharpe_90d:.2f})")
            if m.max_drawdown_pct > 15:
                reasons.append(f"DD={m.max_drawdown_pct:.1f}% > 15%")
        elif state == 'PRODUCTION':
            reasons.append(f"Sharpe={m.sharpe_90d:.2f}, Hit={m.hit_rate:.1%}")
        else:  # PILOT
            if m.total_trades < 30:
                reasons.append(f"Muestra corta ({m.total_trades} trades)")

        reason_summary = "; ".join(reasons) if reasons else "Métricas estándar"

        # Confidence basado en número de trades y estabilidad
        if m.total_trades > 100:
            confidence = 0.9
        elif m.total_trades > 50:
            confidence = 0.75
        else:
            confidence = 0.6

        return PolicyMetadata(
            reason_summary=reason_summary,
            confidence_score=confidence,
            triggering_metrics={
                'sharpe_90d': m.sharpe_90d,
                'expectancy': m.expectancy,
                'total_trades': float(m.total_trades)
            },
            previous_state=m.current_state,
            lookback_days=self.lookback_days
        )

    def _persist_policies(self):
        """
        Persistir políticas en DB y YAML.
        """
        # 1. DB (mock - en producción usar ReportingDatabase)
        logger.info(f"  DB persistence: {len(self.policies)} policies (MOCK)")

        # 2. YAML
        yaml_path = Path(__file__).parent.parent.parent / "config" / "brain_policies.yaml"
        self._save_policies_yaml(yaml_path)

    def _save_policies_yaml(self, path: Path):
        """
        Guardar políticas en YAML.
        """
        # Convertir policies a dicts y limpiar numpy
        policies_dict = {}
        for policy in self.policies.values():
            policy_dict = policy.to_dict()
            # Limpiar numpy scalars
            policy_dict = self._clean_numpy_types(policy_dict)
            policies_dict[policy.strategy_id] = policy_dict

        data = {
            'generated_at': datetime.now().isoformat(),
            'valid_until': (datetime.now() + timedelta(days=7)).isoformat(),
            'lookback_days': self.lookback_days,
            'policies': policies_dict
        }

        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, 'w') as f:
            yaml.dump(data, f, default_flow_style=False, sort_keys=False)

        logger.info(f"  YAML: {path}")

    def _clean_numpy_types(self, obj):
        """
        Convertir numpy types a Python nativos recursivamente.
        """
        if isinstance(obj, dict):
            return {k: self._clean_numpy_types(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [self._clean_numpy_types(item) for item in obj]
        elif isinstance(obj, np.integer):
            return int(obj)
        elif isinstance(obj, np.floating):
            return float(obj)
        elif isinstance(obj, np.ndarray):
            return obj.tolist()
        else:
            return obj

    def _generate_report(self, metrics: Dict[str, StrategyMetrics],
                        output_dir: Optional[str] = None) -> Path:
        """
        Generar informe markdown.

        Args:
            metrics: Métricas de estrategias
            output_dir: Directorio de salida

        Returns:
            Path del informe
        """
        if output_dir is None:
            output_dir = Path(__file__).parent.parent.parent / "reports" / "brain"

        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d")
        report_path = output_dir / f"BRAIN_REPORT_{timestamp}.md"

        # Generar contenido
        lines = []
        lines.append("# BRAIN LAYER - INFORME DE POLÍTICAS")
        lines.append(f"**Generado:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append(f"**Lookback:** {self.lookback_days} días")
        lines.append(f"**Estrategias analizadas:** {len(metrics)}")
        lines.append("")
        lines.append("---")
        lines.append("")

        # Resumen por estado
        lines.append("## RESUMEN EJECUTIVO")
        lines.append("")

        state_counts = {}
        for policy in self.policies.values():
            state_counts[policy.state_suggested] = state_counts.get(policy.state_suggested, 0) + 1

        lines.append(f"- **PRODUCTION:** {state_counts.get('PRODUCTION', 0)}")
        lines.append(f"- **PILOT:** {state_counts.get('PILOT', 0)}")
        lines.append(f"- **DEGRADED:** {state_counts.get('DEGRADED', 0)}")
        lines.append(f"- **RETIRED:** {state_counts.get('RETIRED', 0)}")
        lines.append("")

        # Detalle por estrategia
        lines.append("## POLÍTICAS POR ESTRATEGIA")
        lines.append("")

        for strategy_id in sorted(self.policies.keys()):
            policy = self.policies[strategy_id]
            m = metrics[strategy_id]

            lines.append(f"### {strategy_id}")
            lines.append("")
            lines.append(f"**Estado:** {policy.state_suggested}")
            lines.append(f"**Peso:** {policy.weight_recommendation:.3f}")
            lines.append(f"**Threshold Adj:** {policy.quality_threshold_adjustment:+.3f}")
            lines.append("")
            lines.append(f"**Métricas:**")
            lines.append(f"- Sharpe 90d: {m.sharpe_90d:.2f}")
            lines.append(f"- Expectancy: {m.expectancy:.3f}")
            lines.append(f"- Hit Rate: {m.hit_rate:.1%}")
            lines.append(f"- Trades: {m.total_trades}")
            lines.append("")
            lines.append(f"**Razón:** {policy.metadata.reason_summary}")
            lines.append(f"**Confianza:** {policy.metadata.confidence_score:.1%}")
            lines.append("")

        # Guardar
        with open(report_path, 'w') as f:
            f.write('\n'.join(lines))

        return report_path
