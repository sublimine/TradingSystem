"""
Unit tests for microstructure features module
"""

import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent / 'src' / 'features'))

import microstructure as ms
import numpy as np


def test_microprice():
    """Test microprice calculation."""
    bid, ask = 1.1000, 1.1002
    bid_vol, ask_vol = 100000, 50000
    
    result = ms.calculate_microprice(bid, ask, bid_vol, ask_vol)
    
    expected = (1.1002 * 100000 + 1.1000 * 50000) / 150000
    
    assert abs(result - expected) < 1e-10, f"Expected {expected}, got {result}"
    print(f"✓ Microprice test passed: {result:.6f}")


def test_spread():
    """Test spread calculation."""
    bid, ask = 1.1000, 1.1002
    
    spread_abs = ms.calculate_spread(bid, ask, in_percentage=False)
    assert abs(spread_abs - 0.0002) < 1e-10
    
    spread_pct = ms.calculate_spread(bid, ask, in_percentage=True)
    expected_pct = (0.0002 / 1.1001) * 100
    assert abs(spread_pct - expected_pct) < 1e-6
    
    print(f"✓ Spread test passed: {spread_abs:.6f} ({spread_pct:.4f}%)")


def test_order_book_imbalance():
    """Test order book imbalance calculation."""
    bid_vol, ask_vol = 100000, 50000
    
    result = ms.calculate_order_book_imbalance(bid_vol, ask_vol)
    
    expected = (100000 - 50000) / (100000 + 50000)
    
    assert abs(result - expected) < 1e-10
    print(f"✓ Order book imbalance test passed: {result:.4f}")


def test_trade_classification():
    """Test trade direction classification."""
    bid, ask = 1.1000, 1.1002
    mid = 1.1001
    
    buy_trade = ms.classify_trade_direction(1.10015, 1.10010, bid, ask)
    assert buy_trade == 1, "Trade above mid should be buy"
    
    sell_trade = ms.classify_trade_direction(1.10005, 1.10010, bid, ask)
    assert sell_trade == -1, "Trade below mid should be sell"
    
    print("✓ Trade classification test passed")


def test_roll_measure():
    """Test Roll's measure calculation."""
    import pandas as pd
    
    prices = pd.Series([1.1000, 1.1002, 1.1001, 1.1003, 1.1002, 1.1004])
    
    result = ms.calculate_roll_measure(prices)
    
    assert result >= 0, "Roll measure should be non-negative"
    print(f"✓ Roll measure test passed: {result:.6f}")


if __name__ == "__main__":
    print("Running microstructure module tests...\n")
    
    test_microprice()
    test_spread()
    test_order_book_imbalance()
    test_trade_classification()
    test_roll_measure()
    
    print("\n✓ All microstructure tests passed successfully!")