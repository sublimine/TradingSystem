-- =====================================================
-- TRADING SYSTEM DATABASE SCHEMA
-- Complete institutional-grade schema for algorithmic trading
-- =====================================================

-- Drop existing tables if they exist (careful in production!)
DROP TABLE IF EXISTS circuit_breaker_activations CASCADE;
DROP TABLE IF EXISTS circuit_breakers CASCADE;
DROP TABLE IF EXISTS equity_tracking CASCADE;
DROP TABLE IF EXISTS rejected_signals CASCADE;
DROP TABLE IF EXISTS signals CASCADE;
DROP TABLE IF EXISTS trades CASCADE;
DROP TABLE IF EXISTS system_metrics CASCADE;

-- =====================================================
-- TRADES TABLE
-- Stores executed trades with complete lifecycle tracking
-- =====================================================
CREATE TABLE trades (
    trade_id SERIAL PRIMARY KEY,
    ticket BIGINT UNIQUE,
    symbol VARCHAR(20) NOT NULL,
    trade_direction VARCHAR(10) NOT NULL CHECK (trade_direction IN ('LONG', 'SHORT')),
    entry_price NUMERIC(12,5) NOT NULL,
    exit_price NUMERIC(12,5),
    trade_volume NUMERIC(10,2) NOT NULL CHECK (trade_volume > 0),
    stop_loss NUMERIC(12,5) NOT NULL,
    take_profit NUMERIC(12,5) NOT NULL,
    entry_time TIMESTAMP NOT NULL,
    exit_time TIMESTAMP,
    trade_status VARCHAR(20) NOT NULL DEFAULT 'open' 
        CHECK (trade_status IN ('open', 'closed', 'cancelled')),
    profit_loss NUMERIC(12,2),
    commission NUMERIC(10,2) DEFAULT 0,
    swap NUMERIC(10,2) DEFAULT 0,
    slippage_pips NUMERIC(8,2),
    strategy_name VARCHAR(100) NOT NULL,
    signal_id INTEGER,
    exit_reason VARCHAR(50),
    metadata JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_trades_symbol ON trades(symbol);
CREATE INDEX idx_trades_status ON trades(trade_status);
CREATE INDEX idx_trades_entry_time ON trades(entry_time DESC);
CREATE INDEX idx_trades_strategy ON trades(strategy_name);
CREATE INDEX idx_trades_symbol_status ON trades(symbol, trade_status);

-- =====================================================
-- SIGNALS TABLE
-- Stores trading signals awaiting execution
-- =====================================================
CREATE TABLE signals (
    signal_id SERIAL PRIMARY KEY,
    timestamp TIMESTAMP NOT NULL,
    symbol VARCHAR(20) NOT NULL,
    strategy VARCHAR(100) NOT NULL,
    signal_direction VARCHAR(10) NOT NULL CHECK (signal_direction IN ('LONG', 'SHORT')),
    entry_price NUMERIC(12,5) NOT NULL,
    stop_loss NUMERIC(12,5) NOT NULL,
    take_profit NUMERIC(12,5) NOT NULL,
    signal_volume NUMERIC(10,2) NOT NULL CHECK (signal_volume > 0),
    sizing_level INTEGER NOT NULL CHECK (sizing_level BETWEEN 1 AND 5),
    signal_status VARCHAR(20) NOT NULL DEFAULT 'pending'
        CHECK (signal_status IN ('pending', 'transmitted', 'executed', 'rejected', 'cancelled')),
    metadata JSONB,
    approved_at TIMESTAMP,
    executed_at TIMESTAMP,
    rejection_reason VARCHAR(200),
    ticket BIGINT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(timestamp, symbol, strategy, signal_direction)
);

CREATE INDEX idx_signals_status ON signals(signal_status);
CREATE INDEX idx_signals_timestamp ON signals(timestamp DESC);
CREATE INDEX idx_signals_symbol ON signals(symbol);
CREATE INDEX idx_signals_status_timestamp ON signals(signal_status, timestamp);

-- =====================================================
-- REJECTED SIGNALS TABLE
-- Audit trail of rejected signals with detailed reasons
-- =====================================================
CREATE TABLE rejected_signals (
    rejection_id SERIAL PRIMARY KEY,
    timestamp TIMESTAMP NOT NULL,
    symbol VARCHAR(20) NOT NULL,
    strategy VARCHAR(100) NOT NULL,
    signal_direction VARCHAR(10) NOT NULL,
    entry_price NUMERIC(12,5) NOT NULL,
    rejection_reason VARCHAR(200) NOT NULL,
    rejection_details JSONB,
    account_balance NUMERIC(12,2),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_rejected_signals_timestamp ON rejected_signals(timestamp DESC);
CREATE INDEX idx_rejected_signals_reason ON rejected_signals(rejection_reason);

-- =====================================================
-- CIRCUIT BREAKERS TABLE
-- Configuration and status of circuit breakers
-- =====================================================
CREATE TABLE circuit_breakers (
    breaker_id VARCHAR(50) PRIMARY KEY,
    breaker_type VARCHAR(50) NOT NULL,
    threshold_value NUMERIC(10,2) NOT NULL,
    is_active BOOLEAN DEFAULT FALSE,
    activated_at TIMESTAMP,
    deactivated_at TIMESTAMP,
    activation_count INTEGER DEFAULT 0,
    description TEXT,
    severity_level INTEGER NOT NULL CHECK (severity_level BETWEEN 1 AND 5),
    action_required VARCHAR(100) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_circuit_breakers_active ON circuit_breakers(is_active, severity_level);

-- =====================================================
-- CIRCUIT BREAKER ACTIVATIONS TABLE
-- Historical log of breaker activations
-- =====================================================
CREATE TABLE circuit_breaker_activations (
    activation_id SERIAL PRIMARY KEY,
    breaker_id VARCHAR(50) NOT NULL,
    activated_at TIMESTAMP NOT NULL,
    trigger_value NUMERIC(12,4) NOT NULL,
    threshold_value NUMERIC(12,4) NOT NULL,
    action_taken VARCHAR(100) NOT NULL,
    deactivated_at TIMESTAMP,
    duration_minutes INTEGER,
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (breaker_id) REFERENCES circuit_breakers(breaker_id)
);

CREATE INDEX idx_breaker_activations_time ON circuit_breaker_activations(activated_at DESC);
CREATE INDEX idx_breaker_activations_breaker ON circuit_breaker_activations(breaker_id);

-- =====================================================
-- EQUITY TRACKING TABLE
-- Continuous tracking of account equity and drawdown
-- =====================================================
CREATE TABLE equity_tracking (
    tracking_id SERIAL PRIMARY KEY,
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

CREATE INDEX idx_equity_tracking_timestamp ON equity_tracking(timestamp DESC);
CREATE INDEX idx_equity_tracking_date ON equity_tracking(DATE(timestamp));

-- =====================================================
-- SYSTEM METRICS TABLE
-- Performance and health metrics of the trading system
-- =====================================================
CREATE TABLE system_metrics (
    metric_id SERIAL PRIMARY KEY,
    timestamp TIMESTAMP NOT NULL,
    metric_type VARCHAR(50) NOT NULL,
    metric_name VARCHAR(100) NOT NULL,
    metric_value NUMERIC(15,4),
    metric_text VARCHAR(500),
    metadata JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_system_metrics_timestamp ON system_metrics(timestamp DESC);
CREATE INDEX idx_system_metrics_type ON system_metrics(metric_type);
CREATE INDEX idx_system_metrics_type_time ON system_metrics(metric_type, timestamp DESC);

-- =====================================================
-- INSERT DEFAULT CIRCUIT BREAKERS
-- =====================================================
INSERT INTO circuit_breakers (breaker_id, breaker_type, threshold_value, severity_level, action_required, description)
VALUES 
    ('DD_INTRADAY_5PCT', 'DRAWDOWN_INTRADAY', 5.0, 1, 'REDUCE_SIZING_20PCT', 
     'Reduce position sizing by 20% when intraday drawdown exceeds 5%'),
    ('DD_INTRADAY_10PCT', 'DRAWDOWN_INTRADAY', 10.0, 2, 'REDUCE_SIZING_40PCT', 
     'Reduce position sizing by 40% when intraday drawdown exceeds 10%'),
    ('DD_INTRADAY_20PCT', 'DRAWDOWN_INTRADAY', 20.0, 3, 'REDUCE_SIZING_60PCT', 
     'Reduce position sizing by 60% when intraday drawdown exceeds 20%'),
    ('DD_INTRADAY_30PCT', 'DRAWDOWN_INTRADAY', 30.0, 4, 'REDUCE_SIZING_80PCT', 
     'Reduce position sizing by 80% when intraday drawdown exceeds 30%'),
    ('DD_INTRADAY_40PCT', 'DRAWDOWN_INTRADAY', 40.0, 5, 'HALT_TRADING', 
     'Halt all trading when intraday drawdown exceeds 40%'),
    ('VOLATILITY_EXTREME', 'VOLATILITY_SPIKE', 300.0, 3, 'PAUSE_NEW_SIGNALS', 
     'Pause new signals when volatility exceeds 3x historical average'),
    ('SPREAD_WIDENING', 'SPREAD_ANOMALY', 500.0, 2, 'REDUCE_SIZING_30PCT', 
     'Reduce sizing when spreads widen beyond 5x normal'),
    ('CONSECUTIVE_LOSSES', 'LOSS_STREAK', 10.0, 2, 'REDUCE_SIZING_50PCT', 
     'Reduce sizing after 10 consecutive losing trades');

-- =====================================================
-- GRANT PERMISSIONS
-- =====================================================
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO trading_user;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO trading_user;

-- =====================================================
-- SCHEMA CREATION COMPLETE
-- =====================================================
