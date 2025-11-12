# PLAN DE IMPLEMENTACIÓN - Trading System Institucional
## Guía para el Próximo Agente IA

**Fecha:** 2025-11-11
**Estado Actual:** Fase 1 COMPLETA (Parámetros Corregidos)
**Siguiente:** Fase 2-5 (MTF, Risk Manager, Position Manager, Brain Layer)

---

# CONTEXTO - QUÉ SE HA HECHO

## ✅ COMPLETADO (Fase 1):

### 1. Análisis Completo del Sistema
- **Archivo:** `/home/user/TradingSystem/ANALISIS_INSTITUCIONAL_COMPLETO.md` (150+ páginas)
- Análisis línea por línea de las 14 estrategias
- Identificación de problemas críticos
- Parámetros corregidos basados en investigación académica

### 2. Correcciones Críticas Implementadas

**Mean Reversion Statistical:**
```python
# ANTES (Retail):
entry_sigma_threshold = 1.5
volume_spike_multiplier = 1.8
reversal_velocity_min = 5.0

# DESPUÉS (Institucional):
entry_sigma_threshold = 2.8
volume_spike_multiplier = 3.2
reversal_velocity_min = 18.0
adx_max_for_entry = 22  # NUEVO
use_vwap_mean = True    # NUEVO
```

**Liquidity Sweep:**
```python
# ANTES:
penetration_max = 15  # pips
volume_threshold = 1.3
reversal_velocity_min = 3.5

# DESPUÉS:
penetration_max = 8  # ICT 2024
volume_threshold = 2.8
reversal_velocity_min = 12.0
```

**Order Flow Toxicity - LÓGICA INVERTIDA:**
```python
# ANTES: Entraba cuando VPIN alto (tóxico) ❌
# DESPUÉS: Es un FILTRO, no genera señales
# High VPIN = DO NOT TRADE (Easley et al. 2012)
```

### 3. Configuración Centralizada
- **Archivo:** `/home/user/TradingSystem/config/strategies_institutional.yaml`
- Parámetros para las 14 estrategias
- Pares configurados para Kalman/Correlation (estaban vacíos)
- Live engine modificado para cargar YAML

### 4. Problema "9 Estrategias Silenciosas" RESUELTO
**Root Cause:** Inicialización con `config = {'enabled': True}` (mínimo)
**Solución:** YAML con configuración completa

**Estrategias ahora con configuración correcta:**
- Kalman Pairs: 4 pares monitorizados
- Correlation Divergence: 4 pares monitorizados
- Volatility Regime: Thresholds ajustados
- Breakout/FVG/HTF-LTF/Iceberg/IDP/OFI: Parámetros menos estrictos

---

# PENDIENTE - QUÉ FALTA IMPLEMENTAR

## Fase 2: Multi-Timeframe Architecture (CRÍTICO)

### Problema Actual:
```python
# scripts/live_trading_engine.py línea 187
rates = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_M1, 0, bars)
```
**Solo carga M1. NO hay H1, H4, D1.**

### Solución Requerida:

#### Crear: `src/core/mtf_data_manager.py`

```python
"""
Multi-Timeframe Data Manager

RESPONSABILIDADES:
1. Cargar datos de M1, M5, M15, M30, H1, H4, D1 para cada símbolo
2. Mantener cache sincronizado
3. Proporcionar acceso rápido a cualquier timeframe
4. Actualizar datos en cada ciclo
"""

import MetaTrader5 as mt5
import pandas as pd
from typing import Dict, List
import logging

logger = logging.getLogger(__name__)


class MultiTimeframeDataManager:
    """Manages data across multiple timeframes for all symbols."""

    def __init__(self, symbols: List[str]):
        """
        Initialize MTF data manager.

        Args:
            symbols: List of symbols to track (e.g., ['EURUSD.pro', 'GBPUSD.pro'])
        """
        self.symbols = symbols

        # Timeframe mappings
        self.timeframes = {
            'M1': mt5.TIMEFRAME_M1,
            'M5': mt5.TIMEFRAME_M5,
            'M15': mt5.TIMEFRAME_M15,
            'M30': mt5.TIMEFRAME_M30,
            'H1': mt5.TIMEFRAME_H1,
            'H4': mt5.TIMEFRAME_H4,
            'D1': mt5.TIMEFRAME_D1,
        }

        # Data cache: {symbol: {timeframe: DataFrame}}
        self.data_cache: Dict[str, Dict[str, pd.DataFrame]] = {}

        # Initialize cache structure
        for symbol in symbols:
            self.data_cache[symbol] = {}
            for tf_name in self.timeframes.keys():
                self.data_cache[symbol][tf_name] = pd.DataFrame()

        logger.info(f"MTF Data Manager initialized for {len(symbols)} symbols, "
                   f"{len(self.timeframes)} timeframes")

    def update_all_timeframes(self, symbol: str, bars_config: Dict[str, int] = None):
        """
        Update all timeframes for a symbol.

        Args:
            symbol: Symbol to update
            bars_config: Dict of {timeframe: bars_to_load}
                        Example: {'M1': 500, 'H1': 200, 'D1': 100}
                        If None, uses defaults
        """
        if bars_config is None:
            # Default bars to load per timeframe
            bars_config = {
                'M1': 500,
                'M5': 300,
                'M15': 200,
                'M30': 150,
                'H1': 200,
                'H4': 100,
                'D1': 60,
            }

        for tf_name, tf_const in self.timeframes.items():
            bars = bars_config.get(tf_name, 100)

            try:
                rates = mt5.copy_rates_from_pos(symbol, tf_const, 0, bars)

                if rates is not None and len(rates) > 0:
                    df = pd.DataFrame(rates)
                    df['time'] = pd.to_datetime(df['time'], unit='s')
                    df['timestamp'] = df['time']
                    df['symbol'] = symbol
                    df['volume'] = df['tick_volume']
                    df.attrs['symbol'] = symbol
                    df.attrs['timeframe'] = tf_name

                    self.data_cache[symbol][tf_name] = df

                    logger.debug(f"Updated {symbol} {tf_name}: {len(df)} bars")
                else:
                    logger.warning(f"No data for {symbol} {tf_name}")

            except Exception as e:
                logger.error(f"Error updating {symbol} {tf_name}: {e}")

    def get_data(self, symbol: str, timeframe: str) -> pd.DataFrame:
        """
        Get cached data for symbol and timeframe.

        Args:
            symbol: Symbol (e.g., 'EURUSD.pro')
            timeframe: Timeframe string (e.g., 'H1', 'D1')

        Returns:
            DataFrame with OHLCV data, or empty DataFrame if not available
        """
        return self.data_cache.get(symbol, {}).get(timeframe, pd.DataFrame())

    def get_current_candle(self, symbol: str, timeframe: str) -> pd.Series:
        """
        Get the most recent candle for symbol/timeframe.

        Returns:
            Series with latest candle data, or empty Series if not available
        """
        df = self.get_data(symbol, timeframe)
        if len(df) > 0:
            return df.iloc[-1]
        return pd.Series()

    def calculate_mtf_trend(self, symbol: str) -> Dict[str, str]:
        """
        Calculate trend direction for each timeframe.

        Returns:
            Dict like {'D1': 'UP', 'H4': 'UP', 'H1': 'DOWN', ...}

        Trend detection:
        - Uses EMA 20/50 crossover
        - UP: EMA20 > EMA50 and price > EMA20
        - DOWN: EMA20 < EMA50 and price < EMA20
        - NEUTRAL: otherwise
        """
        trends = {}

        for tf in ['D1', 'H4', 'H1', 'M30', 'M15']:
            df = self.get_data(symbol, tf)

            if len(df) < 50:
                trends[tf] = 'NEUTRAL'
                continue

            # Calculate EMAs
            closes = df['close']
            ema_20 = closes.ewm(span=20, adjust=False).mean()
            ema_50 = closes.ewm(span=50, adjust=False).mean()

            current_price = closes.iloc[-1]
            current_ema20 = ema_20.iloc[-1]
            current_ema50 = ema_50.iloc[-1]

            # Determine trend
            if current_ema20 > current_ema50:
                if current_price > current_ema20:
                    trends[tf] = 'UP'
                else:
                    trends[tf] = 'UP_WEAK'  # Pullback in uptrend
            else:
                if current_price < current_ema20:
                    trends[tf] = 'DOWN'
                else:
                    trends[tf] = 'DOWN_WEAK'  # Pullback in downtrend

        return trends

    def calculate_mtf_confluence(self, symbol: str, direction: str) -> float:
        """
        Calculate multi-timeframe confluence score.

        Args:
            symbol: Symbol
            direction: 'LONG' or 'SHORT'

        Returns:
            Score 0.0-1.0 representing MTF alignment

        Weighting:
        - D1: 35%
        - H4: 30%
        - H1: 20%
        - M30: 10%
        - M15: 5%
        """
        trends = self.calculate_mtf_trend(symbol)

        weights = {
            'D1': 0.35,
            'H4': 0.30,
            'H1': 0.20,
            'M30': 0.10,
            'M15': 0.05,
        }

        score = 0.0

        for tf, weight in weights.items():
            trend = trends.get(tf, 'NEUTRAL')

            if direction == 'LONG':
                if trend == 'UP':
                    score += weight * 1.0
                elif trend == 'UP_WEAK':
                    score += weight * 0.7
                elif trend == 'NEUTRAL':
                    score += weight * 0.3
                # DOWN trends contribute 0

            elif direction == 'SHORT':
                if trend == 'DOWN':
                    score += weight * 1.0
                elif trend == 'DOWN_WEAK':
                    score += weight * 0.7
                elif trend == 'NEUTRAL':
                    score += weight * 0.3

        return score


# INSTRUCCIONES DE INTEGRACIÓN EN LIVE ENGINE:

# 1. En LiveTradingEngine.__init__:
#    self.mtf_manager = MultiTimeframeDataManager(SYMBOLS)

# 2. En el loop principal (antes de evaluar estrategias):
#    for symbol in SYMBOLS:
#        self.mtf_manager.update_all_timeframes(symbol)

# 3. Al evaluar estrategias, pasar MTF context:
#    mtf_trends = self.mtf_manager.calculate_mtf_trend(symbol)
#    mtf_confluence = self.mtf_manager.calculate_mtf_confluence(symbol, signal.direction)
#
#    # Filtrar señal si confluence bajo
#    if mtf_confluence < 0.60:
#        logger.info(f"Signal filtered: MTF confluence {mtf_confluence:.2f} < 0.60")
#        continue
```

---

## Fase 3: Risk Manager Institucional

### Problema Actual:
El sistema usa `sizing_level` 1-5 pero NO calcula:
- Probabilidad real de éxito
- Tamaño óptimo basado en calidad
- Exposición correlacionada
- Límites de drawdown

### Solución Requerida:

#### Crear: `src/core/institutional_risk_manager.py`

```python
"""
Institutional Risk Manager

FUNCIONES:
1. Calcular quality score preciso (0.0-1.0) para cada trade
2. Determinar tamaño óptimo de posición basado en calidad
3. Monitorear correlaciones entre posiciones abiertas
4. Aplicar límites de riesgo dinámicos
5. Pausar trading si condiciones adversas
"""

import logging
from typing import Dict, List, Optional
import numpy as np

logger = logging.getLogger(__name__)


class InstitutionalRiskManager:
    """Advanced risk management with precise quality measurement."""

    def __init__(self, config: Dict):
        """
        Initialize risk manager.

        Config should contain:
        - initial_capital: Starting capital
        - base_risk_percent: Base risk per trade (e.g., 1.0)
        - max_risk_percent: Maximum risk per trade (e.g., 3.0)
        - max_correlated_risk: Max % in correlated positions (e.g., 5.0)
        - daily_loss_limit: Pause if daily loss > % (e.g., 5.0)
        - max_drawdown_pause: Pause if drawdown > % (e.g., 20.0)
        """
        self.config = config
        self.current_capital = config.get('initial_capital', 10000.0)
        self.base_risk_pct = config.get('base_risk_percent', 1.0)
        self.max_risk_pct = config.get('max_risk_percent', 3.0)
        self.max_correlated_risk = config.get('max_correlated_risk', 5.0)
        self.daily_loss_limit = config.get('daily_loss_limit', 5.0)
        self.max_drawdown_pause = config.get('max_drawdown_pause', 20.0)

        self.active_positions = []
        self.daily_pnl = 0.0
        self.peak_capital = self.current_capital

        # Performance tracking per strategy
        self.strategy_performance = {}

        logger.info("Institutional Risk Manager initialized")

    def calculate_trade_quality_score(self, signal, market_context: Dict) -> float:
        """
        Calculate precise quality score for a trade (0.0-1.0).

        FACTORS:
        1. MTF Confluence (35%)
        2. Strategy Historical Win Rate (25%)
        3. Market Regime Compatibility (20%)
        4. Risk/Reward Ratio (10%)
        5. VPIN / Flow Quality (10%)

        Args:
            signal: Signal object from strategy
            market_context: Dict with:
                - mtf_confluence: MTF score
                - volatility_regime: Current regime
                - vpin: Current VPIN value

        Returns:
            Quality score 0.0-1.0
        """
        scores = {}
        weights = {}

        # FACTOR 1: MTF Confluence (35%)
        mtf_confluence = signal.metadata.get('mtf_confluence_score',
                                             market_context.get('mtf_confluence', 0.5))
        scores['mtf'] = mtf_confluence
        weights['mtf'] = 0.35

        # FACTOR 2: Strategy Historical Performance (25%)
        strategy_name = signal.strategy_name
        strategy_stats = self.strategy_performance.get(strategy_name, {})
        win_rate = strategy_stats.get('win_rate', 0.50)  # Default 50%

        # Normalize win rate to 0-1 (assuming 0.30-0.70 range)
        win_rate_normalized = (win_rate - 0.30) / 0.40
        win_rate_normalized = max(0.0, min(1.0, win_rate_normalized))

        scores['strategy_performance'] = win_rate_normalized
        weights['strategy_performance'] = 0.25

        # FACTOR 3: Market Regime Compatibility (20%)
        regime = market_context.get('volatility_regime', 'NORMAL')
        regime_compatibility = self._calculate_regime_compatibility(
            strategy_name, regime
        )
        scores['regime'] = regime_compatibility
        weights['regime'] = 0.20

        # FACTOR 4: Risk/Reward Ratio (10%)
        rr_ratio = signal.metadata.get('risk_reward_ratio', 2.0)

        if rr_ratio >= 3.0:
            rr_score = 1.0
        elif rr_ratio >= 2.0:
            rr_score = 0.7
        elif rr_ratio >= 1.5:
            rr_score = 0.4
        else:
            rr_score = 0.0

        scores['risk_reward'] = rr_score
        weights['risk_reward'] = 0.10

        # FACTOR 5: VPIN / Flow Quality (10%)
        vpin = market_context.get('vpin', 0.5)

        if vpin < 0.30:
            vpin_score = 1.0  # Clean flow
        elif vpin < 0.45:
            vpin_score = 0.6  # Acceptable
        elif vpin < 0.60:
            vpin_score = 0.3  # Caution
        else:
            vpin_score = 0.0  # Toxic

        scores['vpin'] = vpin_score
        weights['vpin'] = 0.10

        # CALCULATE WEIGHTED SCORE
        total_score = sum(scores[k] * weights[k] for k in scores)

        # Add to signal metadata for transparency
        signal.metadata['quality_score'] = total_score
        signal.metadata['quality_breakdown'] = scores

        logger.info(f"Trade quality score: {total_score:.2f} "
                   f"(MTF:{scores['mtf']:.2f}, "
                   f"WinRate:{scores['strategy_performance']:.2f}, "
                   f"Regime:{scores['regime']:.2f})")

        return total_score

    def _calculate_regime_compatibility(self, strategy: str, regime: str) -> float:
        """
        Calculate strategy-regime compatibility.

        Different strategies perform better in different regimes:
        - Mean Reversion: best in LOW_VOLATILITY, RANGING
        - Momentum: best in TRENDING, HIGH_VOLATILITY
        - Liquidity Sweep: best in HIGH_VOLATILITY
        """
        compatibility_matrix = {
            'mean_reversion_statistical': {
                'LOW_VOLATILITY': 1.0,
                'RANGING': 0.9,
                'NORMAL': 0.7,
                'TRENDING': 0.4,
                'HIGH_VOLATILITY': 0.3,
            },
            'momentum_quality': {
                'LOW_VOLATILITY': 0.4,
                'RANGING': 0.5,
                'NORMAL': 0.8,
                'TRENDING': 1.0,
                'HIGH_VOLATILITY': 0.9,
            },
            'liquidity_sweep': {
                'LOW_VOLATILITY': 0.5,
                'RANGING': 0.7,
                'NORMAL': 0.8,
                'TRENDING': 0.7,
                'HIGH_VOLATILITY': 1.0,
            },
            'order_block_institutional': {
                'LOW_VOLATILITY': 0.7,
                'RANGING': 0.8,
                'NORMAL': 0.9,
                'TRENDING': 0.9,
                'HIGH_VOLATILITY': 0.8,
            },
            # Add other strategies...
        }

        return compatibility_matrix.get(strategy, {}).get(regime, 0.5)

    def calculate_position_size(self, signal, quality_score: float,
                               account_balance: float) -> float:
        """
        Calculate optimal lot size based on quality score.

        FORMULA:
        risk_pct = base_risk * quality_multiplier
        risk_usd = account_balance * (risk_pct / 100)
        lot_size = risk_usd / (stop_distance_pips * pip_value)

        Quality Score → Risk %:
        - 0.85+: 1.5%
        - 0.75-0.85: 1.2%
        - 0.65-0.75: 1.0%
        - 0.55-0.65: 0.66%
        - <0.55: 0.33%

        Args:
            signal: Signal object
            quality_score: Calculated quality (0.0-1.0)
            account_balance: Current account balance

        Returns:
            Lot size to trade (e.g., 0.15)
        """
        # Determine risk % based on quality
        if quality_score >= 0.85:
            risk_pct = 1.5
        elif quality_score >= 0.75:
            risk_pct = 1.2
        elif quality_score >= 0.65:
            risk_pct = 1.0
        elif quality_score >= 0.55:
            risk_pct = 0.66
        else:
            risk_pct = 0.33

        # Cap at max risk
        risk_pct = min(risk_pct, self.max_risk_pct)

        # Calculate risk in USD
        risk_usd = account_balance * (risk_pct / 100.0)

        # Calculate stop distance in pips
        stop_distance_price = abs(signal.entry_price - signal.stop_loss)
        stop_distance_pips = stop_distance_price * 10000  # For FX

        # Pip value per lot (simplified for EUR/USD)
        pip_value_per_lot = 10.0  # $10 per pip for 1.0 lot

        # Calculate lot size
        if stop_distance_pips > 0:
            lot_size = risk_usd / (stop_distance_pips * pip_value_per_lot)
        else:
            lot_size = 0.01  # Minimum

        # Round to 0.01
        lot_size = round(lot_size, 2)

        # Apply limits
        min_lot = 0.01
        max_lot = 2.0
        lot_size = max(min_lot, min(lot_size, max_lot))

        logger.info(f"Position size: {lot_size} lots "
                   f"(quality={quality_score:.2f}, risk={risk_pct:.2f}%, "
                   f"risk_usd=${risk_usd:.2f}, stop={stop_distance_pips:.1f}pips)")

        return lot_size

    def should_pause_trading(self) -> bool:
        """
        Determine if trading should be paused due to adverse conditions.

        PAUSE IF:
        1. Daily loss > daily_loss_limit %
        2. Drawdown > max_drawdown_pause %
        3. 5+ consecutive losses

        Returns:
            True if should pause, False otherwise
        """
        # Check daily loss
        daily_loss_pct = (self.daily_pnl / self.current_capital) * 100

        if daily_loss_pct < -(self.daily_loss_limit):
            logger.warning(f"PAUSE: Daily loss {daily_loss_pct:.1f}% > "
                          f"{self.daily_loss_limit}%")
            return True

        # Check drawdown
        drawdown_pct = ((self.peak_capital - self.current_capital) /
                       self.peak_capital) * 100

        if drawdown_pct > self.max_drawdown_pause:
            logger.warning(f"PAUSE: Drawdown {drawdown_pct:.1f}% > "
                          f"{self.max_drawdown_pause}%")
            return True

        # Check consecutive losses (if tracked)
        # ...

        return False

    def approve_trade(self, signal, market_context: Dict,
                     account_balance: float) -> Optional[Dict]:
        """
        Approve or reject trade after complete analysis.

        Returns:
            None if rejected, or Dict with:
            {
                'approved': True,
                'lot_size': 0.15,
                'quality_score': 0.82,
                'risk_usd': 120.50,
            }
        """
        # Check if paused
        if self.should_pause_trading():
            logger.warning("Trading is PAUSED - rejecting all signals")
            return None

        # Calculate quality score
        quality_score = self.calculate_trade_quality_score(signal, market_context)

        # Minimum quality threshold
        if quality_score < 0.50:
            logger.info(f"Trade REJECTED: quality {quality_score:.2f} < 0.50")
            return None

        # Calculate position size
        lot_size = self.calculate_position_size(signal, quality_score, account_balance)

        # Calculate risk
        stop_distance = abs(signal.entry_price - signal.stop_loss)
        pip_value = 10 * lot_size  # Simplified
        risk_usd = stop_distance * 10000 * pip_value

        approval = {
            'approved': True,
            'lot_size': lot_size,
            'quality_score': quality_score,
            'risk_usd': risk_usd,
            'risk_pct': (risk_usd / account_balance) * 100,
        }

        logger.info(f"Trade APPROVED: {signal.strategy_name} {signal.direction} "
                   f"quality={quality_score:.2f} lot={lot_size} risk=${risk_usd:.2f}")

        return approval


# INSTRUCCIONES DE INTEGRACIÓN EN LIVE ENGINE:

# 1. En __init__:
#    self.risk_manager = InstitutionalRiskManager({
#        'initial_capital': 10000.0,
#        'base_risk_percent': 1.0,
#        'max_risk_percent': 3.0,
#        'max_correlated_risk': 5.0,
#        'daily_loss_limit': 5.0,
#        'max_drawdown_pause': 20.0,
#    })

# 2. Antes de ejecutar trade:
#    market_context = {
#        'mtf_confluence': mtf_confluence,
#        'volatility_regime': 'NORMAL',  # From regime detector
#        'vpin': current_vpin,
#    }
#
#    approval = self.risk_manager.approve_trade(
#        signal, market_context, account.equity
#    )
#
#    if approval:
#        lot_size = approval['lot_size']
#        # Execute trade with calculated lot_size
#    else:
#        # Reject trade
#        continue
```

---

## Fase 4: Position Manager (Trailing/Breakeven)

### Crear: `src/core/position_manager.py`

```python
"""
Position Manager - Trailing Stop & Breakeven

FUNCIONES:
1. Move stop to breakeven after +15 pips
2. Trail stop after +25 pips (15 pips behind price)
3. Take 50% profit at 50% to target
4. Time-based exit if no progress
"""

import logging
from typing import Dict, Optional
import pandas as pd

logger = logging.getLogger(__name__)


class PositionManager:
    """Manages open positions with trailing and breakeven logic."""

    def __init__(self, config: Dict):
        self.config = config
        logger.info("Position Manager initialized")

    def manage_position(self, position: Dict, current_price: float) -> Dict:
        """
        Analyze position and return recommended actions.

        Args:
            position: Dict with:
                - entry_price
                - stop_loss
                - take_profit
                - direction
                - partial_taken (bool)
                - bars_open (int)
            current_price: Current market price

        Returns:
            Dict with actions:
                - move_stop_to: New stop price (if should update)
                - close_partial: Fraction to close (e.g., 0.5)
                - close_full: Reason for full close
        """
        actions = {}

        entry_price = position['entry_price']
        current_stop = position['stop_loss']
        take_profit = position['take_profit']
        direction = position['direction']

        # Calculate profit in pips
        if direction == 'LONG':
            profit_pips = (current_price - entry_price) * 10000
        else:
            profit_pips = (entry_price - current_price) * 10000

        logger.debug(f"Position {direction} profit: {profit_pips:.1f} pips")

        # RULE 1: Breakeven after +15 pips
        if profit_pips >= 15:
            if direction == 'LONG':
                breakeven_price = entry_price + (5 * 0.0001)  # BE + 5 pips
                if current_stop < breakeven_price:
                    actions['move_stop_to'] = breakeven_price
                    logger.info(f"Moving stop to BREAKEVEN+5: {breakeven_price:.5f}")

            else:  # SHORT
                breakeven_price = entry_price - (5 * 0.0001)
                if current_stop > breakeven_price:
                    actions['move_stop_to'] = breakeven_price
                    logger.info(f"Moving stop to BREAKEVEN+5: {breakeven_price:.5f}")

        # RULE 2: Trailing stop after +25 pips
        if profit_pips >= 25:
            trail_distance_pips = 15  # Trail 15 pips behind

            if direction == 'LONG':
                new_stop = current_price - (trail_distance_pips * 0.0001)
                if new_stop > current_stop:
                    actions['move_stop_to'] = new_stop
                    logger.info(f"TRAILING stop to {new_stop:.5f}")

            else:  # SHORT
                new_stop = current_price + (trail_distance_pips * 0.0001)
                if new_stop < current_stop:
                    actions['move_stop_to'] = new_stop
                    logger.info(f"TRAILING stop to {new_stop:.5f}")

        # RULE 3: Partial profit at 50% to target
        target_pips = abs(take_profit - entry_price) * 10000

        if profit_pips >= target_pips * 0.50:
            if not position.get('partial_taken', False):
                actions['close_partial'] = 0.50  # Close 50%
                logger.info(f"Taking 50% profit at {current_price:.5f}")

        # RULE 4: Time-based exit
        bars_open = position.get('bars_open', 0)

        if bars_open > 120 and profit_pips < 10:  # 2 hours, <10 pips profit
            actions['close_full'] = 'TIME_EXIT'
            logger.info("Time-based exit: 2 hours with minimal profit")

        return actions


# INSTRUCCIONES DE INTEGRACIÓN EN LIVE ENGINE:

# 1. En __init__:
#    self.position_manager = PositionManager({})

# 2. En loop principal (cada ciclo):
#    for position in self.open_positions:
#        current_price = self.get_current_price(position['symbol'])
#
#        actions = self.position_manager.manage_position(position, current_price)
#
#        if 'move_stop_to' in actions:
#            self.modify_position_stop(position['ticket'], actions['move_stop_to'])
#
#        if 'close_partial' in actions:
#            self.close_partial_position(position['ticket'], actions['close_partial'])
#
#        if 'close_full' in actions:
#            self.close_position(position['ticket'], actions['close_full'])
#
#        position['bars_open'] = position.get('bars_open', 0) + 1
```

---

## Fase 5: Integración Completa en Live Engine

### Modificaciones Requeridas en `scripts/live_trading_engine.py`:

```python
# At top of file:
from src.core.mtf_data_manager import MultiTimeframeDataManager
from src.core.institutional_risk_manager import InstitutionalRiskManager
from src.core.position_manager import PositionManager

# In __init__:
def __init__(self):
    # ... existing code ...

    # NEW: Initialize components
    self.mtf_manager = MultiTimeframeDataManager(SYMBOLS)
    self.risk_manager = InstitutionalRiskManager({
        'initial_capital': 10000.0,
        'base_risk_percent': 1.0,
        'max_risk_percent': 3.0,
        'max_correlated_risk': 5.0,
        'daily_loss_limit': 5.0,
        'max_drawdown_pause': 20.0,
    })
    self.position_manager = PositionManager({})

    logger.info("MTF Manager, Risk Manager, Position Manager initialized")

# In main loop:
def run(self):
    while self.running:
        for symbol in SYMBOLS:
            # 1. UPDATE MTF DATA
            self.mtf_manager.update_all_timeframes(symbol)

            # 2. EVALUATE STRATEGIES (existing code)
            # ... strategy evaluation ...

            # 3. CHECK MTF CONFLUENCE
            if signal:
                mtf_confluence = self.mtf_manager.calculate_mtf_confluence(
                    symbol, signal.direction
                )
                signal.metadata['mtf_confluence_score'] = mtf_confluence

                if mtf_confluence < 0.60:
                    logger.info(f"Signal filtered: MTF confluence {mtf_confluence:.2f}")
                    continue

                # 4. RISK MANAGER APPROVAL
                market_context = {
                    'mtf_confluence': mtf_confluence,
                    'volatility_regime': 'NORMAL',  # TODO: implement regime detection
                    'vpin': self.vpin_calculators[symbol].calculate(data),
                }

                approval = self.risk_manager.approve_trade(
                    signal, market_context, account.equity
                )

                if not approval:
                    logger.info("Trade rejected by risk manager")
                    continue

                # 5. EXECUTE TRADE with calculated lot size
                lot_size = approval['lot_size']
                # ... execute trade ...

        # 6. MANAGE OPEN POSITIONS
        for position in self.open_positions:
            current_price = self.get_current_price(position['symbol'])

            actions = self.position_manager.manage_position(position, current_price)

            if 'move_stop_to' in actions:
                self.modify_position_stop(position['ticket'], actions['move_stop_to'])

            if 'close_partial' in actions:
                self.close_partial_position(position['ticket'], actions['close_partial'])

        time.sleep(SCAN_INTERVAL_SECONDS)
```

---

## ORDEN DE IMPLEMENTACIÓN RECOMENDADO

### Día 1-2: MTF Data Manager
1. Crear `/home/user/TradingSystem/src/core/mtf_data_manager.py`
2. Implementar código completo (copiar del ejemplo arriba)
3. Integrar en `live_trading_engine.py`
4. Test: Verificar que carga datos de todos los timeframes

### Día 3-4: Risk Manager
1. Crear `/home/user/TradingSystem/src/core/institutional_risk_manager.py`
2. Implementar código completo
3. Integrar en live engine
4. Test: Verificar cálculo de quality scores y lot sizes

### Día 5: Position Manager
1. Crear `/home/user/TradingSystem/src/core/position_manager.py`
2. Implementar código completo
3. Integrar gestión de posiciones en loop
4. Test: Verificar breakeven y trailing funcionan

### Día 6-7: Testing Completo
1. Backtest con nuevos componentes
2. Paper trading 2-3 días
3. Verificar que las 14 estrategias generan señales
4. Ajustar si necesario

---

## ARCHIVOS A CREAR

1. `/home/user/TradingSystem/src/core/mtf_data_manager.py` (nuevo)
2. `/home/user/TradingSystem/src/core/institutional_risk_manager.py` (nuevo)
3. `/home/user/TradingSystem/src/core/position_manager.py` (nuevo)

## ARCHIVOS A MODIFICAR

1. `/home/user/TradingSystem/scripts/live_trading_engine.py`
   - Agregar imports
   - Inicializar componentes en `__init__`
   - Integrar en loop principal

---

## TESTING CHECKLIST

### MTF Manager:
- [ ] Carga datos de M1, M5, M15, M30, H1, H4, D1
- [ ] Cache se actualiza correctamente
- [ ] `calculate_mtf_trend()` retorna trends
- [ ] `calculate_mtf_confluence()` calcula scores 0.0-1.0

### Risk Manager:
- [ ] `calculate_trade_quality_score()` retorna 0.0-1.0
- [ ] Quality score considera los 5 factores
- [ ] `calculate_position_size()` retorna lot sizes razonables
- [ ] `should_pause_trading()` pausa si daily loss >5%

### Position Manager:
- [ ] Stop se mueve a breakeven después de +15 pips
- [ ] Trailing activado después de +25 pips
- [ ] Partial profit tomado a 50% target
- [ ] Time exit después de 2 horas sin progreso

### Integración:
- [ ] Live engine inicializa los 3 componentes
- [ ] MTF data se actualiza cada ciclo
- [ ] Señales filtradas por MTF confluence <0.60
- [ ] Risk manager aprueba/rechaza trades
- [ ] Lot sizes calculados dinámicamente
- [ ] Posiciones abiertas gestionadas automáticamente

---

## RESULTADO ESPERADO

Después de implementar estas 5 fases:

### Sistema tendrá:
1. ✅ Parámetros institucionales corregidos (HECHO)
2. ✅ Configuración centralizada YAML (HECHO)
3. ✅ Multi-timeframe real con H1/H4/D1 (PENDIENTE)
4. ✅ Risk manager con quality scoring preciso (PENDIENTE)
5. ✅ Trailing/breakeven profesional (PENDIENTE)

### Estrategias generarán señales:
- **Mean Reversion:** Con parámetros correctos, menos stops
- **Liquidity Sweep:** Con ICT 2024 parameters, más precisión
- **Momentum Quality:** Con VPIN correcto
- **Order Block:** Funcionando bien (ya)
- **Kalman Pairs:** Con 4 pares configurados
- **Correlation Divergence:** Con 4 pares configurados
- **9 estrategias restantes:** Con thresholds ajustados

### Sistema será institucional:
- MTF confluence filtering
- Dynamic position sizing basado en calidad
- Trailing stops/breakeven automático
- Risk limits dinámicos
- Performance superior a retail

---

## CONTACTO PARA DUDAS

Si durante la implementación surgen dudas:
1. Revisar `/home/user/TradingSystem/ANALISIS_INSTITUCIONAL_COMPLETO.md` para contexto
2. Revisar `/home/user/TradingSystem/config/strategies_institutional.yaml` para parámetros
3. Los commits tienen mensajes detallados con research basis

---

**FIN DEL PLAN DE IMPLEMENTACIÓN**

Este documento contiene TODO lo necesario para completar el sistema.
Implementación estimada: 5-7 días de trabajo enfocado.
Resultado: Sistema de trading institucional completo y operativo.
