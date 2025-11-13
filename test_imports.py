# Test funcional de componentes de gobernanza
import sys
from pathlib import Path

try:
    # Test 1: ID Generation
    from governance.id_generation import generate_batch_id, generate_uuidv7
    batch_id = generate_batch_id(42)
    uuid = generate_uuidv7()
    print(f"✓ ID Generation OK - batch_id={batch_id}, uuid={uuid[:20]}...")
    
    # Test 2: EventStore (sin escribir archivos)
    from governance.event_store import EventStore, Event
    print("✓ EventStore import OK")
    
    # Test 3: VersionManager
    from governance.version_manager import VersionManager
    print("✓ VersionManager import OK")
    
    # Test 4: ModelRegistry
    from governance.model_registry import ModelRegistry, ModelStatus
    print("✓ ModelRegistry import OK")
    
    # Test 5: FactorLimits
    from risk.factor_limits import FactorLimitsManager
    print("✓ FactorLimitsManager import OK")
    
    print("\n✓ TODOS LOS TESTS FUNCIONALES PASARON")
    sys.exit(0)
    
except Exception as e:
    print(f"\n✗ ERROR: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
