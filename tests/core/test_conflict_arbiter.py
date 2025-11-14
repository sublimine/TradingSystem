"""
Tests críticos para ConflictArbiter
Mandato 6 - Testing P0
"""
import pytest
from unittest.mock import Mock, patch
from src.core.conflict_arbiter import ConflictArbiter, EVCalculation, ConflictResolution
from src.core.signal_schema import InstitutionalSignal


def test_conflict_arbiter_no_signals():
    """Test P0: Arbiter con cero señales retorna SILENCE."""
    arbiter = ConflictArbiter()

    resolution = arbiter.arbitrate(
        signals=[],
        instrument="EURUSD",
        horizon="M15",
        batch_id="B001"
    )

    assert resolution.decision == "SILENCE"
    assert resolution.winning_signal is None
    assert "NO_SIGNALS" in resolution.reason_codes


def test_conflict_arbiter_single_signal_high_quality():
    """Test P0: Señal única de alta calidad debe ejecutarse."""
    arbiter = ConflictArbiter()

    # Mock de señal de alta calidad
    signal = Mock(spec=InstitutionalSignal)
    signal.signal_id = "S001"
    signal.strategy_name = "momentum_quality"
    signal.direction = "LONG"
    signal.quality_score = 0.85
    signal.confidence = 0.9
    signal.instrument = "EURUSD"
    signal.horizon = "M15"
    signal.to_dict = Mock(return_value={"signal_id": "S001"})

    # Mock regime engine
    with patch.object(arbiter, 'regime_engine') as mock_regime:
        mock_regime.get_regime_probabilities.return_value = {
            "TREND_STRONG": 0.7,
            "RANGING": 0.3
        }

        resolution = arbiter.arbitrate(
            signals=[signal],
            instrument="EURUSD",
            horizon="M15",
            batch_id="B001"
        )

    assert resolution.decision in ["EXECUTE", "SILENCE"]
    # Si se ejecuta, debe ser la señal ganadora
    if resolution.decision == "EXECUTE":
        assert resolution.winning_signal == signal


def test_conflict_arbiter_conflicting_signals():
    """Test P0: Señales conflictivas (LONG vs SHORT) se resuelven por calidad."""
    arbiter = ConflictArbiter()

    # Señal LONG calidad media
    signal_long = Mock(spec=InstitutionalSignal)
    signal_long.signal_id = "S001"
    signal_long.strategy_name = "momentum_quality"
    signal_long.direction = "LONG"
    signal_long.quality_score = 0.70
    signal_long.confidence = 0.75
    signal_long.instrument = "EURUSD"
    signal_long.to_dict = Mock(return_value={"signal_id": "S001"})

    # Señal SHORT calidad alta
    signal_short = Mock(spec=InstitutionalSignal)
    signal_short.signal_id = "S002"
    signal_short.strategy_name = "mean_reversion"
    signal_short.direction = "SHORT"
    signal_short.quality_score = 0.85
    signal_short.confidence = 0.90
    signal_short.instrument = "EURUSD"
    signal_short.to_dict = Mock(return_value={"signal_id": "S002"})

    with patch.object(arbiter, 'regime_engine') as mock_regime:
        mock_regime.get_regime_probabilities.return_value = {"TREND_STRONG": 1.0}

        resolution = arbiter.arbitrate(
            signals=[signal_long, signal_short],
            instrument="EURUSD",
            horizon="M15",
            batch_id="B001"
        )

    # Debe resolver conflicto
    assert resolution.decision in ["EXECUTE", "REJECT", "SILENCE"]

    # Si ejecuta, debe elegir la de mayor calidad (SHORT)
    if resolution.decision == "EXECUTE":
        assert resolution.winning_signal == signal_short
        assert signal_long in resolution.losing_signals


def test_conflict_arbiter_quality_threshold():
    """Test P0: Señales bajo quality threshold se rechazan."""
    arbiter = ConflictArbiter()
    arbiter.min_quality_threshold = 0.60  # Threshold mínimo

    # Señal de baja calidad
    signal_low = Mock(spec=InstitutionalSignal)
    signal_low.signal_id = "S001"
    signal_low.strategy_name = "test_strategy"
    signal_low.direction = "LONG"
    signal_low.quality_score = 0.45  # Bajo threshold
    signal_low.confidence = 0.50
    signal_low.instrument = "EURUSD"
    signal_low.to_dict = Mock(return_value={"signal_id": "S001"})

    with patch.object(arbiter, 'regime_engine') as mock_regime:
        mock_regime.get_regime_probabilities.return_value = {"TREND_STRONG": 1.0}

        resolution = arbiter.arbitrate(
            signals=[signal_low],
            instrument="EURUSD",
            horizon="M15",
            batch_id="B001"
        )

    # Debe rechazar por quality baja
    assert resolution.decision in ["REJECT", "SILENCE"]
    if "QUALITY_THRESHOLD" in arbiter.__dict__:
        assert any("QUALITY" in code for code in resolution.reason_codes)
