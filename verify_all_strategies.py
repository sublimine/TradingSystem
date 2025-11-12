"""Script de verificación con imports consistentes."""
import sys
sys.path.insert(0, 'C:/Users/Administrator/TradingSystem')

# Import todas las estrategias usando el mismo método que el orchestrator
from src.strategies.ofi_refinement import OFIRefinement
from src.strategies.fvg_institutional import FVGInstitutional
from src.strategies.htf_ltf_liquidity import HTFLTFLiquidity
from src.strategies.order_block_institutional import OrderBlockInstitutional
from src.strategies.volatility_regime_adaptation import VolatilityRegimeAdaptation
from src.strategies.momentum_quality import MomentumQuality
from src.strategies.mean_reversion_statistical import MeanReversionStatistical
from src.strategies.idp_inducement_distribution import IDPInducement
from src.strategies.iceberg_detection import IcebergDetection
from src.strategies.breakout_volume_confirmation import AbsorptionBreakout
from src.strategies.correlation_divergence import CorrelationDivergence
from src.strategies.kalman_pairs_trading import KalmanPairsTrading
from src.strategies.liquidity_sweep import LiquiditySweepStrategy
from src.strategies.order_flow_toxicity import OrderFlowToxicityStrategy

print("=" * 70)
print("VERIFICACIÓN DE 14 ESTRATEGIAS INSTITUCIONALES")
print("=" * 70)
print()

strategies = [
    ("OFI Refinement", OFIRefinement),
    ("FVG Institutional", FVGInstitutional),
    ("HTF-LTF Liquidity", HTFLTFLiquidity),
    ("Order Block Institutional", OrderBlockInstitutional),
    ("Volatility Regime Adaptation", VolatilityRegimeAdaptation),
    ("Momentum Quality", MomentumQuality),
    ("Mean Reversion Statistical", MeanReversionStatistical),
    ("IDP Inducement", IDPInducement),
    ("Iceberg Detection", IcebergDetection),
    ("Breakout Volume Confirmation", AbsorptionBreakout),
    ("Correlation Divergence", CorrelationDivergence),
    ("Kalman Pairs Trading", KalmanPairsTrading),
    ("Liquidity Sweep", LiquiditySweepStrategy),
    ("Order Flow Toxicity", OrderFlowToxicityStrategy)
]

passed = 0

for name, strategy_class in strategies:
    try:
        has_evaluate = hasattr(strategy_class, 'evaluate')
        
        test_config = {'enabled': True, 'name': name.lower().replace(' ', '_')}
        instance = strategy_class(test_config)
        
        has_logger = hasattr(instance, 'logger')
        has_name = hasattr(instance, 'name')
        
        if has_evaluate and has_logger and has_name:
            print(f"[OK] {name}")
            passed += 1
        else:
            print(f"[FAIL] {name} - evaluate={has_evaluate}, logger={has_logger}, name={has_name}")
            
    except Exception as e:
        print(f"[ERROR] {name}: {e}")

print()
print("=" * 70)
print(f"RESULTADO: {passed}/{len(strategies)} estrategias verificadas")
print("=" * 70)
print()

if passed == len(strategies):
    print("[SUCCESS] Todas las estrategias operativas")
else:
    print(f"[FAIL] {len(strategies) - passed} estrategias con problemas")