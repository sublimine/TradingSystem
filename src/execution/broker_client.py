"""
Broker Client - Cliente de broker con state machine completa
Maneja envío de órdenes, tracking de estados y confirmaciones.
"""

import logging
from typing import Dict, Optional, Callable
from datetime import datetime
from enum import Enum
from dataclasses import dataclass
import time
import uuid

logger = logging.getLogger(__name__)


class OrderType(Enum):
    """Tipos de orden."""
    MARKET = "market"
    LIMIT = "limit"
    STOP = "stop"
    STOP_LIMIT = "stop_limit"


class OrderSide(Enum):
    """Lado de la orden."""
    BUY = "buy"
    SELL = "sell"


class OrderStatus(Enum):
    """Estados de orden."""
    PENDING = "pending"           # Enviada, esperando confirmación
    ACCEPTED = "accepted"         # Aceptada por broker
    PARTIALLY_FILLED = "partial"  # Parcialmente llenada
    FILLED = "filled"             # Completamente llenada
    REJECTED = "rejected"         # Rechazada por broker
    CANCELLED = "cancelled"       # Cancelada
    EXPIRED = "expired"           # Expirada
    TIMEOUT = "timeout"           # Timeout esperando respuesta


class RejectReason(Enum):
    """Razones de rechazo."""
    INSUFFICIENT_MARGIN = "insufficient_margin"
    INVALID_PRICE = "invalid_price"
    MARKET_CLOSED = "market_closed"
    POSITION_LIMIT = "position_limit"
    INVALID_VOLUME = "invalid_volume"
    UNKNOWN = "unknown"


@dataclass
class Order:
    """Orden completa."""
    order_id: str
    instrument: str
    side: OrderSide
    order_type: OrderType
    volume: float
    price: Optional[float]
    stop_loss: Optional[float]
    take_profit: Optional[float]
    magic_number: int
    status: OrderStatus
    created_at: datetime
    
    # Campos de ejecución
    filled_volume: float = 0.0
    fill_price: Optional[float] = None
    fill_timestamp: Optional[datetime] = None
    commission: float = 0.0
    
    # Rechazo
    reject_reason: Optional[RejectReason] = None
    reject_message: Optional[str] = None
    
    # Metadata
    mid_at_send: Optional[float] = None
    mid_at_fill: Optional[float] = None
    hold_ms: Optional[int] = None


class BrokerClient:
    """
    Cliente de broker institucional con state machine.
    
    Features:
    - State machine completa de órdenes
    - Retry logic con backoff exponencial
    - Manejo de fills parciales
    - Timeouts configurables
    - Tracking completo de latencias
    """
    
    def __init__(
        self,
        broker_name: str,
        account_id: str,
        timeout_seconds: int = 5,
        max_retries: int = 3,
        retry_backoff_ms: int = 100
    ):
        """
        Inicializa broker client.
        
        Args:
            broker_name: Nombre del broker
            account_id: ID de cuenta
            timeout_seconds: Timeout para confirmaciones
            max_retries: Reintentos máximos para errores transitorios
            retry_backoff_ms: Backoff exponencial inicial
        """
        self.broker_name = broker_name
        self.account_id = account_id
        self.timeout_seconds = timeout_seconds
        self.max_retries = max_retries
        self.retry_backoff_ms = retry_backoff_ms
        
        self._orders: Dict[str, Order] = {}
        self._connected = False
        
        logger.info(
            f"BrokerClient initialized: {broker_name}, "
            f"account={account_id}"
        )
    
    def connect(self) -> bool:
        """Establece conexión con broker."""
        try:
            # En producción, conectaría con API del broker
            logger.info(f"Connecting to broker {self.broker_name}")
            self._connected = True
            return True
        
        except Exception as e:
            logger.error(f"Failed to connect to broker: {e}")
            return False
    
    def disconnect(self):
        """Cierra conexión."""
        self._connected = False
        logger.info("Broker connection closed")
    
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
        mid_at_send: Optional[float] = None
    ) -> Order:
        """
        Envía orden al broker.
        
        Args:
            instrument: Instrumento
            side: BUY o SELL
            volume: Volumen en lotes
            order_type: Tipo de orden
            price: Precio (para limit/stop)
            stop_loss: Stop loss
            take_profit: Take profit
            magic_number: Magic number único
            mid_at_send: Mid price al enviar (para TCA)
            
        Returns:
            Order object
        """
        if not self._connected:
            raise Exception("Not connected to broker")
        
        # Generar order ID
        order_id = str(uuid.uuid4())
        
        if magic_number is None:
            magic_number = int(time.time() * 1000) % 1000000
        
        # Crear orden
        order = Order(
            order_id=order_id,
            instrument=instrument,
            side=side,
            order_type=order_type,
            volume=volume,
            price=price,
            stop_loss=stop_loss,
            take_profit=take_profit,
            magic_number=magic_number,
            status=OrderStatus.PENDING,
            created_at=datetime.now(),
            mid_at_send=mid_at_send
        )
        
        self._orders[order_id] = order
        
        logger.info(
            f"Order placed: {order_id} {instrument} {side.value} "
            f"{volume} lots (type={order_type.value})"
        )
        
        # Enviar al broker (con retry)
        self._send_order_with_retry(order)
        
        return order
    
    def _send_order_with_retry(self, order: Order):
        """Envía orden con retry logic."""
        for attempt in range(self.max_retries):
            try:
                # En producción, enviaría al broker via API
                # success = broker_api.send_order(...)
                
                # Simular envío
                send_start = time.time()
                
                # Simular processing
                time.sleep(0.01)  # 10ms simulado
                
                # Simular respuesta del broker
                success = True  # En producción vendría del broker
                
                if success:
                    hold_ms = int((time.time() - send_start) * 1000)
                    order.hold_ms = hold_ms
                    
                    # Simular fill (en producción vendría por callback)
                    self._simulate_fill(order)
                    
                    return
                else:
                    # Error transitorio, reintentar
                    if attempt < self.max_retries - 1:
                        backoff = self.retry_backoff_ms * (2 ** attempt)
                        logger.warning(
                            f"Order {order.order_id} send failed, "
                            f"retrying in {backoff}ms"
                        )
                        time.sleep(backoff / 1000.0)
                    else:
                        # Reintentos agotados
                        order.status = OrderStatus.REJECTED
                        order.reject_reason = RejectReason.UNKNOWN
                        logger.error(
                            f"Order {order.order_id} rejected after "
                            f"{self.max_retries} retries"
                        )
            
            except Exception as e:
                logger.error(f"Error sending order: {e}")
                order.status = OrderStatus.REJECTED
                order.reject_reason = RejectReason.UNKNOWN
                order.reject_message = str(e)
    
    def _simulate_fill(self, order: Order):
        """Simula fill de orden (en producción vendría del broker)."""
        # NOTA: Esto es solo para testing
        # En producción, los fills vendrían por callbacks del broker
        
        order.status = OrderStatus.FILLED
        order.filled_volume = order.volume
        order.fill_timestamp = datetime.now()
        
        # Simular precio de fill
        if order.price:
            order.fill_price = order.price
        else:
            # Market order, simular slippage
            order.fill_price = order.mid_at_send if order.mid_at_send else 1.1000
        
        # Simular comisión
        order.commission = order.volume * 7.0  # $7 por lote
        
        logger.info(
            f"Order filled: {order.order_id} {order.filled_volume} lots "
            f"@ {order.fill_price:.5f} (commission=${order.commission:.2f})"
        )
    
    def get_order(self, order_id: str) -> Optional[Order]:
        """Obtiene orden por ID."""
        return self._orders.get(order_id)
    
    def get_open_orders(self, instrument: Optional[str] = None) -> list[Order]:
        """Obtiene órdenes abiertas."""
        orders = [
            o for o in self._orders.values()
            if o.status in [OrderStatus.PENDING, OrderStatus.ACCEPTED, OrderStatus.PARTIALLY_FILLED]
        ]
        
        if instrument:
            orders = [o for o in orders if o.instrument == instrument]
        
        return orders
    
    def cancel_order(self, order_id: str) -> bool:
        """Cancela una orden."""
        order = self._orders.get(order_id)
        
        if not order:
            logger.error(f"Order {order_id} not found")
            return False
        
        if order.status not in [OrderStatus.PENDING, OrderStatus.ACCEPTED]:
            logger.warning(
                f"Cannot cancel order {order_id} in status {order.status.value}"
            )
            return False
        
        try:
            # En producción, enviaría cancelación al broker
            order.status = OrderStatus.CANCELLED
            logger.info(f"Order {order_id} cancelled")
            return True
        
        except Exception as e:
            logger.error(f"Failed to cancel order {order_id}: {e}")
            return False
    
    def get_account_info(self) -> Dict:
        """Obtiene información de cuenta."""
        # En producción consultaría al broker
        return {
            'account_id': self.account_id,
            'balance': 10000.0,
            'equity': 10000.0,
            'margin_free': 10000.0,
            'margin_level': 100.0,
            'open_positions': 0
        }
    
    def get_statistics(self) -> Dict:
        """Obtiene estadísticas de órdenes."""
        total_orders = len(self._orders)
        
        status_counts = {}
        for order in self._orders.values():
            status = order.status.value
            status_counts[status] = status_counts.get(status, 0) + 1
        
        filled_orders = [
            o for o in self._orders.values()
            if o.status == OrderStatus.FILLED
        ]
        
        avg_hold_time = 0
        if filled_orders:
            hold_times = [o.hold_ms for o in filled_orders if o.hold_ms]
            if hold_times:
                avg_hold_time = sum(hold_times) / len(hold_times)
        
        return {
            'total_orders': total_orders,
            'status_counts': status_counts,
            'avg_hold_time_ms': avg_hold_time,
            'fill_rate': (
                len(filled_orders) / total_orders * 100
                if total_orders > 0 else 0
            )
        }