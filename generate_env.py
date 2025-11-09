import sys
import json
import platform
from datetime import datetime

try:
    import MetaTrader5 as mt5
    mt5_version = mt5.__version__ if hasattr(mt5, '__version__') else 'installed'
except:
    mt5_version = 'not_installed'

try:
    import pandas as pd
    pandas_version = pd.__version__
except:
    pandas_version = 'not_installed'

try:
    import numpy as np
    numpy_version = np.__version__
except:
    numpy_version = 'not_installed'

env_snapshot = {
    'timestamp': datetime.now().isoformat(),
    'python_version': sys.version,
    'platform': platform.platform(),
    'os': platform.system(),
    'timezone': 'Europe/Zurich',
    'libraries': {
        'MetaTrader5': mt5_version,
        'pandas': pandas_version,
        'numpy': numpy_version
    }
}

with open('C:\TradingSystem\checkpoint_CANONICO_20251105\checkpoint_CANONICO_2025-11-05T20251105_140501_ZRH/ENV_SNAPSHOT.json', 'w') as f:
    json.dump(env_snapshot, f, indent=2)

print('ENV_SNAPSHOT generado')
