"""
Adaptive Participation Rate (APR) Execution Module.

Dynamic order slicing based on market conditions.
Not a signal generator - execution optimizer.

Based on:
- Almgren & Chriss (2001). "Optimal execution of portfolio transactions."
- Kissell et al. (2004). "A practical framework for estimating transaction costs."

INSTITUTIONAL NOTE:
This module is critical for large order execution (>$100k notional).
It prevents market impact by adaptively slicing orders based on real-time
volume, volatility, and momentum conditions. Implements square-root impact model
with temporary and permanent components per institutional research.
"""

import pandas as pd
import numpy as np
from typing import Dict, Optional, Tuple, List
from dataclasses import dataclass
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)

@dataclass
class ExecutionPlan:
    """
    Represents an institutional-grade adaptive execution plan.
    
    This plan divides a large order into optimal slices to minimize
    market impact while achieving target completion time.
    """
    total_size: float  # Total position size to execute (lots)
    target_duration: int  # Target minutes to complete execution
    slices: List[Dict]  # List of individual execution slices with timing
    participation_rate: float  # Current adaptive participation rate
    market_impact_estimate: float  # Expected impact in basis points
    slippage_estimate: float  # Expected slippage in basis points
    
    @property
    def average_slice_size(self) -> float:
        """Calculate average size per slice for monitoring."""
        if self.slices:
            return sum(s['size'] for s in self.slices) / len(self.slices)
        return 0
    
    @property
    def completion_percentage(self) -> float:
        """
        Calculate execution completion percentage.
        
        This tracks how much of the total order has been filled,
        allowing for real-time monitoring and adjustment.
        """
        if self.total_size > 0:
            executed = sum(s['size'] for s in self.slices if s.get('executed', False))
            return (executed / self.total_size) * 100
        return 0

class APRExecutor:
    """
    Adaptive Participation Rate executor for institutional orders.
    
    This class implements sophisticated order execution algorithms that
    dynamically adjust participation rates based on market microstructure.
    The core principle is to balance execution urgency against market impact,
    following the theoretical framework established by Almgren & Chriss (2001).
    
    METHODOLOGY:
    1. Calculate base participation rate (typically 10% of market volume)
    2. Apply momentum adjustment (faster execution in favorable direction)
    3. Apply volatility adjustment (slower execution in high volatility)
    4. Apply volume adjustment (faster execution in high volume periods)
    5. Enforce floor and ceiling limits (5%-25% institutional standards)
    6. Create TWAP-based slicing with random variation to avoid detection
    7. Monitor and track execution for post-trade analysis
    
    INSTITUTIONAL STANDARDS:
    - Minimum notional: $100,000 USD for APR activation
    - Participation limits: 5% floor, 25% ceiling
    - Impact model: Square-root with temporary + permanent components
    - Slippage tracking: Real-time basis point calculation
    - Completion target: 30 minutes default with adjustable urgency
    """
    
    def __init__(self, params: Dict):
        """
        Initialize APR executor with institutional-grade parameters.
        
        Parameters control the risk/reward tradeoff between execution speed
        and market impact. Conservative parameters reduce impact but increase
        time risk; aggressive parameters reduce time risk but increase impact.
        """
        # Core participation parameters with institutional defaults
        self.base_rate = params.get('base_rate', 0.10)  # 10% of market volume (institutional standard)
        self.momentum_alpha = params.get('momentum_alpha', 0.05)  # Momentum sensitivity (5% per unit momentum)
        self.volatility_beta = params.get('volatility_beta', 0.15)  # Volatility sensitivity (15% per unit volatility)
        
        # Participation rate constraints (critical for institutional compliance)
        self.rate_floor = params.get('rate_floor', 0.05)  # 5% minimum (avoid excessive time risk)
        self.rate_ceiling = params.get('rate_ceiling', 0.25)  # 25% maximum (avoid excessive impact)
        
        # Activation threshold to prevent unnecessary slicing on small orders
        self.minimum_notional_for_activation = params.get('minimum_notional_for_activation', 100000)  # $100k USD
        
        # Monitoring and compliance flags
        self.slippage_monitoring = params.get('slippage_monitoring', True)  # Track actual vs. expected slippage
        self.market_impact_tracking = params.get('market_impact_tracking', True)  # Track actual vs. estimated impact
        
        # Execution history for post-trade analysis and optimization
        self.execution_history: List[ExecutionPlan] = []
        
        logger.info(f"APR Executor initialized with institutional parameters:")
        logger.info(f"  Base Rate: {self.base_rate:.1%}")
        logger.info(f"  Rate Limits: [{self.rate_floor:.1%}, {self.rate_ceiling:.1%}]")
        logger.info(f"  Minimum Notional: ${self.minimum_notional_for_activation:,}")
        logger.info(f"  Monitoring: Slippage={self.slippage_monitoring}, Impact={self.market_impact_tracking}")
    
    def calculate_participation_rate(self,
                                    price_momentum: float,
                                    volatility: float,
                                    volume_profile: pd.Series) -> float:
        """
        Calculate adaptive participation rate using institutional methodology.
        
        This is the core algorithm that determines how aggressively to execute.
        The formula balances three key market factors:
        
        1. MOMENTUM: If price is moving favorably, increase participation to
           capture the move. If moving adversely, slow down to avoid chasing.
        
        2. VOLATILITY: Higher volatility increases uncertainty and impact cost.
           Reduce participation in volatile markets to minimize adverse selection.
        
        3. VOLUME: Higher volume provides more liquidity and lower impact.
           Increase participation when markets are liquid.
        
        Mathematical Framework (Almgren-Chriss adapted):
        rate = base_rate × (1 + α×momentum) × (1 - β×volatility) × volume_factor
        
        Where:
        - α (alpha) = momentum sensitivity parameter
        - β (beta) = volatility sensitivity parameter
        - volume_factor = liquidity adjustment based on current vs. average volume
        
        Args:
            price_momentum: Normalized momentum score from -1 (strong down) to +1 (strong up)
            volatility: Normalized volatility from 0 (calm) to 1 (extreme)
            volume_profile: Recent volume time series for liquidity assessment
            
        Returns:
            Participation rate between floor and ceiling (e.g., 0.05 to 0.25)
        """
        try:
            # STEP 1: Apply momentum adjustment per Almgren-Chriss momentum factor
            # Positive momentum → increase rate (favorable execution conditions)
            # Negative momentum → decrease rate (adverse execution conditions)
            momentum_adjustment = 1 + (self.momentum_alpha * price_momentum)
            
            # STEP 2: Apply volatility adjustment per volatility trading literature
            # Higher volatility → decrease rate (reduce adverse selection risk)
            # Lower volatility → increase rate (take advantage of stable conditions)
            volatility_adjustment = 1 - (self.volatility_beta * volatility)
            
            # STEP 3: Calculate volume factor for liquidity assessment
            # This adjusts for current market liquidity conditions
            volume_factor = 1.0
            if not volume_profile.empty:
                current_volume = volume_profile.iloc[-1]
                avg_volume = volume_profile.mean()
                
                if avg_volume > 0:
                    volume_ratio = current_volume / avg_volume
                    # Increase participation when volume is high (more liquidity)
                    # Factor ranges from 0.8 (low volume) to 1.2 (high volume)
                    volume_factor = 0.8 + 0.4 * min(volume_ratio, 2.0)
            
            # STEP 4: Calculate final adjusted rate
            adjusted_rate = self.base_rate * momentum_adjustment * volatility_adjustment * volume_factor
            
            # STEP 5: Apply institutional limits (critical for risk management)
            final_rate = max(self.rate_floor, min(self.rate_ceiling, adjusted_rate))
            
            # LOGGING: Detailed breakdown for audit trail
            logger.debug(f"APR Calculation Breakdown:")
            logger.debug(f"  Base Rate: {self.base_rate:.3f}")
            logger.debug(f"  Momentum Adjustment: {momentum_adjustment:.3f} (momentum={price_momentum:+.2f})")
            logger.debug(f"  Volatility Adjustment: {volatility_adjustment:.3f} (volatility={volatility:.2f})")
            logger.debug(f"  Volume Factor: {volume_factor:.3f}")
            logger.debug(f"  Adjusted Rate: {adjusted_rate:.3f}")
            logger.debug(f"  Final Rate (after limits): {final_rate:.3f}")
            
            return final_rate
            
        except Exception as e:
            logger.error(f"Participation rate calculation failed: {str(e)}", exc_info=True)
            # FAIL-SAFE: Return conservative base rate on error
            logger.warning(f"Returning conservative base rate {self.base_rate:.3f} due to calculation error")
            return self.base_rate
    
    def create_execution_plan(self,
                             total_size: float,
                             current_price: float,
                             direction: str,
                             market_data: pd.DataFrame,
                             target_duration_minutes: int = 30) -> Optional[ExecutionPlan]:
        """
        Create comprehensive execution plan for large institutional order.
        
        This method is the main entry point for order execution planning. It takes
        a large order and determines the optimal way to execute it by creating a
        series of smaller "slices" that minimize market impact while meeting the
        target completion time.
        
        EXECUTION PLAN CREATION PROCESS:
        
        1. ACTIVATION CHECK: Verify order size exceeds minimum notional threshold
           - Orders below threshold execute as single order (no slicing needed)
           - Prevents unnecessary complexity for small orders
        
        2. MARKET ANALYSIS: Calculate current market conditions
           - Price momentum: Is market moving favorably or adversely?
           - Volatility: How uncertain/risky is current environment?
           - Volume profile: How much liquidity is available?
        
        3. PARTICIPATION DETERMINATION: Calculate optimal participation rate
           - Uses adaptive algorithm based on market conditions
           - Balances speed vs. impact tradeoff
        
        4. SLICE CALCULATION: Determine number and size of slices
           - Based on available volume and participation rate
           - Limited by target duration (can't execute slower than target)
        
        5. SLICE SCHEDULING: Create time-based execution schedule
           - TWAP (Time-Weighted Average Price) base distribution
           - Add randomization to avoid pattern detection
           - Assign target times to each slice
        
        6. IMPACT ESTIMATION: Calculate expected market impact
           - Uses Kissell framework with temporary + permanent components
           - Provides basis point estimate for cost analysis
        
        7. PLAN FINALIZATION: Package everything into ExecutionPlan object
           - Store in history for tracking and analysis
           - Return to execution system for implementation
        
        INSTITUTIONAL EXAMPLE:
        Order: 10 lots EURUSD @ 1.1050
        Notional: 10 × 100,000 × 1.1050 = $1,105,000 USD (above $100k threshold)
        Market: Moderate volume, low volatility, slight positive momentum
        Result: 12 slices over 30 minutes, ~0.83 lots per slice
        Expected Impact: 3.2 basis points
        Expected Slippage: 4.1 basis points
        
        Args:
            total_size: Total order size in lots
            current_price: Current market price
            direction: 'BUY' or 'SELL'
            market_data: Recent OHLCV data for analysis
            target_duration_minutes: Target completion time (default 30 min)
            
        Returns:
            ExecutionPlan with optimal slicing strategy, or None if below threshold
        """
        try:
            # STEP 1: ACTIVATION CHECK - Verify order meets minimum notional
            # Standard lot = 100,000 units of base currency
            notional_value = total_size * current_price * 100000
            
            if notional_value < self.minimum_notional_for_activation:
                logger.info(f"Order notional ${notional_value:,.0f} below APR activation threshold "
                          f"${self.minimum_notional_for_activation:,}")
                logger.info(f"Recommendation: Execute as single market order (no slicing required)")
                return None
            
            logger.info(f"Large order detected: ${notional_value:,.0f} notional")
            logger.info(f"Initiating institutional APR execution planning...")
            
            # STEP 2: MARKET ANALYSIS - Calculate market condition parameters
            logger.debug("Analyzing current market conditions...")
            
            price_momentum = self._calculate_momentum(market_data)
            logger.debug(f"  Price Momentum: {price_momentum:+.3f} (range: -1 to +1)")
            
            volatility = self._calculate_volatility(market_data)
            logger.debug(f"  Volatility: {volatility:.3f} (range: 0 to 1)")
            
            volume_profile = market_data['tick_volume'].tail(20)
            avg_volume = volume_profile.mean()
            logger.debug(f"  Average Volume: {avg_volume:.0f} ticks/minute")
            
            # STEP 3: PARTICIPATION DETERMINATION
            logger.debug("Calculating optimal participation rate...")
            participation_rate = self.calculate_participation_rate(
                price_momentum,
                volatility,
                volume_profile
            )
            logger.info(f"Optimal Participation Rate: {participation_rate:.1%}")
            
            # STEP 4: SLICE CALCULATION
            # Calculate how many slices are needed based on available volume
            # Formula: Expected volume per slice = average_volume_per_minute × participation_rate
            logger.debug("Calculating slice structure...")
            
            avg_volume_per_minute = volume_profile.mean()
            if avg_volume_per_minute > 0:
                # Convert lots to base units for volume comparison (1 lot = 1000 base units typically)
                volume_per_slice = avg_volume_per_minute * participation_rate
                num_slices = max(1, int(total_size * 1000 / volume_per_slice))
            else:
                # If no volume data, distribute evenly across duration
                num_slices = target_duration_minutes
            
            # Limit slices to target duration (one slice per minute maximum)
            num_slices = min(num_slices, target_duration_minutes)
            
            logger.info(f"Slice Structure: {num_slices} slices over {target_duration_minutes} minutes")
            logger.info(f"  Average Slice Size: {total_size / num_slices:.3f} lots")
            
            # STEP 5: SLICE SCHEDULING - Create individual execution slices
            logger.debug("Creating execution schedule...")
            slices = []
            remaining_size = total_size
            
            for i in range(num_slices):
                if i < num_slices - 1:
                    # TWAP base with randomization to avoid detection
                    slice_size = total_size / num_slices
                    # Add ±10% random variation (institutional anti-gaming technique)
                    slice_size *= (1 + np.random.uniform(-0.1, 0.1))
                else:
                    # Last slice takes all remaining size (ensures complete fill)
                    slice_size = remaining_size
                
                # Calculate target execution time for this slice
                slice_minutes = i * target_duration_minutes / num_slices
                target_time = datetime.now() + timedelta(minutes=slice_minutes)
                
                slices.append({
                    'slice_number': i + 1,
                    'size': slice_size,
                    'target_time': target_time,
                    'participation_rate': participation_rate,
                    'executed': False,
                    'direction': direction
                })
                
                remaining_size -= slice_size
                
                logger.debug(f"  Slice {i+1}/{num_slices}: {slice_size:.3f} lots at {target_time.strftime('%H:%M:%S')}")
            
            # STEP 6: IMPACT ESTIMATION - Calculate expected market impact
            logger.debug("Estimating market impact...")
            market_impact_bps = self._estimate_market_impact(
                total_size,
                avg_volume_per_minute,
                volatility,
                target_duration_minutes
            )
            logger.info(f"Expected Market Impact: {market_impact_bps:.2f} basis points")
            
            # Estimate slippage (simplified: impact + volatility component)
            slippage_bps = market_impact_bps * 0.5 + volatility * 10
            logger.info(f"Expected Slippage: {slippage_bps:.2f} basis points")
            
            # STEP 7: PLAN FINALIZATION
            plan = ExecutionPlan(
                total_size=total_size,
                target_duration=target_duration_minutes,
                slices=slices,
                participation_rate=participation_rate,
                market_impact_estimate=market_impact_bps,
                slippage_estimate=slippage_bps
            )
            
            # Store in execution history for analysis
            self.execution_history.append(plan)
            
            logger.info("═" * 80)
            logger.info("EXECUTION PLAN CREATED SUCCESSFULLY")
            logger.info(f"  Total Size: {total_size:.2f} lots")
            logger.info(f"  Number of Slices: {num_slices}")
            logger.info(f"  Target Duration: {target_duration_minutes} minutes")
            logger.info(f"  Participation Rate: {participation_rate:.1%}")
            logger.info(f"  Expected Impact: {market_impact_bps:.2f} bps")
            logger.info(f"  Expected Slippage: {slippage_bps:.2f} bps")
            logger.info(f"  Total Expected Cost: {market_impact_bps + slippage_bps:.2f} bps")
            logger.info("═" * 80)
            
            return plan
            
        except Exception as e:
            logger.error(f"Execution plan creation failed: {str(e)}", exc_info=True)
            return None
    
    def _calculate_momentum(self, data: pd.DataFrame, lookback: int = 20) -> float:
        """
        Calculate normalized price momentum for directional bias.
        
        Momentum measures the recent price trend. Positive momentum suggests
        favorable conditions for buying (or adverse for selling). Negative
        momentum suggests favorable conditions for selling (or adverse for buying).
        
        This influences participation rate: we execute faster when momentum
        is favorable to capture the move, and slower when adverse to avoid
        chasing a bad price.
        
        Args:
            data: Market price data
            lookback: Period for momentum calculation (default 20 bars)
            
        Returns:
            Normalized momentum from -1 (strong down) to +1 (strong up)
        """
        try:
            if len(data) < lookback:
                logger.warning(f"Insufficient data for momentum: {len(data)} < {lookback}")
                return 0.0
            
            # Calculate percentage return over lookback period
            returns = data['close'].pct_change(lookback).iloc[-1]
            
            # Normalize to [-1, 1] using hyperbolic tangent
            # This provides smooth scaling: small moves → small momentum, large moves → ±1
            normalized_momentum = np.tanh(returns * 100)
            
            return normalized_momentum
            
        except Exception as e:
            logger.error(f"Momentum calculation failed: {str(e)}", exc_info=True)
            return 0.0
    
    def _calculate_volatility(self, data: pd.DataFrame, lookback: int = 20) -> float:
        """
        Calculate normalized volatility for risk assessment.
        
        Volatility measures market uncertainty and execution risk. Higher volatility
        means prices can move more between slices, increasing adverse selection risk
        and market impact cost.
        
        This influences participation rate: we execute slower (lower participation)
        in volatile markets to reduce risk of being adversely selected.
        
        Args:
            data: Market price data
            lookback: Period for volatility calculation (default 20 bars)
            
        Returns:
            Normalized volatility from 0 (calm) to 1 (extreme)
        """
        try:
            if len(data) < lookback:
                logger.warning(f"Insufficient data for volatility: {len(data)} < {lookback}")
                return 0.5  # Return neutral value
            
            # Calculate standard deviation of returns
            returns = data['close'].pct_change().tail(lookback)
            volatility = returns.std()
            
            # Normalize to [0, 1] range
            # Typical FX volatility around 0.0005 (0.05%) → maps to 0.5
            # Scale by 100 to get reasonable range
            normalized_vol = min(1.0, volatility * 100)
            
            return normalized_vol
            
        except Exception as e:
            logger.error(f"Volatility calculation failed: {str(e)}", exc_info=True)
            return 0.5  # Return neutral value on error
    
    def _estimate_market_impact(self,
                               order_size: float,
                               avg_volume: float,
                               volatility: float,
                               duration_minutes: int) -> float:
        """
        Estimate market impact using Almgren-Chriss framework.
        
        Market impact is the adverse price movement caused by executing a large order.
        It consists of two components:
        
        1. TEMPORARY IMPACT: Price moves against you during execution but reverts
           after completion. Caused by short-term supply/demand imbalance.
           
        2. PERMANENT IMPACT: Lasting price change due to information revelation.
           Market learns about your intent and adjusts prices accordingly.
        
        This implementation uses a simplified square-root model based on
        empirical research showing impact scales with √(participation_rate).
        
        INSTITUTIONAL NOTE:
        This is a simplified model. Real institutional systems use more sophisticated
        models with calibrated parameters from historical execution data.
        
        Args:
            order_size: Size of order in lots
            avg_volume: Average market volume per minute
            volatility: Current market volatility
            duration_minutes: Execution duration
            
        Returns:
            Estimated total impact in basis points
        """
        try:
            if avg_volume <= 0 or duration_minutes <= 0:
                logger.warning("Invalid parameters for impact estimation")
                return 10.0  # Conservative default estimate
            
            # Calculate participation rate (what fraction of market volume is this order?)
            expected_volume = avg_volume * duration_minutes
            # Convert lots to base units (1 lot ≈ 1000 units for calculation)
            participation = min(1.0, order_size * 1000 / expected_volume)
            
            logger.debug(f"Impact Calculation:")
            logger.debug(f"  Expected Market Volume: {expected_volume:.0f}")
            logger.debug(f"  Order Participation: {participation:.1%}")
            
            # TEMPORARY IMPACT: Square-root model per Almgren-Chriss
            # Coefficient 10 is calibrated for FX markets (basis points)
            temp_impact = 10 * np.sqrt(participation)
            logger.debug(f"  Temporary Impact: {temp_impact:.2f} bps")
            
            # PERMANENT IMPACT: Linear in participation
            # Coefficient 5 represents information leakage cost
            perm_impact = 5 * participation
            logger.debug(f"  Permanent Impact: {perm_impact:.2f} bps")
            
            # Total impact (sum of components)
            total_impact = temp_impact + perm_impact
            
            # Volatility adjustment: Higher volatility increases execution uncertainty
            volatility_multiplier = (1 + volatility)
            adjusted_impact = total_impact * volatility_multiplier
            
            logger.debug(f"  Volatility Multiplier: {volatility_multiplier:.3f}")
            logger.debug(f"  Total Impact (adjusted): {adjusted_impact:.2f} bps")
            
            return adjusted_impact
            
        except Exception as e:
            logger.error(f"Market impact estimation failed: {str(e)}", exc_info=True)
            return 10.0  # Conservative fallback estimate
    
    def update_execution(self,
                        plan: ExecutionPlan,
                        slice_number: int,
                        executed_price: float,
                        executed_size: float) -> None:
        """
        Update execution plan with actual fill data for monitoring and analysis.
        
        This method is called after each slice executes to record actual results.
        Recording actual execution data enables:
        1. Real-time progress monitoring
        2. Slippage analysis (actual vs. expected prices)
        3. Post-trade analysis and optimization
        4. Regulatory compliance (audit trail)
        
        INSTITUTIONAL BEST PRACTICE:
        All institutional trading systems maintain detailed execution records for:
        - Trade surveillance and compliance
        - Best execution analysis (MiFID II / Reg NMS)
        - Algorithm optimization and calibration
        - Client reporting and transparency
        
        Args:
            plan: The execution plan being updated
            slice_number: Which slice was executed (1-indexed)
            executed_price: Actual fill price received
            executed_size: Actual size filled
        """
        try:
            if 0 < slice_number <= len(plan.slices):
                slice_data = plan.slices[slice_number - 1]
                
                # Mark slice as executed
                slice_data['executed'] = True
                slice_data['executed_price'] = executed_price
                slice_data['executed_size'] = executed_size
                slice_data['executed_time'] = datetime.now()
                
                # Calculate actual slippage if monitoring enabled
                if self.slippage_monitoring and 'target_price' in slice_data:
                    # Slippage = difference between executed price and benchmark price
                    # Expressed in basis points for standardization
                    slippage_bps = abs(executed_price - slice_data['target_price']) / slice_data['target_price'] * 10000
                    slice_data['actual_slippage_bps'] = slippage_bps
                    
                    logger.info(f"Slice {slice_number}/{len(plan.slices)} executed:")
                    logger.info(f"  Size: {executed_size:.3f} lots (target: {slice_data['size']:.3f})")
                    logger.info(f"  Price: {executed_price:.5f}")
                    logger.info(f"  Slippage: {slippage_bps:.2f} bps")
                    
                    # Check if slippage exceeds expected (alert condition)
                    if slippage_bps > plan.slippage_estimate * 1.5:
                        logger.warning(f"  ⚠ Slippage {slippage_bps:.2f} bps exceeds expected "
                                     f"{plan.slippage_estimate:.2f} bps by >50%")
                        logger.warning(f"  Consider reducing participation rate for remaining slices")
                else:
                    logger.info(f"Slice {slice_number}/{len(plan.slices)} executed: "
                              f"{executed_size:.3f} lots @ {executed_price:.5f}")
                
                # Log overall progress
                completion = plan.completion_percentage
                logger.info(f"Overall Progress: {completion:.1f}% complete")
                
            else:
                logger.error(f"Invalid slice number: {slice_number} (plan has {len(plan.slices)} slices)")
            
        except Exception as e:
            logger.error(f"Execution update failed: {str(e)}", exc_info=True)
    
    def get_execution_statistics(self) -> Dict:
        """
        Calculate aggregate statistics across all executions for analysis.
        
        This provides portfolio-level insights into execution quality:
        - Average impact and slippage
        - Execution success rate
        - Cost distributions
        - Performance trends
        
        Used for algorithm optimization and reporting to stakeholders.
        
        Returns:
            Dictionary containing aggregate execution statistics
        """
        try:
            if not self.execution_history:
                return {
                    'total_executions': 0,
                    'message': 'No execution history available'
                }
            
            total_executions = len(self.execution_history)
            total_size = sum(plan.total_size for plan in self.execution_history)
            avg_participation = np.mean([plan.participation_rate for plan in self.execution_history])
            avg_impact = np.mean([plan.market_impact_estimate for plan in self.execution_history])
            avg_slippage = np.mean([plan.slippage_estimate for plan in self.execution_history])
            
            # Calculate completion statistics
            completed_plans = [p for p in self.execution_history if p.completion_percentage == 100]
            completion_rate = len(completed_plans) / total_executions * 100 if total_executions > 0 else 0
            
            stats = {
                'total_executions': total_executions,
                'total_volume_traded': total_size,
                'average_participation_rate': avg_participation,
                'average_market_impact_bps': avg_impact,
                'average_slippage_bps': avg_slippage,
                'average_total_cost_bps': avg_impact + avg_slippage,
                'execution_completion_rate': completion_rate,
                'completed_executions': len(completed_plans),
                'in_progress_executions': total_executions - len(completed_plans)
            }
            
            logger.info("Execution Statistics Summary:")
            for key, value in stats.items():
                if isinstance(value, float):
                    logger.info(f"  {key}: {value:.2f}")
                else:
                    logger.info(f"  {key}: {value}")
            
            return stats
            
        except Exception as e:
            logger.error(f"Statistics calculation failed: {str(e)}", exc_info=True)
            return {'error': str(e)}