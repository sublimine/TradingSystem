"""
Modulo de reconexion automatica a MT5
Implementa backoff exponencial y reintentos
"""

import MetaTrader5 as mt5
import time
from typing import Optional
import logging

logger = logging.getLogger(__name__)

class MT5Connector:
    """Manejador de conexion con reconexion automatica"""
    
    def __init__(self, max_retries: int = 5, base_delay: float = 2.0):
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.connected = False
        self.connection_attempts = 0
    
    def connect(self) -> bool:
        """Conecta a MT5 con reintentos exponenciales"""
        for attempt in range(1, self.max_retries + 1):
            self.connection_attempts += 1
            
            logger.info(f"Intento de conexion {attempt}/{self.max_retries}")
            
            if mt5.initialize():
                self.connected = True
                account = mt5.account_info()
                logger.info(f"Conectado exitosamente: {account.server} | {account.login}")
                return True
            
            if attempt < self.max_retries:
                delay = self.base_delay * (2 ** (attempt - 1))  # Backoff exponencial
                logger.warning(f"Fallo conexion, reintentando en {delay}s...")
                time.sleep(delay)
        
        logger.error("No se pudo conectar a MT5 despues de todos los intentos")
        self.connected = False
        return False
    
    def ensure_connected(self) -> bool:
        """Verifica conexion y reconecta si es necesario"""
        if not self.is_connected():
            logger.warning("Conexion perdida, reconectando...")
            return self.connect()
        return True
    
    def is_connected(self) -> bool:
        """Verifica si MT5 esta conectado"""
        try:
            account = mt5.account_info()
            return account is not None
        except:
            return False
    
    def disconnect(self):
        """Desconecta de MT5"""
        if self.connected:
            mt5.shutdown()
            self.connected = False
            logger.info("Desconectado de MT5")
    
    def __enter__(self):
        """Context manager entry"""
        self.connect()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.disconnect()
