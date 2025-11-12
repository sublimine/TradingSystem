"""
Event Store - Sistema de eventos inmutable con firma HMAC encadenada
Implementa append-only event log con verificación de integridad criptográfica.
"""

import json
import hashlib
import hmac
from typing import Dict, List, Optional, Any
from datetime import datetime, date
from pathlib import Path
import logging

logger = logging.getLogger(__name__)



from enum import Enum


class EventType(Enum):
    """Tipos de eventos del sistema."""
    MODEL_TRAINED = "model_trained"
    MODEL_DEPLOYED = "model_deployed"
    SIGNAL_GENERATED = "signal_generated"
    ORDER_PLACED = "order_placed"
    ORDER_FILLED = "order_filled"
    ORDER_REJECTED = "order_rejected"
    ORDER_CANCELLED = "order_cancelled"
    POSITION_OPENED = "position_opened"
    POSITION_CLOSED = "position_closed"
    RISK_LIMIT_BREACHED = "risk_limit_breached"
    CIRCUIT_BREAKER_TRIPPED = "circuit_breaker_tripped"
    DATA_QUALITY_ISSUE = "data_quality_issue"
    SYSTEM_STARTED = "system_started"
    SYSTEM_STOPPED = "system_stopped"

class Event:
    """Evento inmutable con firma HMAC."""
    
    def __init__(
        self,
        event_type: str,
        payload: Dict[str, Any],
        event_id: str,
        timestamp: datetime,
        module_versions: Dict[str, str],
        config_hashes: Dict[str, str],
        data_slice_id: Optional[str] = None,
        prev_event_hash: Optional[str] = None
    ):
        self.event_type = event_type
        self.payload = payload
        self.event_id = event_id
        self.timestamp = timestamp
        self.module_versions = module_versions
        self.config_hashes = config_hashes
        self.data_slice_id = data_slice_id
        self.prev_event_hash = prev_event_hash
        self.event_hash = self._compute_hash()
    
    def _compute_hash(self) -> str:
        """Calcula SHA256 hash del evento."""
        content = {
            'event_type': self.event_type,
            'event_id': self.event_id,
            'timestamp': self.timestamp.isoformat(),
            'payload': self.payload,
            'module_versions': self.module_versions,
            'config_hashes': self.config_hashes,
            'data_slice_id': self.data_slice_id,
            'prev_event_hash': self.prev_event_hash
        }
        
        content_json = json.dumps(content, sort_keys=True)
        return hashlib.sha256(content_json.encode()).hexdigest()
    
    def to_dict(self) -> Dict:
        """Serializa evento a dict."""
        return {
            'event_type': self.event_type,
            'event_id': self.event_id,
            'timestamp': self.timestamp.isoformat(),
            'payload': self.payload,
            'module_versions': self.module_versions,
            'config_hashes': self.config_hashes,
            'data_slice_id': self.data_slice_id,
            'prev_event_hash': self.prev_event_hash,
            'event_hash': self.event_hash
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'Event':
        """Deserializa evento desde dict."""
        return cls(
            event_type=data['event_type'],
            payload=data['payload'],
            event_id=data['event_id'],
            timestamp=datetime.fromisoformat(data['timestamp']),
            module_versions=data['module_versions'],
            config_hashes=data['config_hashes'],
            data_slice_id=data.get('data_slice_id'),
            prev_event_hash=data.get('prev_event_hash')
        )


class EventStore:
    """
    Event Store institucional con WORM y HMAC chain.
    
    Características:
    - Append-only: eventos nunca se modifican ni eliminan
    - HMAC chain: cada evento firma el hash del anterior
    - Rotación diaria: archivos separados por día
    - Verificación de integridad: valida cadena completa
    - Indexación eficiente: búsqueda por tipo, fecha, ID
    """
    
    def __init__(
        self,
        store_path: Path,
        hmac_key: str = "institutional_trading_system_key_2025"
    ):
        """
        Inicializa Event Store.
        
        Args:
            store_path: Directorio base para eventos
            hmac_key: Clave secreta para HMAC (cambiar en producción)
        """
        self.store_path = Path(store_path)
        self.events_dir = self.store_path / "events"
        self.integrity_dir = self.store_path / "integrity"
        
        # Crear directorios
        self.events_dir.mkdir(parents=True, exist_ok=True)
        self.integrity_dir.mkdir(parents=True, exist_ok=True)
        
        self.hmac_key = hmac_key.encode()
        self._last_event_hash: Optional[str] = None
        self._current_date = date.today()
        self._current_file_handle = None
        
        # Cargar último hash si existe
        self._load_last_hash()
        
        logger.info(f"EventStore inicializado: {self.store_path}")
    
    def append_event(
        self,
        event_type: str,
        payload: Dict[str, Any],
        event_id: str,
        module_versions: Dict[str, str],
        config_hashes: Dict[str, str],
        data_slice_id: Optional[str] = None
    ) -> Event:
        """
        Añade evento al store con firma HMAC.
        
        Args:
            event_type: Tipo de evento (SIGNAL, DECISION, EXECUTION, etc)
            payload: Contenido del evento
            event_id: ID único del evento
            module_versions: Versiones de módulos activos
            config_hashes: Hashes de configuraciones
            data_slice_id: ID del slice de datos asociado
            
        Returns:
            Evento creado y persistido
        """
        # Crear evento
        event = Event(
            event_type=event_type,
            payload=payload,
            event_id=event_id,
            timestamp=datetime.now(),
            module_versions=module_versions,
            config_hashes=config_hashes,
            data_slice_id=data_slice_id,
            prev_event_hash=self._last_event_hash
        )
        
        # Calcular HMAC
        event_hmac = self._compute_hmac(event)
        
        # Persistir
        self._write_event(event, event_hmac)
        
        # Actualizar último hash
        self._last_event_hash = event.event_hash
        
        return event
    
    def get_events(
        self,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        event_type: Optional[str] = None,
        event_id: Optional[str] = None,
        limit: int = 1000
    ) -> List[Event]:
        """
        Consulta eventos con filtros.
        
        Args:
            start_date: Fecha inicio (inclusive)
            end_date: Fecha fin (inclusive)
            event_type: Filtrar por tipo de evento
            event_id: Buscar evento específico por ID
            limit: Máximo número de eventos a retornar
            
        Returns:
            Lista de eventos que cumplen filtros
        """
        events = []
        
        # Determinar archivos a leer
        if start_date is None:
            start_date = date(2025, 1, 1)  # Fecha arbitraria pasada
        if end_date is None:
            end_date = date.today()
        
        current = start_date
        while current <= end_date and len(events) < limit:
            file_path = self._get_file_path(current)
            
            if file_path.exists():
                with open(file_path, 'r') as f:
                    for line in f:
                        if len(events) >= limit:
                            break
                        
                        try:
                            event_data = json.loads(line.strip())
                            event = Event.from_dict(event_data['event'])
                            
                            # Aplicar filtros
                            if event_type and event.event_type != event_type:
                                continue
                            if event_id and event.event_id != event_id:
                                continue
                            
                            events.append(event)
                        
                        except (json.JSONDecodeError, KeyError) as e:
                            logger.error(f"Error parsing event: {e}")
                            continue
            
            # Siguiente día
            from datetime import timedelta
            current += timedelta(days=1)
        
        return events
    
    def verify_chain_integrity(
        self,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None
    ) -> bool:
        """
        Verifica integridad de la cadena de eventos.
        
        Valida que cada evento N contiene el hash correcto del evento N-1.
        
        Args:
            start_date: Fecha inicio para verificación
            end_date: Fecha fin para verificación
            
        Returns:
            True si la cadena es íntegra, False si detecta corrupción
        """
        events = self.get_events(start_date=start_date, end_date=end_date, limit=100000)
        
        if not events:
            return True
        
        for i in range(1, len(events)):
            prev_event = events[i - 1]
            current_event = events[i]
            
            # Verificar que current_event.prev_event_hash == prev_event.event_hash
            if current_event.prev_event_hash != prev_event.event_hash:
                logger.error(
                    f"CHAIN_INTEGRITY_BREACH: Event {current_event.event_id} "
                    f"has invalid prev_hash. Expected {prev_event.event_hash}, "
                    f"got {current_event.prev_event_hash}"
                )
                return False
        
        logger.info(f"Chain integrity verified: {len(events)} events OK")
        return True
    
    def _compute_hmac(self, event: Event) -> str:
        """Calcula HMAC del evento."""
        content = event.to_dict()
        content_json = json.dumps(content, sort_keys=True)
        return hmac.new(self.hmac_key, content_json.encode(), hashlib.sha256).hexdigest()
    
    def _write_event(self, event: Event, event_hmac: str):
        """Escribe evento a archivo append-only."""
        today = date.today()
        
        # Si cambió el día, rotar archivo
        if today != self._current_date:
            if self._current_file_handle:
                self._current_file_handle.close()
            self._current_date = today
            self._current_file_handle = None
        
        file_path = self._get_file_path(today)
        
        # Escribir evento como línea JSON
        event_record = {
            'event': event.to_dict(),
            'hmac': event_hmac,
            'written_at': datetime.now().isoformat()
        }
        
        with open(file_path, 'a') as f:
            f.write(json.dumps(event_record) + '\n')
    
    def _get_file_path(self, event_date: date) -> Path:
        """Obtiene path del archivo para una fecha."""
        filename = f"{event_date.strftime('%Y-%m-%d')}.events.jsonl"
        return self.events_dir / filename
    
    def _load_last_hash(self):
        """Carga el último hash de evento del archivo más reciente."""
        # Buscar archivo más reciente
        event_files = sorted(self.events_dir.glob("*.events.jsonl"), reverse=True)
        
        if not event_files:
            return
        
        latest_file = event_files[0]
        
        # Leer última línea
        try:
            with open(latest_file, 'r') as f:
                lines = f.readlines()
                if lines:
                    last_line = lines[-1].strip()
                    event_record = json.loads(last_line)
                    self._last_event_hash = event_record['event']['event_hash']
        except (json.JSONDecodeError, KeyError, IndexError) as e:
            logger.error(f"Error loading last hash: {e}")
    
    def get_stats(self) -> Dict:
        """Obtiene estadísticas del event store."""
        event_files = list(self.events_dir.glob("*.events.jsonl"))
        
        total_events = 0
        total_size_bytes = 0
        
        for file_path in event_files:
            total_size_bytes += file_path.stat().st_size
            with open(file_path, 'r') as f:
                total_events += sum(1 for _ in f)
        
        return {
            'total_events': total_events,
            'total_files': len(event_files),
            'total_size_mb': total_size_bytes / (1024 * 1024),
            'last_event_hash': self._last_event_hash,
            'store_path': str(self.store_path)
        }
