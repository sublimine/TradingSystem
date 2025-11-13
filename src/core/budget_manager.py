"""
Budget Manager - Gestor de presupuestos por familia de estrategias

Mantiene tracking en tiempo real de capital asignado, comprometido y disponible
por cada familia de estrategias. Garantiza que no se sobre-aloque capital.
"""

import logging
from typing import Dict, Optional
from threading import Lock
from datetime import datetime

logger = logging.getLogger(__name__)


class BudgetManager:
    """
    Gestor centralizado de presupuestos de capital.
    
    RESPONSABILIDADES:
    - Tracking de capital asignado por familia
    - Reserva de capital cuando se abre posición
    - Liberación de capital cuando se cierra posición
    - Verificación de budget disponible antes de ejecutar
    - Auditoría completa de movimientos de capital
    """
    
    def __init__(self, total_capital: float, family_allocations: Dict[str, float]):
        """
        Args:
            total_capital: Capital total del portfolio (ej: 100000.0)
            family_allocations: Dict[familia, fracción] donde fracción suma <= 1.0
                               Ej: {'momentum': 0.30, 'mean_reversion': 0.25, 'breakout': 0.20}
        """
        # P1-024: Validar total_capital >= 0 para evitar utilization negativa
        if total_capital < 0:
            raise ValueError(f"total_capital debe ser >= 0, recibido: {total_capital}")

        self.total_capital = total_capital
        self.family_allocations = family_allocations

        # Validar que allocations no excedan 100%
        total_allocation = sum(family_allocations.values())
        if total_allocation > 1.0:
            raise ValueError(f"Total family allocations ({total_allocation:.2%}) exceed 100%")
        
        # Budget absoluto por familia
        self.family_budgets = {
            family: total_capital * allocation
            for family, allocation in family_allocations.items()
        }
        
        # Capital actualmente comprometido por familia
        self.family_committed = {family: 0.0 for family in family_allocations.keys()}
        
        # Registro de posiciones abiertas para tracking
        # Key: position_id, Value: {'family': str, 'capital_reserved': float}
        self.open_positions: Dict[str, Dict] = {}
        
        # Lock para thread-safety
        self.lock = Lock()
        
        # Métricas
        self.stats = {
            'total_reservations': 0,
            'total_releases': 0,
            'peak_capital_used': 0.0,
            'budget_exhausted_events': 0
        }
        
        logger.info(
            f"BudgetManager inicializado: capital=${total_capital:,.2f}, "
            f"familias={len(family_allocations)}"
        )
    
    def get_available_capital(self, family: str) -> float:
        """
        Retorna capital disponible para una familia.
        
        Args:
            family: Nombre de la familia
            
        Returns:
            Capital disponible en unidades absolutas
        """
        with self.lock:
            if family not in self.family_budgets:
                logger.warning(f"Familia '{family}' no reconocida, retornando 0")
                return 0.0
            
            total_budget = self.family_budgets[family]
            committed = self.family_committed[family]
            available = total_budget - committed
            
            return max(0.0, available)
    
    def get_available_fraction(self, family: str) -> float:
        """
        Retorna fracción disponible del budget familiar.
        
        Returns:
            Fracción entre 0.0 y 1.0
        """
        with self.lock:
            if family not in self.family_budgets:
                return 0.0
            
            total_budget = self.family_budgets[family]
            if total_budget == 0:
                return 0.0
            
            available = self.get_available_capital(family)
            return available / total_budget
    
    def reserve_capital(self, position_id: str, family: str, amount: float) -> bool:
        """
        Reserva capital para una posición.
        
        Args:
            position_id: ID único de la posición
            family: Familia de la estrategia
            amount: Cantidad absoluta de capital a reservar
            
        Returns:
            True si se pudo reservar, False si budget insuficiente
        """
        with self.lock:
            # Verificar familia válida
            if family not in self.family_budgets:
                logger.error(f"BUDGET_ERROR: Familia '{family}' no existe")
                return False
            
            # Verificar disponibilidad
            available = self.get_available_capital(family)
            
            if amount > available:
                logger.warning(
                    f"BUDGET_INSUFFICIENT: familia={family} requiere=${amount:,.2f} "
                    f"pero solo disponible=${available:,.2f}"
                )
                self.stats['budget_exhausted_events'] += 1
                return False
            
            # Reservar capital
            self.family_committed[family] += amount
            self.open_positions[position_id] = {
                'family': family,
                'capital_reserved': amount,
                'timestamp': datetime.now().isoformat()
            }
            
            self.stats['total_reservations'] += 1
            
            # Actualizar peak
            total_used = sum(self.family_committed.values())
            if total_used > self.stats['peak_capital_used']:
                self.stats['peak_capital_used'] = total_used
            
            logger.info(
                f"BUDGET_RESERVED: position={position_id} familia={family} "
                f"amount=${amount:,.2f} remaining=${available - amount:,.2f}"
            )
            
            return True
    
    def release_capital(self, position_id: str) -> bool:
        """
        Libera capital cuando se cierra posición.
        
        Args:
            position_id: ID de la posición cerrada
            
        Returns:
            True si se liberó correctamente, False si posición no encontrada
        """
        with self.lock:
            if position_id not in self.open_positions:
                logger.warning(f"BUDGET_RELEASE_SKIP: position={position_id} no encontrada")
                return False
            
            position_info = self.open_positions[position_id]
            family = position_info['family']
            amount = position_info['capital_reserved']
            
            # Liberar capital
            self.family_committed[family] -= amount
            del self.open_positions[position_id]
            
            self.stats['total_releases'] += 1
            
            available_now = self.get_available_capital(family)
            
            logger.info(
                f"BUDGET_RELEASED: position={position_id} familia={family} "
                f"amount=${amount:,.2f} now_available=${available_now:,.2f}"
            )
            
            return True
    
    def get_utilization(self) -> Dict:
        """Retorna utilización actual de budgets."""
        with self.lock:
            utilization = {}
            
            for family in self.family_budgets.keys():
                total = self.family_budgets[family]
                committed = self.family_committed[family]
                available = total - committed
                
                utilization[family] = {
                    'total_budget': total,
                    'committed': committed,
                    'available': available,
                    'utilization_pct': (committed / total * 100) if total > 0 else 0.0
                }
            
            total_committed = sum(self.family_committed.values())
            
            utilization['portfolio'] = {
                'total_capital': self.total_capital,
                'total_committed': total_committed,
                'total_available': self.total_capital - total_committed,
                'utilization_pct': (total_committed / self.total_capital * 100) if self.total_capital > 0 else 0.0,
                'open_positions': len(self.open_positions)
            }
            
            return utilization
    
    def get_stats(self) -> Dict:
        """Retorna estadísticas del manager."""
        with self.lock:
            return {
                **self.stats,
                'current_utilization': self.get_utilization()
            }


# Instancia global
_BUDGET_MANAGER_INSTANCE: Optional[BudgetManager] = None


def get_budget_manager(total_capital: Optional[float] = None,
                       family_allocations: Optional[Dict[str, float]] = None) -> BudgetManager:
    """
    Obtiene instancia global del Budget Manager.
    
    Args:
        total_capital: Requerido en primera llamada
        family_allocations: Requerido en primera llamada
    """
    global _BUDGET_MANAGER_INSTANCE
    
    if _BUDGET_MANAGER_INSTANCE is None:
        if total_capital is None or family_allocations is None:
            raise ValueError("Budget Manager requiere total_capital y family_allocations en primera inicialización")
        _BUDGET_MANAGER_INSTANCE = BudgetManager(total_capital, family_allocations)
    
    return _BUDGET_MANAGER_INSTANCE
