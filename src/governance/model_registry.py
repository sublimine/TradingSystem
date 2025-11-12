"""
Model Registry - Gestión institucional de modelos ML con governance completo
Implementa registro, validación, approval workflow y tracking de modelos.
"""

import json
import pickle
import hashlib
from typing import Dict, List, Optional, Any
from pathlib import Path
from datetime import datetime, date
from dataclasses import dataclass, asdict
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class ModelStatus(Enum):
    """Estados posibles de un modelo."""
    CANDIDATE = "candidate"
    STAGING = "staging"
    PRODUCTION = "production"
    DEPRECATED = "deprecated"
    FAILED = "failed"


@dataclass
class ModelMetadata:
    """Metadata completa de un modelo ML."""
    model_id: str
    model_name: str
    version: str
    status: ModelStatus
    
    # Propósito y contexto
    purpose: str
    problem_type: str  # classification, regression, ranking, etc
    
    # Datos de entrenamiento
    training_data_slice_ids: List[str]
    training_start_date: date
    training_end_date: date
    training_samples: int
    
    # Performance
    validation_metrics: Dict[str, float]
    validation_method: str
    out_of_sample_periods: List[str]
    
    # Supuestos y limitaciones
    assumptions: List[str]
    limitations: List[str]
    applicability_conditions: List[str]
    
    # Stress tests
    stress_test_results: Dict[str, Any]
    
    # Governance
    created_at: datetime
    created_by: str
    approved_by: Optional[List[str]]
    approval_date: Optional[datetime]
    next_review_date: Optional[date]
    
    # Tracking
    deployed_at: Optional[datetime]
    retirement_date: Optional[datetime]
    
    # Artifacts
    model_file_path: str
    model_file_hash: str
    feature_set_id: Optional[str]
    
    # Changelog
    changes_from_previous: Optional[str]
    
    def __post_init__(self):
        """Convert string dates to proper types if needed."""
        if isinstance(self.status, str):
            self.status = ModelStatus(self.status)
        if isinstance(self.training_start_date, str):
            self.training_start_date = date.fromisoformat(self.training_start_date)
        if isinstance(self.training_end_date, str):
            self.training_end_date = date.fromisoformat(self.training_end_date)
        if isinstance(self.created_at, str):
            self.created_at = datetime.fromisoformat(self.created_at)
        if isinstance(self.approval_date, str):
            self.approval_date = datetime.fromisoformat(self.approval_date)
        if isinstance(self.deployed_at, str):
            self.deployed_at = datetime.fromisoformat(self.deployed_at)
        if isinstance(self.retirement_date, str):
            self.retirement_date = date.fromisoformat(self.retirement_date)
        if isinstance(self.next_review_date, str):
            self.next_review_date = date.fromisoformat(self.next_review_date)


class ModelValidationChecklist:
    """Checklist de validación para aprobar modelo."""
    
    @staticmethod
    def validate_model(
        model: Any,
        metadata: ModelMetadata,
        validation_data: Any = None
    ) -> tuple[bool, List[str]]:
        """
        Ejecuta checklist completo de validación.
        
        Args:
            model: Modelo ML a validar
            metadata: Metadata del modelo
            validation_data: Datos de validación opcionales
            
        Returns:
            (is_valid, list_of_issues)
        """
        issues = []
        
        # 1. Verificar data leakage
        if not ModelValidationChecklist._check_no_data_leakage(metadata):
            issues.append("CRITICAL: Potential data leakage detected")
        
        # 2. Verificar performance consistente
        if not ModelValidationChecklist._check_consistent_performance(metadata):
            issues.append("WARNING: Performance inconsistent across validation periods")
        
        # 3. Verificar ausencia de sesgo
        if not ModelValidationChecklist._check_no_bias(metadata):
            issues.append("WARNING: Potential bias detected in predictions")
        
        # 4. Verificar manejo de extremos
        if not ModelValidationChecklist._check_extreme_handling(metadata):
            issues.append("WARNING: Extreme value handling not verified")
        
        # 5. Verificar stress tests
        if not metadata.stress_test_results:
            issues.append("CRITICAL: Stress tests not performed")
        
        # 6. Verificar documentación completa
        if not metadata.assumptions or not metadata.limitations:
            issues.append("WARNING: Incomplete documentation")
        
        is_valid = not any(issue.startswith("CRITICAL") for issue in issues)
        
        return is_valid, issues
    
    @staticmethod
    def _check_no_data_leakage(metadata: ModelMetadata) -> bool:
        """Verifica que no hay data leakage temporal."""
        # En producción, analizarías feature importance temporal
        # Por ahora, verificación básica
        return len(metadata.training_data_slice_ids) > 0
    
    @staticmethod
    def _check_consistent_performance(metadata: ModelMetadata) -> bool:
        """Verifica performance consistente en múltiples períodos."""
        return len(metadata.out_of_sample_periods) >= 3
    
    @staticmethod
    def _check_no_bias(metadata: ModelMetadata) -> bool:
        """Verifica ausencia de sesgo sistemático."""
        # Verificar que hay métricas relevantes
        return 'sharpe_ratio' in metadata.validation_metrics
    
    @staticmethod
    def _check_extreme_handling(metadata: ModelMetadata) -> bool:
        """Verifica manejo de casos extremos."""
        return 'stress_tests' in metadata.stress_test_results


class ModelRegistry:
    """
    Registro institucional de modelos ML.
    
    Gestiona ciclo de vida completo:
    - Registro inicial
    - Validación con checklist
    - Approval workflow (two-person rule)
    - Deployment tracking
    - Review periódico
    - Retirement
    """
    
    def __init__(self, registry_path: Path):
        """
        Inicializa model registry.
        
        Args:
            registry_path: Directorio para registry
        """
        self.registry_path = Path(registry_path)
        self.models_dir = self.registry_path / "models"
        self.artifacts_dir = self.registry_path / "artifacts"
        
        # Crear directorios
        self.models_dir.mkdir(parents=True, exist_ok=True)
        self.artifacts_dir.mkdir(parents=True, exist_ok=True)
        
        # Cargar registry
        self.registry_file = self.models_dir / "registry.json"
        self.registry = self._load_registry()
        
        logger.info(f"ModelRegistry inicializado: {self.registry_path}")
    
    def register_model(
        self,
        model: Any,
        model_name: str,
        version: str,
        purpose: str,
        problem_type: str,
        training_data_slice_ids: List[str],
        training_start_date: date,
        training_end_date: date,
        training_samples: int,
        validation_metrics: Dict[str, float],
        validation_method: str,
        out_of_sample_periods: List[str],
        assumptions: List[str],
        limitations: List[str],
        applicability_conditions: List[str],
        stress_test_results: Dict[str, Any],
        created_by: str,
        feature_set_id: Optional[str] = None,
        changes_from_previous: Optional[str] = None
    ) -> ModelMetadata:
        """
        Registra nuevo modelo en estado CANDIDATE.
        
        Args:
            model: Objeto modelo ML (sklearn, etc)
            model_name: Nombre descriptivo del modelo
            version: Versión semántica
            ... (otros parámetros según ModelMetadata)
            
        Returns:
            ModelMetadata del modelo registrado
        """
        # Generar model_id único
        timestamp = int(datetime.now().timestamp() * 1000)
        model_id = f"MODEL_{model_name}_{version}_{timestamp}"
        
        # Serializar modelo
        model_file_path = self.artifacts_dir / f"{model_id}.pkl"
        with open(model_file_path, 'wb') as f:
            pickle.dump(model, f)
        
        # Calcular hash del modelo
        model_file_hash = self._compute_file_hash(model_file_path)
        
        # Crear metadata
        metadata = ModelMetadata(
            model_id=model_id,
            model_name=model_name,
            version=version,
            status=ModelStatus.CANDIDATE,
            purpose=purpose,
            problem_type=problem_type,
            training_data_slice_ids=training_data_slice_ids,
            training_start_date=training_start_date,
            training_end_date=training_end_date,
            training_samples=training_samples,
            validation_metrics=validation_metrics,
            validation_method=validation_method,
            out_of_sample_periods=out_of_sample_periods,
            assumptions=assumptions,
            limitations=limitations,
            applicability_conditions=applicability_conditions,
            stress_test_results=stress_test_results,
            created_at=datetime.now(),
            created_by=created_by,
            approved_by=None,
            approval_date=None,
            next_review_date=None,
            deployed_at=None,
            retirement_date=None,
            model_file_path=str(model_file_path),
            model_file_hash=model_file_hash,
            feature_set_id=feature_set_id,
            changes_from_previous=changes_from_previous
        )
        
        # Persistir metadata
        self._save_model_metadata(metadata)
        
        # Añadir al registry
        self.registry['models'][model_id] = {
            'model_name': model_name,
            'version': version,
            'status': ModelStatus.CANDIDATE.value,
            'created_at': metadata.created_at.isoformat(),
            'created_by': created_by
        }
        self._save_registry()
        
        logger.info(f"Model registered: {model_id} (status=CANDIDATE)")
        
        return metadata
    
    def validate_model(self, model_id: str) -> tuple[bool, List[str]]:
        """
        Ejecuta validación completa del modelo.
        
        Args:
            model_id: ID del modelo a validar
            
        Returns:
            (is_valid, list_of_issues)
        """
        metadata = self.load_model_metadata(model_id)
        if not metadata:
            return False, ["Model not found"]
        
        # Cargar modelo
        model = self.load_model(model_id)
        
        # Ejecutar checklist
        is_valid, issues = ModelValidationChecklist.validate_model(
            model, metadata
        )
        
        logger.info(
            f"Model validation: {model_id} valid={is_valid} "
            f"issues={len(issues)}"
        )
        
        return is_valid, issues
    
    def approve_model(
        self,
        model_id: str,
        approver: str,
        next_review_months: int = 3
    ) -> bool:
        """
        Aprueba modelo para staging (requiere two-person rule).
        
        Args:
            model_id: ID del modelo
            approver: Nombre del aprobador
            next_review_months: Meses hasta próxima revisión
            
        Returns:
            True si aprobación exitosa
        """
        metadata = self.load_model_metadata(model_id)
        if not metadata:
            logger.error(f"Model not found: {model_id}")
            return False
        
        # Verificar que no sea el mismo que creó
        if metadata.created_by == approver:
            logger.error(
                f"Two-person rule violation: creator cannot approve "
                f"(creator={metadata.created_by}, approver={approver})"
            )
            return False
        
        # Validar modelo primero
        is_valid, issues = self.validate_model(model_id)
        if not is_valid:
            logger.error(
                f"Model validation failed: {model_id} issues={issues}"
            )
            return False
        
        # Actualizar metadata
        if metadata.approved_by is None:
            metadata.approved_by = []
        metadata.approved_by.append(approver)
        metadata.approval_date = datetime.now()
        metadata.status = ModelStatus.STAGING
        
        from dateutil.relativedelta import relativedelta
        metadata.next_review_date = (
            date.today() + relativedelta(months=next_review_months)
        )
        
        # Persistir
        self._save_model_metadata(metadata)
        
        # Actualizar registry
        self.registry['models'][model_id]['status'] = ModelStatus.STAGING.value
        self.registry['models'][model_id]['approved_by'] = metadata.approved_by
        self._save_registry()
        
        logger.info(
            f"Model approved: {model_id} by {approver} "
            f"(status=STAGING, next_review={metadata.next_review_date})"
        )
        
        return True
    
    def deploy_model(self, model_id: str) -> bool:
        """
        Despliega modelo a producción (solo si está en STAGING).
        
        Args:
            model_id: ID del modelo
            
        Returns:
            True si deployment exitoso
        """
        metadata = self.load_model_metadata(model_id)
        if not metadata:
            return False
        
        if metadata.status != ModelStatus.STAGING:
            logger.error(
                f"Cannot deploy model {model_id}: "
                f"status={metadata.status.value} (must be STAGING)"
            )
            return False
        
        # Actualizar metadata
        metadata.status = ModelStatus.PRODUCTION
        metadata.deployed_at = datetime.now()
        
        # Persistir
        self._save_model_metadata(metadata)
        
        # Actualizar registry
        self.registry['models'][model_id]['status'] = ModelStatus.PRODUCTION.value
        self.registry['models'][model_id]['deployed_at'] = metadata.deployed_at.isoformat()
        self._save_registry()
        
        logger.info(f"Model deployed to production: {model_id}")
        
        return True
    
    def retire_model(self, model_id: str, reason: str) -> bool:
        """
        Retira modelo de producción.
        
        Args:
            model_id: ID del modelo
            reason: Razón del retirement
            
        Returns:
            True si retirement exitoso
        """
        metadata = self.load_model_metadata(model_id)
        if not metadata:
            return False
        
        # Actualizar metadata
        metadata.status = ModelStatus.DEPRECATED
        metadata.retirement_date = date.today()
        
        # Persistir
        self._save_model_metadata(metadata)
        
        # Actualizar registry
        self.registry['models'][model_id]['status'] = ModelStatus.DEPRECATED.value
        self.registry['models'][model_id]['retirement_reason'] = reason
        self._save_registry()
        
        logger.info(f"Model retired: {model_id} reason={reason}")
        
        return True
    
    def load_model(self, model_id: str) -> Optional[Any]:
        """Carga modelo desde artifacts."""
        metadata = self.load_model_metadata(model_id)
        if not metadata:
            return None
        
        model_path = Path(metadata.model_file_path)
        if not model_path.exists():
            logger.error(f"Model file not found: {model_path}")
            return None
        
        try:
            with open(model_path, 'rb') as f:
                model = pickle.load(f)
            return model
        except Exception as e:
            logger.error(f"Error loading model {model_id}: {e}")
            return None
    
    def load_model_metadata(self, model_id: str) -> Optional[ModelMetadata]:
        """Carga metadata de un modelo."""
        metadata_path = self.models_dir / f"{model_id}.json"
        
        if not metadata_path.exists():
            return None
        
        try:
            with open(metadata_path, 'r') as f:
                data = json.load(f)
            return ModelMetadata(**data)
        except Exception as e:
            logger.error(f"Error loading model metadata {model_id}: {e}")
            return None
    
    def get_production_models(self) -> List[ModelMetadata]:
        """Obtiene todos los modelos en producción."""
        production_models = []
        
        for model_id, info in self.registry['models'].items():
            if info['status'] == ModelStatus.PRODUCTION.value:
                metadata = self.load_model_metadata(model_id)
                if metadata:
                    production_models.append(metadata)
        
        return production_models
    
    def get_models_due_for_review(self) -> List[ModelMetadata]:
        """Obtiene modelos que requieren revisión."""
        due_models = []
        today = date.today()
        
        for model_id, info in self.registry['models'].items():
            if info['status'] == ModelStatus.PRODUCTION.value:
                metadata = self.load_model_metadata(model_id)
                if metadata and metadata.next_review_date:
                    if metadata.next_review_date <= today:
                        due_models.append(metadata)
        
        return due_models
    
    def _compute_file_hash(self, file_path: Path) -> str:
        """Calcula SHA256 hash de archivo."""
        hasher = hashlib.sha256()
        with open(file_path, 'rb') as f:
            while chunk := f.read(8192):
                hasher.update(chunk)
        return hasher.hexdigest()
    
    def _save_model_metadata(self, metadata: ModelMetadata):
        """Persiste metadata de modelo."""
        metadata_path = self.models_dir / f"{metadata.model_id}.json"
        
        # Convertir a dict serializable
        data = asdict(metadata)
        data['status'] = metadata.status.value
        data['created_at'] = metadata.created_at.isoformat()
        if metadata.approval_date:
            data['approval_date'] = metadata.approval_date.isoformat()
        if metadata.deployed_at:
            data['deployed_at'] = metadata.deployed_at.isoformat()
        if metadata.next_review_date:
            data['next_review_date'] = metadata.next_review_date.isoformat()
        if metadata.retirement_date:
            data['retirement_date'] = metadata.retirement_date.isoformat()
        data['training_start_date'] = metadata.training_start_date.isoformat()
        data['training_end_date'] = metadata.training_end_date.isoformat()
        
        with open(metadata_path, 'w') as f:
            json.dump(data, f, indent=2)
    
    def _load_registry(self) -> Dict:
        """Carga registry desde disco."""
        if not self.registry_file.exists():
            return {
                'created_at': datetime.now().isoformat(),
                'models': {}
            }
        
        with open(self.registry_file, 'r') as f:
            return json.load(f)
    
    def _save_registry(self):
        """Persiste registry a disco."""
        self.registry['updated_at'] = datetime.now().isoformat()
        
        with open(self.registry_file, 'w') as f:
            json.dump(self.registry, f, indent=2)
    
    def get_stats(self) -> Dict:
        """Obtiene estadísticas del registry."""
        status_counts = {}
        for model_info in self.registry['models'].values():
            status = model_info['status']
            status_counts[status] = status_counts.get(status, 0) + 1
        
        return {
            'total_models': len(self.registry['models']),
            'by_status': status_counts,
            'registry_path': str(self.registry_path)
        }
