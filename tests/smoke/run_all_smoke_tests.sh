#!/bin/bash
# Run All Smoke Tests - PLAN OMEGA FASE 5.1
# Executes all 4 smoke tests in sequence

set -e  # Exit on first failure

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

echo "================================================================================"
echo "PLAN OMEGA - SMOKE TESTS SUITE"
echo "================================================================================"
echo ""
echo "Running all 4 smoke tests in sequence..."
echo ""

# Test 1: MicrostructureEngine
echo "================================================================================"
echo "TEST 1/4: MicrostructureEngine"
echo "================================================================================"
python test_microstructure_engine.py
if [ $? -eq 0 ]; then
    TEST1="✅ PASSED"
else
    TEST1="❌ FAILED"
fi
echo ""

# Test 2: Execution System
echo "================================================================================"
echo "TEST 2/4: ExecutionManager + KillSwitch"
echo "================================================================================"
python test_execution_system.py
if [ $? -eq 0 ]; then
    TEST2="✅ PASSED"
else
    TEST2="❌ FAILED"
fi
echo ""

# Test 3: Runtime Profiles
echo "================================================================================"
echo "TEST 3/4: Runtime Profiles"
echo "================================================================================"
python test_runtime_profiles.py
if [ $? -eq 0 ]; then
    TEST3="✅ PASSED"
else
    TEST3="❌ FAILED"
fi
echo ""

# Test 4: BacktestEngine
echo "================================================================================"
echo "TEST 4/4: BacktestEngine"
echo "================================================================================"
python test_backtest_engine.py
if [ $? -eq 0 ]; then
    TEST4="✅ PASSED"
else
    TEST4="❌ FAILED"
fi
echo ""

# Summary
echo "================================================================================"
echo "SMOKE TESTS SUMMARY"
echo "================================================================================"
echo ""
echo "  $TEST1  Test 1: MicrostructureEngine"
echo "  $TEST2  Test 2: ExecutionManager + KillSwitch"
echo "  $TEST3  Test 3: Runtime Profiles"
echo "  $TEST4  Test 4: BacktestEngine"
echo ""
echo "================================================================================"

# Check if all passed
if [[ "$TEST1" == *"PASSED"* ]] && \
   [[ "$TEST2" == *"PASSED"* ]] && \
   [[ "$TEST3" == *"PASSED"* ]] && \
   [[ "$TEST4" == *"PASSED"* ]]; then
    echo "✅ ALL SMOKE TESTS PASSED - PLAN OMEGA IS PRODUCTION READY"
    echo "================================================================================"
    exit 0
else
    echo "❌ SOME SMOKE TESTS FAILED - CHECK OUTPUT ABOVE"
    echo "================================================================================"
    exit 1
fi
