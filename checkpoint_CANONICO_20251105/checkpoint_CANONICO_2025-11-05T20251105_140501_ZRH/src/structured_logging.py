"""
Modulo de logging estructurado en JSON
Para auditoria y analisis automatizado
"""

import logging
import json
from datetime import datetime
from typing import Dict, Any, Optional

class JSONFormatter(logging.Formatter):
    """Formateador de logs en JSON"""
    
    def format(self, record: logging.LogRecord) -> str:
        """Convierte LogRecord a JSON estructurado"""
        
        log_data = {
            'timestamp': datetime.utcnow().isoformat() + 'Z',
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage()
        }
        
        # Agregar campos adicionales si existen
        if hasattr(record, 'strategy'):
            log_data['strategy'] = record.strategy
        if hasattr(record, 'symbol'):
            log_data['symbol'] = record.symbol
        if hasattr(record, 'action'):
            log_data['action'] = record.action
        if hasattr(record, 'price'):
            log_data['price'] = record.price
        if hasattr(record, 'size'):
            log_data['size'] = record.size
        if hasattr(record, 'pnl'):
            log_data['pnl'] = record.pnl
        if hasattr(record, 'balance'):
            log_data['balance'] = record.balance
        if hasattr(record, 'trade_id'):
            log_data['trade_id'] = record.trade_id
        
        # Agregar excepciones si existen
        if record.exc_info:
            log_data['exception'] = self.formatException(record.exc_info)
        
        return json.dumps(log_data)

def setup_structured_logging(log_path: str, level: int = logging.INFO) -> logging.Logger:
    """
    Configura logging estructurado con JSON
    
    Args:
        log_path: Ruta del archivo de log
        level: Nivel de logging (default: INFO)
        
    Returns:
        Logger configurado
    """
    logger = logging.getLogger('trading_system')
    logger.setLevel(level)
    
    # Handler para archivo JSON
    json_handler = logging.FileHandler(log_path, encoding='utf-8')
    json_handler.setLevel(level)
    json_handler.setFormatter(JSONFormatter())
    
    # Handler para consola (formato legible)
    console_handler = logging.StreamHandler()
    console_handler.setLevel(level)
    console_format = logging.Formatter(
        '%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    console_handler.setFormatter(console_format)
    
    logger.addHandler(json_handler)
    logger.addHandler(console_handler)
    
    return logger

def log_signal(logger: logging.Logger, strategy: str, symbol: str, 
               action: str, price: float, size: float, confidence: float):
    """Log de señal generada"""
    logger.info(
        f"Signal: {action} {symbol} @ {price}",
        extra={
            'strategy': strategy,
            'symbol': symbol,
            'action': action,
            'price': price,
            'size': size,
            'confidence': confidence
        }
    )

def log_trade_execution(logger: logging.Logger, trade_id: int, symbol: str,
                       action: str, price: float, size: float):
    """Log de ejecucion de trade"""
    logger.info(
        f"Trade executed: {action} {size} {symbol} @ {price}",
        extra={
            'trade_id': trade_id,
            'symbol': symbol,
            'action': action,
            'price': price,
            'size': size
        }
    )

def log_trade_closed(logger: logging.Logger, trade_id: int, symbol: str,
                    pnl: float, balance: float):
    """Log de cierre de trade"""
    logger.info(
        f"Trade closed: {symbol} PnL: ${pnl:.2f}",
        extra={
            'trade_id': trade_id,
            'symbol': symbol,
            'pnl': pnl,
            'balance': balance
        }
    )

def log_error_with_context(logger: logging.Logger, error: Exception,
                          context: Dict[str, Any]):
    """Log de error con contexto adicional"""
    logger.error(
        f"Error: {str(error)}",
        exc_info=True,
        extra=context
    )
