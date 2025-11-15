# Institutional Smoke Test Report

**Date**: 2025-11-15 08:51:28
**Status**: ❌ P0 FAILURE - ABORT LAUNCH
**Exit Code**: 1
**Duration**: 0.70s

## Summary

- Total Tests: 7
- Passed: 6
- Failed: 1

## Test Results

| Test | Level | Status | Duration | Message |
|------|-------|--------|----------|----------|
| Python environment | P0_HEALTH | ✓ | 0ms | OK |
| Core imports | P0_HEALTH | ✓ | 634ms | OK |
| Config file exists | P0_HEALTH | ✓ | 1ms | OK |
| Config loads | P0_HEALTH | ✓ | 0ms | OK |
| KillSwitch config | P0_HEALTH | ✓ | 20ms | OK |
| Database connection | P0_HEALTH | ✓ | 35ms | OK |
| Execution system imports | P0_HEALTH | ✗ | 5ms | No module named 'MetaTrader5' |

## Exit Code Interpretation

- `0`: All tests passed - Safe to launch
- `1`: P0 failure - ABORT launch (infrastructure broken)
- `2`: P1 failure - WARNING (needs review before launch)
- `3`: P2 warnings - Proceed with caution (non-critical issues)
