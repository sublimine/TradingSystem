"""
Multi-Source Data Manager - Gestión de múltiples fuentes con fallback automático
Conectividad redundante con health checking y failover.
"""

import logging
from typing import Dict, List, Optional, Callable
from datetime import datetime, timedelta
from enum import Enum
import time
from dataclasses import dataclass

logger = logging.getLogger(__name__)


class SourceStatus(Enum):
    """Estado de una fuente de datos."""
    ACTIVE = "active"
    DEGRADED = "degraded"
    FAILED = "failed"
    UNKNOWN = "unknown"


@dataclass
class SourceHealth:
    """Salud de una fuente de datos."""
    source_name: str
    status: SourceStatus
    last_success: Optional[datetime]
    last_failure: Optional[datetime]
    consecutive_failures: int
    latency_ms: float
    uptime_pct: float
    error_rate_pct: float


class DataSource:
    """Fuente de datos abstracta."""
    
    def __init__(self, name: str):
        self.name = name
        self.status = SourceStatus.UNKNOWN
        self._last_success: Optional[datetime] = None
        self._last_failure: Optional[datetime] = None
        self._consecutive_failures = 0
        self._success_count = 0
        self._failure_count = 0
        self._latencies: List[float] = []
        
    def connect(self) -> bool:
        """Establece conexión. Implementar en subclases."""
        raise NotImplementedError
    
    def disconnect(self):
        """Cierra conexión. Implementar en subclases."""
        raise NotImplementedError
    
    def get_latest_bars(self, instrument: str, count: int) -> Optional[List[Dict]]:
        """Obtiene últimas barras. Implementar en subclases."""
        raise NotImplementedError
    
    def is_connected(self) -> bool:
        """Verifica si está conectado. Implementar en subclases."""
        raise NotImplementedError
    
    def record_success(self, latency_ms: float):
        """Registra operación exitosa."""
        self._last_success = datetime.now()
        self._consecutive_failures = 0
        self._success_count += 1
        self._latencies.append(latency_ms)
        
        if len(self._latencies) > 100:
            self._latencies.pop(0)
        
        if self.status == SourceStatus.FAILED:
            self.status = SourceStatus.ACTIVE
            logger.info(f"Source {self.name} recovered")
    
    def record_failure(self, error: Exception):
        """Registra operación fallida."""
        self._last_failure = datetime.now()
        self._consecutive_failures += 1
        self._failure_count += 1
        
        if self._consecutive_failures >= 3:
            self.status = SourceStatus.FAILED
            logger.error(f"Source {self.name} marked as FAILED after {self._consecutive_failures} failures")
        elif self._consecutive_failures >= 1:
            self.status = SourceStatus.DEGRADED
    
    def get_health(self) -> SourceHealth:
        """Obtiene métricas de salud."""
        total_ops = self._success_count + self._failure_count
        uptime_pct = (self._success_count / total_ops * 100) if total_ops > 0 else 0
        error_rate_pct = (self._failure_count / total_ops * 100) if total_ops > 0 else 0
        avg_latency = sum(self._latencies) / len(self._latencies) if self._latencies else 0
        
        return SourceHealth(
            source_name=self.name,
            status=self.status,
            last_success=self._last_success,
            last_failure=self._last_failure,
            consecutive_failures=self._consecutive_failures,
            latency_ms=avg_latency,
            uptime_pct=uptime_pct,
            error_rate_pct=error_rate_pct
        )


class PostgreSQLSource(DataSource):
    """Fuente de datos PostgreSQL."""
    
    def __init__(self, name: str, connection_string: str):
        super().__init__(name)
        self.connection_string = connection_string
        self._connection = None
    
    def connect(self) -> bool:
        """Conecta a PostgreSQL."""
        try:
            # NOTA: Requiere psycopg2
            # import psycopg2
            # self._connection = psycopg2.connect(self.connection_string)
            logger.info(f"PostgreSQL source {self.name} connected (simulated)")
            self.status = SourceStatus.ACTIVE
            return True
        except Exception as e:
            logger.error(f"Failed to connect to PostgreSQL {self.name}: {e}")
            self.status = SourceStatus.FAILED
            return False
    
    def disconnect(self):
        """Desconecta de PostgreSQL."""
        if self._connection:
            # self._connection.close()
            logger.info(f"PostgreSQL source {self.name} disconnected")
            self._connection = None
    
    def get_latest_bars(self, instrument: str, count: int) -> Optional[List[Dict]]:
        """Obtiene últimas barras de PostgreSQL."""
        start_time = time.time()
        
        try:
            # Simulación - en producción ejecutaría query SQL
            # cursor = self._connection.cursor()
            # cursor.execute("SELECT * FROM bars WHERE instrument = %s ORDER BY timestamp DESC LIMIT %s", (instrument, count))
            # rows = cursor.fetchall()
            
            latency_ms = (time.time() - start_time) * 1000
            self.record_success(latency_ms)
            
            # Retornar datos simulados
            return []
        
        except Exception as e:
            self.record_failure(e)
            logger.error(f"PostgreSQL {self.name} query failed: {e}")
            return None
    
    def is_connected(self) -> bool:
        """Verifica conexión."""
        return self._connection is not None


class MT5Source(DataSource):
    """Fuente de datos MetaTrader 5."""
    
    def __init__(self, name: str):
        super().__init__(name)
        self._mt5_initialized = False
    
    def connect(self) -> bool:
        """Conecta a MT5."""
        try:
            # NOTA: Requiere MetaTrader5 package
            # import MetaTrader5 as mt5
            # if not mt5.initialize():
            #     raise Exception("MT5 initialization failed")
            
            logger.info(f"MT5 source {self.name} connected (simulated)")
            self._mt5_initialized = True
            self.status = SourceStatus.ACTIVE
            return True
        
        except Exception as e:
            logger.error(f"Failed to connect to MT5 {self.name}: {e}")
            self.status = SourceStatus.FAILED
            return False
    
    def disconnect(self):
        """Desconecta de MT5."""
        if self._mt5_initialized:
            # mt5.shutdown()
            logger.info(f"MT5 source {self.name} disconnected")
            self._mt5_initialized = False
    
    def get_latest_bars(self, instrument: str, count: int) -> Optional[List[Dict]]:
        """Obtiene últimas barras de MT5."""
        start_time = time.time()
        
        try:
            # Simulación - en producción usaría mt5.copy_rates_from_pos
            # rates = mt5.copy_rates_from_pos(instrument, mt5.TIMEFRAME_M1, 0, count)
            
            latency_ms = (time.time() - start_time) * 1000
            self.record_success(latency_ms)
            
            return []
        
        except Exception as e:
            self.record_failure(e)
            logger.error(f"MT5 {self.name} query failed: {e}")
            return None
    
    def is_connected(self) -> bool:
        """Verifica conexión."""
        return self._mt5_initialized


class MultiSourceDataManager:
    """
    Gestor de múltiples fuentes con failover automático.
    
    Features:
    - Primary/secondary sources con prioridad
    - Health checking continuo
    - Failover automático cuando primary falla
    - Reconciliación de datos entre fuentes
    - Métricas de calidad por fuente
    """
    
    def __init__(
        self,
        primary_source: DataSource,
        secondary_sources: List[DataSource],
        health_check_interval_seconds: int = 30,
        max_divergence_pips: float = 5.0
    ):
        """
        Inicializa manager.
        
        Args:
            primary_source: Fuente primaria
            secondary_sources: Fuentes secundarias (fallback)
            health_check_interval_seconds: Intervalo de health check
            max_divergence_pips: Divergencia máxima entre fuentes
        """
        self.primary_source = primary_source
        self.secondary_sources = secondary_sources
        self.health_check_interval = health_check_interval_seconds
        self.max_divergence_pips = max_divergence_pips
        
        self._active_source: DataSource = primary_source
        self._last_health_check: Optional[datetime] = None
        self._divergence_warnings: List[Dict] = []
        
        logger.info(
            f"MultiSourceDataManager initialized: "
            f"primary={primary_source.name}, "
            f"secondaries={[s.name for s in secondary_sources]}"
        )
    
    def initialize(self) -> bool:
        """Inicializa todas las fuentes."""
        success = True
        
        # Conectar fuente primaria
        if not self.primary_source.connect():
            logger.error(f"Failed to connect primary source {self.primary_source.name}")
            success = False
        
        # Conectar fuentes secundarias
        for source in self.secondary_sources:
            if not source.connect():
                logger.warning(f"Failed to connect secondary source {source.name}")
        
        return success
    
    def shutdown(self):
        """Cierra todas las conexiones."""
        self.primary_source.disconnect()
        
        for source in self.secondary_sources:
            source.disconnect()
        
        logger.info("MultiSourceDataManager shutdown complete")
    
    def get_latest_bars(
        self,
        instrument: str,
        count: int
    ) -> Optional[List[Dict]]:
        """
        Obtiene últimas barras con failover automático.
        
        Args:
            instrument: Instrumento
            count: Número de barras
            
        Returns:
            Lista de barras o None si todas las fuentes fallan
        """
        # Health check periódico
        self._perform_health_check()
        
        # Intentar con fuente activa
        bars = self._active_source.get_latest_bars(instrument, count)
        
        if bars is not None:
            # Reconciliar con otras fuentes si están disponibles
            self._reconcile_data(instrument, bars)
            return bars
        
        # Si falla, intentar failover
        logger.warning(
            f"Active source {self._active_source.name} failed, "
            f"attempting failover"
        )
        
        return self._failover_and_retry(instrument, count)
    
    def _failover_and_retry(
        self,
        instrument: str,
        count: int
    ) -> Optional[List[Dict]]:
        """Ejecuta failover a fuentes secundarias."""
        # Intentar primero recuperar fuente primaria si no es la activa
        if self._active_source != self.primary_source:
            if self.primary_source.status != SourceStatus.FAILED:
                logger.info("Attempting to restore primary source")
                bars = self.primary_source.get_latest_bars(instrument, count)
                
                if bars is not None:
                    self._active_source = self.primary_source
                    logger.info("Primary source restored")
                    return bars
        
        # Intentar fuentes secundarias
        for source in self.secondary_sources:
            if source.status == SourceStatus.FAILED:
                continue
            
            logger.info(f"Failing over to {source.name}")
            bars = source.get_latest_bars(instrument, count)
            
            if bars is not None:
                self._active_source = source
                logger.info(f"Failover successful to {source.name}")
                return bars
        
        logger.error("All data sources failed")
        return None
    
    def _perform_health_check(self):
        """Ejecuta health check periódico."""
        now = datetime.now()
        
        if (self._last_health_check is None or
            (now - self._last_health_check).total_seconds() >= self.health_check_interval):
            
            # Check primary
            if not self.primary_source.is_connected():
                logger.warning(f"Primary source {self.primary_source.name} disconnected")
                self.primary_source.status = SourceStatus.FAILED
            
            # Check secondaries
            for source in self.secondary_sources:
                if not source.is_connected():
                    logger.warning(f"Secondary source {source.name} disconnected")
                    source.status = SourceStatus.FAILED
            
            self._last_health_check = now
    
    def _reconcile_data(self, instrument: str, primary_bars: List[Dict]):
        """
        Reconcilia datos entre fuentes.
        
        Compara precios de múltiples fuentes y alerta si hay divergencia.
        """
        if not self.secondary_sources:
            return
        
        # Obtener dato de una fuente secundaria para comparar
        for source in self.secondary_sources:
            if source.status != SourceStatus.ACTIVE:
                continue
            
            secondary_bars = source.get_latest_bars(instrument, 1)
            
            if secondary_bars and primary_bars:
                # Comparar último precio
                primary_close = primary_bars[-1].get('close', 0)
                secondary_close = secondary_bars[-1].get('close', 0)
                
                divergence_pips = abs(primary_close - secondary_close) * 10000
                
                if divergence_pips > self.max_divergence_pips:
                    warning = {
                        'timestamp': datetime.now(),
                        'instrument': instrument,
                        'primary_source': self._active_source.name,
                        'secondary_source': source.name,
                        'primary_price': primary_close,
                        'secondary_price': secondary_close,
                        'divergence_pips': divergence_pips
                    }
                    
                    self._divergence_warnings.append(warning)
                    
                    logger.warning(
                        f"Price divergence detected: {instrument} "
                        f"{self._active_source.name}={primary_close:.5f} "
                        f"{source.name}={secondary_close:.5f} "
                        f"(divergence={divergence_pips:.1f} pips)"
                    )
            
            break  # Solo comparar con una fuente secundaria
    
    def get_health_report(self) -> Dict:
        """Obtiene reporte completo de salud."""
        report = {
            'active_source': self._active_source.name,
            'primary_health': self.primary_source.get_health(),
            'secondary_health': [
                source.get_health() for source in self.secondary_sources
            ],
            'recent_divergences': self._divergence_warnings[-10:],
            'last_health_check': (
                self._last_health_check.isoformat()
                if self._last_health_check else None
            )
        }
        
        return report