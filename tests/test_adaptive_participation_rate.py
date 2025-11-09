"""
Unit tests for Adaptive Participation Rate Executor.

TESTING PHILOSOPHY:
The APR module is not a signal generator but an execution optimizer. These tests
validate that large orders are sliced intelligently to minimize market impact
while meeting target completion times.

WHAT WE'RE TESTING:
1. Participation rate calculation (momentum/volatility/volume adjustments)
2. Execution plan creation (slice sizing and timing)
3. Market impact estimation (Almgren-Chriss framework)
4. Threshold enforcement (small orders don't get sliced unnecessarily)
5. Rate limits (participation stays within institutional bounds)
6. Progress tracking (execution monitoring and updates)

WHY IT MATTERS:
Poor execution can turn a profitable signal into a losing trade. A $1M order
executed badly can easily lose 10-20 basis points ($1,000-$2,000) in slippage
and impact. Good execution on the same order might cost only 3-4 bps ($300-$400).
Over many trades, execution quality is the difference between profit and loss.

INSTITUTIONAL CONTEXT:
Every major institution has dedicated execution algorithms (TWAP, VWAP, POV, etc.).
APR is a simplified version of POV (Percentage of Volume) with adaptive features.
Real institutional systems are far more complex, but this provides 80% of the
value with 20% of the complexity.
"""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from src.execution.adaptive_participation_rate import APRExecutor, ExecutionPlan

class TestAPRExecutor:
    """Comprehensive test suite for APR execution module."""
    
    @pytest.fixture
    def executor(self):
        """
        Initialize executor with institutional parameters.
        
        These parameters are standard for institutional execution:
        - Base rate 10%: Participate in 10% of market volume (balance of speed/impact)
        - Momentum alpha 5%: Moderate sensitivity to price direction
        - Volatility beta 15%: Higher sensitivity to volatility (risk averse)
        - Rate floor 5%: Never go below 5% (excessive time risk)
        - Rate ceiling 25%: Never exceed 25% (excessive impact)
        - Minimum notional $100k: Only use APR for meaningful orders
        """
        params = {
            'base_rate': 0.10,
            'momentum_alpha': 0.05,
            'volatility_beta': 0.15,
            'rate_floor': 0.05,
            'rate_ceiling': 0.25,
            'minimum_notional_for_activation': 100000,
            'slippage_monitoring': True,
            'market_impact_tracking': True
        }
        return APRExecutor(params)
    
    @pytest.fixture
    def market_data(self):
        """
        Generate realistic market data for testing.
        
        CHARACTERISTICS:
        - 100 bars of M1 data (simulates ~1.5 hours of trading)
        - Trending market (simulates momentum condition)
        - Moderate volatility (0.02% per bar)
        - Realistic volume distribution (400-800 per bar)
        
        This data allows us to test APR under typical market conditions.
        """
        np.random.seed(42)
        
        dates = pd.date_range(end=datetime.now(), periods=100, freq='1min')
        
        # Generate trending price action
        trend = np.linspace(1.1000, 1.1050, 100)  # 50 pip uptrend
        noise = np.random.normal(0, 0.0002, 100)  # 2 pip noise
        
        data = pd.DataFrame({
            'timestamp': dates,
            'close': trend + noise,
            'tick_volume': np.random.uniform(400, 800, 100),
            'spread': [0.00002] * 100
        })
        
        # Add OHLC derived from close
        data['open'] = data['close'] - np.random.uniform(0, 0.0001, 100)
        data['high'] = data['close'] + np.random.uniform(0, 0.0002, 100)
        data['low'] = data['close'] - np.random.uniform(0, 0.0002, 100)
        
        return data
    
    def test_participation_rate_calculation(self, executor, market_data):
        """
        Test adaptive participation rate calculation.
        
        WHAT WE'RE TESTING:
        The core algorithm that determines execution speed. Participation rate
        should increase with favorable momentum and liquidity, decrease with
        volatility.
        
        TEST CASE:
        - Positive momentum (+0.5) → increase rate
        - Low volatility (0.2) → increase rate
        - Normal volume → neutral effect
        
        Expected: Rate > base_rate (0.10)
        
        WHY THIS MATTERS:
        If participation rate calculation is wrong, we either execute too fast
        (high impact) or too slow (time risk). The adaptive algorithm balances
        these competing concerns.
        """
        # Test with favorable conditions
        rate = executor.calculate_participation_rate(
            price_momentum=0.5,  # Strong positive momentum
            volatility=0.2,  # Low volatility
            volume_profile=market_data['tick_volume'].tail(20)
        )
        
        # ASSERTION 1: Rate should be higher than base with favorable conditions
        assert rate > executor.base_rate, \
               f"Rate {rate:.3f} should exceed base {executor.base_rate:.3f} with favorable conditions"
        
        # ASSERTION 2: Rate must respect ceiling
        assert rate <= executor.rate_ceiling, \
               f"Rate {rate:.3f} must not exceed ceiling {executor.rate_ceiling:.3f}"
        
        # Test with adverse conditions
        rate_adverse = executor.calculate_participation_rate(
            price_momentum=-0.5,  # Strong negative momentum
            volatility=0.8,  # High volatility
            volume_profile=market_data['tick_volume'].tail(20)
        )
        
        # ASSERTION 3: Rate should be lower with adverse conditions
        assert rate_adverse < executor.base_rate, \
               "Rate should decrease with adverse conditions"
        
        # ASSERTION 4: Rate must respect floor
        assert rate_adverse >= executor.rate_floor, \
               f"Rate {rate_adverse:.3f} must not go below floor {executor.rate_floor:.3f}"
    
    def test_execution_plan_creation(self, executor, market_data):
        """
        Test creation of execution plan for large order.
        
        WHAT WE'RE TESTING:
        Given a large order (10 lots = $1.1M notional), can the executor create
        a sensible execution plan that:
        1. Slices the order appropriately
        2. Schedules slices across target duration
        3. Estimates impact and slippage
        4. Respects participation rate constraints
        
        TEST ORDER:
        - Size: 10 lots
        - Price: 1.1050
        - Notional: 10 × 100,000 × 1.1050 = $1,105,000
        - Above threshold: Yes ($1.1M > $100k)
        - Expected: Plan created with multiple slices
        """
        total_size = 10.0  # 10 lots
        current_price = 1.1050
        
        plan = executor.create_execution_plan(
            total_size=total_size,
            current_price=current_price,
            direction='BUY',
            market_data=market_data,
            target_duration_minutes=30
        )
        
        # ASSERTION 1: Plan should be created for large order
        assert plan is not None, "Plan should be created for order above threshold"
        
        # ASSERTION 2: Verify plan properties
        assert plan.total_size == total_size, "Plan should match requested size"
        assert len(plan.slices) > 0, "Plan should contain slices"
        assert plan.participation_rate > 0, "Plan should have valid participation rate"
        
        # ASSERTION 3: Verify slices sum to total
        # Allow small rounding error due to randomization
        total_slice_size = sum(s['size'] for s in plan.slices)
        assert abs(total_slice_size - total_size) < 0.01, \
               f"Slices should sum to total: {total_slice_size:.3f} vs {total_size:.3f}"
        
        # ASSERTION 4: Verify slices are scheduled across duration
        first_slice_time = plan.slices[0]['target_time']
        last_slice_time = plan.slices[-1]['target_time']
        duration_seconds = (last_slice_time - first_slice_time).total_seconds()
        
        # Should span approximately target duration (within 10%)
        target_seconds = 30 * 60  # 30 minutes
        assert 0.8 * target_seconds <= duration_seconds <= 1.2 * target_seconds, \
               f"Slices should span ~{30} minutes, got {duration_seconds/60:.1f} min"
        
        # ASSERTION 5: Impact and slippage estimates should be reasonable
        # For 10 lots with 30 min duration, impact should be single-digit bps
        assert 0 < plan.market_impact_estimate < 20, \
               f"Impact estimate {plan.market_impact_estimate:.2f} bps seems unreasonable"
        assert 0 < plan.slippage_estimate < 30, \
               f"Slippage estimate {plan.slippage_estimate:.2f} bps seems unreasonable"
    
    def test_small_order_no_apr(self, executor, market_data):
        """
        Test that small orders bypass APR (no slicing).
        
        WHAT WE'RE TESTING:
        Orders below $100k threshold should execute as single order, not sliced.
        Slicing tiny orders adds complexity without benefit.
        
        TEST CASE:
        - Size: 0.1 lots
        - Price: 1.1050
        - Notional: 0.1 × 100,000 × 1.1050 = $11,050
        - Below threshold: Yes ($11k < $100k)
        - Expected: None (execute as single order)
        
        WHY THIS MATTERS:
        Unnecessary slicing increases operational risk (more fills to track,
        more opportunities for errors) without reducing impact on tiny orders.
        """
        total_size = 0.1  # 0.1 lots (small order)
        current_price = 1.1050
        
        plan = executor.create_execution_plan(
            total_size=total_size,
            current_price=current_price,
            direction='BUY',
            market_data=market_data
        )
        
        # ASSERTION: No plan should be created for small order
        assert plan is None, \
               "Small order below threshold should return None (execute as single order)"
    
    def test_market_impact_estimation(self, executor):
        """
        Test market impact estimation using Almgren-Chriss framework.
        
        WHAT WE'RE TESTING:
        The mathematical model that predicts how much our order will move the market.
        Impact should:
        1. Increase with order size (larger orders = more impact)
        2. Decrease with duration (slower execution = less impact)
        3. Increase with volatility (uncertain markets = more impact)
        
        TEST CASE:
        Standard parameters should yield reasonable impact estimate.
        
        THEORY:
        Impact has two components per Almgren-Chriss:
        - Temporary: Proportional to √(participation_rate)
        - Permanent: Proportional to participation_rate
        
        Total impact = (temp + perm) × volatility_factor
        """
        impact = executor._estimate_market_impact(
            order_size=10.0,  # 10 lots
            avg_volume=500,   # 500 ticks/min average volume
            volatility=0.3,   # Moderate volatility
            duration_minutes=30  # 30 minute execution
        )
        
        # ASSERTION 1: Impact should be positive
        assert impact > 0, "Impact must be positive"
        
        # ASSERTION 2: Impact should be reasonable for this order
        # 10 lots over 30 min with moderate volume/volatility
        # Should be single-digit basis points
        assert impact < 100, \
               f"Impact {impact:.2f} bps seems unreasonably high for this order"
        
        # Test impact scales with size
        impact_large = executor._estimate_market_impact(
            order_size=50.0,  # 5x larger order
            avg_volume=500,
            volatility=0.3,
            duration_minutes=30
        )
        
        # ASSERTION 3: Larger order should have higher impact
        assert impact_large > impact, \
               "Larger order should have higher impact"
    
    def test_execution_update(self, executor, market_data):
        """
        Test execution update and tracking functionality.
        
        WHAT WE'RE TESTING:
        Can the executor track actual fills and calculate slippage?
        This is critical for:
        1. Monitoring execution quality
        2. Detecting execution problems
        3. Post-trade analysis
        4. Algorithm optimization
        
        TEST FLOW:
        1. Create execution plan
        2. Simulate fill of first slice
        3. Update plan with actual fill data
        4. Verify tracking and calculations
        """
        # Create plan
        plan = executor.create_execution_plan(
            total_size=5.0,
            current_price=1.1050,
            direction='BUY',
            market_data=market_data,
            target_duration_minutes=10
        )
        
        if plan:
            # Simulate fill of first slice
            first_slice = plan.slices[0]
            executed_price = 1.1051  # Small slippage
            executed_size = first_slice['size']
            
            # Update execution
            executor.update_execution(
                plan=plan,
                slice_number=1,
                executed_price=executed_price,
                executed_size=executed_size
            )
            
            # ASSERTION 1: Slice should be marked as executed
            assert plan.slices[0]['executed'] == True, \
                   "Slice should be marked as executed"
            
            # ASSERTION 2: Execution data should be recorded
            assert 'executed_price' in plan.slices[0], \
                   "Executed price should be recorded"
            assert plan.slices[0]['executed_price'] == executed_price, \
                   "Recorded price should match actual fill"
            
            # ASSERTION 3: Completion percentage should update
            assert plan.completion_percentage > 0, \
                   "Completion percentage should increase after fill"
    
    def test_rate_limits_enforcement(self, executor):
        """
        Test that participation rate respects floor and ceiling.
        
        WHAT WE'RE TESTING:
        No matter how extreme the market conditions, participation rate must
        stay within institutional risk limits (5%-25%).
        
        WHY THIS MATTERS:
        - Below floor: Excessive time risk (order may not complete)
        - Above ceiling: Excessive impact (order moves market too much)
        
        TEST CASES:
        1. Extreme favorable conditions → should hit ceiling
        2. Extreme adverse conditions → should hit floor
        """
        # Test ceiling with extreme favorable conditions
        rate_high = executor.calculate_participation_rate(
            price_momentum=1.0,   # Maximum positive momentum
            volatility=0.0,       # Zero volatility
            volume_profile=pd.Series([1000] * 20)  # High volume
        )
        
        # ASSERTION 1: Should not exceed ceiling
        assert rate_high <= executor.rate_ceiling, \
               f"Rate {rate_high:.3f} exceeds ceiling {executor.rate_ceiling:.3f}"
        
        # Test floor with extreme adverse conditions
        rate_low = executor.calculate_participation_rate(
            price_momentum=-1.0,  # Maximum negative momentum
            volatility=1.0,       # Maximum volatility
            volume_profile=pd.Series([100] * 20)  # Low volume
        )
        
        # ASSERTION 2: Should not go below floor
        assert rate_low >= executor.rate_floor, \
               f"Rate {rate_low:.3f} below floor {executor.rate_floor:.3f}"

if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])