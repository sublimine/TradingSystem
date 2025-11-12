"""
Version Manager - Control de versiones estricto de código, configs y features
Implementa versionado semántico con tracking de cambios y compatibilidad.
"""

import json
import hashlib
from typing import Dict, List, Optional, Tuple
from pathlib import Path
from datetime import datetime
from dataclasses import dataclass, asdict
import logging

logger = logging.getLogger(__name__)


@dataclass
class ModuleVersion:
    """Versión de un módulo del sistema."""
    module_name: str
    version: str  # Semver: MAJOR.MINOR.PATCH
    file_hash: str
    deployed_at: datetime
    changes: str
    author: str
    
    def __post_init__(self):
        if isinstance(self.deployed_at, str):
            self.deployed_at = datetime.fromisoformat(self.deployed_at)


@dataclass
class ConfigVersion:
    """Versión de una configuración."""
    config_name: str
    version: str
    content_hash: str
    deployed_at: datetime
    changes: str
    
    def __post_init__(self):
        if isinstance(self.deployed_at, str):
            self.deployed_at = datetime.fromisoformat(self.deployed_at)


@dataclass
class FeatureSetVersion:
    """Versión de un conjunto de features."""
    feature_set_id: str
    features: List[str]
    definition_hash: str
    created_at: datetime
    compatible_with: List[str]  # feature_set_ids compatibles
    
    def __post_init__(self):
        if isinstance(self.created_at, str):
            self.created_at = datetime.fromisoformat(self.created_at)


class VersionManager:
    """
    Gestor de versiones institucional.
    
    Rastrea versiones de:
    - Módulos Python (código)
    - Configuraciones YAML/JSON
    - Feature sets (definiciones de features)
    - Modelos ML
    
    Garantiza reproducibilidad y previene incompatibilidades.
    """
    
    def __init__(self, versions_path: Path):
        """
        Inicializa version manager.
        
        Args:
            versions_path: Directorio para registry de versiones
        """
        self.versions_path = Path(versions_path)
        self.registry_path = self.versions_path / "registry"
        self.configs_path = self.versions_path / "configs"
        self.models_path = self.versions_path / "models"
        
        # Crear directorios
        self.registry_path.mkdir(parents=True, exist_ok=True)
        self.configs_path.mkdir(parents=True, exist_ok=True)
        self.models_path.mkdir(parents=True, exist_ok=True)
        
        # Cargar registry
        self.registry_file = self.registry_path / "versions.json"
        self.registry = self._load_registry()
        
        logger.info(f"VersionManager inicializado: {self.versions_path}")
    
    def register_module_version(
        self,
        module_name: str,
        version: str,
        file_path: Path,
        changes: str,
        author: str = "system"
    ) -> ModuleVersion:
        """
        Registra nueva versión de un módulo.
        
        Args:
            module_name: Nombre del módulo (ej: 'core.conflict_arbiter')
            version: Versión semántica (ej: '1.2.3')
            file_path: Path al archivo del módulo
            changes: Descripción de cambios
            author: Autor del cambio
            
        Returns:
            ModuleVersion registrado
        """
        # Calcular hash del archivo
        file_hash = self._compute_file_hash(file_path)
        
        # Crear versión
        module_version = ModuleVersion(
            module_name=module_name,
            version=version,
            file_hash=file_hash,
            deployed_at=datetime.now(),
            changes=changes,
            author=author
        )
        
        # Añadir al registry
        if 'modules' not in self.registry:
            self.registry['modules'] = {}
        
        if module_name not in self.registry['modules']:
            self.registry['modules'][module_name] = []
        
        self.registry['modules'][module_name].append({
            'version': version,
            'file_hash': file_hash,
            'deployed_at': module_version.deployed_at.isoformat(),
            'changes': changes,
            'author': author
        })
        
        # Persistir
        self._save_registry()
        
        logger.info(f"Module version registered: {module_name} v{version}")
        
        return module_version
    
    def register_config_version(
        self,
        config_name: str,
        version: str,
        config_path: Path,
        changes: str
    ) -> ConfigVersion:
        """
        Registra nueva versión de configuración.
        
        Args:
            config_name: Nombre de la config (ej: 'regime_thresholds')
            version: Versión semántica
            config_path: Path al archivo de configuración
            changes: Descripción de cambios
            
        Returns:
            ConfigVersion registrado
        """
        # Calcular hash del contenido
        content_hash = self._compute_file_hash(config_path)
        
        # Crear versión
        config_version = ConfigVersion(
            config_name=config_name,
            version=version,
            content_hash=content_hash,
            deployed_at=datetime.now(),
            changes=changes
        )
        
        # Copiar config a versions/configs con timestamp
        versioned_name = f"{config_name}_v{version}_{int(datetime.now().timestamp())}.yaml"
        versioned_path = self.configs_path / versioned_name
        
        import shutil
        shutil.copy(config_path, versioned_path)
        
        # Añadir al registry
        if 'configs' not in self.registry:
            self.registry['configs'] = {}
        
        if config_name not in self.registry['configs']:
            self.registry['configs'][config_name] = []
        
        self.registry['configs'][config_name].append({
            'version': version,
            'content_hash': content_hash,
            'deployed_at': config_version.deployed_at.isoformat(),
            'changes': changes,
            'versioned_file': str(versioned_path)
        })
        
        # Persistir
        self._save_registry()
        
        logger.info(f"Config version registered: {config_name} v{version}")
        
        return config_version
    
    def register_feature_set(
        self,
        features: List[str],
        definitions: Dict[str, str],
        compatible_with: Optional[List[str]] = None
    ) -> FeatureSetVersion:
        """
        Registra nuevo conjunto de features.
        
        Args:
            features: Lista de nombres de features
            definitions: Dict con definición matemática de cada feature
            compatible_with: Lista de feature_set_ids compatibles
            
        Returns:
            FeatureSetVersion registrado
        """
        # Calcular hash de las definiciones
        definitions_json = json.dumps(definitions, sort_keys=True)
        definition_hash = hashlib.sha256(definitions_json.encode()).hexdigest()
        
        feature_set_id = f"FSET_{definition_hash[:16]}"
        
        # Crear versión
        feature_set = FeatureSetVersion(
            feature_set_id=feature_set_id,
            features=features,
            definition_hash=definition_hash,
            created_at=datetime.now(),
            compatible_with=compatible_with or []
        )
        
        # Añadir al registry
        if 'feature_sets' not in self.registry:
            self.registry['feature_sets'] = {}
        
        self.registry['feature_sets'][feature_set_id] = {
            'features': features,
            'definition_hash': definition_hash,
            'created_at': feature_set.created_at.isoformat(),
            'compatible_with': compatible_with or [],
            'definitions': definitions
        }
        
        # Persistir
        self._save_registry()
        
        logger.info(f"Feature set registered: {feature_set_id}")
        
        return feature_set
    
    def get_current_versions(self) -> Dict[str, str]:
        """
        Obtiene versiones actuales de todos los módulos.
        
        Returns:
            Dict mapeando module_name a version
        """
        current_versions = {}
        
        if 'modules' in self.registry:
            for module_name, versions in self.registry['modules'].items():
                if versions:
                    # Última versión es la actual
                    current_versions[module_name] = versions[-1]['version']
        
        return current_versions
    
    def get_current_config_hashes(self) -> Dict[str, str]:
        """
        Obtiene hashes actuales de todas las configs.
        
        Returns:
            Dict mapeando config_name a content_hash
        """
        config_hashes = {}
        
        if 'configs' in self.registry:
            for config_name, versions in self.registry['configs'].items():
                if versions:
                    config_hashes[config_name] = versions[-1]['content_hash']
        
        return config_hashes
    
    def verify_compatibility(
        self,
        module_versions: Dict[str, str],
        config_hashes: Dict[str, str]
    ) -> Tuple[bool, List[str]]:
        """
        Verifica que las versiones especificadas son compatibles.
        
        Args:
            module_versions: Dict de versiones de módulos
            config_hashes: Dict de hashes de configs
            
        Returns:
            (is_compatible, incompatibility_reasons)
        """
        incompatibilities = []
        
        # Verificar módulos
        for module_name, version in module_versions.items():
            if module_name not in self.registry.get('modules', {}):
                incompatibilities.append(f"Unknown module: {module_name}")
                continue
            
            # Verificar que la versión existe
            module_versions_list = self.registry['modules'][module_name]
            if not any(v['version'] == version for v in module_versions_list):
                incompatibilities.append(
                    f"Unknown version for {module_name}: {version}"
                )
        
        # Verificar configs
        for config_name, content_hash in config_hashes.items():
            if config_name not in self.registry.get('configs', {}):
                incompatibilities.append(f"Unknown config: {config_name}")
                continue
            
            # Verificar que el hash existe
            config_versions_list = self.registry['configs'][config_name]
            if not any(v['content_hash'] == content_hash for v in config_versions_list):
                incompatibilities.append(
                    f"Unknown config hash for {config_name}: {content_hash[:8]}..."
                )
        
        is_compatible = len(incompatibilities) == 0
        return is_compatible, incompatibilities
    
    def _compute_file_hash(self, file_path: Path) -> str:
        """Calcula SHA256 hash de un archivo."""
        hasher = hashlib.sha256()
        
        with open(file_path, 'rb') as f:
            while chunk := f.read(8192):
                hasher.update(chunk)
        
        return hasher.hexdigest()
    
    def _load_registry(self) -> Dict:
        """Carga registry desde disco."""
        if not self.registry_file.exists():
            return {
                'created_at': datetime.now().isoformat(),
                'modules': {},
                'configs': {},
                'feature_sets': {},
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
        """Obtiene estadísticas del version manager."""
        return {
            'total_modules': len(self.registry.get('modules', {})),
            'total_configs': len(self.registry.get('configs', {})),
            'total_feature_sets': len(self.registry.get('feature_sets', {})),
            'total_models': len(self.registry.get('models', {})),
            'registry_path': str(self.registry_path)
        }
