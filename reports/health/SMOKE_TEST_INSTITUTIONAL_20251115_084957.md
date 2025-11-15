# Institutional Smoke Test Report

**Date**: 2025-11-15 08:49:57
**Status**: ❌ P0 FAILURE - ABORT LAUNCH
**Exit Code**: 1
**Duration**: 0.76s

## Summary

- Total Tests: 7
- Passed: 2
- Failed: 5

## Test Results

| Test | Level | Status | Duration | Message |
|------|-------|--------|----------|----------|
| Python environment | P0_HEALTH | ✓ | 0ms | OK |
| Core imports | P0_HEALTH | ✓ | 699ms | OK |
| Config file exists | P0_HEALTH | ✗ | 0ms | config.yaml not found at /home/user/TradingSystem/config.yaml |
| Config loads | P0_HEALTH | ✗ | 0ms | [Errno 2] No such file or directory: '/home/user/TradingSystem/config.yaml' |
| KillSwitch config | P0_HEALTH | ✗ | 23ms | No module named 'MetaTrader5' |
| Database connection | P0_HEALTH | ✗ | 34ms | Database connection failed: [Errno 2] No such file or directory: '/home/user/TradingSystem/config.yaml' |
| Execution system imports | P0_HEALTH | ✗ | 3ms | No module named 'MetaTrader5' |

## Exit Code Interpretation

- `0`: All tests passed - Safe to launch
- `1`: P0 failure - ABORT launch (infrastructure broken)
- `2`: P1 failure - WARNING (needs review before launch)
- `3`: P2 warnings - Proceed with caution (non-critical issues)
