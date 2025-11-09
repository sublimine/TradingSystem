"""
Drift Detection - Detección de concept drift en producción
Implementa ADWIN y SPRT para detectar cambios en distribución.
"""

import logging
import numpy as np
from typing import Optional, List, Tuple
from datetime import datetime
from collections import deque

logger = logging.getLogger(__name__)


class ADWIN:
    """
    ADaptive WINdowing - Detector de drift automático.
    
    Mantiene ventana deslizante de tamaño variable que se ajusta
    cuando detecta cambio estadístico en la distribución.
    """
    
    def __init__(self, delta: float = 0.002):
        """
        Inicializa ADWIN.
        
        Args:
            delta: Nivel de confianza (menor = más sensible)
        """
        self.delta = delta
        self._window: deque = deque()
        self._width = 0
        self._variance = 0.0
        self._total = 0.0
        
        self._drift_detected = False
        self._detection_count = 0
        
        logger.info(f"ADWIN initialized with delta={delta}")
    
    def update(self, value: float) -> bool:
        """
        Añade valor y verifica drift.
        
        Args:
            value: Nuevo valor (ej: error de predicción)
            
        Returns:
            True si se detectó drift
        """
        self._window.append(value)
        self._width += 1
        
        # Actualizar estadísticas
        if self._width == 1:
            self._total = value
            self._variance = 0.0
        else:
            old_mean = self._total / (self._width - 1)
            self._total += value
            new_mean = self._total / self._width
            
            self._variance += (value - old_mean) * (value - new_mean)
        
        # Verificar drift
        drift = self._detect_change()
        
        if drift:
            self._drift_detected = True
            self._detection_count += 1
            logger.warning(
                f"Drift detected! Window size before: {self._width}, "
                f"detection #{self._detection_count}"
            )
        
        return drift
    
    def _detect_change(self) -> bool:
        """Verifica si hay cambio estadístico."""
        if self._width < 2:
            return False
        
        # Probar diferentes split points
        n = self._width
        
        # Simplificación: probar split en el medio
        n0 = n // 2
        n1 = n - n0
        
        if n0 < 5 or n1 < 5:
            return False
        
        # Calcular medias de cada subventana
        window_list = list(self._window)
        mean0 = np.mean(window_list[:n0])
        mean1 = np.mean(window_list[n0:])
        
        # Calcular bound (Hoeffding bound)
        m = 1.0 / (1.0 / n0 + 1.0 / n1)
        
        epsilon = np.sqrt(
            (1.0 / (2 * m)) * np.log(4.0 / self.delta)
        )
        
        # Detectar si diferencia excede bound
        if abs(mean0 - mean1) > epsilon:
            # Reducir ventana, eliminar datos antiguos
            remove_count = n0
            for _ in range(remove_count):
                self._window.popleft()
            
            self._width = len(self._window)
            
            # Recalcular estadísticas
            if self._width > 0:
                self._total = sum(self._window)
                window_array = np.array(self._window)
                self._variance = np.var(window_array) * self._width
            else:
                self._total = 0.0
                self._variance = 0.0
            
            return True
        
        return False
    
    def reset(self):
        """Resetea detector."""
        self._window.clear()
        self._width = 0
        self._variance = 0.0
        self._total = 0.0
        self._drift_detected = False
    
    @property
    def drift_detected(self) -> bool:
        """Indica si se detectó drift."""
        return self._drift_detected
    
    @property
    def window_size(self) -> int:
        """Tamaño actual de la ventana."""
        return self._width


class SPRT:
    """
    Sequential Probability Ratio Test - Test secuencial de hipótesis.
    
    Detecta cambio en media de una distribución usando test
    de razón de likelihood secuencial.
    """
    
    def __init__(
        self,
        baseline_mean: float,
        baseline_std: float,
        alpha: float = 0.05,
        beta: float = 0.05,
        delta: float = 0.5
    ):
        """
        Inicializa SPRT.
        
        Args:
            baseline_mean: Media esperada bajo H0
            baseline_std: Desviación estándar esperada
            alpha: Probabilidad de error tipo I
            beta: Probabilidad de error tipo II
            delta: Tamaño de cambio a detectar (en unidades de std)
        """
        self.baseline_mean = baseline_mean
        self.baseline_std = baseline_std
        self.alpha = alpha
        self.beta = beta
        self.delta = delta
        
        # Thresholds
        self.upper_threshold = np.log((1 - beta) / alpha)
        self.lower_threshold = np.log(beta / (1 - alpha))
        
        # Estado
        self._log_likelihood_ratio = 0.0
        self._sample_count = 0
        
        logger.info(
            f"SPRT initialized: "
            f"baseline={baseline_mean:.4f}±{baseline_std:.4f}, "
            f"delta={delta}"
        )
    
    def update(self, value: float) -> Optional[str]:
        """
        Añade observación y testea hipótesis.
        
        Args:
            value: Nueva observación
            
        Returns:
            'drift' si H1 aceptada (hay cambio),
            'no_drift' si H0 aceptada (no cambio),
            None si aún no se puede decidir
        """
        # Mean bajo H1 (hipótesis alternativa)
        h1_mean = self.baseline_mean + self.delta * self.baseline_std
        
        # Log-likelihood ratio
        if self.baseline_std > 0:
            lr_h0 = -0.5 * ((value - self.baseline_mean) / self.baseline_std) ** 2
            lr_h1 = -0.5 * ((value - h1_mean) / self.baseline_std) ** 2
            
            self._log_likelihood_ratio += (lr_h1 - lr_h0)
        
        self._sample_count += 1
        
        # Verificar thresholds
        if self._log_likelihood_ratio >= self.upper_threshold:
            logger.warning(
                f"SPRT: Drift detected after {self._sample_count} samples"
            )
            self.reset()
            return 'drift'
        elif self._log_likelihood_ratio <= self.lower_threshold:
            # No drift confirmado
            self.reset()
            return 'no_drift'
        
        return None
    
    def reset(self):
        """Resetea test."""
        self._log_likelihood_ratio = 0.0
        self._sample_count = 0
    
    @property
    def current_ratio(self) -> float:
        """Ratio actual de log-likelihood."""
        return self._log_likelihood_ratio


class DriftDetector:
    """
    Drift detector combinado usando ADWIN y SPRT.
    
    Monitorea múltiples métricas y reporta drift cuando
    alguno de los detectores lo identifica.
    """
    
    def __init__(
        self,
        baseline_metrics: dict,
        sensitivity: str = 'medium'
    ):
        """
        Inicializa detector combinado.
        
        Args:
            baseline_metrics: Dict con métricas baseline
                {
                    'accuracy': {'mean': 0.65, 'std': 0.05},
                    'sharpe': {'mean': 1.2, 'std': 0.3},
                    ...
                }
            sensitivity: 'low', 'medium', 'high'
        """
        self.baseline_metrics = baseline_metrics
        
        # Configurar sensibilidad
        sensitivity_configs = {
            'low': {'delta_adwin': 0.005, 'delta_sprt': 1.0},
            'medium': {'delta_adwin': 0.002, 'delta_sprt': 0.5},
            'high': {'delta_adwin': 0.001, 'delta_sprt': 0.25}
        }
        
        config = sensitivity_configs.get(sensitivity, sensitivity_configs['medium'])
        
        # Inicializar detectores por métrica
        self._adwin_detectors = {}
        self._sprt_detectors = {}
        
        for metric_name, metric_stats in baseline_metrics.items():
            # ADWIN
            self._adwin_detectors[metric_name] = ADWIN(
                delta=config['delta_adwin']
            )
            
            # SPRT
            self._sprt_detectors[metric_name] = SPRT(
                baseline_mean=metric_stats['mean'],
                baseline_std=metric_stats['std'],
                delta=config['delta_sprt']
            )
        
        self._drift_history: List[dict] = []
        
        logger.info(
            f"DriftDetector initialized: "
            f"{len(baseline_metrics)} metrics, sensitivity={sensitivity}"
        )
    
    def update(self, metrics: dict) -> dict:
        """
        Actualiza con nuevas métricas y verifica drift.
        
        Args:
            metrics: Dict con valores actuales de métricas
            
        Returns:
            Dict con resultados de detección
        """
        results = {
            'drift_detected': False,
            'drifted_metrics': [],
            'timestamp': datetime.now()
        }
        
        for metric_name, value in metrics.items():
            if metric_name not in self._adwin_detectors:
                continue
            
            # Test ADWIN
            adwin_drift = self._adwin_detectors[metric_name].update(value)
            
            # Test SPRT
            sprt_result = self._sprt_detectors[metric_name].update(value)
            
            # Marcar drift si alguno lo detecta
            if adwin_drift or sprt_result == 'drift':
                results['drift_detected'] = True
                results['drifted_metrics'].append({
                    'metric': metric_name,
                    'value': value,
                    'baseline_mean': self.baseline_metrics[metric_name]['mean'],
                    'detector': 'ADWIN' if adwin_drift else 'SPRT'
                })
        
        if results['drift_detected']:
            self._drift_history.append(results)
            
            logger.warning(
                f"Drift detected in metrics: "
                f"{[m['metric'] for m in results['drifted_metrics']]}"
            )
        
        return results
    
    def get_drift_history(self) -> List[dict]:
        """Obtiene historial de drift detectado."""
        return self._drift_history
    
    def reset_all(self):
        """Resetea todos los detectores."""
        for detector in self._adwin_detectors.values():
            detector.reset()
        
        for detector in self._sprt_detectors.values():
            detector.reset()
        
        self._drift_history.clear()
        
        logger.info("All drift detectors reset")