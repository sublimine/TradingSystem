"""
Data Validator - Validación robusta de datos de mercado
Verifica calidad de cada tick antes de procesamiento.
"""

import logging
from typing import Dict, List, Tuple, Optional
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class ValidationSeverity(Enum):
    """Severidad de validación."""
    CRITICAL = "critical"  # Rechaza el tick
    WARNING = "warning"    # Logea pero continúa
    INFO = "info"          # Solo informativo


@dataclass
class ValidationResult:
    """Resultado de validación."""
    is_valid: bool
    severity: ValidationSeverity
    check_name: str
    message: str
    instrument: str
    timestamp: datetime


class DataValidator:
    """
    Validador de datos de mercado institucional.
    
    Ejecuta batería completa de verificaciones:
    - Timestamps duplicados o fuera de orden
    - OHLC inconsistente
    - Valores negativos o cero anómalos
    - Outliers estadísticos
    - Volúmenes anómalos
    - Spreads expandidos
    - Gaps temporales excesivos
    - Patrones sospechosos
    """
    
    def __init__(
        self,
        outlier_std_threshold: float = 5.0,
        volume_std_threshold: float = 3.0,
        spread_multiplier_threshold: float = 3.0,
        max_gap_minutes: int = 5,
        recent_bars_window: int = 100
    ):
        """
        Inicializa validador.
        
        Args:
            outlier_std_threshold: Desviaciones estándar para outlier de precio
            volume_std_threshold: Desviaciones estándar para volumen anómalo
            spread_multiplier_threshold: Multiplicador de spread mediano
            max_gap_minutes: Minutos máximos sin datos
            recent_bars_window: Ventana de barras recientes para estadísticas
        """
        self.outlier_std_threshold = outlier_std_threshold
        self.volume_std_threshold = volume_std_threshold
        self.spread_multiplier_threshold = spread_multiplier_threshold
        self.max_gap_minutes = max_gap_minutes
        self.recent_bars_window = recent_bars_window
        
        # Cache de timestamps recientes por instrumento
        self._recent_timestamps: Dict[str, List[datetime]] = {}
        
        # Estadísticas rolling por instrumento
        self._price_stats: Dict[str, Dict] = {}
        self._volume_stats: Dict[str, Dict] = {}
        self._spread_stats: Dict[str, Dict] = {}
        
        logger.info("DataValidator inicializado")
    
    def validate_bar(
        self,
        instrument: str,
        timestamp: datetime,
        open_price: float,
        high: float,
        low: float,
        close: float,
        volume: float,
        bid: Optional[float] = None,
        ask: Optional[float] = None
    ) -> Tuple[bool, List[ValidationResult]]:
        """
        Valida una barra completa.
        
        Args:
            instrument: Instrumento
            timestamp: Timestamp de la barra
            open_price: Precio de apertura
            high: Precio máximo
            low: Precio mínimo
            close: Precio de cierre
            volume: Volumen
            bid: Precio bid (opcional)
            ask: Precio ask (opcional)
            
        Returns:
            (is_valid, list_of_validation_results)
        """
        results = []
        
        # Verificaciones críticas
        results.extend(self._check_duplicate_timestamp(instrument, timestamp))
        results.extend(self._check_timestamp_order(instrument, timestamp))
        results.extend(self._check_ohlc_consistency(
            instrument, timestamp, open_price, high, low, close
        ))
        results.extend(self._check_negative_or_zero(
            instrument, timestamp, open_price, high, low, close, volume
        ))
        results.extend(self._check_temporal_gap(instrument, timestamp))
        
        # Verificaciones de advertencia
        results.extend(self._check_price_outlier(
            instrument, timestamp, close
        ))
        results.extend(self._check_volume_anomaly(
            instrument, timestamp, volume
        ))
        
        if bid is not None and ask is not None:
            results.extend(self._check_spread_anomaly(
                instrument, timestamp, bid, ask
            ))
        
        # Actualizar estadísticas
        self._update_statistics(instrument, timestamp, close, volume, bid, ask)
        
        # Determinar si es válido (no hay errores críticos)
        is_valid = not any(
            r.severity == ValidationSeverity.CRITICAL for r in results
        )
        
        return is_valid, results
    
    def _check_duplicate_timestamp(
        self,
        instrument: str,
        timestamp: datetime
    ) -> List[ValidationResult]:
        """Verifica timestamps duplicados."""
        if instrument not in self._recent_timestamps:
            self._recent_timestamps[instrument] = []
        
        recent = self._recent_timestamps[instrument]
        
        if timestamp in recent:
            return [ValidationResult(
                is_valid=False,
                severity=ValidationSeverity.CRITICAL,
                check_name="duplicate_timestamp",
                message=f"Duplicate timestamp: {timestamp}",
                instrument=instrument,
                timestamp=timestamp
            )]
        
        return []
    
    def _check_timestamp_order(
        self,
        instrument: str,
        timestamp: datetime
    ) -> List[ValidationResult]:
        """Verifica orden temporal."""
        if instrument not in self._recent_timestamps:
            return []
        
        recent = self._recent_timestamps[instrument]
        
        if recent and timestamp < recent[-1]:
            return [ValidationResult(
                is_valid=False,
                severity=ValidationSeverity.CRITICAL,
                check_name="timestamp_out_of_order",
                message=f"Timestamp {timestamp} is before last {recent[-1]}",
                instrument=instrument,
                timestamp=timestamp
            )]
        
        return []
    
    def _check_ohlc_consistency(
        self,
        instrument: str,
        timestamp: datetime,
        open_price: float,
        high: float,
        low: float,
        close: float
    ) -> List[ValidationResult]:
        """Verifica consistencia OHLC."""
        issues = []
        
        # High debe ser >= max(open, close)
        if high < max(open_price, close):
            issues.append(ValidationResult(
                is_valid=False,
                severity=ValidationSeverity.CRITICAL,
                check_name="ohlc_high_inconsistent",
                message=f"High {high} < max(open {open_price}, close {close})",
                instrument=instrument,
                timestamp=timestamp
            ))
        
        # Low debe ser <= min(open, close)
        if low > min(open_price, close):
            issues.append(ValidationResult(
                is_valid=False,
                severity=ValidationSeverity.CRITICAL,
                check_name="ohlc_low_inconsistent",
                message=f"Low {low} > min(open {open_price}, close {close})",
                instrument=instrument,
                timestamp=timestamp
            ))
        
        return issues
    
    def _check_negative_or_zero(
        self,
        instrument: str,
        timestamp: datetime,
        open_price: float,
        high: float,
        low: float,
        close: float,
        volume: float
    ) -> List[ValidationResult]:
        """Verifica valores negativos o cero anómalos."""
        issues = []
        
        prices = [
            ("open", open_price),
            ("high", high),
            ("low", low),
            ("close", close)
        ]
        
        for name, price in prices:
            if price <= 0:
                issues.append(ValidationResult(
                    is_valid=False,
                    severity=ValidationSeverity.CRITICAL,
                    check_name="negative_or_zero_price",
                    message=f"{name} price is {price} (invalid)",
                    instrument=instrument,
                    timestamp=timestamp
                ))
        
        if volume < 0:
            issues.append(ValidationResult(
                is_valid=False,
                severity=ValidationSeverity.CRITICAL,
                check_name="negative_volume",
                message=f"Volume is {volume} (negative)",
                instrument=instrument,
                timestamp=timestamp
            ))
        
        return issues
    
    def _check_temporal_gap(
        self,
        instrument: str,
        timestamp: datetime
    ) -> List[ValidationResult]:
        """Verifica gaps temporales excesivos."""
        if instrument not in self._recent_timestamps:
            return []
        
        recent = self._recent_timestamps[instrument]
        
        if recent:
            last_ts = recent[-1]
            gap = (timestamp - last_ts).total_seconds() / 60.0
            
            if gap > self.max_gap_minutes:
                return [ValidationResult(
                    is_valid=False,
                    severity=ValidationSeverity.CRITICAL,
                    check_name="excessive_temporal_gap",
                    message=f"Gap of {gap:.1f} minutes (limit {self.max_gap_minutes})",
                    instrument=instrument,
                    timestamp=timestamp
                )]
        
        return []
    
    def _check_price_outlier(
        self,
        instrument: str,
        timestamp: datetime,
        price: float
    ) -> List[ValidationResult]:
        """Verifica outliers de precio."""
        if instrument not in self._price_stats:
            return []
        
        stats = self._price_stats[instrument]
        
        if 'mean' not in stats or 'std' not in stats:
            return []
        
        mean = stats['mean']
        std = stats['std']
        
        if std > 0:
            z_score = abs(price - mean) / std
            
            if z_score > self.outlier_std_threshold:
                return [ValidationResult(
                    is_valid=True,
                    severity=ValidationSeverity.WARNING,
                    check_name="price_outlier",
                    message=f"Price {price} is {z_score:.2f} std from mean {mean:.5f}",
                    instrument=instrument,
                    timestamp=timestamp
                )]
        
        return []
    
    def _check_volume_anomaly(
        self,
        instrument: str,
        timestamp: datetime,
        volume: float
    ) -> List[ValidationResult]:
        """Verifica anomalías de volumen."""
        if instrument not in self._volume_stats:
            return []
        
        stats = self._volume_stats[instrument]
        
        if 'mean' not in stats or 'std' not in stats:
            return []
        
        mean = stats['mean']
        std = stats['std']
        
        if std > 0 and mean > 0:
            z_score = abs(volume - mean) / std
            
            if z_score > self.volume_std_threshold:
                return [ValidationResult(
                    is_valid=True,
                    severity=ValidationSeverity.WARNING,
                    check_name="volume_anomaly",
                    message=f"Volume {volume:.0f} is {z_score:.2f} std from mean {mean:.0f}",
                    instrument=instrument,
                    timestamp=timestamp
                )]
        
        return []
    
    def _check_spread_anomaly(
        self,
        instrument: str,
        timestamp: datetime,
        bid: float,
        ask: float
    ) -> List[ValidationResult]:
        """Verifica spreads anómalos."""
        spread = ask - bid
        
        if spread < 0:
            return [ValidationResult(
                is_valid=False,
                severity=ValidationSeverity.CRITICAL,
                check_name="negative_spread",
                message=f"Negative spread: bid={bid}, ask={ask}",
                instrument=instrument,
                timestamp=timestamp
            )]
        
        if instrument not in self._spread_stats:
            return []
        
        stats = self._spread_stats[instrument]
        
        if 'median' not in stats:
            return []
        
        median_spread = stats['median']
        
        if median_spread > 0:
            multiplier = spread / median_spread
            
            if multiplier > self.spread_multiplier_threshold:
                return [ValidationResult(
                    is_valid=True,
                    severity=ValidationSeverity.WARNING,
                    check_name="spread_expanded",
                    message=f"Spread {spread:.5f} is {multiplier:.1f}x median {median_spread:.5f}",
                    instrument=instrument,
                    timestamp=timestamp
                )]
        
        return []
    
    def _update_statistics(
        self,
        instrument: str,
        timestamp: datetime,
        price: float,
        volume: float,
        bid: Optional[float],
        ask: Optional[float]
    ):
        """Actualiza estadísticas rolling."""
        # Actualizar timestamps
        if instrument not in self._recent_timestamps:
            self._recent_timestamps[instrument] = []
        
        self._recent_timestamps[instrument].append(timestamp)
        
        # Mantener solo ventana reciente
        if len(self._recent_timestamps[instrument]) > self.recent_bars_window:
            self._recent_timestamps[instrument].pop(0)
        
        # Actualizar estadísticas de precio
        if instrument not in self._price_stats:
            self._price_stats[instrument] = {'prices': []}
        
        self._price_stats[instrument]['prices'].append(price)
        
        if len(self._price_stats[instrument]['prices']) > self.recent_bars_window:
            self._price_stats[instrument]['prices'].pop(0)
        
        prices = self._price_stats[instrument]['prices']
        self._price_stats[instrument]['mean'] = np.mean(prices)
        self._price_stats[instrument]['std'] = np.std(prices)
        
        # Actualizar estadísticas de volumen
        if instrument not in self._volume_stats:
            self._volume_stats[instrument] = {'volumes': []}
        
        self._volume_stats[instrument]['volumes'].append(volume)
        
        if len(self._volume_stats[instrument]['volumes']) > self.recent_bars_window:
            self._volume_stats[instrument]['volumes'].pop(0)
        
        volumes = self._volume_stats[instrument]['volumes']
        self._volume_stats[instrument]['mean'] = np.mean(volumes)
        self._volume_stats[instrument]['std'] = np.std(volumes)
        
        # Actualizar estadísticas de spread
        if bid is not None and ask is not None:
            spread = ask - bid
            
            if instrument not in self._spread_stats:
                self._spread_stats[instrument] = {'spreads': []}
            
            self._spread_stats[instrument]['spreads'].append(spread)
            
            if len(self._spread_stats[instrument]['spreads']) > self.recent_bars_window:
                self._spread_stats[instrument]['spreads'].pop(0)
            
            spreads = self._spread_stats[instrument]['spreads']
            self._spread_stats[instrument]['median'] = np.median(spreads)
    
    def get_statistics(self, instrument: str) -> Dict:
        """Obtiene estadísticas actuales de un instrumento."""
        return {
            'price_stats': self._price_stats.get(instrument, {}),
            'volume_stats': self._volume_stats.get(instrument, {}),
            'spread_stats': self._spread_stats.get(instrument, {}),
            'recent_bars_count': len(self._recent_timestamps.get(instrument, []))
        }