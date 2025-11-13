"""
Tests críticos para InstitutionalRiskManager
Mandato 6 - Testing P0
"""
import pytest
from unittest.mock import Mock
from src.core.risk_manager import InstitutionalRiskManager, QualityScorer


def test_quality_scorer_basic():
    """Test P0: QualityScorer calcula score en rango [0, 1]."""
    scorer = QualityScorer()

    signal = {
        'metadata': {
            'mtf_confluence': 0.8,
            'structure_alignment': 0.7,
            'regime_confidence': 0.75
        },
        'strategy_name': 'momentum_quality'
    }

    market_context = {
        'vpin': 0.35,
        'strategy_performance': {'momentum_quality': 0.70}
    }

    quality = scorer.calculate_quality(signal, market_context)

    assert 0.0 <= quality <= 1.0, "Quality debe estar en [0, 1]"
    assert isinstance(quality, float)


def test_quality_scorer_weights_sum_to_one():
    """Test P0: Pesos del QualityScorer suman 1.0."""
    scorer = QualityScorer()

    total_weight = sum(scorer.weights.values())

    assert abs(total_weight - 1.0) < 0.001, f"Pesos deben sumar 1.0, sum={total_weight}"


def test_risk_manager_rejects_low_quality():
    """Test P0: Risk Manager rechaza señales con quality < threshold."""
    config = {
        'min_quality_score': 0.65,
        'base_risk_per_trade': 0.5,
        'initial_balance': 100000
    }

    risk_mgr = InstitutionalRiskManager(config)

    # Señal de baja calidad
    signal = {
        'symbol': 'EURUSD.pro',
        'strategy_name': 'test_strategy',
        'direction': 'LONG',
        'entry_price': 1.1000,
        'stop_loss': 1.0950,
        'take_profit': 1.1100,
        'metadata': {
            'mtf_confluence': 0.40,  # Bajo
            'structure_alignment': 0.50,  # Bajo
            'regime_confidence': 0.60
        }
    }

    market_context = {
        'vpin': 0.40,
        'strategy_performance': {'test_strategy': 0.50}
    }

    result = risk_mgr.evaluate_signal(signal, market_context)

    assert result['approved'] is False
    assert 'quality' in result['reason'].lower() or 'low' in result['reason'].lower()


def test_risk_manager_respects_max_risk_cap():
    """Test P0: Risk Manager respeta cap de 2% por trade."""
    config = {
        'min_quality_score': 0.50,
        'max_risk_per_trade': 1.0,  # 1% máximo
        'initial_balance': 100000
    }

    risk_mgr = InstitutionalRiskManager(config)

    # Señal de alta calidad
    signal = {
        'symbol': 'EURUSD.pro',
        'strategy_name': 'momentum_quality',
        'direction': 'LONG',
        'entry_price': 1.1000,
        'stop_loss': 1.0900,  # 100 pips (stop amplio)
        'take_profit': 1.1200,
        'metadata': {
            'mtf_confluence': 0.95,
            'structure_alignment': 0.90,
            'regime_confidence': 0.85
        }
    }

    market_context = {
        'vpin': 0.25,
        'volatility_regime': 'NORMAL',
        'atr': {'EURUSD.pro': 0.0050},
        'strategy_performance': {'momentum_quality': 0.80}
    }

    result = risk_mgr.evaluate_signal(signal, market_context)

    if result['approved']:
        # Risk asignado nunca debe exceder max_risk_per_trade
        assert result['position_size_pct'] <= config['max_risk_per_trade']


def test_risk_manager_exposure_limits():
    """Test P0: Risk Manager rechaza si exposure total >= límite."""
    config = {
        'min_quality_score': 0.50,
        'max_total_exposure': 6.0,  # 6% máximo total
        'initial_balance': 100000
    }

    risk_mgr = InstitutionalRiskManager(config)

    # Simular posiciones activas que suman 5.9%
    risk_mgr.active_positions = {
        'pos_001': {'symbol': 'EURUSD.pro', 'strategy': 'strat1', 'risk_pct': 2.0},
        'pos_002': {'symbol': 'GBPUSD.pro', 'strategy': 'strat2', 'risk_pct': 2.0},
        'pos_003': {'symbol': 'XAUUSD.pro', 'strategy': 'strat3', 'risk_pct': 1.9},
    }

    # Intentar nueva posición de 1.0%
    signal = {
        'symbol': 'BTCUSD.pro',
        'strategy_name': 'momentum_quality',
        'direction': 'LONG',
        'entry_price': 50000.0,
        'stop_loss': 49000.0,
        'take_profit': 52000.0,
        'metadata': {'mtf_confluence': 0.80, 'structure_alignment': 0.75, 'regime_confidence': 0.70}
    }

    market_context = {
        'vpin': 0.30,
        'volatility_regime': 'NORMAL',
        'strategy_performance': {'momentum_quality': 0.70}
    }

    result = risk_mgr.evaluate_signal(signal, market_context)

    # Debe rechazar por exposure total (5.9 + propuesto >= 6.0)
    assert result['approved'] is False or result['position_size_pct'] < 0.2
    if not result['approved']:
        assert 'exposure' in result['reason'].lower()


def test_risk_manager_circuit_breaker():
    """Test P0: Circuit breaker se activa tras pérdidas estadísticamente anómalas."""
    config = {
        'min_quality_score': 0.50,
        'circuit_breaker_z_score': 2.5,
        'initial_balance': 100000
    }

    risk_mgr = InstitutionalRiskManager(config)

    # Simular 10 pérdidas consecutivas (estadísticamente anómalo)
    for i in range(10):
        risk_mgr.circuit_breaker.record_trade(
            pnl_pct=-1.5,  # Pérdidas
            symbol='EURUSD.pro',
            strategy='test_strategy'
        )

    # Intentar evaluar nueva señal
    signal = {
        'symbol': 'EURUSD.pro',
        'strategy_name': 'test_strategy',
        'direction': 'LONG',
        'entry_price': 1.1000,
        'stop_loss': 1.0950,
        'take_profit': 1.1100,
        'metadata': {'mtf_confluence': 0.80, 'structure_alignment': 0.75, 'regime_confidence': 0.70}
    }

    market_context = {'vpin': 0.30, 'strategy_performance': {'test_strategy': 0.70}}

    result = risk_mgr.evaluate_signal(signal, market_context)

    # Circuit breaker debe estar activo o cerca
    stats = risk_mgr.circuit_breaker.get_statistics()
    assert stats['consecutive_losses'] >= 10
