import os
from pathlib import Path

RISK_KEYWORDS = [
    "stop_loss", "stop loss", "sl_", " sl",
    "take_profit", "take profit", "tp_", " tp",
    "target",
    "risk_", " risk",
    "position_size",
    "qty", "quantity",
    "exposure", "leverage",
    "lot", "lots",
]

ROOTS = ["src", "scripts"]


def scan_file(path: Path):
    type_a = []
    type_b = []

    try:
        text = path.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return type_a, type_b

    in_docstring = False

    for idx, line in enumerate(text.splitlines(), start=1):
        stripped = line.strip()

        # Detectar y saltar docstrings ("""...""" o '''...''')
        triple_count = stripped.count('"""') + stripped.count("'''")
        if in_docstring or triple_count:
            if triple_count % 2 == 1:
                in_docstring = not in_docstring
            # No analizamos docstrings
            continue

        # Separar código del comentario inline
        if "#" in line:
            code_part = line.split("#", 1)[0]
        else:
            code_part = line

        lower_code = code_part.lower()

        if "atr" not in lower_code:
            continue

        # Stub legacy: permitido como TYPE B (bloquea uso real)
        if "calculate_stop_loss_atr" in lower_code:
            type_b.append((idx, line.rstrip()))
            continue

        if any(kw in lower_code for kw in RISK_KEYWORDS):
            type_a.append((idx, line.rstrip()))
        else:
            type_b.append((idx, line.rstrip()))

    return type_a, type_b


def main():
    repo_root = Path(__file__).resolve().parent.parent

    print(f"🔍 Scanning repository: {repo_root}")
    print("=" * 80)
    print()
    print("=" * 80)
    print("ATR GUARD REPORT - INSTITUTIONAL COMPLIANCE CHECK")
    print("=" * 80)
    print()

    total_a = 0
    total_b = 0
    per_file_a = {}

    for root in ROOTS:
        root_path = repo_root / root
        if not root_path.exists():
            continue

        for dirpath, _, filenames in os.walk(root_path):
            for name in filenames:
                if not name.endswith(".py"):
                    continue
                if name == "check_no_atr_in_risk.py":
                    continue

                file_path = Path(dirpath) / name
                type_a, type_b = scan_file(file_path)

                if type_a:
                    rel = os.path.relpath(file_path, repo_root)
                    per_file_a.setdefault(rel, []).extend(type_a)
                    total_a += len(type_a)

                total_b += len(type_b)

    print("📊 SUMMARY:")
    print(f"  TYPE A (PROHIBITED): {total_a} violations")
    print(f"  TYPE B (ALLOWED):    {total_b} occurrences")
    print()
    print("=" * 80)

    if total_a:
        print("❌ TYPE A VIOLATIONS (MUST BE ELIMINATED):")
        print()
        for rel, items in sorted(per_file_a.items()):
            print(f"📁 {rel} ({len(items)} violations)")
            for lineno, line in items:
                print(f"   Line {lineno:4d}: {line}")
            print()
        print("=" * 80)
        print(f"TOTAL TYPE A VIOLATIONS: {total_a}")
        print("=" * 80)
        print()
        print("🚨 ACTION REQUIRED:")
        print("   Replace ALL TYPE A violations with institutional alternatives:")
        print("   - SL/TP: Use structural levels, % price, invalidation zones")
        print("   - Position sizing: Use fixed % risk (0-2% per idea)")
        print("   - Entry: Use microstructure, order flow, imbalance")
        print("   - Thresholds: Use statistical measures, regime-based values")
    else:
        print("✅ NO TYPE A VIOLATIONS - SYSTEM IS ATR-COMPLIANT")
        print("   All ATR usage is classified as descriptive / non-risk.")
    print()


if __name__ == "__main__":
    main()
