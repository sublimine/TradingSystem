"""
Tests unitarios CORRECTOS para technical_indicators.py
Basados en API real verificada
"""
import sys
sys.path.insert(0, "C:/TradingSystem/src/features")
import pandas as pd
import numpy as np
from technical_indicators import (
    calculate_rsi, calculate_bollinger_bands, calculate_atr,
    calculate_macd, identify_swing_points
)

def test_rsi_bounds():
    """RSI debe estar entre 0 y 100"""
    prices = pd.Series([44, 44.5, 45, 44.8, 45.2, 45.5, 45.3, 45.6, 45.4, 45.8,
                       46, 45.9, 46.2, 46.1, 46.3] * 3)
    rsi = calculate_rsi(prices, period=14)
    
    assert rsi is not None, "RSI retorno None"
    assert len(rsi) == len(prices), f"Longitud incorrecta: {len(rsi)} vs {len(prices)}"
    
    valid = rsi.dropna()
    assert all(valid >= 0), f"RSI negativo encontrado: {valid.min()}"
    assert all(valid <= 100), f"RSI > 100 encontrado: {valid.max()}"
    
    print(f"  OK RSI: {len(valid)} valores validos, rango [{valid.min():.2f}, {valid.max():.2f}]")

def test_bollinger_bands():
    """Bollinger Bands: upper >= middle >= lower"""
    prices = pd.Series(np.random.randn(100).cumsum() + 100)
    upper, middle, lower = calculate_bollinger_bands(prices, period=20, num_std=2.0)
    
    assert len(upper) == len(prices), "Upper banda longitud incorrecta"
    assert len(middle) == len(prices), "Middle banda longitud incorrecta"
    assert len(lower) == len(prices), "Lower banda longitud incorrecta"
    
    valid_idx = ~middle.isna()
    violations_upper = (upper[valid_idx] < middle[valid_idx]).sum()
    violations_lower = (middle[valid_idx] < lower[valid_idx]).sum()
    
    assert violations_upper == 0, f"Upper < Middle en {violations_upper} puntos"
    assert violations_lower == 0, f"Middle < Lower en {violations_lower} puntos"
    
    print(f"  OK Bollinger Bands: {valid_idx.sum()} puntos validos, orden correcto")

def test_atr_positive():
    """ATR debe ser siempre positivo o cero"""
    high = pd.Series([101, 102, 103, 102, 104, 105, 104, 106, 107, 106] * 3)
    low = pd.Series([99, 100, 101, 100, 102, 103, 102, 104, 105, 104] * 3)
    close = pd.Series([100, 101, 102, 101, 103, 104, 103, 105, 106, 105] * 3)
    
    atr = calculate_atr(high, low, close, period=14)
    
    assert atr is not None, "ATR retorno None"
    valid = atr.dropna()
    negatives = (valid < 0).sum()
    assert negatives == 0, f"ATR negativo en {negatives} puntos"
    
    print(f"  OK ATR: {len(valid)} valores positivos, rango [{valid.min():.4f}, {valid.max():.4f}]")

def test_macd_consistency():
    """MACD: histogram debe ser macd - signal"""
    prices = pd.Series(np.random.randn(100).cumsum() + 100)
    macd, signal, histogram = calculate_macd(prices)
    
    assert len(macd) == len(prices), "MACD longitud incorrecta"
    assert len(signal) == len(prices), "Signal longitud incorrecta"
    assert len(histogram) == len(prices), "Histogram longitud incorrecta"
    
    valid_idx = ~macd.isna() & ~signal.isna() & ~histogram.isna()
    computed_hist = macd[valid_idx] - signal[valid_idx]
    diff = (computed_hist - histogram[valid_idx]).abs()
    max_error = diff.max()
    
    assert max_error < 1e-10, f"Histogram != MACD - Signal, error max: {max_error}"
    
    print(f"  OK MACD: {valid_idx.sum()} puntos validos, histogram consistente")

def test_swing_points_detection():
    """identify_swing_points con parametro 'order' correcto"""
    # Crear serie con swing points obvios
    prices = pd.Series([100, 102, 105, 103, 101,  # swing high en 105
                       99, 97, 99, 101, 103])     # swing low en 97
    
    swing_highs, swing_lows = identify_swing_points(prices, order=2)
    
    assert isinstance(swing_highs, pd.Series), "swing_highs no es Series"
    assert isinstance(swing_lows, pd.Series), "swing_lows no es Series"
    assert len(swing_highs) == len(prices), "swing_highs longitud incorrecta"
    assert len(swing_lows) == len(prices), "swing_lows longitud incorrecta"
    
    # Verificar que son booleanos
    assert swing_highs.dtype == bool, "swing_highs no es booleano"
    assert swing_lows.dtype == bool, "swing_lows no es booleano"
    
    # Debe detectar al menos 1 swing high en posicion 2 (105)
    assert swing_highs.iloc[2] == True, f"No detecto swing high obvio en posicion 2"
    
    print(f"  OK Swing Points: {swing_highs.sum()} highs, {swing_lows.sum()} lows detectados")

if __name__ == "__main__":
    print("\n" + "="*70)
    print("TESTS UNITARIOS: TECHNICAL INDICATORS")
    print("="*70 + "\n")
    
    tests_run = 0
    tests_passed = 0
    
    for test_func in [test_rsi_bounds, test_bollinger_bands, test_atr_positive,
                     test_macd_consistency, test_swing_points_detection]:
        tests_run += 1
        try:
            test_func()
            tests_passed += 1
        except AssertionError as e:
            print(f"  FAIL {test_func.__name__}: {e}")
        except Exception as e:
            print(f"  ERROR {test_func.__name__}: {e}")
    
    print("\n" + "="*70)
    print(f"RESULTADO: {tests_passed}/{tests_run} tests pasados")
    print("="*70)
    
    exit(0 if tests_passed == tests_run else 1)
