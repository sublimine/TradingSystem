"""Decision Ledger - Idempotencia con firma flexible."""
from __future__ import annotations

import json
import logging
import threading  # P1-012: Agregar threading para locks
import uuid
from typing import Dict, Optional, Tuple
from datetime import datetime
from collections import OrderedDict

logger = logging.getLogger(__name__)

class DecisionLedger:
    """
    Ledger de decisiones con LRU y soporte de idempotencia.
    Firma flexible:
      - write(uid, payload)               # compat anterior
      - write(uid, ulid_temporal, payload)  # versión extendida
    """
    # P1-025: Aumentar max_size a 100k para evitar memory leak en producción HF
    def __init__(self, max_size: int = 100000):
        # P1-012: Lock para thread-safety
        self.lock = threading.RLock()
        self.decisions: OrderedDict[str, Dict] = OrderedDict()
        self.max_size = max_size
        self.stats = {"total_decisions": 0, "duplicates_prevented": 0}

    def exists(self, decision_uid: str) -> bool:
        return decision_uid in self.decisions

    def write(self, decision_uid: str, *args) -> bool:
        """
        Acepta:
          write(uid, payload_dict)
          write(uid, ulid_temporal_str, payload_dict)
        """
        if len(args) == 1:
            payload = args[0]
            ulid_temporal = None
        elif len(args) == 2:
            ulid_temporal, payload = args
        else:
            raise TypeError("DecisionLedger.write espera (uid, payload) o (uid, ulid_temporal, payload)")

        if not isinstance(payload, dict):
            raise TypeError("payload debe ser dict serializable")

        # P1-012: Proteger acceso con lock
        with self.lock:
            if self.exists(decision_uid):
                logger.warning(f"DUPLICATE_DECISION: {decision_uid} ya existe")
                self.stats["duplicates_prevented"] += 1
                return False

            record = {
                "timestamp": datetime.now().isoformat(),
                "ulid_temporal": ulid_temporal,
                "payload": payload
            }
            self.decisions[decision_uid] = record

            if len(self.decisions) > self.max_size:
                self.decisions.popitem(last=False)

            self.stats["total_decisions"] += 1
            logger.debug(f"LEDGER_WRITE: {decision_uid}")
            return True

    def get(self, decision_uid: str) -> Optional[Dict]:
        return self.decisions.get(decision_uid)

    def generate_decision_uid(
        self,
        batch_id: str,
        signal_id: str,
        instrument: str,
        horizon: str
    ) -> Tuple[str, str]:
        """
        Genera UIDs únicos para una decisión.

        Genera dos identificadores:
        - UUID5: Determinístico basado en parámetros (idempotencia)
        - ULID temporal: Timestamp-based para ordenación

        Args:
            batch_id: ID del batch de decisiones
            signal_id: ID de la señal winning
            instrument: Instrumento (ej: 'EURUSD')
            horizon: Horizonte temporal (ej: 'M15')

        Returns:
            Tuple (uuid5_str, ulid_temporal_str)
        """
        # Construir key determinística
        decision_key = f"{batch_id}:{signal_id}:{instrument}:{horizon}"

        # UUID5 determinístico (idempotente)
        uuid5_str = str(uuid.uuid5(uuid.NAMESPACE_DNS, decision_key))

        # ULID temporal para ordenación
        ulid_temporal = f"ULID_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}"

        return uuid5_str, ulid_temporal

    def add_execution_metadata(
        self,
        decision_id: str,
        mid_at_send: float,
        mid_at_fill: Optional[float] = None,
        hold_ms: Optional[int] = None,
        fill_prob_model_version: Optional[str] = None,
        lp_name: Optional[str] = None,
        reject_reason: Optional[str] = None
    ):
        """
        Añade metadata detallada de ejecución a una decisión.

        Esta metadata es crítica para TCA (Transaction Cost Analysis)
        y para entrenar modelos de fill probability y venue selection.

        Args:
            decision_id: ID de la decisión
            mid_at_send: Mid price en el momento de enviar la orden
            mid_at_fill: Mid price en el momento del fill (None si rechazada)
            hold_ms: Hold time en milisegundos (latencia desde send hasta fill)
            fill_prob_model_version: Versión del modelo que predijo fill probability
            lp_name: Nombre del LP/venue usado
            reject_reason: Razón de rechazo si la orden no se llenó
        """
        # P1-011: Iterar sobre items() no keys(). decisions es OrderedDict[str, Dict]
        for uid, decision_data in self.decisions.items():
            if decision_data['payload'].get('decision_id') == decision_id:
                execution_meta = {
                    'mid_at_send': mid_at_send,
                    'mid_at_fill': mid_at_fill,
                    'hold_ms': hold_ms,
                    'fill_prob_model_version': fill_prob_model_version,
                    'lp_name': lp_name,
                    'reject_reason': reject_reason,
                    'timestamp_added': datetime.now().isoformat()
                }
                decision_data['execution_metadata'] = execution_meta
                logger.debug(f"METADATA_ADDED: {decision_id} -> {uid}")
                break

    def export_to_json(self, filepath: str):
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(dict(self.decisions), f, indent=2, ensure_ascii=False)
        logger.info(f"Ledger exportado a {filepath}")

# Instancia global
DECISION_LEDGER = DecisionLedger()

