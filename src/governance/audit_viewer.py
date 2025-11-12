"""
Audit Log Viewer - Herramienta para consultar y reconstruir decisiones históricas
Permite replay completo de cualquier decisión del sistema.
"""

import json
from typing import Dict, List, Optional, Any
from pathlib import Path
from datetime import datetime, date
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)


@dataclass
class DecisionReconstruction:
    """Reconstrucción completa de una decisión."""
    decision_id: str
    timestamp: datetime
    event_chain: List[Dict]
    data_slice: Optional[Dict]
    module_versions: Dict[str, str]
    config_hashes: Dict[str, str]
    reasoning: str
    outcome: str


class AuditLogViewer:
    """
    Visor de logs de auditoría institucional.
    
    Permite:
    - Consultar eventos históricos con filtros complejos
    - Reconstruir decisiones completas con todo su contexto
    - Reproducir exactamente decisiones para debugging
    - Verificar integridad de la cadena de eventos
    - Generar reportes de auditoría
    """
    
    def __init__(
        self,
        event_store_path: Path,
        data_lineage_path: Path,
        versions_path: Path
    ):
        """
        Inicializa audit viewer.
        
        Args:
            event_store_path: Path al event store
            data_lineage_path: Path al data lineage tracker
            versions_path: Path al version manager
        """
        self.event_store_path = Path(event_store_path)
        self.data_lineage_path = Path(data_lineage_path)
        self.versions_path = Path(versions_path)
        
        logger.info("AuditLogViewer inicializado")
    
    def reconstruct_decision(
        self,
        decision_id: str
    ) -> Optional[DecisionReconstruction]:
        """
        Reconstruye completamente una decisión histórica.
        
        Args:
            decision_id: ID de la decisión a reconstruir
            
        Returns:
            DecisionReconstruction con todo el contexto
        """
        logger.info(f"Reconstructing decision: {decision_id}")
        
        # 1. Buscar evento de decisión
        decision_event = self._find_decision_event(decision_id)
        if not decision_event:
            logger.error(f"Decision event not found: {decision_id}")
            return None
        
        # 2. Buscar eventos relacionados (señales que llevaron a la decisión)
        related_events = self._find_related_events(decision_event)
        
        # 3. Cargar data slice asociado
        data_slice = None
        if 'data_slice_id' in decision_event:
            data_slice = self._load_data_slice(decision_event['data_slice_id'])
        
        # 4. Obtener versiones de módulos y configs
        module_versions = decision_event.get('module_versions', {})
        config_hashes = decision_event.get('config_hashes', {})
        
        # 5. Extraer reasoning y outcome
        payload = decision_event.get('payload', {})
        reasoning = payload.get('reasoning', 'N/A')
        outcome = payload.get('outcome', 'N/A')
        
        # 6. Construir reconstrucción completa
        reconstruction = DecisionReconstruction(
            decision_id=decision_id,
            timestamp=datetime.fromisoformat(decision_event['timestamp']),
            event_chain=[decision_event] + related_events,
            data_slice=data_slice,
            module_versions=module_versions,
            config_hashes=config_hashes,
            reasoning=reasoning,
            outcome=outcome
        )
        
        logger.info(
            f"Decision reconstructed: {decision_id} "
            f"events={len(reconstruction.event_chain)}"
        )
        
        return reconstruction
    
    def query_events(
        self,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        event_type: Optional[str] = None,
        instrument: Optional[str] = None,
        strategy_id: Optional[str] = None,
        outcome: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict]:
        """
        Consulta eventos con filtros avanzados.
        
        Args:
            start_date: Fecha inicio
            end_date: Fecha fin
            event_type: Tipo de evento (SIGNAL, DECISION, EXECUTION)
            instrument: Filtrar por instrumento
            strategy_id: Filtrar por estrategia
            outcome: Filtrar por outcome (EXECUTE, SILENCE, REJECT)
            limit: Máximo eventos a retornar
            
        Returns:
            Lista de eventos que cumplen filtros
        """
        events = []
        
        # Determinar archivos a leer
        if start_date is None:
            start_date = date(2025, 1, 1)
        if end_date is None:
            end_date = date.today()
        
        current = start_date
        while current <= end_date and len(events) < limit:
            file_path = self._get_events_file(current)
            
            if file_path.exists():
                with open(file_path, 'r') as f:
                    for line in f:
                        if len(events) >= limit:
                            break
                        
                        try:
                            event_record = json.loads(line.strip())
                            event = event_record['event']
                            
                            # Aplicar filtros
                            if event_type and event['event_type'] != event_type:
                                continue
                            
                            payload = event.get('payload', {})
                            
                            if instrument and payload.get('instrument') != instrument:
                                continue
                            
                            if strategy_id and payload.get('strategy_id') != strategy_id:
                                continue
                            
                            if outcome and payload.get('outcome') != outcome:
                                continue
                            
                            events.append(event)
                        
                        except (json.JSONDecodeError, KeyError) as e:
                            logger.error(f"Error parsing event: {e}")
                            continue
            
            # Siguiente día
            from datetime import timedelta
            current += timedelta(days=1)
        
        return events
    
    def generate_audit_report(
        self,
        start_date: date,
        end_date: date,
        output_path: Path
    ):
        """
        Genera reporte de auditoría completo para un período.
        
        Args:
            start_date: Fecha inicio del reporte
            end_date: Fecha fin del reporte
            output_path: Path donde guardar el reporte
        """
        logger.info(
            f"Generating audit report: {start_date} to {end_date}"
        )
        
        # Consultar todos los eventos del período
        all_events = self.query_events(
            start_date=start_date,
            end_date=end_date,
            limit=100000
        )
        
        # Agrupar por tipo
        events_by_type = {}
        for event in all_events:
            event_type = event['event_type']
            if event_type not in events_by_type:
                events_by_type[event_type] = []
            events_by_type[event_type].append(event)
        
        # Calcular estadísticas
        stats = {
            'period': {
                'start_date': start_date.isoformat(),
                'end_date': end_date.isoformat()
            },
            'total_events': len(all_events),
            'events_by_type': {
                event_type: len(events)
                for event_type, events in events_by_type.items()
            }
        }
        
        # Estadísticas de decisiones
        decision_events = events_by_type.get('DECISION', [])
        if decision_events:
            outcomes = {}
            for event in decision_events:
                outcome = event.get('payload', {}).get('outcome', 'UNKNOWN')
                outcomes[outcome] = outcomes.get(outcome, 0) + 1
            
            stats['decisions'] = {
                'total': len(decision_events),
                'by_outcome': outcomes
            }
        
        # Estadísticas de ejecuciones
        execution_events = events_by_type.get('EXECUTION', [])
        if execution_events:
            stats['executions'] = {
                'total': len(execution_events)
            }
        
        # Verificar integridad
        integrity_ok = self._verify_chain_integrity_period(start_date, end_date)
        stats['integrity_check'] = {
            'passed': integrity_ok,
            'checked_at': datetime.now().isoformat()
        }
        
        # Generar reporte
        report = {
            'report_type': 'audit_log',
            'generated_at': datetime.now().isoformat(),
            'statistics': stats,
            'sample_events': all_events[:10]  # Primeros 10 como muestra
        }
        
        # Guardar
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, 'w') as f:
            json.dump(report, f, indent=2)
        
        logger.info(f"Audit report saved: {output_path}")
    
    def compare_decisions_between_versions(
        self,
        decision_id_1: str,
        decision_id_2: str
    ) -> Dict[str, Any]:
        """
        Compara dos decisiones (típicamente misma entrada, diferentes versiones).
        
        Args:
            decision_id_1: Primera decisión
            decision_id_2: Segunda decisión
            
        Returns:
            Dict con diferencias encontradas
        """
        recon_1 = self.reconstruct_decision(decision_id_1)
        recon_2 = self.reconstruct_decision(decision_id_2)
        
        if not recon_1 or not recon_2:
            return {'error': 'Could not reconstruct one or both decisions'}
        
        differences = {
            'decision_1': decision_id_1,
            'decision_2': decision_id_2,
            'outcome_differs': recon_1.outcome != recon_2.outcome,
            'reasoning_differs': recon_1.reasoning != recon_2.reasoning,
            'module_version_diffs': self._compare_versions(
                recon_1.module_versions,
                recon_2.module_versions
            ),
            'config_hash_diffs': self._compare_hashes(
                recon_1.config_hashes,
                recon_2.config_hashes
            )
        }
        
        return differences
    
    def _find_decision_event(self, decision_id: str) -> Optional[Dict]:
        """Busca evento de decisión por ID."""
        # Buscar en todos los archivos de eventos
        event_files = sorted(self.event_store_path.glob("events/*.events.jsonl"))
        
        for file_path in event_files:
            with open(file_path, 'r') as f:
                for line in f:
                    try:
                        event_record = json.loads(line.strip())
                        event = event_record['event']
                        
                        if event.get('event_id') == decision_id:
                            return event
                        
                        # También buscar en payload
                        payload = event.get('payload', {})
                        if payload.get('decision_id') == decision_id:
                            return event
                    
                    except (json.JSONDecodeError, KeyError):
                        continue
        
        return None
    
    def _find_related_events(self, decision_event: Dict) -> List[Dict]:
        """Encuentra eventos relacionados a una decisión."""
        related = []
        
        # Buscar eventos con mismo data_slice_id
        data_slice_id = decision_event.get('data_slice_id')
        if not data_slice_id:
            return related
        
        # Buscar en ventana temporal alrededor de la decisión
        decision_time = datetime.fromisoformat(decision_event['timestamp'])
        
        # Buscar en archivo del mismo día
        decision_date = decision_time.date()
        file_path = self._get_events_file(decision_date)
        
        if file_path.exists():
            with open(file_path, 'r') as f:
                for line in f:
                    try:
                        event_record = json.loads(line.strip())
                        event = event_record['event']
                        
                        # Mismo data_slice_id y no es el evento original
                        if (event.get('data_slice_id') == data_slice_id and
                            event.get('event_id') != decision_event.get('event_id')):
                            related.append(event)
                    
                    except (json.JSONDecodeError, KeyError):
                        continue
        
        return related
    
    def _load_data_slice(self, data_slice_id: str) -> Optional[Dict]:
        """Carga data slice desde lineage tracker."""
        # Parsear data_slice_id para obtener path
        parts = data_slice_id.split('_')
        if len(parts) >= 2:
            try:
                timestamp_ms = int(parts[1])
                dt = datetime.fromtimestamp(timestamp_ms / 1000)
                year_month = dt.strftime('%Y/%m')
                
                slice_path = (
                    self.data_lineage_path / year_month / f"{data_slice_id}.json"
                )
                
                if slice_path.exists():
                    with open(slice_path, 'r') as f:
                        return json.load(f)
            except (ValueError, IndexError):
                pass
        
        return None
    
    def _verify_chain_integrity_period(
        self,
        start_date: date,
        end_date: date
    ) -> bool:
        """Verifica integridad de cadena en un período."""
        events = self.query_events(
            start_date=start_date,
            end_date=end_date,
            limit=100000
        )
        
        if not events:
            return True
        
        for i in range(1, len(events)):
            prev_event = events[i - 1]
            current_event = events[i]
            
            if current_event.get('prev_event_hash') != prev_event.get('event_hash'):
                logger.error(
                    f"Chain integrity breach between "
                    f"{prev_event.get('event_id')} and {current_event.get('event_id')}"
                )
                return False
        
        return True
    
    def _compare_versions(
        self,
        versions_1: Dict[str, str],
        versions_2: Dict[str, str]
    ) -> Dict[str, tuple]:
        """Compara dos dicts de versiones."""
        diffs = {}
        
        all_modules = set(versions_1.keys()) | set(versions_2.keys())
        
        for module in all_modules:
            v1 = versions_1.get(module)
            v2 = versions_2.get(module)
            
            if v1 != v2:
                diffs[module] = (v1, v2)
        
        return diffs
    
    def _compare_hashes(
        self,
        hashes_1: Dict[str, str],
        hashes_2: Dict[str, str]
    ) -> Dict[str, tuple]:
        """Compara dos dicts de hashes."""
        diffs = {}
        
        all_configs = set(hashes_1.keys()) | set(hashes_2.keys())
        
        for config in all_configs:
            h1 = hashes_1.get(config)
            h2 = hashes_2.get(config)
            
            if h1 != h2:
                diffs[config] = (h1, h2)
        
        return diffs
    
    def _get_events_file(self, event_date: date) -> Path:
        """Obtiene path del archivo de eventos para una fecha."""
        filename = f"{event_date.strftime('%Y-%m-%d')}.events.jsonl"
        return self.event_store_path / "events" / filename
