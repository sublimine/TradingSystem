import sys
sys.path.insert(0, 'C:/Users/Administrator/TradingSystem/src')

try:
    from gatekeepers.gatekeeper_adapter import GatekeeperAdapter
    adapter = GatekeeperAdapter()
    
    with open('adapter_test_result.txt', 'w') as f:
        f.write('SUCCESS: Adapter imported and instantiated\n')
        f.write(f'Regime: {adapter.get_current_regime()}\n')
    
    print('Test completed - check adapter_test_result.txt')
    
except Exception as e:
    with open('adapter_test_result.txt', 'w') as f:
        f.write(f'FAILED: {str(e)}\n')
    print(f'Test failed: {str(e)}')
