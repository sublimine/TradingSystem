"""
PaperBrokerAdapter - PLAN OMEGA FASE 3.2

Simulador de broker para trading en modo PAPER.
Ejecuta órdenes en entorno simulado sin conexión a broker real.

Features:
- Simulación completa de órdenes y posiciones
- Tracking de balance y equity
- Simulación de slippage y spread
- Validación de stops y targets
- Historial de trades

Author: Elite Institutional Trading System
Version: 1.0
"""

from typing import Dict, List, Optional
from datetime import datetime
import logging
from collections import defaultdict
import uuid

from .broker_adapter import BrokerAdapter, Order, Position

logger = logging.getLogger(__name__)


class PaperBrokerAdapter(BrokerAdapter):
    """
    Adaptador de broker simulado para modo PAPER.

    Simula ejecución de órdenes sin conexión real a broker.
    Útil para testing y validación de estrategias.
    """

    def __init__(self, config: Dict):
        """
        Inicializar broker simulado.

        Args:
            config: Configuración del broker
                - initial_capital: Capital inicial (default: 10000.0)
                - slippage_pips: Slippage en pips (default: 0.5)
                - spread_pips: Spread por símbolo (default: {'EURUSD': 1.0})
                - commission_per_lot: Comisión por lote (default: 7.0)
        """
        super().__init__(config)

        # Configuración
        self.initial_capital = config.get('initial_capital', 10000.0)
        self.slippage_pips = config.get('slippage_pips', 0.5)
        self.spread_pips = config.get('spread_pips', {'EURUSD': 1.0})
        self.commission_per_lot = config.get('commission_per_lot', 7.0)

        # Estado del broker
        self.balance = self.initial_capital
        self.equity = self.initial_capital

        # Órdenes y posiciones
        self.orders: Dict[str, Order] = {}
        self.positions: Dict[str, Position] = {}
        self.closed_positions: List[Dict] = []

        # Tracking
        self.total_trades = 0
        self.winning_trades = 0
        self.losing_trades = 0
        self.total_pnl = 0.0

        self.logger.info(f"PaperBroker initialized with capital=${self.initial_capital:,.2f}")

    def connect(self) -> bool:
        """
        Conectar al broker simulado.

        Returns:
            True (siempre exitoso en modo PAPER)
        """
        self.connected = True
        self.logger.info("✅ PaperBroker connected (simulation mode)")
        return True

    def disconnect(self):
        """Desconectar del broker simulado."""
        self.connected = False
        self.logger.info("PaperBroker disconnected")

    def submit_order(self, order: Order) -> bool:
        """
        Enviar orden al broker simulado.

        Args:
            order: Orden a ejecutar

        Returns:
            True si orden aceptada
        """
        if not self.connected:
            self.logger.error("Cannot submit order - broker not connected")
            return False

        try:
            # Aplicar slippage y spread
            fill_price = self._apply_slippage_and_spread(
                order.entry_price,
                order.symbol,
                order.direction
            )

            # Calcular comisión
            commission = order.position_size * self.commission_per_lot

            # Validar suficiente capital
            risk_amount = abs(fill_price - order.stop_loss) * order.position_size * 100000
            if risk_amount + commission > self.balance * 0.5:  # No usar más del 50% del balance
                self.logger.warning(f"Order rejected - insufficient capital (risk={risk_amount:.2f}, balance={self.balance:.2f})")
                order.status = 'REJECTED'
                return False

            # Marcar orden como FILLED
            order.status = 'FILLED'
            order.fill_price = fill_price
            order.fill_time = datetime.now()

            # Guardar orden
            self.orders[order.order_id] = order

            # Crear posición
            position = Position(
                position_id=f"POS_{uuid.uuid4().hex[:8]}",
                order_id=order.order_id,
                symbol=order.symbol,
                direction=order.direction,
                entry_price=fill_price,
                entry_time=order.fill_time,
                stop_loss=order.stop_loss,
                take_profit=order.take_profit,
                position_size=order.position_size,
                strategy_name=order.strategy_name,
                metadata=order.metadata
            )

            self.positions[position.position_id] = position

            # Deducir comisión del balance
            self.balance -= commission

            self.logger.info(f"✅ Order FILLED: {order.direction} {order.symbol} @ {fill_price:.5f}, "
                           f"Size={order.position_size:.2f}, Commission=${commission:.2f}")
            self.logger.info(f"   SL={order.stop_loss:.5f}, TP={order.take_profit:.5f}")

            return True

        except Exception as e:
            self.logger.error(f"Failed to submit order: {e}", exc_info=True)
            order.status = 'REJECTED'
            return False

    def cancel_order(self, order_id: str) -> bool:
        """
        Cancelar orden pendiente.

        Args:
            order_id: ID de la orden

        Returns:
            True si orden cancelada
        """
        if order_id not in self.orders:
            self.logger.warning(f"Order {order_id} not found")
            return False

        order = self.orders[order_id]

        if order.status != 'PENDING':
            self.logger.warning(f"Cannot cancel order {order_id} - status is {order.status}")
            return False

        order.status = 'CANCELLED'
        self.logger.info(f"Order {order_id} cancelled")
        return True

    def get_positions(self) -> List[Position]:
        """
        Obtener todas las posiciones abiertas.

        Returns:
            Lista de posiciones
        """
        return list(self.positions.values())

    def close_position(self, position_id: str, exit_price: Optional[float] = None,
                      exit_reason: str = 'MANUAL') -> bool:
        """
        Cerrar posición abierta.

        Args:
            position_id: ID de la posición
            exit_price: Precio de salida (si None, usar precio actual)
            exit_reason: Razón del cierre

        Returns:
            True si posición cerrada
        """
        if position_id not in self.positions:
            self.logger.warning(f"Position {position_id} not found")
            return False

        position = self.positions[position_id]

        # Usar precio actual si no se especifica
        if exit_price is None:
            exit_price = position.current_price

        # Calcular P&L
        if position.direction == 'LONG':
            price_diff = exit_price - position.entry_price
        else:  # SHORT
            price_diff = position.entry_price - exit_price

        pips = price_diff * 10000
        pnl = pips * 10 * position.position_size

        # Deducir comisión de salida
        commission = position.position_size * self.commission_per_lot
        pnl -= commission

        # Actualizar balance
        self.balance += pnl

        # Tracking
        self.total_trades += 1
        self.total_pnl += pnl

        if pnl > 0:
            self.winning_trades += 1
        else:
            self.losing_trades += 1

        # Guardar posición cerrada
        closed_position = position.to_dict()
        closed_position.update({
            'exit_price': exit_price,
            'exit_time': datetime.now().isoformat(),
            'exit_reason': exit_reason,
            'pnl': pnl,
            'pips': pips
        })
        self.closed_positions.append(closed_position)

        # Eliminar posición
        del self.positions[position_id]

        self.logger.info(f"✅ Position CLOSED: {position.symbol} {position.direction}, "
                       f"P&L=${pnl:.2f} ({pips:.1f} pips), Reason={exit_reason}")

        return True

    def get_account_balance(self) -> float:
        """
        Obtener balance actual.

        Returns:
            Balance en USD
        """
        return self.balance

    def get_account_equity(self) -> float:
        """
        Obtener equity actual (balance + P&L no realizado).

        Returns:
            Equity en USD
        """
        unrealized_pnl = sum(pos.unrealized_pnl for pos in self.positions.values())
        self.equity = self.balance + unrealized_pnl
        return self.equity

    def update_positions(self, market_data: Dict):
        """
        Actualizar posiciones con datos de mercado.

        Verifica stops/targets y actualiza P&L.

        Args:
            market_data: {symbol: {'bid': x, 'ask': y, 'high': h, 'low': l}}
        """
        if not self.positions:
            return

        positions_to_close = []

        for position_id, position in self.positions.items():
            symbol = position.symbol

            if symbol not in market_data:
                continue

            bar = market_data[symbol]

            # Actualizar precio actual
            if position.direction == 'LONG':
                current_price = bar.get('bid', bar.get('close'))
            else:
                current_price = bar.get('ask', bar.get('close'))

            position.update_pnl(current_price)

            # Verificar stop loss
            if position.direction == 'LONG':
                if bar.get('low', current_price) <= position.stop_loss:
                    positions_to_close.append((position_id, position.stop_loss, 'STOP_LOSS'))
            else:  # SHORT
                if bar.get('high', current_price) >= position.stop_loss:
                    positions_to_close.append((position_id, position.stop_loss, 'STOP_LOSS'))

            # Verificar take profit
            if position.direction == 'LONG':
                if bar.get('high', current_price) >= position.take_profit:
                    positions_to_close.append((position_id, position.take_profit, 'TAKE_PROFIT'))
            else:  # SHORT
                if bar.get('low', current_price) <= position.take_profit:
                    positions_to_close.append((position_id, position.take_profit, 'TAKE_PROFIT'))

        # Cerrar posiciones que tocaron SL o TP
        for position_id, exit_price, reason in positions_to_close:
            self.close_position(position_id, exit_price, reason)

    def _apply_slippage_and_spread(self, price: float, symbol: str, direction: str) -> float:
        """
        Aplicar slippage y spread al precio.

        Args:
            price: Precio base
            symbol: Símbolo
            direction: 'LONG' o 'SHORT'

        Returns:
            Precio ajustado con slippage y spread
        """
        # Obtener spread para el símbolo
        spread = self.spread_pips.get(symbol, 1.0)

        # Convertir pips a precio
        pip_value = 0.0001 if 'JPY' not in symbol else 0.01

        slippage_value = self.slippage_pips * pip_value
        spread_value = spread * pip_value

        if direction == 'LONG':
            # LONG: compramos al ask (precio + spread + slippage)
            adjusted_price = price + spread_value + slippage_value
        else:
            # SHORT: vendemos al bid (precio - spread - slippage)
            adjusted_price = price - spread_value - slippage_value

        return adjusted_price

    def get_statistics(self) -> Dict:
        """
        Obtener estadísticas del broker simulado.

        Returns:
            Diccionario con estadísticas
        """
        win_rate = self.winning_trades / self.total_trades if self.total_trades > 0 else 0.0

        return {
            'initial_capital': self.initial_capital,
            'current_balance': self.balance,
            'current_equity': self.get_account_equity(),
            'total_trades': self.total_trades,
            'winning_trades': self.winning_trades,
            'losing_trades': self.losing_trades,
            'win_rate': win_rate,
            'total_pnl': self.total_pnl,
            'return_pct': (self.balance - self.initial_capital) / self.initial_capital * 100,
            'open_positions': len(self.positions)
        }

    def reset(self):
        """Resetear broker a estado inicial."""
        self.balance = self.initial_capital
        self.equity = self.initial_capital
        self.orders.clear()
        self.positions.clear()
        self.closed_positions.clear()
        self.total_trades = 0
        self.winning_trades = 0
        self.losing_trades = 0
        self.total_pnl = 0.0
        self.logger.info("PaperBroker reset to initial state")
