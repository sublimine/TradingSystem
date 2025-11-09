-- Correlation Matrix Table
CREATE TABLE IF NOT EXISTS correlation_matrix (
    symbol_a VARCHAR(20) NOT NULL,
    symbol_b VARCHAR(20) NOT NULL,
    correlation_value NUMERIC(8,6) NOT NULL,
    lookback_days INTEGER NOT NULL,
    calculated_at TIMESTAMP NOT NULL,
    data_points INTEGER NOT NULL,
    PRIMARY KEY (symbol_a, symbol_b)
);

CREATE INDEX IF NOT EXISTS idx_correlation_symbol_a ON correlation_matrix(symbol_a);
CREATE INDEX IF NOT EXISTS idx_correlation_symbol_b ON correlation_matrix(symbol_b);
CREATE INDEX IF NOT EXISTS idx_correlation_calculated ON correlation_matrix(calculated_at DESC);

GRANT ALL PRIVILEGES ON correlation_matrix TO trading_user;
