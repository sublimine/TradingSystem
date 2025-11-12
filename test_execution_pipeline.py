"""Test de ejecuciÃ³n con todos los componentes."""
import pandas as pd
from execution import (
    BrokerClient, OrderType, OrderSide,
    LPAnalytics, TCAEngine,
    CircuitBreakerManager, VenueSimulator, CapacityModel
)

print("=== EXECUTION PIPELINE TEST ===\n")

# Cargar datos de EURUSD
df = pd.read_csv(
    "backtest/datasets/EURUSD_pro_synthetic.csv",
    parse_dates=['timestamp'],
    index_col='timestamp'
)

# Inicializar componentes
print("Initializing components...")

broker = BrokerClient(
    broker_name="TestBroker",
    account_id="TEST123"
)
broker.connect()

lp_analytics = LPAnalytics(window_size=100)
tca_engine = TCAEngine()

circuit_breakers = CircuitBreakerManager(
    total_capital=10000.0,
    max_daily_loss_pct=0.02
)

venue_sim = VenueSimulator(
    venue_name="PrimeLP",
    base_fill_probability=0.95
)

capacity_model = CapacityModel()

print("âœ“ Components initialized\n")

# Simular 10 trades
print("Simulating 10 trades...\n")

for i in range(10):
    bar = df.iloc[i * 100]  # Cada 100 barras
    
    instrument = 'EURUSD.pro'
    side = OrderSide.BUY if i % 2 == 0 else OrderSide.SELL
    size = 1.0
    mid_price = (bar['bid'] + bar['ask']) / 2
    
    # Check capacity
    is_allowed, reason = capacity_model.check_capacity_constraint(
        instrument, size, bar.name.hour
    )
    
    if not is_allowed:
        print(f"Trade {i+1}: REJECTED - {reason}")
        continue
    
    # Check circuit breakers
    allowed, tripped = circuit_breakers.check_all(
        current_pnl=0.0,
        current_exposure=size * 100000 * 0.01,
        clock_skew_seconds=0.001
    )
    
    if not allowed:
        print(f"Trade {i+1}: BLOCKED - Circuit breaker: {tripped}")
        continue
    
    # Simulate venue execution
    execution_result = venue_sim.simulate_execution(
        instrument=instrument,
        side=side.value,
        order_size=size,
        mid_at_send=mid_price,
        volatility=0.0001
    )
    
    if execution_result['is_filled']:
        # Place order with broker
        order = broker.place_order(
            instrument=instrument,
            side=side,
            volume=size,
            order_type=OrderType.MARKET,
            mid_at_send=mid_price
        )
        
        # Record LP analytics
        lp_analytics.record_order_sent("PrimeLP", instrument, size, mid_price)
        lp_analytics.record_order_filled(
            "PrimeLP", instrument, size,
            execution_result['hold_time_ms'],
            mid_price,
            execution_result['mid_at_fill'],
            execution_result['fill_price'],
            side.value
        )
        
        # TCA analysis
        tca_result = tca_engine.analyze_at_trade(
            order_id=order.order_id,
            instrument=instrument,
            side=side.value,
            order_size=size,
            mid_at_decision=mid_price,
            mid_at_send=mid_price,
            mid_at_fill=execution_result['mid_at_fill'],
            fill_price=execution_result['fill_price'],
            hold_time_ms=execution_result['hold_time_ms']
        )
        
        print(f"Trade {i+1}: FILLED")
        print(f"  Price: {execution_result['fill_price']:.5f}")
        print(f"  Hold time: {execution_result['hold_time_ms']:.1f}ms")
        print(f"  Total cost: {tca_result.total_cost_bps:.2f} bps")
        
        circuit_breakers.record_order_sent()
    else:
        print(f"Trade {i+1}: REJECTED - {execution_result['reject_reason']}")
        circuit_breakers.record_order_sent()
        circuit_breakers.record_order_rejected()
        lp_analytics.record_order_rejected("PrimeLP", instrument, size, "venue_reject")

print("\n=== STATISTICS ===")
print("\nBroker:")
print(f"  {broker.get_statistics()}")

print("\nLP Analytics:")
lp_report = lp_analytics.get_lp_report("PrimeLP")
print(f"  Fill rate: {lp_report['fill_probability_pct']:.1f}%")
print(f"  Avg hold time: {lp_report['avg_hold_time_ms']:.1f}ms")
print(f"  LP score: {lp_report['overall_score']:.1f}/100")

print("\nTCA:")
print(f"  {tca_engine.get_statistics()}")

print("\nCircuit Breakers:")
print(f"  {circuit_breakers.get_status()}")

broker.disconnect()

print("\nâœ“ Execution pipeline test complete\n")