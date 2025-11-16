"""
BrokerAdapter - PLAN OMEGA FASE 3.2

Interfaz abstracta para adaptadores de brokers.
Permite ejecutar órdenes en modo PAPER o LIVE de forma uniforme.

Author: Elite Institutional Trading System
Version: 1.0
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional
from datetime import datetime
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)


@dataclass
class Order:
    """
    Orden de trading institucional.

    Representa una orden completa con todos los parámetros necesarios
    para ejecución en broker.
    """
    order_id: str
    symbol: str
    direction: str  # 'LONG' o 'SHORT'
    entry_price: float
    stop_loss: float
    take_profit: float
    position_size: float  # En lotes
    strategy_name: str
    timestamp: datetime
    status: str = 'PENDING'  # PENDING, FILLED, REJECTED, CANCELLED
    fill_price: Optional[float] = None
    fill_time: Optional[datetime] = None
    metadata: Optional[Dict] = None

    def __post_init__(self):
        """Validar orden después de inicialización."""
        if self.direction not in ['LONG', 'SHORT']:
            raise ValueError(f"Invalid direction: {self.direction}")

        if self.position_size <= 0:
            raise ValueError(f"Invalid position_size: {self.position_size}")

        # Validar SL/TP según dirección
        if self.direction == 'LONG':
            if self.stop_loss >= self.entry_price:
                raise ValueError(f"LONG: SL ({self.stop_loss}) debe ser < entry ({self.entry_price})")
            if self.take_profit <= self.entry_price:
                raise ValueError(f"LONG: TP ({self.take_profit}) debe ser > entry ({self.entry_price})")
        else:  # SHORT
            if self.stop_loss <= self.entry_price:
                raise ValueError(f"SHORT: SL ({self.stop_loss}) debe ser > entry ({self.entry_price})")
            if self.take_profit >= self.entry_price:
                raise ValueError(f"SHORT: TP ({self.take_profit}) debe ser < entry ({self.entry_price})")

    def to_dict(self) -> Dict:
        """Convertir orden a diccionario."""
        return {
            'order_id': self.order_id,
            'symbol': self.symbol,
            'direction': self.direction,
            'entry_price': self.entry_price,
            'stop_loss': self.stop_loss,
            'take_profit': self.take_profit,
            'position_size': self.position_size,
            'strategy_name': self.strategy_name,
            'timestamp': self.timestamp.isoformat(),
            'status': self.status,
            'fill_price': self.fill_price,
            'fill_time': self.fill_time.isoformat() if self.fill_time else None,
            'metadata': self.metadata
        }


@dataclass
class Position:
    """
    Posición abierta en el broker.

    Representa una posición activa con tracking de P&L.
    """
    position_id: str
    order_id: str
    symbol: str
    direction: str
    entry_price: float
    entry_time: datetime
    stop_loss: float
    take_profit: float
    position_size: float
    strategy_name: str
    current_price: float = 0.0
    unrealized_pnl: float = 0.0
    metadata: Optional[Dict] = None

    def update_pnl(self, current_price: float):
        """
        Actualizar P&L no realizado basado en precio actual.

        Args:
            current_price: Precio actual del mercado
        """
        self.current_price = current_price

        if self.direction == 'LONG':
            price_diff = current_price - self.entry_price
        else:  # SHORT
            price_diff = self.entry_price - current_price

        # Calcular P&L en pips (assuming 4-digit pricing)
        pips = price_diff * 10000
        # P&L en USD (aproximado: $10 por pip por lote para EURUSD)
        self.unrealized_pnl = pips * 10 * self.position_size

    def to_dict(self) -> Dict:
        """Convertir posición a diccionario."""
        return {
            'position_id': self.position_id,
            'order_id': self.order_id,
            'symbol': self.symbol,
            'direction': self.direction,
            'entry_price': self.entry_price,
            'entry_time': self.entry_time.isoformat(),
            'stop_loss': self.stop_loss,
            'take_profit': self.take_profit,
            'position_size': self.position_size,
            'strategy_name': self.strategy_name,
            'current_price': self.current_price,
            'unrealized_pnl': self.unrealized_pnl,
            'metadata': self.metadata
        }


class BrokerAdapter(ABC):
    """
    Interfaz abstracta para adaptadores de brokers.

    Define la API común que todos los brokers deben implementar.
    Permite cambiar entre PAPER y LIVE sin modificar código del sistema.
    """

    def __init__(self, config: Dict):
        """
        Inicializar adaptador.

        Args:
            config: Configuración del broker
        """
        self.config = config
        self.logger = logging.getLogger(self.__class__.__name__)
        self.connected = False

    @abstractmethod
    def connect(self) -> bool:
        """
        Conectar al broker.

        Returns:
            True si conexión exitosa, False en caso contrario
        """
        pass

    @abstractmethod
    def disconnect(self):
        """Desconectar del broker."""
        pass

    @abstractmethod
    def submit_order(self, order: Order) -> bool:
        """
        Enviar orden al broker.

        Args:
            order: Orden a ejecutar

        Returns:
            True si orden enviada exitosamente, False en caso contrario
        """
        pass

    @abstractmethod
    def cancel_order(self, order_id: str) -> bool:
        """
        Cancelar orden pendiente.

        Args:
            order_id: ID de la orden a cancelar

        Returns:
            True si orden cancelada, False en caso contrario
        """
        pass

    @abstractmethod
    def get_positions(self) -> List[Position]:
        """
        Obtener todas las posiciones abiertas.

        Returns:
            Lista de posiciones abiertas
        """
        pass

    @abstractmethod
    def close_position(self, position_id: str) -> bool:
        """
        Cerrar posición abierta.

        Args:
            position_id: ID de la posición a cerrar

        Returns:
            True si posición cerrada, False en caso contrario
        """
        pass

    @abstractmethod
    def get_account_balance(self) -> float:
        """
        Obtener balance actual de la cuenta.

        Returns:
            Balance en USD
        """
        pass

    @abstractmethod
    def get_account_equity(self) -> float:
        """
        Obtener equity actual (balance + P&L no realizado).

        Returns:
            Equity en USD
        """
        pass

    @abstractmethod
    def update_positions(self, market_data: Dict):
        """
        Actualizar posiciones con datos de mercado actuales.

        Verifica stops/targets y actualiza P&L no realizado.

        Args:
            market_data: Datos actuales del mercado {symbol: {'bid': x, 'ask': y, ...}}
        """
        pass

    def is_connected(self) -> bool:
        """Retorna True si adaptador está conectado."""
        return self.connected

    def get_order_status(self, order_id: str) -> Optional[str]:
        """
        Obtener status de una orden.

        Args:
            order_id: ID de la orden

        Returns:
            Status de la orden o None si no se encuentra
        """
        # Implementación por defecto - subclases pueden override
        return None
