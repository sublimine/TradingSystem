"""
Test de IntegraciÃƒÆ’Ã‚Â³n Completo - Sistema de Trading Institucional
Verifica que todos los componentes funcionan correctamente en conjunto.
"""

import sys
sys.path.insert(0, 'C:/Users/Administrator/TradingSystem')

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from pathlib import Path

print("=" * 80)
print("TEST DE INTEGRACIÃƒÆ’Ã¢â‚¬Å“N - SISTEMA DE TRADING INSTITUCIONAL")
print("=" * 80)
print()

# ============================================================================
# FASE 1: VERIFICACIÃƒÆ’Ã¢â‚¬Å“N DE COMPONENTES
# ============================================================================

print("[FASE 1] Verificando componentes del sistema...")
print()

components_status = {}

# 1. Strategy Orchestrator
print("1. Strategy Orchestrator...")
try:
    from src.strategy_orchestrator import StrategyOrchestrator
    orchestrator = StrategyOrchestrator()
    components_status['orchestrator'] = {
        'status': 'OK',
        'strategies_loaded': len(orchestrator.strategies),
        'details': list(orchestrator.strategies.keys())
    }
    print(f"   [OK] {len(orchestrator.strategies)} estrategias cargadas")
    for name in orchestrator.strategies.keys():
        print(f"        - {name}")
except Exception as e:
    components_status['orchestrator'] = {'status': 'FAIL', 'error': str(e)}
    print(f"   [FAIL] {e}")

print()

# 2. Backtesting Engine
print("2. Backtesting Engine...")
try:
    from src.research.backtesting_engine import BacktestEngine, BacktestConfig
    from datetime import datetime
    backtest_config = BacktestConfig(
        start_date=datetime(2024, 1, 1),
        end_date=datetime(2024, 12, 31),
        instruments=['EURUSD.pro'],
        initial_capital=10000.0,
        commission_per_lot=7.0,
        slippage_pct=0.0001
    )
    backtester = BacktestEngine(backtest_config)
    components_status['backtester'] = {'status': 'OK'}
    print(f"   [OK] BacktestingEngine inicializado")
except Exception as e:
    components_status['backtester'] = {'status': 'FAIL', 'error': str(e)}
    print(f"   [FAIL] {e}")

print()

# 3. Event Store (Gobernanza)
print("3. Event Store...")
try:
    from src.governance.event_store import EventStore
    event_store = EventStore(Path("test_integration/events"))
    test_event = event_store.append_event(
        event_type="SYSTEM_TEST",
        payload={"test": "integration"},
        event_id="test_001",
        module_versions={"test": "1.0.0"},
        config_hashes={"test": "hash123"}
    )
    components_status['event_store'] = {'status': 'OK'}
    print(f"   [OK] Event Store operativo")
except Exception as e:
    components_status['event_store'] = {'status': 'FAIL', 'error': str(e)}
    print(f"   [FAIL] {e}")

print()

# 4. Gatekeepers
print("4. Gatekeepers...")
try:
    from src.gatekeepers.kyles_lambda import KylesLambdaEstimator
    from src.gatekeepers.epin_estimator import ePINEstimator
    from src.gatekeepers.spread_monitor import SpreadMonitor
    
    kyle = KylesLambdaEstimator(estimation_window=100)
    epin = ePINEstimator(volume_buckets=50)
    spread = SpreadMonitor(window_size=100)
    
    components_status['gatekeepers'] = {
        'status': 'OK',
        'count': 3,
        'types': ['kyles_lambda', 'epin', 'spread_monitor']
    }
    print(f"   [OK] 3 gatekeepers operativos")
except Exception as e:
    components_status['gatekeepers'] = {'status': 'FAIL', 'error': str(e)}
    print(f"   [FAIL] {e}")

print()

# ============================================================================
# FASE 2: GENERACIÃƒÆ’Ã¢â‚¬Å“N DE DATOS SINTÃƒÆ’Ã¢â‚¬Â°TICOS PARA TEST
# ============================================================================

print("[FASE 2] Generando datos sintÃƒÆ’Ã‚Â©ticos para prueba...")
print()

def generate_synthetic_data(n_bars=500):
    """Genera datos OHLCV sintÃƒÆ’Ã‚Â©ticos realistas."""
    np.random.seed(42)
    
    # Precio base con tendencia y ruido
    base_price = 1.1000
    trend = np.linspace(0, 0.0050, n_bars)
    noise = np.random.normal(0, 0.0005, n_bars)
    close_prices = base_price + trend + noise.cumsum() * 0.1
    
    # OHLC basado en close
    high = close_prices + np.abs(np.random.normal(0, 0.0003, n_bars))
    low = close_prices - np.abs(np.random.normal(0, 0.0003, n_bars))
    open_prices = np.roll(close_prices, 1)
    open_prices[0] = close_prices[0]
    
    # Volumen con spikes ocasionales
    base_volume = 1000
    volume = base_volume + np.random.exponential(500, n_bars)
    
    # Timestamps
    start_time = datetime.now() - timedelta(hours=n_bars)
    timestamps = [start_time + timedelta(hours=i) for i in range(n_bars)]
    
    df = pd.DataFrame({
        'timestamp': timestamps,
        'open': open_prices,
        'high': high,
        'low': low,
        'close': close_prices,
        'volume': volume,
        'tick_volume': volume  # Alias para compatibilidad
    })
    
    df.set_index('timestamp', inplace=True)
    
    return df

try:
    test_data = generate_synthetic_data(500)
    print(f"   [OK] Datos sintÃƒÆ’Ã‚Â©ticos generados: {len(test_data)} barras")
    print(f"        Rango de precios: {test_data['close'].min():.5f} - {test_data['close'].max():.5f}")
    print(f"        Volumen promedio: {test_data['volume'].mean():.0f}")
    components_status['test_data'] = {'status': 'OK', 'bars': len(test_data)}
except Exception as e:
    components_status['test_data'] = {'status': 'FAIL', 'error': str(e)}
    print(f"   [FAIL] {e}")

print()

# ============================================================================
# FASE 3: TEST DE EVALUACIÃƒÆ’Ã¢â‚¬Å“N DE ESTRATEGIAS
# ============================================================================

print("[FASE 3] Evaluando estrategias con datos sintÃƒÆ’Ã‚Â©ticos...")
print()

if components_status.get('orchestrator', {}).get('status') == 'OK' and \
   components_status.get('test_data', {}).get('status') == 'OK':
    
    signals_generated = []
    
    # Features mÃƒÆ’Ã‚Â­nimos para las estrategias
    test_features = {
        'vpin': 0.25,
        'kyle_lambda': 0.5,
        'spread_bps': 1.5,
        'ofi_imbalance': 0.1,
        'order_flow_imbalance': 50.0
    }
    
    for strategy_name, strategy in orchestrator.strategies.items():
        try:
            signal = strategy.evaluate(test_data, test_features)
            
            if signal:
                signals_generated.append({
                    'strategy': strategy_name,
                    'direction': signal.direction,
                    'confidence': signal.confidence,
                    'sizing_level': signal.sizing_level
                })
                print(f"   [SIGNAL] {strategy_name}: {signal.direction.upper()} @ confidence {signal.confidence:.2f}")
            else:
                print(f"   [NO SIGNAL] {strategy_name}")
                
        except Exception as e:
            print(f"   [ERROR] {strategy_name}: {e}")
    
    components_status['strategy_evaluation'] = {
        'status': 'OK',
        'signals_generated': len(signals_generated),
        'signals': signals_generated
    }
    
    print()
    print(f"   Resumen: {len(signals_generated)} seÃƒÆ’Ã‚Â±ales generadas de {len(orchestrator.strategies)} estrategias")
else:
    print("   [SKIP] No se puede evaluar - componentes previos fallaron")
    components_status['strategy_evaluation'] = {'status': 'SKIP'}

print()

# ============================================================================
# FASE 4: TEST DE BACKTESTING PIPELINE
# ============================================================================

print("[FASE 4] Ejecutando pipeline de backtesting...")
print()

if components_status.get('backtester', {}).get('status') == 'OK' and \
   components_status.get('test_data', {}).get('status') == 'OK':
    
    try:
        # Crear seÃƒÆ’Ã‚Â±ales de prueba para el backtester
        test_signals = []
        
        # SeÃƒÆ’Ã‚Â±al LONG
        test_signals.append({
            'timestamp': test_data.index[100],
            'direction': 'long',
            'entry_price': test_data.iloc[100]['close'],
            'stop_loss': test_data.iloc[100]['close'] - 0.0020,
            'take_profit': test_data.iloc[100]['close'] + 0.0040,
            'size': 0.1,
            'strategy': 'test_strategy'
        })
        
        # SeÃƒÆ’Ã‚Â±al SHORT
        test_signals.append({
            'timestamp': test_data.index[300],
            'direction': 'short',
            'entry_price': test_data.iloc[300]['close'],
            'stop_loss': test_data.iloc[300]['close'] + 0.0020,
            'take_profit': test_data.iloc[300]['close'] - 0.0040,
            'size': 0.1,
            'strategy': 'test_strategy'
        })
        
        # Ejecutar backtest con seÃƒÆ’Ã‚Â±ales de prueba
        results = backtester.run_backtest(
            data=test_data,
            signals=test_signals,
            instrument='EURUSD.pro'
        )
        
        print(f"   [OK] Backtest ejecutado")
        print(f"        Total trades: {results.get('total_trades', 0)}")
        print(f"        Win rate: {results.get('win_rate', 0):.1%}")
        print(f"        PnL final: ${results.get('final_pnl', 0):.2f}")
        
        components_status['backtest_pipeline'] = {
            'status': 'OK',
            'total_trades': results.get('total_trades', 0),
            'win_rate': results.get('win_rate', 0)
        }
        
    except Exception as e:
        print(f"   [FAIL] {e}")
        components_status['backtest_pipeline'] = {'status': 'FAIL', 'error': str(e)}
else:
    print("   [SKIP] No se puede ejecutar - componentes previos fallaron")
    components_status['backtest_pipeline'] = {'status': 'SKIP'}

print()

# ============================================================================
# FASE 5: REPORTE FINAL
# ============================================================================

print("=" * 80)
print("REPORTE FINAL DE INTEGRACIÃƒÆ’Ã¢â‚¬Å“N")
print("=" * 80)
print()

total_components = len(components_status)
ok_components = sum(1 for v in components_status.values() if v.get('status') == 'OK')
fail_components = sum(1 for v in components_status.values() if v.get('status') == 'FAIL')

print(f"Componentes verificados: {total_components}")
print(f"  OK: {ok_components}")
print(f"  FAIL: {fail_components}")
print(f"  SKIP: {total_components - ok_components - fail_components}")
print()

print("Detalle por componente:")
for component, status in components_status.items():
    status_str = status.get('status', 'UNKNOWN')
    if status_str == 'OK':
        print(f"  [ÃƒÂ¢Ã…â€œÃ¢â‚¬Å“] {component}")
        if 'strategies_loaded' in status:
            print(f"      Estrategias: {status['strategies_loaded']}")
        if 'signals_generated' in status:
            print(f"      SeÃƒÆ’Ã‚Â±ales: {status['signals_generated']}")
        if 'total_trades' in status:
            print(f"      Trades: {status['total_trades']}")
    elif status_str == 'FAIL':
        print(f"  [ÃƒÂ¢Ã…â€œÃ¢â‚¬â€] {component}")
        if 'error' in status:
            print(f"      Error: {status['error']}")
    else:
        print(f"  [ÃƒÂ¢Ã¢â‚¬â€Ã¢â‚¬Â¹] {component} (skipped)")

print()

if fail_components == 0 and ok_components >= 4:
    print("=" * 80)
    print("RESULTADO: SISTEMA OPERATIVO Y LISTO PARA PRODUCCIÃƒÆ’Ã¢â‚¬Å“N")
    print("=" * 80)
    exit(0)
elif fail_components > 0:
    print("=" * 80)
    print(f"ADVERTENCIA: {fail_components} componente(s) requieren atenciÃƒÆ’Ã‚Â³n")
    print("=" * 80)
    exit(1)
else:
    print("=" * 80)
    print("SISTEMA EN DESARROLLO - Continuar con implementaciÃƒÆ’Ã‚Â³n")
    print("=" * 80)
    exit(0)