"""Signal Bus - versión con tuplas y singleton."""
from __future__ import annotations

import threading
import logging
from typing import Dict, List, Optional, Tuple
from collections import defaultdict

from core.signal_schema import InstitutionalSignal
from core.conflict_arbiter import ConflictArbiter, ConflictResolution

__all__ = ["SignalBus", "get_signal_bus"]

logger = logging.getLogger(__name__)

class SignalBus:
    """
    Bus central de señales institucionales.
    - Keys: (instrument, horizon) como tuplas (robusto ante underscores).
    - Thread-safe para publicaciones concurrentes.
    """
    def __init__(self, arbiter: ConflictArbiter):
        self.arbiter = arbiter
        self.signal_buffer: Dict[Tuple[str, str], List[InstitutionalSignal]] = defaultdict(list)
        self.lock = threading.Lock()
        self.current_tick = 0
        self.stats = {
            "total_published": 0,
            "expired_filtered": 0,
            "conflicts_resolved": 0,
            "decisions_made": 0
        }

    def publish(self, signal: InstitutionalSignal) -> bool:
        if signal.is_expired():
            logger.debug(
                f"SIGNAL_EXPIRED: {signal.strategy_id} en {signal.instrument}"
            )
            self.stats["expired_filtered"] += 1
            return False

        group_key = (signal.instrument, signal.horizon)  # tupla
        with self.lock:
            self.signal_buffer[group_key].append(signal)
            self.stats["total_published"] += 1

        logger.info(
            f"SIGNAL_PUBLISHED: {signal.strategy_id} → {signal.instrument} "
            f"{signal.direction:+d} (group={group_key}, buffer_size={len(self.signal_buffer[group_key])})"
        )
        return True

    def process_decision_tick(self, data_by_instrument: Dict,
                              features_by_instrument: Dict,
                              batch_id: Optional[str] = None) -> Dict[Tuple[str, str], ConflictResolution]:
        if batch_id is None:
            batch_id = self.arbiter.get_next_batch_id()

        self.current_tick += 1
        logger.info(
            f"DECISION_TICK_START: tick={self.current_tick} batch={batch_id} groups={len(self.signal_buffer)}"
        )

        decisions: Dict[Tuple[str, str], ConflictResolution] = {}

        with self.lock:
            buffer_snapshot = dict(self.signal_buffer)
            self.signal_buffer.clear()

        for group_key, signals in buffer_snapshot.items():
            if not signals:
                continue

            instrument, horizon = group_key
            data = data_by_instrument.get(instrument)
            features = features_by_instrument.get(instrument, {})

            if data is None or getattr(data, "empty", False):
                logger.warning(
                    f"DECISION_SKIP: {group_key} sin data ({len(signals)} señales descartadas)"
                )
                continue

            try:
                resolution = self.arbiter.decide(
                    signals=signals, data=data, features=features, batch_id=batch_id
                )
                decisions[group_key] = resolution
                self.stats["decisions_made"] += 1
                if len(signals) > 1:
                    self.stats["conflicts_resolved"] += 1

                logger.info(
                    f"DECISION_RESOLVED: {group_key} → {resolution.decision} "
                    f"(signals={len(signals)})"
                )
            except Exception as e:
                logger.error(
                    f"DECISION_ERROR: {group_key} failed: {e}", exc_info=True
                )
                decisions[group_key] = ConflictResolution(
                    decision="REJECT",
                    winning_signal=None,
                    losing_signals=signals,
                    reason_codes=["ARBITER_ERROR", str(e)],
                    net_direction_weight=0.0,
                    regime_probs={},
                    ev_calculations={},
                    colinearity_matrix=None,
                    metadata={"batch_id": batch_id, "error": str(e)}
                )

        logger.info(
            f"DECISION_TICK_END: tick={self.current_tick} decisions={len(decisions)}"
        )
        return decisions

    def get_stats(self) -> Dict:
        with self.lock:
            return {
                **self.stats,
                "current_buffer_size": sum(len(sigs) for sigs in self.signal_buffer.values()),
                "current_tick": self.current_tick
            }

# Singleton
_SIGNAL_BUS_INSTANCE: Optional[SignalBus] = None

def get_signal_bus(arbiter: Optional[ConflictArbiter] = None) -> SignalBus:
    """Obtiene instancia global del Signal Bus."""
    global _SIGNAL_BUS_INSTANCE
    if _SIGNAL_BUS_INSTANCE is None:
        if arbiter is None:
            raise ValueError("Signal Bus requiere Conflict Arbiter en primera inicialización")
        _SIGNAL_BUS_INSTANCE = SignalBus(arbiter)
    return _SIGNAL_BUS_INSTANCE
