"""
ExecutionMode - PLAN OMEGA FASE 3.2

Define los modos de ejecución del sistema de trading:
- PAPER: Trading simulado (sin dinero real)
- LIVE: Trading en vivo (dinero real)

Author: Elite Institutional Trading System
Version: 1.0
"""

from enum import Enum
from typing import Dict, Optional


class ExecutionMode(Enum):
    """
    Modos de ejecución del sistema.

    PAPER: Simulación completa (sin conexión a broker real)
    LIVE: Ejecución real en mercado (requiere broker conectado)
    """
    PAPER = "paper"
    LIVE = "live"

    def __str__(self) -> str:
        return self.value

    def is_paper(self) -> bool:
        """Retorna True si es modo PAPER."""
        return self == ExecutionMode.PAPER

    def is_live(self) -> bool:
        """Retorna True si es modo LIVE."""
        return self == ExecutionMode.LIVE

    @classmethod
    def from_string(cls, mode_str: str) -> 'ExecutionMode':
        """
        Crea ExecutionMode desde string.

        Args:
            mode_str: "paper" o "live"

        Returns:
            ExecutionMode correspondiente

        Raises:
            ValueError si mode_str no es válido
        """
        mode_str = mode_str.lower().strip()
        if mode_str == "paper":
            return cls.PAPER
        elif mode_str == "live":
            return cls.LIVE
        else:
            raise ValueError(f"Invalid execution mode: '{mode_str}'. Must be 'paper' or 'live'")


class ExecutionConfig:
    """
    Configuración de ejecución para el sistema.

    Controla parámetros de riesgo y límites según el modo.
    """

    def __init__(self,
                 mode: ExecutionMode,
                 initial_capital: float = 10000.0,
                 max_positions: int = 5,
                 max_risk_per_trade: float = 0.02,
                 max_daily_loss: float = 0.05,
                 broker_config: Optional[Dict] = None):
        """
        Inicializar configuración de ejecución.

        Args:
            mode: ExecutionMode (PAPER o LIVE)
            initial_capital: Capital inicial (solo PAPER)
            max_positions: Máximo de posiciones simultáneas
            max_risk_per_trade: Riesgo máximo por trade (0.02 = 2%)
            max_daily_loss: Pérdida máxima diaria (0.05 = 5%)
            broker_config: Configuración del broker (para LIVE)
        """
        self.mode = mode
        self.initial_capital = initial_capital
        self.max_positions = max_positions
        self.max_risk_per_trade = max_risk_per_trade
        self.max_daily_loss = max_daily_loss
        self.broker_config = broker_config or {}

        # Validar límites de riesgo
        if self.max_risk_per_trade > 0.025:
            raise ValueError(f"max_risk_per_trade ({self.max_risk_per_trade}) excede límite de 2.5%")

        if self.max_daily_loss > 0.10:
            raise ValueError(f"max_daily_loss ({self.max_daily_loss}) excede límite de 10%")

    def __repr__(self) -> str:
        return (f"ExecutionConfig(mode={self.mode}, capital={self.initial_capital}, "
                f"max_positions={self.max_positions}, max_risk={self.max_risk_per_trade:.1%})")

    def to_dict(self) -> Dict:
        """Convertir configuración a diccionario."""
        return {
            'mode': str(self.mode),
            'initial_capital': self.initial_capital,
            'max_positions': self.max_positions,
            'max_risk_per_trade': self.max_risk_per_trade,
            'max_daily_loss': self.max_daily_loss,
            'broker_config': self.broker_config
        }

    @classmethod
    def from_dict(cls, config_dict: Dict) -> 'ExecutionConfig':
        """Crear configuración desde diccionario."""
        mode = ExecutionMode.from_string(config_dict['mode'])
        return cls(
            mode=mode,
            initial_capital=config_dict.get('initial_capital', 10000.0),
            max_positions=config_dict.get('max_positions', 5),
            max_risk_per_trade=config_dict.get('max_risk_per_trade', 0.02),
            max_daily_loss=config_dict.get('max_daily_loss', 0.05),
            broker_config=config_dict.get('broker_config')
        )
