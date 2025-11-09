"""
Backtesting Engine - Motor de backtesting institucional
SimulaciÃƒÂ³n realista con costos, slippage y limitaciones.
"""

import logging
from typing import Dict, List, Optional, Callable
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class BacktestConfig:
    """ConfiguraciÃƒÂ³n de backtest."""
    start_date: datetime
    end_date: datetime
    instruments: List[str]
    initial_capital: float
    
    # Costos
    commission_per_lot: float = 7.0
    spread_multiplier: float = 1.0
    slippage_pct: float = 0.0001
    
    # Limitaciones
    max_position_size_pct: float = 0.05
    max_volume_pct: float = 0.5
    
    # Overnight
    financing_rate_annual: float = 0.05


@dataclass
class BacktestTrade:
    """Trade individual en backtest."""
    trade_id: int
    timestamp: datetime
    instrument: str
    side: str
    entry_price: float
    exit_price: float
    size: float
    entry_cost: float
    exit_cost: float
    pnl: float
    pnl_pct: float
    holding_bars: int
    strategy_id: str


@dataclass
class BacktestResults:
    """Resultados completos de backtest."""
    config: BacktestConfig
    
    # Performance
    total_return_pct: float
    annualized_return_pct: float
    sharpe_ratio: float
    sortino_ratio: float
    max_drawdown_pct: float
    max_drawdown_duration_days: int
    calmar_ratio: float
    
    # Trade statistics
    total_trades: int
    winning_trades: int
    losing_trades: int
    win_rate_pct: float
    profit_factor: float
    avg_win: float
    avg_loss: float
    
    # Equity curve
    equity_curve: pd.DataFrame
    trades: List[BacktestTrade]
    
    # Por estrategia
    performance_by_strategy: Dict[str, Dict]
    
    # Por instrumento
    performance_by_instrument: Dict[str, Dict]


class BacktestEngine:
    """
    Motor de backtesting institucional.
    
    Features:
    - SimulaciÃƒÂ³n barra por barra
    - Costos realistas (spread, slippage, commission, financing)
    - Limitaciones de volumen
    - Gap handling
    - Rolling statistics
    """
    
    def __init__(self, config: BacktestConfig):
        """
        Inicializa engine.
        
        Args:
            config: ConfiguraciÃƒÂ³n del backtest
        """
        self.config = config
        
        # Estado
        self._capital = config.initial_capital
        self._positions: Dict[str, Dict] = {}
        self._equity_history: List[Dict] = []
        self._trades: List[BacktestTrade] = []
        self._trade_counter = 0
        
        logger.info(
            f"BacktestEngine initialized: "
            f"{config.start_date.date()} to {config.end_date.date()}, "
            f"capital=${config.initial_capital:,.0f}"
        )
    
    def run(
        self,
        data: Dict[str, pd.DataFrame],
        signal_generator: Callable
    ) -> BacktestResults:
        """
        Ejecuta backtest completo.
        
        Args:
            data: Dict de DataFrames OHLCV por instrumento
            signal_generator: FunciÃƒÂ³n que genera seÃƒÂ±ales
                Firma: signal_generator(timestamp, bars_dict) -> List[signal]
        
        Returns:
            BacktestResults completo
        """
        logger.info("Starting backtest...")
        
        # Obtener fechas comunes
        common_dates = self._get_common_dates(data)
        
        if not common_dates:
            raise ValueError("No common dates found in data")
        
        logger.info(f"Processing {len(common_dates)} bars")
        
        # Iterar barra por barra
        for i, timestamp in enumerate(common_dates):
            # Obtener barras actuales
            current_bars = {}
            for instrument, df in data.items():
                if timestamp in df.index:
                    current_bars[instrument] = df.loc[timestamp]
            
            # Generar seÃƒÂ±ales
            signals = signal_generator(timestamp, current_bars)
            
            # Procesar seÃƒÂ±ales
            for signal in signals:
                self._process_signal(timestamp, signal, current_bars)
            
            # Actualizar posiciones existentes
            self._update_positions(timestamp, current_bars)
            
            # Registrar equity
            equity = self._calculate_equity(current_bars)
            self._equity_history.append({
                'timestamp': timestamp,
                'equity': equity,
                'cash': self._capital,
                'positions_value': equity - self._capital
            })
            
            if (i + 1) % 1000 == 0:
                logger.info(f"Processed {i + 1}/{len(common_dates)} bars")
        
        # Calcular resultados
        results = self._calculate_results()
        
        logger.info(
            f"Backtest complete: "
            f"return={results.total_return_pct:.2f}%, "
            f"sharpe={results.sharpe_ratio:.2f}"
        )
        
        return results
    
    def _process_signal(
        self,
        timestamp: datetime,
        signal: Dict,
        current_bars: Dict[str, pd.Series]
    ):
        """Procesa una seÃƒÂ±al de trading."""
        instrument = signal['instrument']
        direction = signal['direction']
        size = signal.get('size', 1.0)
        
        # Verificar que tenemos datos
        if instrument not in current_bars:
            return
        
        bar = current_bars[instrument]
        
        # Precio de entrada (simulamos ejecuciÃƒÂ³n en close)
        entry_price = bar['close']
        
        # Verificar limitaciones
        if not self._check_execution_constraints(
            instrument, size, bar, current_bars
        ):
            return
        
        # Calcular costos de entrada
        spread = entry_price * 0.00015  # Spread tÃƒÂ­pico
        slippage = entry_price * self.config.slippage_pct
        commission = size * self.config.commission_per_lot
        
        entry_cost = (spread + slippage) * size + commission
        
        # Verificar capital suficiente
        required_capital = entry_price * size * 100000 * 0.01  # Margen 1%
        if required_capital + entry_cost > self._capital:
            return
        
        # Abrir posiciÃƒÂ³n
        if instrument not in self._positions:
            self._positions[instrument] = []
        
        self._positions[instrument].append({
            'timestamp': timestamp,
            'direction': direction,
            'size': size,
            'entry_price': entry_price,
            'entry_cost': entry_cost,
            'strategy_id': signal.get('strategy_id', 'unknown')
        })
        
        self._capital -= (required_capital + entry_cost)
    
    def _update_positions(
        self,
        timestamp: datetime,
        current_bars: Dict[str, pd.Series]
    ):
        """Actualiza posiciones abiertas."""
        for instrument, positions in list(self._positions.items()):
            if instrument not in current_bars:
                continue
            
            bar = current_bars[instrument]
            current_price = bar['close']
            
            # Revisar cada posiciÃƒÂ³n
            for pos in positions[:]:
                # LÃƒÂ³gica simple: cerrar despuÃƒÂ©s de N barras o por stop/target
                holding_time = (timestamp - pos['timestamp']).total_seconds() / 60
                
                should_close = False
                exit_reason = None
                
                # Simple: cerrar despuÃƒÂ©s de 60 minutos
                if holding_time >= 60:
                    should_close = True
                    exit_reason = 'time'
                
                if should_close:
                    self._close_position(
                        instrument,
                        pos,
                        timestamp,
                        current_price,
                        exit_reason
                    )
                    positions.remove(pos)
            
            if not positions:
                del self._positions[instrument]
    
    def _close_position(
        self,
        instrument: str,
        position: Dict,
        timestamp: datetime,
        exit_price: float,
        reason: str
    ):
        """Cierra una posiciÃƒÂ³n."""
        # Calcular costos de salida
        spread = exit_price * 0.00015
        slippage = exit_price * self.config.slippage_pct
        commission = position['size'] * self.config.commission_per_lot
        
        exit_cost = (spread + slippage) * position['size'] + commission
        
        # Calcular P&L
        if position['direction'] == 1:  # Long
            pnl = (exit_price - position['entry_price']) * position['size'] * 100000
        else:  # Short
            pnl = (position['entry_price'] - exit_price) * position['size'] * 100000
        
        pnl -= (position['entry_cost'] + exit_cost)
        
        # Devolver capital
        returned_capital = position['entry_price'] * position['size'] * 100000 * 0.01
        self._capital += returned_capital + pnl
        
        # Registrar trade
        holding_bars = int((timestamp - position['timestamp']).total_seconds() / 60)
        
        trade = BacktestTrade(
            trade_id=self._trade_counter,
            timestamp=timestamp,
            instrument=instrument,
            side='long' if position['direction'] == 1 else 'short',
            entry_price=position['entry_price'],
            exit_price=exit_price,
            size=position['size'],
            entry_cost=position['entry_cost'],
            exit_cost=exit_cost,
            pnl=pnl,
            pnl_pct=(pnl / returned_capital * 100) if returned_capital > 0 else 0,
            holding_bars=holding_bars,
            strategy_id=position['strategy_id']
        )
        
        self._trades.append(trade)
        self._trade_counter += 1
    
    def _check_execution_constraints(
        self,
        instrument: str,
        size: float,
        bar: pd.Series,
        all_bars: Dict[str, pd.Series]
    ) -> bool:
        """Verifica constraints de ejecuciÃƒÂ³n."""
        # Max position size
        position_value = bar['close'] * size * 100000 * 0.01  # Margin requirement
        if position_value > self.config.initial_capital * self.config.max_position_size_pct:
            return False
        
        # Max volume (no ejecutar si excede X% del volumen de la barra)
        if 'volume' in bar and bar['volume'] > 0:
            if size > bar['volume'] * self.config.max_volume_pct:
                return False
        
        return True
    
    def _calculate_equity(self, current_bars: Dict[str, pd.Series]) -> float:
        """Calcula equity total."""
        equity = self._capital
        
        # AÃƒÂ±adir valor de posiciones abiertas
        for instrument, positions in self._positions.items():
            if instrument in current_bars:
                current_price = current_bars[instrument]['close']
                for pos in positions:
                    if pos['direction'] == 1:
                        unrealized = (current_price - pos['entry_price']) * pos['size'] * 100000
                    else:
                        unrealized = (pos['entry_price'] - current_price) * pos['size'] * 100000
                    
                    equity += unrealized
        
        return equity
    
    def _get_common_dates(self, data: Dict[str, pd.DataFrame]) -> List[datetime]:
        """Obtiene fechas comunes entre todos los instrumentos."""
        if not data:
            return []
        
        common_index = None
        for df in data.values():
            if common_index is None:
                common_index = set(df.index)
            else:
                common_index &= set(df.index)
        
        dates = sorted(list(common_index))
        
        # Filtrar por rango de config
        dates = [
            d for d in dates
            if self.config.start_date <= d <= self.config.end_date
        ]
        
        return dates
    
    def _calculate_results(self) -> BacktestResults:
        """Calcula resultados finales."""
        equity_df = pd.DataFrame(self._equity_history)
        equity_df.set_index('timestamp', inplace=True)
        
        # Returns
        final_equity = equity_df['equity'].iloc[-1]
        total_return = (final_equity / self.config.initial_capital - 1) * 100
        
        # Calcular returns diarios
        daily_returns = equity_df['equity'].pct_change().dropna()
        
        # Sharpe
        if len(daily_returns) > 0 and daily_returns.std() > 0:
            sharpe = (
                daily_returns.mean() / daily_returns.std() *
                np.sqrt(252)  # Anualizar
            )
        else:
            sharpe = 0.0
        
        # Sortino (solo downside vol)
        negative_returns = daily_returns[daily_returns < 0]
        if len(negative_returns) > 0 and negative_returns.std() > 0:
            sortino = (
                daily_returns.mean() / negative_returns.std() *
                np.sqrt(252)
            )
        else:
            sortino = 0.0
        
        # Drawdown
        cummax = equity_df['equity'].cummax()
        drawdown = (equity_df['equity'] - cummax) / cummax * 100
        max_dd = abs(drawdown.min())
        
        # DuraciÃƒÂ³n de max DD
        # Simplificado: contar barras en DD
        in_dd = drawdown < -0.01
        max_dd_duration = 0
        if in_dd.any():
            dd_lengths = []
            current_length = 0
            for val in in_dd:
                if val:
                    current_length += 1
                else:
                    if current_length > 0:
                        dd_lengths.append(current_length)
                    current_length = 0
            
            if dd_lengths:
                max_dd_duration = max(dd_lengths)
        
        # Calmar
        days = (self.config.end_date - self.config.start_date).days
        annualized_return = total_return * (365 / days) if days > 0 else 0
        calmar = annualized_return / max_dd if max_dd > 0 else 0
        
        # Trade stats
        winning_trades = [t for t in self._trades if t.pnl > 0]
        losing_trades = [t for t in self._trades if t.pnl < 0]
        
        win_rate = (
            len(winning_trades) / len(self._trades) * 100
            if self._trades else 0
        )
        
        total_wins = sum(t.pnl for t in winning_trades)
        total_losses = abs(sum(t.pnl for t in losing_trades))
        profit_factor = total_wins / total_losses if total_losses > 0 else 0
        
        avg_win = total_wins / len(winning_trades) if winning_trades else 0
        avg_loss = total_losses / len(losing_trades) if losing_trades else 0
        
        return BacktestResults(
            config=self.config,
            total_return_pct=total_return,
            annualized_return_pct=annualized_return,
            sharpe_ratio=sharpe,
            sortino_ratio=sortino,
            max_drawdown_pct=max_dd,
            max_drawdown_duration_days=max_dd_duration,
            calmar_ratio=calmar,
            total_trades=len(self._trades),
            winning_trades=len(winning_trades),
            losing_trades=len(losing_trades),
            win_rate_pct=win_rate,
            profit_factor=profit_factor,
            avg_win=avg_win,
            avg_loss=avg_loss,
            equity_curve=equity_df,
            trades=self._trades,
            performance_by_strategy={},
            performance_by_instrument={}
        )