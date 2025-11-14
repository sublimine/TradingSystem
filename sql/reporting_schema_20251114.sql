-- ============================================================
-- ESQUEMA DE REPORTING INSTITUCIONAL
-- Proyecto: SUBLIMINE TradingSystem
-- Mandato: MANDATO 11
-- Fecha: 2025-11-14
-- Base de Datos: PostgreSQL 12+
-- ============================================================

-- Tabla de referencia: símbolos del universo (27 símbolos de Mandato 10)
CREATE TABLE IF NOT EXISTS symbols (
    symbol VARCHAR(20) PRIMARY KEY,
    asset_class VARCHAR(20) NOT NULL,
    region VARCHAR(50),
    role VARCHAR(100),
    priority VARCHAR(20),
    max_exposure_pct NUMERIC(6, 4),
    spread_typical_value NUMERIC(10, 6),
    liquidity_tier VARCHAR(20),
    eligible_strategies JSONB,
    correlation_pairs JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Tabla principal: trade_events (cada entrada/salida/parcial/ajuste)
CREATE TABLE IF NOT EXISTS trade_events (
    event_id BIGSERIAL PRIMARY KEY,
    timestamp TIMESTAMPTZ NOT NULL,
    event_type VARCHAR(20) NOT NULL CHECK (event_type IN ('ENTRY', 'EXIT', 'PARTIAL', 'SL_HIT', 'TP_HIT', 'BE_MOVED', 'REJECTION')),

    -- Identificación
    trade_id VARCHAR(64) NOT NULL,
    symbol VARCHAR(20) NOT NULL,
    strategy_id VARCHAR(64) NOT NULL,
    strategy_name VARCHAR(100) NOT NULL,
    strategy_category VARCHAR(50),

    -- Concepto/Edge
    setup_type VARCHAR(100),
    edge_description TEXT,
    research_basis VARCHAR(200),

    -- Dirección y sizing
    direction VARCHAR(10) CHECK (direction IN ('LONG', 'SHORT', 'NEUTRAL')),
    quantity NUMERIC(20, 8),
    price NUMERIC(20, 8),

    -- Riesgo
    risk_pct NUMERIC(6, 4) CHECK (risk_pct >= 0 AND risk_pct <= 2.0),
    position_size_usd NUMERIC(20, 2),
    stop_loss NUMERIC(20, 8),
    take_profit NUMERIC(20, 8),
    sl_type VARCHAR(50),
    tp_type VARCHAR(50),

    -- QualityScore desglosado
    quality_score_total NUMERIC(5, 3),
    quality_pedigree NUMERIC(5, 3),
    quality_signal NUMERIC(5, 3),
    quality_microstructure NUMERIC(5, 3),
    quality_multiframe NUMERIC(5, 3),
    quality_data_health NUMERIC(5, 3),
    quality_portfolio NUMERIC(5, 3),

    -- Contexto microestructura
    vpin NUMERIC(5, 3),
    ofi NUMERIC(10, 4),
    cvd NUMERIC(10, 4),
    depth_imbalance NUMERIC(5, 3),
    spoofing_score NUMERIC(5, 3),

    -- Contexto multiframe
    htf_trend VARCHAR(20),
    mtf_structure VARCHAR(50),
    ltf_entry_quality NUMERIC(5, 3),

    -- Universo/Clasificación
    asset_class VARCHAR(20) CHECK (asset_class IN ('FX', 'INDEX', 'COMMODITY', 'CRYPTO')),
    region VARCHAR(50),
    risk_cluster VARCHAR(50),

    -- PnL (para EXIT events)
    pnl_gross NUMERIC(20, 2),
    pnl_net NUMERIC(20, 2),
    r_multiple NUMERIC(10, 4),
    mae NUMERIC(20, 2),
    mfe NUMERIC(20, 2),
    holding_time_minutes INTEGER,

    -- Metadata
    regime VARCHAR(20) CHECK (regime IN ('LOW_VOL', 'NORMAL', 'HIGH_VOL', 'CRISIS')),
    data_health_score NUMERIC(5, 3),
    slippage_bps NUMERIC(10, 2),
    notes TEXT,

    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_trade_events_timestamp ON trade_events(timestamp);
CREATE INDEX idx_trade_events_trade_id ON trade_events(trade_id);
CREATE INDEX idx_trade_events_strategy ON trade_events(strategy_id);
CREATE INDEX idx_trade_events_symbol ON trade_events(symbol);
CREATE INDEX idx_trade_events_event_type ON trade_events(event_type);
CREATE INDEX idx_trade_events_date ON trade_events(DATE(timestamp));

-- Tabla: position_snapshots (estado de posiciones en cada momento)
CREATE TABLE IF NOT EXISTS position_snapshots (
    snapshot_id BIGSERIAL PRIMARY KEY,
    timestamp TIMESTAMPTZ NOT NULL,

    symbol VARCHAR(20) NOT NULL,
    strategy_id VARCHAR(64) NOT NULL,
    trade_id VARCHAR(64),

    -- Posición
    direction VARCHAR(10),
    quantity NUMERIC(20, 8),
    entry_price NUMERIC(20, 8),
    current_price NUMERIC(20, 8),
    unrealized_pnl NUMERIC(20, 2),

    -- Riesgo
    risk_allocated_pct NUMERIC(6, 4),
    stop_loss NUMERIC(20, 8),
    take_profit NUMERIC(20, 8),

    -- Clasificación
    asset_class VARCHAR(20),
    region VARCHAR(50),
    risk_cluster VARCHAR(50),

    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_position_snapshots_timestamp ON position_snapshots(timestamp);
CREATE INDEX idx_position_snapshots_symbol ON position_snapshots(symbol);
CREATE INDEX idx_position_snapshots_strategy ON position_snapshots(strategy_id);

-- Tabla: risk_snapshots (estado de riesgo del portfolio)
CREATE TABLE IF NOT EXISTS risk_snapshots (
    snapshot_id BIGSERIAL PRIMARY KEY,
    timestamp TIMESTAMPTZ NOT NULL,

    -- Riesgo total
    total_risk_used_pct NUMERIC(6, 4),
    total_risk_available_pct NUMERIC(6, 4),
    max_risk_allowed_pct NUMERIC(6, 4),

    -- Desglose por dimensión (JSONB para flexibilidad)
    risk_by_asset_class JSONB,
    risk_by_region JSONB,
    risk_by_strategy JSONB,
    risk_by_cluster JSONB,

    -- Límites
    symbols_at_limit INTEGER,
    strategies_at_limit INTEGER,
    clusters_at_limit INTEGER,

    -- Correlación
    portfolio_correlation_avg NUMERIC(5, 3),
    herfindahl_index NUMERIC(5, 3),

    -- Eventos
    rejections_last_hour INTEGER,
    circuit_breaker_active BOOLEAN,

    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_risk_snapshots_timestamp ON risk_snapshots(timestamp);

-- Tabla: strategy_performance (KPIs agregados por estrategia)
CREATE TABLE IF NOT EXISTS strategy_performance (
    performance_id BIGSERIAL PRIMARY KEY,
    period_start TIMESTAMPTZ NOT NULL,
    period_end TIMESTAMPTZ NOT NULL,
    frequency VARCHAR(20) NOT NULL CHECK (frequency IN ('DAILY', 'WEEKLY', 'MONTHLY', 'QUARTERLY', 'ANNUAL')),

    strategy_id VARCHAR(64) NOT NULL,
    strategy_name VARCHAR(100),
    strategy_category VARCHAR(50),

    -- Trades
    total_trades INTEGER,
    winning_trades INTEGER,
    losing_trades INTEGER,
    hit_rate NUMERIC(5, 3),

    -- PnL
    pnl_gross NUMERIC(20, 2),
    pnl_net NUMERIC(20, 2),
    return_pct NUMERIC(10, 4),

    -- Risk-adjusted
    sharpe_ratio NUMERIC(10, 4),
    sortino_ratio NUMERIC(10, 4),
    calmar_ratio NUMERIC(10, 4),
    mar_ratio NUMERIC(10, 4),

    -- Drawdown
    max_drawdown_pct NUMERIC(10, 4),
    max_drawdown_duration_days INTEGER,
    current_drawdown_pct NUMERIC(10, 4),

    -- Trade stats
    avg_win NUMERIC(20, 2),
    avg_loss NUMERIC(20, 2),
    payoff_ratio NUMERIC(10, 4),
    expectancy NUMERIC(20, 2),
    avg_r_multiple NUMERIC(10, 4),

    -- Sizing
    avg_risk_pct NUMERIC(6, 4),
    avg_holding_time_minutes INTEGER,
    turnover_rate NUMERIC(10, 4),

    -- Quality
    avg_quality_score NUMERIC(5, 3),
    quality_vs_return_correlation NUMERIC(5, 3),

    -- Estado
    lifecycle_state VARCHAR(20) CHECK (lifecycle_state IN ('EXPERIMENTAL', 'PILOT', 'PRODUCTION', 'DEGRADED', 'RETIRED')),
    decay_signals JSONB,

    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_strategy_performance_period ON strategy_performance(period_start, period_end);
CREATE INDEX idx_strategy_performance_strategy ON strategy_performance(strategy_id);
CREATE INDEX idx_strategy_performance_frequency ON strategy_performance(frequency);

-- Tabla: microstructure_snapshots (estado de microestructura en momento de entrada)
CREATE TABLE IF NOT EXISTS microstructure_snapshots (
    snapshot_id BIGSERIAL PRIMARY KEY,
    trade_id VARCHAR(64) NOT NULL,
    timestamp TIMESTAMPTZ NOT NULL,
    symbol VARCHAR(20) NOT NULL,

    -- Order flow
    vpin NUMERIC(5, 3),
    ofi NUMERIC(10, 4),
    cvd NUMERIC(10, 4),
    trade_intensity NUMERIC(10, 4),

    -- Depth
    bid_depth NUMERIC(20, 2),
    ask_depth NUMERIC(20, 2),
    depth_imbalance NUMERIC(5, 3),

    -- Toxicity
    flow_toxicity NUMERIC(5, 3),
    spoofing_score NUMERIC(5, 3),

    -- Volume
    volume_ratio NUMERIC(10, 4),
    buy_volume_pct NUMERIC(5, 3),
    sell_volume_pct NUMERIC(5, 3),

    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_microstructure_snapshots_trade_id ON microstructure_snapshots(trade_id);
CREATE INDEX idx_microstructure_snapshots_symbol ON microstructure_snapshots(symbol);
CREATE INDEX idx_microstructure_snapshots_timestamp ON microstructure_snapshots(timestamp);

-- Vista: trades completos (ENTRY + EXIT join)
CREATE OR REPLACE VIEW v_completed_trades AS
SELECT
    e.trade_id,
    e.timestamp AS entry_timestamp,
    e.symbol,
    e.strategy_id,
    e.strategy_name,
    e.strategy_category,
    e.direction,
    e.quantity,
    e.price AS entry_price,
    e.risk_pct,
    e.quality_score_total,
    e.asset_class,
    e.region,
    e.risk_cluster,
    x.timestamp AS exit_timestamp,
    x.price AS exit_price,
    x.pnl_gross,
    x.pnl_net,
    x.r_multiple,
    x.mae,
    x.mfe,
    x.holding_time_minutes,
    CASE WHEN x.pnl_gross > 0 THEN 1 ELSE 0 END AS is_winner
FROM trade_events e
JOIN trade_events x ON e.trade_id = x.trade_id
WHERE e.event_type = 'ENTRY' AND x.event_type IN ('EXIT', 'SL_HIT', 'TP_HIT');

-- Comentarios para documentación
COMMENT ON TABLE trade_events IS 'Registro completo de eventos de trading (entradas, salidas, parciales, ajustes)';
COMMENT ON TABLE position_snapshots IS 'Snapshots de posiciones abiertas (actualizado cada minuto o cada cambio)';
COMMENT ON TABLE risk_snapshots IS 'Snapshots de estado de riesgo del portfolio';
COMMENT ON TABLE strategy_performance IS 'KPIs agregados por estrategia (diario/semanal/mensual/trimestral/anual)';
COMMENT ON TABLE microstructure_snapshots IS 'Estado de microestructura en momento de entrada (para análisis post-trade)';
COMMENT ON VIEW v_completed_trades IS 'Vista de trades completos (ENTRY + EXIT)';

-- ============================================================
-- FIN DEL ESQUEMA
-- ============================================================
