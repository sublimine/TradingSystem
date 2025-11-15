"""
Execution Adapter - Interface abstracta para backends de ejecución

Define el contrato que TODOS los adapters deben cumplir:
- PaperExecutionAdapter: Simulación (VenueSimulator)
- LiveExecutionAdapter: Ejecución real (BrokerClient + MT5)

CRITICAL: Ningún código fuera de LiveExecutionAdapter puede llamar al broker.
CRITICAL: Todas las acciones de ejecución pasan por esta abstracción.

Author: SUBLIMINE Institutional Trading System
Date: 2025-11-14
Mandato: MANDATO 23 - Live Execution & Kill Switch
"""

import logging
from abc import ABC, abstractmethod
from typing import Dict, List, Optional
from datetime import datetime
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


# Re-export enums from broker_client (para consistencia)
from src.execution.broker_client import OrderType, OrderSide, OrderStatus


@dataclass
class AccountInfo:
    """Información de cuenta."""
    account_id: str
    balance: float
    equity: float
    margin_free: float
    margin_used: float
    margin_level: float
    open_positions: int
    unrealized_pnl: float
    timestamp: datetime


@dataclass
class Position:
    """Posición abierta."""
    position_id: str
    instrument: str
    side: OrderSide
    volume: float
    open_price: float
    current_price: float
    unrealized_pnl: float
    stop_loss: Optional[float]
    take_profit: Optional[float]
    open_time: datetime
    magic_number: int


@dataclass
class OrderResult:
    """Resultado de orden."""
    success: bool
    order_id: Optional[str]
    message: str
    timestamp: datetime
    # Detalles adicionales
    filled: bool = False
    fill_price: Optional[float] = None
    fill_volume: Optional[float] = None
    commission: float = 0.0
    slippage_pips: Optional[float] = None


class ExecutionAdapter(ABC):
    """
    Interface abstracta para backends de ejecución.

    TODOS los adapters (Paper, Live) deben implementar estos métodos.

    Garantías:
    - Logging completo de TODAS las acciones
    - Validación de parámetros
    - Manejo de errores robusto
    - Trazabilidad con decision_id, strategy_id
    """

    def __init__(self, config: Dict, mode_name: str):
        """
        Inicializa adapter.

        Args:
            config: Configuración del sistema
            mode_name: Nombre del modo ("PAPER", "LIVE")
        """
        self.config = config
        self.mode_name = mode_name
        self.initialized = False

        logger.info(f"ExecutionAdapter ({mode_name}) initializing...")

    @abstractmethod
    def initialize(self) -> bool:
        """
        Inicializa el adapter.

        Returns:
            True si inicialización exitosa, False si falla

        Raises:
            Exception: Si falla inicialización crítica
        """
        pass

    @abstractmethod
    def shutdown(self):
        """
        Cierra el adapter y libera recursos.
        """
        pass

    @abstractmethod
    def place_order(
        self,
        instrument: str,
        side: OrderSide,
        volume: float,
        order_type: OrderType = OrderType.MARKET,
        price: Optional[float] = None,
        stop_loss: Optional[float] = None,
        take_profit: Optional[float] = None,
        magic_number: Optional[int] = None,
        decision_id: Optional[str] = None,
        strategy_id: Optional[str] = None,
        metadata: Optional[Dict] = None
    ) -> OrderResult:
        """
        Coloca una orden.

        Args:
            instrument: Símbolo (ej: "EURUSD")
            side: BUY o SELL
            volume: Volumen en lotes
            order_type: Tipo de orden (MARKET, LIMIT, STOP)
            price: Precio para órdenes LIMIT/STOP
            stop_loss: Stop loss price
            take_profit: Take profit price
            magic_number: Magic number único
            decision_id: ID de decisión del brain
            strategy_id: ID de estrategia
            metadata: Metadata adicional (quality_score, risk_pct, etc.)

        Returns:
            OrderResult con detalles de ejecución
        """
        pass

    @abstractmethod
    def modify_order(
        self,
        order_id: str,
        stop_loss: Optional[float] = None,
        take_profit: Optional[float] = None
    ) -> OrderResult:
        """
        Modifica SL/TP de una orden/posición.

        Args:
            order_id: ID de orden/posición
            stop_loss: Nuevo stop loss (opcional)
            take_profit: Nuevo take profit (opcional)

        Returns:
            OrderResult con resultado de modificación
        """
        pass

    @abstractmethod
    def cancel_order(self, order_id: str) -> OrderResult:
        """
        Cancela una orden pendiente.

        Args:
            order_id: ID de orden a cancelar

        Returns:
            OrderResult con resultado de cancelación
        """
        pass

    @abstractmethod
    def close_position(
        self,
        position_id: str,
        volume: Optional[float] = None,
        reason: str = "manual_close"
    ) -> OrderResult:
        """
        Cierra una posición (total o parcial).

        Args:
            position_id: ID de posición
            volume: Volumen a cerrar (None = cerrar todo)
            reason: Razón del cierre

        Returns:
            OrderResult con resultado de cierre
        """
        pass

    @abstractmethod
    def get_account_info(self) -> AccountInfo:
        """
        Obtiene información de cuenta.

        Returns:
            AccountInfo con balance, equity, margin, etc.
        """
        pass

    @abstractmethod
    def get_open_positions(self) -> List[Position]:
        """
        Obtiene todas las posiciones abiertas.

        Returns:
            Lista de Position
        """
        pass

    @abstractmethod
    def get_position(self, position_id: str) -> Optional[Position]:
        """
        Obtiene una posición específica.

        Args:
            position_id: ID de posición

        Returns:
            Position o None si no existe
        """
        pass

    @abstractmethod
    def get_current_price(self, instrument: str) -> Dict[str, float]:
        """
        Obtiene precio actual (bid/ask/mid).

        Args:
            instrument: Símbolo

        Returns:
            Dict con 'bid', 'ask', 'mid'
        """
        pass

    # ========================================================================
    # HELPERS (implementación por defecto)
    # ========================================================================

    def _validate_order_params(
        self,
        instrument: str,
        side: OrderSide,
        volume: float,
        order_type: OrderType,
        price: Optional[float],
        stop_loss: Optional[float],
        take_profit: Optional[float]
    ) -> tuple[bool, str]:
        """
        Valida parámetros de orden.

        Returns:
            (is_valid, error_message)
        """
        # Volumen positivo
        if volume <= 0:
            return False, f"Invalid volume: {volume}"

        # Precio requerido para LIMIT/STOP
        if order_type in [OrderType.LIMIT, OrderType.STOP] and price is None:
            return False, f"Price required for {order_type.value} orders"

        # SL/TP lógicos
        if stop_loss is not None and stop_loss <= 0:
            return False, f"Invalid stop_loss: {stop_loss}"

        if take_profit is not None and take_profit <= 0:
            return False, f"Invalid take_profit: {take_profit}"

        # Símbolo no vacío
        if not instrument or len(instrument) < 2:
            return False, f"Invalid instrument: {instrument}"

        return True, "OK"

    def _log_order(
        self,
        action: str,
        instrument: str,
        side: OrderSide,
        volume: float,
        order_id: Optional[str] = None,
        decision_id: Optional[str] = None,
        strategy_id: Optional[str] = None,
        **kwargs
    ):
        """
        Log de orden para auditoría.

        Args:
            action: Acción (PLACE, MODIFY, CANCEL, CLOSE)
            instrument: Símbolo
            side: BUY o SELL
            volume: Volumen
            order_id: ID de orden
            decision_id: ID de decisión
            strategy_id: ID de estrategia
            **kwargs: Campos adicionales
        """
        log_data = {
            'mode': self.mode_name,
            'action': action,
            'instrument': instrument,
            'side': side.value if isinstance(side, OrderSide) else side,
            'volume': volume,
            'order_id': order_id,
            'decision_id': decision_id,
            'strategy_id': strategy_id,
            'timestamp': datetime.now().isoformat(),
            **kwargs
        }

        logger.info(f"[{self.mode_name}] {action}: {log_data}")

    def is_initialized(self) -> bool:
        """
        Verifica si el adapter está inicializado.

        Returns:
            True si inicializado, False si no
        """
        return self.initialized

    def get_mode_name(self) -> str:
        """
        Obtiene nombre del modo.

        Returns:
            String con nombre del modo
        """
        return self.mode_name
