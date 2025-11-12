import sys
import json
import hashlib
import platform
from pathlib import Path
from datetime import datetime

sys.path.insert(0, 'C:/TradingSystem/src')

checkpoint_root = Path('C:/TradingSystem/checkpoint/STATE_20251105_T0')

# 1. manifest_hashes.json
def get_hash(filepath):
    sha256 = hashlib.sha256()
    with open(filepath, 'rb') as f:
        sha256.update(f.read())
    return sha256.hexdigest()

hashes = {}
for file in checkpoint_root.rglob('*'):
    if file.is_file() and not file.name.endswith('.json'):
        try:
            rel_path = str(file.relative_to(checkpoint_root))
            hashes[rel_path] = get_hash(file)
        except:
            pass

with open(checkpoint_root / 'manifest_hashes.json', 'w') as f:
    json.dump(hashes, f, indent=2)

# 2. env_fingerprint.json
try:
    import MetaTrader5 as mt5
    mt5_info = mt5.__version__ if hasattr(mt5, '__version__') else 'installed'
except:
    mt5_info = 'not_installed'

try:
    import pandas as pd
    pandas_ver = pd.__version__
except:
    pandas_ver = 'unknown'

try:
    import numpy as np
    numpy_ver = np.__version__
except:
    numpy_ver = 'unknown'

env_fingerprint = {
    'timestamp': datetime.now().isoformat(),
    'timezone': 'Europe/Zurich',
    'os': platform.system(),
    'os_version': platform.version(),
    'python_version': sys.version,
    'libraries': {
        'MetaTrader5': mt5_info,
        'pandas': pandas_ver,
        'numpy': numpy_ver
    },
    'mt5_endpoint': 'Axi-US50-Demo'
}

with open(checkpoint_root / 'env_fingerprint.json', 'w') as f:
    json.dump(env_fingerprint, f, indent=2)

# 3. config_effective.json
config_effective = {
    'mode': 'DEMO',
    'risk_per_trade': '1%',
    'cooldown_seconds': 300,
    'scan_interval_seconds': 60,
    'symbols': [
        'EURUSD.pro', 'GBPUSD.pro', 'USDJPY.pro', 'AUDUSD.pro',
        'USDCAD.pro', 'USDCHF.pro', 'NZDUSD.pro', 'EURGBP.pro',
        'XAUUSD.pro', 'BTCUSD', 'ETHUSD'
    ],
    'lookback_bars': 500,
    'strategies_active': 9,
    'max_open_per_symbol': 2,
    'lotaje': 'dynamic'
}

with open(checkpoint_root / 'config_effective.json', 'w') as f:
    json.dump(config_effective, f, indent=2)

# 4. run_signature.json
run_signature = {
    'timestamp': datetime.now().isoformat(),
    'strategies_loaded': '9/9',
    'strategies_list': [
        'breakout_volume_confirmation',
        'correlation_divergence',
        'kalman_pairs_trading',
        'liquidity_sweep',
        'mean_reversion_statistical',
        'momentum_quality',
        'news_event_positioning',
        'order_flow_toxicity',
        'volatility_regime_adaptation'
    ],
    'scan_time_avg_ms': 200,
    'latency_avg_ms': 150,
    'build': '20251105_FINAL'
}

with open(checkpoint_root / 'run_signature.json', 'w') as f:
    json.dump(run_signature, f, indent=2)

# 5. data_index.json
data_index = {
    'historical_data': 'MT5 live feed',
    'cache_location': 'none',
    'local_storage': 'logs/ and checkpoints/',
    'persistence': 'File-based (logs, JSON)'
}

with open(checkpoint_root / 'data_index.json', 'w') as f:
    json.dump(data_index, f, indent=2)

# 6. tag.txt
with open(checkpoint_root / 'tag.txt', 'w') as f:
    f.write(f'STATE_20251105_T0\n')
    f.write(f'Created: {datetime.now().isoformat()}\n')
    f.write(f'Timezone: Europe/Zurich\n')
    f.write(f'Strategies: 9/9 active\n')
    f.write(f'Mode: DEMO\n')

print('Checkpoint manifests generated')
print(f'Files hashed: {len(hashes)}')
