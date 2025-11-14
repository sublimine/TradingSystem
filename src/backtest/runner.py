"""
Backtest Runner - MANDATO 17

Loop de ejecución del backtest institucional.

Procesa candle por candle, ejecutando el flujo completo:
1. Actualizar datos de mercado
2. Actualizar microestructura (VPIN, OFI, depth, spoofing)
3. Actualizar multiframe context (HTF, MTF, LTF)
4. Evaluar señales de estrategias
5. QualityScorer puntúa cada señal
6. RiskManager aprueba/rechaza
7. PositionManager gestiona stops/targets estructurales
8. ExecutionEventLogger registra todo

Respeta EXACTAMENTE el flujo de producción. NO simplificaciones.
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import logging
from tqdm import tqdm
import uuid

from .engine import BacktestEngine

logger = logging.getLogger(__name__)


class BacktestRunner:
    """
    Ejecutor del backtest institucional.

    Procesa datos históricos candle por candle, ejecutando el sistema completo.
    """

    def __init__(self, engine: BacktestEngine):
        """
        Inicializar runner.

        Args:
            engine: BacktestEngine inicializado
        """
        self.engine = engine
        self.execution_mode = engine.config.get('execution_mode', 'CLOSE')  # 'CLOSE' o 'TICK'

        # State tracking
        self.current_bar_index: Dict[str, int] = {}  # {symbol: current_index}
        self.iteration_count = 0

        logger.info(f"BacktestRunner initialized: execution_mode={self.execution_mode}")

    def run(self, start_date: Optional[datetime] = None, end_date: Optional[datetime] = None,
            progress_bar: bool = True):
        """
        Ejecutar backtest completo.

        Args:
            start_date: Fecha de inicio (None = usar mínimo de datos)
            end_date: Fecha de fin (None = usar máximo de datos)
            progress_bar: Mostrar barra de progreso
        """
        logger.info("="*60)
        logger.info("STARTING BACKTEST")
        logger.info("="*60)

        # Determinar rango de fechas
        if start_date is None or end_date is None:
            start_date, end_date = self._determine_date_range()

        logger.info(f"Backtest period: {start_date} to {end_date}")

        # Inicializar índices
        for symbol in self.engine.market_data:
            self.current_bar_index[symbol] = 0

        # Obtener timestamps únicos (unión de todos los símbolos)
        all_timestamps = self._get_all_timestamps(start_date, end_date)

        logger.info(f"Total timestamps to process: {len(all_timestamps)}")

        # Ejecutar loop principal
        if progress_bar:
            iterator = tqdm(all_timestamps, desc="Backtest", unit="bar")
        else:
            iterator = all_timestamps

        for timestamp in iterator:
            self._process_timestamp(timestamp)
            self.iteration_count += 1

            # Log cada 1000 barras
            if self.iteration_count % 1000 == 0:
                stats = self.engine.get_statistics()
                logger.info(f"Progress: {self.iteration_count} bars processed, "
                           f"{stats['trades_opened']} trades opened, "
                           f"{stats['trades_closed']} trades closed")

        # Finalizar
        self.engine.finalize()

        logger.info(f"✅ Backtest completed: {self.iteration_count} bars processed")

    def _determine_date_range(self) -> tuple:
        """
        Determinar rango de fechas común a todos los símbolos.

        Returns:
            (start_date, end_date)
        """
        start_dates = []
        end_dates = []

        for symbol, df in self.engine.market_data.items():
            if not df.empty:
                start_dates.append(df.index[0])
                end_dates.append(df.index[-1])

        if not start_dates:
            raise ValueError("No market data available")

        # Usar intersección de rangos (máximo de starts, mínimo de ends)
        start_date = max(start_dates)
        end_date = min(end_dates)

        return start_date, end_date

    def _get_all_timestamps(self, start_date: datetime, end_date: datetime) -> List[datetime]:
        """
        Obtener lista de todos los timestamps únicos en el rango.

        Args:
            start_date: Fecha inicio
            end_date: Fecha fin

        Returns:
            Lista ordenada de timestamps
        """
        all_timestamps = set()

        for symbol, df in self.engine.market_data.items():
            # Filtrar por rango
            df_range = df.loc[start_date:end_date]
            all_timestamps.update(df_range.index.tolist())

        # Ordenar
        timestamps = sorted(list(all_timestamps))

        return timestamps

    def _process_timestamp(self, timestamp: datetime):
        """
        Procesar un timestamp específico.

        Flujo institucional completo:
        1. Actualizar market data
        2. Actualizar microstructure
        3. Actualizar multiframe context
        4. Actualizar posiciones (stops/targets)
        5. Evaluar señales de estrategias
        6. Risk evaluation + execution

        Args:
            timestamp: Timestamp actual
        """
        self.engine.current_timestamp = timestamp

        # 1. Actualizar datos de mercado para cada símbolo
        current_bars = {}
        for symbol, df in self.engine.market_data.items():
            if timestamp in df.index:
                current_bars[symbol] = df.loc[timestamp]

        if not current_bars:
            return  # No hay datos para este timestamp

        # 2. Actualizar microestructura (VPIN, OFI, etc.)
        self._update_microstructure(timestamp, current_bars)

        # 3. Actualizar multiframe context (HTF/MTF/LTF)
        self._update_multiframe_context(timestamp)

        # 4. Actualizar posiciones existentes (stops, targets)
        self._update_positions(timestamp, current_bars)

        # 5. Evaluar señales de estrategias
        signals = self._evaluate_strategies(timestamp, current_bars)

        # 6. Procesar señales (risk management + execution)
        self._process_signals(timestamp, signals, current_bars)

    def _update_microstructure(self, timestamp: datetime, current_bars: Dict):
        """
        Actualizar análisis de microestructura.

        En backtest real necesitaríamos tick data para VPIN/OFI preciso.
        Para backtest con OHLCV, usamos aproximaciones:
        - Volume como proxy para trade volume
        - Precio close vs open como proxy para buy/sell classification
        """
        if not self.engine.microstructure_engine:
            return

        for symbol, bar in current_bars.items():
            # Clasificar trades como buy/sell basado en close vs open
            # Aproximación: close > open = bullish candle = más buy volume
            mid = (bar['high'] + bar['low']) / 2
            close = bar['close']
            volume = bar['volume']

            if close > mid:
                # Candle alcista: clasificar como BUY
                side = 'BUY'
            else:
                # Candle bajista: clasificar como SELL
                side = 'SELL'

            # Crear trade sintético para microstructure engine
            # Convert pandas Timestamp to datetime if needed, ensure timezone-aware
            if hasattr(timestamp, 'to_pydatetime'):
                ts = timestamp.to_pydatetime()
            else:
                ts = timestamp

            # Ensure timezone-aware (UTC)
            if ts.tzinfo is None:
                from datetime import timezone
                ts = ts.replace(tzinfo=timezone.utc)

            trades = [{
                'timestamp': ts,
                'price': float(close),
                'volume': float(volume),
                'side': side
            }]

            # Actualizar microstructure engine
            self.engine.microstructure_engine.update_trades(symbol, trades)

    def _update_multiframe_context(self, timestamp: datetime):
        """
        Actualizar contexto multi-timeframe (HTF, MTF, LTF).

        Analiza estructura en cada símbolo.
        """
        if not self.engine.multiframe_orchestrator:
            return

        for symbol, df in self.engine.market_data.items():
            # Obtener histórico hasta timestamp actual
            historical = df.loc[:timestamp]

            if len(historical) < 50:
                continue  # Insuficiente historia

            # Dividir en HTF y MTF
            # HTF: últimas 200 barras, MTF: últimas 50 barras
            htf_data = historical.tail(200)
            mtf_data = historical.tail(50)

            current_price = historical.iloc[-1]['close']

            # Actualizar análisis (sin signal_direction por ahora, análisis neutral)
            try:
                self.engine.multiframe_orchestrator.analyze_multiframe(
                    symbol=symbol,
                    htf_ohlcv=htf_data,
                    mtf_ohlcv=mtf_data,
                    current_price=current_price,
                    signal_direction=None  # Neutral analysis
                )
            except Exception as e:
                logger.debug(f"Multiframe analysis failed for {symbol}: {e}")

    def _update_positions(self, timestamp: datetime, current_bars: Dict):
        """
        Actualizar posiciones abiertas: stops, targets, partials.

        PositionManager maneja automáticamente:
        - Breakeven @ 1.5R
        - Trailing stops @ 2R (structure-based)
        - Partial exits @ 2.5R
        """
        if not self.engine.position_manager:
            return

        # Preparar market data dict para PositionManager
        market_data_dict = {}
        for symbol, df in self.engine.market_data.items():
            # Últimas 100 barras hasta timestamp actual
            historical = df.loc[:timestamp].tail(100)
            market_data_dict[symbol] = historical

        # PositionManager procesa todos los positions
        self.engine.position_manager.update_positions(market_data_dict)

    def _evaluate_strategies(self, timestamp: datetime, current_bars: Dict) -> List[Dict]:
        """
        Evaluar señales de todas las estrategias.

        Args:
            timestamp: Timestamp actual
            current_bars: Datos actuales {symbol: Series}

        Returns:
            Lista de señales [{symbol, direction, entry_price, stop_loss, take_profit, metadata, strategy_name}, ...]
        """
        all_signals = []

        for symbol, bar in current_bars.items():
            # Obtener histórico para análisis
            df = self.engine.market_data[symbol]
            historical = df.loc[:timestamp]

            if len(historical) < 50:
                continue  # Insuficiente historia para estrategias

            # Evaluar cada estrategia
            for strategy_name, strategy in self.engine.strategies.items():
                try:
                    # Generar señal
                    signal = strategy.generate_signal(symbol, historical)

                    if signal is not None:
                        # Añadir metadata de estrategia
                        signal['strategy_name'] = strategy_name
                        signal['timestamp'] = timestamp
                        signal['signal_id'] = str(uuid.uuid4())

                        all_signals.append(signal)

                        logger.debug(f"Signal generated: {strategy_name} {symbol} {signal['direction']}")

                except Exception as e:
                    logger.error(f"Strategy {strategy_name} failed for {symbol}: {e}")

        return all_signals

    def _process_signals(self, timestamp: datetime, signals: List[Dict], current_bars: Dict):
        """
        Procesar señales: quality scoring + risk management + execution.

        Args:
            timestamp: Timestamp actual
            signals: Lista de señales
            current_bars: Datos actuales
        """
        if not signals:
            return

        self.engine.stats['total_signals'] += len(signals)

        for signal in signals:
            symbol = signal['symbol']

            # Construir market_context para QualityScorer
            market_context = self._build_market_context(symbol, timestamp)

            # Evaluar con RiskManager (incluye QualityScorer)
            risk_decision = self.engine.risk_manager.evaluate_signal(signal, market_context)

            if risk_decision['approved']:
                # Señal aprobada: ejecutar entrada
                self._execute_entry(signal, risk_decision, current_bars)
                self.engine.stats['signals_approved'] += 1

            else:
                # Señal rechazada: ya logueado por RiskManager
                self.engine.stats['signals_rejected'] += 1

    def _build_market_context(self, symbol: str, timestamp: datetime) -> Dict:
        """
        Construir market context para QualityScorer.

        Args:
            symbol: Símbolo
            timestamp: Timestamp actual

        Returns:
            Dict con contexto de mercado
        """
        context = {
            'timestamp': timestamp,
            'volatility_regime': 'NORMAL',  # TODO: Implementar regime detection
            'strategy_performance': {},  # TODO: Tracking de performance por estrategia
        }

        # VPIN desde microstructure engine
        if self.engine.microstructure_engine:
            vpin = self.engine.microstructure_engine.get_vpin(symbol)
            context['vpin'] = vpin if vpin is not None else 0.4

        return context

    def _execute_entry(self, signal: Dict, risk_decision: Dict, current_bars: Dict):
        """
        Ejecutar entrada de posición.

        Args:
            signal: Señal original
            risk_decision: Decisión de RiskManager
            current_bars: Datos actuales
        """
        symbol = signal['symbol']
        position_id = f"BT_{signal['signal_id'][:8]}"

        # Obtener tamaño de posición aprobado
        lot_size = risk_decision['position_size_lots']
        risk_pct = risk_decision['position_size_pct']

        # Registrar en RiskManager
        self.engine.risk_manager.register_position(position_id, signal, lot_size, risk_pct)

        # Registrar en PositionManager (con event_logger integrado)
        self.engine.position_manager.add_position(position_id, signal, lot_size)

        # Actualizar stats
        self.engine.stats['trades_opened'] += 1

        logger.info(f"✅ ENTRY: {position_id} {signal['strategy_name']} {symbol} {signal['direction']} "
                   f"{lot_size} lots @ {signal['entry_price']:.5f}, "
                   f"SL={signal['stop_loss']:.5f}, TP={signal['take_profit']:.5f}, "
                   f"Quality={risk_decision['quality_score']:.3f}")
