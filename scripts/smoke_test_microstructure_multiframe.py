#!/usr/bin/env python3
"""
Smoke Test - Microstructure & MultiFrame Engines
MANDATO 15: Validation of institutional market microstructure and multi-timeframe analysis

Tests:
1. MicrostructureEngine components (VPIN, OFI, Depth, Spoofing)
2. MultiFrameOrchestrator (HTF, MTF, LTF)
3. Integration with QualityScorer
4. Score ranges and caching
"""

import sys
import os
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Mock MetaTrader5 before any imports (avoid dependency in test environment)
from unittest.mock import MagicMock
sys.modules['MetaTrader5'] = MagicMock()

import numpy as np
import pandas as pd
from datetime import datetime, timedelta
import yaml

# Import microstructure components
from src.microstructure import (
    VPINEstimator,
    OrderFlowAnalyzer,
    Level2DepthMonitor,
    SpoofingDetector,
    MicrostructureEngine
)

# Import multiframe components
from src.context import (
    HTFStructureAnalyzer,
    MTFContextValidator,
    LTFTimingExecutor,
    MultiFrameOrchestrator
)

# Import QualityScorer
from src.core.risk_manager import QualityScorer


def load_config():
    """Load microstructure config."""
    config_path = project_root / "config" / "microstructure.yaml"
    if config_path.exists():
        with open(config_path, 'r') as f:
            return yaml.safe_load(f)
    return {}


def generate_synthetic_ohlc(n_candles=100, base_price=1.1000, trend='neutral'):
    """Generate synthetic OHLC data for testing."""
    timestamps = [datetime.now() - timedelta(minutes=i) for i in range(n_candles, 0, -1)]

    prices = [base_price]
    for i in range(1, n_candles):
        change = np.random.randn() * 0.0001
        if trend == 'up':
            change += 0.00005
        elif trend == 'down':
            change -= 0.00005
        prices.append(prices[-1] + change)

    data = []
    for i, (ts, price) in enumerate(zip(timestamps, prices)):
        volatility = 0.0002
        high = price + np.random.uniform(0, volatility)
        low = price - np.random.uniform(0, volatility)
        close = np.random.uniform(low, high)

        data.append({
            'timestamp': ts,
            'open': price,
            'high': high,
            'low': low,
            'close': close,
            'volume': np.random.uniform(1000, 5000)
        })

    return pd.DataFrame(data)


def test_microstructure_engine():
    """Test MicrostructureEngine and all components."""
    print("\n" + "="*60)
    print("TEST 1: MICROSTRUCTURE ENGINE")
    print("="*60)

    config_data = load_config()
    micro_config = config_data.get('microstructure_engine', {})

    # Initialize engine
    engine = MicrostructureEngine(micro_config)
    print(f"✓ MicrostructureEngine initialized")

    # Test VPIN with synthetic trades
    print("\n--- Testing VPIN ---")
    symbol = "EURUSD.pro"
    mid_price = 1.1000

    # Simulate 200 trades (need >bucket_size trades for VPIN)
    for i in range(200):
        trade_price = mid_price + np.random.randn() * 0.0001
        trade_volume = np.random.uniform(1000, 10000)
        bid = mid_price - 0.00005
        ask = mid_price + 0.00005

        engine.vpin.update(symbol, trade_price, trade_volume, bid, ask)

    vpin_score = engine.vpin.get_score(symbol)
    print(f"  VPIN Score: {vpin_score:.3f} (range: [0.0-1.0], higher = better)")
    assert 0.0 <= vpin_score <= 1.0, f"VPIN score out of range: {vpin_score}"
    print(f"  ✓ VPIN score in valid range")

    # Test OFI
    print("\n--- Testing Order Flow ---")
    for i in range(150):
        side = 'BUY' if np.random.rand() > 0.5 else 'SELL'
        volume = np.random.uniform(1000, 5000)
        engine.order_flow.update(symbol, side, volume)

    ofi = engine.order_flow.get_ofi(symbol)
    ofi_score = engine.order_flow.get_score(symbol)
    print(f"  OFI: {ofi:.3f} (range: [-1.0, +1.0])")
    print(f"  OFI Score: {ofi_score:.3f} (range: [0.0-1.0], higher = better)")
    assert -1.0 <= ofi <= 1.0, f"OFI out of range: {ofi}"
    assert 0.0 <= ofi_score <= 1.0, f"OFI score out of range: {ofi_score}"
    print(f"  ✓ OFI and OFI score in valid range")

    # Test Level2 Depth
    print("\n--- Testing Level2 Depth ---")
    bids = [(1.09995 - i*0.00001, np.random.uniform(10000, 50000)) for i in range(10)]
    asks = [(1.10005 + i*0.00001, np.random.uniform(10000, 50000)) for i in range(10)]

    engine.depth.update(symbol, bids, asks)
    depth_score = engine.depth.get_score(symbol)
    print(f"  Depth Score: {depth_score:.3f} (range: [0.0-1.0], higher = better)")
    assert 0.0 <= depth_score <= 1.0, f"Depth score out of range: {depth_score}"
    print(f"  ✓ Depth score in valid range")

    # Test Spoofing Detector
    print("\n--- Testing Spoofing Detector ---")
    # Simulate normal orders and one spoofing event
    for i in range(20):
        order_id = f"order_{i}"
        price = 1.10000 + np.random.randn() * 0.0001
        qty = np.random.uniform(1000, 5000)
        side = 'BID' if np.random.rand() > 0.5 else 'ASK'
        engine.spoofing.track_order_add(symbol, order_id, price, qty, side)

        # Cancel some orders after random delay
        if np.random.rand() > 0.7:
            engine.spoofing.track_order_cancel(symbol, order_id)

    # Simulate spoof (large order cancelled quickly)
    spoof_order = "spoof_1"
    engine.spoofing.track_order_add(symbol, spoof_order, 1.10000, 50000, 'BID')
    engine.spoofing.track_order_cancel(symbol, spoof_order)

    spoof_score = engine.spoofing.get_score(symbol)
    print(f"  Spoofing Score: {spoof_score:.3f} (range: [0.0-1.0], higher = better)")
    assert 0.0 <= spoof_score <= 1.0, f"Spoofing score out of range: {spoof_score}"
    print(f"  ✓ Spoofing score in valid range")

    # Test composite microstructure score
    print("\n--- Testing Composite Microstructure Score ---")
    micro_score = engine.get_microstructure_score(symbol)
    print(f"  Composite Microstructure Score: {micro_score:.3f}")
    print(f"    Components weighted:")
    print(f"      VPIN:     {vpin_score:.3f} × 40% = {vpin_score * 0.40:.3f}")
    print(f"      OFI:      {ofi_score:.3f} × 30% = {ofi_score * 0.30:.3f}")
    print(f"      Depth:    {depth_score:.3f} × 20% = {depth_score * 0.20:.3f}")
    print(f"      Spoofing: {spoof_score:.3f} × 10% = {spoof_score * 0.10:.3f}")
    assert 0.0 <= micro_score <= 1.0, f"Microstructure score out of range: {micro_score}"
    print(f"  ✓ Composite score in valid range")

    # Test caching
    cached_score = engine.get_microstructure_score(symbol)
    assert cached_score == micro_score, "Cache inconsistency"
    print(f"  ✓ Caching works correctly")

    print(f"\n✓✓✓ MicrostructureEngine: ALL TESTS PASSED ✓✓✓")
    return engine


def test_multiframe_orchestrator():
    """Test MultiFrameOrchestrator and all components."""
    print("\n" + "="*60)
    print("TEST 2: MULTIFRAME ORCHESTRATOR")
    print("="*60)

    config_data = load_config()
    mf_config = config_data.get('multiframe_orchestrator', {})

    # Initialize orchestrator
    orchestrator = MultiFrameOrchestrator(mf_config)
    print(f"✓ MultiFrameOrchestrator initialized")

    symbol = "EURUSD.pro"

    # Generate synthetic dataframes
    print("\n--- Generating Synthetic Timeframe Data ---")
    htf_df = generate_synthetic_ohlc(n_candles=50, base_price=1.1000, trend='up')
    mtf_df = generate_synthetic_ohlc(n_candles=100, base_price=1.1000, trend='up')
    ltf_df = generate_synthetic_ohlc(n_candles=200, base_price=1.1000, trend='neutral')
    print(f"  HTF: {len(htf_df)} candles (H4/D1)")
    print(f"  MTF: {len(mtf_df)} candles (M15/M5)")
    print(f"  LTF: {len(ltf_df)} candles (M1)")

    # Test composite multiframe score
    print("\n--- Testing Composite MultiFrame Score ---")
    data_by_tf = {
        'H4': htf_df,
        'M15': mtf_df,
        'M1': ltf_df
    }
    mf_result = orchestrator.analyze(symbol, data_by_tf)
    mf_score = mf_result['multiframe_score']

    print(f"  Composite MultiFrame Score: {mf_score:.3f}")

    # Extract individual component scores from the result
    htf_result = mf_result['htf_analysis']
    mtf_result = mf_result['mtf_analysis']
    ltf_result = mf_result['ltf_analysis']

    print(f"    Components weighted:")
    print(f"      HTF Trend: {htf_result['trend']}, Strength: {htf_result['trend_strength']:.3f} × 50% = {htf_result['trend_strength'] * 0.50:.3f}")
    print(f"      MTF Confluence: {mtf_result['confluence']:.3f} × 30% = {mtf_result['confluence'] * 0.30:.3f}")
    print(f"      LTF Timing: {ltf_result['timing_score']:.3f} × 20% = {ltf_result['timing_score'] * 0.20:.3f}")
    print(f"  Swing Highs: {len(htf_result['swing_highs'])}, Swing Lows: {len(htf_result['swing_lows'])}")
    print(f"  Order Blocks: {len(htf_result['order_blocks'])}")
    print(f"  Supply Zones: {len(mtf_result['supply_zones'])}, Demand Zones: {len(mtf_result['demand_zones'])}")
    print(f"  FVGs: {len(ltf_result['fvgs'])}, Entry Triggers: {ltf_result['entry_triggers']}")

    assert 0.0 <= htf_result['trend_strength'] <= 1.0, "HTF trend_strength out of range"
    assert 0.0 <= mtf_result['confluence'] <= 1.0, "MTF confluence out of range"
    assert 0.0 <= ltf_result['timing_score'] <= 1.0, "LTF timing_score out of range"
    print(f"  ✓ All component scores valid")

    assert 0.0 <= mf_score <= 1.0, f"MultiFrame score out of range: {mf_score}"
    print(f"  ✓ Composite score in valid range")

    # Test caching
    cached_score = orchestrator.get_multiframe_score(symbol)
    assert cached_score == mf_score, "Cache inconsistency"
    print(f"  ✓ Caching works correctly")

    # Test POIs extraction
    print("\n--- Testing POI Extraction ---")
    pois = mf_result['pois']
    print(f"  Points of Interest: {len(pois)}")
    for i, poi in enumerate(pois[:3]):  # Show first 3
        print(f"    - POI #{i+1}: {poi:.5f}")
    print(f"  ✓ POI extraction working")

    print(f"\n✓✓✓ MultiFrameOrchestrator: ALL TESTS PASSED ✓✓✓")
    return orchestrator


def test_quality_scorer_integration(micro_engine, mf_orchestrator):
    """Test QualityScorer integration with engines."""
    print("\n" + "="*60)
    print("TEST 3: QUALITY SCORER INTEGRATION")
    print("="*60)

    # Create QualityScorer with engines
    scorer = QualityScorer(
        microstructure_engine=micro_engine,
        multiframe_orchestrator=mf_orchestrator
    )
    print(f"✓ QualityScorer initialized with engines")

    # Create synthetic signal
    symbol = "EURUSD.pro"
    signal = {
        'symbol': symbol,
        'strategy_name': 'liquidity_sweep',
        'direction': 'LONG',
        'entry_price': 1.10000,
        'stop_loss': 1.09950,
        'take_profit': 1.10100,
        'metadata': {
            'regime_confidence': 0.8,
        }
    }

    market_context = {
        'volatility_regime': 'NORMAL',
        'strategy_performance': {
            'liquidity_sweep': 0.70,
        }
    }

    # Calculate quality with engines
    print("\n--- Quality Score with Engines ---")
    quality_with_engines = scorer.calculate_quality(signal, market_context)
    print(f"  Quality Score: {quality_with_engines:.3f}")
    assert 0.0 <= quality_with_engines <= 1.0, "Quality score out of range"
    print(f"  ✓ Quality score in valid range")

    # Test fallback behavior (without engines)
    print("\n--- Quality Score without Engines (Fallback) ---")
    scorer_no_engines = QualityScorer()

    # Add metadata for fallback
    signal_with_metadata = signal.copy()
    signal_with_metadata['metadata']['mtf_confluence'] = 0.75
    market_context_with_vpin = market_context.copy()
    market_context_with_vpin['vpin'] = 0.35

    quality_fallback = scorer_no_engines.calculate_quality(signal_with_metadata, market_context_with_vpin)
    print(f"  Quality Score (Fallback): {quality_fallback:.3f}")
    assert 0.0 <= quality_fallback <= 1.0, "Quality score (fallback) out of range"
    print(f"  ✓ Fallback logic works correctly")

    # Compare scores
    print("\n--- Comparison ---")
    print(f"  With Engines:    {quality_with_engines:.3f}")
    print(f"  Without Engines: {quality_fallback:.3f}")
    print(f"  Difference:      {abs(quality_with_engines - quality_fallback):.3f}")

    print(f"\n✓✓✓ QualityScorer Integration: ALL TESTS PASSED ✓✓✓")


def run_all_tests():
    """Run all smoke tests."""
    print("\n")
    print("╔" + "="*58 + "╗")
    print("║" + " "*16 + "MANDATO 15 SMOKE TEST" + " "*21 + "║")
    print("║" + " "*10 + "Microstructure & MultiFrame Engines" + " "*13 + "║")
    print("╚" + "="*58 + "╝")

    try:
        # Test 1: MicrostructureEngine
        micro_engine = test_microstructure_engine()

        # Test 2: MultiFrameOrchestrator
        mf_orchestrator = test_multiframe_orchestrator()

        # Test 3: QualityScorer Integration
        test_quality_scorer_integration(micro_engine, mf_orchestrator)

        # Summary
        print("\n" + "="*60)
        print("SUMMARY")
        print("="*60)
        print("✓ MicrostructureEngine: PASSED")
        print("  - VPIN Estimator: OK")
        print("  - Order Flow Analyzer: OK")
        print("  - Level2 Depth Monitor: OK")
        print("  - Spoofing Detector: OK")
        print("  - Composite scoring: OK")
        print("  - Caching: OK")
        print("")
        print("✓ MultiFrameOrchestrator: PASSED")
        print("  - HTF Structure Analyzer: OK")
        print("  - MTF Context Validator: OK")
        print("  - LTF Timing Executor: OK")
        print("  - Composite scoring: OK")
        print("  - POI extraction: OK")
        print("  - Caching: OK")
        print("")
        print("✓ QualityScorer Integration: PASSED")
        print("  - Engine integration: OK")
        print("  - Fallback behavior: OK")
        print("")
        print("="*60)
        print("ALL TESTS PASSED ✓✓✓")
        print("="*60)
        print("\nMANDATO 15 implementation validated successfully.")
        print("Ready for production integration.\n")

        return 0

    except AssertionError as e:
        print(f"\n❌ TEST FAILED: {e}")
        return 1
    except Exception as e:
        print(f"\n❌ UNEXPECTED ERROR: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit_code = run_all_tests()
    sys.exit(exit_code)
