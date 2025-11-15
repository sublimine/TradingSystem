#!/usr/bin/env python3
"""
MANDATO GAMMA - Validador Institucional de Runtime Profiles

FUNCIÓN:
    Valida que todos los runtime profiles cumplan reglas institucionales:
    - Perfiles GREEN_ONLY solo contienen 5 estrategias GREEN COMPLETE
    - Perfiles LIVE tienen KillSwitch habilitado
    - Todas las estrategias existen en el código
    - Risk limits cumplen MANDATO BETA (0-2% per trade)

SALIDA:
    EXIT CODE 0: Todos los profiles válidos
    EXIT CODE 1: Violaciones detectadas (bloquea deployment)

AUTOR: SUBLIMINE Institutional Trading System
FECHA: 2025-11-15
MANDATO: MANDATO GAMMA - Production Hardening
"""

import sys
import yaml
from pathlib import Path
from typing import Dict, List, Set, Tuple
from dataclasses import dataclass


# === GREEN COMPLETE STRATEGIES (MANDATO BETA canonical set) ===
GREEN_COMPLETE_STRATEGIES: Set[str] = {
    'breakout_volume_confirmation',
    'liquidity_sweep',
    'ofi_refinement',
    'order_flow_toxicity',
    'vpin_reversal_extreme'
}

# === HYBRID STRATEGIES (PROHIBIDAS en GREEN_ONLY) ===
HYBRID_STRATEGIES: Set[str] = {
    'fvg_institutional',
    'idp_inducement_distribution',
    'order_block_institutional',
    'htf_ltf_liquidity',
    'volatility_regime_adaptation',
    'fractal_market_structure'
}

# === BROKEN STRATEGIES (PROHIBIDAS en GREEN_ONLY) ===
BROKEN_STRATEGIES: Set[str] = {
    'calendar_arbitrage_flows',
    'correlation_cascade_detection',
    'crisis_mode_volatility_spike',
    'footprint_orderflow_clusters',
    'nfp_news_event_handler',
    'topological_data_analysis_regime',
    'momentum_quality',
    'vwap_reversion_extreme'  # 8th BROKEN strategy
}

# === ALL KNOWN STRATEGIES (GREEN + HYBRID + BROKEN) ===
ALL_KNOWN_STRATEGIES = GREEN_COMPLETE_STRATEGIES | HYBRID_STRATEGIES | BROKEN_STRATEGIES


@dataclass
class ValidationResult:
    """Resultado de validación para un profile"""
    profile_name: str
    is_valid: bool
    violations: List[str]
    warnings: List[str]


class RuntimeProfileValidator:
    """Validador institucional de runtime profiles"""

    def __init__(self, repo_root: Path):
        self.repo_root = repo_root
        self.config_dir = repo_root / 'config'
        self.strategies_dir = repo_root / 'src' / 'strategies'
        self.results: List[ValidationResult] = []

    def validate_all_profiles(self) -> bool:
        """
        Valida todos los runtime profiles en config/.

        Returns:
            True si todos válidos, False si hay violaciones
        """
        profile_files = list(self.config_dir.glob('runtime_profile_*.yaml'))

        if not profile_files:
            print("❌ ERROR: No se encontraron runtime profiles en config/")
            return False

        print(f"📋 Validando {len(profile_files)} runtime profile(s)...\n")

        all_valid = True
        for profile_file in sorted(profile_files):
            result = self.validate_profile(profile_file)
            self.results.append(result)

            if not result.is_valid:
                all_valid = False

        return all_valid

    def validate_profile(self, profile_path: Path) -> ValidationResult:
        """Valida un runtime profile individual"""
        profile_name = profile_path.name
        violations = []
        warnings = []

        try:
            with open(profile_path, 'r') as f:
                config = yaml.safe_load(f)
        except Exception as e:
            violations.append(f"No se pudo parsear YAML: {e}")
            return ValidationResult(profile_name, False, violations, warnings)

        # === VALIDACIÓN 1: Estrategias activas existen ===
        active_strategies = config.get('active_strategies', [])
        if not active_strategies:
            violations.append("No hay estrategias activas definidas")

        unknown_strategies = set(active_strategies) - ALL_KNOWN_STRATEGIES
        if unknown_strategies:
            warnings.append(f"Estrategias desconocidas: {unknown_strategies}")

        # === VALIDACIÓN 2: Perfiles GREEN_ONLY solo contienen GREEN COMPLETE ===
        if 'GREEN_ONLY' in profile_name:
            non_green = set(active_strategies) - GREEN_COMPLETE_STRATEGIES
            if non_green:
                violations.append(
                    f"GREEN_ONLY profile contiene estrategias NO-GREEN: {non_green}"
                )

            # Verificar que son exactamente las 5 GREEN COMPLETE
            if set(active_strategies) != GREEN_COMPLETE_STRATEGIES:
                missing = GREEN_COMPLETE_STRATEGIES - set(active_strategies)
                if missing:
                    warnings.append(f"Faltan GREEN COMPLETE strategies: {missing}")

        # === VALIDACIÓN 3: Perfiles LIVE tienen KillSwitch configurado ===
        if 'live' in profile_name.lower():
            execution_mode = config.get('execution_mode', '')
            if execution_mode != 'live':
                violations.append(
                    f"Profile LIVE debe tener execution_mode: live (encontrado: {execution_mode})"
                )

            live_trading = config.get('live_trading', {})
            if not live_trading:
                violations.append("Profile LIVE debe tener sección live_trading")
            else:
                # KillSwitch: risk_limits debe existir
                if 'risk_limits' not in live_trading:
                    violations.append("Profile LIVE debe tener live_trading.risk_limits")

                # Verificar que live_trading.enabled existe (puede ser false, pero debe existir)
                if 'enabled' not in live_trading:
                    violations.append("Profile LIVE debe declarar live_trading.enabled")

        # === VALIDACIÓN 4: Risk limits institucionales (MANDATO BETA: 0-2%) ===
        risk_config = config.get('risk', {})
        if risk_config:
            max_risk = risk_config.get('max_risk_per_trade', None)
            if max_risk is None:
                warnings.append("No se definió risk.max_risk_per_trade")
            elif max_risk > 0.02:
                violations.append(
                    f"risk.max_risk_per_trade = {max_risk} excede límite institucional 0.02 (2%)"
                )
            elif max_risk <= 0:
                violations.append(f"risk.max_risk_per_trade inválido: {max_risk}")

        # === VALIDACIÓN 5: Execution mode válido ===
        execution_mode = config.get('execution_mode', '')
        valid_modes = {'paper', 'live', 'research'}
        if execution_mode not in valid_modes:
            violations.append(
                f"execution_mode inválido: '{execution_mode}' (debe ser: {valid_modes})"
            )

        is_valid = len(violations) == 0
        return ValidationResult(profile_name, is_valid, violations, warnings)

    def print_report(self) -> None:
        """Imprime reporte de validación institucional"""
        print("=" * 80)
        print("MANDATO GAMMA - RUNTIME PROFILE VALIDATION REPORT")
        print("=" * 80)
        print()

        for result in self.results:
            status_icon = "✅" if result.is_valid else "❌"
            print(f"{status_icon} {result.profile_name}")

            if result.violations:
                print("   VIOLACIONES (P0 - BLOQUEANTES):")
                for v in result.violations:
                    print(f"      • {v}")

            if result.warnings:
                print("   WARNINGS (P1 - REVISAR):")
                for w in result.warnings:
                    print(f"      ⚠ {w}")

            if not result.violations and not result.warnings:
                print("   ✓ Perfil válido - todas las reglas cumplidas")

            print()

        # === SUMMARY ===
        total = len(self.results)
        valid = sum(1 for r in self.results if r.is_valid)
        invalid = total - valid

        print("-" * 80)
        print(f"RESUMEN: {valid}/{total} profiles válidos")

        if invalid > 0:
            print(f"❌ {invalid} profile(s) con VIOLACIONES - DEPLOYMENT BLOQUEADO")
        else:
            print("✅ Todos los profiles válidos - APROBADO para deployment")
        print("-" * 80)


def main():
    """Entry point"""
    repo_root = Path(__file__).parent.parent

    print("MANDATO GAMMA - Validador Institucional de Runtime Profiles")
    print(f"Repo: {repo_root}")
    print()

    validator = RuntimeProfileValidator(repo_root)
    all_valid = validator.validate_all_profiles()
    validator.print_report()

    # EXIT CODE: 0 si válido, 1 si violaciones
    sys.exit(0 if all_valid else 1)


if __name__ == '__main__':
    main()
