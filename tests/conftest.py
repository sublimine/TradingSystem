import os, sys, importlib

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
SRC  = os.path.join(ROOT, "src")
if SRC not in sys.path: sys.path.insert(0, SRC)
if ROOT not in sys.path: sys.path.insert(0, ROOT)

# Alias para imports absolutos legacy dentro de src/*
_ALIASES = {
    "strategies": "src.strategies",
    "risk_management": "src.risk_management",
    "structured_logging": "src.structured_logging",
    "mt5_connector": "src.mt5_connector",
    "signal_generator": "src.signal_generator",
    "features": "src.features",
}

for name, target in _ALIASES.items():
    try:
        sys.modules.setdefault(name, importlib.import_module(target))
    except Exception:
        pass
