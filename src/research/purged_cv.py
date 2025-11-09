"""
Purged Cross-Validation - CV sin data leakage para series temporales
Implementa purging y embargo para evitar información del futuro.
"""

import logging
import numpy as np
import pandas as pd
from typing import List, Tuple, Generator
from datetime import timedelta

logger = logging.getLogger(__name__)


class PurgedKFold:
    """
    K-Fold cross-validation con purging y embargo.
    
    Purging: elimina observaciones del train set que se solapan temporalmente
    con el test set (previene leakage por overlapping labels).
    
    Embargo: elimina observaciones del train set inmediatamente posteriores
    al test set (previene usar información del futuro).
    """
    
    def __init__(
        self,
        n_splits: int = 5,
        purge_pct: float = 0.01,
        embargo_pct: float = 0.01
    ):
        """
        Inicializa purged k-fold.
        
        Args:
            n_splits: Número de folds
            purge_pct: Porcentaje de datos a purgar antes del test
            embargo_pct: Porcentaje de datos a embargar después del test
        """
        self.n_splits = n_splits
        self.purge_pct = purge_pct
        self.embargo_pct = embargo_pct
        
        logger.info(
            f"PurgedKFold initialized: "
            f"splits={n_splits}, purge={purge_pct:.2%}, embargo={embargo_pct:.2%}"
        )
    
    def split(
        self,
        X: pd.DataFrame,
        y: pd.Series = None,
        label_times: pd.Series = None
    ) -> Generator[Tuple[np.ndarray, np.ndarray], None, None]:
        """
        Genera índices de train/test para cada fold.
        
        Args:
            X: Features (debe tener DatetimeIndex)
            y: Target (opcional)
            label_times: Series con timestamp de fin de cada label
                         (si no se provee, usa X.index + holding_period estimado)
        
        Yields:
            (train_indices, test_indices)
        """
        if not isinstance(X.index, pd.DatetimeIndex):
            raise ValueError("X must have DatetimeIndex")
        
        n_samples = len(X)
        indices = np.arange(n_samples)
        
        # Si no hay label_times, asumir que cada observación termina en su timestamp
        if label_times is None:
            label_times = pd.Series(X.index, index=X.index)
        
        # Calcular tamaño de cada fold
        fold_size = n_samples // self.n_splits
        
        for fold in range(self.n_splits):
            # Test set: fold actual
            test_start = fold * fold_size
            test_end = test_start + fold_size if fold < self.n_splits - 1 else n_samples
            
            test_indices = indices[test_start:test_end]
            
            # Train set: todos excepto test
            train_indices = np.concatenate([
                indices[:test_start],
                indices[test_end:]
            ])
            
            # Aplicar purging
            train_indices = self._apply_purging(
                train_indices,
                test_indices,
                X.index,
                label_times
            )
            
            # Aplicar embargo
            train_indices = self._apply_embargo(
                train_indices,
                test_indices,
                X.index
            )
            
            logger.debug(
                f"Fold {fold + 1}/{self.n_splits}: "
                f"train={len(train_indices)}, test={len(test_indices)}"
            )
            
            yield train_indices, test_indices
    
    def _apply_purging(
        self,
        train_indices: np.ndarray,
        test_indices: np.ndarray,
        timestamps: pd.DatetimeIndex,
        label_times: pd.Series
    ) -> np.ndarray:
        """
        Purga observaciones del train que se solapan con test.
        
        Una observación en train se purga si su label_time está
        dentro del período del test set.
        """
        # Timestamps del test set
        test_start = timestamps[test_indices[0]]
        test_end = timestamps[test_indices[-1]]
        
        # Calcular ventana de purge
        total_duration = timestamps[-1] - timestamps[0]
        purge_duration = total_duration * self.purge_pct
        purge_start = test_start - purge_duration
        
        # Filtrar train: mantener solo los que no se solapan
        purged_indices = []
        for idx in train_indices:
            label_end = label_times.iloc[idx]
            
            # Mantener si:
            # 1. Termina antes de purge_start
            # 2. Comienza después de test_end
            if label_end < purge_start or timestamps[idx] > test_end:
                purged_indices.append(idx)
        
        return np.array(purged_indices)
    
    def _apply_embargo(
        self,
        train_indices: np.ndarray,
        test_indices: np.ndarray,
        timestamps: pd.DatetimeIndex
    ) -> np.ndarray:
        """
        Aplica embargo: elimina observaciones inmediatamente después del test.
        
        Previene usar información que podría estar influenciada
        por las operaciones del test set.
        """
        # Timestamp final del test
        test_end = timestamps[test_indices[-1]]
        
        # Calcular ventana de embargo
        total_duration = timestamps[-1] - timestamps[0]
        embargo_duration = total_duration * self.embargo_pct
        embargo_end = test_end + embargo_duration
        
        # Filtrar train: eliminar observaciones en embargo period
        embargoed_indices = []
        for idx in train_indices:
            if timestamps[idx] < test_end or timestamps[idx] > embargo_end:
                embargoed_indices.append(idx)
        
        return np.array(embargoed_indices)


class CombinatorialPurgedKFold:
    """
    Combinatorial Purged K-Fold CV.
    
    Genera múltiples paths de train/test para reducir varianza
    de la estimación de performance.
    """
    
    def __init__(
        self,
        n_splits: int = 5,
        n_test_groups: int = 2,
        purge_pct: float = 0.01,
        embargo_pct: float = 0.01
    ):
        """
        Inicializa combinatorial purged k-fold.
        
        Args:
            n_splits: Número de grupos
            n_test_groups: Número de grupos en cada test set
            purge_pct: Porcentaje de purge
            embargo_pct: Porcentaje de embargo
        """
        self.n_splits = n_splits
        self.n_test_groups = n_test_groups
        self.purge_pct = purge_pct
        self.embargo_pct = embargo_pct
        
        logger.info(
            f"CombinatorialPurgedKFold: "
            f"splits={n_splits}, test_groups={n_test_groups}"
        )
    
    def split(
        self,
        X: pd.DataFrame,
        y: pd.Series = None,
        label_times: pd.Series = None
    ) -> Generator[Tuple[np.ndarray, np.ndarray], None, None]:
        """Genera combinaciones de train/test."""
        if not isinstance(X.index, pd.DatetimeIndex):
            raise ValueError("X must have DatetimeIndex")
        
        n_samples = len(X)
        indices = np.arange(n_samples)
        
        if label_times is None:
            label_times = pd.Series(X.index, index=X.index)
        
        # Dividir en grupos
        group_size = n_samples // self.n_splits
        groups = []
        
        for i in range(self.n_splits):
            start = i * group_size
            end = start + group_size if i < self.n_splits - 1 else n_samples
            groups.append(indices[start:end])
        
        # Generar todas las combinaciones de n_test_groups
        from itertools import combinations
        
        for test_groups in combinations(range(self.n_splits), self.n_test_groups):
            # Test set: unión de grupos seleccionados
            test_indices = np.concatenate([groups[i] for i in test_groups])
            
            # Train set: resto de grupos
            train_groups = [i for i in range(self.n_splits) if i not in test_groups]
            train_indices = np.concatenate([groups[i] for i in train_groups])
            
            # Aplicar purging y embargo
            pkf = PurgedKFold(
                n_splits=self.n_splits,
                purge_pct=self.purge_pct,
                embargo_pct=self.embargo_pct
            )
            
            train_indices = pkf._apply_purging(
                train_indices, test_indices,
                X.index, label_times
            )
            
            train_indices = pkf._apply_embargo(
                train_indices, test_indices,
                X.index
            )
            
            yield train_indices, test_indices


def calculate_sample_weights(
    label_times: pd.Series,
    decay_factor: float = 1.0
) -> pd.Series:
    """
    Calcula pesos por muestra basado en concurrencia y decay.
    
    Muestras con más overlap temporal reciben menor peso.
    Muestras más recientes pueden recibir mayor peso (decay).
    
    Args:
        label_times: Series con timestamp de fin de cada label
        decay_factor: Factor de decay temporal (1.0 = sin decay)
        
    Returns:
        Series con pesos normalizados
    """
    # Calcular concurrencia (cuántas labels se solapan en cada punto)
    all_times = pd.concat([
        label_times.index.to_series(),
        label_times
    ]).sort_values()
    
    concurrency = pd.Series(0, index=label_times.index)
    
    for idx, end_time in label_times.items():
        # Contar cuántas otras labels están activas durante esta
        start_time = idx
        
        overlaps = (
            (label_times.index < end_time) &
            (label_times > start_time)
        ).sum()
        
        concurrency[idx] = overlaps + 1  # +1 para incluir esta misma
    
    # Peso inversamente proporcional a concurrencia
    weights = 1.0 / concurrency
    
    # Aplicar decay temporal si se especifica
    if decay_factor != 1.0:
        time_indices = np.arange(len(weights))
        time_decay = np.exp(-decay_factor * (1 - time_indices / len(weights)))
        weights = weights * time_decay
    
    # Normalizar
    weights = weights / weights.sum()
    
    return weights