"""
Execution Mode - Modos de ejecución del sistema

Define explícitamente el modo de operación:
- RESEARCH: Backtest histórico, NO trading real
- PAPER: Trading simulado, fills por VenueSimulator, NO broker
- LIVE: Trading REAL, órdenes al broker, DINERO REAL EN RIESGO

CRITICAL: Separación quirúrgica entre modos.
NO puede haber ambigüedad en qué modo se está ejecutando.

Author: SUBLIMINE Institutional Trading System
Date: 2025-11-14
Mandato: MANDATO 23 - Live Execution & Kill Switch
"""

from enum import Enum
from typing import Dict


class ExecutionMode(Enum):
    """
    Modo de ejecución del sistema.

    RESEARCH: Análisis histórico, backtest
    PAPER: Simulación en tiempo real (NO órdenes reales)
    LIVE: Trading real (ÓRDENES REALES AL BROKER)
    """

    RESEARCH = "research"
    PAPER = "paper"
    LIVE = "live"

    def allows_real_execution(self) -> bool:
        """
        Indica si el modo permite ejecución REAL al broker.

        Returns:
            True SOLO para LIVE, False para RESEARCH/PAPER
        """
        return self == ExecutionMode.LIVE

    def is_simulated(self) -> bool:
        """
        Indica si el modo usa simulación.

        Returns:
            True para RESEARCH/PAPER, False para LIVE
        """
        return self in [ExecutionMode.RESEARCH, ExecutionMode.PAPER]

    def requires_kill_switch(self) -> bool:
        """
        Indica si el modo requiere kill switch activo.

        Returns:
            True SOLO para LIVE, False para RESEARCH/PAPER
        """
        return self == ExecutionMode.LIVE

    def requires_broker_connection(self) -> bool:
        """
        Indica si el modo requiere conexión real al broker.

        Returns:
            True para PAPER (datos) y LIVE (datos+ejecución)
            False para RESEARCH (datos históricos)
        """
        return self in [ExecutionMode.PAPER, ExecutionMode.LIVE]

    def get_description(self) -> str:
        """
        Descripción del modo.

        Returns:
            String descriptivo
        """
        descriptions = {
            ExecutionMode.RESEARCH: "Historical backtest - NO real-time data, NO execution",
            ExecutionMode.PAPER: "Simulated trading - Real-time data, SIMULATED execution",
            ExecutionMode.LIVE: "LIVE TRADING - Real-time data, REAL execution, MONEY AT RISK"
        }
        return descriptions[self]

    def get_risk_level(self) -> str:
        """
        Nivel de riesgo del modo.

        Returns:
            String con nivel de riesgo
        """
        risk_levels = {
            ExecutionMode.RESEARCH: "ZERO - No execution",
            ExecutionMode.PAPER: "ZERO - Simulated only",
            ExecutionMode.LIVE: "CRITICAL - Real money at risk"
        }
        return risk_levels[self]

    @classmethod
    def from_string(cls, mode_str: str) -> 'ExecutionMode':
        """
        Crea ExecutionMode desde string.

        Args:
            mode_str: String del modo ('research', 'paper', 'live')

        Returns:
            ExecutionMode correspondiente

        Raises:
            ValueError: Si modo no es válido
        """
        mode_str = mode_str.lower().strip()

        mode_map = {
            'research': ExecutionMode.RESEARCH,
            'backtest': ExecutionMode.RESEARCH,  # Alias
            'historical': ExecutionMode.RESEARCH,  # Alias
            'paper': ExecutionMode.PAPER,
            'demo': ExecutionMode.PAPER,  # Alias
            'simulated': ExecutionMode.PAPER,  # Alias
            'live': ExecutionMode.LIVE,
            'real': ExecutionMode.LIVE,  # Alias
            'production': ExecutionMode.LIVE,  # Alias
        }

        if mode_str not in mode_map:
            valid_modes = ', '.join(mode_map.keys())
            raise ValueError(
                f"Invalid execution mode: '{mode_str}'. "
                f"Valid modes: {valid_modes}"
            )

        return mode_map[mode_str]

    def to_dict(self) -> Dict:
        """
        Serializa a diccionario.

        Returns:
            Dict con detalles del modo
        """
        return {
            'mode': self.value,
            'allows_real_execution': self.allows_real_execution(),
            'is_simulated': self.is_simulated(),
            'requires_kill_switch': self.requires_kill_switch(),
            'requires_broker_connection': self.requires_broker_connection(),
            'description': self.get_description(),
            'risk_level': self.get_risk_level()
        }


def validate_execution_mode_transition(
    current_mode: ExecutionMode,
    target_mode: ExecutionMode
) -> tuple[bool, str]:
    """
    Valida si una transición de modo es permitida.

    Args:
        current_mode: Modo actual
        target_mode: Modo objetivo

    Returns:
        (is_allowed, reason)
    """
    # LIVE → PAPER/RESEARCH: OK (reducir riesgo)
    if current_mode == ExecutionMode.LIVE:
        return True, "Downgrade from LIVE allowed"

    # PAPER → RESEARCH: OK
    if current_mode == ExecutionMode.PAPER and target_mode == ExecutionMode.RESEARCH:
        return True, "Downgrade from PAPER to RESEARCH allowed"

    # RESEARCH → PAPER: OK
    if current_mode == ExecutionMode.RESEARCH and target_mode == ExecutionMode.PAPER:
        return True, "Upgrade from RESEARCH to PAPER allowed"

    # PAPER/RESEARCH → LIVE: Requiere confirmación explícita
    if target_mode == ExecutionMode.LIVE:
        return False, "Transition to LIVE requires explicit operator confirmation"

    # Mismo modo
    if current_mode == target_mode:
        return True, "No transition needed"

    # Otras transiciones
    return True, "Transition allowed"
