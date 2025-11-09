-- Circuit Breakers Table
CREATE TABLE IF NOT EXISTS circuit_breakers (
    breaker_id VARCHAR(50) PRIMARY KEY,
    breaker_type VARCHAR(50) NOT NULL,
    threshold_value NUMERIC(10,2) NOT NULL,
    is_active BOOLEAN DEFAULT FALSE,
    activated_at TIMESTAMP,
    deactivated_at TIMESTAMP,
    activation_count INTEGER DEFAULT 0,
    description TEXT,
    severity_level INTEGER NOT NULL,
    action_required VARCHAR(100) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Index for quick lookup of active breakers
CREATE INDEX IF NOT EXISTS idx_circuit_breakers_active 
ON circuit_breakers(is_active, severity_level);

-- Insert standard circuit breaker configurations
INSERT INTO circuit_breakers (breaker_id, breaker_type, threshold_value, severity_level, action_required, description)
VALUES 
    ('DD_INTRADAY_5PCT', 'DRAWDOWN_INTRADAY', 5.0, 1, 'REDUCE_SIZING_20PCT', 'Reduce position sizing by 20% when intraday drawdown exceeds 5%'),
    ('DD_INTRADAY_10PCT', 'DRAWDOWN_INTRADAY', 10.0, 2, 'REDUCE_SIZING_40PCT', 'Reduce position sizing by 40% when intraday drawdown exceeds 10%'),
    ('DD_INTRADAY_20PCT', 'DRAWDOWN_INTRADAY', 20.0, 3, 'REDUCE_SIZING_60PCT', 'Reduce position sizing by 60% when intraday drawdown exceeds 20%'),
    ('DD_INTRADAY_30PCT', 'DRAWDOWN_INTRADAY', 30.0, 4, 'REDUCE_SIZING_80PCT', 'Reduce position sizing by 80% when intraday drawdown exceeds 30%'),
    ('DD_INTRADAY_40PCT', 'DRAWDOWN_INTRADAY', 40.0, 5, 'HALT_TRADING', 'Halt all trading when intraday drawdown exceeds 40%'),
    ('VOLATILITY_EXTREME', 'VOLATILITY_SPIKE', 300.0, 3, 'PAUSE_NEW_SIGNALS', 'Pause new signals when volatility exceeds 3x historical average'),
    ('SPREAD_WIDENING', 'SPREAD_ANOMALY', 500.0, 2, 'REDUCE_SIZING_30PCT', 'Reduce sizing when spreads widen beyond 5x normal'),
    ('CONSECUTIVE_LOSSES', 'LOSS_STREAK', 10.0, 2, 'REDUCE_SIZING_50PCT', 'Reduce sizing after 10 consecutive losing trades')
ON CONFLICT (breaker_id) DO NOTHING;

-- Equity tracking table for drawdown calculation
CREATE TABLE IF NOT EXISTS equity_tracking (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMP NOT NULL,
    account_balance NUMERIC(12,2) NOT NULL,
    unrealized_pnl NUMERIC(12,2) NOT NULL,
    total_equity NUMERIC(12,2) NOT NULL,
    equity_peak NUMERIC(12,2) NOT NULL,
    drawdown_amount NUMERIC(12,2) NOT NULL,
    drawdown_percent NUMERIC(8,4) NOT NULL,
    daily_start_equity NUMERIC(12,2),
    intraday_drawdown_percent NUMERIC(8,4),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_equity_tracking_timestamp 
ON equity_tracking(timestamp DESC);

-- Circuit breaker activation log
CREATE TABLE IF NOT EXISTS circuit_breaker_activations (
    id SERIAL PRIMARY KEY,
    breaker_id VARCHAR(50) NOT NULL,
    activated_at TIMESTAMP NOT NULL,
    trigger_value NUMERIC(12,4) NOT NULL,
    threshold_value NUMERIC(12,4) NOT NULL,
    action_taken VARCHAR(100) NOT NULL,
    deactivated_at TIMESTAMP,
    duration_minutes INTEGER,
    notes TEXT,
    FOREIGN KEY (breaker_id) REFERENCES circuit_breakers(breaker_id)
);

CREATE INDEX IF NOT EXISTS idx_breaker_activations_time 
ON circuit_breaker_activations(activated_at DESC);
