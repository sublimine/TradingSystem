#!/usr/bin/env python3
"""
MANDATO 17 - Tests Unitarios: calculate_max_drawdown

Valida corrección del bug 'numpy.int64' object has no attribute 'days'.

Escenarios:
1. Equity en tendencia alcista suave (drawdown mínimo)
2. Equity sideways (drawdown moderado)
3. Equity con crash profundo y recuperación parcial (drawdown severo)

Valida:
- Índices DatetimeIndex (timestamps)
- Índices numéricos (posiciones)
- Cálculo correcto de max_dd_pct y max_dd_duration_days
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import pandas as pd
import numpy as np
from datetime import datetime, timedelta

from src.reporting.metrics import calculate_max_drawdown, calculate_drawdown


def test_drawdown_uptrend_datetime():
    """Escenario 1a: Tendencia alcista suave con DatetimeIndex"""
    print("TEST 1a: Uptrend con DatetimeIndex")

    dates = pd.date_range(start='2024-01-01', periods=100, freq='D')
    equity = pd.Series(
        10000 + np.arange(100) * 50 + np.random.normal(0, 20, 100),  # +50/día con ruido
        index=dates
    )
    equity = equity.clip(lower=equity.iloc[0])  # No permitir caída bajo inicial

    result = calculate_max_drawdown(equity)

    print(f"  Max DD: {result['max_dd_pct']:.2f}%")
    print(f"  Duration: {result['max_dd_duration_days']} days")

    # Assertions
    assert result['max_dd_pct'] <= 0, "Uptrend debe tener DD negativo o cero"
    assert result['max_dd_pct'] >= -10, "Uptrend suave no debería tener DD > 10%"
    assert result['max_dd_duration_days'] >= 0, "Duración debe ser no-negativa"
    assert isinstance(result['max_dd_duration_days'], (int, np.integer)), "Duración debe ser int"

    print("  ✓ PASSED\n")


def test_drawdown_uptrend_numeric():
    """Escenario 1b: Tendencia alcista con índice numérico"""
    print("TEST 1b: Uptrend con índice numérico")

    equity = pd.Series(
        10000 + np.arange(100) * 50 + np.random.normal(0, 20, 100),
        index=range(100)
    )
    equity = equity.clip(lower=equity.iloc[0])

    result = calculate_max_drawdown(equity)

    print(f"  Max DD: {result['max_dd_pct']:.2f}%")
    print(f"  Duration: {result['max_dd_duration_days']} periods")

    assert result['max_dd_pct'] <= 0, "Uptrend debe tener DD negativo o cero"
    assert result['max_dd_duration_days'] >= 0, "Duración debe ser no-negativa"
    assert isinstance(result['max_dd_duration_days'], (int, np.integer)), "Duración debe ser int"

    print("  ✓ PASSED\n")


def test_drawdown_sideways_datetime():
    """Escenario 2a: Sideways con drawdown moderado (DatetimeIndex)"""
    print("TEST 2a: Sideways con DatetimeIndex")

    dates = pd.date_range(start='2024-01-01', periods=100, freq='D')
    equity = pd.Series(10000, index=dates)

    # Simular sideways con drawdown moderado
    equity.iloc[20:40] *= 0.95  # -5% DD entre día 20-40
    equity.iloc[40:60] = equity.iloc[40] + np.linspace(0, 500, 20)  # Recuperación parcial
    equity.iloc[60:] = equity.iloc[59] + np.random.normal(0, 50, 40)  # Sideways

    result = calculate_max_drawdown(equity)

    print(f"  Max DD: {result['max_dd_pct']:.2f}%")
    print(f"  Duration: {result['max_dd_duration_days']} days")

    assert result['max_dd_pct'] < 0, "Sideways con drawdown debe tener DD negativo"
    assert result['max_dd_pct'] >= -15, "DD no debería exceder 15% en este escenario"
    assert result['max_dd_duration_days'] > 0, "Debe haber duración de DD"
    assert result['max_dd_duration_days'] <= 100, "Duración no puede exceder total de días"

    print("  ✓ PASSED\n")


def test_drawdown_sideways_numeric():
    """Escenario 2b: Sideways con índice numérico"""
    print("TEST 2b: Sideways con índice numérico")

    equity = pd.Series(10000, index=range(100))
    equity.iloc[20:40] *= 0.95
    equity.iloc[40:60] = equity.iloc[40] + np.linspace(0, 500, 20)
    equity.iloc[60:] = equity.iloc[59] + np.random.normal(0, 50, 40)

    result = calculate_max_drawdown(equity)

    print(f"  Max DD: {result['max_dd_pct']:.2f}%")
    print(f"  Duration: {result['max_dd_duration_days']} periods")

    assert result['max_dd_pct'] < 0, "DD debe ser negativo"
    assert result['max_dd_duration_days'] > 0, "Debe haber duración"
    assert isinstance(result['max_dd_duration_days'], (int, np.integer)), "Duración debe ser int"

    print("  ✓ PASSED\n")


def test_drawdown_crash_datetime():
    """Escenario 3a: Crash profundo con recuperación parcial (DatetimeIndex)"""
    print("TEST 3a: Crash profundo con DatetimeIndex")

    dates = pd.date_range(start='2024-01-01', periods=200, freq='D')
    equity = pd.Series(10000, index=dates)

    # Simular crash: -35% entre día 50-70
    equity.iloc[50:71] = 10000 * (1 - np.linspace(0, 0.35, 21))

    # Recuperación parcial: +20% entre día 71-120
    equity.iloc[71:121] = equity.iloc[70] * (1 + np.linspace(0, 0.20, 50))

    # Sideways post-recuperación
    equity.iloc[121:] = equity.iloc[120] + np.random.normal(0, 50, 79)

    result = calculate_max_drawdown(equity)

    print(f"  Max DD: {result['max_dd_pct']:.2f}%")
    print(f"  Duration: {result['max_dd_duration_days']} days")

    assert result['max_dd_pct'] < -20, "Crash profundo debe tener DD > 20%"
    assert result['max_dd_pct'] >= -50, "DD no debería exceder 50% en este escenario"
    assert result['max_dd_duration_days'] > 20, "Crash debería tener duración significativa"
    assert result['max_dd_duration_days'] <= 200, "Duración no puede exceder total"
    assert isinstance(result['max_dd_duration_days'], (int, np.integer)), "Duración debe ser int"

    print("  ✓ PASSED\n")


def test_drawdown_crash_numeric():
    """Escenario 3b: Crash profundo con índice numérico"""
    print("TEST 3b: Crash profundo con índice numérico")

    equity = pd.Series(10000, index=range(200))
    equity.iloc[50:71] = 10000 * (1 - np.linspace(0, 0.35, 21))
    equity.iloc[71:121] = equity.iloc[70] * (1 + np.linspace(0, 0.20, 50))
    equity.iloc[121:] = equity.iloc[120] + np.random.normal(0, 50, 79)

    result = calculate_max_drawdown(equity)

    print(f"  Max DD: {result['max_dd_pct']:.2f}%")
    print(f"  Duration: {result['max_dd_duration_days']} periods")

    assert result['max_dd_pct'] < -20, "Crash debe tener DD significativo"
    assert result['max_dd_duration_days'] > 20, "Crash debe tener duración larga"
    assert isinstance(result['max_dd_duration_days'], (int, np.integer)), "Duración debe ser int"

    print("  ✓ PASSED\n")


def test_empty_equity():
    """Edge case: Equity curve vacía"""
    print("TEST Edge: Equity vacía")

    equity = pd.Series([], dtype=float)
    result = calculate_max_drawdown(equity)

    assert result['max_dd_pct'] == 0
    assert result['max_dd_duration_days'] == 0

    print("  ✓ PASSED\n")


def main():
    """Ejecutar todos los tests"""
    print("="*60)
    print("MANDATO 17 - Tests Unitarios: calculate_max_drawdown")
    print("="*60)
    print()

    tests = [
        test_drawdown_uptrend_datetime,
        test_drawdown_uptrend_numeric,
        test_drawdown_sideways_datetime,
        test_drawdown_sideways_numeric,
        test_drawdown_crash_datetime,
        test_drawdown_crash_numeric,
        test_empty_equity
    ]

    failed = []

    for test_func in tests:
        try:
            test_func()
        except AssertionError as e:
            print(f"  ✗ FAILED: {e}\n")
            failed.append(test_func.__name__)
        except Exception as e:
            print(f"  ✗ ERROR: {e}\n")
            failed.append(test_func.__name__)

    print("="*60)
    if not failed:
        print("✅ ALL TESTS PASSED")
        print("="*60)
        return 0
    else:
        print(f"❌ {len(failed)} TESTS FAILED:")
        for name in failed:
            print(f"  - {name}")
        print("="*60)
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
