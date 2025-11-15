# MANDATO 24 - UNIFIED TRADING LOOP: Technical Design

**Date**: 2025-11-15
**Branch**: claude/mandato24-full-loop-integration-01AqipubodvYuyNtfLsBZpsx
**Status**: DESIGN SPECIFICATION
**Classification**: ARCHITECTURAL FOUNDATION

---

## EXECUTIVE SUMMARY

Este documento especifica el diseño técnico del **Unified Institutional Trading Loop** que reemplazará los 4 entry points fragmentados actuales.

**Objetivo**: UN loop unificado que funcione en modos RESEARCH/PAPER/LIVE con:
- Feature pipeline completo (OFI, CVD, VPIN, L2)
- Brain filtering integrado
- ExecutionAdapter mode-aware
- KillSwitch enforcement en LIVE
- NON-NEGOTIABLES garantizados

---

## BLOQUE 1: LOOP STRUCTURE - Pseudocódigo

```python
class InstitutionalTradingSystem:
    """
    Sistema de trading institucional unificado.

    Soporta 3 modos de ejecución:
    - RESEARCH: Backtest solamente (sin ejecución real)
    - PAPER: Trading simulado (PaperExecutionAdapter)
    - LIVE: Trading REAL (LiveExecutionAdapter + KillSwitch)
    """

    def __init__(self, execution_mode: ExecutionMode, config_path: str):
        # 1. Validar execution mode
        self.execution_mode = execution_mode

        # 2. Cargar configuraciones
        self.config = self._load_configs(execution_mode)

        # 3. Inicializar componentes core
        self._initialize_core_components()

        # 4. Inicializar sistema de ejecución (mode-specific)
        self._initialize_execution_system(execution_mode)

        # 5. Inicializar feature pipeline
        self._initialize_feature_pipeline()

    def run_unified_loop(self):
        """
        Loop unificado para PAPER y LIVE modes.

        Flow:
        1. MTF Update
        2. Feature Calculation (OFI, CVD, VPIN, L2)
        3. Regime Detection
        4. Signal Generation (via StrategyOrchestrator)
        5. Brain Filtering
        6. Execution (mode-aware)
        7. Reporting
        8. Calibration Hooks (ML Supervisor)
        """

        self.is_running = True
        iteration = 0

        while self.is_running:
            try:
                iteration += 1
                logger.debug(f"Loop iteration {iteration}")

                # === STEP 1: MTF UPDATE ===
                self.mtf_manager.update()
                current_data = self.mtf_manager.get_current_data()

                if not current_data or not self._validate_market_data(current_data):
                    logger.warning("Invalid market data, skipping iteration")
                    time.sleep(self.update_interval)
                    continue

                # === STEP 2: FEATURE CALCULATION ===
                # CRITICAL: Calcula OFI, CVD, VPIN, L2 para CADA símbolo
                features_by_symbol = self._calculate_all_features(current_data)

                # === STEP 3: REGIME DETECTION ===
                current_regime = self.regime_detector.detect_regime(current_data)
                logger.debug(f"Current regime: {current_regime}")

                # === STEP 4: SIGNAL GENERATION ===
                # CRITICAL: Pasa features a estrategias
                raw_signals = self.strategy_orchestrator.generate_signals(
                    market_data=current_data,
                    current_regime=current_regime,
                    features=features_by_symbol
                )

                logger.info(f"Generated {len(raw_signals)} raw signals")

                # === STEP 5: BRAIN FILTERING ===
                # Brain valida, filtra, ajusta sizing
                filtered_signals = self.brain.filter_signals(
                    signals=raw_signals,
                    market_data=current_data,
                    current_regime=current_regime
                )

                logger.info(f"Brain filtered to {len(filtered_signals)} signals")

                # === STEP 6: EXECUTION (MODE-AWARE) ===
                if self.execution_mode == ExecutionMode.LIVE:
                    # LIVE: Check Kill Switch ANTES de ejecutar
                    if not self.kill_switch.can_send_orders():
                        logger.critical(
                            f"⚠️  KILL SWITCH BLOCKING ORDERS: {self.kill_switch.get_state().value}"
                        )
                        # NO ejecutar, pero continuar loop
                        time.sleep(self.update_interval)
                        continue

                # Ejecutar señales (PAPER o LIVE)
                executed_trades = self._execute_signals(filtered_signals)

                logger.info(f"Executed {len(executed_trades)} trades")

                # === STEP 7: REPORTING ===
                self._update_reports(executed_trades, current_data)

                # === STEP 8: CALIBRATION HOOKS (ML Supervisor) ===
                self.ml_supervisor.on_iteration_complete(
                    signals=filtered_signals,
                    executed_trades=executed_trades,
                    market_data=current_data
                )

                # Sleep hasta próximo update
                time.sleep(self.update_interval)

            except KeyboardInterrupt:
                logger.info("\n⚠️  Shutdown requested by user")
                self.shutdown()
                break

            except Exception as e:
                logger.error(f"Error in trading loop: {e}")
                import traceback
                traceback.print_exc()

                # En LIVE, errores críticos activan kill switch
                if self.execution_mode == ExecutionMode.LIVE:
                    logger.critical("⚠️  Activating kill switch due to error")
                    self.kill_switch.emergency_stop("Loop error")

                time.sleep(5)  # Backoff before retry
```

---

## BLOQUE 2: COMPONENTE - MicrostructureEngine

### 2.1 Propósito

**MicrostructureEngine** centraliza el cálculo de TODAS las features de microestructura:
- OFI (Order Flow Imbalance)
- CVD (Cumulative Volume Delta)
- VPIN (Volume-Synchronized Probability of Informed Trading)
- L2 snapshot (Level 2 orderbook)
- Imbalance (bid/ask volume imbalance)

### 2.2 Interfaz

```python
# src/microstructure/engine.py

from typing import Dict, Optional
import pandas as pd
from dataclasses import dataclass
from collections import deque

from src.features.order_flow import (
    VPINCalculator,
    calculate_ofi,
    calculate_signed_volume
)
from src.features.orderbook_l2 import (
    OrderBookSnapshot,
    parse_l2_snapshot
)


@dataclass
class MicrostructureFeatures:
    """
    Container para features de microestructura de un símbolo.
    """
    ofi: float = 0.0                        # Order Flow Imbalance
    cvd: float = 0.0                        # Cumulative Volume Delta
    vpin: float = 0.5                       # VPIN (0-1)
    atr: float = 0.0001                     # ATR (para referencia, NO sizing)
    l2_snapshot: Optional[OrderBookSnapshot] = None  # Level 2 snapshot
    imbalance: float = 0.0                  # Bid/Ask imbalance (-1 a 1)
    spread: float = 0.0                     # Spread en pips
    microprice: float = 0.0                 # Volume-weighted mid price


class MicrostructureEngine:
    """
    Motor centralizado de cálculo de features de microestructura.

    Responsibilities:
    - Calcular OFI, CVD, VPIN para cada símbolo
    - Parsear L2 orderbook (si disponible)
    - Mantener estado (VPIN buckets, CVD acumulado)
    - Proveer features a estrategias

    Usage:
        engine = MicrostructureEngine(config)
        features = engine.calculate_features(symbol, market_data, l2_data)
    """

    def __init__(self, config: Dict):
        """
        Inicializa engine.

        Args:
            config: System config dict
        """
        self.config = config

        # VPIN calculators (uno por símbolo)
        self.vpin_calculators: Dict[str, VPINCalculator] = {}

        # CVD accumulators (running sum por símbolo)
        self.cvd_accumulators: Dict[str, float] = {}

        # OFI lookback window (default 20 bars)
        self.ofi_lookback = config.get('features', {}).get('ofi_lookback', 20)

        # VPIN config
        vpin_config = config.get('features', {}).get('vpin', {})
        self.vpin_bucket_size = vpin_config.get('bucket_size', 50000)
        self.vpin_num_buckets = vpin_config.get('num_buckets', 50)

        logger.info(f"MicrostructureEngine initialized (OFI lookback={self.ofi_lookback}, "
                   f"VPIN buckets={self.vpin_num_buckets})")

    def calculate_features(
        self,
        symbol: str,
        market_data: pd.DataFrame,
        l2_data: Optional[any] = None
    ) -> MicrostructureFeatures:
        """
        Calcula TODAS las features de microestructura para un símbolo.

        Args:
            symbol: Symbol to calculate features for
            market_data: OHLCV DataFrame (debe tener al menos ofi_lookback rows)
            l2_data: Level 2 orderbook data (optional, from MT5's market_book_get)

        Returns:
            MicrostructureFeatures con todas las features calculadas
        """
        features = MicrostructureFeatures()

        # Validar data
        if market_data is None or market_data.empty:
            logger.warning(f"{symbol}: No market data, returning defaults")
            return features

        if len(market_data) < 2:
            logger.debug(f"{symbol}: Insufficient data ({len(market_data)} bars)")
            return features

        # === OFI (Order Flow Imbalance) ===
        features.ofi = self._calculate_ofi(symbol, market_data)

        # === CVD (Cumulative Volume Delta) ===
        features.cvd = self._calculate_cvd(symbol, market_data)

        # === VPIN ===
        features.vpin = self._calculate_vpin(symbol, market_data)

        # === ATR (para referencia solamente, NO sizing) ===
        features.atr = self._calculate_atr(market_data)

        # === L2 Snapshot (si disponible) ===
        if l2_data is not None:
            l2_snapshot = parse_l2_snapshot(l2_data)
            if l2_snapshot:
                features.l2_snapshot = l2_snapshot
                features.imbalance = l2_snapshot.imbalance
                features.spread = l2_snapshot.spread
                features.microprice = l2_snapshot.mid_price  # Could calculate volume-weighted

        return features

    def _calculate_ofi(self, symbol: str, market_data: pd.DataFrame) -> float:
        """Calcula Order Flow Imbalance."""
        try:
            # Get lookback window
            lookback_data = market_data.tail(self.ofi_lookback)

            if len(lookback_data) < 2:
                return 0.0

            # Calculate OFI
            ofi = calculate_ofi(
                lookback_data['close'],
                lookback_data['volume']
            )

            return ofi

        except Exception as e:
            logger.debug(f"{symbol}: OFI calculation error: {e}")
            return 0.0

    def _calculate_cvd(self, symbol: str, market_data: pd.DataFrame) -> float:
        """
        Calcula Cumulative Volume Delta.

        Mantiene running sum en self.cvd_accumulators.
        """
        try:
            # Initialize accumulator if first time
            if symbol not in self.cvd_accumulators:
                self.cvd_accumulators[symbol] = 0.0

            # Get latest bar
            latest_bar = market_data.iloc[-1]

            # Get previous close (for signed volume)
            if len(market_data) >= 2:
                prev_close = market_data.iloc[-2]['close']
            else:
                prev_close = latest_bar['close']

            # Calculate signed volume
            signed_vol = calculate_signed_volume(
                latest_bar['close'],
                prev_close,
                latest_bar['volume']
            )

            # Accumulate
            self.cvd_accumulators[symbol] += signed_vol

            return self.cvd_accumulators[symbol]

        except Exception as e:
            logger.debug(f"{symbol}: CVD calculation error: {e}")
            return self.cvd_accumulators.get(symbol, 0.0)

    def _calculate_vpin(self, symbol: str, market_data: pd.DataFrame) -> float:
        """
        Calcula VPIN (Volume-Synchronized Probability of Informed Trading).

        Usa bucket-based accumulation via VPINCalculator.
        """
        try:
            # Initialize VPIN calculator if first time
            if symbol not in self.vpin_calculators:
                self.vpin_calculators[symbol] = VPINCalculator(
                    bucket_size=self.vpin_bucket_size,
                    num_buckets=self.vpin_num_buckets
                )

            calculator = self.vpin_calculators[symbol]

            # Get latest bar
            latest_bar = market_data.iloc[-1]

            # Get previous close
            if len(market_data) >= 2:
                prev_close = market_data.iloc[-2]['close']
            else:
                return 0.5  # Neutral default

            # Calculate trade direction
            signed_vol = calculate_signed_volume(
                latest_bar['close'],
                prev_close,
                latest_bar['volume']
            )

            trade_direction = 1 if signed_vol > 0 else -1 if signed_vol < 0 else 0

            # Add trade to VPIN calculator
            vpin_value = calculator.add_trade(
                latest_bar['volume'],
                trade_direction
            )

            # Return latest VPIN (or 0.5 if bucket not filled yet)
            return vpin_value if vpin_value is not None else 0.5

        except Exception as e:
            logger.debug(f"{symbol}: VPIN calculation error: {e}")
            return 0.5

    def _calculate_atr(self, market_data: pd.DataFrame, period: int = 14) -> float:
        """
        Calcula ATR (Average True Range).

        NOTA: Solo para referencia. NO se usa para position sizing (NON-NEGOTIABLE).
        """
        try:
            if len(market_data) < period:
                return 0.0001  # Default pequeño

            # Calculate True Range
            high = market_data['high']
            low = market_data['low']
            close_prev = market_data['close'].shift(1)

            tr1 = high - low
            tr2 = abs(high - close_prev)
            tr3 = abs(low - close_prev)

            tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)

            # ATR = SMA(TR, period)
            atr = tr.rolling(window=period).mean().iloc[-1]

            return atr if not pd.isna(atr) else 0.0001

        except Exception as e:
            logger.debug(f"ATR calculation error: {e}")
            return 0.0001

    def get_features_dict(self, features: MicrostructureFeatures) -> Dict:
        """
        Convierte MicrostructureFeatures a dict para pasar a estrategias.

        Returns:
            Dict con keys: ofi, cvd, vpin, atr, l2_snapshot, imbalance, spread
        """
        return {
            'ofi': features.ofi,
            'cvd': features.cvd,
            'vpin': features.vpin,
            'atr': features.atr,
            'l2_snapshot': features.l2_snapshot,
            'imbalance': features.imbalance,
            'spread': features.spread,
            'microprice': features.microprice
        }

    def reset_symbol(self, symbol: str):
        """
        Reset state para un símbolo (útil para testing).

        Args:
            symbol: Symbol to reset
        """
        if symbol in self.vpin_calculators:
            del self.vpin_calculators[symbol]

        if symbol in self.cvd_accumulators:
            del self.cvd_accumulators[symbol]

        logger.debug(f"Reset microstructure state for {symbol}")
```

### 2.3 Integración en Loop

```python
# En InstitutionalTradingSystem.__init__()

def _initialize_feature_pipeline(self):
    """Inicializa feature pipeline."""
    self.microstructure_engine = MicrostructureEngine(self.config)
    logger.info("✓ MicrostructureEngine initialized")


# En run_unified_loop()

def _calculate_all_features(self, current_data: Dict[str, pd.DataFrame]) -> Dict[str, Dict]:
    """
    Calcula features para TODOS los símbolos.

    Args:
        current_data: Dict[symbol, DataFrame]

    Returns:
        Dict[symbol, Dict[feature_name, value]]
    """
    features_by_symbol = {}

    for symbol, df in current_data.items():
        # Get L2 data if available (via MT5)
        l2_data = None
        if self.execution_mode == ExecutionMode.LIVE:
            # En LIVE, intentar obtener L2 data de MT5
            try:
                import MetaTrader5 as mt5
                l2_data = mt5.market_book_get(symbol)
            except:
                pass  # L2 no disponible

        # Calculate features
        features = self.microstructure_engine.calculate_features(
            symbol=symbol,
            market_data=df,
            l2_data=l2_data
        )

        # Convert to dict
        features_by_symbol[symbol] = self.microstructure_engine.get_features_dict(features)

    return features_by_symbol
```

---

## BLOQUE 3: COMPONENTE - StrategyOrchestrator.generate_signals()

### 3.1 Propósito

Implementar el método `generate_signals()` que:
1. Filtra estrategias activas por régimen
2. Pasa features a cada estrategia
3. Recolecta señales de todas las estrategias
4. Retorna lista unificada de señales

### 3.2 Implementación

```python
# src/strategy_orchestrator.py

def generate_signals(
    self,
    market_data: Dict[str, pd.DataFrame],
    current_regime: str,
    features: Dict[str, Dict]
) -> List[Signal]:
    """
    Genera señales de TODAS las estrategias activas.

    Args:
        market_data: Dict[symbol, DataFrame] con datos de mercado
        current_regime: Régimen actual ('trending', 'ranging', 'volatile', 'quiet')
        features: Dict[symbol, Dict[feature_name, value]] con features pre-calculadas

    Returns:
        Lista de señales de todas las estrategias

    Example:
        features = {
            'EURUSD': {
                'ofi': 0.35,
                'cvd': 1234.5,
                'vpin': 0.78,
                'l2_snapshot': <OrderBookSnapshot>,
                'imbalance': 0.25
            }
        }

        signals = orchestrator.generate_signals(market_data, 'trending', features)
    """
    all_signals = []

    # Filtrar estrategias activas por régimen
    active_strategies = self._get_strategies_for_regime(current_regime)

    logger.debug(f"{len(active_strategies)} strategies active for regime '{current_regime}'")

    # Generar señales de cada estrategia
    for strategy in active_strategies:
        try:
            # Get primary symbol for strategy
            primary_symbol = getattr(strategy, 'symbol', 'EURUSD')

            # Get market data for symbol
            strategy_data = market_data.get(primary_symbol)

            if strategy_data is None or strategy_data.empty:
                logger.debug(f"No data for {primary_symbol}, skipping {strategy.__class__.__name__}")
                continue

            # Get features for symbol
            strategy_features = features.get(primary_symbol, {})

            # CRITICAL: Pass features to strategy
            signals = strategy.evaluate(strategy_data, strategy_features)

            # Add strategy name to signals
            for signal in signals:
                signal.metadata = signal.metadata or {}
                signal.metadata['strategy'] = strategy.__class__.__name__
                signal.metadata['regime'] = current_regime

            all_signals.extend(signals)

            if signals:
                logger.debug(f"{strategy.__class__.__name__} generated {len(signals)} signals")

        except Exception as e:
            logger.error(f"Error in {strategy.__class__.__name__}: {e}")
            import traceback
            traceback.print_exc()
            continue

    return all_signals


def _get_strategies_for_regime(self, regime: str) -> List:
    """
    Filtra estrategias activas para el régimen actual.

    Args:
        regime: Current market regime

    Returns:
        Lista de estrategias activas
    """
    # Si APR (Active Portfolio Rebalancing) está habilitado, usar sus pesos
    if self.apr and hasattr(self.apr, 'get_active_strategies'):
        return self.apr.get_active_strategies(regime)

    # Si no, usar todas las estrategias (filtradas por config si es necesario)
    active = []

    for strategy in self.strategies:
        # Check si estrategia tiene preferencia de régimen
        if hasattr(strategy, 'preferred_regimes'):
            if regime in strategy.preferred_regimes:
                active.append(strategy)
        else:
            # Si no especifica preferencia, siempre activa
            active.append(strategy)

    return active
```

---

## BLOQUE 4: EXECUTION FLOW - Mode-Aware

### 4.1 RESEARCH Mode (Backtest)

```python
def run_backtest(self, start_date, end_date, capital):
    """
    Run backtest (RESEARCH mode).

    Usa BacktestEngine existente (ya tiene feature calculation).
    """
    if self.execution_mode != ExecutionMode.RESEARCH:
        raise ValueError("Backtest requires RESEARCH mode")

    # Use existing BacktestEngine
    from src.backtesting.backtest_engine import BacktestEngine

    backtest_engine = BacktestEngine(
        config=self.config,
        strategies=self.strategy_orchestrator.strategies,
        initial_capital=capital
    )

    # Load historical data
    historical_data = self._load_historical_data(start_date, end_date)

    # Run backtest (BacktestEngine ALREADY calculates features)
    results = backtest_engine.run_backtest(
        historical_data,
        start_date,
        end_date,
        regime_detector=self.regime_detector
    )

    # Generate report
    self.reporting.generate_backtest_report(results)

    return results
```

### 4.2 PAPER Mode

```python
def run_paper_trading(self):
    """
    Run PAPER mode (simulated execution).

    Uses PaperExecutionAdapter for fills.
    """
    if self.execution_mode != ExecutionMode.PAPER:
        raise ValueError("Paper trading requires PAPER mode")

    logger.warning("⚠️  PAPER MODE: All execution is SIMULATED")

    # Run unified loop
    self.run_unified_loop()
```

### 4.3 LIVE Mode

```python
def run_live_trading(self):
    """
    Run LIVE mode (REAL execution).

    Uses LiveExecutionAdapter + KillSwitch.
    Requires triple confirmation.
    """
    if self.execution_mode != ExecutionMode.LIVE:
        raise ValueError("Live trading requires LIVE mode")

    # Triple confirmation
    logger.critical("⚠️⚠️⚠️  LIVE TRADING MODE - REAL MONEY AT RISK  ⚠️⚠️⚠️")
    logger.critical(f"Kill Switch State: {self.kill_switch.get_state().value}")

    confirm1 = input("Type 'YES' to confirm live trading: ")
    if confirm1 != 'YES':
        logger.info("Live trading cancelled")
        return

    confirm2 = input("Type 'CONFIRM' to proceed with REAL money: ")
    if confirm2 != 'CONFIRM':
        logger.info("Live trading cancelled")
        return

    confirm3 = input("Final confirmation - Type 'LIVE' to start: ")
    if confirm3 != 'LIVE':
        logger.info("Live trading cancelled")
        return

    logger.critical("✅ Live trading confirmed - Starting...")

    # Run unified loop (with KillSwitch checks)
    self.run_unified_loop()
```

---

## BLOQUE 5: KILL SWITCH INTEGRATION

### 5.1 Check en Loop

```python
# En run_unified_loop(), antes de execution

if self.execution_mode == ExecutionMode.LIVE:
    # Check Kill Switch
    if not self.kill_switch.can_send_orders():
        status = self.kill_switch.get_status()

        logger.critical("=" * 80)
        logger.critical("⚠️  KILL SWITCH BLOCKING ORDERS")
        logger.critical(f"State: {status.state.value}")
        logger.critical(f"Reason: {status.reason}")
        logger.critical(f"Failed Layers: {status.failed_layers}")
        logger.critical("=" * 80)

        # NO ejecutar, pero continuar loop (puede resolverse)
        time.sleep(self.update_interval)
        continue
```

### 5.2 Emergency Stop on Error

```python
except Exception as e:
    logger.error(f"Error in trading loop: {e}")
    import traceback
    traceback.print_exc()

    # En LIVE, errores críticos activan kill switch
    if self.execution_mode == ExecutionMode.LIVE:
        logger.critical("⚠️  Activating kill switch due to loop error")
        self.kill_switch.emergency_stop(f"Loop error: {e}")

        # Opcionalmente, salir del loop
        # self.shutdown()
        # break

    time.sleep(5)  # Backoff before retry
```

---

## BLOQUE 6: NON-NEGOTIABLES ENFORCEMENT

### 6.1 Risk 0-2% Per Trade

**Enforcement point**: `RiskManager.calculate_position_size()`

```python
# El loop NUNCA calcula position size directamente
# SIEMPRE usa RiskManager

position_size = self.risk_manager.calculate_position_size(
    signal=signal,
    capital=current_capital,
    max_risk_pct=0.02  # NON-NEGOTIABLE: 0-2%
)
```

**Garantía**: RiskManager está integrado en loop → NON-NEGOTIABLE enforced.

### 6.2 NO ATR for Sizing

**Enforcement point**: `RiskManager` NO usa ATR

```python
# ATR solo se calcula para features (estrategias pueden usarlo para detección)
# Pero RiskManager usa FIXED percentage risk (0-2%)

# features['atr'] = 0.0001  # Calculado pero NO usado para sizing
```

**Garantía**: ATR en features, pero RiskManager lo ignora.

### 6.3 Brain Sin Violar Caps

**Enforcement point**: `InstitutionalBrain.filter_signals()`

```python
# En run_unified_loop()

filtered_signals = self.brain.filter_signals(
    signals=raw_signals,
    market_data=current_data,
    current_regime=current_regime
)

# Brain puede:
# - Rechazar señales (portfolio correlation, max positions, etc.)
# - Reducir sizing (pero NUNCA exceder RiskManager caps)
# - Ajustar SL/TP

# Pero NO puede violar caps de RiskManager
```

**Garantía**: Brain filtra/ajusta DESPUÉS de RiskManager, pero respeta caps.

### 6.4 Kill Switch en LIVE

**Enforcement point**: Loop check antes de execution

```python
if self.execution_mode == ExecutionMode.LIVE:
    if not self.kill_switch.can_send_orders():
        # BLOCK execution
        continue
```

**Garantía**: Órdenes LIVE bloqueadas si Kill Switch activo.

---

## BLOQUE 7: TESTING CHECKLIST

### 7.1 Unit Tests

- [ ] `MicrostructureEngine.calculate_features()` retorna features válidas
- [ ] `MicrostructureEngine._calculate_ofi()` con data real
- [ ] `MicrostructureEngine._calculate_cvd()` mantiene accumulator correcto
- [ ] `MicrostructureEngine._calculate_vpin()` usa buckets correctamente
- [ ] `StrategyOrchestrator.generate_signals()` pasa features a estrategias
- [ ] `StrategyOrchestrator._get_strategies_for_regime()` filtra correctamente

### 7.2 Integration Tests

- [ ] Loop PAPER ejecuta sin errores
- [ ] Loop PAPER calcula features en cada iteración
- [ ] Estrategias reciben features correctas en PAPER
- [ ] Brain filtra señales en PAPER
- [ ] PaperExecutionAdapter ejecuta trades simulados
- [ ] Loop LIVE (demo account) ejecuta sin errores
- [ ] Kill Switch bloquea órdenes en LIVE cuando activo
- [ ] Triple confirmación requerida en LIVE

### 7.3 Smoke Tests

```bash
# PAPER mode
python main_institutional.py --mode paper --capital 10000

# LIVE mode (demo account)
python main_institutional.py --mode live --capital 10000

# Backtest mode
python main_institutional.py --mode backtest --days 90
```

### 7.4 NON-NEGOTIABLES Verification

- [ ] RiskManager limita risk a 0-2% por trade
- [ ] ATR NO se usa para position sizing
- [ ] Brain NO viola caps de RiskManager
- [ ] Kill Switch bloquea órdenes en LIVE cuando activo

---

## BLOQUE 8: MIGRATION PATH

### 8.1 Crear main_institutional.py

1. Copiar main_with_execution.py como base (tiene ExecutionMode, ExecutionAdapter)
2. Importar loop structure de main.py (MTF update, regime, signals)
3. Añadir feature calculation (MicrostructureEngine)
4. Implementar generate_signals() en StrategyOrchestrator
5. Integrar en loop

### 8.2 Deprecar Entry Points Legacy

1. Renombrar `main.py` → `main_DEPRECATED_v1.py`
2. Renombrar `main_with_execution.py` → `main_DEPRECATED_v2.py`
3. Actualizar docs: "Use main_institutional.py"

### 8.3 Update Scripts

- `scripts/start_live_trading.py`: Cambiar subprocess call a `main_institutional.py`
- `config/README_LIVE_TRADING.md`: Update instructions

---

**FIN DEL DISEÑO**

**Próximo paso**: FASE 4 - Implementar MicrostructureEngine.
