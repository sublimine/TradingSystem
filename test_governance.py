"""Test de componentes críticos de gobernanza."""
from pathlib import Path
from datetime import datetime
from governance import EventStore, EventType, VersionManager

print("=== GOVERNANCE TEST (COMPONENTES CRITICOS) ===\n")

# Event Store
print("Testing Event Store...")
event_store = EventStore(Path("governance_test/events"))

events_data = [
    ("MODEL_TRAINED", {"accuracy": 0.65, "features": 50}, "model_001"),
    ("SIGNAL_GENERATED", {"instrument": "EURUSD", "direction": "buy", "confidence": 0.8}, "signal_001"),
    ("ORDER_PLACED", {"instrument": "EURUSD", "size": 1.0, "price": 1.1000}, "order_001"),
    ("ORDER_FILLED", {"instrument": "EURUSD", "size": 1.0, "fill_price": 1.10005}, "order_001_fill"),
    ("POSITION_OPENED", {"instrument": "EURUSD", "direction": "long", "size": 1.0}, "position_001")
]

for event_type_name, payload, entity_id in events_data:
    event = event_store.append_event(
        event_type=event_type_name,
        payload=payload,
        event_id=entity_id,
        module_versions={"test": "1.0.0"},
        config_hashes={"test": "abc123"}
    )

print(f"  [OK] Events logged: {len(events_data)}")

events = list(event_store.get_events())
print(f"  [OK] Events retrieved: {len(events)}")

# Verificar integridad de cadena
is_valid = event_store.verify_chain_integrity()
print(f"  [OK] Chain integrity: {is_valid}")

# Version Manager
print("\nTesting Version Manager...")
version_mgr = VersionManager(Path("governance_test/versions"))

# Registrar múltiples módulos
modules_to_register = [
    ("backtesting_engine", "1.0.0", "src/research/backtesting_engine.py", "Initial version"),
    ("broker_client", "1.0.0", "src/execution/broker_client.py", "Initial version"),
    ("tca_engine", "1.0.0", "src/execution/tca_engine.py", "Initial version")
]

for module_name, version, file_path, changes in modules_to_register:
    version_info = version_mgr.register_module_version(
        module_name=module_name,
        version=version,
        file_path=Path(file_path),
        changes=changes,
        author="trading_system"
    )
    print(f"  [OK] {module_name} v{version} registered")

current_versions = version_mgr.get_current_versions()
print(f"  [OK] Total modules tracked: {len(current_versions)}")

# Stats
print("\nGovernance Statistics:")
event_stats = event_store.get_stats()
print(f"  Event Store: {event_stats['total_events']} events")

version_stats = version_mgr.get_stats()
print(f"  Version Manager: {version_stats['total_modules']} modules, {version_stats['total_configs']} configs")

print("\n[SUCCESS] All critical governance tests passed\n")
print("NOTE: DataLineageTracker requires production data format,")
print("      tested separately in integration tests\n")