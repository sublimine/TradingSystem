-- Desconectar todas las sesiones activas
SELECT pg_terminate_backend(pid) FROM pg_stat_activity 
WHERE datname = 'trading_system' AND pid <> pg_backend_pid();

-- Eliminar TODAS las tablas existentes con CASCADE
DROP TABLE IF EXISTS circuit_breaker_activations CASCADE;
DROP TABLE IF EXISTS circuit_breakers CASCADE;
DROP TABLE IF EXISTS equity_tracking CASCADE;
DROP TABLE IF EXISTS rejected_signals CASCADE;
DROP TABLE IF EXISTS signals CASCADE;
DROP TABLE IF EXISTS trades CASCADE;
DROP TABLE IF EXISTS system_metrics CASCADE;
DROP TABLE IF EXISTS market_data CASCADE;

-- RECREAR tabla trades con esquema correcto GARANTIZADO
CREATE TABLE trades (
    trade_id SERIAL PRIMARY KEY,
    ticket BIGINT UNIQUE,
    symbol VARCHAR(20) NOT NULL,
    trade_direction VARCHAR(10) NOT NULL,
    entry_price NUMERIC(12,5) NOT NULL,
    exit_price NUMERIC(12,5),
    trade_volume NUMERIC(10,2) NOT NULL,
    stop_loss NUMERIC(12,5) NOT NULL,
    take_profit NUMERIC(12,5) NOT NULL,
    entry_time TIMESTAMP NOT NULL,
    exit_time TIMESTAMP,
    trade_status VARCHAR(20) NOT NULL DEFAULT 'open',
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

CREATE TABLE signals (
    signal_id SERIAL PRIMARY KEY,
    timestamp TIMESTAMP NOT NULL,
    symbol VARCHAR(20) NOT NULL,
    strategy VARCHAR(100) NOT NULL,
    signal_direction VARCHAR(10) NOT NULL,
    entry_price NUMERIC(12,5) NOT NULL,
    stop_loss NUMERIC(12,5) NOT NULL,
    take_profit NUMERIC(12,5) NOT NULL,
    signal_volume NUMERIC(10,2) NOT NULL,
    sizing_level INTEGER NOT NULL,
    signal_status VARCHAR(20) NOT NULL DEFAULT 'pending',
    metadata JSONB,
    approved_at TIMESTAMP,
    executed_at TIMESTAMP,
    rejection_reason VARCHAR(200),
    ticket BIGINT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(timestamp, symbol, strategy, signal_direction)
);

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

CREATE TABLE circuit_breakers (
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

-- Indices
CREATE INDEX idx_trades_symbol ON trades(symbol);
CREATE INDEX idx_trades_status ON trades(trade_status);
CREATE INDEX idx_signals_status ON signals(signal_status);
CREATE INDEX idx_equity_tracking_timestamp ON equity_tracking(timestamp DESC);
CREATE INDEX idx_circuit_breakers_active ON circuit_breakers(is_active, severity_level);

-- Insertar circuit breakers
INSERT INTO circuit_breakers (breaker_id, breaker_type, threshold_value, severity_level, action_required, description)
VALUES 
    ('DD_INTRADAY_5PCT', 'DRAWDOWN_INTRADAY', 5.0, 1, 'REDUCE_SIZING_20PCT', 'Reduce sizing 20% at 5% DD'),
    ('DD_INTRADAY_10PCT', 'DRAWDOWN_INTRADAY', 10.0, 2, 'REDUCE_SIZING_40PCT', 'Reduce sizing 40% at 10% DD'),
    ('DD_INTRADAY_20PCT', 'DRAWDOWN_INTRADAY', 20.0, 3, 'REDUCE_SIZING_60PCT', 'Reduce sizing 60% at 20% DD'),
    ('DD_INTRADAY_30PCT', 'DRAWDOWN_INTRADAY', 30.0, 4, 'REDUCE_SIZING_80PCT', 'Reduce sizing 80% at 30% DD'),
    ('DD_INTRADAY_40PCT', 'DRAWDOWN_INTRADAY', 40.0, 5, 'HALT_TRADING', 'Halt trading at 40% DD');

-- Permisos
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO trading_user;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO trading_user;
