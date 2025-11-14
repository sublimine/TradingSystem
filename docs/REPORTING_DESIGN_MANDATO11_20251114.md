# SISTEMA DE REPORTING INSTITUCIONAL - DISEÑO TÉCNICO

**Proyecto**: SUBLIMINE TradingSystem
**Mandato**: MANDATO 11 (Reporting Institucional)
**Fecha**: 2025-11-14
**Estado**: DISEÑO INICIAL
**Clasificación**: INSTITUTIONAL GRADE - NO RETAIL

---

## RESUMEN EJECUTIVO

**Objetivo**: Sistema de reporting completo para mesa de hedge fund, no dashboard retail.

**Filosofía**:
- Cada trade registrado con trazabilidad completa: QUIÉN (estrategia), POR QUÉ (edge), CUÁNTO (riesgo %), EN QUÉ CONTEXTO (microestructura/multiframe)
- Informes diarios/semanales/mensuales/trimestrales/anuales para jefe de mesa, comité de riesgo, inversores
- Reporting sobre sistema de riesgo ya definido: QualityScore → RiskAllocator → 0-2% por idea (NO NEGOCIABLE)
- Integración nativa con DecisionLedger, RiskManager, ExposureManager, QualityScorer
- Base: Postgres + dumps Parquet/CSV para análisis offline

**Requisitos NO NEGOCIABLES**:
- ❌ NO "PnL y 4 ratios de juguete"
- ✅ Métricas institucionales: Sharpe, Sortino, Calmar, MAR, drawdown analysis, factor crowding, realized risk vs allocated
- ✅ Breakdown por estrategia, símbolo, clase de activo, cluster de riesgo, régimen
- ✅ Trazabilidad completa: cada trade con QualityScore desglosado, SL/TP estructurales, microestructure_score, multiframe_score
- ✅ Detección de decay: estrategias que dejan de funcionar, señales de degradación

---

## ARQUITECTURA DEL SISTEMA

### Componentes Principales

```
┌─────────────────────────────────────────────────────────┐
│                   TRADING ENGINE                         │
│  DecisionLedger → QualityScorer → RiskAllocator →       │
│  → TradeManager → ExecutionEngine                        │
└─────────────────┬───────────────────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────────────────┐
│             ExecutionEventLogger                         │
│  - Escucha cada decisión final                          │
│  - Registra TradeRecord completo                        │
│  - Append a DB + buffer de eventos                      │
└─────────────────┬───────────────────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────────────────┐
│              REPORTING DATABASE                          │
│  Postgres: trades, positions, risk_snapshots,           │
│  strategy_performance, microstructure_snapshots          │
└─────────────────┬───────────────────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────────────────┐
│           REPORTING ENGINE                               │
│  Aggregators → Metrics → Generators → Reports           │
│  (daily/weekly/monthly/quarterly/annual)                 │
└─────────────────────────────────────────────────────────┘
```

### Flujo de Datos

1. **Captura**: ExecutionEventLogger registra cada trade
2. **Almacenamiento**: Postgres (tiempo real) + Parquet dumps (EOD)
3. **Agregación**: Aggregators agrupan por fecha/estrategia/símbolo/clase
4. **Cálculo**: Metrics computa KPIs institucionales
5. **Generación**: Generators producen informes Markdown/JSON
6. **Distribución**: reports/ directories + notificaciones

---

## MODELO DE DATOS CANÓNICO

### 1. TradeEvent

**Tabla**: `trade_events`

Registra cada entrada/salida/parcial/ajuste de stop.

```sql
CREATE TABLE trade_events (
    event_id BIGSERIAL PRIMARY KEY,
    timestamp TIMESTAMPTZ NOT NULL,
    event_type VARCHAR(20) NOT NULL,  -- 'ENTRY', 'EXIT', 'PARTIAL', 'SL_HIT', 'TP_HIT', 'BE_MOVED'

    -- Identificación
    trade_id VARCHAR(64) NOT NULL,
    symbol VARCHAR(20) NOT NULL,
    strategy_id VARCHAR(64) NOT NULL,
    strategy_name VARCHAR(100) NOT NULL,
    strategy_category VARCHAR(50),  -- 'momentum', 'liquidity', 'pairs', 'order_flow', etc.

    -- Concepto/Edge
    setup_type VARCHAR(100),  -- 'JOHANSEN_COINTEGRATION_REAL', 'LIQUIDITY_SWEEP_INSTITUTIONAL', etc.
    edge_description TEXT,
    research_basis VARCHAR(200),

    -- Dirección y sizing
    direction VARCHAR(10),  -- 'LONG', 'SHORT'
    quantity NUMERIC(20, 8),
    price NUMERIC(20, 8),

    -- Riesgo
    risk_pct NUMERIC(6, 4),  -- 0.0000 - 2.0000 (max 2%)
    position_size_usd NUMERIC(20, 2),
    stop_loss NUMERIC(20, 8),
    take_profit NUMERIC(20, 8),
    sl_type VARCHAR(50),  -- 'STRUCTURAL_BREAKDOWN', 'Z_SCORE_EXTREME', 'CORRELATION_LOST', etc.
    tp_type VARCHAR(50),  -- 'Z_SCORE_NORMALIZE', 'R_MULTIPLE', 'STRUCTURAL_TARGET', etc.

    -- QualityScore (desglosado)
    quality_score_total NUMERIC(5, 3),
    quality_pedigree NUMERIC(5, 3),
    quality_signal NUMERIC(5, 3),
    quality_microstructure NUMERIC(5, 3),
    quality_multiframe NUMERIC(5, 3),
    quality_data_health NUMERIC(5, 3),
    quality_portfolio NUMERIC(5, 3),

    -- Contexto de microestructura
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
    asset_class VARCHAR(20),  -- 'FX', 'INDEX', 'COMMODITY', 'CRYPTO'
    region VARCHAR(50),
    risk_cluster VARCHAR(50),  -- 'order_flow', 'liquidity', 'pairs', 'volatility', 'news'

    -- PnL (para EXIT events)
    pnl_gross NUMERIC(20, 2),
    pnl_net NUMERIC(20, 2),
    r_multiple NUMERIC(10, 4),
    mae NUMERIC(20, 2),  -- Maximum Adverse Excursion
    mfe NUMERIC(20, 2),  -- Maximum Favorable Excursion
    holding_time_minutes INTEGER,

    -- Metadata
    regime VARCHAR(20),  -- 'LOW_VOL', 'NORMAL', 'HIGH_VOL', 'CRISIS'
    data_health_score NUMERIC(5, 3),
    slippage_bps NUMERIC(10, 2),
    notes TEXT,

    CONSTRAINT fk_symbol FOREIGN KEY (symbol) REFERENCES symbols(symbol),
    INDEX idx_timestamp (timestamp),
    INDEX idx_trade_id (trade_id),
    INDEX idx_strategy (strategy_id),
    INDEX idx_symbol (symbol),
    INDEX idx_event_type (event_type)
);
```

### 2. PositionSnapshot

**Tabla**: `position_snapshots`

Estado de exposición en cada momento (snapshot cada minuto o cada cambio).

```sql
CREATE TABLE position_snapshots (
    snapshot_id BIGSERIAL PRIMARY KEY,
    timestamp TIMESTAMPTZ NOT NULL,

    symbol VARCHAR(20) NOT NULL,
    strategy_id VARCHAR(64) NOT NULL,

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

    INDEX idx_timestamp (timestamp),
    INDEX idx_symbol (symbol),
    INDEX idx_strategy (strategy_id)
);
```

### 3. RiskSnapshot

**Tabla**: `risk_snapshots`

Estado de uso de riesgo del portfolio (snapshot cada minuto o cada cambio).

```sql
CREATE TABLE risk_snapshots (
    snapshot_id BIGSERIAL PRIMARY KEY,
    timestamp TIMESTAMPTZ NOT NULL,

    -- Riesgo total
    total_risk_used_pct NUMERIC(6, 4),
    total_risk_available_pct NUMERIC(6, 4),
    max_risk_allowed_pct NUMERIC(6, 4),  -- 2.0% por idea, pero total portfolio puede ser mayor

    -- Desglose por dimensión
    risk_by_asset_class JSONB,  -- {FX: 15.3%, INDEX: 8.2%, ...}
    risk_by_region JSONB,
    risk_by_strategy JSONB,
    risk_by_cluster JSONB,

    -- Límites
    symbols_at_limit INTEGER,
    strategies_at_limit INTEGER,
    clusters_at_limit INTEGER,

    -- Correlación
    portfolio_correlation_avg NUMERIC(5, 3),
    herfindahl_index NUMERIC(5, 3),  -- Concentración

    -- Eventos
    rejections_last_hour INTEGER,
    circuit_breaker_active BOOLEAN,

    INDEX idx_timestamp (timestamp)
);
```

### 4. StrategyPerformance

**Tabla**: `strategy_performance`

KPIs agregados por estrategia (actualizado EOD o EOW).

```sql
CREATE TABLE strategy_performance (
    performance_id BIGSERIAL PRIMARY KEY,
    period_start TIMESTAMPTZ NOT NULL,
    period_end TIMESTAMPTZ NOT NULL,
    frequency VARCHAR(20),  -- 'DAILY', 'WEEKLY', 'MONTHLY', 'QUARTERLY', 'ANNUAL'

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
    lifecycle_state VARCHAR(20),  -- 'EXPERIMENTAL', 'PILOT', 'PRODUCTION', 'DEGRADED', 'RETIRED'
    decay_signals JSONB,

    INDEX idx_period (period_start, period_end),
    INDEX idx_strategy (strategy_id),
    INDEX idx_frequency (frequency)
);
```

### 5. MicrostructureSnapshot

**Tabla**: `microstructure_snapshots`

Estado de microestructura en el momento de entrada (para análisis post-trade).

```sql
CREATE TABLE microstructure_snapshots (
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
    volume_ratio NUMERIC(10, 4),  -- current vs avg
    buy_volume_pct NUMERIC(5, 3),
    sell_volume_pct NUMERIC(5, 3),

    INDEX idx_trade_id (trade_id),
    INDEX idx_symbol (symbol),
    INDEX idx_timestamp (timestamp)
);
```

### 6. Symbols (referencia)

**Tabla**: `symbols`

Referencia del universo (27 símbolos de Mandato 10).

```sql
CREATE TABLE symbols (
    symbol VARCHAR(20) PRIMARY KEY,
    asset_class VARCHAR(20) NOT NULL,
    region VARCHAR(50),
    role VARCHAR(100),
    priority VARCHAR(20),
    max_exposure_pct NUMERIC(6, 4),

    -- Metadata
    spread_typical_value NUMERIC(10, 6),
    liquidity_tier VARCHAR(20),
    eligible_strategies JSONB,
    correlation_pairs JSONB
);
```

---

## INSTRUMENTACIÓN EN TIEMPO REAL

### ExecutionEventLogger

**Módulo**: `src/reporting/event_logger.py`

**Responsabilidad**: Escuchar decisiones finales de trading y registrar TradeRecord completo.

**Integración**:
- Hook en TradeManager/ExecutionEngine después de cada ejecución
- Hook en DecisionLedger cuando se confirma una decisión
- Hook en RiskManager cuando se rechaza una operación (para auditoría)

**API**:

```python
class ExecutionEventLogger:
    """
    Logger institucional de eventos de trading.

    Registra cada trade con trazabilidad completa:
    - Estrategia + concepto/edge
    - Riesgo asignado (%)
    - QualityScore desglosado
    - SL/TP estructurales
    - Microestructura + multiframe scores
    """

    def __init__(self, db_connection, buffer_size=100):
        """
        Args:
            db_connection: Conexión a Postgres
            buffer_size: Eventos en buffer antes de flush (rendimiento)
        """
        pass

    def log_entry(self, trade_record: TradeRecord):
        """Registrar entrada de trade."""
        pass

    def log_exit(self, trade_id: str, exit_price: float, pnl_gross: float,
                 pnl_net: float, r_multiple: float, mae: float, mfe: float,
                 holding_time_minutes: int, exit_reason: str):
        """Registrar salida de trade."""
        pass

    def log_partial(self, trade_id: str, percent_closed: float, price: float):
        """Registrar cierre parcial."""
        pass

    def log_sl_adjustment(self, trade_id: str, new_sl: float, reason: str):
        """Registrar ajuste de SL (BE, trailing)."""
        pass

    def log_rejection(self, strategy_id: str, symbol: str, reason: str,
                     quality_score: float, risk_requested_pct: float):
        """Registrar operación rechazada (por RiskManager/ExposureManager)."""
        pass

    def flush(self):
        """Flush buffer a DB (batch insert)."""
        pass
```

**TradeRecord**:

```python
@dataclass
class TradeRecord:
    """Registro completo de un trade institucional."""

    # Identificación
    trade_id: str
    timestamp: datetime
    symbol: str
    strategy_id: str
    strategy_name: str
    strategy_category: str  # 'momentum', 'liquidity', 'pairs', etc.

    # Concepto/Edge
    setup_type: str  # 'JOHANSEN_COINTEGRATION_REAL', etc.
    edge_description: str
    research_basis: str

    # Dirección y sizing
    direction: str  # 'LONG', 'SHORT'
    quantity: float
    entry_price: float

    # Riesgo
    risk_pct: float  # 0.0000 - 2.0000
    position_size_usd: float
    stop_loss: float
    take_profit: float
    sl_type: str  # 'STRUCTURAL_BREAKDOWN', 'Z_SCORE_EXTREME', etc.
    tp_type: str  # 'Z_SCORE_NORMALIZE', 'R_MULTIPLE', etc.

    # QualityScore desglosado
    quality_score_total: float
    quality_pedigree: float
    quality_signal: float
    quality_microstructure: float
    quality_multiframe: float
    quality_data_health: float
    quality_portfolio: float

    # Contexto microestructura
    vpin: float
    ofi: float
    cvd: float
    depth_imbalance: float
    spoofing_score: float

    # Contexto multiframe
    htf_trend: str
    mtf_structure: str
    ltf_entry_quality: float

    # Universo/Clasificación
    asset_class: str  # 'FX', 'INDEX', 'COMMODITY', 'CRYPTO'
    region: str
    risk_cluster: str  # 'order_flow', 'liquidity', 'pairs', 'volatility'

    # Metadata
    regime: str  # 'LOW_VOL', 'NORMAL', 'HIGH_VOL', 'CRISIS'
    data_health_score: float
    slippage_bps: float
    notes: str
```

---

## MOTOR DE REPORTING

### Aggregators (`src/reporting/aggregators.py`)

**Funciones**:

```python
def aggregate_by_date(trade_events: List[TradeEvent],
                     start_date: datetime, end_date: datetime) -> pd.DataFrame:
    """Agregar trades por fecha (PnL diario, trades count, etc.)."""
    pass

def aggregate_by_strategy(trade_events: List[TradeEvent]) -> pd.DataFrame:
    """Agregar por estrategia (PnL, hit rate, avg risk, etc.)."""
    pass

def aggregate_by_symbol(trade_events: List[TradeEvent]) -> pd.DataFrame:
    """Agregar por símbolo."""
    pass

def aggregate_by_asset_class(trade_events: List[TradeEvent]) -> pd.DataFrame:
    """Agregar por clase de activo (FX/INDEX/COMMODITY/CRYPTO)."""
    pass

def aggregate_by_risk_cluster(trade_events: List[TradeEvent]) -> pd.DataFrame:
    """Agregar por cluster de riesgo (order_flow, liquidity, pairs, etc.)."""
    pass

def aggregate_by_regime(trade_events: List[TradeEvent]) -> pd.DataFrame:
    """Agregar por régimen de volatilidad."""
    pass
```

### Metrics (`src/reporting/metrics.py`)

**Funciones**:

```python
# ========== PnL y Retornos ==========
def calculate_pnl_stats(trades: pd.DataFrame) -> Dict:
    """PnL bruto/neto, retorno %, vol anualizada."""
    pass

def calculate_equity_curve(trades: pd.DataFrame) -> pd.Series:
    """Curva de equity acumulada."""
    pass

# ========== Risk-Adjusted Metrics ==========
def calculate_sharpe_ratio(returns: pd.Series, risk_free_rate=0.0) -> float:
    """Sharpe ratio."""
    pass

def calculate_sortino_ratio(returns: pd.Series, risk_free_rate=0.0) -> float:
    """Sortino ratio (downside deviation)."""
    pass

def calculate_calmar_ratio(returns: pd.Series, max_drawdown: float) -> float:
    """Calmar ratio (return / max_dd)."""
    pass

def calculate_mar_ratio(returns: pd.Series, max_drawdown: float) -> float:
    """MAR ratio (CAGR / max_dd)."""
    pass

# ========== Drawdown Analysis ==========
def calculate_drawdown(equity_curve: pd.Series) -> pd.DataFrame:
    """Serie de drawdown."""
    pass

def calculate_max_drawdown(equity_curve: pd.Series) -> Dict:
    """Max DD: profundidad, duración, recuperación."""
    pass

# ========== Trade Stats ==========
def calculate_hit_rate(trades: pd.DataFrame) -> float:
    """Win rate (winning trades / total trades)."""
    pass

def calculate_payoff_ratio(trades: pd.DataFrame) -> float:
    """Avg win / Avg loss."""
    pass

def calculate_expectancy(trades: pd.DataFrame) -> float:
    """(Win rate * Avg win) - (Loss rate * Avg loss)."""
    pass

def calculate_avg_r_multiple(trades: pd.DataFrame) -> float:
    """Promedio de R múltiplos."""
    pass

# ========== Riesgo ==========
def calculate_realized_risk_vs_allocated(trades: pd.DataFrame) -> Dict:
    """Comparar riesgo realmente perdido vs riesgo asignado."""
    pass

def calculate_risk_concentration(positions: pd.DataFrame) -> Dict:
    """Herfindahl index de exposición por símbolo/estrategia."""
    pass

def calculate_factor_crowding(strategies_pnl: pd.DataFrame) -> pd.DataFrame:
    """Matriz de correlación de PnL entre estrategias."""
    pass

# ========== Quality Calibration ==========
def calculate_quality_vs_return_correlation(trades: pd.DataFrame) -> float:
    """Correlación entre QualityScore y retorno real."""
    pass

def calculate_quality_distribution_by_outcome(trades: pd.DataFrame) -> Dict:
    """Distribución de QualityScore para wins vs losses."""
    pass

# ========== Decay Detection ==========
def detect_strategy_decay(strategy_performance: pd.DataFrame,
                         lookback_window: int = 90) -> Dict:
    """Señales de decay: hit rate cayendo, Sharpe bajando, etc."""
    pass

# ========== Slippage y Execution ==========
def calculate_slippage_stats(trades: pd.DataFrame) -> Dict:
    """Slippage promedio, outliers, por símbolo."""
    pass
```

### Generators (`src/reporting/generators.py`)

**Funciones**:

```python
def generate_daily_report(date: datetime, trades: pd.DataFrame,
                         positions: pd.DataFrame, risk_snapshot: Dict) -> str:
    """
    Generar informe diario (Markdown).

    Contenido:
    - PnL del día (absoluto y %)
    - Top 5 estrategias por contribución / pérdida
    - Top 10 trades (mejores/peores) con detalles
    - Riesgo usado vs disponible
    - Eventos críticos (stops en cascada, slippage anómalo, circuit breakers)
    """
    pass

def generate_weekly_report(week_start: datetime, week_end: datetime,
                          trades: pd.DataFrame, equity_curve: pd.Series) -> str:
    """
    Generar informe semanal (Markdown).

    Contenido:
    - Curva de equity de la semana
    - Evolución de riesgo medio por trade
    - Distribución de QualityScore vs retorno
    - Estrategias que han cambiado de estado (PRODUCTION → DEGRADED, etc.)
    - Señales de decay preliminares
    """
    pass

def generate_monthly_report(month_start: datetime, month_end: datetime,
                           trades: pd.DataFrame, strategy_perf: pd.DataFrame) -> str:
    """
    Generar informe mensual (Markdown).

    Contenido:
    - KPIs completos: Sharpe, Sortino, Calmar, MAR
    - Análisis de drawdown (profundidad, duración, recuperación)
    - Breakdown por clase de activo, región, estrategia, factor
    - Scatter QualityScore vs retorno por estrategia
    - Segmentación por régimen de volatilidad
    - Matriz de correlación de PnL entre estrategias
    - Anexo de riesgo: uso de límites, cumplimiento de reglas, rechazos
    """
    pass

def generate_quarterly_report(...) -> str:
    """Similar a mensual pero con análisis más profundo."""
    pass

def generate_annual_report(...) -> str:
    """Informe completo de inversor institucional."""
    pass

def generate_json_summary(trades: pd.DataFrame, metrics: Dict) -> str:
    """Generar resumen JSON estructurado para uso programático."""
    pass
```

---

## INTEGRACIÓN CON COMPONENTES EXISTENTES

### DecisionLedger

**Hook**: Después de `record_decision()`, llamar a `ExecutionEventLogger.log_entry()`

```python
# En DecisionLedger.record_decision()
decision_record = self._create_decision_record(...)
self.ledger.append(decision_record)

# NUEVO: Log para reporting
if self.event_logger:
    trade_record = self._convert_to_trade_record(decision_record)
    self.event_logger.log_entry(trade_record)
```

### RiskManager / TradeManager

**Hook**: Al cerrar posición (exit/SL/TP), llamar a `ExecutionEventLogger.log_exit()`

```python
# En TradeManager.close_position()
exit_price = ...
pnl_gross = ...
r_multiple = ...

# NUEVO: Log exit
if self.event_logger:
    self.event_logger.log_exit(
        trade_id=position.trade_id,
        exit_price=exit_price,
        pnl_gross=pnl_gross,
        pnl_net=pnl_net,
        r_multiple=r_multiple,
        mae=position.mae,
        mfe=position.mfe,
        holding_time_minutes=holding_minutes,
        exit_reason=reason
    )
```

### ExposureManager

**Hook**: Al rechazar operación, llamar a `ExecutionEventLogger.log_rejection()`

```python
# En ExposureManager.check_limits()
if rejection_reason:
    if self.event_logger:
        self.event_logger.log_rejection(
            strategy_id=strategy_id,
            symbol=symbol,
            reason=rejection_reason,
            quality_score=quality_score,
            risk_requested_pct=risk_pct
        )
    return False, rejection_reason
```

### QualityScorer

**Modificación**: Asegurar que emite scores desglosados (ya debería estar así según Mandatos anteriores)

```python
quality_breakdown = {
    'total': total_score,
    'pedigree': pedigree_score,
    'signal': signal_score,
    'microstructure': microstructure_score,
    'multiframe': multiframe_score,
    'data_health': data_health_score,
    'portfolio': portfolio_score
}
```

---

## CONTENIDO DE INFORMES

### Informe Diario

**Archivo**: `reports/daily/report_YYYYMMDD.md`

```markdown
# INFORME DIARIO - ALGORITMO INSTITUCIONAL SUBLIMINE

**Fecha**: 2025-11-14
**Sesión**: Asia + London + NY

---

## RESUMEN EJECUTIVO

- **PnL Día**: +$12,345.67 (+0.87%)
- **Trades**: 23 (15W / 8L, hit rate 65.2%)
- **Riesgo Usado**: 14.3% del capital (máx permitido: 30%)
- **Sharpe Intraday**: 2.1

---

## TOP 5 ESTRATEGIAS (Contribución PnL)

1. **liquidity_sweep**: +$5,234.12 (8 trades, 7W/1L)
2. **statistical_arbitrage_johansen**: +$3,456.78 (3 trades, 3W/0L)
3. **breakout_volume_confirmation**: +$2,123.45 (6 trades, 4W/2L)
4. **vpin_reversal_extreme**: +$1,234.56 (2 trades, 1W/1L)
5. **order_flow_toxicity**: +$123.45 (4 trades, 2W/2L)

**Peores**:
- **correlation_divergence**: -$543.21 (2 trades, 0W/2L) ⚠️ Revisar

---

## TOP 10 TRADES DEL DÍA

### 🏆 Mejores 5

| # | Estrategia | Símbolo | Dir | R | PnL | Risk% | QS | Notas |
|---|-----------|---------|-----|---|-----|-------|-----|-------|
| 1 | liquidity_sweep | EURUSD | LONG | +3.2R | +$2,134 | 1.2% | 0.87 | Sweep @ 1.0850, OFI absorption clean |
| 2 | stat_arb_johansen | AUDUSD_NZDUSD | LONG spread | +2.8R | +$1,876 | 1.5% | 0.92 | Z-score -2.7 → 0, halflife 32h |
| 3 | breakout_volume | US500 | LONG | +2.3R | +$1,234 | 0.9% | 0.81 | Breakout 4500, vol 1.8x avg |
| 4 | vpin_reversal | GBPJPY | SHORT | +2.1R | +$987 | 1.1% | 0.79 | VPIN 0.76 → reversal confirmed |
| 5 | liquidity_sweep | XAUUSD | SHORT | +1.9R | +$765 | 1.3% | 0.85 | Gold sweep @ 2050, OFI neg |

### 💀 Peores 5

| # | Estrategia | Símbolo | Dir | R | PnL | Risk% | QS | Notas |
|---|-----------|---------|-----|---|-----|-------|-----|-------|
| 1 | correlation_div | EURUSD_GBPUSD | SHORT spread | -1.0R | -$543 | 1.2% | 0.68 | Divergence failed, correlation restored early |
| 2 | breakout_volume | BTCUSD | LONG | -1.0R | -$432 | 0.8% | 0.73 | False breakout, slippage 12bps |
| 3 | order_flow_toxicity | EURJPY | SHORT | -0.8R | -$321 | 0.9% | 0.71 | VPIN spike after entry |
| 4 | mean_reversion | EURGBP | LONG | -0.7R | -$234 | 0.6% | 0.69 | Range broke, SL hit |
| 5 | momentum_quality | GBPUSD | LONG | -0.5R | -$123 | 0.5% | 0.66 | HTF reversal, stopped |

---

## RIESGO Y EXPOSICIÓN

### Riesgo Usado
- **Total**: 14.3% del capital
- **Disponible**: 15.7% (límite soft: 30%)
- **Posiciones abiertas**: 7 (máx: 15)

### Exposición por Clase
- **FX**: 8.2%
- **Índices**: 3.4%
- **Commodities**: 2.1%
- **Crypto**: 0.6%

### Clusters de Riesgo
- **Order Flow**: 5.1%
- **Liquidity**: 4.3%
- **Pairs Trading**: 3.0%
- **Breakout**: 1.9%

---

## EVENTOS CRÍTICOS

### ⚠️ Alertas

1. **correlation_divergence** (2 pérdidas consecutivas): Revisar calibración, posible decay
2. **Slippage BTCUSD**: 12bps (media: 4bps), volumen anómalo en Binance

### ✅ Cumplimiento

- ✅ Ninguna operación >2.0% de riesgo
- ✅ Todos los SL estructurales (0 ATR-based)
- ✅ No hay correlation clusters sobrecargados

---

## MICROESTRUCTURA (Estadísticas de Entrada)

- **VPIN promedio**: 0.32 (rango: 0.15 - 0.76)
- **OFI promedio**: 1.8 (wins), -0.3 (losses)
- **Spoofing score**: 0.12 (bajo)

---

**Próxima revisión**: EOD NY session
```

### Informe Semanal

**Archivo**: `reports/weekly/report_YYYYMMDD_to_YYYYMMDD.md`

Contenido adicional vs diario:
- Curva de equity de la semana (gráfico ASCII o link a PNG)
- Evolución de riesgo medio por trade (trending up/down?)
- Distribución de QualityScore vs retorno (scatter)
- Cambios de lifecycle de estrategias
- Señales de decay preliminares

### Informe Mensual

**Archivo**: `reports/monthly/report_YYYYMM.md`

Contenido adicional vs semanal:
- **KPIs completos**: Sharpe anualizado, Sortino, Calmar, MAR
- **Drawdown analysis**: Max DD profundidad, duración, recuperación
- **Breakdown completo**: Por estrategia, clase activo, región, factor, régimen
- **Scatter QualityScore vs retorno**: Por estrategia (detectar miscalibration)
- **Matriz de correlación**: PnL entre estrategias (factor crowding)
- **Anexo de riesgo**: Uso de límites, rechazos, circuit breakers

### Informe Trimestral / Anual

Similar a mensual pero con:
- Análisis de tendencias de largo plazo
- Segmentación por ciclos de mercado
- Comparación con benchmarks
- Evolución de estrategias (lifecycle transitions)

---

## GOBERNANZA Y RUNBOOK

### Runbook Operativo

Ver: `docs/REPORTING_RUNBOOK_MANDATO11_20251114.md`

**Tareas Diarias**:
1. Revisar informe diario @ EOD
2. Verificar eventos críticos
3. Revisar estrategias con señales de decay
4. Confirmar límites de riesgo no violados

**Tareas Semanales**:
1. Revisar informe semanal
2. Ajustar parámetros de estrategias si necesario
3. Revisar lifecycle de estrategias

**Tareas Mensuales**:
1. Revisar informe mensual completo
2. Presentar KPIs a comité de riesgo
3. Decidir acciones sobre estrategias DEGRADED
4. Recalibrar QualityScorer si correlación quality-return <0.3

---

## AUTOMATIZACIÓN

### Script Principal

**Archivo**: `scripts/generate_reports.py`

```bash
# Generar informe diario
python scripts/generate_reports.py --frequency daily --date 2025-11-14

# Generar informe semanal
python scripts/generate_reports.py --frequency weekly --start 2025-11-08 --end 2025-11-14

# Generar informe mensual
python scripts/generate_reports.py --frequency monthly --month 2025-11

# Generar todos los informes pendientes
python scripts/generate_reports.py --auto
```

### Integración PowerShell

```powershell
# En monitor.ps1 (EOD)
if ((Get-Date).Hour -eq 23) {
    python scripts/generate_reports.py --frequency daily --date (Get-Date -Format "yyyy-MM-dd")
}

# Weekly (domingo)
if ((Get-Date).DayOfWeek -eq "Sunday") {
    $start = (Get-Date).AddDays(-7).ToString("yyyy-MM-dd")
    $end = (Get-Date).ToString("yyyy-MM-dd")
    python scripts/generate_reports.py --frequency weekly --start $start --end $end
}
```

---

## PRÓXIMOS PASOS (POST-MANDATO 11)

### Mandato 12: Backtesting Completo
- Aplicar reporting engine a backtests históricos
- Validar estrategias APROBAR en universo de 27 símbolos
- Ajustar parámetros según performance real

### Mandato 13: Elevación HYBRID
- Reporting de estrategias HYBRID durante elevación
- Tracking de mejoras pre/post elevación

### Mandato 14: Brain Layer Final
- Integrar reporting con decisiones de brain layer
- Tracking de meta-decisiones (strategy selection, regime adaptation)

---

**ESTADO**: DISEÑO COMPLETADO
**PRÓXIMO**: Implementación de módulos + esquema SQL
