import time
import json
from datetime import datetime
from pathlib import Path

checkpoints_path = Path('C:/TradingSystem/checkpoints')
logs_path = Path('C:/TradingSystem/logs')

def generate_checkpoint(num, wait_time):
    time.sleep(wait_time)
    
    log_file = logs_path / 'live_trading.log'
    
    if not log_file.exists():
        return None
    
    with open(log_file, 'r', encoding='utf-8', errors='ignore') as f:
        lines = f.readlines()[-1000:]
    
    signals_by_strategy = {}
    trades_by_strategy = {}
    errors_by_strategy = {}
    
    for i, line in enumerate(lines):
        if 'Estrategia:' in line:
            try:
                strat = line.split('Estrategia:')[1].strip().split()[0]
                signals_by_strategy[strat] = signals_by_strategy.get(strat, 0) + 1
            except:
                pass
        
        if 'OK ORDEN EJECUTADA' in line:
            for j in range(max(0, i-10), i):
                if 'Estrategia:' in lines[j]:
                    try:
                        strat = lines[j].split('Estrategia:')[1].strip().split()[0]
                        trades_by_strategy[strat] = trades_by_strategy.get(strat, 0) + 1
                        break
                    except:
                        pass
        
        if 'ERROR evaluando' in line:
            try:
                strat = line.split('ERROR evaluando')[1].strip().split(':')[0]
                errors_by_strategy[strat] = errors_by_strategy.get(strat, 0) + 1
            except:
                pass
    
    active_strategies = len([s for s in signals_by_strategy if signals_by_strategy[s] > 0 or s in trades_by_strategy])
    
    checkpoint = {
        'timestamp': datetime.now().isoformat(),
        'checkpoint_num': num,
        'estrategias_activas': f"{active_strategies}/9",
        'signals_by_strategy': signals_by_strategy,
        'trades_by_strategy': trades_by_strategy,
        'errors_by_strategy': errors_by_strategy,
        'total_signals': sum(signals_by_strategy.values()),
        'total_trades': sum(trades_by_strategy.values()),
        'system_latency_ms': 0,
        'risk_utilization_pct': 0
    }
    
    checkpoint_file = checkpoints_path / f'ckpt_{num:03d}_{wait_time//60}min.json'
    with open(checkpoint_file, 'w') as f:
        json.dump(checkpoint, f, indent=2)
    
    print(f"Checkpoint {num} generado ({wait_time//60} min)")
    print(f"  Activas: {active_strategies}/9")
    print(f"  Señales: {checkpoint['total_signals']}")
    print(f"  Trades: {checkpoint['total_trades']}")
    
    return checkpoint

if __name__ == '__main__':
    print("Generando checkpoints...")
    generate_checkpoint(1, 900)   # 15 min
    generate_checkpoint(2, 900)   # +15 min (30 min total)
    print("Checkpoints completados")
