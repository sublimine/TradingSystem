"""
Portfolio Manager Layer - Version con Position Sizing Integrado
"""

import logging
from typing import Dict, List, Optional
import pandas as pd
import uuid
from datetime import datetime

from core.regime_engine import RegimeEngine
from core.conflict_arbiter import ConflictArbiter
from core.signal_bus import get_signal_bus
from core.correlation_tracker import CORRELATION_TRACKER
from core.decision_ledger import DECISION_LEDGER
from core.budget_manager import BudgetManager
from core.position_sizer import PositionSizer

logger = logging.getLogger(__name__)


class PortfolioManagerLayer:
    """Portfolio Manager Layer con position sizing institucional integrado."""
    
    def __init__(self, 
                 total_capital: float = 10000.0,
                 family_allocations: Optional[Dict[str, float]] = None,
                 strategy_families: Optional[Dict[str, str]] = None):
        
        if family_allocations is None:
            family_allocations = {
                'momentum': 0.35,
                'mean_reversion': 0.25,
                'breakout': 0.20,
                'other': 0.15
            }
        
        if strategy_families is None:
            strategy_families = {
                'momentum_quality': 'momentum',
            }
        
        self.total_capital = total_capital
        self.strategy_families = strategy_families
        
        self.regime_engine = RegimeEngine(min_dwell_ticks=5, timeframe_seconds=60)
        self.conflict_arbiter = ConflictArbiter(regime_engine=self.regime_engine)
        self.signal_bus = get_signal_bus(arbiter=self.conflict_arbiter)
        self.correlation_tracker = CORRELATION_TRACKER
        self.decision_ledger = DECISION_LEDGER
        
        self.budget_manager = BudgetManager(total_capital, family_allocations)
        self.position_sizer = PositionSizer(
            total_capital=total_capital,
            kelly_fraction=0.25,
            min_position_pct=0.002,
            max_position_pct=0.05
        )
        
        self.total_ticks_processed = 0
        self.total_executions = 0
        self.total_silences = 0
        self.total_rejections = 0
        
        logger.info(
            f"PortfolioManagerLayer inicializado: capital=${total_capital:,.2f}, "
            f"familias={len(family_allocations)}"
        )
    
    def process_decision_tick(
        self,
        data_by_instrument: Dict[str, pd.DataFrame],
        features_by_instrument: Dict[str, Dict],
        batch_id: Optional[str] = None
    ) -> Dict:
        
        if batch_id is None:
            batch_id = self.conflict_arbiter.get_next_batch_id()
        
        self.total_ticks_processed += 1
        logger.info(f"PML_TICK_START: batch={batch_id} tick={self.total_ticks_processed}")
        
        decisions = self.signal_bus.process_decision_tick(
            data_by_instrument=data_by_instrument,
            features_by_instrument=features_by_instrument,
            batch_id=batch_id
        )
        
        for group_key, res in decisions.items():
            win = res.winning_signal
            
            if isinstance(group_key, tuple):
                instrument, horizon = group_key
                group_str = f"{instrument}_{horizon}"
            else:
                group_str = str(group_key)
            
            decision_key = f"{batch_id}:{group_str}:{win.strategy_id if win else 'NONE'}"
            decision_uuid5 = str(uuid.uuid5(uuid.NAMESPACE_DNS, decision_key))
            ulid_temporal = f"ULID_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}"
            
            payload = {
                'batch_id': batch_id,
                'group': group_str,
                'decision': res.decision,
                'reason_codes': res.reason_codes,
                'instrument': getattr(win, "instrument", None),
                'horizon': getattr(win, "horizon", None),
                'winner': getattr(win, "strategy_id", None),
                'net_direction_weight': res.net_direction_weight,
                'regime_probs': res.regime_probs,
                'ulid': ulid_temporal,
                'timestamp': datetime.now().isoformat()
            }
            
            if win and res.ev_calculations:
                ev_obj = res.ev_calculations.get(win.strategy_id)
                if ev_obj is not None:
                    try:
                        payload['ev_net_bp'] = getattr(ev_obj, "ev_net", None)
                        payload['ev_reasoning'] = getattr(ev_obj, "reasoning", "")
                    except (AttributeError, TypeError):
                        try:
                            payload['ev_net_bp'] = ev_obj.get('ev_net')
                            payload['ev_reasoning'] = ev_obj.get('reasoning', "")
                        except Exception:
                            pass
            
            self.decision_ledger.write(decision_uuid5, payload)
        
        executions_with_sizing = []
        
        for group_key, resolution in decisions.items():
            if resolution.decision == 'EXECUTE' and resolution.winning_signal:
                signal = resolution.winning_signal
                family = self.strategy_families.get(signal.strategy_id, 'other')
                
                available_fraction = self.budget_manager.get_available_fraction(family)
                
                position_size = self.position_sizer.calculate_size(
                    signal=signal,
                    regime_probs=resolution.regime_probs,
                    available_capital_fraction=available_fraction,
                    historical_stats=None
                )
                
                executions_with_sizing.append({
                    'signal': signal,
                    'position_size': position_size,
                    'family': family
                })
                
                self.total_executions += 1
                
                logger.info(
                    f"EXECUTION_WITH_SIZING: {signal.strategy_id} {signal.instrument} "
                    f"size={position_size.capital_fraction:.4f} (${position_size.capital_amount:,.2f}) "
                    f"family={family}"
                )
            
            elif resolution.decision == 'SILENCE':
                self.total_silences += 1
            elif resolution.decision == 'REJECT':
                self.total_rejections += 1
        
        self._assert_no_duplicate_directions([e['signal'] for e in executions_with_sizing])
        
        stats = {
            'total_decisions': len(decisions),
            'executions': len(executions_with_sizing),
            'silences': sum(1 for d in decisions.values() if d.decision == 'SILENCE'),
            'rejections': sum(1 for d in decisions.values() if d.decision == 'REJECT'),
            'signal_bus': self.signal_bus.get_stats(),
            'arbiter': self.conflict_arbiter.stats,
            'regime_engine': self.regime_engine.stats,
            'budget_utilization': self.budget_manager.get_utilization()
        }
        
        logger.info(f"PML_TICK_END: batch={batch_id} executions={len(executions_with_sizing)}")
        
        return {
            'decisions': decisions,
            'batch_id': batch_id,
            'tick': self.total_ticks_processed,
            'executions': executions_with_sizing,
            'stats': stats
        }
    
    def _assert_no_duplicate_directions(self, executions: List):
        seen = set()
        for sig in executions:
            key = (sig.instrument, sig.horizon)
            if key in seen:
                raise RuntimeError(f"NO_HEDGE_INVARIANT_BROKEN: {key}")
            seen.add(key)
    
    def record_signal_outcome(self, strategy_id: str, pnl_r: float, horizon: str, regime: str):
        self.correlation_tracker.record_signal_outcome(strategy_id, pnl_r)
        
        if not hasattr(self.conflict_arbiter, "performance_stats"):
            from collections import defaultdict
            self.conflict_arbiter.performance_stats = defaultdict(
                lambda: defaultdict(
                    lambda: defaultdict(
                        lambda: {'trades':0,'wins':0,'total_pnl_r':0.0,'total_payoff':0.0}
                    )
                )
            )
        
        if hasattr(self.conflict_arbiter, "record_performance"):
            self.conflict_arbiter.record_performance(strategy_id, horizon, regime, pnl_r)
        else:
            perf = self.conflict_arbiter.performance_stats[horizon][regime][strategy_id]
            perf['trades'] += 1
            if pnl_r > 0:
                perf['wins'] += 1
            perf['total_pnl_r'] += pnl_r
            perf['total_payoff'] += abs(pnl_r)
        
        logger.info(f"OUTCOME_RECORDED: {strategy_id} pnl={pnl_r:.2f}R [{horizon}/{regime}]")
    
    def update_correlations(self):
        self.correlation_tracker.update_correlation_matrix()
        logger.info("CORRELATIONS_UPDATED")
    
    def export_ledger(self, filepath: str):
        import os
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        self.decision_ledger.export_to_json(filepath)
        logger.info(f"Ledger exportado: {filepath}")
    
    def get_aggregate_stats(self) -> Dict:
        return {
            'total_ticks': self.total_ticks_processed,
            'total_executions': self.total_executions,
            'total_silences': self.total_silences,
            'total_rejections': self.total_rejections,
            'execution_rate': self.total_executions / self.total_ticks_processed if self.total_ticks_processed > 0 else 0.0,
            'signal_bus': self.signal_bus.get_stats(),
            'arbiter': self.conflict_arbiter.stats,
            'regime_engine': self.regime_engine.stats,
            'correlation_tracker': self.correlation_tracker.stats,
            'decision_ledger': self.decision_ledger.stats,
            'budget_manager': self.budget_manager.get_stats()
        }
