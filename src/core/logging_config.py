"""
Logging institucional centralizado
Mandato 6 - Observabilidad P0
"""
import logging
import sys
from datetime import datetime
from pathlib import Path


class InstitutionalLogger:
    """Logger centralizado con niveles institucionales."""

    _initialized = False
    _loggers = {}

    @classmethod
    def setup(cls, log_level: str = "INFO", log_dir: str = "logs"):
        """
        Configuración global de logging institucional.

        Args:
            log_level: Nivel mínimo (DEBUG, INFO, WARNING, ERROR, CRITICAL)
            log_dir: Directorio para logs (default: logs/)
        """
        if cls._initialized:
            return

        # Crear directorio de logs
        log_path = Path(log_dir)
        log_path.mkdir(exist_ok=True)

        # Formato institucional
        log_format = (
            "%(asctime)s | %(name)-30s | %(levelname)-8s | "
            "%(funcName)-20s | %(message)s"
        )
        date_format = "%Y-%m-%d %H:%M:%S"

        # Handler para consola
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(getattr(logging, log_level))
        console_handler.setFormatter(logging.Formatter(log_format, date_format))

        # Handler para archivo (rotating diario)
        today = datetime.now().strftime("%Y%m%d")
        file_handler = logging.FileHandler(
            log_path / f"sublimine_{today}.log",
            encoding="utf-8"
        )
        file_handler.setLevel(logging.DEBUG)  # Archivo captura todo
        file_handler.setFormatter(logging.Formatter(log_format, date_format))

        # Configurar root logger
        root_logger = logging.getLogger()
        root_logger.setLevel(logging.DEBUG)
        root_logger.addHandler(console_handler)
        root_logger.addHandler(file_handler)

        cls._initialized = True

        root_logger.info("LOGGING_INIT: Sistema de logging institucional inicializado")

    @classmethod
    def get_logger(cls, name: str) -> logging.Logger:
        """
        Obtiene logger con nombre específico.

        Args:
            name: Nombre del módulo (ej: 'sublimine.core.arbiter')

        Returns:
            Logger configurado
        """
        if not cls._initialized:
            cls.setup()

        if name not in cls._loggers:
            logger = logging.getLogger(f"sublimine.{name}")
            cls._loggers[name] = logger

        return cls._loggers[name]


# Logger global para uso directo
def get_logger(module_name: str) -> logging.Logger:
    """
    Shortcut para obtener logger institucional.

    Uso:
        from src.core.logging_config import get_logger
        logger = get_logger(__name__)
        logger.info("Mensaje institucional")
    """
    return InstitutionalLogger.get_logger(module_name)


# Eventos institucionales clave (códigos estandarizados)
class LogEvent:
    """Códigos de eventos institucionales para logging estructurado."""

    # DecisionLedger
    LEDGER_WRITE = "LEDGER_WRITE"
    LEDGER_DUPLICATE = "LEDGER_DUPLICATE"

    # ConflictArbiter
    ARBITER_EXECUTE = "ARBITER_EXECUTE"
    ARBITER_REJECT = "ARBITER_REJECT"
    ARBITER_SILENCE = "ARBITER_SILENCE"
    ARBITER_CONFLICT = "ARBITER_CONFLICT"

    # RiskManager
    RISK_APPROVED = "RISK_APPROVED"
    RISK_REJECTED = "RISK_REJECTED"
    RISK_EXPOSURE_LIMIT = "RISK_EXPOSURE_LIMIT"
    RISK_QUALITY_LOW = "RISK_QUALITY_LOW"
    CIRCUIT_BREAKER_OPEN = "CIRCUIT_BREAKER_OPEN"
    CIRCUIT_BREAKER_CLOSE = "CIRCUIT_BREAKER_CLOSE"

    # RegimeEngine
    REGIME_CHANGE = "REGIME_CHANGE"
    REGIME_UPDATE = "REGIME_UPDATE"

    # Trading
    TRADE_OPEN = "TRADE_OPEN"
    TRADE_CLOSE = "TRADE_CLOSE"
    TRADE_SL_HIT = "TRADE_SL_HIT"
    TRADE_TP_HIT = "TRADE_TP_HIT"

    # System
    SYSTEM_START = "SYSTEM_START"
    SYSTEM_STOP = "SYSTEM_STOP"
    SYSTEM_ERROR = "SYSTEM_ERROR"
    DATA_FEED_ERROR = "DATA_FEED_ERROR"


def log_institutional_event(
    logger: logging.Logger,
    event_code: str,
    level: str = "INFO",
    **kwargs
):
    """
    Log de evento institucional estructurado.

    Args:
        logger: Logger a usar
        event_code: Código de evento (ver LogEvent)
        level: Nivel de log (INFO, WARNING, ERROR)
        **kwargs: Campos adicionales del evento

    Ejemplo:
        log_institutional_event(
            logger,
            LogEvent.RISK_REJECTED,
            level="WARNING",
            signal_id="S001",
            reason="exposure_limit",
            current_exposure=5.9,
            max_exposure=6.0
        )
    """
    # Construir mensaje estructurado
    fields = " | ".join(f"{k}={v}" for k, v in kwargs.items())
    message = f"{event_code}: {fields}" if fields else event_code

    log_level = getattr(logging, level.upper(), logging.INFO)
    logger.log(log_level, message)
