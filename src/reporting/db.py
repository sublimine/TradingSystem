"""
Database Layer - Reporting Institucional

Conexión a Postgres para reporting engine.
Fallback a JSONL si DB no disponible (no romper trading loop).

Mandato: MANDATO 12
Fecha: 2025-11-14
"""

import os
import logging
import psycopg2
import psycopg2.pool
from psycopg2.extras import execute_batch
from typing import List, Dict, Optional
from pathlib import Path
import yaml
from contextlib import contextmanager


class ReportingDatabase:
    """
    Capa de acceso a Postgres para reporting institucional.

    Features:
    - Connection pooling
    - Batch inserts (performance)
    - Fallback a JSONL si DB no disponible
    - Non-blocking (no rompe trading loop)
    """

    def __init__(self, config_path: str = "config/reporting_db.yaml"):
        """
        Args:
            config_path: Ruta al archivo de configuración YAML
        """
        self.logger = logging.getLogger(self.__class__.__name__)
        self.config = self._load_config(config_path)
        self.pool = None
        self.fallback_enabled = self.config.get('fallback', {}).get('enabled', True)
        self.fallback_dir = Path(self.config.get('fallback', {}).get('directory', 'reports/raw'))

        try:
            self._init_pool()
        except Exception as e:
            self.logger.error(f"Failed to initialize DB pool: {e}")
            if not self.fallback_enabled:
                raise

    def _load_config(self, config_path: str) -> Dict:
        """Cargar configuración desde YAML, con variables de entorno."""
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)

        # Expandir variables de entorno
        db_config = config['database']
        for key, value in db_config.items():
            if isinstance(value, str) and "${" in value:
                # Parse ${VAR:-default}
                var_name = value.split("${")[1].split(":-")[0].split("}")[0]
                default = value.split(":-")[1].split("}")[0] if ":-" in value else None
                db_config[key] = os.getenv(var_name, default)

        return config

    def _init_pool(self):
        """Inicializar connection pool."""
        db_config = self.config['database']

        self.pool = psycopg2.pool.ThreadedConnectionPool(
            minconn=1,
            maxconn=db_config.get('pool_size', 5),
            host=db_config['host'],
            port=db_config['port'],
            dbname=db_config['dbname'],
            user=db_config['user'],
            password=db_config['password'],
            connect_timeout=db_config.get('connection_timeout', 10)
        )

        self.logger.info(f"✅ DB pool initialized: {db_config['host']}:{db_config['port']}/{db_config['dbname']}")

    @contextmanager
    def get_connection(self):
        """Context manager para conexión del pool."""
        conn = None
        try:
            if self.pool:
                conn = self.pool.getconn()
                yield conn
            else:
                yield None
        except Exception as e:
            self.logger.error(f"DB connection error: {e}")
            yield None
        finally:
            if conn and self.pool:
                self.pool.putconn(conn)

    def insert_trade_events(self, events: List[Dict]) -> bool:
        """
        Insertar eventos de trading (batch).

        Args:
            events: Lista de eventos (dicts)

        Returns:
            True si éxito, False si fallback
        """
        if not events:
            return True

        with self.get_connection() as conn:
            if not conn:
                return self._fallback_to_file(events, 'trade_events')

            try:
                cursor = conn.cursor()

                # SQL insert (ajustar campos según schema)
                sql = """
                    INSERT INTO trade_events (
                        timestamp, event_type, trade_id, symbol, strategy_id, strategy_name,
                        strategy_category, setup_type, edge_description, research_basis,
                        direction, quantity, price, risk_pct, position_size_usd,
                        stop_loss, take_profit, sl_type, tp_type,
                        quality_score_total, quality_pedigree, quality_signal,
                        quality_microstructure, quality_multiframe, quality_data_health, quality_portfolio,
                        vpin, ofi, cvd, depth_imbalance, spoofing_score,
                        htf_trend, mtf_structure, ltf_entry_quality,
                        asset_class, region, risk_cluster,
                        pnl_gross, pnl_net, r_multiple, mae, mfe, holding_time_minutes,
                        regime, data_health_score, slippage_bps, notes
                    ) VALUES (
                        %(timestamp)s, %(event_type)s, %(trade_id)s, %(symbol)s, %(strategy_id)s, %(strategy_name)s,
                        %(strategy_category)s, %(setup_type)s, %(edge_description)s, %(research_basis)s,
                        %(direction)s, %(quantity)s, %(price)s, %(risk_pct)s, %(position_size_usd)s,
                        %(stop_loss)s, %(take_profit)s, %(sl_type)s, %(tp_type)s,
                        %(quality_score_total)s, %(quality_pedigree)s, %(quality_signal)s,
                        %(quality_microstructure)s, %(quality_multiframe)s, %(quality_data_health)s, %(quality_portfolio)s,
                        %(vpin)s, %(ofi)s, %(cvd)s, %(depth_imbalance)s, %(spoofing_score)s,
                        %(htf_trend)s, %(mtf_structure)s, %(ltf_entry_quality)s,
                        %(asset_class)s, %(region)s, %(risk_cluster)s,
                        %(pnl_gross)s, %(pnl_net)s, %(r_multiple)s, %(mae)s, %(mfe)s, %(holding_time_minutes)s,
                        %(regime)s, %(data_health_score)s, %(slippage_bps)s, %(notes)s
                    )
                """

                execute_batch(cursor, sql, events)
                conn.commit()
                cursor.close()

                self.logger.debug(f"✅ Inserted {len(events)} trade events to DB")
                return True

            except Exception as e:
                self.logger.error(f"DB insert failed: {e}")
                conn.rollback()
                return self._fallback_to_file(events, 'trade_events')

    def insert_position_snapshot(self, snapshot: Dict) -> bool:
        """Insertar snapshot de posiciones."""
        with self.get_connection() as conn:
            if not conn:
                return self._fallback_to_file([snapshot], 'position_snapshots')

            try:
                cursor = conn.cursor()
                sql = """
                    INSERT INTO position_snapshots (
                        timestamp, symbol, strategy_id, trade_id,
                        direction, quantity, entry_price, current_price, unrealized_pnl,
                        risk_allocated_pct, stop_loss, take_profit,
                        asset_class, region, risk_cluster
                    ) VALUES (
                        %(timestamp)s, %(symbol)s, %(strategy_id)s, %(trade_id)s,
                        %(direction)s, %(quantity)s, %(entry_price)s, %(current_price)s, %(unrealized_pnl)s,
                        %(risk_allocated_pct)s, %(stop_loss)s, %(take_profit)s,
                        %(asset_class)s, %(region)s, %(risk_cluster)s
                    )
                """
                cursor.execute(sql, snapshot)
                conn.commit()
                cursor.close()
                return True
            except Exception as e:
                self.logger.error(f"Position snapshot insert failed: {e}")
                conn.rollback()
                return self._fallback_to_file([snapshot], 'position_snapshots')

    def insert_risk_snapshot(self, snapshot: Dict) -> bool:
        """Insertar snapshot de riesgo."""
        with self.get_connection() as conn:
            if not conn:
                return self._fallback_to_file([snapshot], 'risk_snapshots')

            try:
                cursor = conn.cursor()
                sql = """
                    INSERT INTO risk_snapshots (
                        timestamp, total_risk_used_pct, total_risk_available_pct, max_risk_allowed_pct,
                        risk_by_asset_class, risk_by_region, risk_by_strategy, risk_by_cluster,
                        symbols_at_limit, strategies_at_limit, clusters_at_limit,
                        portfolio_correlation_avg, herfindahl_index,
                        rejections_last_hour, circuit_breaker_active
                    ) VALUES (
                        %(timestamp)s, %(total_risk_used_pct)s, %(total_risk_available_pct)s, %(max_risk_allowed_pct)s,
                        %(risk_by_asset_class)s, %(risk_by_region)s, %(risk_by_strategy)s, %(risk_by_cluster)s,
                        %(symbols_at_limit)s, %(strategies_at_limit)s, %(clusters_at_limit)s,
                        %(portfolio_correlation_avg)s, %(herfindahl_index)s,
                        %(rejections_last_hour)s, %(circuit_breaker_active)s
                    )
                """
                cursor.execute(sql, snapshot)
                conn.commit()
                cursor.close()
                return True
            except Exception as e:
                self.logger.error(f"Risk snapshot insert failed: {e}")
                conn.rollback()
                return self._fallback_to_file([snapshot], 'risk_snapshots')

    def _fallback_to_file(self, events: List[Dict], table_name: str) -> bool:
        """Fallback: escribir eventos a JSONL."""
        if not self.fallback_enabled:
            self.logger.error("DB failed and fallback disabled")
            return False

        try:
            import json
            from datetime import datetime

            self.fallback_dir.mkdir(parents=True, exist_ok=True)
            filename = self.fallback_dir / f"{table_name}_{datetime.now().strftime('%Y%m%d')}.jsonl"

            with open(filename, 'a') as f:
                for event in events:
                    # Convert datetime to isoformat
                    if 'timestamp' in event and hasattr(event['timestamp'], 'isoformat'):
                        event['timestamp'] = event['timestamp'].isoformat()
                    f.write(json.dumps(event) + '\n')

            self.logger.warning(f"⚠️ DB unavailable, fallback to file: {filename}")
            return True

        except Exception as e:
            self.logger.error(f"Fallback to file failed: {e}")
            return False

    def close(self):
        """Cerrar pool de conexiones."""
        if self.pool:
            self.pool.closeall()
            self.logger.info("DB pool closed")
