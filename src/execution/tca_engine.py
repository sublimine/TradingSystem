"""
TCA Engine - Transaction Cost Analysis institucional
Mide y descompone costos completos de cada trade.
"""

import logging
from typing import Dict, List, Optional
from datetime import datetime
from dataclasses import dataclass
import numpy as np

logger = logging.getLogger(__name__)


@dataclass
class TCAPreTrade:
    """Análisis pre-trade."""
    instrument: str
    order_size: float
    current_spread: float
    volatility_5min: float
    volume_relative: float
    expected_slippage_bps: float
    expected_impact_bps: float
    total_cost_estimate_bps: float
    recommendation: str  # 'execute', 'reduce_size', 'wait'


@dataclass
class TCAAtTrade:
    """Análisis at-trade."""
    order_id: str
    instrument: str
    side: str
    order_size: float
    mid_at_decision: float
    mid_at_send: float
    mid_at_fill: float
    fill_price: float
    hold_time_ms: float
    
    # Descomposición de costos
    spread_capture_bps: float
    market_impact_bps: float
    timing_cost_bps: float
    adverse_selection_bps: float
    total_cost_bps: float


@dataclass
class TCAPostTrade:
    """Análisis post-trade agregado."""
    period_start: datetime
    period_end: datetime
    total_trades: int
    
    # Estadísticas de costos (en bps)
    mean_cost_bps: float
    median_cost_bps: float
    std_cost_bps: float
    p95_cost_bps: float
    p99_cost_bps: float
    
    # Por instrumento
    costs_by_instrument: Dict[str, Dict]
    
    # Por estrategia
    costs_by_strategy: Dict[str, Dict]
    
    # Por hora del día
    costs_by_hour: Dict[int, Dict]


class TCAEngine:
    """
    Transaction Cost Analysis Engine.
    
    Implementa análisis en tres niveles:
    - Pre-trade: estima costos antes de ejecutar
    - At-trade: mide costos durante ejecución
    - Post-trade: analiza distribución de costos
    """
    
    def __init__(self):
        """Inicializa TCA engine."""
        self._at_trade_records: List[TCAAtTrade] = []
        
        logger.info("TCAEngine initialized")
    
    def analyze_pre_trade(
        self,
        instrument: str,
        order_size: float,
        current_spread: float,
        recent_bars: List[Dict],
        average_volume: float
    ) -> TCAPreTrade:
        """
        Análisis pre-trade: estima costos esperados.
        
        Args:
            instrument: Instrumento
            order_size: Tamaño propuesto (lotes)
            current_spread: Spread actual
            recent_bars: Barras recientes para calcular volatility
            average_volume: Volumen promedio del instrumento
            
        Returns:
            TCAPreTrade con estimaciones
        """
        # Calcular volatility de últimos 5 minutos
        if len(recent_bars) >= 5:
            closes = [bar['close'] for bar in recent_bars[-5:]]
            returns = np.diff(closes) / closes[:-1]
            volatility_5min = np.std(returns)
        else:
            volatility_5min = 0.0001  # Default
        
        # Volumen relativo (orden / volumen promedio)
        volume_relative = order_size / average_volume if average_volume > 0 else 0
        
        # Estimar slippage (spread + vol impact)
        spread_bps = current_spread * 10000
        vol_impact_bps = volatility_5min * 10000 * 0.5
        expected_slippage_bps = spread_bps + vol_impact_bps
        
        # Estimar market impact (proporcional a tamaño relativo)
        # Modelo simplificado: impact = k * sqrt(volume_relative)
        k = 5.0  # Parámetro de impacto
        expected_impact_bps = k * np.sqrt(volume_relative) if volume_relative > 0 else 0
        
        # Costo total estimado
        total_cost_estimate_bps = expected_slippage_bps + expected_impact_bps
        
        # Recomendación
        if total_cost_estimate_bps > 20:
            recommendation = 'reduce_size'
        elif total_cost_estimate_bps > 10:
            recommendation = 'wait'
        else:
            recommendation = 'execute'
        
        return TCAPreTrade(
            instrument=instrument,
            order_size=order_size,
            current_spread=current_spread,
            volatility_5min=volatility_5min,
            volume_relative=volume_relative,
            expected_slippage_bps=expected_slippage_bps,
            expected_impact_bps=expected_impact_bps,
            total_cost_estimate_bps=total_cost_estimate_bps,
            recommendation=recommendation
        )
    
    def analyze_at_trade(
        self,
        order_id: str,
        instrument: str,
        side: str,
        order_size: float,
        mid_at_decision: float,
        mid_at_send: float,
        mid_at_fill: float,
        fill_price: float,
        hold_time_ms: float
    ) -> TCAAtTrade:
        """
        Análisis at-trade: descompone costos durante ejecución.
        
        Args:
            order_id: ID de la orden
            instrument: Instrumento
            side: 'buy' o 'sell'
            order_size: Tamaño ejecutado
            mid_at_decision: Mid cuando se decidió tradear
            mid_at_send: Mid cuando se envió la orden
            mid_at_fill: Mid cuando se llenó
            fill_price: Precio de fill
            hold_time_ms: Tiempo de hold
            
        Returns:
            TCAAtTrade con descomposición completa
        """
        # Spread capture (diferencia entre fill y mid al enviar)
        spread_capture = abs(fill_price - mid_at_send)
        spread_capture_bps = spread_capture / mid_at_send * 10000
        
        # Market impact (movimiento del mid durante hold)
        market_impact = abs(mid_at_fill - mid_at_send)
        market_impact_bps = market_impact / mid_at_send * 10000
        
        # Timing cost (movimiento del mid antes de enviar)
        timing_cost = abs(mid_at_send - mid_at_decision)
        timing_cost_bps = timing_cost / mid_at_decision * 10000
        
        # Adverse selection (movimiento post-fill)
        # Si compramos y el precio subió después, fue adverse
        if side == 'buy':
            adverse_selection = max(0, mid_at_fill - mid_at_send)
        else:
            adverse_selection = max(0, mid_at_send - mid_at_fill)
        
        adverse_selection_bps = adverse_selection / mid_at_send * 10000
        
        # Costo total
        total_cost_bps = (
            spread_capture_bps +
            market_impact_bps +
            timing_cost_bps +
            adverse_selection_bps
        )
        
        record = TCAAtTrade(
            order_id=order_id,
            instrument=instrument,
            side=side,
            order_size=order_size,
            mid_at_decision=mid_at_decision,
            mid_at_send=mid_at_send,
            mid_at_fill=mid_at_fill,
            fill_price=fill_price,
            hold_time_ms=hold_time_ms,
            spread_capture_bps=spread_capture_bps,
            market_impact_bps=market_impact_bps,
            timing_cost_bps=timing_cost_bps,
            adverse_selection_bps=adverse_selection_bps,
            total_cost_bps=total_cost_bps
        )
        
        # Almacenar para análisis post-trade
        self._at_trade_records.append(record)
        
        return record
    
    def analyze_post_trade(
        self,
        start_date: datetime,
        end_date: datetime
    ) -> TCAPostTrade:
        """
        Análisis post-trade: distribución agregada de costos.
        
        Args:
            start_date: Fecha inicio del período
            end_date: Fecha fin del período
            
        Returns:
            TCAPostTrade con estadísticas agregadas
        """
        # Filtrar registros del período
        period_records = [
            r for r in self._at_trade_records
            # En producción filtrarías por timestamp del record
        ]
        
        if not period_records:
            return TCAPostTrade(
                period_start=start_date,
                period_end=end_date,
                total_trades=0,
                mean_cost_bps=0,
                median_cost_bps=0,
                std_cost_bps=0,
                p95_cost_bps=0,
                p99_cost_bps=0,
                costs_by_instrument={},
                costs_by_strategy={},
                costs_by_hour={}
            )
        
        # Extraer costos totales
        total_costs = [r.total_cost_bps for r in period_records]
        
        # Estadísticas
        mean_cost = np.mean(total_costs)
        median_cost = np.median(total_costs)
        std_cost = np.std(total_costs)
        p95_cost = np.percentile(total_costs, 95)
        p99_cost = np.percentile(total_costs, 99)
        
        # Por instrumento
        costs_by_instrument = {}
        instruments = set(r.instrument for r in period_records)
        
        for instrument in instruments:
            inst_costs = [
                r.total_cost_bps for r in period_records
                if r.instrument == instrument
            ]
            
            costs_by_instrument[instrument] = {
                'count': len(inst_costs),
                'mean_bps': np.mean(inst_costs),
                'median_bps': np.median(inst_costs),
                'p95_bps': np.percentile(inst_costs, 95)
            }
        
        return TCAPostTrade(
            period_start=start_date,
            period_end=end_date,
            total_trades=len(period_records),
            mean_cost_bps=mean_cost,
            median_cost_bps=median_cost,
            std_cost_bps=std_cost,
            p95_cost_bps=p95_cost,
            p99_cost_bps=p99_cost,
            costs_by_instrument=costs_by_instrument,
            costs_by_strategy={},  # Implementar si hay info de estrategia
            costs_by_hour={}       # Implementar desagregación horaria
        )
    
    def get_statistics(self) -> Dict:
        """Obtiene estadísticas generales."""
        if not self._at_trade_records:
            return {'total_records': 0}
        
        total_costs = [r.total_cost_bps for r in self._at_trade_records]
        
        return {
            'total_records': len(self._at_trade_records),
            'mean_cost_bps': np.mean(total_costs),
            'median_cost_bps': np.median(total_costs),
            'best_cost_bps': np.min(total_costs),
            'worst_cost_bps': np.max(total_costs)
        }