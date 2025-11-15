# Strategy Metadata Contract - MANDATO 25

**Status**: DOCUMENTED (P1-M25-4 partial completion)
**Date**: 2025-11-15
**Purpose**: Define expected metadata fields for Signal objects

---

## CORE CONTRACT - REQUIRED FIELDS

All strategies MUST emit Signal objects with these metadata fields:

### Tier 1: Core Identification (REQUIRED)
```python
{
    'setup_type': str,              # Pattern type identifier (e.g., 'INSTITUTIONAL_IDP', 'VPIN_REVERSAL')
    'risk_reward_ratio': float,     # RR ratio (must be >= 2.0 for institutional)
    'rationale': str,               # Human-readable explanation of setup
}
```

### Tier 2: Quality Metrics (STRONGLY RECOMMENDED)
```python
{
    'confirmation_score': float,    # Setup quality score (0-5 scale typical)
    'expected_win_rate': float,     # Estimated probability of success (0.0-1.0)
}
```

### Tier 3: Order Flow Context (RECOMMENDED for order flow strategies)
```python
{
    'ofi': float,                   # Current OFI value (if used in setup)
    'cvd': float,                   # Current CVD value (if used in setup)
    'vpin': float,                  # Current VPIN value (if used in setup)
}
```

### Tier 4: Strategy-Specific (OPTIONAL)
- Pattern-specific details (e.g., 'inducement_level', 'displacement_velocity')
- Partial exit plans (e.g., 'partial_exit_1': {'r_level': 1.5, 'percent': 50})
- Diagnostic data for debugging

---

## AUDIT RESULTS - 2025-11-15

### ✅ COMPLIANT Strategies (10 confirmed):

| Strategy | Tier 1 | Tier 2 | Tier 3 | Notes |
|----------|--------|--------|--------|-------|
| breakout_volume_confirmation | ✓ | ✓ | ✓ | Full compliance |
| htf_ltf_liquidity | ✓ | ✓ | ✓ | Full compliance |
| idp_inducement_distribution | ✓ | ✓ | ✓ | Full compliance |
| mean_reversion_statistical | ✓ | ✓ | ✓ | Full compliance |
| nfp_news_event_handler | ✓ | ✓ | ✓ | Full compliance |
| order_flow_toxicity | ✓ | ✓ | ✓ | Full compliance |
| statistical_arbitrage_johansen | ✓ | ✓ | ✓ | Full compliance |
| vpin_reversal_extreme | ✓ | ✓ | ✓ | Full compliance |
| ofi_refinement | ✓ | ⚠️ | ✓ | Missing confirmation_score |

### ⚠️ UNKNOWN Compliance (16 strategies):

Strategies where Signal() emission pattern unclear from regex audit:
- calendar_arbitrage_flows
- correlation_cascade_detection
- correlation_divergence
- crisis_mode_volatility_spike
- footprint_orderflow_clusters
- fractal_market_structure
- fvg_institutional
- iceberg_detection
- kalman_pairs_trading
- liquidity_sweep
- momentum_quality
- order_block_institutional
- spoofing_detection_l2
- topological_data_analysis_regime
- volatility_regime_adaptation

**Action Required**: Manual review of these strategies to verify Signal emission

---

## VALIDATION APPROACH (Future Work - P2)

### Option 1: Runtime Validation
```python
def validate_signal_metadata(signal: Signal, strategy_type: str) -> bool:
    """Validate signal has required metadata fields."""
    required = ['setup_type', 'risk_reward_ratio', 'rationale']

    for field in required:
        if field not in signal.metadata:
            logger.error(f"{strategy_type}: Missing required metadata field '{field}'")
            return False

    return True
```

### Option 2: Unit Tests
```python
def test_strategy_metadata_contract():
    """Test that all strategies emit required metadata."""
    for strategy_class in STRATEGY_REGISTRY:
        # Create test signal
        signal = strategy.evaluate(test_data, test_features)

        # Validate contract
        assert validate_signal_metadata(signal, strategy_class.__name__)
```

### Option 3: Static Analysis
Use AST parsing to verify all `Signal()` instantiations include required metadata keys.

---

## COMMON METADATA PATTERNS

### Pattern 1: Institutional Order Flow Setup
```python
metadata = {
    'setup_type': 'ORDER_FLOW_REVERSAL',
    'confirmation_score': 4.2,
    'expected_win_rate': 0.74,
    'risk_reward_ratio': 3.5,
    'rationale': f"VPIN={vpin:.2f} (extreme), OFI={ofi:.2f} (reversal), CVD={cvd:.0f} (divergence)",

    # Order flow context
    'ofi': ofi,
    'cvd': cvd,
    'vpin': vpin,
    'vpin_threshold': 0.85,

    # Pattern-specific
    'reversal_direction': 'DOWN',
    'toxicity_duration': 5,
}
```

### Pattern 2: Structural Breakout
```python
metadata = {
    'setup_type': 'VOLUME_BREAKOUT',
    'confirmation_score': 3.8,
    'expected_win_rate': 0.68,
    'risk_reward_ratio': 2.8,
    'rationale': f"Range breakout after {range_bars} bars consolidation",

    # Pattern-specific
    'range_bars': range_bars,
    'range_size_atr': range_size / atr,
    'breakout_volume_ratio': volume / avg_volume,
}
```

### Pattern 3: Pairs/Arbitrage
```python
metadata = {
    'setup_type': 'STATISTICAL_ARBITRAGE',
    'risk_reward_ratio': 2.5,
    'rationale': f"Pair {symbol1}/{symbol2} spread z-score {zscore:.2f}",

    # Pairs-specific
    'pair_key': f"{symbol1}_{symbol2}",
    'spread_zscore': zscore,
    'hedge_ratio': hedge_ratio,
    'half_life_bars': half_life,
}
```

---

## IMPLEMENTATION STATUS

| Component | Status | Notes |
|-----------|--------|-------|
| Contract Definition | ✅ DONE | This document |
| Strategy Audit | ⚠️ PARTIAL | 10/26 strategies confirmed compliant |
| Validation Function | ❌ TODO | Runtime validator not implemented |
| Unit Tests | ❌ TODO | No automated contract tests |
| Documentation | ✅ DONE | This document serves as spec |

---

## NEXT STEPS (P2 Priority)

1. **Manual Review** (4 hours)
   - Review 16 strategies with unclear Signal() patterns
   - Verify they emit Tier 1 required fields
   - Document any non-compliant strategies

2. **Validation Integration** (2 hours)
   - Add `validate_signal_metadata()` to StrategyOrchestrator
   - Log warnings for non-compliant signals
   - Optional: Reject signals missing required fields

3. **Unit Tests** (3 hours)
   - Create `tests/test_strategy_metadata_contract.py`
   - Test each strategy emits required metadata
   - Fail CI if any strategy non-compliant

4. **Refactor Non-Compliant** (varies)
   - Fix strategies missing required fields
   - Standardize metadata key naming

---

## RATIONALE

**Why this contract matters:**

1. **Observability**: Brain needs consistent metadata for logging/debugging
2. **Risk Management**: Requires 'risk_reward_ratio' for position sizing validation
3. **Performance Attribution**: 'setup_type' enables strategy-level analysis
4. **Operational Transparency**: 'rationale' enables human review of signals
5. **Quality Control**: 'confirmation_score', 'expected_win_rate' enable filtering

**Impact of non-compliance:**
- Logging/debugging harder (missing context)
- Risk management can't validate RR
- Performance attribution incomplete
- Operations can't understand why signal fired

**Severity**: MEDIUM (P1) - System functional but harder to operate/debug
