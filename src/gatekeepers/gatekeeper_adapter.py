"""
Gatekeeper Data Adapter - Capa de Integración

Este adaptador sirve como puente entre el motor de trading y el sistema
de gatekeepers. Su responsabilidad es transformar los datos del motor
(que vienen en formato específico de MT5) al formato que esperan los
gatekeepers, y proporcionar una interface limpia para consultas.

Filosofía de diseño:
- Single source of truth: Los gatekeepers reciben todos los ticks
- Thread-safe: Puede ser llamado desde múltiples estrategias simultáneamente
- Fail-safe: Si hay error, asume condiciones adversas
- Stateful: Mantiene historia completa de decisiones para análisis

Author: Sistema de Trading Institucional
Date: 2025-11-06
Version: 1.0
"""

import numpy as np
import pandas as pd
from typing import Dict, Optional, Tuple
from datetime import datetime
import logging
import threading

from gatekeepers.gatekeeper_integrator import GatekeeperIntegrator


class GatekeeperAdapter:
    """
    Adaptador entre motor de trading MT5 y sistema de gatekeepers.
    
    Este adaptador traduce entre dos mundos:
    1. Motor MT5: Opera con ticks en formato OHLCV
    2. Gatekeepers: Operan con prices, volumes, bid/ask individuales
    
    También mantiene un buffer de decisiones históricas para debugging
    y análisis post-mortem de por qué se tomaron ciertas decisiones.
    """
    
    def __init__(self, config: Optional[Dict] = None):
        """
        Inicializa el adaptador con configuración opcional.
        
        Args:
            config: Configuración para los gatekeepers subyacentes
        """
        config = config or {}
        
        # Inicializar el integrador de gatekeepers
        self.integrator = GatekeeperIntegrator(
            kyle_config=config.get('kyle', {}),
            epin_config=config.get('epin', {}),
            spread_config=config.get('spread', {})
        )
        
        # Estado previo (necesario para calcular cambios)
        self.prev_price = None
        self.prev_mid = None
        self.prev_timestamp = None
        
        # Historia de decisiones (para debugging)
        self.decision_history = []
        self.max_history_size = 1000
        
        # Lock para thread safety
        self.lock = threading.Lock()
        
        # Contadores de estadísticas
        self.stats = {
            'total_ticks_processed': 0,
            'total_trades_approved': 0,
            'total_trades_rejected': 0,
            'total_sizing_reductions': 0
        }
        
        self.logger = logging.getLogger(self.__class__.__name__)
        self.logger.info("Gatekeeper Adapter inicializado")
    
    def process_tick(self, tick_data: Dict) -> None:
        """
        Procesa un nuevo tick del mercado y actualiza gatekeepers.
        
        Este método debe ser llamado por el motor de trading cada vez
        que recibe un nuevo tick, ANTES de que las estrategias evalúen
        si quieren operar.
        
        Args:
            tick_data: Diccionario con keys:
                - symbol: str
                - bid: float
                - ask: float
                - last: float (precio de última transacción)
                - volume: float (volumen del tick)
                - time: datetime
        """
        with self.lock:
            try:
                # Extraer datos del tick
                symbol = tick_data.get('symbol', 'UNKNOWN')
                bid = tick_data['bid']
                ask = tick_data['ask']
                last = tick_data.get('last', (bid + ask) / 2)
                volume = tick_data.get('volume', 0.0)
                timestamp = tick_data.get('time', datetime.now())
                
                current_mid = (bid + ask) / 2
                
                # Para el primer tick, inicializar estado previo
                if self.prev_price is None:
                    self.prev_price = last
                    self.prev_mid = current_mid
                    self.prev_timestamp = timestamp
                    self.logger.info(f"Estado inicial establecido para {symbol}")
                    return
                
                # Actualizar todos los gatekeepers
                self.integrator.update_all(
                    trade_price=last,
                    prev_price=self.prev_price,
                    volume=volume,
                    bid=bid,
                    ask=ask,
                    prev_mid=self.prev_mid
                )
                
                # Actualizar estado previo para próximo tick
                self.prev_price = last
                self.prev_mid = current_mid
                self.prev_timestamp = timestamp
                
                # Incrementar contador
                self.stats['total_ticks_processed'] += 1
                
                if self.stats['total_ticks_processed'] % 100 == 0:
                    self.logger.debug(
                        f"Procesados {self.stats['total_ticks_processed']} ticks"
                    )
                
            except Exception as e:
                self.logger.error(
                    f"Error procesando tick: {str(e)}",
                    exc_info=True
                )
                # En caso de error, no actualizar estado
                # El sistema continuará con último estado conocido
    
    def check_trade_permission(self, 
                              strategy_name: str,
                              direction: str,
                              symbol: str,
                              proposed_size: float) -> Dict:
        """
        Verifica si una estrategia tiene permiso para ejecutar un trade.
        
        Esta es la función principal que llaman las estrategias antes
        de intentar ejecutar cualquier trade.
        
        Args:
            strategy_name: Nombre de la estrategia solicitante
            direction: 'long' o 'short'
            symbol: Símbolo a tradear
            proposed_size: Tamaño propuesto del trade
            
        Returns:
            Dict con:
            - permitted: bool (True si puede proceder)
            - adjusted_size: float (tamaño ajustado según gatekeepers)
            - reason: str (explicación de la decisión)
            - regime: str ('GREEN', 'YELLOW', 'RED')
            - details: Dict (información detallada para logging)
        """
        with self.lock:
            try:
                # Obtener decisión de gatekeepers
                approval = self.integrator.check_trade_approval()
                
                # Calcular tamaño ajustado
                sizing_multiplier = approval['sizing_multiplier']
                adjusted_size = proposed_size * sizing_multiplier
                
                # Determinar si está permitido
                permitted = approval['approved']
                
                # Construir razón descriptiva
                if not permitted:
                    reason = f"RECHAZADO: {approval['halt_reason']}"
                elif sizing_multiplier < 1.0:
                    reason = (
                        f"APROBADO CON REDUCCIÓN: Sizing ajustado a "
                        f"{sizing_multiplier:.0%} debido a: {', '.join(approval['warnings'])}"
                    )
                else:
                    reason = "APROBADO: Condiciones normales de mercado"
                
                # Crear registro de decisión
                decision_record = {
                    'timestamp': datetime.now(),
                    'strategy': strategy_name,
                    'direction': direction,
                    'symbol': symbol,
                    'proposed_size': proposed_size,
                    'adjusted_size': adjusted_size,
                    'permitted': permitted,
                    'regime': approval['regime'],
                    'sizing_multiplier': sizing_multiplier,
                    'reason': reason
                }
                
                # Agregar a historia (limitar tamaño)
                self.decision_history.append(decision_record)
                if len(self.decision_history) > self.max_history_size:
                    self.decision_history.pop(0)
                
                # Actualizar estadísticas
                if permitted:
                    self.stats['total_trades_approved'] += 1
                    if sizing_multiplier < 1.0:
                        self.stats['total_sizing_reductions'] += 1
                else:
                    self.stats['total_trades_rejected'] += 1
                
                # Log la decisión
                log_level = logging.INFO if permitted else logging.WARNING
                self.logger.log(
                    log_level,
                    f"{strategy_name} - {symbol} {direction}: {reason}"
                )
                
                # Retornar decisión completa
                return {
                    'permitted': permitted,
                    'adjusted_size': adjusted_size,
                    'reason': reason,
                    'regime': approval['regime'],
                    'details': {
                        'sizing_multiplier': sizing_multiplier,
                        'original_size': proposed_size,
                        'warnings': approval['warnings'],
                        'halt_reason': approval['halt_reason']
                    }
                }
                
            except Exception as e:
                # En caso de error, adoptar postura conservadora
                self.logger.error(
                    f"Error en check_trade_permission: {str(e)}",
                    exc_info=True
                )
                
                return {
                    'permitted': False,
                    'adjusted_size': 0.0,
                    'reason': f"ERROR EN GATEKEEPERS: {str(e)}",
                    'regime': 'RED',
                    'details': {'error': str(e)}
                }
    
    def get_current_regime(self) -> str:
        """
        Retorna el régimen actual del mercado sin hacer solicitud de trade.
        
        Útil para dashboard o monitoring.
        
        Returns:
            'GREEN', 'YELLOW', o 'RED'
        """
        with self.lock:
            return self.integrator.get_market_regime()
    
    def get_comprehensive_status(self) -> Dict:
        """
        Retorna status completo de todos los gatekeepers.
        
        Incluye tanto el estado de los gatekeepers como las estadísticas
        del adaptador.
        
        Returns:
            Dict comprehensivo con todo el estado del sistema
        """
        with self.lock:
            gatekeeper_status = self.integrator.get_comprehensive_status()
            
            return {
                'gatekeepers': gatekeeper_status,
                'adapter_stats': self.stats.copy(),
                'current_regime': self.get_current_regime(),
                'recent_decisions': self.decision_history[-10:] if self.decision_history else []
            }
    
    def get_statistics_summary(self) -> Dict:
        """
        Retorna resumen de estadísticas del adaptador.
        
        Returns:
            Dict con contadores y ratios
        """
        with self.lock:
            total_decisions = (
                self.stats['total_trades_approved'] + 
                self.stats['total_trades_rejected']
            )
            
            if total_decisions > 0:
                approval_rate = (
                    self.stats['total_trades_approved'] / total_decisions
                )
                reduction_rate = (
                    self.stats['total_sizing_reductions'] / 
                    self.stats['total_trades_approved']
                ) if self.stats['total_trades_approved'] > 0 else 0
            else:
                approval_rate = 0.0
                reduction_rate = 0.0
            
            return {
                'ticks_processed': self.stats['total_ticks_processed'],
                'trades_approved': self.stats['total_trades_approved'],
                'trades_rejected': self.stats['total_trades_rejected'],
                'sizing_reductions': self.stats['total_sizing_reductions'],
                'approval_rate': approval_rate,
                'reduction_rate': reduction_rate
            }
