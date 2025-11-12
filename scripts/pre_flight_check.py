#!/usr/bin/env python3
"""
PRE-FLIGHT CHECK - Institutional Trading System
Verifica que TODO esté correcto antes del lanzamiento
"""

import sys
import os
from pathlib import Path
from typing import List, Tuple
import importlib.util

# Add to path
sys.path.insert(0, str(Path(__file__).parent.parent))
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

class PreFlightChecker:
    def __init__(self):
        self.errors = []
        self.warnings = []
        self.checks_passed = 0
        self.checks_total = 0

    def check(self, name: str, passed: bool, message: str = "", critical: bool = True):
        """Record check result"""
        self.checks_total += 1
        if passed:
            self.checks_passed += 1
            print(f"✅ {name}")
        else:
            symbol = "❌" if critical else "⚠️ "
            print(f"{symbol} {name}: {message}")
            if critical:
                self.errors.append(f"{name}: {message}")
            else:
                self.warnings.append(f"{name}: {message}")

    def check_imports(self):
        """Check all critical imports"""
        print("\n🔍 Checking Python dependencies...")

        required = [
            ('numpy', True),
            ('pandas', True),
            ('MetaTrader5', True),
            ('psycopg2', True),
            ('sklearn', True),
        ]

        for module_name, critical in required:
            try:
                __import__(module_name)
                self.check(f"Import {module_name}", True, critical=critical)
            except ImportError as e:
                self.check(f"Import {module_name}", False, str(e), critical=critical)

    def check_strategies(self):
        """Check all 19 institutional strategies"""
        print("\n🔍 Checking 19 institutional strategies...")

        strategies = [
            'breakout_volume_confirmation',
            'footprint_orderflow_clusters',
            'idp_inducement_distribution',
            'liquidity_sweep',
            'fvg_institutional',
            'order_block_institutional',
            'htf_ltf_liquidity',
            'nfp_news_event_handler',
            'ofi_refinement',
            'crisis_mode_volatility_spike',
            'calendar_arbitrage_flows',
            'topological_data_analysis_regime',
            'fractal_market_structure',
            'correlation_divergence',
            'correlation_cascade_detection',
            'kalman_pairs_trading',
            'statistical_arbitrage_johansen',
            'iceberg_detection',
            'spoofing_detection_l2',
        ]

        for strategy in strategies:
            try:
                # Try to import
                module = importlib.import_module(f'strategies.{strategy}')

                # Check has validate_inputs
                class_name = ''.join(word.capitalize() for word in strategy.split('_'))
                if hasattr(module, class_name):
                    cls = getattr(module, class_name)
                    has_validate = hasattr(cls, 'validate_inputs')
                    self.check(f"Strategy {strategy}", has_validate,
                             "Missing validate_inputs()" if not has_validate else "")
                else:
                    self.check(f"Strategy {strategy}", False, f"Class {class_name} not found")
            except Exception as e:
                self.check(f"Strategy {strategy}", False, str(e))

    def check_core_components(self):
        """Check core system components"""
        print("\n🔍 Checking core components...")

        components = [
            ('core.brain', 'InstitutionalBrain'),
            ('core.risk_manager', 'InstitutionalRiskManager'),
            ('core.position_manager', 'InstitutionalPositionManager'),
            ('core.regime_detector', 'RegimeDetector'),
            ('core.ml_adaptive_engine', 'MLAdaptiveEngine'),
        ]

        for module_name, class_name in components:
            try:
                module = importlib.import_module(module_name)
                if hasattr(module, class_name):
                    self.check(f"Core: {class_name}", True)
                else:
                    self.check(f"Core: {class_name}", False, "Class not found")
            except Exception as e:
                self.check(f"Core: {class_name}", False, str(e))

    def check_feature_calculators(self):
        """Check feature calculation modules"""
        print("\n🔍 Checking feature calculators...")

        features = [
            ('features.ofi', 'calculate_ofi'),
            ('features.order_flow', 'VPINCalculator'),
            ('features.order_flow', 'calculate_cumulative_volume_delta'),
            ('features.technical_indicators', 'calculate_atr'),
        ]

        for module_name, func_name in features:
            try:
                module = importlib.import_module(module_name)
                if hasattr(module, func_name):
                    self.check(f"Feature: {func_name}", True)
                else:
                    self.check(f"Feature: {func_name}", False, "Function not found")
            except Exception as e:
                self.check(f"Feature: {func_name}", False, str(e))

    def check_engines(self):
        """Check trading engines"""
        print("\n🔍 Checking trading engines...")

        engines = [
            'scripts/live_trading_engine.py',
            'scripts/live_trading_engine_institutional.py',
            'scripts/institutional_backtest.py',
        ]

        for engine in engines:
            path = Path(__file__).parent.parent / engine
            exists = path.exists()
            self.check(f"Engine: {engine}", exists, "File not found" if not exists else "")

    def check_directory_structure(self):
        """Check required directories"""
        print("\n🔍 Checking directory structure...")

        required_dirs = [
            'src/strategies',
            'src/core',
            'src/features',
            'scripts',
            'logs',
            'data',
        ]

        for dir_path in required_dirs:
            path = Path(__file__).parent.parent / dir_path
            exists = path.exists()
            if not exists:
                path.mkdir(parents=True, exist_ok=True)
                self.check(f"Directory: {dir_path}", True, "Created")
            else:
                self.check(f"Directory: {dir_path}", True)

    def print_summary(self):
        """Print final summary"""
        print("\n" + "="*80)
        print("PRE-FLIGHT CHECK SUMMARY")
        print("="*80)
        print(f"Checks passed: {self.checks_passed}/{self.checks_total}")

        if self.errors:
            print(f"\n❌ CRITICAL ERRORS ({len(self.errors)}):")
            for error in self.errors:
                print(f"  - {error}")

        if self.warnings:
            print(f"\n⚠️  WARNINGS ({len(self.warnings)}):")
            for warning in self.warnings:
                print(f"  - {warning}")

        if not self.errors:
            print("\n✅ ALL CRITICAL CHECKS PASSED - System ready for launch!")
            return True
        else:
            print("\n❌ CRITICAL ERRORS FOUND - Fix before launching!")
            return False

def main():
    checker = PreFlightChecker()

    print("="*80)
    print("INSTITUTIONAL TRADING SYSTEM - PRE-FLIGHT CHECK")
    print("="*80)

    checker.check_imports()
    checker.check_directory_structure()
    checker.check_feature_calculators()
    checker.check_core_components()
    checker.check_strategies()
    checker.check_engines()

    passed = checker.print_summary()

    sys.exit(0 if passed else 1)

if __name__ == "__main__":
    main()
