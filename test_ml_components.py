"""Test de componentes ML."""
import pandas as pd
import numpy as np
from research import triple_barrier_label, PurgedKFold

print("=== ML COMPONENTS TEST ===\n")

# Cargar datos
df = pd.read_csv(
    "backtest/datasets/EURUSD_pro_synthetic.csv",
    parse_dates=['timestamp'],
    index_col='timestamp'
)

print(f"Data: {len(df)} bars\n")

# Triple barrier labeling
print("Applying triple barrier labeling...")
labels = triple_barrier_label(
    prices=df['close'],
    upper_threshold=0.002,  # 0.2% gain
    lower_threshold=-0.001,  # 0.1% loss
    max_holding_bars=60
)

print(f"Labels generated: {len(labels)}")
print(f"  Winners: {(labels['label'] == 1).sum()}")
print(f"  Losers: {(labels['label'] == -1).sum()}")
print(f"  Neutral: {(labels['label'] == 0).sum()}")
print(f"  Avg holding: {labels['holding_bars'].mean():.1f} bars")

# Guardar labels
labels.to_csv("labeling/labeled_data/eurusd_labels.csv")
print(f"  Saved to labeling/labeled_data/\n")

# Purged K-Fold
print("Testing Purged K-Fold CV...")

# Crear features dummy
X = df[['open', 'high', 'low', 'close', 'volume']].iloc[:len(labels)]
X.index = labels.index
y = labels['label']

pkf = PurgedKFold(n_splits=5, purge_pct=0.01, embargo_pct=0.01)

fold_sizes = []
for fold, (train_idx, test_idx) in enumerate(pkf.split(X, y)):
    fold_sizes.append({
        'fold': fold + 1,
        'train': len(train_idx),
        'test': len(test_idx)
    })

print(f"Generated {len(fold_sizes)} folds:")
for fs in fold_sizes:
    print(f"  Fold {fs['fold']}: train={fs['train']}, test={fs['test']}")

print("\n✓ ML components test complete\n")