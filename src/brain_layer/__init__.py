"""
Brain Layer - Institutional Strategy Supervisor

MANDATO 14: Brain-layer para gestión adaptativa de estrategias.

Componentes:
- offline_trainer: Generación de políticas basada en performance histórica
- runtime: BrainPolicyStore para consultas en tiempo real
- models: Estructuras de datos (BrainPolicy, RegimeConfig, etc.)
"""

from .models import BrainPolicy, RegimeConfig, PolicyMetadata

__all__ = ['BrainPolicy', 'RegimeConfig', 'PolicyMetadata']
