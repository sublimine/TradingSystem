"""
Gatekeepers Package - Sistema de Protección Institucional

Este paquete contiene el sistema completo de gatekeepers que protege
el sistema de trading de condiciones adversas de mercado.

Componentes:
- KylesLambdaEstimator: Monitoreo de impacto de mercado
- ePINEstimator: Detección de informed trading
- SpreadMonitor: Vigilancia de costos de transacción
- GatekeeperIntegrator: Coordinación y decisión unificada
"""

from gatekeepers.kyles_lambda import KylesLambdaEstimator
from gatekeepers.epin_estimator import ePINEstimator
from gatekeepers.spread_monitor import SpreadMonitor
from gatekeepers.gatekeeper_integrator import GatekeeperIntegrator

__all__ = [
    'KylesLambdaEstimator',
    'ePINEstimator',
    'SpreadMonitor',
    'GatekeeperIntegrator'
]
