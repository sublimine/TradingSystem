#!/usr/bin/env python3
"""
MANDATO GAMMA - Guardia Contra ATR en Risk/Sizing/SL/TP

FUNCIÓN:
    Escanea codebase para detectar uso prohibido de ATR en:
    - Position sizing
    - Stop loss calculation
    - Take profit calculation
    - Risk calculation (portfolio, per-trade)

    ATR SOLO permitido como métrica descriptiva (logging, reporting).

SALIDA:
    EXIT CODE 0: ZERO ATR contamination en risk paths
    EXIT CODE 1: ATR contamination detectada (bloquea deployment)

AUTOR: SUBLIMINE Institutional Trading System
FECHA: 2025-11-15
MANDATO: MANDATO GAMMA - Production Hardening
"""

import sys
import re
from pathlib import Path
from typing import List, Dict, Tuple
from dataclasses import dataclass


@dataclass
class ATRViolation:
    """Violación de uso prohibido de ATR"""
    file_path: Path
    line_number: int
    line_content: str
    violation_type: str  # 'sizing', 'stop_loss', 'take_profit', 'risk_calc'
    severity: str  # 'P0_BLOCKING', 'P1_WARNING'


class ATRGuard:
    """
    Guard contra reintroducción de ATR en risk paths.

    MANDATO BETA estableció: ATR PROHIBIDO en sizing/SL/TP/risk.
    Este script asegura que no se reintroduzca ATR en esos paths.
    """

    def __init__(self, repo_root: Path):
        self.repo_root = repo_root
        self.violations: List[ATRViolation] = []

        # === PROHIBITED PATTERNS (P0 - BLOCKING) ===
        # Estos patrones indican uso prohibido de ATR
        self.prohibited_patterns = [
            # Position sizing with ATR
            (r'\bposition.*size.*atr\b', 'sizing', 'P0_BLOCKING'),
            (r'\bsize.*position.*atr\b', 'sizing', 'P0_BLOCKING'),
            (r'\bvolume.*atr\b', 'sizing', 'P0_BLOCKING'),
            (r'\blot.*size.*atr\b', 'sizing', 'P0_BLOCKING'),

            # Stop loss with ATR
            (r'\bstop.*loss.*atr\b', 'stop_loss', 'P0_BLOCKING'),
            (r'\bsl.*atr\b', 'stop_loss', 'P0_BLOCKING'),
            (r'\bcalculate_stop.*atr\b', 'stop_loss', 'P0_BLOCKING'),
            (r'\bstop.*distance.*atr\b', 'stop_loss', 'P0_BLOCKING'),

            # Take profit with ATR
            (r'\btake.*profit.*atr\b', 'take_profit', 'P0_BLOCKING'),
            (r'\btp.*atr\b', 'take_profit', 'P0_BLOCKING'),
            (r'\bcalculate_tp.*atr\b', 'take_profit', 'P0_BLOCKING'),
            (r'\btarget.*atr\b', 'take_profit', 'P0_BLOCKING'),

            # Risk calculation with ATR
            (r'\brisk.*per.*trade.*atr\b', 'risk_calc', 'P0_BLOCKING'),
            (r'\bcalculate.*risk.*atr\b', 'risk_calc', 'P0_BLOCKING'),
            (r'\brisk.*amount.*atr\b', 'risk_calc', 'P0_BLOCKING'),
            (r'\bmax.*risk.*atr\b', 'risk_calc', 'P0_BLOCKING'),

            # Multiplier patterns (common in ATR-based sizing)
            (r'\batr\s*\*\s*multiplier\b', 'sizing', 'P0_BLOCKING'),
            (r'\bmultiplier\s*\*\s*atr\b', 'sizing', 'P0_BLOCKING'),
            (r'\batr\s*\*\s*[\d.]+', 'sizing', 'P0_BLOCKING'),  # atr * 2.0, etc.
        ]

        # === ALLOWED PATTERNS (context where ATR is OK) ===
        # ATR permitido solo como métrica descriptiva
        self.allowed_contexts = [
            r'#.*atr',  # Comments
            r'logger\..*atr',  # Logging
            r'print.*atr',  # Debug prints
            r'report.*atr',  # Reporting
            r'metric.*atr',  # Metrics
            r'feature.*atr',  # Feature calculation (microstructure)
            r'MicrostructureFeatures.*atr',  # MicrostructureFeatures dataclass
            r'calculate_atr\(',  # Technical indicator calculation
            r'def calculate_atr',  # Function definition
            r'⚠️.*MANDATO.*ATR',  # MANDATO warning comments
        ]

    def scan_all_files(self) -> bool:
        """
        Escanea todos los archivos críticos.

        Returns:
            True si ZERO violations, False si violations detectadas
        """
        print("MANDATO GAMMA - ATR Guard: Scanning for prohibited ATR usage...")
        print()

        # === CRITICAL PATHS (high priority) ===
        critical_paths = [
            self.repo_root / 'src' / 'risk_management.py',
            self.repo_root / 'src' / 'position_manager.py',
            self.repo_root / 'src' / 'core' / 'risk_manager.py',
            self.repo_root / 'src' / 'core' / 'position_sizing.py',
        ]

        # Scan critical files (individual)
        for file_path in critical_paths:
            if file_path.exists():
                self._scan_file(file_path, critical=True)

        # === STRATEGY FILES ===
        strategies_dir = self.repo_root / 'src' / 'strategies'
        if strategies_dir.exists():
            for strategy_file in strategies_dir.glob('*.py'):
                if strategy_file.name == '__init__.py':
                    continue
                self._scan_file(strategy_file, critical=False)

        # === RISK MODULE (all files) ===
        risk_dirs = [
            self.repo_root / 'src' / 'risk',
            self.repo_root / 'src' / 'core' / 'risk',
        ]
        for risk_dir in risk_dirs:
            if risk_dir.exists():
                for risk_file in risk_dir.glob('**/*.py'):
                    self._scan_file(risk_file, critical=True)

        return len(self.violations) == 0

    def _scan_file(self, file_path: Path, critical: bool = False):
        """Escanea un archivo para violations"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()

            for line_num, line in enumerate(lines, start=1):
                line_lower = line.lower()

                # Skip if ATR in allowed context
                if self._is_allowed_context(line):
                    continue

                # Check prohibited patterns
                for pattern, violation_type, severity in self.prohibited_patterns:
                    if re.search(pattern, line_lower, re.IGNORECASE):
                        # Found violation
                        self.violations.append(ATRViolation(
                            file_path=file_path,
                            line_number=line_num,
                            line_content=line.strip(),
                            violation_type=violation_type,
                            severity=severity
                        ))

        except Exception as e:
            print(f"⚠️  WARNING: No se pudo leer {file_path}: {e}")

    def _is_allowed_context(self, line: str) -> bool:
        """Verifica si la línea está en contexto permitido"""
        for allowed_pattern in self.allowed_contexts:
            if re.search(allowed_pattern, line, re.IGNORECASE):
                return True
        return False

    def print_report(self) -> None:
        """Imprime reporte de violations"""
        print("=" * 80)
        print("MANDATO GAMMA - ATR GUARD REPORT")
        print("=" * 80)
        print()

        if not self.violations:
            print("✅ ZERO ATR CONTAMINATION DETECTED")
            print()
            print("ATR usage is limited to descriptive metrics only.")
            print("NO ATR found in: position sizing, stop loss, take profit, risk calculation.")
            print()
            print("-" * 80)
            print("✅ APROBADO - Safe to deploy")
            print("=" * 80)
            return

        # Group violations by severity
        p0_violations = [v for v in self.violations if v.severity == 'P0_BLOCKING']
        p1_violations = [v for v in self.violations if v.severity == 'P1_WARNING']

        if p0_violations:
            print(f"❌ {len(p0_violations)} P0 BLOCKING VIOLATIONS DETECTED")
            print()
            print("ATR found in PROHIBITED paths (sizing/SL/TP/risk):")
            print()

            # Group by file
            violations_by_file: Dict[Path, List[ATRViolation]] = {}
            for v in p0_violations:
                if v.file_path not in violations_by_file:
                    violations_by_file[v.file_path] = []
                violations_by_file[v.file_path].append(v)

            for file_path, violations in violations_by_file.items():
                rel_path = file_path.relative_to(self.repo_root)
                print(f"📁 {rel_path}")
                for v in violations:
                    print(f"   Line {v.line_number:4d} [{v.violation_type:12s}]: {v.line_content[:60]}")
                print()

        if p1_violations:
            print(f"⚠️  {len(p1_violations)} P1 WARNINGS (non-blocking)")
            print()

        print("-" * 80)
        if p0_violations:
            print("❌ DEPLOYMENT BLOQUEADO")
            print()
            print("ACCIÓN REQUERIDA:")
            print("1. Remover ATR de paths prohibidos (sizing/SL/TP/risk)")
            print("2. Usar stops estructurales (extreme price, order blocks, wick sweeps)")
            print("3. Re-ejecutar: python scripts/check_no_atr_in_risk.py")
            print()
            print("REFERENCIA: docs/MANDATO_ATR_PURGE_20251115.md")
        else:
            print("✅ APROBADO con warnings menores")

        print("=" * 80)


def main():
    """Entry point"""
    repo_root = Path(__file__).parent.parent

    print("MANDATO GAMMA - ATR Guard")
    print(f"Repo: {repo_root}")
    print()

    guard = ATRGuard(repo_root)
    clean = guard.scan_all_files()
    guard.print_report()

    # EXIT CODE: 0 si limpio, 1 si violations
    sys.exit(0 if clean else 1)


if __name__ == '__main__':
    main()
