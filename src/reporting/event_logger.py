"""
ExecutionEventLogger - Logger institucional de eventos de trading

Registra cada trade con trazabilidad completa:
- Estrategia + concepto/edge
- Riesgo asignado (%)
- QualityScore desglosado
- SL/TP estructurales
- Microestructura + multiframe scores

Integración con Postgres para persistencia institucional.

Mandato: MANDATO 12 (actualizado con integración DB)
Fecha: 2025-11-14
"""

from dataclasses import dataclass, asdict
from datetime import datetime
from typing import Optional, List, Dict
import logging
import json

# Import DB layer
try:
    from .db import ReportingDatabase
    DB_AVAILABLE = True
except ImportError:
    DB_AVAILABLE = False
    ReportingDatabase = None


@dataclass
class TradeRecord:
    """Registro completo de un trade institucional."""

    # Identificación
    trade_id: str
    timestamp: datetime
    symbol: str
    strategy_id: str
    strategy_name: str
    strategy_category: str

    # Concepto/Edge
    setup_type: str
    edge_description: str
    research_basis: str

    # Dirección y sizing
    direction: str
    quantity: float
    entry_price: float

    # Riesgo
    risk_pct: float
    position_size_usd: float
    stop_loss: float
    take_profit: float
    sl_type: str
    tp_type: str

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
    asset_class: str
    region: str
    risk_cluster: str

    # Metadata
    regime: str
    data_health_score: float
    slippage_bps: float
    notes: str


class ExecutionEventLogger:
    """
    Logger institucional de eventos de trading.

    Registra cada entrada/salida/parcial/ajuste en DB y buffer.
    NO bloquea el loop de trading (batch inserts).
    """

    def __init__(self, db: Optional['ReportingDatabase'] = None,
                 config_path: str = "config/reporting_db.yaml",
                 buffer_size: int = 100):
        """
        Args:
            db: ReportingDatabase instance (None = auto-create from config)
            config_path: Ruta al archivo de configuración DB
            buffer_size: Eventos en buffer antes de flush
        """
        self.logger = logging.getLogger(self.__class__.__name__)

        # Initialize DB connection
        if db is not None:
            self.db = db
        elif DB_AVAILABLE:
            try:
                self.db = ReportingDatabase(config_path)
                self.logger.info("✅ ReportingDatabase initialized")
            except Exception as e:
                self.logger.warning(f"Failed to initialize DB: {e}. Using fallback mode.")
                self.db = None
        else:
            self.logger.warning("ReportingDatabase module not available. Using fallback mode.")
            self.db = None

        self.buffer_size = buffer_size
        self.event_buffer = []

    def log_entry(self, trade_record: TradeRecord):
        """Registrar entrada de trade."""
        event = {
            'event_type': 'ENTRY',
            'timestamp': trade_record.timestamp,
            **asdict(trade_record)
        }
        self._append_event(event)
        self.logger.info(f"✅ ENTRY logged: {trade_record.strategy_name} {trade_record.symbol} {trade_record.direction} @ {trade_record.entry_price}")

    def log_exit(self, trade_id: str, exit_timestamp: datetime, exit_price: float,
                 pnl_gross: float, pnl_net: float, r_multiple: float,
                 mae: float, mfe: float, holding_time_minutes: int,
                 exit_reason: str):
        """Registrar salida de trade."""
        event = {
            'event_type': 'EXIT',
            'timestamp': exit_timestamp,
            'trade_id': trade_id,
            'price': exit_price,
            'pnl_gross': pnl_gross,
            'pnl_net': pnl_net,
            'r_multiple': r_multiple,
            'mae': mae,
            'mfe': mfe,
            'holding_time_minutes': holding_time_minutes,
            'notes': f"Exit reason: {exit_reason}"
        }
        self._append_event(event)
        self.logger.info(f"🔚 EXIT logged: {trade_id}, PnL: {pnl_gross:.2f}, R: {r_multiple:.2f}")

    def log_partial(self, trade_id: str, timestamp: datetime, percent_closed: float,
                    price: float, pnl_partial: float):
        """Registrar cierre parcial."""
        event = {
            'event_type': 'PARTIAL',
            'timestamp': timestamp,
            'trade_id': trade_id,
            'price': price,
            'pnl_gross': pnl_partial,
            'notes': f"Partial close {percent_closed:.0f}%"
        }
        self._append_event(event)

    def log_sl_adjustment(self, trade_id: str, timestamp: datetime,
                         new_sl: float, reason: str):
        """Registrar ajuste de SL (BE, trailing)."""
        event = {
            'event_type': 'BE_MOVED' if 'breakeven' in reason.lower() else 'SL_ADJUSTED',
            'timestamp': timestamp,
            'trade_id': trade_id,
            'stop_loss': new_sl,
            'notes': reason
        }
        self._append_event(event)

    def log_rejection(self, timestamp: datetime, strategy_id: str, symbol: str,
                     reason: str, quality_score: float, risk_requested_pct: float):
        """Registrar operación rechazada (por RiskManager/ExposureManager)."""
        event = {
            'event_type': 'REJECTION',
            'timestamp': timestamp,
            'strategy_id': strategy_id,
            'symbol': symbol,
            'quality_score_total': quality_score,
            'risk_pct': risk_requested_pct,
            'notes': f"Rejected: {reason}"
        }
        self._append_event(event)
        self.logger.warning(f"⛔ REJECTION: {strategy_id} {symbol} - {reason}")

    def _append_event(self, event: Dict):
        """Añadir evento a buffer y flush si necesario."""
        self.event_buffer.append(event)
        if len(self.event_buffer) >= self.buffer_size:
            self.flush()

    def flush(self):
        """Flush buffer a DB (batch insert)."""
        if not self.event_buffer:
            return

        num_events = len(self.event_buffer)

        if self.db:
            try:
                # Batch insert to Postgres via ReportingDatabase
                success = self.db.insert_trade_events(self.event_buffer)
                if success:
                    self.logger.debug(f"📊 Flushed {num_events} events to DB")
                else:
                    # DB layer handles fallback internally
                    self.logger.debug(f"📊 Flushed {num_events} events (fallback)")
            except Exception as e:
                self.logger.error(f"DB flush failed: {e}")
                # Last resort fallback
                self._emergency_fallback(self.event_buffer)
        else:
            # No DB available: fallback to JSONL
            self._emergency_fallback(self.event_buffer)

        self.event_buffer.clear()

    def _emergency_fallback(self, events: List[Dict]):
        """Fallback de emergencia: escribir a JSONL local."""
        from pathlib import Path
        fallback_dir = Path('reports/raw')
        fallback_dir.mkdir(parents=True, exist_ok=True)

        fallback_file = fallback_dir / 'events_emergency.jsonl'

        try:
            with open(fallback_file, 'a') as f:
                for event in events:
                    # Convert datetime to isoformat for JSON serialization
                    event_copy = event.copy()
                    if 'timestamp' in event_copy and hasattr(event_copy['timestamp'], 'isoformat'):
                        event_copy['timestamp'] = event_copy['timestamp'].isoformat()
                    f.write(json.dumps(event_copy) + '\n')
            self.logger.warning(f"⚠️ Emergency fallback: wrote {len(events)} events to {fallback_file}")
        except Exception as e:
            self.logger.error(f"Emergency fallback failed: {e}")

    def close(self):
        """Flush pendientes y cerrar."""
        self.flush()
        if self.db:
            self.db.close()
