"""
Correlation Tracker - Matriz EWMA de Correlación Histórica de Señales
Rastrea correlación entre estrategias basada en retornos reales de señales.
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Tuple
from collections import deque, defaultdict
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)


class CorrelationTracker:
    """
    Mantiene matriz EWMA de correlación entre estrategias.
    
    La correlación se calcula sobre retornos de señales (PnL normalizado),
    no sobre precios de mercado. Esto captura si dos estrategias generan
    alphas correlacionados versus independientes.
    """
    
    def __init__(self, decay_halflife_days: int = 30):
        """
        Args:
            decay_halflife_days: Half-life para decay exponencial
        """
        # Retornos históricos por estrategia
        self.strategy_returns: Dict[str, deque] = defaultdict(lambda: deque(maxlen=500))
        
        # Matriz de correlación EWMA
        self.correlation_matrix: Dict[Tuple[str, str], float] = {}
        
        # Configuración
        self.decay_alpha = np.exp(-np.log(2) / decay_halflife_days)
        
        # Timestamp de última actualización
        self.last_update: Dict[Tuple[str, str], datetime] = {}
        
        # Métricas
        self.stats = {
            'total_updates': 0,
            'high_correlations_detected': 0
        }
    
    def record_signal_outcome(self, strategy_id: str, pnl_r: float):
        """
        Registra outcome de una señal (PnL en unidades de R).
        
        Args:
            strategy_id: ID de la estrategia
            pnl_r: PnL normalizado (1R = stop_distance)
        """
        self.strategy_returns[strategy_id].append({
            'timestamp': datetime.now(),
            'pnl_r': pnl_r
        })
        
        logger.debug(f"CORR_TRACKER: Recorded {strategy_id} pnl={pnl_r:.2f}R")
    
    def update_correlation_matrix(self):
        """Recalcula matriz de correlación EWMA."""
        strategies = list(self.strategy_returns.keys())
        
        for i, strat1 in enumerate(strategies):
            for strat2 in strategies[i+1:]:
                corr = self._calculate_pairwise_correlation(strat1, strat2)
                
                key = tuple(sorted([strat1, strat2]))
                self.correlation_matrix[key] = corr
                self.last_update[key] = datetime.now()
                
                if abs(corr) > 0.85:
                    logger.info(
                        f"HIGH_CORRELATION: {strat1} ↔ {strat2} = {corr:.3f}"
                    )
                    self.stats['high_correlations_detected'] += 1
        
        self.stats['total_updates'] += 1
    
    def get_correlation(self, strat1: str, strat2: str) -> float:
        """
        Obtiene correlación entre dos estrategias.
        
        Returns:
            Correlación [-1, 1] o 0.0 si no hay data suficiente
        """
        key = tuple(sorted([strat1, strat2]))
        return self.correlation_matrix.get(key, 0.0)
    
    def get_colinearity_matrix(self, strategy_ids: List[str]) -> np.ndarray:
        """
        Construye matriz de correlación para un set de estrategias.
        
        Args:
            strategy_ids: Lista de IDs de estrategias
        
        Returns:
            Matriz NxN de correlaciones
        """
        n = len(strategy_ids)
        matrix = np.eye(n)
        
        for i, strat1 in enumerate(strategy_ids):
            for j, strat2 in enumerate(strategy_ids):
                if i != j:
                    matrix[i, j] = self.get_correlation(strat1, strat2)
        
        return matrix
    
    def _calculate_pairwise_correlation(self, strat1: str, strat2: str) -> float:
        """Calcula correlación entre dos estrategias usando EWMA."""
        returns1 = self.strategy_returns[strat1]
        returns2 = self.strategy_returns[strat2]
        
        if len(returns1) < 10 or len(returns2) < 10:
            return 0.0  # Insuficiente data
        
        # Alinear timestamps y extraer retornos comunes
        # (señales pueden no ser simultáneas, buscamos overlap temporal)
        series1 = pd.Series([r['pnl_r'] for r in returns1],
                           index=[r['timestamp'] for r in returns1])
        series2 = pd.Series([r['pnl_r'] for r in returns2],
                           index=[r['timestamp'] for r in returns2])
        
        # Resample a daily para tener puntos comparables
        daily1 = series1.resample('1D').sum()
        daily2 = series2.resample('1D').sum()
        
        # Align
        aligned = pd.DataFrame({'s1': daily1, 's2': daily2}).dropna()
        
        if len(aligned) < 5:
            return 0.0
        
        # Correlación con decay exponencial (más peso a reciente)
        weights = np.array([self.decay_alpha ** i for i in range(len(aligned))][::-1])
        weights /= weights.sum()
        
        # Weighted correlation
        mean1 = np.average(aligned['s1'], weights=weights)
        mean2 = np.average(aligned['s2'], weights=weights)
        
        cov = np.average(
            (aligned['s1'] - mean1) * (aligned['s2'] - mean2),
            weights=weights
        )
        
        std1 = np.sqrt(np.average((aligned['s1'] - mean1)**2, weights=weights))
        std2 = np.sqrt(np.average((aligned['s2'] - mean2)**2, weights=weights))
        
        if std1 > 0 and std2 > 0:
            corr = cov / (std1 * std2)
            return np.clip(corr, -1.0, 1.0)
        else:
            return 0.0


# Instancia global
CORRELATION_TRACKER = CorrelationTracker()
