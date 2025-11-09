"""
Feature Contracts - Schema registry para features
Garantiza consistencia de features entre train y producción.
"""

import logging
import json
from typing import Dict, List, Optional, Any
from datetime import datetime
from pathlib import Path
import hashlib
import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


class FeatureContract:
    """
    Contrato de una feature individual.
    
    Define:
    - Nombre
    - Tipo de dato esperado
    - Rango de valores válidos
    - Distribución esperada
    - Handling de nulls
    """
    
    def __init__(
        self,
        name: str,
        dtype: str,
        nullable: bool = False,
        min_value: Optional[float] = None,
        max_value: Optional[float] = None,
        allowed_values: Optional[List] = None,
        distribution_stats: Optional[Dict] = None
    ):
        """
        Inicializa contrato de feature.
        
        Args:
            name: Nombre de la feature
            dtype: Tipo de dato ('float64', 'int64', 'category', etc)
            nullable: Si permite valores null
            min_value: Valor mínimo permitido
            max_value: Valor máximo permitido
            allowed_values: Lista de valores permitidos (para categoricals)
            distribution_stats: Estadísticas de distribución esperada
        """
        self.name = name
        self.dtype = dtype
        self.nullable = nullable
        self.min_value = min_value
        self.max_value = max_value
        self.allowed_values = allowed_values
        self.distribution_stats = distribution_stats or {}
        
        self.created_at = datetime.now()
    
    def validate(self, series: pd.Series) -> Dict:
        """
        Valida una serie contra este contrato.
        
        Returns:
            Dict con resultado de validación
        """
        issues = []
        
        # Check dtype
        if str(series.dtype) != self.dtype:
            issues.append(f"Type mismatch: expected {self.dtype}, got {series.dtype}")
        
        # Check nulls
        null_count = series.isnull().sum()
        if null_count > 0 and not self.nullable:
            issues.append(f"Contains {null_count} nulls but nullable=False")
        
        # Check range
        if self.min_value is not None:
            below_min = (series < self.min_value).sum()
            if below_min > 0:
                issues.append(f"{below_min} values below min {self.min_value}")
        
        if self.max_value is not None:
            above_max = (series > self.max_value).sum()
            if above_max > 0:
                issues.append(f"{above_max} values above max {self.max_value}")
        
        # Check allowed values
        if self.allowed_values is not None:
            invalid = ~series.isin(self.allowed_values)
            invalid_count = invalid.sum()
            if invalid_count > 0:
                issues.append(f"{invalid_count} values not in allowed set")
        
        # Check distribution drift
        if self.distribution_stats:
            current_mean = series.mean()
            expected_mean = self.distribution_stats.get('mean', 0)
            expected_std = self.distribution_stats.get('std', 1)
            
            if expected_std > 0:
                z_score = abs(current_mean - expected_mean) / expected_std
                if z_score > 3:
                    issues.append(
                        f"Mean drift: current={current_mean:.4f}, "
                        f"expected={expected_mean:.4f} (z={z_score:.2f})"
                    )
        
        return {
            'is_valid': len(issues) == 0,
            'issues': issues
        }
    
    def to_dict(self) -> Dict:
        """Serializa a dict."""
        return {
            'name': self.name,
            'dtype': self.dtype,
            'nullable': self.nullable,
            'min_value': self.min_value,
            'max_value': self.max_value,
            'allowed_values': self.allowed_values,
            'distribution_stats': self.distribution_stats,
            'created_at': self.created_at.isoformat()
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'FeatureContract':
        """Deserializa desde dict."""
        contract = cls(
            name=data['name'],
            dtype=data['dtype'],
            nullable=data['nullable'],
            min_value=data.get('min_value'),
            max_value=data.get('max_value'),
            allowed_values=data.get('allowed_values'),
            distribution_stats=data.get('distribution_stats')
        )
        
        if 'created_at' in data:
            contract.created_at = datetime.fromisoformat(data['created_at'])
        
        return contract


class FeatureContractRegistry:
    """
    Registry de feature contracts.
    
    Gestiona versiones de contratos y valida features
    contra contratos registrados.
    """
    
    def __init__(self, registry_path: Path):
        """
        Inicializa registry.
        
        Args:
            registry_path: Path al directorio del registry
        """
        self.registry_path = Path(registry_path)
        self.registry_path.mkdir(parents=True, exist_ok=True)
        
        self._contracts: Dict[str, FeatureContract] = {}
        self._version_history: List[Dict] = []
        
        # Cargar contratos existentes
        self._load_registry()
        
        logger.info(
            f"FeatureContractRegistry initialized: "
            f"{len(self._contracts)} contracts loaded"
        )
    
    def register_contract(
        self,
        contract: FeatureContract,
        version: Optional[str] = None
    ):
        """
        Registra un nuevo contrato o actualiza existente.
        
        Args:
            contract: Contrato a registrar
            version: Versión (si None, auto-incrementa)
        """
        if version is None:
            version = self._generate_version()
        
        self._contracts[contract.name] = contract
        
        # Guardar a disco
        self._save_contract(contract, version)
        
        # Registrar en historial
        self._version_history.append({
            'feature': contract.name,
            'version': version,
            'timestamp': datetime.now().isoformat()
        })
        
        logger.info(f"Contract registered: {contract.name} v{version}")
    
    def register_from_dataframe(
        self,
        df: pd.DataFrame,
        nullable_features: Optional[List[str]] = None,
        categorical_features: Optional[List[str]] = None
    ):
        """
        Genera y registra contratos desde un DataFrame.
        
        Args:
            df: DataFrame con features
            nullable_features: Lista de features que permiten nulls
            categorical_features: Lista de features categóricas
        """
        nullable_features = nullable_features or []
        categorical_features = categorical_features or []
        
        for col in df.columns:
            series = df[col]
            
            # Determinar tipo
            if col in categorical_features:
                dtype = 'category'
                allowed_values = series.unique().tolist()
                min_val = None
                max_val = None
            else:
                dtype = str(series.dtype)
                allowed_values = None
                min_val = float(series.min())
                max_val = float(series.max())
            
            # Estadísticas de distribución
            dist_stats = {
                'mean': float(series.mean()) if dtype != 'category' else None,
                'std': float(series.std()) if dtype != 'category' else None,
                'median': float(series.median()) if dtype != 'category' else None,
                'q25': float(series.quantile(0.25)) if dtype != 'category' else None,
                'q75': float(series.quantile(0.75)) if dtype != 'category' else None
            }
            
            contract = FeatureContract(
                name=col,
                dtype=dtype,
                nullable=col in nullable_features,
                min_value=min_val,
                max_value=max_val,
                allowed_values=allowed_values,
                distribution_stats=dist_stats
            )
            
            self.register_contract(contract)
    
    def validate_dataframe(self, df: pd.DataFrame) -> Dict:
        """
        Valida DataFrame completo contra contratos registrados.
        
        Returns:
            Dict con resultados de validación
        """
        results = {
            'is_valid': True,
            'missing_features': [],
            'extra_features': [],
            'validation_results': {}
        }
        
        # Check missing features
        expected_features = set(self._contracts.keys())
        actual_features = set(df.columns)
        
        missing = expected_features - actual_features
        if missing:
            results['is_valid'] = False
            results['missing_features'] = list(missing)
        
        # Check extra features
        extra = actual_features - expected_features
        if extra:
            results['extra_features'] = list(extra)
        
        # Validate each feature
        for feature_name, contract in self._contracts.items():
            if feature_name in df.columns:
                validation = contract.validate(df[feature_name])
                results['validation_results'][feature_name] = validation
                
                if not validation['is_valid']:
                    results['is_valid'] = False
        
        return results
    
    def get_contract(self, feature_name: str) -> Optional[FeatureContract]:
        """Obtiene contrato de una feature."""
        return self._contracts.get(feature_name)
    
    def get_all_contracts(self) -> Dict[str, FeatureContract]:
        """Obtiene todos los contratos."""
        return self._contracts.copy()
    
    def compute_schema_hash(self) -> str:
        """Computa hash del schema completo."""
        schema_str = json.dumps(
            {name: contract.to_dict() for name, contract in self._contracts.items()},
            sort_keys=True
        )
        
        return hashlib.sha256(schema_str.encode()).hexdigest()
    
    def _generate_version(self) -> str:
        """Genera número de versión."""
        return datetime.now().strftime('%Y%m%d_%H%M%S')
    
    def _save_contract(self, contract: FeatureContract, version: str):
        """Guarda contrato a disco."""
        contract_file = self.registry_path / f"{contract.name}_{version}.json"
        
        with open(contract_file, 'w') as f:
            json.dump(contract.to_dict(), f, indent=2)
    
    def _load_registry(self):
        """Carga contratos desde disco."""
        # Buscar archivos de contratos
        for contract_file in self.registry_path.glob("*.json"):
            try:
                with open(contract_file, 'r') as f:
                    data = json.load(f)
                
                contract = FeatureContract.from_dict(data)
                
                # Mantener solo la versión más reciente
                if contract.name not in self._contracts:
                    self._contracts[contract.name] = contract
                elif contract.created_at > self._contracts[contract.name].created_at:
                    self._contracts[contract.name] = contract
            
            except Exception as e:
                logger.error(f"Failed to load contract from {contract_file}: {e}")