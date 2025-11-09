# Institutional Trading System

Sistema de trading algorítmico de grado institucional con enfoque en:
- Microestructura de mercado
- Order flow analytics
- Gestión de riesgo factorial
- Gobernanza completa con event sourcing
- Reproducibilidad determinística

## Instalación
```bash
# Instalar en modo editable (desarrollo)
pip install -e .

# Con dependencias de desarrollo
pip install -e ".[dev]"

# Con dependencias de optimización
pip install -e ".[optimization]"
```

## Estructura
```
src/
  governance/     - Event sourcing, versioning, auditoría
  risk/          - Gestión de riesgo factorial
  core/          - Componentes core del sistema
  strategies/    - Estrategias de trading
```

## Uso
```python
from governance import EventStore, VersionManager
from risk import FactorLimitsManager

# Inicializar componentes
event_store = EventStore(Path("event_store"))
version_mgr = VersionManager(Path("versions"))
```

## Testing
```bash
pytest tests/ -v
python verify_integrity.py
```
