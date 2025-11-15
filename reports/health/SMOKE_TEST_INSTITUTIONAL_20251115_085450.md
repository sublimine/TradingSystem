# Institutional Smoke Test Report

**Date**: 2025-11-15 08:54:50
**Status**: ⚠️  P1 FAILURES - NEEDS REVIEW
**Exit Code**: 2
**Duration**: 1.79s

## Summary

- Total Tests: 17
- Passed: 13
- Failed: 4

## Test Results

| Test | Level | Status | Duration | Message |
|------|-------|--------|----------|----------|
| Python environment | P0_HEALTH | ✓ | 0ms | OK |
| Core imports | P0_HEALTH | ✓ | 673ms | OK |
| Config file exists | P0_HEALTH | ✓ | 1ms | OK |
| Config loads | P0_HEALTH | ✓ | 0ms | OK |
| KillSwitch config | P0_HEALTH | ✓ | 21ms | OK |
| Database connection | P0_HEALTH | ✓ | 37ms | OK |
| Execution system imports | P0_HEALTH | ✓ | 5ms | OK |
| MicrostructureEngine import | P1_INTEGRATION | ✓ | 6ms | OK |
| MicrostructureEngine calculation | P1_INTEGRATION | ✓ | 7ms | OK |
| Strategy orchestrator | P1_INTEGRATION | ✗ | 1019ms | No module named 'MetaTrader5' |
| Backtest engine parity | P1_INTEGRATION | ✓ | 10ms | OK |
| Brain import | P1_INTEGRATION | ✗ | 5ms | No module named 'MetaTrader5' |
| Reporting system | P1_INTEGRATION | ✓ | 1ms | OK |
| Risk allocator | P1_INTEGRATION | ✗ | 5ms | No module named 'MetaTrader5' |
| MT5 availability | P2_COSMETIC | ✗ | 1ms | MetaTrader5 not installed (OK for non-MT5 environments) |
| Reports directory | P2_COSMETIC | ✓ | 0ms | OK |
| Data directory | P2_COSMETIC | ✓ | 0ms | OK |

## Exit Code Interpretation

- `0`: All tests passed - Safe to launch
- `1`: P0 failure - ABORT launch (infrastructure broken)
- `2`: P1 failure - WARNING (needs review before launch)
- `3`: P2 warnings - Proceed with caution (non-critical issues)
