"""
Gatekeeper Integrator - Sistema de Protección Unificado

Coordina los tres gatekeepers (Kyle Lambda, ePIN, Spread Monitor)
en un sistema unificado de decisión sobre entrada y sizing.

Este es el punto de control central que consultan todas las estrategias
antes de ejecutar cualquier trade.

Filosofía de decisión:
- Todos los gatekeepers deben estar "green" para permitir trading normal
- Si uno está "yellow", reducir sizing
- Si uno está "red", halt trading

Referencias:
- Risk Management Best Practices - CME Group
- Market Making & Optimal Execution - Stoikov
- High Frequency Trading - Cartea & Jaimungal

Author: Sistema de Trading Institucional
Date: 2025-11-06
Version: 1.0
"""

import numpy as np
from typing import Dict, Optional, Tuple
import logging

from gatekeepers.kyles_lambda import KylesLambdaEstimator
from gatekeepers.epin_estimator import ePINEstimator
from gatekeepers.spread_monitor import SpreadMonitor


class GatekeeperIntegrator:
    """
    Coordinador central del sistema de gatekeepers.
    
    Integra decisiones de tres gatekeepers independientes:
    1. Kyle's Lambda (impacto de mercado)
    2. ePIN/VPIN (informed trading)
    3. Spread Monitor (costos de transacción)
    
    Proporciona decisión unificada sobre:
    - ¿Permitir trading? (halt vs continue)
    - ¿Qué sizing usar? (multiplier 0.0 a 1.2)
    - ¿Qué nivel de precaución? (green/yellow/red)
    """
    
    def __init__(self,
                 kyle_config: Optional[Dict] = None,
                 epin_config: Optional[Dict] = None,
                 spread_config: Optional[Dict] = None):
        """
        Inicializa el integrador con los tres gatekeepers.
        
        Args:
            kyle_config: Config para Kyle's Lambda (opcional)
            epin_config: Config para ePIN (opcional)
            spread_config: Config para Spread Monitor (opcional)
        """
        # Configuraciones por defecto si no se proporcionan
        kyle_config = kyle_config or {}
        epin_config = epin_config or {}
        spread_config = spread_config or {}
        
        # Inicializar los tres gatekeepers
        self.kyle = KylesLambdaEstimator(
            estimation_window=kyle_config.get('estimation_window', 100),
            update_frequency=kyle_config.get('update_frequency', 10),
            historical_window=kyle_config.get('historical_window', 1000)
        )
        
        self.epin = ePINEstimator(
            volume_buckets=epin_config.get('volume_buckets', 50),
            bucket_size=epin_config.get('bucket_size', 10000.0),
            epin_window=epin_config.get('epin_window', 100)
        )
        
        self.spread = SpreadMonitor(
            window_size=spread_config.get('window_size', 100),
            historical_window=spread_config.get('historical_window', 1000)
        )
        
        self.logger = logging.getLogger(self.__class__.__name__)
        
        self.logger.info("Gatekeeper Integrator inicializado con 3 gatekeepers")
    
    def update_all(self,
                   trade_price: float,
                   prev_price: float,
                   volume: float,
                   bid: float,
                   ask: float,
                   prev_mid: float) -> None:
        """
        Actualiza todos los gatekeepers con nuevo tick de mercado.
        
        Args:
            trade_price: Precio de la transacción
            prev_price: Precio previo
            volume: Volumen del trade
            bid: Bid actual
            ask: Ask actual
            prev_mid: Mid price previo
        """
        current_mid = (bid + ask) / 2
        
        # Actualizar Kyle's Lambda
        self.kyle.update(
            current_price=trade_price,
            prev_price=prev_price,
            volume=volume,
            mid_price=current_mid,
            prev_mid=prev_mid
        )
        
        # Actualizar ePIN
        self.epin.update(
            price=trade_price,
            volume=volume,
            prev_mid=prev_mid
        )
        
        # Actualizar Spread Monitor con quoted spread
        self.spread.update_quoted(bid, ask)
    
    def should_halt_trading(self) -> Tuple[bool, str]:
        """
        Determina si se debe detener el trading.
        
        Halt si CUALQUIERA de los tres gatekeepers recomienda halt.
        
        Returns:
            Tuple de (should_halt: bool, reason: str)
        """
        # Verificar cada gatekeeper
        kyle_halt = self.kyle.should_halt_trading()
        epin_halt = self.epin.should_halt_trading()
        spread_halt = self.spread.should_halt_trading()
        
        if kyle_halt:
            return True, "Kyle's Lambda crítico - Impacto de mercado prohibitivo"
        
        if epin_halt:
            return True, "PIN crítico - Alta probabilidad de informed trading"
        
        if spread_halt:
            return True, "Spread crítico - Costos de transacción prohibitivos"
        
        return False, ""
    
    def should_reduce_sizing(self) -> Tuple[bool, str]:
        """
        Determina si se debe reducir sizing.
        
        Reduce si CUALQUIERA de los tres gatekeepers lo recomienda.
        
        Returns:
            Tuple de (should_reduce: bool, reason: str)
        """
        # Verificar cada gatekeeper
        kyle_reduce = self.kyle.should_reduce_sizing()
        epin_reduce = self.epin.should_reduce_sizing()
        spread_reduce = self.spread.should_reduce_sizing()
        
        reasons = []
        
        if kyle_reduce:
            reasons.append("Lambda elevado")
        
        if epin_reduce:
            reasons.append("PIN elevado")
        
        if spread_reduce:
            reasons.append("Spread elevado")
        
        if reasons:
            return True, ", ".join(reasons)
        
        return False, ""
    
    def get_unified_sizing_multiplier(self) -> float:
        """
        Calcula multiplicador de sizing unificado.
        
        Usa el MÍNIMO de los tres multipliers (más conservador).
        
        Returns:
            Multiplicador entre 0.0 y 1.2
        """
        kyle_mult = self.kyle.get_sizing_multiplier()
        epin_mult = self.epin.get_sizing_multiplier()
        spread_mult = self.spread.get_sizing_multiplier()
        
        # Usar el más conservador (mínimo)
        unified_mult = min(kyle_mult, epin_mult, spread_mult)
        
        self.logger.debug(
            f"Sizing multipliers: Kyle={kyle_mult:.2f}, "
            f"ePIN={epin_mult:.2f}, Spread={spread_mult:.2f}, "
            f"Unified={unified_mult:.2f}"
        )
        
        return unified_mult
    
    def get_market_regime(self) -> str:
        """
        Determina el régimen actual del mercado.
        
        Returns:
            'GREEN' (safe), 'YELLOW' (caution), o 'RED' (dangerous)
        """
        should_halt, _ = self.should_halt_trading()
        
        if should_halt:
            return 'RED'
        
        should_reduce, _ = self.should_reduce_sizing()
        
        if should_reduce:
            return 'YELLOW'
        
        return 'GREEN'
    
    def check_trade_approval(self) -> Dict:
        """
        Verifica si un trade puede ejecutarse y con qué sizing.
        
        Esta es la función principal que llaman las estrategias.
        
        Returns:
            Dict con:
            - approved: bool (True si se permite trading)
            - sizing_multiplier: float (multiplicador a aplicar)
            - regime: str ('GREEN', 'YELLOW', 'RED')
            - halt_reason: str (razón de halt si approved=False)
            - warnings: List[str] (advertencias activas)
        """
        should_halt, halt_reason = self.should_halt_trading()
        should_reduce, reduce_reason = self.should_reduce_sizing()
        
        regime = self.get_market_regime()
        sizing_mult = self.get_unified_sizing_multiplier()
        
        warnings = []
        
        if should_reduce:
            warnings.append(reduce_reason)
        
        return {
            'approved': not should_halt,
            'sizing_multiplier': sizing_mult,
            'regime': regime,
            'halt_reason': halt_reason if should_halt else None,
            'warnings': warnings
        }
    
    def get_comprehensive_status(self) -> Dict:
        """
        Retorna status completo de todos los gatekeepers.
        
        Returns:
            Dict con status de cada gatekeeper más decisión unificada
        """
        return {
            'kyle_lambda': self.kyle.get_status_report(),
            'epin': self.epin.get_status_report(),
            'spread': self.spread.get_status_report(),
            'unified': {
                'regime': self.get_market_regime(),
                'sizing_multiplier': self.get_unified_sizing_multiplier(),
                'should_halt': self.should_halt_trading()[0],
                'should_reduce': self.should_reduce_sizing()[0]
            }
        }
