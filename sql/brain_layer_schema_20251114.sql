-- ========================================
-- BRAIN LAYER SCHEMA - MANDATO 14
-- SUBLIMINE TradingSystem
-- ========================================
-- Fecha: 2025-11-14
-- Versión: 1.0
--
-- Descripción:
-- Schema para persistencia de políticas del Brain-layer
-- y auditoría de decisiones aplicadas en runtime.
-- ========================================

-- ========================================
-- Tabla: brain_policies
-- ========================================
-- Almacena políticas generadas por offline_trainer.py
-- Una policy por estrategia, versionada por created_at

CREATE TABLE IF NOT EXISTS brain_policies (
    id SERIAL PRIMARY KEY,

    -- Identificación
    strategy_id VARCHAR(100) NOT NULL,

    -- Estado operativo recomendado
    state_suggested VARCHAR(20) NOT NULL
        CHECK (state_suggested IN ('PRODUCTION', 'PILOT', 'DEGRADED', 'RETIRED')),

    -- Peso relativo en cluster (0.0–1.0)
    weight_recommendation NUMERIC(5, 4) NOT NULL
        CHECK (weight_recommendation >= 0.0 AND weight_recommendation <= 1.0),

    -- Ajuste de threshold de QualityScore (-0.15 a +0.15)
    quality_threshold_adjustment NUMERIC(4, 3) NOT NULL
        CHECK (quality_threshold_adjustment >= -0.15 AND quality_threshold_adjustment <= 0.15),

    -- Configuración por régimen (JSON)
    -- Estructura: {"HIGH_VOL": {"enabled": true, "weight_factor": 1.2, ...}, ...}
    regime_overrides JSONB,

    -- Metadata de decisión (JSON)
    -- Estructura: {"reason_summary": "...", "confidence": 0.9, "triggering_metrics": {...}}
    metadata JSONB NOT NULL,

    -- Vigencia temporal
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    valid_until TIMESTAMPTZ NOT NULL,

    -- Control de activación
    is_active BOOLEAN DEFAULT TRUE
);

-- Índices para queries de runtime
CREATE INDEX idx_brain_policies_strategy_active
    ON brain_policies(strategy_id, is_active, valid_until);

CREATE INDEX idx_brain_policies_created
    ON brain_policies(created_at DESC);

-- Constraint: una sola policy activa por estrategia en un momento dado
CREATE UNIQUE INDEX idx_brain_policies_unique_active
    ON brain_policies(strategy_id)
    WHERE is_active = TRUE;

COMMENT ON TABLE brain_policies IS
    'Políticas del Brain-layer generadas offline. Una policy activa por estrategia.';

COMMENT ON COLUMN brain_policies.state_suggested IS
    'Estado operativo: PRODUCTION (full), PILOT (observación), DEGRADED (reducido), RETIRED (desactivado)';

COMMENT ON COLUMN brain_policies.weight_recommendation IS
    'Peso relativo 0–1 dentro del cluster. Usado por Arbiter para resolver conflictos.';

COMMENT ON COLUMN brain_policies.quality_threshold_adjustment IS
    'Delta sobre threshold base (0.60). Rango [-0.15, +0.15] para evitar drift excesivo.';

COMMENT ON COLUMN brain_policies.regime_overrides IS
    'Configuración específica por régimen de mercado (HIGH_VOL, LOW_VOL, TRENDING, RANGING).';


-- ========================================
-- Tabla: brain_events
-- ========================================
-- Log de eventos del Brain-layer para auditoría y análisis

CREATE TABLE IF NOT EXISTS brain_events (
    id BIGSERIAL PRIMARY KEY,

    -- Tipo de evento
    event_type VARCHAR(50) NOT NULL
        CHECK (event_type IN ('BRAIN_POLICY_UPDATE', 'BRAIN_DECISION_APPLIED')),

    -- Timestamp del evento
    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    -- Estrategia afectada (nullable para eventos globales)
    strategy_id VARCHAR(100),

    -- Payload completo del evento (JSON)
    -- POLICY_UPDATE: {old_state, new_state, old_weight, new_weight, reason, ...}
    -- DECISION_APPLIED: {action, quality_score, threshold, regime, brain_weight, ...}
    payload JSONB NOT NULL
);

-- Índices para queries de análisis
CREATE INDEX idx_brain_events_type_time
    ON brain_events(event_type, timestamp DESC);

CREATE INDEX idx_brain_events_strategy_time
    ON brain_events(strategy_id, timestamp DESC)
    WHERE strategy_id IS NOT NULL;

CREATE INDEX idx_brain_events_timestamp
    ON brain_events(timestamp DESC);

COMMENT ON TABLE brain_events IS
    'Registro de auditoría de decisiones del Brain-layer aplicadas en runtime.';

COMMENT ON COLUMN brain_events.event_type IS
    'BRAIN_POLICY_UPDATE: cambio de policy. BRAIN_DECISION_APPLIED: decisión en runtime.';

COMMENT ON COLUMN brain_events.payload IS
    'Payload completo del evento en formato JSON para análisis flexible.';


-- ========================================
-- Vista: active_brain_policies
-- ========================================
-- Vista de conveniencia para policies activas

CREATE OR REPLACE VIEW active_brain_policies AS
SELECT
    strategy_id,
    state_suggested,
    weight_recommendation,
    quality_threshold_adjustment,
    regime_overrides,
    metadata,
    created_at,
    valid_until
FROM brain_policies
WHERE is_active = TRUE
  AND valid_until > NOW()
ORDER BY strategy_id;

COMMENT ON VIEW active_brain_policies IS
    'Políticas activas y vigentes del Brain-layer.';


-- ========================================
-- Función: get_effective_quality_threshold
-- ========================================
-- Calcula threshold efectivo para una estrategia en un régimen dado

CREATE OR REPLACE FUNCTION get_effective_quality_threshold(
    p_strategy_id VARCHAR(100),
    p_regime VARCHAR(20) DEFAULT 'NORMAL'
)
RETURNS NUMERIC(4, 3) AS $$
DECLARE
    v_base_threshold NUMERIC(4, 3) := 0.60;  -- Base institucional
    v_adjustment NUMERIC(4, 3);
    v_regime_adjustment NUMERIC(4, 3) := 0.0;
BEGIN
    -- Obtener ajuste de policy activa
    SELECT quality_threshold_adjustment
    INTO v_adjustment
    FROM brain_policies
    WHERE strategy_id = p_strategy_id
      AND is_active = TRUE
      AND valid_until > NOW()
    LIMIT 1;

    -- Si no hay policy, retornar base
    IF v_adjustment IS NULL THEN
        RETURN v_base_threshold;
    END IF;

    -- Intentar obtener ajuste específico de régimen
    -- (implementación simplificada, podría expandirse)

    RETURN v_base_threshold + v_adjustment + v_regime_adjustment;
END;
$$ LANGUAGE plpgsql STABLE;

COMMENT ON FUNCTION get_effective_quality_threshold IS
    'Calcula threshold efectivo de QualityScore para estrategia y régimen dados.';


-- ========================================
-- Función helper: log_brain_event
-- ========================================
-- Función para insertar eventos del Brain desde Python

CREATE OR REPLACE FUNCTION log_brain_event(
    p_event_type VARCHAR(50),
    p_strategy_id VARCHAR(100),
    p_payload JSONB
)
RETURNS BIGINT AS $$
DECLARE
    v_event_id BIGINT;
BEGIN
    INSERT INTO brain_events (event_type, strategy_id, payload)
    VALUES (p_event_type, p_strategy_id, p_payload)
    RETURNING id INTO v_event_id;

    RETURN v_event_id;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION log_brain_event IS
    'Helper para logging de eventos del Brain desde aplicación Python.';


-- ========================================
-- Grants (ajustar según usuario de aplicación)
-- ========================================
-- GRANT SELECT, INSERT, UPDATE ON brain_policies TO trading_app;
-- GRANT SELECT, INSERT ON brain_events TO trading_app;
-- GRANT USAGE ON SEQUENCE brain_policies_id_seq TO trading_app;
-- GRANT USAGE ON SEQUENCE brain_events_id_seq TO trading_app;


-- ========================================
-- FIN DEL SCHEMA
-- ========================================
