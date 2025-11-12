"""
Conflict Arbiter - VersiÃ³n Institucional con 12 Mejoras Integradas

Este es el nÃºcleo del Portfolio Manager Layer con arquitectura de producciÃ³n.

MEJORAS IMPLEMENTADAS:
1. Conversiones correctas usando instrument_specs.json
2. Colinearidad real con CorrelationTracker.get_colinearity_matrix()
3. EV condicional por [horizon][regime][strategy_id]
4. Slippage con impacto de tamaÃ±o: qty/depth + notional/ADV
5. Fill probability realista segÃºn execution_style
6. VerificaciÃ³n de family_budgets antes de EXECUTE
7. SerializaciÃ³n segura con asdict() para ev_calculations
8. Gating con shutdown duro cuando spread > threshold
9. No-trade zone dinÃ¡mica con colinealidad y data_quality
10. Idempotencia con DecisionLedger y UUIDs
11. Invariantes con asserts
12. Event sourcing completo con reason codes
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Tuple
from datetime import datetime
from collections import defaultdict
from dataclasses import dataclass, asdict
import threading
import logging
import json
import hashlib
from pathlib import Path

from core.signal_schema import InstitutionalSignal
from core.regime_engine import RegimeEngine
from typing import Optional
try:
    from core.position_sizer import PositionSize
except ImportError:
    PositionSize = None  # Will be available after position_sizer.py is created
from core.correlation_tracker import CORRELATION_TRACKER
from core.decision_ledger import DECISION_LEDGER

logger = logging.getLogger(__name__)


@dataclass
class IntentionLock:
    """Lock de intenciÃ³n para prevenir race conditions."""
    instrument: str
    horizon: str
    batch_id: str
    timestamp: datetime
    thread_id: int


@dataclass
class EVCalculation:
    """Resultado de cÃ¡lculo de Expected Value."""
    ev_raw: float
    slippage_bp: float
    fees_bp: float
    ev_net: float
    fill_probability: float
    hit_rate_conditional: float  # Hit rate especÃ­fico de [horizon][regime]
    payoff_conditional: float  # Payoff especÃ­fico de [horizon][regime]
    reasoning: str
    
    def to_dict(self) -> Dict:
        """SerializaciÃ³n segura."""
        return asdict(self)


@dataclass
class ConflictResolution:
    """Resultado de resoluciÃ³n de conflicto."""
    decision: str  # 'EXECUTE', 'SILENCE', 'REJECT'
    winning_signal: Optional[InstitutionalSignal]
    losing_signals: List[InstitutionalSignal]
    reason_codes: List[str]
    net_direction_weight: float
    regime_probs: Dict[str, float]
    ev_calculations: Dict[str, Dict]  # Serializado como dict
    colinearity_matrix: Optional[List[List[float]]]  # Serializado como list
    metadata: Dict
    position_size: Optional['PositionSize'] = None  # Tamaño calculado de posición
    
    def to_dict(self) -> Dict:
        """SerializaciÃ³n completa para ledger."""
        return {
            'decision': self.decision,
            'winning_signal': self.winning_signal.to_dict() if self.winning_signal else None,
            'losing_signals': [s.to_dict() for s in self.losing_signals],
            'reason_codes': self.reason_codes,
            'net_direction_weight': self.net_direction_weight,
            'regime_probs': self.regime_probs,
            'ev_calculations': self.ev_calculations,
            'colinearity_matrix': self.colinearity_matrix,
            'metadata': self.metadata
        }


class ConflictArbiter:
    """
    Ãrbitro de conflictos con EV explÃ­cito y arquitectura institucional.
    
    RESPONSABILIDADES:
    - Calcular EV neto condicional por rÃ©gimen y horizonte
    - Detectar colinealidad real usando matriz EWMA histÃ³rica
    - Modelar slippage con impacto de tamaÃ±o (qty/depth, notional/ADV)
    - Aplicar gating con shutdown duro durante degradaciÃ³n de liquidez
    - Verificar presupuestos por familia antes de ejecutar
    - Garantizar idempotencia con UUIDs determinÃ­sticos
    - Event sourcing completo con reason codes serializables
    
    INVARIANTES GARANTIZADOS:
    - Una sola decisiÃ³n por instrument-horizon-batch_id
    - No-Hedge: nunca dos direcciones opuestas
    - Idempotencia: mismo input â†’ mismo output
    - EV-guard: solo ejecuta si ev_net >= threshold
    """
    
    def __init__(self, regime_engine: RegimeEngine):
        """
        Args:
            regime_engine: Engine de clasificaciÃ³n de rÃ©gimen
        """
        self.regime_engine = regime_engine
        
        # Cargar instrument specs
        self.instrument_specs = self._load_instrument_specs()
        
        # Decision ticks
        self.decision_tick_ms = 200
        self.batch_id_counter = 0
        self.batch_id_lock = threading.Lock()
        
        # Intention locks
        self.intention_locks: Dict[str, IntentionLock] = {}
        self.lock_timeout_seconds = 5.0
        
        # Strategy families
        self.strategy_families = {
            'MOMENTUM': [
                'liquidity_sweep', 'momentum_quality', 'breakout_volume_confirmation',
                'absorption_breakout', 'order_flow_toxicity'
            ],
            'MEAN_REVERSION': [
                'mean_reversion_statistical', 'correlation_divergence'
            ],
            'MICROSTRUCTURE': [
                'ofi_refinement', 'fvg_institutional', 'order_block_institutional',
                'htf_ltf_liquidity', 'idp_inducement_distribution', 'iceberg_detection'
            ],
            'VOLATILITY': [
                'volatility_regime_adaptation', 'kalman_pairs_trading'
            ]
        }
        
        # No-trade zone base por horizonte
        self.base_no_trade_zones = {
            'scalp': 0.3,
            'intraday': 0.5,
            'swing': 0.7
        }
        
        # Risk budgets por familia (fraction of capital)
        self.family_budgets = {
            'MOMENTUM': 0.35,
            'MEAN_REVERSION': 0.25,
            'MICROSTRUCTURE': 0.30,
            'VOLATILITY': 0.10
        }
        
        # Exposure tracking por familia e instrumento
        self.family_exposure: Dict[str, float] = defaultdict(float)
        self.instrument_positions: Dict[str, Dict] = {}  # {instrument: {direction, family}}
        
        # Colinearity threshold
        self.colinearity_threshold = 0.7
        self.mutual_exclusion_threshold = 0.85  # Si |Ï| > 0.85, elegir solo una
        
        # EV parameters
        self.ev_params = {
            'slippage_base_bp': 1.0,
            'slippage_vol_multiplier': 0.5,
            'slippage_depth_factor': 2.0,
            'slippage_size_factor': 0.3,  # k_size
            'slippage_adv_factor': 0.5,   # k_adv
            'fees_bp': 0.5,
            'min_ev_net_bp_base': 2.0,
            'min_ev_net_bp_shock': 5.0,  # Threshold sube durante shock
        }
        
        # Performance tracking por [horizon][regime][strategy_id]
        self.performance_stats: Dict[str, Dict[str, Dict[str, Dict]]] = defaultdict(
            lambda: defaultdict(lambda: defaultdict(lambda: {
                'trades': 0,
                'wins': 0,
                'total_pnl_r': 0.0,
                'total_payoff': 0.0
            }))
        )
        
        # Historial de decisiones
        self.decision_history: List[ConflictResolution] = []
        
        # MÃ©tricas
        self.stats = {
            'total_decisions': 0,
            'executions': 0,
            'silences': 0,
            'rejections': 0,
            'race_conditions_prevented': 0,
            'ev_rejections': 0,
            'regime_gates': 0,
            'colinearity_downweights': 0,
            'mutual_exclusions': 0,
            'budget_violations': 0,
            'liquidity_shutdowns': 0
        }
    
    def _load_instrument_specs(self) -> Dict:
        """Carga especificaciones de instrumentos desde JSON."""
        try:
            specs_path = Path("config/instrument_specs.json")
            with open(specs_path, 'r') as f:
                specs = json.load(f)
            
            logger.info(f"Loaded instrument specs for {len(specs)} instruments")
            return specs
        
        except Exception as e:
            logger.error(f"Failed to load instrument specs: {e}")
            return {}
    
    def get_instrument_spec(self, instrument: str) -> Dict:
        """Obtiene spec del instrumento o DEFAULT."""
        return self.instrument_specs.get(instrument, self.instrument_specs.get('DEFAULT', {}))
    
    def move_to_bp(self, price_move: float, price: float) -> float:
        """
        Convierte movimiento de precio a basis points.
        
        CORRECCIÃ“N: Calculado en runtime, no hardcoded.
        bp = (price_move / price) Ã— 10,000
        """
        if price <= 0:
            return 0.0
        return (price_move / price) * 10000
    
    def get_next_batch_id(self) -> str:
        """Genera batch_id monotÃ³nico thread-safe."""
        with self.batch_id_lock:
            self.batch_id_counter += 1
            return f"BATCH_{self.batch_id_counter:08d}_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}"
    
    def acquire_intention_lock(self, instrument: str, horizon: str, batch_id: str) -> bool:
        """Adquiere lock de intenciÃ³n."""
        lock_key = f"{instrument}_{horizon}"
        now = datetime.now()
        
        if lock_key in self.intention_locks:
            existing_lock = self.intention_locks[lock_key]
            age = (now - existing_lock.timestamp).total_seconds()
            
            if age > self.lock_timeout_seconds:
                logger.warning(
                    f"LOCK_TIMEOUT: Liberando lock expirado {lock_key} "
                    f"(batch={existing_lock.batch_id}, age={age:.1f}s)"
                )
                del self.intention_locks[lock_key]
            else:
                logger.debug(
                    f"LOCK_CONTENTION: {lock_key} locked por {existing_lock.batch_id}"
                )
                self.stats['race_conditions_prevented'] += 1
                return False
        
        self.intention_locks[lock_key] = IntentionLock(
            instrument=instrument,
            horizon=horizon,
            batch_id=batch_id,
            timestamp=now,
            thread_id=threading.get_ident()
        )
        
        logger.debug(f"LOCK_ACQUIRED: {lock_key} por {batch_id}")
        return True
    
    def release_intention_lock(self, instrument: str, horizon: str, batch_id: str):
        """Libera lock de intenciÃ³n."""
        lock_key = f"{instrument}_{horizon}"
        
        if lock_key in self.intention_locks:
            lock = self.intention_locks[lock_key]
            if lock.batch_id == batch_id:
                del self.intention_locks[lock_key]
                logger.debug(f"LOCK_RELEASED: {lock_key} por {batch_id}")
    
    def decide(self, signals: List[InstitutionalSignal], 
               data: pd.DataFrame, features: Dict,
               batch_id: Optional[str] = None,
               data_slice_hash: Optional[str] = None) -> ConflictResolution:
        """
        Decide quÃ© seÃ±al ejecutar (o ninguna).
        
        ALGORITMO COMPLETO:
        1. Validar y adquirir lock
        2. Obtener rÃ©gimen
        3. Aplicar gating por rÃ©gimen (con shutdown duro)
        4. Calcular EV neto condicional
        5. Verificar budgets por familia
        6. Detectar colinealidad real y down-weight
        7. Calcular net direction weight
        8. Comparar contra no-trade zone dinÃ¡mica
        9. Decidir y aplicar invariantes
        10. Registrar en ledger con idempotencia
        """
        # Generar IDs
        if batch_id is None:
            batch_id = self.get_next_batch_id()
        
        if data_slice_hash is None:
            data_slice_hash = self._hash_dataframe(data)
        
        # Validar seÃ±ales
        if not signals:
            return self._create_rejection("NO_SIGNALS", [], batch_id, data_slice_hash)
        
        instrument = signals[0].instrument
        horizon = signals[0].horizon
        
        if not all(s.instrument == instrument and s.horizon == horizon for s in signals):
            return self._create_rejection("MIXED_INSTRUMENTS", signals, batch_id, data_slice_hash)
        
        # Adquirir lock
        if not self.acquire_intention_lock(instrument, horizon, batch_id):
            return self._create_rejection("LOCK_CONTENTION", signals, batch_id, data_slice_hash)
        
        try:
            # PASO 1: Obtener rÃ©gimen
            regime_probs = self.regime_engine.classify_regime(
                data, features, 
                batch_id=batch_id, 
                data_slice_id=data_slice_hash
            )
            
            logger.info(
                f"ARBITER_START: {instrument}_{horizon} batch={batch_id} "
                f"signals={len(signals)} regime={regime_probs}"
            )
            
            # PASO 2: Gating por rÃ©gimen CON SHUTDOWN DURO
            gated_signals, regime_rejects = self._apply_regime_gating_with_shutdown(
                signals, regime_probs, features, instrument
            )
            
            if not gated_signals:
                return self._create_silence(
                    signals, regime_probs, batch_id, data_slice_hash,
                    reason_codes=['REGIME_GATE_ALL'] if regime_rejects else ['LIQUIDITY_SHUTDOWN'],
                    metadata={'regime_rejects': len(regime_rejects)}
                )
            
            # PASO 3: Calcular EV neto condicional
            ev_calculations = {}
            for signal in gated_signals:
                ev_calc = self._calculate_expected_value_conditional(
                    signal, data, features, regime_probs, horizon
                )
                ev_calculations[signal.strategy_id] = ev_calc
            
            # Determinar threshold dinÃ¡mico de EV
            p_shock = regime_probs.get('shock', 0)
            min_ev_threshold = (
                self.ev_params['min_ev_net_bp_shock'] if p_shock > 0.5
                else self.ev_params['min_ev_net_bp_base']
            )
            
            # Filtrar por EV
            viable_signals = [
                s for s in gated_signals
                if ev_calculations[s.strategy_id].ev_net >= min_ev_threshold
            ]
            
            if not viable_signals:
                self.stats['ev_rejections'] += 1
                return self._create_silence(
                    signals, regime_probs, batch_id, data_slice_hash,
                    reason_codes=['EV_INSUFFICIENT'],
                    metadata={
                        'ev_calculations': {k: v.to_dict() for k, v in ev_calculations.items()},
                        'min_ev_threshold': min_ev_threshold
                    }
                )
            
            # PASO 4: Verificar budgets por familia
            budget_ok, budget_reason = self._check_family_budgets(viable_signals, instrument)
            
            if not budget_ok:
                self.stats['budget_violations'] += 1
                return self._create_silence(
                    signals, regime_probs, batch_id, data_slice_hash,
                    reason_codes=['BUDGET_EXCEEDED'],
                    metadata={'budget_reason': budget_reason}
                )
            
            # PASO 5: Colinealidad real con mutual exclusion
            colinearity_matrix, adjusted_weights, excluded = self._calculate_adjusted_weights_real(
                viable_signals, regime_probs
            )
            
            # Eliminar seÃ±ales con correlaciÃ³n >0.85 (mutual exclusion)
            final_signals = [s for s in viable_signals if s.strategy_id not in excluded]
            
            if not final_signals:
                return self._create_silence(
                    signals, regime_probs, batch_id, data_slice_hash,
                    reason_codes=['MUTUAL_EXCLUSION_ALL'],
                    metadata={'excluded_strategies': excluded}
                )
            
            # PASO 6: Net direction weight
            net_weight = sum(
                adjusted_weights[s.strategy_id] * s.direction
                for s in final_signals
            )
            
            # PASO 7: No-trade zone dinÃ¡mica
            no_trade_threshold = self._calculate_dynamic_no_trade_zone_complete(
                horizon, regime_probs, features, colinearity_matrix, final_signals
            )
            
            # PASO 8: DecisiÃ³n
            if abs(net_weight) < no_trade_threshold:
                return self._create_silence(
                    signals, regime_probs, batch_id, data_slice_hash,
                    reason_codes=['NET_WEIGHT_BELOW_THRESHOLD'],
                    metadata={
                        'net_weight': net_weight,
                        'threshold': no_trade_threshold,
                        'viable_signals': len(final_signals)
                    }
                )
            
            # PASO 9: Seleccionar ganador
            final_direction = 1 if net_weight > 0 else -1
            
            directional_signals = [
                s for s in final_signals
                if s.direction == final_direction
            ]
            
            if not directional_signals:
                return self._create_silence(
                    signals, regime_probs, batch_id, data_slice_hash,
                    reason_codes=['NO_DIRECTIONAL_CONSENSUS'],
                    metadata={'net_weight': net_weight}
                )
            
            # Seleccionar por peso ajustado Ã— EV neto
            winning_signal = max(
                directional_signals,
                key=lambda s: adjusted_weights[s.strategy_id] * ev_calculations[s.strategy_id].ev_net
            )
            
            losing_signals = [s for s in signals if s != winning_signal]
            
            # PASO 10: Invariantes
            self._assert_no_hedge_invariant(instrument, horizon, winning_signal)
            
            # PASO 11: Idempotencia con ledger
            signal_id = winning_signal.metadata.get('signal_id', winning_signal.strategy_id)
            uuid5, ulid_id = DECISION_LEDGER.generate_decision_uid(
                batch_id, signal_id, instrument, horizon
            )
            
            # PASO 12: Crear resoluciÃ³n
            resolution = ConflictResolution(
                decision='EXECUTE',
                winning_signal=winning_signal,
                losing_signals=losing_signals,
                reason_codes=['EV_MAXIMIZATION', 'REGIME_ALIGNED'],
                net_direction_weight=net_weight,
                regime_probs=regime_probs,
                ev_calculations={k: v.to_dict() for k, v in ev_calculations.items()},
                colinearity_matrix=colinearity_matrix.tolist() if colinearity_matrix is not None else None,
                metadata={
                    'batch_id': batch_id,
                    'data_slice_hash': data_slice_hash,
                    'instrument': instrument,
                    'horizon': horizon,
                    'total_signals': len(signals),
                    'viable_signals': len(final_signals),
                    'no_trade_threshold': no_trade_threshold,
                    'winning_weight': adjusted_weights[winning_signal.strategy_id],
                    'winning_ev_net': ev_calculations[winning_signal.strategy_id].ev_net,
                    'uuid5': uuid5,
                    'ulid': ulid_id
                }
            )
            
            # Registrar en ledger
            if not DECISION_LEDGER.write(uuid5, ulid_id, resolution.to_dict()):
                logger.error(f"DUPLICATE_DECISION detected: uuid5={uuid5}")
                return self._create_rejection("DUPLICATE_DECISION", signals, batch_id, data_slice_hash)
            
            # Actualizar tracking
            self._update_position_tracking(instrument, horizon, winning_signal)
            
            logger.info(
                f"CONFLICT_RESOLVED: {winning_signal.strategy_id} gana en {instrument} "
                f"(batch={batch_id}, weight={adjusted_weights[winning_signal.strategy_id]:.3f}, "
                f"ev_net={ev_calculations[winning_signal.strategy_id].ev_net:.2f}bp, "
                f"uuid5={uuid5[:8]}...)"
            )
            
            self.stats['executions'] += 1
            self.stats['total_decisions'] += 1
            self.decision_history.append(resolution)
            
            return resolution
        
        finally:
            self.release_intention_lock(instrument, horizon, batch_id)
    
    def _apply_regime_gating_with_shutdown(self, signals: List[InstitutionalSignal],
                                           regime_probs: Dict[str, float],
                                           features: Dict,
                                           instrument: str) -> Tuple[List, List]:
        """
        Gating por rÃ©gimen CON SHUTDOWN DURO.
        
        CORRECCIÃ“N: Durante shock, si spread > shutdown threshold, silencio total.
        """
        p_shock = regime_probs.get('shock', 0)
        p_trend = regime_probs.get('trend', 0)
        p_range = regime_probs.get('range', 0)
        
        # SHUTDOWN DURO
        if p_shock > 0.5:
            instrument_spec = self.get_instrument_spec(instrument)
            shutdown_threshold = instrument_spec.get('spread_bp_shutdown', 50.0)
            spread_bp = features.get('spread_bp', 0)
            
            if spread_bp > shutdown_threshold:
                logger.warning(
                    f"LIQUIDITY_SHUTDOWN: {instrument} spread={spread_bp:.1f}bp "
                    f"> threshold={shutdown_threshold}bp durante shock (p_shock={p_shock:.2f})"
                )
                self.stats['liquidity_shutdowns'] += 1
                return [], signals  # Rechazar todas
        
        # Gating normal
        enabled_families = set(['MICROSTRUCTURE', 'VOLATILITY'])
        
        if p_trend > 0.6:
            enabled_families.add('MOMENTUM')
        if p_range > 0.6:
            enabled_families.add('MEAN_REVERSION')
        if p_trend < 0.6 and p_range < 0.6 and p_shock < 0.5:
            enabled_families.update(['MOMENTUM', 'MEAN_REVERSION'])
        
        accepted = []
        rejected = []
        
        for signal in signals:
            family = self._get_strategy_family(signal.strategy_id)
            
            if family in enabled_families:
                accepted.append(signal)
            else:
                rejected.append(signal)
                self.stats['regime_gates'] += 1
        
        return accepted, rejected
    
    def _get_strategy_family(self, strategy_id: str) -> str:
        """Mapea strategy_id a familia."""
        strategy_id_lower = strategy_id.lower()
        
        for family, strategies in self.strategy_families.items():
            if any(s in strategy_id_lower for s in strategies):
                return family
        
        return 'MICROSTRUCTURE'
    
    def _calculate_expected_value_conditional(self, signal: InstitutionalSignal,
                                              data: pd.DataFrame, features: Dict,
                                              regime_probs: Dict[str, float],
                                              horizon: str) -> EVCalculation:
        """
        Calcula EV condicional por [horizon][regime][strategy_id].
        
        CORRECCIÃ“N: Usa hit_rate especÃ­fico del rÃ©gimen, no global.
        Si no hay historial, usa prior bayesiano conservador (Jeffreys: 0.5).
        """
        # Determinar rÃ©gimen dominante
        regime = max(regime_probs, key=regime_probs.get)
        
        # Obtener performance condicional
        perf = self.performance_stats[horizon][regime][signal.strategy_id]
        
        if perf['trades'] >= 10:
            # Suficiente historial: usar hit_rate observado
            hit_rate = perf['wins'] / perf['trades']
            avg_payoff = perf['total_payoff'] / perf['trades'] if perf['trades'] > 0 else 1.5
        else:
            # Historial insuficiente: prior conservador
            # Jeffreys prior: Beta(0.5, 0.5) â†’ mean = 0.5
            hit_rate = 0.5
            avg_payoff = 1.5  # Conservative default
            
            logger.debug(
                f"EV_PRIOR: {signal.strategy_id} en {horizon}/{regime} "
                f"con {perf['trades']} trades â†’ usando prior conservador"
            )
        
        # Payoff desde signal o histÃ³rico
        if 'risk_reward_ratio' in signal.metadata:
            payoff_ratio = signal.metadata['risk_reward_ratio']
        elif signal.target_profile:
            payoff_ratio = list(signal.target_profile.values())[0]
        else:
            payoff_ratio = avg_payoff
        
        # EV raw
        ev_raw_r = hit_rate * payoff_ratio - (1 - hit_rate) * 1.0
        
        # Convertir a bp
        stop_distance = signal.stop_distance_points
        entry_price = signal.entry_price
        risk_bp = self.move_to_bp(stop_distance, entry_price)
        
        ev_raw_bp = ev_raw_r * risk_bp
        
        # Slippage CON IMPACTO DE TAMAÃ‘O
        slippage_bp = self._estimate_slippage_with_size(
            data, features, signal, regime_probs
        )
        
        # Fees
        fees_bp = self.ev_params['fees_bp']
        
        # EV neto
        ev_net_bp = ev_raw_bp - slippage_bp - fees_bp
        
        # Fill probability segÃºn execution style
        fill_prob = self._estimate_fill_probability_realistic(
            features, regime_probs, signal
        )
        
        ev_net_bp_adjusted = ev_net_bp * fill_prob
        
        reasoning = (
            f"EV[{horizon}/{regime}] = hit_rate({hit_rate:.2f}) Ã— payoff({payoff_ratio:.1f}R) - "
            f"(1-hit) Ã— 1R = {ev_raw_r:.2f}R = {ev_raw_bp:.1f}bp, "
            f"slippage={slippage_bp:.1f}bp, fees={fees_bp:.1f}bp, "
            f"fill_prob={fill_prob:.2f}, net={ev_net_bp_adjusted:.1f}bp"
        )
        
        return EVCalculation(
            ev_raw=ev_raw_bp,
            slippage_bp=slippage_bp,
            fees_bp=fees_bp,
            ev_net=ev_net_bp_adjusted,
            fill_probability=fill_prob,
            hit_rate_conditional=hit_rate,
            payoff_conditional=payoff_ratio,
            reasoning=reasoning
        )
    
    def _estimate_slippage_with_size(self, data: pd.DataFrame, features: Dict,
                                     signal: InstitutionalSignal,
                                     regime_probs: Dict[str, float]) -> float:
        """
        Slippage con impacto de tamaÃ±o.
        
        MEJORA: slip = base + vol + depth + size + adv
        donde:
        - size: k_size Ã— (qty / top_of_book_depth)
        - adv: k_adv Ã— (notional / ADV_daily)
        """
        base = self.ev_params['slippage_base_bp']
        
        # Vol component
        returns = data['close'].pct_change().dropna()
        vol_realized = returns.tail(20).std() if len(returns) >= 20 else returns.std()
        vol_component = vol_realized * 10000 * self.ev_params['slippage_vol_multiplier']
        
        # Depth component
        spread_bp = features.get('spread_bp', 0)
        median_spread_bp = features.get('median_spread_bp', spread_bp)
        spread_ratio = spread_bp / median_spread_bp if median_spread_bp > 0 else 1.0
        depth_component = self.ev_params['slippage_depth_factor'] * max(0, spread_ratio - 1)
        
        # Size component: necesitamos qty y depth
        # Para simplificar, usamos proxy desde metadata o default conservador
        qty_lots = signal.metadata.get('quantity_lots', 1.0)
        
        # Top of book depth estimado desde ADV
        instrument = signal.instrument
        spec = self.get_instrument_spec(instrument)
        adv_daily = spec.get('adv_daily_lots', 1000)
        
        # Proxy: top_of_book ~ 1% del ADV diario
        top_of_book_estimate = adv_daily * 0.01
        
        size_impact = self.ev_params['slippage_size_factor'] * (qty_lots / top_of_book_estimate)
        
        # ADV component
        notional_usd = qty_lots * signal.entry_price * spec.get('point_value', 100000) / 100000
        adv_daily_usd = adv_daily * signal.entry_price * spec.get('point_value', 100000) / 100000
        
        adv_impact = self.ev_params['slippage_adv_factor'] * (notional_usd / adv_daily_usd) if adv_daily_usd > 0 else 0
        
        # Urgency component
        half_life_min = signal.expected_half_life_seconds / 60
        urgency = 0.5 if half_life_min < 5 else (0.3 if half_life_min < 15 else 0.0)
        
        # Shock multiplier
        p_shock = regime_probs.get('shock', 0)
        shock_mult = 1.0 + p_shock
        
        total_slip = (base + vol_component + depth_component + size_impact + adv_impact + urgency) * shock_mult
        
        return total_slip
    
    def _estimate_fill_probability_realistic(self, features: Dict,
                                             regime_probs: Dict[str, float],
                                             signal: InstitutionalSignal) -> float:
        """
        Fill probability realista segÃºn execution style.
        
        MEJORA: Queue penalty:
        - aggressive (market orders): fill_prob â‰ˆ 1.0 pero slippage alto
        - passive (limit orders): fill_prob mÃ¡s bajo, slippage bajo
        """
        base_fill = 0.95
        
        # Execution style desde metadata
        exec_style = signal.metadata.get('execution_style', 'aggressive')
        
        if exec_style == 'passive':
            # Limit orders: menor probabilidad de fill pero mejor precio
            base_fill = 0.75
        elif exec_style == 'aggressive':
            # Market orders: alto fill pero peor precio
            base_fill = 0.98
        
        # Penalizar por shock
        p_shock = regime_probs.get('shock', 0)
        base_fill -= p_shock * 0.15
        
        # Penalizar por spread ancho
        spread_bp = features.get('spread_bp', 0)
        median_spread_bp = features.get('median_spread_bp', spread_bp)
        
        if median_spread_bp > 0:
            spread_ratio = spread_bp / median_spread_bp
            if spread_ratio > 2.0:
                base_fill -= 0.1
            elif spread_ratio > 1.5:
                base_fill -= 0.05
        
        return max(0.5, min(1.0, base_fill))
    
    def _check_family_budgets(self, signals: List[InstitutionalSignal],
                              instrument: str) -> Tuple[bool, str]:
        """
        Verifica presupuestos por familia antes de ejecutar.
        
        MEJORA: Budget enforcement real, no solo definiciÃ³n.
        """
        for signal in signals:
            family = self._get_strategy_family(signal.strategy_id)
            budget = self.family_budgets.get(family, 0.1)
            current_exposure = self.family_exposure[family]
            
            # Verificar si agregar esta seÃ±al excederÃ­a budget
            # (simplified: asumimos cada seÃ±al = 1% de capital)
            new_exposure = current_exposure + 0.01
            
            if new_exposure > budget:
                reason = f"{family} budget exceeded: {new_exposure:.2%} > {budget:.2%}"
                logger.warning(f"BUDGET_VIOLATION: {reason}")
                return False, reason
        
        return True, ""
    
    def _calculate_adjusted_weights_real(self, signals: List[InstitutionalSignal],
                                         regime_probs: Dict[str, float]) -> Tuple[np.ndarray, Dict, List]:
        """
        Calcula pesos con colinealidad REAL usando CorrelationTracker.
        
        MEJORA: Usa matriz EWMA histÃ³rica, no heurÃ­stica de familia.
        Mutual exclusion si |Ï| > 0.85.
        """
        n = len(signals)
        
        # Pesos iniciales por rÃ©gimen
        initial_weights = {}
        for signal in signals:
            regime_weight = signal.calculate_regime_weight(regime_probs)
            initial_weights[signal.strategy_id] = regime_weight
        
        # Matriz de colinealidad REAL
        strategy_ids = [s.strategy_id for s in signals]
        colinearity_matrix = CORRELATION_TRACKER.get_colinearity_matrix(strategy_ids)
        
        # Mutual exclusion: si |Ï| > 0.85, elegir solo la de mayor peso
        excluded = set()
        
        for i, sig1 in enumerate(signals):
            for j, sig2 in enumerate(signals):
                if i < j and abs(colinearity_matrix[i, j]) > self.mutual_exclusion_threshold:
                    # AltÃ­sima correlaciÃ³n: mutual exclusion
                    weight1 = initial_weights[sig1.strategy_id]
                    weight2 = initial_weights[sig2.strategy_id]
                    
                    if weight1 > weight2:
                        excluded.add(sig2.strategy_id)
                        logger.info(
                            f"MUTUAL_EXCLUSION: {sig2.strategy_id} excluido "
                            f"(corr={colinearity_matrix[i,j]:.2f} con {sig1.strategy_id})"
                        )
                    else:
                        excluded.add(sig1.strategy_id)
                        logger.info(
                            f"MUTUAL_EXCLUSION: {sig1.strategy_id} excluido "
                            f"(corr={colinearity_matrix[i,j]:.2f} con {sig2.strategy_id})"
                        )
                    
                    self.stats['mutual_exclusions'] += 1
        
        # Down-weight por colinealidad para las no-excluidas
        adjusted_weights = {}
        
        for i, signal in enumerate(signals):
            if signal.strategy_id in excluded:
                adjusted_weights[signal.strategy_id] = 0.0
                continue
            
            weight = initial_weights[signal.strategy_id]
            
            # Suma de correlaciones con otras seÃ±ales activas
            colinear_mass = sum(
                abs(colinearity_matrix[i, j]) * initial_weights[signals[j].strategy_id]
                for j in range(n)
                if i != j 
                and signals[j].strategy_id not in excluded
                and abs(colinearity_matrix[i, j]) > self.colinearity_threshold
            )
            
            if colinear_mass > 0:
                downweight_factor = 1.0 / (1.0 + colinear_mass)
                weight *= downweight_factor
                
                logger.debug(
                    f"COLINEARITY_DOWNWEIGHT: {signal.strategy_id} "
                    f"factor={downweight_factor:.2f} (colinear_mass={colinear_mass:.2f})"
                )
                self.stats['colinearity_downweights'] += 1
            
            adjusted_weights[signal.strategy_id] = weight
        
        return colinearity_matrix, adjusted_weights, list(excluded)
    
    def _calculate_dynamic_no_trade_zone_complete(self, horizon: str,
                                                   regime_probs: Dict[str, float],
                                                   features: Dict,
                                                   colinearity_matrix: np.ndarray,
                                                   signals: List[InstitutionalSignal]) -> float:
        """
        No-trade zone dinÃ¡mica COMPLETA.
        
        MEJORA: Î¸ = Î¸_base + k_shockÃ—p_shock + k_volÃ—vol_of_vol + 
                     k_colÃ—mean_corr + k_dqÃ—(1-data_quality)
        """
        base = self.base_no_trade_zones.get(horizon, 0.5)
        
        # Shock adjustment
        p_shock = regime_probs.get('shock', 0)
        shock_adj = 0.3 * p_shock
        
        # Vol-of-vol adjustment
        vol_of_vol = features.get('vol_of_vol', 0)
        vol_adj = 0.2 * min(vol_of_vol, 1.5)
        
        # Spread adjustment
        spread_bp = features.get('spread_bp', 0)
        median_spread_bp = features.get('median_spread_bp', spread_bp)
        spread_ratio = spread_bp / median_spread_bp if median_spread_bp > 0 else 1.0
        spread_adj = 0.2 if spread_ratio > 2.0 else (0.1 if spread_ratio > 1.5 else 0.0)
        
        # Colinealidad adjustment
        if colinearity_matrix is not None and len(signals) > 1:
            # Media de correlaciones absolutas entre seÃ±ales activas
            n = len(signals)
            correlations = []
            for i in range(n):
                for j in range(i+1, n):
                    correlations.append(abs(colinearity_matrix[i, j]))
            
            mean_corr = np.mean(correlations) if correlations else 0.0
            col_adj = 0.15 * max(0.0, mean_corr - 0.6)
        else:
            col_adj = 0.0
        
        # Data quality adjustment
        data_quality = features.get('data_quality', True)
        dq_adj = 0.0 if data_quality else 0.1
        
        dynamic = base + shock_adj + vol_adj + spread_adj + col_adj + dq_adj
        
        logger.debug(
            f"NO_TRADE_ZONE: base={base:.2f}, shock={shock_adj:.2f}, "
            f"vol={vol_adj:.2f}, spread={spread_adj:.2f}, "
            f"col={col_adj:.2f}, dq={dq_adj:.2f}, total={dynamic:.2f}"
        )
        
        return dynamic
    
    def _assert_no_hedge_invariant(self, instrument: str, horizon: str,
                                   winning_signal: InstitutionalSignal):
        """
        Assert del invariante No-Hedge.
        
        INVARIANTE: Nunca dos direcciones opuestas en mismo instrument-horizon.
        """
        key = f"{instrument}_{horizon}"
        
        if key in self.instrument_positions:
            existing = self.instrument_positions[key]
            existing_direction = existing['direction']
            
            assert existing_direction == winning_signal.direction, (
                f"NO_HEDGE_VIOLATION: {instrument} ya tiene {existing_direction} "
                f"pero intentando abrir {winning_signal.direction}"
            )
    
    def _update_position_tracking(self, instrument: str, horizon: str,
                                  signal: InstitutionalSignal):
        """Actualiza tracking de posiciones."""
        key = f"{instrument}_{horizon}"
        family = self._get_strategy_family(signal.strategy_id)
        
        self.instrument_positions[key] = {
            'direction': 'LONG' if signal.direction > 0 else 'SHORT',
            'family': family,
            'strategy': signal.strategy_id
        }
        
        # Incrementar exposure de familia (simplified)
        self.family_exposure[family] += 0.01
    
    def _hash_dataframe(self, df: pd.DataFrame) -> str:
        """Genera hash del DataFrame para reproducibilidad."""
        try:
            # Usar Ãºltimas 100 filas para eficiencia
            data_bytes = df.tail(100).to_numpy().tobytes()
            return hashlib.sha1(data_bytes).hexdigest()[:16]
        except Exception as e:
            logger.debug(f"DataFrame hash failed: {e}")
            return "HASH_UNAVAILABLE"
    
    def _create_silence(self, signals: List[InstitutionalSignal],
                       regime_probs: Dict[str, float],
                       batch_id: str,
                       data_slice_hash: str,
                       reason_codes: List[str],
                       metadata: Dict) -> ConflictResolution:
        """Crea resoluciÃ³n SILENCE."""
        
        logger.warning(
            f"CONFLICT_SILENCE: {len(signals)} seÃ±ales canceladas "
            f"(batch={batch_id}, reasons={reason_codes}, regime={regime_probs})"
        )
        
        resolution = ConflictResolution(
            decision='SILENCE',
            winning_signal=None,
            losing_signals=signals,
            reason_codes=reason_codes,
            net_direction_weight=metadata.get('net_weight', 0.0),
            regime_probs=regime_probs,
            ev_calculations=metadata.get('ev_calculations', {}),
            colinearity_matrix=None,
            metadata={
                **metadata,
                'batch_id': batch_id,
                'data_slice_hash': data_slice_hash,
                'instrument': signals[0].instrument if signals else 'UNKNOWN',
                'horizon': signals[0].horizon if signals else 'UNKNOWN'
            }
        )
        
        self.stats['silences'] += 1
        self.stats['total_decisions'] += 1
        self.decision_history.append(resolution)
        
        return resolution
    
    def _create_rejection(self, reason: str, signals: List[InstitutionalSignal],
                         batch_id: str, data_slice_hash: str) -> ConflictResolution:
        """Crea resoluciÃ³n REJECT."""
        
        logger.error(f"CONFLICT_REJECT: {reason} (batch={batch_id})")
        
        resolution = ConflictResolution(
            decision='REJECT',
            winning_signal=None,
            losing_signals=signals,
            reason_codes=[reason],
            net_direction_weight=0.0,
            regime_probs={},
            ev_calculations={},
            colinearity_matrix=None,
            metadata={
                'batch_id': batch_id,
                'data_slice_hash': data_slice_hash,
                'reason': reason
            }
        )
        
        self.stats['rejections'] += 1
        self.stats['total_decisions'] += 1
        self.decision_history.append(resolution)
        
        return resolution


# ============================================================================
# PARCHE: Performance tracking
# ============================================================================

from collections import defaultdict as _dd
import logging as _logging

def _record_performance_method(self, strategy_id: str, horizon: str, regime: str, pnl_r: float):
    """Registra performance condicional."""
    if not hasattr(self, 'performance_stats'):
        self.performance_stats = _dd(
            lambda: _dd(
                lambda: _dd(
                    lambda: {'trades':0,'wins':0,'total_pnl_r':0.0,'total_payoff':0.0}
                )
            )
        )
    
    perf = self.performance_stats[horizon][regime][strategy_id]
    perf['trades'] += 1
    if pnl_r > 0:
        perf['wins'] += 1
    perf['total_pnl_r'] += pnl_r
    perf['total_payoff'] += abs(pnl_r)
    
    _logging.getLogger(__name__).debug(
        f"PERF_RECORD: {strategy_id} [{horizon}/{regime}] pnl={pnl_r:.2f}R"
    )

if not hasattr(ConflictArbiter, "record_performance"):
    ConflictArbiter.record_performance = _record_performance_method


