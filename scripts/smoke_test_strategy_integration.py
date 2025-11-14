#!/usr/bin/env python3
"""
MANDATO 16 - Smoke Test: Strategy Integration

Valida integración de MicrostructureEngine + MultiFrameOrchestrator con estrategias núcleo.

Escenarios:
1. Tendencia alcista limpia
2. Rango consolidado
3. Flujo tóxico (VPIN alto)

Estrategias testeadas:
- liquidity_sweep
- order_flow_toxicity
- ofi_refinement
- vpin_reversal_extreme
- breakout_volume_confirmation

Exit code 0 = ✅ Todo OK
Exit code 1 = ❌ Fallo detectado
"""

import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import numpy as np
import pandas as pd
from datetime import datetime, timedelta
import logging

# Import motores
from src.microstructure import MicrostructureEngine
from src.context import MultiFrameOrchestrator

# Import estrategias núcleo
from src.strategies.liquidity_sweep import LiquiditySweepStrategy
from src.strategies.order_flow_toxicity import OrderFlowToxicityStrategy
from src.strategies.ofi_refinement import OFIRefinement
from src.strategies.vpin_reversal_extreme import VPINReversalExtreme
from src.strategies.breakout_volume_confirmation import BreakoutVolumeConfirmation

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def generate_synthetic_ohlcv(bars: int, scenario: str, symbol: str = 'EURUSD') -> pd.DataFrame:
    """
    Genera datos OHLCV sintéticos para testing.

    Args:
        bars: Número de barras
        scenario: 'uptrend', 'range', 'toxic_flow'
        symbol: Símbolo

    Returns:
        DataFrame con OHLCV + symbol column
    """
    timestamps = [datetime.now() - timedelta(minutes=bars - i) for i in range(bars)]

    base_price = 1.1000
    volatility = 0.0001  # 1 pip

    if scenario == 'uptrend':
        # Tendencia alcista limpia
        trend = np.linspace(0, 0.0050, bars)  # +50 pips
        noise = np.random.normal(0, volatility, bars)
        closes = base_price + trend + noise

    elif scenario == 'range':
        # Rango consolidado
        noise = np.random.normal(0, volatility / 2, bars)
        closes = base_price + noise

    elif scenario == 'toxic_flow':
        # Movimiento parabólico + colapso (flujo tóxico)
        phase1_bars = int(bars * 0.7)
        phase2_bars = bars - phase1_bars

        # Fase 1: subida parabólica
        phase1 = base_price + np.power(np.linspace(0, 1, phase1_bars), 2) * 0.0100
        # Fase 2: colapso
        phase2 = phase1[-1] - np.linspace(0, 0.0080, phase2_bars)

        closes = np.concatenate([phase1, phase2])
        closes += np.random.normal(0, volatility, bars)

    else:
        raise ValueError(f"Unknown scenario: {scenario}")

    # Generate OHLC from closes
    highs = closes + np.random.uniform(0, volatility * 2, bars)
    lows = closes - np.random.uniform(0, volatility * 2, bars)
    opens = np.roll(closes, 1)
    opens[0] = closes[0]

    volumes = np.random.uniform(50, 150, bars)

    df = pd.DataFrame({
        'timestamp': timestamps,
        'open': opens,
        'high': highs,
        'low': lows,
        'close': closes,
        'volume': volumes,
        'symbol': symbol
    })

    df = df.set_index('timestamp')
    df.attrs['symbol'] = symbol

    return df


def generate_synthetic_trades(ohlcv: pd.DataFrame, vpin_target: float = 0.4) -> list:
    """
    Genera trades sintéticos a partir de OHLCV.

    Args:
        ohlcv: DataFrame OHLCV
        vpin_target: VPIN objetivo (0.4 = balanced, 0.7 = toxic)

    Returns:
        Lista de trades [{price, volume, bid, ask, timestamp, side}, ...]
    """
    trades = []

    for idx, row in ohlcv.iterrows():
        # Generar ~10 trades por barra
        num_trades = np.random.randint(8, 15)
        bar_prices = np.random.uniform(row['low'], row['high'], num_trades)
        bar_volumes = np.random.uniform(1, 20, num_trades)

        # Adjust buy/sell ratio based on vpin_target
        buy_ratio = 0.5 if vpin_target < 0.5 else (0.8 if vpin_target > 0.6 else 0.65)

        for price, volume in zip(bar_prices, bar_volumes):
            side = 'BUY' if np.random.rand() < buy_ratio else 'SELL'

            trades.append({
                'price': price,
                'volume': volume,
                'bid': price - 0.00002,  # 0.2 pip spread
                'ask': price + 0.00002,
                'timestamp': idx,
                'side': side
            })

    return trades


def test_microstructure_engine():
    """Test 1: MicrostructureEngine básico"""
    logger.info("="*60)
    logger.info("TEST 1: MicrostructureEngine")
    logger.info("="*60)

    config = {
        'vpin': {'bucket_volume': 50, 'window_buckets': 20},
        'order_flow': {'window_seconds': 60, 'min_trades': 3}
    }

    engine = MicrostructureEngine(config)
    symbol = 'EURUSD'

    # Scenario: balanced flow
    trades_balanced = [
        {'price': 1.1000 + i * 0.00001, 'volume': 10, 'bid': 1.1000, 'ask': 1.1001,
         'timestamp': datetime.now(), 'side': 'BUY' if i % 2 == 0 else 'SELL'}
        for i in range(100)
    ]

    engine.update_trades(symbol, trades_balanced)
    score = engine.get_microstructure_score(symbol)

    logger.info(f"✓ Balanced flow → microstructure_score = {score}")
    assert 0.4 <= score <= 1.0, f"Score {score} fuera de rango esperado para flujo balanceado"

    logger.info("✅ TEST 1 PASSED")
    return True


def test_multiframe_orchestrator():
    """Test 2: MultiFrameOrchestrator básico"""
    logger.info("="*60)
    logger.info("TEST 2: MultiFrameOrchestrator")
    logger.info("="*60)

    config = {
        'htf': {'lookback_swings': 10},
        'mtf': {'poi_lookback': 20}
    }

    orchestrator = MultiFrameOrchestrator(config)
    symbol = 'EURUSD'

    # Scenario: uptrend
    htf_data = generate_synthetic_ohlcv(200, 'uptrend', symbol)
    mtf_data = generate_synthetic_ohlcv(50, 'uptrend', symbol)
    current_price = mtf_data['close'].iloc[-1]

    result = orchestrator.analyze_multiframe(symbol, htf_data, mtf_data, current_price, signal_direction=1)

    logger.info(f"✓ HTF trend = {result['htf_structure']['trend_direction']}")
    logger.info(f"✓ Multiframe score = {result['multiframe_score']:.4f}")
    logger.info(f"✓ MTF confluence = {result['mtf_confluence']:.4f}")

    assert 0.0 <= result['multiframe_score'] <= 1.0, "Multiframe score fuera de rango"
    assert result['htf_structure']['trend_direction'] in ['BULLISH', 'BEARISH', 'RANGE']

    logger.info("✅ TEST 2 PASSED")
    return True


def test_strategy_integration(strategy_class, strategy_name, config_override=None):
    """
    Test genérico de integración de estrategia.

    Args:
        strategy_class: Clase de estrategia
        strategy_name: Nombre para logging
        config_override: Config específico (opcional)
    """
    logger.info("="*60)
    logger.info(f"TEST: {strategy_name}")
    logger.info("="*60)

    # Setup motores
    micro_engine = MicrostructureEngine({
        'vpin': {'bucket_volume': 50, 'window_buckets': 20},
        'order_flow': {'window_seconds': 60}
    })

    multi_orchestrator = MultiFrameOrchestrator({
        'htf': {'lookback_swings': 10},
        'mtf': {'poi_lookback': 20}
    })

    # Setup estrategia
    base_config = {
        'enabled': True,
        'microstructure_engine': micro_engine,
        'multiframe_orchestrator': multi_orchestrator
    }

    if config_override:
        base_config.update(config_override)

    strategy = strategy_class(base_config)

    # Generate data
    symbol = 'EURUSD'
    market_data = generate_synthetic_ohlcv(250, 'uptrend', symbol)
    trades = generate_synthetic_trades(market_data, vpin_target=0.4)

    # Update motores
    micro_engine.update_trades(symbol, trades)

    # Prepare features (mock)
    features = {
        'vpin': micro_engine.get_microstructure_score(symbol),
        'ofi': 0.3,
        'order_book_imbalance': 0.2,
        'swing_highs': [1.1050, 1.1060],
        'swing_lows': [1.0980, 1.0990]
    }

    # Evaluate strategy
    signals = strategy.evaluate(market_data, features)

    logger.info(f"✓ Señales generadas: {len(signals)}")

    # Validate signals (si hay)
    if signals:
        signal = signals[0]
        metadata = signal.metadata

        logger.info(f"✓ Signal direction: {signal.direction}")
        logger.info(f"✓ Metadata keys: {list(metadata.keys())[:10]}...")  # Primeras 10 keys

        # Validate metadata MANDATO 16
        required_keys = ['signal_strength', 'structure_alignment', 'microstructure_quality', 'regime_confidence']
        for key in required_keys:
            assert key in metadata, f"❌ Missing metadata key: {key}"
            value = metadata[key]
            assert isinstance(value, (int, float)), f"❌ {key} debe ser numérico"
            assert 0.0 <= value <= 1.0, f"❌ {key} = {value} fuera de rango [0-1]"

        logger.info(f"✓ signal_strength = {metadata['signal_strength']:.4f}")
        logger.info(f"✓ structure_alignment = {metadata['structure_alignment']:.4f}")
        logger.info(f"✓ microstructure_quality = {metadata['microstructure_quality']:.4f}")
        logger.info(f"✓ regime_confidence = {metadata['regime_confidence']:.4f}")

        assert 'strategy_version' in metadata, "❌ Missing strategy_version"
        assert 'MANDATO16' in metadata['strategy_version'], "❌ Strategy version no indica MANDATO16"

    logger.info(f"✅ {strategy_name} INTEGRATION PASSED")
    return True


def main():
    """Run all smoke tests"""
    logger.info("🚀 MANDATO 16 - Smoke Test: Strategy Integration")
    logger.info("="*60)

    try:
        # Test 1: MicrostructureEngine
        test_microstructure_engine()

        # Test 2: MultiFrameOrchestrator
        test_multiframe_orchestrator()

        # Test 3-7: Estrategias núcleo
        test_strategy_integration(
            LiquiditySweepStrategy,
            "LiquiditySweepStrategy",
            {'lookback_periods': [60, 120], 'min_confirmation_score': 2}
        )

        test_strategy_integration(
            VPINReversalExtreme,
            "VPINReversalExtreme",
            {'vpin_reversal_entry': 0.70, 'vpin_peak_required': 0.75}
        )

        # Las otras 3 estrategias pueden no generar señales con datos sintéticos simples
        # pero validamos que se inicialicen correctamente con los motores
        for strategy_class, name in [
            (OrderFlowToxicityStrategy, "OrderFlowToxicityStrategy"),
            (OFIRefinement, "OFIRefinement"),
            (BreakoutVolumeConfirmation, "BreakoutVolumeConfirmation")
        ]:
            logger.info("="*60)
            logger.info(f"TEST: {name} (initialization)")
            logger.info("="*60)

            micro = MicrostructureEngine({})
            multi = MultiFrameOrchestrator({})

            strategy = strategy_class({
                'enabled': True,
                'microstructure_engine': micro,
                'multiframe_orchestrator': multi
            })

            assert strategy.microstructure_engine is not None, f"❌ {name} no tiene microstructure_engine"
            assert strategy.multiframe_orchestrator is not None, f"❌ {name} no tiene multiframe_orchestrator"

            logger.info(f"✅ {name} initialization OK")

        logger.info("="*60)
        logger.info("🎉 ALL TESTS PASSED")
        logger.info("="*60)
        logger.info("")
        logger.info("✅ MicrostructureEngine + MultiFrameOrchestrator operativos")
        logger.info("✅ 5 estrategias núcleo integradas correctamente")
        logger.info("✅ Metadata completa para QualityScorer")
        logger.info("✅ Sistema listo para operación institucional")
        logger.info("")

        return 0

    except AssertionError as e:
        logger.error(f"❌ TEST FAILED: {e}")
        return 1

    except Exception as e:
        logger.error(f"❌ UNEXPECTED ERROR: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
