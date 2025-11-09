"""
Regime Engine - Versión Final Institucional
Con spread baseline estable, Roll en log-returns, y config por instrumento.
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
from collections import deque
import logging
import yaml
from pathlib import Path

logger = logging.getLogger(__name__)


class RegimeEngine:
    """
    Clasifica régimen de mercado por instrumento con features cuantificables.
    
    VERSIÓN FINAL con correcciones institucionales:
    1. Spread baseline: rolling median del spread propio (100-300 ticks)
    2. Roll estimator: usa Δlog precio (escala-invariante)
    3. Thresholds por instrumento: cargados desde YAML
    4. Liquidity shutdown → p_shock ≥ 0.85
    5. Telemetría completa con batch_id y data_slice_id
    """
    
    def __init__(self, min_dwell_ticks: int = 5, timeframe_seconds: int = 60,
                 config_path: str = "config/regime_thresholds.yaml"):
        """
        Args:
            min_dwell_ticks: Mínimo de ticks consecutivos antes de cambiar régimen
            timeframe_seconds: Timeframe de las barras en segundos
            config_path: Ruta al archivo YAML de thresholds por instrumento
        """
        # Historial de clasificaciones
        self.regime_history: Dict[str, deque] = {}
        self.current_regime: Dict[str, str] = {}
        self.candidate_regime_buffer: Dict[str, deque] = {}
        
        # Caché de features caros
        self.hurst_cache: Dict[str, Tuple[float, datetime]] = {}
        self.hurst_cache_ttl_seconds = 300
        
        self.followthrough_cache: Dict[str, Tuple[float, datetime]] = {}
        self.followthrough_cache_ttl_seconds = 120
        
        # Caché de spread baseline por instrumento
        self.spread_baseline_cache: Dict[str, deque] = {}  # Rolling window de spreads
        self.spread_baseline_window = 200  # 200 ticks de historia
        
        # Configuración
        self.min_dwell_ticks = min_dwell_ticks
        self.timeframe_seconds = timeframe_seconds
        
        # Cargar thresholds por instrumento desde YAML
        self.instrument_configs = self._load_instrument_configs(config_path)
        
        # Thresholds globales (invariantes)
        self.global_thresholds = {
            'hurst_range_max': 0.45,
            'adx_range_max': 15.0,
            'ofi_persistence_trend_min': 0.6,
            'spread_shock_multiplier': 2.5,
            'hurst_max_lags': 12,
            'spread_baseline_min_samples': 50,  # Mínimo para considerar baseline válido
        }
        
        # Contadores para métricas
        self.stats = {
            'regime_changes': 0,
            'dwell_time_blocks': 0,
            'shock_detections': 0,
            'liquidity_shutdowns': 0,
            'hurst_cache_hits': 0,
            'hurst_cache_misses': 0,
            'spread_baseline_missing': 0,
        }
    
    def _load_instrument_configs(self, config_path: str) -> Dict:
        """Carga configuración de thresholds por instrumento desde YAML."""
        try:
            with open(config_path, 'r') as f:
                configs = yaml.safe_load(f)
            
            logger.info(f"Loaded instrument configs for {len(configs)} instruments")
            return configs
        
        except Exception as e:
            logger.warning(f"Failed to load instrument config from {config_path}: {e}")
            logger.warning("Using hardcoded DEFAULT config for all instruments")
            
            # Fallback a config default
            return {
                'DEFAULT': {
                    'adx_trend_enter': 28.0,
                    'adx_trend_exit': 22.0,
                    'spread_bp_shutdown': 50.0,
                    'follow_through_trend_min': 0.60,
                    'hurst_trend_min': 0.55,
                    'vol_ratio_shock_min': 1.5
                }
            }
    
    def _get_instrument_config(self, symbol: str) -> Dict:
        """Obtiene config específico del instrumento o DEFAULT."""
        if symbol in self.instrument_configs:
            return self.instrument_configs[symbol]
        else:
            logger.debug(f"No specific config for {symbol}, using DEFAULT")
            return self.instrument_configs.get('DEFAULT', {
                'adx_trend_enter': 28.0,
                'adx_trend_exit': 22.0,
                'spread_bp_shutdown': 50.0,
                'follow_through_trend_min': 0.60,
                'hurst_trend_min': 0.55,
                'vol_ratio_shock_min': 1.5
            })
    
    def classify_regime(self, data: pd.DataFrame, features: Dict, 
                       batch_id: Optional[str] = None,
                       data_slice_id: Optional[str] = None) -> Dict[str, float]:
        """
        Clasifica régimen con batch_id y data_slice_id para reproducibilidad.
        
        Args:
            data: DataFrame OHLCV
            features: Features del motor
            batch_id: ID del batch de decisión (para logging)
            data_slice_id: ID del slice de datos (para reproducibilidad)
        """
        symbol = data.attrs.get('symbol', 'UNKNOWN')
        
        # Calcular features de régimen
        regime_features = self._calculate_regime_features(data, features, symbol)
        
        # Scoring con config específico del instrumento
        raw_probs = self._score_regimes(regime_features, symbol)
        
        # Régimen dominante
        raw_regime = max(raw_probs, key=raw_probs.get)
        
        # Aplicar dwell-time
        persistent_regime, persistent_probs = self._apply_dwell_time(
            symbol, raw_regime, raw_probs, regime_features, batch_id, data_slice_id
        )
        
        # Guardar historial
        self._record_regime(symbol, persistent_regime, persistent_probs, regime_features)
        
        return persistent_probs
    
    def _calculate_regime_features(self, data: pd.DataFrame, features: Dict, symbol: str) -> Dict:
        """Calcula features con spread baseline estable y Roll correcto."""
        
        close = data['close']
        high = data['high']
        low = data['low']
        
        # ===== SPREAD CON BASELINE ESTABLE =====
        spread_bp, median_spread_bp, spread_shock_ratio, spread_proxy_used = self._calculate_spread_metrics(
            data, features, symbol
        )
        
        # ===== HURST (cached) =====
        hurst = self._calculate_hurst_cached(close, symbol)
        
        # ===== ADX =====
        adx = self._calculate_adx(data)
        
        # ===== VOLATILITY (ventanas por tiempo) =====
        returns = close.pct_change().dropna()
        
        bars_4h = int((4 * 3600) / self.timeframe_seconds)
        bars_24h = int((24 * 3600) / self.timeframe_seconds)
        
        vol_4h = returns.tail(bars_4h).std() if len(returns) >= bars_4h else returns.std()
        vol_24h = returns.tail(bars_24h).std() if len(returns) >= bars_24h else returns.std()
        vol_ratio = vol_4h / vol_24h if vol_24h > 0 else 1.0
        
        bars_1h = int(3600 / self.timeframe_seconds)
        vol_series = returns.rolling(window=bars_1h).std()
        vol_of_vol = vol_series.std() / vol_series.mean() if vol_series.mean() > 0 else 0
        
        # ===== OFI PERSISTENCE =====
        ofi_values = features.get('ofi_history', [])
        ofi_persistence = abs(np.corrcoef(ofi_values[-20:], range(20))[0, 1]) if len(ofi_values) > 20 else 0.0
        
        # ===== FOLLOW-THROUGH (cached, sin leak) =====
        follow_through = self._calculate_follow_through_no_leak(data, symbol)
        
        # ===== VPIN =====
        vpin = features.get('vpin', 0.5)
        
        # ===== DATA QUALITY =====
        data_quality = len(data) >= bars_1h * 2
        
        # ===== LIQUIDITY SHUTDOWN =====
        instrument_config = self._get_instrument_config(symbol)
        shutdown_threshold = instrument_config['spread_bp_shutdown']
        liquidity_shutdown = spread_bp > shutdown_threshold
        
        if liquidity_shutdown:
            logger.warning(
                f"LIQUIDITY_SHUTDOWN: {symbol} spread={spread_bp:.1f}bp > {shutdown_threshold}bp "
                f"(spread_proxy={spread_proxy_used})"
            )
            self.stats['liquidity_shutdowns'] += 1
        
        return {
            'hurst': hurst,
            'adx': adx,
            'vol_ratio': vol_ratio,
            'vol_of_vol': vol_of_vol,
            'ofi_persistence': ofi_persistence,
            'follow_through': follow_through,
            'spread_bp': spread_bp,
            'median_spread_bp': median_spread_bp,
            'spread_shock_ratio': spread_shock_ratio,
            'spread_proxy_used': spread_proxy_used,
            'vpin': vpin,
            'data_quality': data_quality,
            'liquidity_shutdown': liquidity_shutdown
        }
    
    def _calculate_spread_metrics(self, data: pd.DataFrame, features: Dict, 
                                   symbol: str) -> Tuple[float, float, float, str]:
        """
        Calcula spread con baseline estable (rolling median del spread propio).
        
        Returns:
            (current_spread_bp, median_spread_bp, spread_shock_ratio, proxy_used)
        """
        bid = features.get('bid', None)
        ask = features.get('ask', None)
        
        if bid is not None and ask is not None and bid > 0:
            # Spread real disponible
            current_spread_bp = ((ask - bid) / bid) * 10000
            proxy_used = 'BID_ASK'
        else:
            # Usar Roll estimator en log-returns
            current_spread_bp = self._estimate_effective_spread_roll_log(data['close'])
            proxy_used = 'ROLL'
        
        # Actualizar baseline cache
        if symbol not in self.spread_baseline_cache:
            self.spread_baseline_cache[symbol] = deque(maxlen=self.spread_baseline_window)
        
        self.spread_baseline_cache[symbol].append(current_spread_bp)
        
        # Calcular median spread baseline
        spread_history = list(self.spread_baseline_cache[symbol])
        
        if len(spread_history) >= self.global_thresholds['spread_baseline_min_samples']:
            median_spread_bp = np.median(spread_history)
            spread_shock_ratio = current_spread_bp / median_spread_bp if median_spread_bp > 0 else 1.0
        else:
            # No hay baseline suficiente
            median_spread_bp = 0.0
            spread_shock_ratio = 1.0  # Neutral, no sobredetectar shock
            
            logger.debug(
                f"REASON: NO_SPREAD_BASELINE for {symbol} "
                f"(samples={len(spread_history)}, need={self.global_thresholds['spread_baseline_min_samples']})"
            )
            self.stats['spread_baseline_missing'] += 1
        
        return current_spread_bp, median_spread_bp, spread_shock_ratio, proxy_used
    
    def _estimate_effective_spread_roll_log(self, close: pd.Series) -> float:
        """
        Roll estimator usando Δlog precio (escala-invariante).
        Roll (1984): spread = 2 * sqrt(-cov(Δlog(p_t), Δlog(p_{t-1})))
        """
        try:
            if len(close) < 10:
                return 0.0
            
            # Log-returns en lugar de pct_change
            log_returns = np.log(close / close.shift(1)).dropna()
            
            if len(log_returns) < 2:
                return 0.0
            
            # Covariance de log-returns consecutivos
            cov = np.cov(log_returns.iloc[:-1], log_returns.iloc[1:])[0, 1]
            
            if cov < 0:
                # Roll clásico
                spread_pct = 2 * np.sqrt(-cov)
                spread_bp = spread_pct * 10000
                return spread_bp
            else:
                # Covariance positiva: usar upper bound
                spread_bp = 2 * log_returns.std() * 10000
                return spread_bp
        
        except Exception as e:
            logger.debug(f"Roll estimator (log) failed: {e}")
            return 0.0
    
    def _calculate_hurst_cached(self, series: pd.Series, symbol: str) -> float:
        """Hurst con caché."""
        now = datetime.now()
        
        if symbol in self.hurst_cache:
            cached_value, cached_time = self.hurst_cache[symbol]
            age = (now - cached_time).total_seconds()
            
            if age < self.hurst_cache_ttl_seconds:
                self.stats['hurst_cache_hits'] += 1
                return cached_value
        
        self.stats['hurst_cache_misses'] += 1
        hurst = self._calculate_hurst_exponent(
            series, 
            lags=self.global_thresholds['hurst_max_lags']
        )
        
        self.hurst_cache[symbol] = (hurst, now)
        return hurst
    
    def _calculate_follow_through_no_leak(self, data: pd.DataFrame, symbol: str) -> float:
        """Follow-through sin lookahead (cached)."""
        now = datetime.now()
        
        if symbol in self.followthrough_cache:
            cached_value, cached_time = self.followthrough_cache[symbol]
            age = (now - cached_time).total_seconds()
            
            if age < self.followthrough_cache_ttl_seconds:
                return cached_value
        
        lookback = 50
        confirm_bars = 5
        
        if len(data) < lookback + confirm_bars + 1:
            return 0.5
        
        high = data['high']
        low = data['low']
        close = data['close']
        
        rolling_high = high.rolling(window=20).max().shift(1)
        rolling_low = low.rolling(window=20).min().shift(1)
        
        breakout_up = close > rolling_high
        breakout_down = close < rolling_low
        
        continued = 0
        total = 0
        
        # CRÍTICO: terminar en len(close) - confirm_bars - 1
        end_idx = len(close) - confirm_bars - 1
        start_idx = max(0, end_idx - lookback)
        
        for i in range(start_idx, end_idx):
            if breakout_up.iloc[i]:
                total += 1
                if close.iloc[i + confirm_bars] > close.iloc[i]:
                    continued += 1
            elif breakout_down.iloc[i]:
                total += 1
                if close.iloc[i + confirm_bars] < close.iloc[i]:
                    continued += 1
        
        ratio = (continued / total) if total > 0 else 0.5
        self.followthrough_cache[symbol] = (ratio, now)
        
        return ratio
    
    def _score_regimes(self, features: Dict, symbol: str) -> Dict[str, float]:
        """Score con histéresis ADX y config por instrumento."""
        
        # Obtener config del instrumento
        config = self._get_instrument_config(symbol)
        
        trend_score = 0.0
        range_score = 0.0
        shock_score = 0.0
        
        # LIQUIDITY SHUTDOWN: forzar p_shock ≥ 0.85
        if features['liquidity_shutdown']:
            return {'trend': 0.075, 'range': 0.075, 'shock': 0.85}
        
        if not features['data_quality']:
            return {'trend': 0.33, 'range': 0.33, 'shock': 0.33}
        
        # ===== HURST =====
        hurst = features['hurst']
        hurst_trend_min = config['hurst_trend_min']
        
        if hurst > hurst_trend_min:
            trend_score += 0.3
        elif hurst < self.global_thresholds['hurst_range_max']:
            range_score += 0.3
        else:
            trend_score += 0.15
            range_score += 0.15
        
        # ===== ADX CON HISTÉRESIS =====
        adx = features['adx']
        current_regime = self.current_regime.get(symbol, 'range')
        
        adx_enter = config['adx_trend_enter']
        adx_exit = config['adx_trend_exit']
        
        if current_regime == 'trend':
            # En trend: usar threshold más bajo para salir (histéresis)
            if adx < adx_exit:
                range_score += 0.25
            else:
                trend_score += 0.25
        else:
            # No en trend: usar threshold más alto para entrar
            if adx > adx_enter:
                trend_score += 0.25
            elif adx < self.global_thresholds['adx_range_max']:
                range_score += 0.25
            else:
                trend_score += 0.1
                range_score += 0.1
        
        # ===== VOLATILITY SHOCK =====
        vol_ratio = features['vol_ratio']
        vol_of_vol = features['vol_of_vol']
        vol_ratio_shock_min = config['vol_ratio_shock_min']
        
        if vol_ratio > vol_ratio_shock_min or vol_of_vol > 1.5:
            shock_score += 0.4
            trend_score *= 0.5
            range_score *= 0.5
            self.stats['shock_detections'] += 1
        
        # ===== OFI PERSISTENCE =====
        if features['ofi_persistence'] > self.global_thresholds['ofi_persistence_trend_min']:
            trend_score += 0.2
        else:
            range_score += 0.2
        
        # ===== FOLLOW-THROUGH =====
        follow_through = features['follow_through']
        follow_through_min = config['follow_through_trend_min']
        
        if follow_through > follow_through_min:
            trend_score += 0.15
        elif follow_through < 0.4:
            range_score += 0.15
        
        # ===== SPREAD SHOCK =====
        if features['spread_shock_ratio'] > self.global_thresholds['spread_shock_multiplier']:
            shock_score += 0.25
        
        # ===== VPIN =====
        if features['vpin'] > 0.7:
            shock_score += 0.1
        
        # ===== NORMALIZACIÓN =====
        total = trend_score + range_score + shock_score
        
        if total == 0:
            return {'trend': 0.33, 'range': 0.33, 'shock': 0.33}
        
        return {
            'trend': trend_score / total,
            'range': range_score / total,
            'shock': shock_score / total
        }
    
    def _apply_dwell_time(self, symbol: str, new_regime: str, 
                          new_probs: Dict[str, float], features: Dict,
                          batch_id: Optional[str], data_slice_id: Optional[str]) -> tuple:
        """Dwell-time con batch_id y data_slice_id para reproducibilidad."""
        
        if symbol not in self.current_regime:
            self.current_regime[symbol] = new_regime
            self.candidate_regime_buffer[symbol] = deque(maxlen=self.min_dwell_ticks)
            
            logger.info(
                f"REGIME_INIT: {symbol} → {new_regime} "
                f"(batch_id={batch_id}, data_slice_id={data_slice_id}, "
                f"probs={new_probs}, features={self._get_feature_summary(features)})"
            )
            
            return new_regime, new_probs
        
        current = self.current_regime[symbol]
        buffer = self.candidate_regime_buffer[symbol]
        
        if new_regime == current:
            buffer.clear()
            return current, new_probs
        
        buffer.append(new_regime)
        
        if len(buffer) == self.min_dwell_ticks:
            if all(r == new_regime for r in buffer):
                reason_codes = self._get_regime_change_reasons(features)
                
                logger.info(
                    f"REGIME_CHANGE: {symbol} {current} → {new_regime} "
                    f"(batch_id={batch_id}, data_slice_id={data_slice_id}, "
                    f"dwell_ticks={self.min_dwell_ticks}, reason_codes={reason_codes}, "
                    f"features={self._get_feature_summary(features)})"
                )
                
                self.current_regime[symbol] = new_regime
                self.stats['regime_changes'] += 1
                buffer.clear()
                return new_regime, new_probs
            else:
                self.stats['dwell_time_blocks'] += 1
        
        # Mantener con probs mezcladas
        alpha = len(buffer) / self.min_dwell_ticks
        current_probs = self._get_regime_probs_for_name(current)
        
        blended_probs = {
            regime: (1 - alpha) * current_probs[regime] + alpha * new_probs[regime]
            for regime in ['trend', 'range', 'shock']
        }
        
        return current, blended_probs
    
    def _get_regime_change_reasons(self, features: Dict) -> List[str]:
        """Genera reason codes para telemetría."""
        reasons = []
        
        if features.get('liquidity_shutdown', False):
            reasons.append('LIQUIDITY_CRITICAL')
        
        if features['adx'] > 28:
            reasons.append('ADX_HIGH')
        elif features['adx'] < 22:
            reasons.append('ADX_LOW')
        
        if features['hurst'] > 0.55:
            reasons.append('HURST_TRENDING')
        elif features['hurst'] < 0.45:
            reasons.append('HURST_REVERTING')
        
        if features['spread_shock_ratio'] > 2.5:
            reasons.append('SPREAD_SHOCK')
        
        if features['vol_ratio'] > 1.5:
            reasons.append('VOL_SPIKE')
        
        if not features.get('median_spread_bp', 0):
            reasons.append('NO_SPREAD_BASELINE')
        
        return reasons if reasons else ['COMPOSITE']
    
    def _get_feature_summary(self, features: Dict) -> Dict:
        """Features clave para logging."""
        return {
            'adx': round(features['adx'], 1),
            'hurst': round(features['hurst'], 3),
            'spread_bp': round(features['spread_bp'], 1),
            'spread_proxy': features.get('spread_proxy_used', 'UNKNOWN'),
            'vol_ratio': round(features['vol_ratio'], 2),
            'follow_through': round(features['follow_through'], 2)
        }
    
    def _get_regime_probs_for_name(self, regime_name: str) -> Dict[str, float]:
        """Convierte nombre a probs."""
        if regime_name == 'trend':
            return {'trend': 0.9, 'range': 0.05, 'shock': 0.05}
        elif regime_name == 'range':
            return {'trend': 0.05, 'range': 0.9, 'shock': 0.05}
        else:
            return {'trend': 0.05, 'range': 0.05, 'shock': 0.9}
    
    def _record_regime(self, symbol: str, regime: str, probs: Dict, features: Dict):
        """Guarda en historial."""
        if symbol not in self.regime_history:
            self.regime_history[symbol] = deque(maxlen=1000)
        
        self.regime_history[symbol].append({
            'timestamp': datetime.now(),
            'regime': regime,
            'probs': probs,
            'features': features
        })
    
    def _calculate_hurst_exponent(self, series: pd.Series, lags: int = 12) -> float:
        """Hurst con límite de lags."""
        try:
            if len(series) < lags * 3:
                return 0.5
            
            tau = []
            rs_values = []
            
            for lag in range(2, min(lags, len(series) // 3)):
                n_chunks = len(series) // lag
                if n_chunks < 2:
                    continue
                
                rs_chunk = []
                for i in range(n_chunks):
                    chunk = series.iloc[i*lag:(i+1)*lag].values
                    if len(chunk) < lag:
                        continue
                    
                    mean_adj = chunk - np.mean(chunk)
                    cum_sum = np.cumsum(mean_adj)
                    R = np.max(cum_sum) - np.min(cum_sum)
                    S = np.std(chunk, ddof=1)
                    
                    if S > 0:
                        rs_chunk.append(R / S)
                
                if rs_chunk:
                    tau.append(lag)
                    rs_values.append(np.mean(rs_chunk))
            
            if len(tau) < 2:
                return 0.5
            
            hurst = np.polyfit(np.log(tau), np.log(rs_values), 1)[0]
            return np.clip(hurst, 0.3, 0.7)
        
        except Exception as e:
            logger.debug(f"Hurst failed: {e}")
            return 0.5
    
    def _calculate_adx(self, data: pd.DataFrame, period: int = 14) -> float:
        """ADX estándar."""
        try:
            high = data['high']
            low = data['low']
            close = data['close']
            
            if len(data) < period * 2:
                return 15.0
            
            tr1 = high - low
            tr2 = abs(high - close.shift(1))
            tr3 = abs(low - close.shift(1))
            tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
            
            up_move = high - high.shift(1)
            down_move = low.shift(1) - low
            
            plus_dm = np.where((up_move > down_move) & (up_move > 0), up_move, 0)
            minus_dm = np.where((down_move > up_move) & (down_move > 0), down_move, 0)
            
            atr = tr.rolling(window=period).mean()
            plus_di = 100 * pd.Series(plus_dm).rolling(window=period).mean() / atr
            minus_di = 100 * pd.Series(minus_dm).rolling(window=period).mean() / atr
            
            dx = 100 * abs(plus_di - minus_di) / (plus_di + minus_di)
            adx = dx.rolling(window=period).mean()
            
            return float(adx.iloc[-1]) if not adx.empty else 15.0
        
        except Exception as e:
            logger.debug(f"ADX failed: {e}")
            return 15.0
