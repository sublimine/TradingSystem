"""
Data Lineage Tracker - Rastreo completo de datos que producen cada decisión
Captura snapshots de datos con hashing determinístico para reproducibilidad.
"""

import json
import hashlib
import pandas as pd
from typing import Dict, Any, Optional
from pathlib import Path
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class DataSlice:
    """Snapshot inmutable de datos de entrada para un tick."""
    
    def __init__(
        self,
        data_slice_id: str,
        timestamp: datetime,
        bars_by_instrument: Dict[str, pd.DataFrame],
        features_by_instrument: Dict[str, Dict],
        regime_states: Dict[str, Dict],
        portfolio_state: Dict[str, Any]
    ):
        self.data_slice_id = data_slice_id
        self.timestamp = timestamp
        self.bars_by_instrument = bars_by_instrument
        self.features_by_instrument = features_by_instrument
        self.regime_states = regime_states
        self.portfolio_state = portfolio_state
    
    def to_dict(self) -> Dict:
        """Serializa slice a dict (sin DataFrames completos por tamaño)."""
        return {
            'data_slice_id': self.data_slice_id,
            'timestamp': self.timestamp.isoformat(),
            'instruments': list(self.bars_by_instrument.keys()),
            'features_summary': {
                instr: list(feats.keys())
                for instr, feats in self.features_by_instrument.items()
            },
            'regime_states': self.regime_states,
            'portfolio_state': self.portfolio_state
        }


class DataLineageTracker:
    """
    Rastreador de linaje de datos institucional.
    
    Captura y persiste snapshots completos de datos de entrada
    que producen cada decisión del sistema, permitiendo reproducción
    bit-a-bit de cualquier decisión histórica.
    """
    
    def __init__(self, storage_path: Path):
        """
        Inicializa tracker.
        
        Args:
            storage_path: Directorio para persistir data slices
        """
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"DataLineageTracker inicializado: {self.storage_path}")
    
    def capture_data_slice(
        self,
        bars_by_instrument: Dict[str, pd.DataFrame],
        features_by_instrument: Dict[str, Dict],
        regime_states: Dict[str, Dict],
        portfolio_state: Dict[str, Any]
    ) -> DataSlice:
        """
        Captura snapshot completo de datos actuales.
        
        Args:
            bars_by_instrument: Dict de DataFrames OHLCV por instrumento
            features_by_instrument: Dict de features calculados
            regime_states: Estados de régimen por instrumento
            portfolio_state: Estado completo del portfolio
            
        Returns:
            DataSlice con ID único determinístico
        """
        timestamp = datetime.now()
        
        # Calcular hash determinístico del contenido
        content_hash = self._compute_content_hash(
            bars_by_instrument,
            features_by_instrument,
            regime_states,
            portfolio_state
        )
        
        # Generar data_slice_id
        data_slice_id = f"SLICE_{int(timestamp.timestamp() * 1000)}_{content_hash[:16]}"
        
        # Crear slice
        slice_obj = DataSlice(
            data_slice_id=data_slice_id,
            timestamp=timestamp,
            bars_by_instrument=bars_by_instrument,
            features_by_instrument=features_by_instrument,
            regime_states=regime_states,
            portfolio_state=portfolio_state
        )
        
        # Persistir
        self._persist_slice(slice_obj, content_hash)
        
        logger.debug(f"Data slice captured: {data_slice_id}")
        
        return slice_obj
    
    def load_data_slice(self, data_slice_id: str) -> Optional[DataSlice]:
        """
        Carga un data slice desde storage.
        
        Args:
            data_slice_id: ID del slice a cargar
            
        Returns:
            DataSlice reconstruido o None si no existe
        """
        slice_path = self._get_slice_path(data_slice_id)
        
        if not slice_path.exists():
            logger.warning(f"Data slice not found: {data_slice_id}")
            return None
        
        try:
            with open(slice_path, 'r') as f:
                data = json.load(f)
            
            # Reconstruir DataFrames
            bars_by_instrument = {}
            for instr, bars_dict in data['bars_by_instrument'].items():
                bars_by_instrument[instr] = pd.DataFrame(bars_dict)
            
            return DataSlice(
                data_slice_id=data['data_slice_id'],
                timestamp=datetime.fromisoformat(data['timestamp']),
                bars_by_instrument=bars_by_instrument,
                features_by_instrument=data['features_by_instrument'],
                regime_states=data['regime_states'],
                portfolio_state=data['portfolio_state']
            )
        
        except (json.JSONDecodeError, KeyError) as e:
            logger.error(f"Error loading data slice {data_slice_id}: {e}")
            return None
    
    def _compute_content_hash(
        self,
        bars_by_instrument: Dict[str, pd.DataFrame],
        features_by_instrument: Dict[str, Dict],
        regime_states: Dict[str, Dict],
        portfolio_state: Dict[str, Any]
    ) -> str:
        """Calcula hash SHA256 del contenido completo."""
        # Serializar todo a formato determinístico
        content = {
            'bars': {
                instr: df.tail(200).to_dict(orient='records')
                for instr, df in bars_by_instrument.items()
            },
            'features': features_by_instrument,
            'regimes': regime_states,
            'portfolio': portfolio_state
        }
        
        content_json = json.dumps(content, sort_keys=True)
        return hashlib.sha256(content_json.encode()).hexdigest()
    
    def _persist_slice(self, slice_obj: DataSlice, content_hash: str):
        """Persiste slice a storage."""
        slice_path = self._get_slice_path(slice_obj.data_slice_id)
        
        # Crear directorio por año/mes para organización
        slice_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Serializar con DataFrames
        data = {
            'data_slice_id': slice_obj.data_slice_id,
            'timestamp': slice_obj.timestamp.isoformat(),
            'content_hash': content_hash,
            'bars_by_instrument': {
                instr: df.tail(200).to_dict(orient='records')
                for instr, df in slice_obj.bars_by_instrument.items()
            },
            'features_by_instrument': slice_obj.features_by_instrument,
            'regime_states': slice_obj.regime_states,
            'portfolio_state': slice_obj.portfolio_state
        }
        
        with open(slice_path, 'w') as f:
            json.dump(data, f, indent=2)
    
    def _get_slice_path(self, data_slice_id: str) -> Path:
        """Obtiene path de archivo para un data slice."""
        # Extraer timestamp del ID
        parts = data_slice_id.split('_')
        if len(parts) >= 2:
            try:
                timestamp_ms = int(parts[1])
                dt = datetime.fromtimestamp(timestamp_ms / 1000)
                year_month = dt.strftime('%Y/%m')
            except (ValueError, IndexError):
                year_month = "unknown"
        else:
            year_month = "unknown"
        
        filename = f"{data_slice_id}.json"
        return self.storage_path / year_month / filename
    
    def get_stats(self) -> Dict:
        """Obtiene estadísticas del lineage tracker."""
        slice_files = list(self.storage_path.rglob("SLICE_*.json"))
        
        total_size_bytes = sum(f.stat().st_size for f in slice_files)
        
        return {
            'total_slices': len(slice_files),
            'total_size_mb': total_size_bytes / (1024 * 1024),
            'storage_path': str(self.storage_path)
        }
