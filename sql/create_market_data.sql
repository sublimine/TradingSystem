-- Market Data Table for Historical Prices
CREATE TABLE IF NOT EXISTS market_data (
    id SERIAL PRIMARY KEY,
    symbol VARCHAR(20) NOT NULL,
    time TIMESTAMP NOT NULL,
    open NUMERIC(12,6) NOT NULL,
    high NUMERIC(12,6) NOT NULL,
    low NUMERIC(12,6) NOT NULL,
    close NUMERIC(12,6) NOT NULL,
    tick_volume BIGINT NOT NULL,
    spread INTEGER,
    real_volume BIGINT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(symbol, time)
);

CREATE INDEX IF NOT EXISTS idx_market_data_symbol_time ON market_data(symbol, time DESC);
CREATE INDEX IF NOT EXISTS idx_market_data_time ON market_data(time DESC);

GRANT ALL PRIVILEGES ON market_data TO trading_user;
GRANT USAGE, SELECT ON SEQUENCE market_data_id_seq TO trading_user;
