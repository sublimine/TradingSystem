"""
Tests críticos para DecisionLedger
Mandato 6 - Testing P0
"""
import pytest
from src.core.decision_ledger import DecisionLedger


def test_decision_ledger_idempotencia():
    """Test P0: Ledger previene duplicados (idempotencia)."""
    ledger = DecisionLedger(max_size=100)

    # Primera escritura debe exitosa
    uid = "test_decision_001"
    payload = {"signal_id": "S001", "action": "LONG", "instrument": "EURUSD"}

    assert ledger.write(uid, payload) is True
    assert ledger.exists(uid) is True

    # Segunda escritura mismo UID debe rechazarse
    assert ledger.write(uid, payload) is False
    assert ledger.stats["duplicates_prevented"] == 1


def test_decision_ledger_lru_eviction():
    """Test P0: Ledger respeta límite max_size (LRU eviction)."""
    ledger = DecisionLedger(max_size=3)

    # Llenar ledger
    for i in range(5):
        uid = f"decision_{i:03d}"
        payload = {"index": i}
        ledger.write(uid, payload)

    # Solo últimos 3 deben existir
    assert ledger.exists("decision_000") is False  # Evicted
    assert ledger.exists("decision_001") is False  # Evicted
    assert ledger.exists("decision_002") is True
    assert ledger.exists("decision_003") is True
    assert ledger.exists("decision_004") is True
    assert len(ledger.decisions) == 3


def test_decision_ledger_generate_uid():
    """Test P0: UIDs generados son determinísticos (idempotencia)."""
    ledger = DecisionLedger()

    # Mismos params → mismo UUID5
    uid1, ulid1 = ledger.generate_decision_uid("B001", "S001", "EURUSD", "M15")
    uid2, ulid2 = ledger.generate_decision_uid("B001", "S001", "EURUSD", "M15")

    assert uid1 == uid2, "UUID5 debe ser determinístico"
    # ULIDs serán diferentes (timestamp-based)
    assert ulid1 != ulid2, "ULIDs temporales deben diferir"


def test_decision_ledger_thread_safety():
    """Test P0: Ledger es thread-safe (lock funciona)."""
    import threading

    ledger = DecisionLedger(max_size=1000)
    errors = []

    def write_batch(start_idx):
        try:
            for i in range(start_idx, start_idx + 100):
                uid = f"concurrent_{i:04d}"
                payload = {"thread": start_idx, "index": i}
                ledger.write(uid, payload)
        except Exception as e:
            errors.append(e)

    # 5 threads escribiendo concurrentemente
    threads = []
    for t in range(5):
        thread = threading.Thread(target=write_batch, args=(t * 100,))
        threads.append(thread)
        thread.start()

    for thread in threads:
        thread.join()

    assert len(errors) == 0, f"No debe haber errores de concurrencia: {errors}"
    assert ledger.stats["total_decisions"] == 500, "Debe tener 500 decisiones únicas"
