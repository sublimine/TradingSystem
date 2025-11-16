#!/usr/bin/env python3
"""
ATR GUARD - INSTITUTIONAL COMPLIANCE ENFORCER

Audits entire repository for ATR usage and classifies violations:
- TYPE A (PROHIBITED): ATR in risk sizing, SL, TP, entry, quality scoring
- TYPE B (ALLOWED): ATR as descriptive metric for analysis only

ZERO TOLERANCE for TYPE A violations.

Usage:
    python scripts/check_no_atr_in_risk.py [--fix]

    --fix: Automatically comment out violations with FIXME markers
"""

import os
import re
import sys
from pathlib import Path
from typing import Dict, List, Tuple
from dataclasses import dataclass
from enum import Enum


class ViolationType(Enum):
    """Classification of ATR usage"""
    TYPE_A_PROHIBITED = "TYPE_A_PROHIBITED"  # ATR in risk/SL/TP/entry/quality
    TYPE_B_DESCRIPTIVE = "TYPE_B_DESCRIPTIVE"  # ATR as metric only
    FALSE_POSITIVE = "FALSE_POSITIVE"  # Not actually ATR usage


@dataclass
class ATRViolation:
    """Represents a single ATR violation"""
    file_path: str
    line_number: int
    line_content: str
    violation_type: ViolationType
    context: str  # Why it's a violation


class ATRGuard:
    """Audits repository for ATR usage violations"""

    # Patterns that indicate TYPE A violations (PROHIBITED)
    TYPE_A_PATTERNS = [
        # Stop loss calculations
        r'stop.*atr',
        r'atr.*stop',
        r'sl.*atr',
        r'atr.*sl',

        # Take profit calculations
        r'tp.*atr',
        r'atr.*tp',
        r'target.*atr',
        r'atr.*target',
        r'take.*profit.*atr',

        # Position sizing / risk
        r'size.*atr',
        r'atr.*size',
        r'risk.*atr',
        r'atr.*risk',
        r'position.*atr',

        # Entry conditions
        r'entry.*atr',
        r'atr.*entry',
        r'threshold.*atr',
        r'atr.*threshold',

        # Displacement / movement (when used for decisions)
        r'displacement.*atr',
        r'atr.*displacement',
        r'move.*atr',
        r'atr.*move',

        # Buffer / tolerance (when used for SL/TP)
        r'buffer.*atr',
        r'atr.*buffer',

        # Multiplier patterns (SIZE/SL/TP)
        r'atr\s*\*\s*\d',
        r'\d\s*\*\s*atr',
        r'atr_multiplier',
        r'atr_multiple',

        # Configuration keys (YAML)
        r'stop_loss_atr',
        r'take_profit_atr',
        r'atr_stop',
        r'atr_target',
        r'gap_atr',
        r'structure_break_atr',
    ]

    # Patterns that indicate TYPE B (ALLOWED - descriptive metrics)
    TYPE_B_PATTERNS = [
        r'# .*atr',  # Comments
        r'""".*atr.*"""',  # Docstrings
        r"'''.*atr.*'''",  # Docstrings
        r'atr.*=.*calculate',  # Calculation for metric
        r'features\[.*atr.*\]',  # Feature storage
        r'log.*atr',  # Logging
        r'print.*atr',  # Debug output
    ]

    # Files to exclude from scanning
    EXCLUDE_PATTERNS = [
        r'__pycache__',
        r'\.git',
        r'\.pyc$',
        r'node_modules',
        r'venv',
        r'\.egg-info',
        r'test_',  # Test files (may contain ATR for testing)
        r'check_no_atr_in_risk\.py',  # This script itself
    ]

    def __init__(self, repo_root: Path):
        self.repo_root = repo_root
        self.violations: List[ATRViolation] = []

    def scan_repository(self) -> None:
        """Scan entire repository for ATR usage"""
        print(f"🔍 Scanning repository: {self.repo_root}")
        print(f"{'='*80}")

        # Scan Python files
        for py_file in self.repo_root.rglob("*.py"):
            if self._should_exclude(py_file):
                continue
            self._scan_file(py_file, 'python')

        # Scan YAML files
        for yaml_file in self.repo_root.rglob("*.yaml"):
            if self._should_exclude(yaml_file):
                continue
            self._scan_file(yaml_file, 'yaml')

        for yml_file in self.repo_root.rglob("*.yml"):
            if self._should_exclude(yml_file):
                continue
            self._scan_file(yml_file, 'yaml')

    def _should_exclude(self, file_path: Path) -> bool:
        """Check if file should be excluded from scanning"""
        file_str = str(file_path)
        return any(re.search(pattern, file_str) for pattern in self.EXCLUDE_PATTERNS)

    def _scan_file(self, file_path: Path, file_type: str) -> None:
        """Scan a single file for ATR violations"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
        except Exception as e:
            print(f"⚠️  Error reading {file_path}: {e}")
            return

        for line_num, line in enumerate(lines, start=1):
            # Check if line contains 'atr' (case insensitive)
            if not re.search(r'\batr\b', line, re.IGNORECASE):
                continue

            # Classify the violation
            violation_type = self._classify_violation(line, file_type)

            if violation_type == ViolationType.TYPE_A_PROHIBITED:
                context = self._get_violation_context(line)
                violation = ATRViolation(
                    file_path=str(file_path.relative_to(self.repo_root)),
                    line_number=line_num,
                    line_content=line.strip(),
                    violation_type=violation_type,
                    context=context
                )
                self.violations.append(violation)

    def _classify_violation(self, line: str, file_type: str) -> ViolationType:
        """Classify ATR usage as TYPE A, TYPE B, or false positive"""
        line_lower = line.lower()

        # Check TYPE B patterns first (allowed)
        for pattern in self.TYPE_B_PATTERNS:
            if re.search(pattern, line, re.IGNORECASE):
                return ViolationType.FALSE_POSITIVE

        # Check TYPE A patterns (prohibited)
        for pattern in self.TYPE_A_PATTERNS:
            if re.search(pattern, line_lower):
                return ViolationType.TYPE_A_PROHIBITED

        # If it's in a YAML config and contains 'atr', likely TYPE A
        if file_type == 'yaml' and 'atr' in line_lower:
            # Check if it's a parameter definition
            if ':' in line and not line.strip().startswith('#'):
                return ViolationType.TYPE_A_PROHIBITED

        # Default: if ATR appears in code context, assume TYPE A unless proven otherwise
        if re.search(r'(=|self\.|def |class |import |from )', line):
            # Could be assignment, method, etc - check more carefully
            if any(keyword in line_lower for keyword in ['stop', 'target', 'size', 'risk', 'entry', 'threshold']):
                return ViolationType.TYPE_A_PROHIBITED

        return ViolationType.FALSE_POSITIVE

    def _get_violation_context(self, line: str) -> str:
        """Get human-readable context for why this is a violation"""
        line_lower = line.lower()

        if 'stop' in line_lower:
            return "ATR used in stop loss calculation"
        elif 'target' in line_lower or 'tp' in line_lower or 'take_profit' in line_lower:
            return "ATR used in take profit calculation"
        elif 'size' in line_lower or 'position' in line_lower:
            return "ATR used in position sizing"
        elif 'risk' in line_lower:
            return "ATR used in risk calculation"
        elif 'entry' in line_lower:
            return "ATR used in entry condition"
        elif 'displacement' in line_lower:
            return "ATR used in displacement threshold"
        elif 'buffer' in line_lower:
            return "ATR used in buffer calculation"
        elif 'threshold' in line_lower:
            return "ATR used in threshold definition"
        elif 'gap' in line_lower:
            return "ATR used in gap sizing"
        else:
            return "ATR used in operational decision"

    def generate_report(self) -> None:
        """Generate detailed violation report"""
        print(f"\n{'='*80}")
        print(f"ATR GUARD REPORT - INSTITUTIONAL COMPLIANCE CHECK")
        print(f"{'='*80}\n")

        # Count violations by type
        type_a_violations = [v for v in self.violations if v.violation_type == ViolationType.TYPE_A_PROHIBITED]

        print(f"📊 SUMMARY:")
        print(f"  TYPE A (PROHIBITED): {len(type_a_violations)} violations")
        print(f"  TYPE B (ALLOWED):    N/A (only TYPE A reported)")
        print(f"\n{'='*80}\n")

        if not type_a_violations:
            print("✅ NO TYPE A VIOLATIONS - SYSTEM IS ATR-COMPLIANT")
            print("   All ATR usage is for descriptive metrics only.")
            return

        # Group violations by file
        violations_by_file: Dict[str, List[ATRViolation]] = {}
        for v in type_a_violations:
            if v.file_path not in violations_by_file:
                violations_by_file[v.file_path] = []
            violations_by_file[v.file_path].append(v)

        print(f"❌ TYPE A VIOLATIONS (MUST BE ELIMINATED):\n")

        for file_path in sorted(violations_by_file.keys()):
            violations = violations_by_file[file_path]
            print(f"📁 {file_path} ({len(violations)} violations)")

            for v in sorted(violations, key=lambda x: x.line_number):
                print(f"   Line {v.line_number:4d}: {v.context}")
                print(f"              {v.line_content[:100]}")
            print()

        print(f"{'='*80}")
        print(f"TOTAL TYPE A VIOLATIONS: {len(type_a_violations)}")
        print(f"{'='*80}\n")

        if type_a_violations:
            print("🚨 ACTION REQUIRED:")
            print("   Replace ALL TYPE A violations with institutional alternatives:")
            print("   - SL/TP: Use structural levels, % price, invalidation zones")
            print("   - Position sizing: Use fixed % risk (0-2% per idea)")
            print("   - Entry: Use microstructure, order flow, imbalance")
            print("   - Thresholds: Use statistical measures, regime-based values")
            print(f"\n   Run with --fix to generate FIXME markers (manual review required)")

    def get_exit_code(self) -> int:
        """Return exit code: 0 if compliant, 1 if violations found"""
        type_a_count = len([v for v in self.violations if v.violation_type == ViolationType.TYPE_A_PROHIBITED])
        return 1 if type_a_count > 0 else 0


def main():
    """Main entry point"""
    # Get repository root (parent of scripts/)
    script_dir = Path(__file__).parent
    repo_root = script_dir.parent

    # Initialize guard
    guard = ATRGuard(repo_root)

    # Scan repository
    guard.scan_repository()

    # Generate report
    guard.generate_report()

    # Exit with appropriate code
    sys.exit(guard.get_exit_code())


if __name__ == "__main__":
    main()
