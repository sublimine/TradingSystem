#!/usr/bin/env python3
"""
INSTITUTIONAL ATR GUARD - MANDATO DELTA
========================================
Verifica que CERO lógica de riesgo, sizing, SL/TP dependa de ATR.

REGLAS:
- ATR PROHIBIDO en: sizing, SL/TP, filtros de entrada/salida
- ATR PERMITIDO en: indicadores puramente descriptivos/informativos
- Exit code 1 si hay violaciones, 0 si limpio

Autor: Arquitecto Cuant Institucional
Fecha: 2025-11-16
"""

import re
import sys
from pathlib import Path
from typing import List, Tuple
from dataclasses import dataclass


@dataclass
class Violation:
    """Violación de ATR encontrada"""
    file_path: str
    line_number: int
    line_content: str
    context: str


class ATRGuard:
    """Guard para detectar uso prohibido de ATR en lógica de riesgo"""

    # Archivos/directorios a escanear
    SCAN_PATHS = [
        "src/strategies",
        "src/risk_management.py",
        "src/core",
        "src/risk",
        "src/signal_generator",
    ]

    # Archivos EXCLUIDOS (solo indicadores descriptivos)
    EXCLUDED_FILES = {
        "src/features/technical_indicators.py",
        "src/features/volatility_indicators.py",
        "src/microstructure/engine.py",  # Solo métricas descriptivas
    }

    # Patrones de ATR prohibidos
    ATR_PATTERNS = [
        r'\bATR\b',
        r'\batr\b',
        r'AverageTrueRange',
        r'average_true_range',
        r'calculate_atr',
        r'get_atr',
    ]

    # Patrones de contexto PERMITIDO (comentarios, docstrings, etc.)
    ALLOWED_CONTEXTS = [
        r'^\s*#',           # Comentarios
        r'^\s*"""',         # Docstrings
        r"^\s*'''",         # Docstrings
        r'# DEPRECATED',    # Código deprecated
        r'# TODO.*remove',  # TODOs para remover ATR
    ]

    def __init__(self, repo_root: Path):
        self.repo_root = repo_root
        self.violations: List[Violation] = []

    def is_excluded_file(self, file_path: Path) -> bool:
        """Verifica si el archivo está en la lista de exclusión"""
        relative_path = str(file_path.relative_to(self.repo_root))
        return any(relative_path == excluded or relative_path.startswith(excluded)
                   for excluded in self.EXCLUDED_FILES)

    def is_allowed_context(self, line: str) -> bool:
        """Verifica si la línea está en contexto permitido (comentario, etc.)"""
        stripped = line.strip()
        return any(re.match(pattern, stripped) for pattern in self.ALLOWED_CONTEXTS)

    def scan_file(self, file_path: Path) -> List[Violation]:
        """Escanea un archivo en busca de violaciones ATR"""
        violations = []

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()

            in_docstring = False
            docstring_char = None

            for line_num, line in enumerate(lines, start=1):
                # Detectar docstrings multi-línea
                stripped = line.strip()
                if stripped.startswith('"""') or stripped.startswith("'''"):
                    if not in_docstring:
                        in_docstring = True
                        docstring_char = stripped[:3]
                    elif stripped.endswith(docstring_char):
                        in_docstring = False
                        continue

                # Saltar si estamos en docstring o comentario
                if in_docstring or self.is_allowed_context(line):
                    continue

                # Buscar patrones ATR
                for pattern in self.ATR_PATTERNS:
                    if re.search(pattern, line):
                        # Verificar que no sea un falso positivo (ej: "pattern", "matter")
                        if self._is_genuine_atr_reference(line, pattern):
                            context = self._extract_context(lines, line_num - 1)
                            violations.append(Violation(
                                file_path=str(file_path.relative_to(self.repo_root)),
                                line_number=line_num,
                                line_content=line.rstrip(),
                                context=context
                            ))
                            break  # Una violación por línea

        except Exception as e:
            print(f"⚠️  Error leyendo {file_path}: {e}", file=sys.stderr)

        return violations

    def _is_genuine_atr_reference(self, line: str, pattern: str) -> bool:
        """Verifica que sea una referencia genuina a ATR, no un falso positivo"""
        # Excluir palabras que contienen 'atr' pero no son ATR
        false_positives = ['pattern', 'matter', 'theatre', 'atro', 'patriot']
        line_lower = line.lower()

        for fp in false_positives:
            if fp in line_lower and pattern.lower() in fp:
                return False

        return True

    def _extract_context(self, lines: List[str], line_idx: int, context_lines: int = 2) -> str:
        """Extrae contexto alrededor de la violación"""
        start = max(0, line_idx - context_lines)
        end = min(len(lines), line_idx + context_lines + 1)
        context_lines_list = lines[start:end]

        # Determinar si es sizing, SL, TP, filtro, etc.
        context_text = ''.join(context_lines_list).lower()

        if 'position_size' in context_text or 'sizing' in context_text or 'quantity' in context_text:
            return "SIZING LOGIC"
        elif 'stop_loss' in context_text or 'stop loss' in context_text or 'sl' in context_text:
            return "STOP LOSS LOGIC"
        elif 'take_profit' in context_text or 'take profit' in context_text or 'tp' in context_text:
            return "TAKE PROFIT LOGIC"
        elif 'filter' in context_text or 'entry' in context_text or 'exit' in context_text:
            return "ENTRY/EXIT FILTER"
        elif 'risk' in context_text:
            return "RISK MANAGEMENT"
        else:
            return "STRATEGY LOGIC"

    def scan_all(self) -> int:
        """Escanea todos los archivos relevantes"""
        print("🔍 INSTITUTIONAL ATR GUARD - MANDATO DELTA")
        print("=" * 80)
        print()

        total_files = 0

        for scan_path in self.SCAN_PATHS:
            path = self.repo_root / scan_path

            if not path.exists():
                print(f"⚠️  Path no encontrado: {scan_path}")
                continue

            if path.is_file():
                if not self.is_excluded_file(path):
                    total_files += 1
                    violations = self.scan_file(path)
                    self.violations.extend(violations)
            else:
                # Escanear todos los .py en el directorio
                for py_file in path.rglob("*.py"):
                    if not self.is_excluded_file(py_file):
                        total_files += 1
                        violations = self.scan_file(py_file)
                        self.violations.extend(violations)

        print(f"📊 Archivos escaneados: {total_files}")
        print(f"📊 Violaciones encontradas: {len(self.violations)}")
        print()

        if self.violations:
            self._report_violations()
            return 1
        else:
            print("✅ SISTEMA LIMPIO - CERO ATR EN LÓGICA DE RIESGO")
            print()
            return 0

    def _report_violations(self):
        """Reporta todas las violaciones encontradas"""
        print("❌ VIOLACIONES DETECTADAS:")
        print("=" * 80)
        print()

        # Agrupar por archivo
        violations_by_file = {}
        for v in self.violations:
            if v.file_path not in violations_by_file:
                violations_by_file[v.file_path] = []
            violations_by_file[v.file_path].append(v)

        for file_path, file_violations in sorted(violations_by_file.items()):
            print(f"📄 {file_path}")
            print("-" * 80)
            for v in sorted(file_violations, key=lambda x: x.line_number):
                print(f"  Línea {v.line_number:4d} [{v.context}]")
                print(f"    {v.line_content.strip()}")
                print()
            print()

        print("=" * 80)
        print(f"🚨 TOTAL: {len(self.violations)} violaciones ATR en lógica de riesgo")
        print()
        print("ACCIÓN REQUERIDA:")
        print("  1. Eliminar TODAS las referencias a ATR en sizing/SL/TP")
        print("  2. Reemplazar con lógica estructural (swing levels, order blocks, etc.)")
        print("  3. Volver a ejecutar este guard hasta que pase")
        print()


def main():
    """Entry point"""
    repo_root = Path(__file__).parent.parent

    guard = ATRGuard(repo_root)
    exit_code = guard.scan_all()

    sys.exit(exit_code)


if __name__ == "__main__":
    main()
